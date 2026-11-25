import os
import sqlite3
import tempfile
import unittest

from library_website.db import is_culled_book, read_db_to_list


class DbTests(unittest.TestCase):
    def test_is_culled_book_matches_supported_notes(self) -> None:
        self.assertTrue(is_culled_book("Culled 2026-07-13"))
        self.assertTrue(is_culled_book("Utgallrad 2026-07-13"))
        self.assertFalse(is_culled_book("Culled someday"))
        self.assertFalse(is_culled_book(None))

    def test_read_db_to_list_excludes_culled_books(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "library.sqlite")
            with sqlite3.connect(db_path) as connection:
                cursor = connection.cursor()
                cursor.execute("CREATE TABLE library (Title TEXT, Notes TEXT)")
                cursor.execute(
                    "INSERT INTO library (Title, Notes) VALUES (?, ?)",
                    ("Kept", None),
                )
                cursor.execute(
                    "INSERT INTO library (Title, Notes) VALUES (?, ?)",
                    ("Removed", "Culled 2026-07-13"),
                )

            field_names, books = read_db_to_list(db_path)

        self.assertEqual(field_names, ["Title", "Notes"])
        self.assertEqual(books, [{"Title": "Kept"}])


if __name__ == "__main__":
    unittest.main()
