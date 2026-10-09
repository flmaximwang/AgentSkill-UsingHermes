#!/usr/bin/env python3
"""Drive an interactive terminal program in a pty and capture what it really draws.

Examples
--------
  # basic edit/save/quit cycle, screens after every step
  python3 pty_capture.py --prog /usr/bin/pico --file /tmp/demo.txt \
      --keys 'startup=' 'type=hello world\r' 'write=^O' 'confirm=\r' 'quit=^X'

  # jump-to-line check, reconstruct the screen grid instead of a text dump
  python3 pty_capture.py --prog /usr/bin/pico --extra +3 --file /tmp/five.txt \
      --text 'a\nb\nc\nd\ne\n' --keys 'pos=^C' --grid

Key data syntax
---------------
  ^O        control char (any ^<letter>, ^? = DEL)
  \r \n \t  escapes; NOTE \n is 0x0A = Ctrl-J, use \r for Enter
  label=    empty data just captures the current screen
"""

import argparse
import codecs
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time

CSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
GOTO = re.compile(r"\x1b\[(\d+);(\d+)H")


def decode_keys(data):
    """Translate ^X notation and backslash escapes into raw bytes."""
    out = []
    i = 0
    while i < len(data):
        ch = data[i]
        if ch == "^" and i + 1 < len(data):
            nxt = data[i + 1]
            out.append(chr(0x7F) if nxt == "?" else chr(ord(nxt.upper()) - 64))
            i += 2
            continue
        if ch == "\\" and i + 1 < len(data):
            out.append(codecs.decode(data[i:i + 2], "unicode_escape"))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out).encode("latin-1")


def strip_escapes(text):
    lines = text.replace("\r", "\n").split("\n")
    return "\n".join(l for l in (CSI.sub("", x).strip() for x in lines) if l)


def screen_grid(text, rows, cols):
    """Rebuild the drawn screen from ESC[row;colH addressing."""
    grid, row, col, i = {}, 1, 1, 0
    while i < len(text):
        got = GOTO.match(text, i)
        if got:
            row, col = int(got.group(1)), int(got.group(2))
            i = got.end()
            continue
        if text[i] == "\x1b":
            m = CSI.match(text, i)
            i = m.end() if m else i + 1
            continue
        ch = text[i]
        if ch == "\r":
            col = 1
        elif ch == "\n":
            row, col = row + 1, 1
        elif ch >= " ":
            grid[(row, col)] = ch
            col += 1
        i += 1
    out = []
    for r in range(1, rows + 1):
        line = "".join(grid.get((r, c), " ") for c in range(1, cols + 1)).rstrip()
        out.append("%2d|%s|" % (r, line))
    return "\n".join(out)


def read_pty(fd, seconds):
    buf, end = b"", time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                buf += os.read(fd, 65536)
            except OSError:
                break
    return buf.decode("latin-1")


def show(label, data, rows, cols, use_grid):
    print("--- %s ---" % (label or "(screen)"))
    print(screen_grid(data, rows, cols) if use_grid else strip_escapes(data))
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prog", required=True, help="absolute path of the interactive program")
    ap.add_argument("--file", help="file the program edits; its content is repr()d at the end")
    ap.add_argument("--text", default="", help="initial content for --file (default: empty)")
    ap.add_argument("--extra", nargs="*", default=[], help="program arguments placed before --file")
    ap.add_argument("--winsize", default="80x24", help="COLSxROWS for the pty (default: %(default)s)")
    ap.add_argument("--keys", nargs="*", default=[], help="LABEL=DATA steps, replayed in order")
    ap.add_argument("--wait", type=float, default=0.5, help="seconds to drain after each step (default: %(default)s)")
    ap.add_argument("--timeout", type=int, default=60, help="hard wall-clock guard in seconds (default: %(default)s)")
    ap.add_argument("--grid", action="store_true", help="reconstruct the screen grid from cursor addressing")
    args = ap.parse_args()

    cols, rows = (int(v) for v in args.winsize.lower().split("x"))
    if args.file:
        with open(args.file, "w") as fh:
            fh.write(args.text)

    signal.alarm(args.timeout)
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.setdefault("TERM", "xterm")
        try:
            fcntl.ioctl(1, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass
        argv = [os.path.basename(args.prog)] + list(args.extra)
        if args.file:
            argv.append(args.file)
        os.execv(args.prog, argv)

    time.sleep(0.4)
    show("startup", read_pty(fd, args.wait), rows, cols, args.grid)

    for step in args.keys:
        label, _, data = step.partition("=")
        if data:
            os.write(fd, decode_keys(data))
        time.sleep(0.35)
        show(label, read_pty(fd, args.wait), rows, cols, args.grid)

    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

    if args.file:
        with open(args.file) as fh:
            print(">>> file now: %r" % fh.read())


if __name__ == "__main__":
    main()
