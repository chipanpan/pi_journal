"""Start the lightweight Tkinter daily journal."""

import tkinter as tk
from contextlib import closing

import db
import ui


def main():
    try:
        with closing(db.open_database()) as connection:
            ui.run(connection)
    except tk.TclError as error:
        raise SystemExit(
            "Could not start the graphical journal. Run it inside an XFCE desktop "
            "session with Tkinter installed (on Debian/DietPi: python3-tk).\n{}".format(error)
        )


if __name__ == "__main__":
    main()
