import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

import calendar as journal_calendar
import db
from editor import Editor


class DatabaseTests(unittest.TestCase):
    def test_save_load_and_marks(self):
        with tempfile.TemporaryDirectory() as directory:
            with closing(db.open_database(Path(directory) / "journal.db")) as connection:
                day = date(2026, 9, 19)
                self.assertIsNone(db.get_entry(connection, day))
                db.save_entry(connection, day, "first")
                first = db.get_entry(connection, day)
                connection.execute("UPDATE entries SET favorite = 1 WHERE date = ?", (day.isoformat(),))
                connection.commit()
                db.save_entry(connection, day, "revised")
                revised = db.get_entry(connection, day)
                self.assertEqual(revised["content"], "revised")
                self.assertEqual(revised["id"], first["id"])
                self.assertEqual(revised["favorite"], 1)
                self.assertEqual(revised["created_at"], first["created_at"])
                self.assertEqual(db.entry_days(connection, 2026, 9), {19})
                db.save_entry(connection, day, "")
                self.assertEqual(db.entry_days(connection, 2026, 9), set())


class EditorTests(unittest.TestCase):
    def test_edit_and_wrap(self):
        editor = Editor("ab\ncd")
        editor.handle("home")
        editor.handle("backspace")
        self.assertEqual(editor.content, "abcd")
        editor.handle("insert", "!")
        self.assertEqual(editor.content, "ab!cd")
        rows, cursor = editor.visual_rows(3)
        self.assertEqual(rows, ["ab!", "cd"])
        self.assertEqual(cursor, (1, 0))

    def test_wrap_prefers_whole_words_and_hyphens(self):
        editor = Editor("one two-three four")
        rows, cursor = editor.visual_rows(7)
        self.assertEqual(rows, ["one ", "two-", "three ", "four"])
        self.assertEqual(cursor, (3, 4))

        editor = Editor("a abc-def")
        rows, cursor = editor.visual_rows(7)
        self.assertEqual(rows, ["a abc-", "def"])
        self.assertEqual(cursor, (1, 3))

    def test_wrap_splits_only_words_wider_than_pane(self):
        editor = Editor("abcdefgh")
        rows, cursor = editor.visual_rows(5)
        self.assertEqual(rows, ["abcde", "fgh"])
        self.assertEqual(cursor, (1, 3))


class CalendarTests(unittest.TestCase):
    def test_month_edges(self):
        weeks = journal_calendar.month_grid(2026, 9)
        self.assertEqual(weeks[0][1], date(2026, 9, 1))
        self.assertEqual(journal_calendar.change_month(date(2026, 1, 31), 1), date(2026, 2, 28))


if __name__ == "__main__":
    unittest.main()
