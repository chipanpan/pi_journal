import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

import calendar as journal_calendar
import categories
import db
import editor
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
                self.assertFalse(db.toggle_favorite(connection, day))
                unfavorited = db.get_entry(connection, day)
                self.assertEqual(unfavorited["content"], "revised")
                self.assertEqual(unfavorited["created_at"], first["created_at"])
                self.assertEqual(db.month_markers(connection, 2026, 9), {19: False})
                self.assertTrue(db.toggle_favorite(connection, day))
                self.assertEqual(db.month_markers(connection, 2026, 9), {19: True})
                self.assertFalse(db.toggle_favorite(connection, day))
                db.save_entry(connection, day, "")
                self.assertEqual(db.entry_days(connection, 2026, 9), set())

                empty_favorite = date(2026, 9, 17)
                self.assertTrue(db.toggle_favorite(connection, empty_favorite))
                self.assertEqual(db.month_markers(connection, 2026, 9), {17: True})

                db.save_entry(connection, date(2026, 9, 18), "older")
                db.save_entry(connection, day, "newer")
                self.assertEqual(
                    [row["date"] for row in db.all_entries(connection)],
                    ["2026-09-19", "2026-09-18"],
                )
                self.assertEqual(db.block_types(connection)[:5], categories.DEFAULT_BLOCK_TYPES)
                db.save_entry(connection, day, "/News\nA custom block")
                self.assertIn("news", db.block_types(connection))


class EditorTests(unittest.TestCase):
    def test_plain_text_formatting(self):
        self.assertEqual(editor.formatted_text("word", "bold"), "**word**")
        self.assertTrue(editor.has_format_markers("***", "***", "bold"))
        self.assertTrue(editor.has_format_markers("***", "***", "italic"))
        self.assertFalse(editor.has_format_markers("**", "**", "italic"))
        self.assertFalse(editor.has_format_markers("*", "*", "bold"))
        self.assertEqual(editor.toggle_bullet_lines([""]), ["- "])
        self.assertEqual(editor.toggle_bullet_lines(["one", "two"]), ["- one", "- two"])
        self.assertEqual(editor.toggle_bullet_lines(["- one", "- two"]), ["one", "two"])

    def test_bold_markers_are_not_misread_as_italic(self):
        matches = {
            name: [match.span(1) for match in pattern.finditer("**word**")]
            for name, pattern, _marker_size in editor.INLINE_PATTERNS
        }
        self.assertEqual(matches["bold"], [(2, 6)])
        self.assertEqual(matches["italic"], [])

        combined = {
            name: [match.span(1) for match in pattern.finditer("***word***")]
            for name, pattern, _marker_size in editor.INLINE_PATTERNS
        }
        self.assertEqual(combined["bold_italic"], [(3, 7)])
        self.assertEqual(combined["bold"], [])
        self.assertEqual(combined["italic"], [])

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


class CategoryTests(unittest.TestCase):
    def test_parses_dynamic_blocks_for_future_migration(self):
        text = "A preface\n/memory\nRead on the train\n/news\nHeadlines\n/todo\nPack"
        blocks = categories.parse_blocks(text)
        self.assertEqual(
            [block.category for block in blocks], [None, "memory", "news", "todo"]
        )
        self.assertEqual(blocks[1].content, "Read on the train")
        self.assertEqual(blocks[2].content, "Headlines")
        self.assertEqual(categories.block_types_in_text(text), ("memory", "news", "todo"))
        self.assertEqual(categories.block_types_in_text("/ne"), ())
        self.assertEqual(categories.block_types_in_text("/news\n"), ("news",))

    def test_any_valid_command_line_splits_blocks(self):
        blocks = categories.parse_blocks("/memory lane\n/unknown\n/idea\nTry it")
        self.assertEqual(len(blocks), 3)
        self.assertIsNone(blocks[0].category)
        self.assertEqual(blocks[1].category, "unknown")
        self.assertEqual(blocks[2].category, "idea")
        self.assertEqual(
            categories.matching_commands("/n", ("memory", "news")), ("/news",)
        )
        self.assertEqual(categories.matching_commands("memory"), ())

    def test_autocomplete_token_is_anchored_to_the_cursor(self):
        self.assertEqual(categories.autocomplete_token("/grat"), ("/grat", 0))
        self.assertEqual(categories.autocomplete_token("  /grat"), ("/grat", 2))
        self.assertIsNone(categories.autocomplete_token("note /grat"))
        self.assertIsNone(categories.autocomplete_token("note/grat"))
        self.assertIsNone(categories.autocomplete_token("/grat", "itude"))

    def test_entries_are_filtered_by_block_type(self):
        entries = (
            ("2026-09-20", "/memory\nTrain ride\n/news\nDaily headlines"),
            ("2026-09-19", "/news\nWeekly headlines\n/idea\nRead more"),
        )
        matches = categories.blocks_for_type(entries, "/news")
        self.assertEqual([entry_date for entry_date, _block in matches], [
            "2026-09-20", "2026-09-19"
        ])
        self.assertEqual(matches[0][1].category, "news")
        self.assertEqual(matches[0][1].content, "Daily headlines")


if __name__ == "__main__":
    unittest.main()
