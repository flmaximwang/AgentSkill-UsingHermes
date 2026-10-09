#!/usr/bin/env python3
"""Apple Calendar access for the `secretary` Hermes profile.

Read and write the calendars of the logged-in macOS user through
AppleScript (`osascript`).  No Full Disk Access needed: everything goes
through Calendar.app's scripting interface, so macOS only asks for the
one-time "Automation" permission.

Usage
-----
  cal.py calendars [--json]
  cal.py events [--calendar NAME] [--from -7] [--to +30] [--all-calendars]
                [--include-noise] [--json] [--limit N]
  cal.py today  [--json]
  cal.py week   [--json]
  cal.py add --calendar NAME --title T --date 2026-10-08 --start 09:00
             [--end 10:00] [--minutes 60] [--notes N] [--location L] [--allday]
  cal.py delete --calendar NAME --title T [--from -1] [--to +30] [--yes]

Reading is safe and always allowed.  `add` / `delete` change the user's
real calendar: confirm with the user before running them.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import unicodedata

OSASCRIPT = "/usr/bin/osascript"

# Calendars that are not the user's own schedule.
NOISE = {"中国大陆节假日", "Siri建议", "计划的提醒事项", "Holidays"}

# One AppleScript body for reading events.  argv: calendarName|ALL, from, to.
READ_SCRIPT = r'''
on run argv
	set calName to item 1 of argv
	set fromOff to (item 2 of argv) as integer
	set toOff to (item 3 of argv) as integer
	set dFrom to (current date) + (fromOff * days)
	set time of dFrom to 0
	set dTo to (current date) + (toOff * days)
	set time of dTo to 0
	set dTo to dTo + (1 * days) - 1
	set out to ""
	tell application "Calendar"
		if calName is "ALL" then
			set theCals to every calendar
		else
			set theCals to {calendar calName}
		end if
		repeat with c in theCals
			set cName to name of c
			try
				set evs to (every event of c whose start date is greater than or equal to dFrom and start date is less than or equal to dTo)
				repeat with e in evs
					set sD to (start date of e)
					set eD to (end date of e)
					set ad to "0"
					try
						if allday event of e then set ad to "1"
					end try
					set out to out & cName & tab & (summary of e) & tab & (sD as string) & tab & (eD as string) & tab & ad & linefeed
				end repeat
			on error errMsg
				set out to out & cName & tab & "[read error] " & errMsg & tab & "" & tab & "" & tab & "" & linefeed
			end try
		end repeat
	end tell
	return out
end run
'''

LIST_SCRIPT = r'''
tell application "Calendar"
	return name of every calendar
end tell
'''

WRITE_SCRIPT = r'''
on run argv
	set calName to item 1 of argv
	set evTitle to item 2 of argv
	set dayOff to (item 3 of argv) as integer
	set hh to (item 4 of argv) as integer
	set mm to (item 5 of argv) as integer
	set durMin to (item 6 of argv) as integer
	set notesTxt to item 7 of argv
	set locTxt to item 8 of argv
	set isAllDay to (item 9 of argv) as integer

	set dStart to (current date)
	set time of dStart to 0
	set dStart to dStart + (dayOff * days)
	set hours of dStart to hh
	set minutes of dStart to mm
	set seconds of dStart to 0
	set dEnd to dStart + (durMin * minutes)
	set ad to false
	if isAllDay is 1 then set ad to true
	tell application "Calendar"
		tell calendar calName
			set newEv to make new event with properties {summary:evTitle, start date:dStart, end date:dEnd, allday event:ad}
			if notesTxt is not "" then set description of newEv to notesTxt
			if locTxt is not "" then set location of newEv to locTxt
			return "CREATED " & (uid of newEv)
		end tell
	end tell
end run
'''

FIND_SCRIPT = r'''
on run argv
	set calName to item 1 of argv
	set evTitle to item 2 of argv
	set fromOff to (item 3 of argv) as integer
	set toOff to (item 4 of argv) as integer
	set dFrom to (current date) + (fromOff * days)
	set time of dFrom to 0
	set dTo to (current date) + (toOff * days) + (1 * days)
	set out to ""
	tell application "Calendar"
		tell calendar calName
			set evs to (every event whose start date is greater than or equal to dFrom and start date is less than or equal to dTo and summary is evTitle)
			repeat with e in evs
				set out to out & (uid of e) & tab & (summary of e) & tab & ((start date of e) as string) & tab & calName & linefeed
			end repeat
		end tell
	end tell
	return out
end run
'''

DELETE_SCRIPT = r'''
on run argv
	set uids to items 2 thru -1 of argv
	tell application "Calendar"
		set n to 0
		repeat with u in uids
			set uStr to (u as string)
			repeat with c in (every calendar)
				try
					set hits to (every event of c whose uid is uStr)
					repeat with e in hits
						delete e
						set n to n + 1
					end repeat
				end try
			end repeat
		end repeat
		return "DELETED " & n
	end tell
end run
'''


def run_script(source: str, args: list[str] | None = None) -> str:
    if not shutil.which("osascript") and not (OSASCRIPT and __import__("os").path.exists(OSASCRIPT)):
        sys.exit("osascript not found — this skill only works on macOS")
    cmd = [OSASCRIPT, "-e", source] if args is None else [OSASCRIPT, "-", *args]
    proc = subprocess.run(
        cmd,
        input=source if args is not None else None,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        sys.exit(f"osascript failed (rc={proc.returncode}):\n{proc.stderr.strip()}")
    return proc.stdout


def parse_rows(raw: str) -> list[dict]:
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        rows.append(
            {
                "calendar": parts[0],
                "title": parts[1],
                "start": parts[2],
                "end": parts[3],
                "all_day": parts[4] == "1",
            }
        )
    return rows


def pretty(rows: list[dict]) -> str:
    if not rows:
        return "(no events in this window)"
    out = []
    cur = None
    for r in rows:
        if r["calendar"] != cur:
            cur = r["calendar"]
            out.append(f"### {cur}")
        flag = " [全天]" if r["all_day"] else ""
        out.append(f"  - {r['start']} → {r['end'][-8:]} | {r['title']}{flag}")
    return "\n".join(out)


def cmd_calendars(a) -> None:
    names = [n.strip() for n in run_script(LIST_SCRIPT).split(",") if n.strip()]
    if a.json:
        print(json.dumps(names, ensure_ascii=False, indent=2))
    else:
        for n in names:
            print(("- " if n in NOISE else "* ") + n + ("   (noise)" if n in NOISE else ""))


def cmd_events(a, from_off: int, to_off: int) -> None:
    if a.all_calendars:
        cal = "ALL"
    elif a.calendar:
        cal = a.calendar
    else:
        cal = "ALL"
    rows = parse_rows(run_script(READ_SCRIPT, [cal, str(from_off), str(to_off)]))
    if not a.include_noise:
        rows = [r for r in rows if r["calendar"] not in NOISE]
    rows.sort(key=lambda r: r["start"])
    if a.limit:
        rows = rows[: a.limit]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(pretty(rows))


def cmd_add(a) -> None:
    from datetime import date as _date

    y, mo, d = (int(x) for x in a.date.split("-"))
    hh, mm = (int(x) for x in a.start.split(":"))
    if a.end:
        eh, em = (int(x) for x in a.end.split(":"))
        dur = (eh * 60 + em) - (hh * 60 + mm)
    else:
        dur = a.minutes
    if dur <= 0:
        sys.exit("end time must be after start time")
    today = _date.today()
    day_off = (_date(y, mo, d) - today).days
    out = run_script(
        WRITE_SCRIPT,
        [a.calendar, a.title, str(day_off), str(hh), str(mm), str(dur), a.notes or "", a.location or "", "1" if a.allday else "0"],
    )
    print(out.strip())
    print(f"→ {a.date} {a.start} ({dur} min) «{a.title}» in calendar «{a.calendar}»")


def cmd_delete(a) -> None:
    hits = [l for l in run_script(FIND_SCRIPT, [a.calendar, a.title, str(a.frm), str(a.to)]).splitlines() if l.strip()]
    if not hits:
        print("no matching event found — nothing deleted")
        return
    for h in hits:
        print("match: " + h.replace("\t", " | "))
    if not a.yes:
        sys.exit("refusing to delete without --yes (show these matches to the user first)")
    uids = [h.split("\t")[0] for h in hits]
    print(run_script(DELETE_SCRIPT, ["x", *uids]).strip())


def main() -> None:
    p = argparse.ArgumentParser(description="Apple Calendar via AppleScript")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("calendars")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_calendars)

    for name, frm, to in (("events", -7, 30), ("today", 0, 0), ("week", 0, 7)):
        e = sub.add_parser(name)
        e.add_argument("--calendar")
        e.add_argument("--all-calendars", action="store_true")
        e.add_argument("--from", dest="frm", type=int, default=frm)
        e.add_argument("--to", dest="to", type=int, default=to)
        e.add_argument("--include-noise", action="store_true")
        e.add_argument("--limit", type=int, default=0)
        e.add_argument("--json", action="store_true")
        e.set_defaults(fn=cmd_events)

    w = sub.add_parser("add")
    w.add_argument("--calendar", required=True)
    w.add_argument("--title", required=True)
    w.add_argument("--date", required=True, help="YYYY-MM-DD")
    w.add_argument("--start", required=True, help="HH:MM")
    w.add_argument("--end", help="HH:MM")
    w.add_argument("--minutes", type=int, default=60)
    w.add_argument("--notes")
    w.add_argument("--location")
    w.add_argument("--allday", action="store_true")
    w.set_defaults(fn=cmd_add)

    d = sub.add_parser("delete")
    d.add_argument("--calendar", required=True)
    d.add_argument("--title", required=True)
    d.add_argument("--from", dest="frm", type=int, default=-1)
    d.add_argument("--to", dest="to", type=int, default=30)
    d.add_argument("--yes", action="store_true")
    d.set_defaults(fn=cmd_delete)

    a = p.parse_args()
    if a.fn is cmd_events:
        cmd_events(a, a.frm, a.to)
    else:
        a.fn(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
