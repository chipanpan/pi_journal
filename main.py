"""Start the journal in a Linux terminal."""

import curses
import sys
from contextlib import closing

import db
import ui


def main():
    try:
        with closing(db.open_database()) as connection:
            # wrapper restores the terminal even if the UI raises an exception.
            curses.wrapper(lambda screen: ui.run(screen, connection))
    finally:
        # Leave the small display clean instead of exposing the previous shell.
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
