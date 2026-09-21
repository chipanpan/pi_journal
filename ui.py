"""Keyboard-only curses screens. All drawing and key handling live here."""

import curses
from datetime import date, timedelta
from pathlib import Path

import calendar as journal_calendar
import db
from editor import Editor


ART = (Path(__file__).parent / "ascii" / "cat.txt").read_text(encoding="utf-8").splitlines()
SIDE_WIDTH = 19
CALENDAR_WIDTH = 22


def put(screen, y, x, value, attributes=0):
    """Clip text so small SSH terminals do not raise curses.error."""
    height, width = screen.getmaxyx()
    if 0 <= y < height and 0 <= x < width - 1:
        try:
            screen.addnstr(y, x, value, width - x - 1, attributes)
        except curses.error:
            pass


def draw_entry(screen, day, editor, editing, scroll, message):
    screen.erase()
    height, width = screen.getmaxyx()
    if height < 12 or width < 38:
        put(screen, 0, 0, "Terminal too small (need 38x12)")
        screen.refresh()
        return scroll

    # A side rail gives the entry nearly the full screen height on short LCDs.
    for row, art_line in enumerate(ART[:7]):
        put(screen, row, 1, art_line)
    for row in range(height):
        put(screen, row, SIDE_WIDTH, "|")

    hint_row = min(8, height - 5)
    hints = (
        ("EDIT", "Esc save/close", "Ctrl-S save")
        if editing else
        ("VIEW", "</> change day", "E edit", "C calendar", "Q quit")
    )
    for offset, hint in enumerate(hints):
        put(screen, hint_row + offset, 1, hint, curses.A_DIM)

    text_left = SIDE_WIDTH + 2
    text_width = width - text_left - 1
    put(screen, 0, text_left, day.strftime("%a, %d %b %Y"), curses.A_BOLD)
    rows, cursor = editor.visual_rows(text_width)
    body_top, body_height = 2, height - 2
    if editing:
        scroll = max(0, min(scroll, cursor[0]))
        if cursor[0] >= scroll + body_height:
            scroll = cursor[0] - body_height + 1
    else:
        scroll = min(scroll, max(0, len(rows) - body_height))
    for offset, line in enumerate(rows[scroll:scroll + body_height]):
        put(screen, body_top + offset, text_left, line)
    if not editor.content and not editing:
        put(screen, body_top, text_left, "No entry. Press E.", curses.A_DIM)
    if message:
        put(screen, 1, text_left, message, curses.A_DIM)
    try:
        curses.curs_set(1 if editing else 0)
        if editing:
            screen.move(body_top + cursor[0] - scroll, text_left + cursor[1])
    except curses.error:
        pass
    screen.refresh()
    return scroll


def draw_calendar(screen, picked, entry_days, preview):
    screen.erase()
    height, width = screen.getmaxyx()
    if height < 12 or width < 38:
        put(screen, 0, 0, "Terminal too small (need 38x12)")
        screen.refresh()
        return

    for row in range(height):
        put(screen, row, CALENDAR_WIDTH, "|")

    put(screen, 0, 1, picked.strftime("%b %Y"), curses.A_BOLD)
    put(screen, 2, 1, "Mo Tu We Th Fr Sa Su")
    for week_number, week in enumerate(journal_calendar.month_grid(picked.year, picked.month)):
        for weekday, day in enumerate(week):
            if day is None:
                continue
            marker = "*" if day.day in entry_days else " "
            cell = f"{day.day:2d}{marker}"
            attr = curses.A_REVERSE if day == picked else 0
            put(screen, 3 + week_number, 1 + weekday * 3, cell, attr)
    put(screen, 9, 1, "* entry   Q quit", curses.A_DIM)
    put(screen, 10, 1, "Arrows move Esc back", curses.A_DIM)
    put(screen, 11, 1, "[ ] month Enter open", curses.A_DIM)

    text_left = CALENDAR_WIDTH + 2
    text_width = width - text_left - 1
    put(screen, 0, text_left, picked.strftime("%d %b %Y"), curses.A_BOLD)
    rows, _ = preview.visual_rows(text_width)
    for offset, line in enumerate(rows[:height - 2]):
        put(screen, 2 + offset, text_left, line)
    if not preview.content:
        put(screen, 2, text_left, "No entry.", curses.A_DIM)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.refresh()


def edit_action(key):
    """Translate curses keys into actions understood by the pure editor."""
    arrows = {
        curses.KEY_LEFT: "left", curses.KEY_RIGHT: "right",
        curses.KEY_UP: "up", curses.KEY_DOWN: "down",
        curses.KEY_HOME: "home", curses.KEY_END: "end",
        curses.KEY_DC: "delete", curses.KEY_BACKSPACE: "backspace",
    }
    if isinstance(key, int):
        return arrows.get(key), None
    if key in ("\n", "\r"):
        return "enter", None
    if key in ("\b", "\x7f"):
        return "backspace", None
    if key.isprintable():
        return "insert", key
    return None, None


def run(screen, connection):
    screen.keypad(True)
    day = date.today()
    entry = db.get_entry(connection, day)
    editor = Editor(entry["content"] if entry else "")
    mode, scroll, dirty, message = "view", 0, False, ""
    picked = day
    marked_days = set()

    while True:
        if mode == "calendar":
            preview_entry = db.get_entry(connection, picked)
            preview = Editor(preview_entry["content"] if preview_entry else "")
            draw_calendar(screen, picked, marked_days, preview)
        else:
            scroll = draw_entry(screen, day, editor, mode == "edit", scroll, message)
        try:
            key = screen.get_wch()
        except curses.error:
            continue

        if key == curses.KEY_RESIZE:
            continue
        if mode == "edit":
            if key in ("\x1b", "\x13", curses.KEY_F2):
                if dirty:
                    db.save_entry(connection, day, editor.content)
                    dirty = False
                message = "Saved"
                if key == "\x1b":
                    mode = "view"
                continue
            action, character = edit_action(key)
            if action:
                dirty |= editor.handle(action, character)
                message = "Unsaved" if dirty else ""
            continue

        if mode == "calendar":
            if key in ("q", "Q"):
                return
            if key == "\x1b":
                mode = "view"
                continue
            if key in ("\n", "\r", curses.KEY_ENTER):
                day = picked
                entry = db.get_entry(connection, day)
                editor = Editor(entry["content"] if entry else "")
                scroll, mode, message = 0, "view", ""
                continue
            if key == curses.KEY_LEFT:
                picked -= timedelta(days=1)
            elif key == curses.KEY_RIGHT:
                picked += timedelta(days=1)
            elif key == curses.KEY_UP:
                picked -= timedelta(days=7)
            elif key == curses.KEY_DOWN:
                picked += timedelta(days=7)
            elif key == "[":
                picked = journal_calendar.change_month(picked, -1)
            elif key == "]":
                picked = journal_calendar.change_month(picked, 1)
            marked_days = db.entry_days(connection, picked.year, picked.month)
            continue

        # View mode: writing starts only after E, so Q always quits here.
        if key in ("q", "Q"):
            return
        if key in ("e", "E"):
            mode, message = "edit", ""
        elif key in ("c", "C"):
            picked, mode = day, "calendar"
            marked_days = db.entry_days(connection, picked.year, picked.month)
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            day += timedelta(days=-1 if key == curses.KEY_LEFT else 1)
            entry = db.get_entry(connection, day)
            editor = Editor(entry["content"] if entry else "")
            scroll, message = 0, ""
        elif key in ("j", "J", curses.KEY_DOWN):
            scroll += 1
        elif key in ("k", "K", curses.KEY_UP):
            scroll = max(0, scroll - 1)
