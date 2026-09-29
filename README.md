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

- Click a calendar date, or press `Ctrl+Left` / `Ctrl+Right`, to change day.
- Press `Ctrl+S` to save immediately. Changes also save automatically after a
  short pause and whenever you change dates or close the app.
- Press `F9` or use the menu button to collapse the calendar sidebar.
- Use `Alt+Left` / `Alt+Right` to change the displayed calendar month.
- Choose light, dark, or sepia from the theme selector.
- Select text and use `Ctrl+B`, `Ctrl+I`, or `Ctrl+H` for bold, italic, or
  highlight. `Ctrl+L` toggles bullets on the selected lines.
- Choose a PNG illustration from the sidebar. It stays in the editor's
  lower-right corner and the choice is remembered.

Formatting is stored as readable plain text (`**bold**`, `*italic*`,
`==highlight==`, and `- ` list items), so no schema change or proprietary rich
text format is needed.

## Categories and tags

Put a recognized command on its own line to start a journal block:

```text
/memory
/reflection
/gratitude
/todo
/idea
```

Typing `/` opens a small autocomplete list; use Up/Down and Tab or Enter to
accept a command. Subject tags such as `#career`, `#travel`, and `#books` remain
part of the text. `categories.py` dynamically parses blocks and tags into a
stable intermediate representation, ready for a later migration to `blocks`,
`tags`, and `block_tags` tables.

## Project structure

- `main.py`: opens SQLite and starts Tkinter.
- `ui.py`: Tkinter layout, themes, calendar controls, formatting, and keys.
- `db.py`: parameterized database creation, loading, saving, and date marks.
- `calendar.py`: Monday-first month grids and date math.
- `categories.py`: UI-independent slash-block and subject-tag parsing.
- `settings.py`: small JSON preference store.
- `editor.py`: retained pure text-editor core from v0.1.

The `entries` table keeps `id`, `date`, `content`, `favorite`, `created_at`, and
`updated_at`. Editing an entry preserves its id, creation time, and favorite
value.

## Checks

Run the standard-library tests with:

```sh
python3 -m unittest discover -s tests
```

Because the interface needs a graphical display, launch it from an XFCE session
on the Pi for the final screen and keyboard check. The application itself does
not require network access.
