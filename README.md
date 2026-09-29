# Daily Journal MVP

A lightweight, fullscreen daily journal for Linux and Raspberry Pi. The app uses
only Python 3's standard library: **Tkinter** for the interface and **SQLite** for
storage. It is designed for keyboard use on a 3.5-inch display under DietPi/XFCE.

## Run

On Debian, Raspberry Pi OS, or DietPi, install Python's Tk package once:

```sh
sudo apt install python3-tk
```

Then start the journal from this directory:

```sh
python3 main.py
```

The app opens fullscreen by default. `F11` toggles fullscreen and `Escape`
leaves it. The window can still be resized for desktop development.

Entries are stored at `~/.local/share/terminal-journal/journal.db`, or beneath
`$XDG_DATA_HOME/terminal-journal/` when that variable is set. This is the same
SQLite database and one-entry-per-date schema used by v0.1. Preferences are
kept beside it in `settings.json`.

## Using the journal

- Press `Ctrl+Left` / `Ctrl+Right` to change day and `Ctrl+Up` / `Ctrl+Down`
  to move by one week.
- Press `Alt+Left` / `Alt+Right` to move to the same date in the previous or
  next month, or `Ctrl+T` to return to today.
- Press `Ctrl+S` to save immediately. Changes also save automatically after a
  short pause and whenever you change dates or close the app.
- Press `F9` to collapse or restore the calendar sidebar.
- Press `F7` to enter the Block types navigator, use Up/Down to move, and press
  Enter to display the selected type. Escape returns to the daily entry.
- Press `F6` to cycle through light, dark, and sepia themes.
- Press `F11` to toggle fullscreen and `Ctrl+Q` to save and close the app.
- Select text and use `Ctrl+B`, `Ctrl+I`, or `Ctrl+H` for bold, italic, or
  highlight. `Ctrl+L` toggles bullets on the selected lines.
- Use the arrow keys, Page Up, and Page Down to move and scroll in the editor.

All app controls are keyboard-driven. The calendar is an informational sidebar:
days containing entries have a dot, the whole weekday header row is shaded, and
only the currently open date number is highlighted.
The text editor intentionally has no visible scrollbar; normal Tkinter keyboard
scrolling remains available.

Formatting is stored as readable plain text (`**bold**`, `*italic*`,
`***bold italic***`, `==highlight==`, and `- ` list items), but the wrappers are
hidden while editing and the content is rendered with its actual formatting.
Pressing a formatting shortcut again removes that format. This avoids a schema
change or proprietary rich-text format.

## Block types

Put a slash command on its own line to start a journal block:

```text
/memory
/reflection
/gratitude
/todo
/idea
```

Typing `/` opens a small autocomplete list; use Up/Down and Tab or Enter to
accept a registered command. Block types are dynamic: typing a new valid type,
such as `/news`, on its own line creates the block immediately. After
save/autosave, that type is registered in SQLite, appears in the Block types
explorer below the calendar, and is offered by future autocomplete sessions.
Names may contain letters, numbers, underscores, and hyphens, but must begin
with a letter.

Select a block type with the mouse, or press F7 and use Up/Down followed by
Enter. The selected type uses the same highlight style as the current calendar
date. The editor then shows a read-only, newest-first list of every block of that
type across all dates. Press Escape or navigate to another date to return to the
daily entry. Hashtags such as `#outdoors` have no special meaning.

`categories.py` dynamically parses blocks into a stable intermediate
representation, ready for a later migration to structured `blocks` tables.

## Project structure

- `main.py`: opens SQLite and starts Tkinter.
- `ui.py`: Tkinter layout, themes, calendar controls, formatting, and keys.
- `db.py`: parameterized database creation, loading, saving, and date marks.
- `calendar.py`: Monday-first month grids and date math.
- `categories.py`: UI-independent dynamic slash-block parsing.
- `settings.py`: small JSON preference store.
- `editor.py`: retained pure text-editor core from v0.1.

The `entries` table keeps `id`, `date`, `content`, `favorite`, `created_at`, and
`updated_at`. Editing an entry preserves its id, creation time, and favorite
value. The small `block_types` registry stores autocomplete/explorer names; the
entry content and one-entry-per-date model remain unchanged.

## Checks

Run the standard-library tests with:

```sh
python3 -m unittest discover -s tests
```

Because the interface needs a graphical display, launch it from an XFCE session
on the Pi for the final screen and keyboard check. The application itself does
not require network access.
