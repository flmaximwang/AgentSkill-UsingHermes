---
name: apple-calendar
description: Use when the user asks about their schedule, appointments, meetings, 日程, 安排, 空闲时间, or wants to read/add/move/delete events — Apple Calendar (日历.app) on this Mac through the bundled `cal.py` AppleScript bridge.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [calendar, apple, macos, applescript, scheduling, 日程]
    category: apple
    related_skills: [macos-computer-use]
---

# Apple Calendar (macOS) — read and write the user's real calendars

This skill is the only supported way for this profile to see the user's schedule. It drives
**Calendar.app** (`日历.app`) through AppleScript, using the bundled script:

```
scripts/cal.py          # in this skill's directory
```

Paths are relative to this skill dir; resolve it with
`$(dirname "$(realpath "$0")")` or just use the absolute path
`~/.hermes/profiles/daily-scheduler/skills/apple/apple-calendar/scripts/cal.py`.

## Commands (all verified working on this machine, 2026-10-05)

```bash
CAL=~/.hermes/profiles/daily-scheduler/skills/apple/apple-calendar/scripts/cal.py

python3 $CAL calendars                       # list calendars (* = the user's own, - = noise)
python3 $CAL today                           # today's events
python3 $CAL week                            # today .. +7 days
python3 $CAL events --from -7 --to 30        # window in DAYS relative to today, all own calendars
python3 $CAL events --calendar 个人 --from 0 --to 14
python3 $CAL events --from 0 --to 60 --json  # machine-readable
python3 $CAL events --include-noise --all-calendars

# writes — ASK THE USER FIRST, these hit the real calendar
python3 $CAL add --calendar 个人 --title "组会" --date 2026-10-08 --start 14:00 --minutes 90 \
                 [--notes "..." --location "..." --allday]
python3 $CAL delete --calendar 个人 --title "组会" --from -1 --to 30          # dry run: shows matches
python3 $CAL delete --calendar 个人 --title "组会" --from -1 --to 30 --yes    # actually deletes
```

`--from` / `--to` are **day offsets from today** (`-14` = two weeks ago, `+30` = a month ahead);
the script turns them into dates, you never build date strings. Reading is always safe; `add` and
`delete` change the user's data — show the user what you are about to write and confirm.

## The user's calendars

| Calendar | What it is |
|---|---|
| `个人` | personal |
| `家庭` | family / travel |
| `业务` | lab & work items (this is where 大组会, measurement tasks, design tasks live) |
| `计划的提醒事项` | Reminders-backed — **noise**, excluded by default |
| `中国大陆节假日` | holidays, thousands of entries — **noise** |
| `Siri建议` | Siri suggestions — **noise** |

Default `events`/`today`/`week` exclude the three noise calendars. Plan from `个人` + `家庭` +
`业务`; only reach for `--include-noise` when the question is about holidays.

## Answering a scheduling question

1. Run the read command for the right window (`today`, `week`, or an explicit `--from/--to`).
   Widen the window rather than guessing: `--from -14 --to 60` is cheap.
2. Report events with calendar name + start + end + title, and flag all-day items.
3. Point out **conflicts and free slots** explicitly — that is what the user actually wants from
   this profile ("this and that overlap", "you are free 10:00–13:30").
4. Never invent an event to fill a gap; if a window is empty, say it is empty.

## Permissions / failure modes

- macOS grants Calendar access to the **process that runs osascript** — here the Hermes gateway
  python process. It was granted on 2026-10-05 and reading works; the first call from a *new*
  parent process can raise a GUI prompt the user must approve.
- If osascript returns `Not authorized to send Apple events` / `不允许发送 Apple 事件`:
  System Settings → Privacy & Security → **Automation** → enable Calendar for the Hermes/python
  entry (and check **Calendars** under Privacy & Security while there). Do not retry in a loop —
  each retry re-triggers the prompt.
- **Do not** try `sqlite3 ~/Library/Calendars/...` or read the calendar store directly: this
  machine's Hermes process has no Full Disk Access, `~/Library/Calendars/` is
  `Operation not permitted`, and the store is not a supported interface. AppleScript is the path.
- Calendar.app is launched on demand by AppleScript (it becomes visible in the Dock). That is
  expected, not a bug.

## AppleScript pitfalls this script already handles (keep them handled)

These cost real debugging time; if you ever rewrite the embedded scripts, preserve the fixes:

1. **`set its hours to H` silently corrupts the date.** Outside a `tell` block `it` is the *script
   object*, so `its hours` / `its minutes` set properties on the script — and `its minutes` then
   shadows the `minutes` unit constant, making `d + 30 * minutes` a no-op. Always write
   `set hours of dStart to H`, `set minutes of dStart to M`, `set seconds of dStart to 0`.
2. **`months` is not usable as a unit in this AppleScript version** (`can't make "every month of
   «script»" into a number`). Do date arithmetic in **days only** — Python computes the day offset
   from today, AppleScript does `d + (offset * days)`.
3. **`name of calendar of e` on an event reference raises -1700.** Pass the calendar name you
   already know instead of querying it back off the event.
4. **Dates come back as localized strings** (`2026年10月6日 星期二 14:30:00`), not ISO. Compare and
   parse accordingly; never `datetime.strptime` them as ISO.
5. **`whose start date ≥ X` is the fast filter**; iterating `every event of every calendar`
   unfiltered takes minutes because of the holiday calendar.

## User conventions already observed (2026-10)

- Lab bookings live in `业务` and are titled like `TEM`, `✅ 8. EcBfr_Mirror电镜`, `✅ 10. γPFD 纯化`;
  TEM slots on record are **Tuesdays 10:00–11:00 (1 h)**.
- Machine time (TEM etc.) is booked **by phone, callable from 09:00**; the reminder event for that is
  written to `业务` as `📞 打电话约 …（<sample> / <lab room>）`, 09:00 for 30 min, room in `--location`,
  what to book in `--notes`.
- Long-holiday phrasing: `国庆后` = the **first working day after the holiday**, computed from the
  State Council notice — never guessed. (`中国大陆节假日` on this Mac can be empty; if so, look the
  year's 放假安排 up on gov.cn.) 2026 国庆 = 10/1–10/7, so 节后首日 = 10/8 (Thu), 10/10 (Sat) 补班.

## Reporting

Give the user a plain-language schedule, not AppleScript output: what's coming, where the clashes
are, what's free. Keep the raw event dumps for when they ask to see the data.
