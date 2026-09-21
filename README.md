# Terminal Journal v0.1

## To-do
[] Switch language: EN, FR, VN
[] Change illustration switch 

A small, keyboard-only daily journal for Linux and Raspberry Pi terminals. It uses only Python 3's standard library: `curses` for the screen and `sqlite3` for storage. It also works in an SSH terminal.

## Run

Install Python 3 with curses support (included in most Linux distributions), then from this directory run:

```sh
python3 main.py
```

Use a terminal at least 38 columns wide and 14 rows tall for every screen. The journal view is optimized for a roughly 40-by-13-cell LCD: art and compact navigation hints occupy the left rail while the entry uses the full height on the right. Set a UTF-8 locale if you want to type non-ASCII characters. No packages or virtual environment are needed.

Entries are stored at `~/.local/share/terminal-journal/journal.db`, or under `$XDG_DATA_HOME/terminal-journal/journal.db` when that variable is set. The directory and database are created on first run. Back up that file to keep your journal safe.

## Keys

| Screen | Keys |
| --- | --- |
| Journal | Left/Right: previous/next day; E: edit; C: calendar; J/K or Up/Down: scroll; Q: quit |
| Editor | Type to insert; arrows, Home, End, Backspace, Delete, Enter to edit; F2: save; Esc: save and return |
| Calendar | Arrows: move one day or week; `[` / `]`: previous/next month; Enter: open date; Esc: cancel; Q: quit |

The calendar marks dates containing text with `*`. An empty entry does not receive a mark. The currently selected date is highlighted. `Q` is a normal text character while editing; press Esc, then Q to quit.

## Files

- `main.py`: opens SQLite and starts the curses screen.
- `db.py`: creates the table, loads and saves entries, and finds marked dates.
- `ui.py`: draws the journal and calendar, and handles navigation keys.
- `editor.py`: keeps text and cursor state, independent of curses.
- `calendar.py`: builds the month grid and handles month changes.
- `ascii/`: the small illustration shown above each entry.

The database keeps one row per date, with `id`, `date`, `content`, `favorite`, `created_at`, and `updated_at`. The `favorite` field is reserved for a later version.

## Checks

Run the standard-library tests with:

```sh
python3 -m unittest discover -s tests
```

The terminal UI should be tried in a Linux terminal or over SSH; Windows Python does not provide the Unix `curses` module.

## Windows and Raspberry Pi workflow

Keep the **code** in a private GitHub repository. On your Windows PC, commit and push code changes. Clone the repository once on the Pi, then run `git pull --ff-only` on the Pi whenever you want to update the app. Git commands need a network connection; the journal itself does not.

The journal database lives outside this repository, in the Pi user's home directory. It is deliberately excluded by `.gitignore` if copied into the project. Do not commit personal entries. Back up the database separately, for example to a USB drive you control.

For a new GitHub repository, create an **empty** private repository there first (without a README or license), then run these commands in this project directory after it has been initialized locally:

```sh
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

On the Pi, while online:

```sh
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git ~/terminal-journal
cd ~/terminal-journal
python3 -m unittest discover -s tests
python3 main.py
```

Later updates on the Pi take `git pull --ff-only` from inside `~/terminal-journal`. If you edit code on the Pi, commit and push those changes when online, then pull them on Windows before editing there again.
