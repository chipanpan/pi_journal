"""Start the journal in a Linux terminal."""

import curses
from contextlib import closing

import db
import ui


def main():
    with closing(db.open_database()) as connection:
        # wrapper restores the terminal even if the UI raises an exception.
        curses.wrapper(lambda screen: ui.run(screen, connection))


if __name__ == "__main__":
    main()
