# Project notes for coding agents

- Keep v0.1 compatible with Python 3 and the standard library only.
- Preserve the small file split: database queries in `db.py`, curses drawing and keys in `ui.py`, text editing in `editor.py`, and date math in `calendar.py`.
- Keep all database queries parameterized. Preserve the one-entry-per-date constraint and existing timestamps/favorite values when editing content.
- Keep the UI usable by keyboard in a basic SSH terminal. Avoid mouse support, colors as the only indicator, and terminal-specific shortcuts.
- Run `python3 -m unittest discover -s tests` after changing core logic. Try the curses UI manually on Linux when possible.
