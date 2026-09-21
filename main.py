"""Start the journal in a Linux terminal."""

import curses
import sys
import termios
from contextlib import closing

import db
import ui


def main():
    terminal_settings = None
    try:
        if sys.stdin.isatty():
            terminal_settings = termios.tcgetattr(sys.stdin.fileno())
            app_settings = terminal_settings.copy()
            # Let curses receive Ctrl-S instead of pausing terminal output.
            app_settings[0] &= ~termios.IXON
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, app_settings)
        with closing(db.open_database()) as connection:
            # wrapper restores the terminal even if the UI raises an exception.
            curses.wrapper(lambda screen: ui.run(screen, connection))
    finally:
        if terminal_settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, terminal_settings)
        # Leave the small display clean instead of exposing the previous shell.
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
