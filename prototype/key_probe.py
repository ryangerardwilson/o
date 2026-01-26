#!/usr/bin/env python3
"""Interactive helper to capture raw key codes for Enter vs Ctrl+J.

Run inside different terminal environments (plain shell, tmux, etc.) to see
what integer codes are produced for Return and Ctrl+J. Results are printed when
the session ends so they can be copied into documentation.
"""

from __future__ import annotations

import curses
from typing import List


def _format_entry(key: int) -> str:
    try:
        key_name = curses.keyname(key).decode("ascii", "ignore")
    except Exception:
        key_name = "?"

    if 32 <= key <= 126:
        glyph = chr(key)
    elif key == 10:
        glyph = "\\n"
    elif key == 13:
        glyph = "\\r"
    else:
        glyph = ""

    hex_code = f"0x{key & 0xFFFF:04x}"
    glyph_part = f" '{glyph}'" if glyph else ""
    return f"{key:>5} | {hex_code} | {key_name}{glyph_part}"


def _capture(stdscr) -> List[str]:
    entries: List[str] = []

    try:
        curses.curs_set(0)
    except curses.error:
        pass

    for fn in (curses.noecho, curses.raw, curses.nonl):
        try:
            fn()
        except curses.error:
            pass

    try:
        stdscr.keypad(True)
    except curses.error:
        pass

    header = "Ctrl+J key probe — press Enter, Ctrl+J, then ESC to quit"

    while True:
        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()
        try:
            stdscr.addstr(0, 0, header[:max_x])
            stdscr.addstr(
                1,
                0,
                "Entries show: decimal | hex | curses name (printable glyph)",
            )
        except curses.error:
            pass

        start_row = 3
        available_rows = max(0, max_y - start_row - 1)
        visible = entries[-available_rows:] if available_rows else entries

        for idx, line in enumerate(visible):
            row = start_row + idx
            if row >= max_y - 1:
                break
            try:
                stdscr.addstr(row, 0, line[:max_x])
            except curses.error:
                pass

        stdscr.refresh()
        key = stdscr.getch()

        if key == 27:  # ESC exits the probe
            entries.append(_format_entry(key))
            break

        entries.append(_format_entry(key))

    return entries


def main() -> None:
    entries: List[str] = []

    def _run(stdscr):
        entries.extend(_capture(stdscr))

    curses.wrapper(_run)

    print("Captured key codes (most recent last):")
    for line in entries:
        print(line)


if __name__ == "__main__":
    main()
