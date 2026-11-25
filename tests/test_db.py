import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from library_website.db import add_book_to_db, is_culled_book, read_db_to_list


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

    def test_concurrent_imports_check_identifiers_inside_the_write_transaction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "library.sqlite")
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    "CREATE TABLE library "
                    "(Title TEXT, ISBN TEXT, IDLibris TEXT, Notes TEXT)"
                )
            start = Barrier(2)

            def insert(book):
                start.wait(timeout=5)
                return add_book_to_db(db_path, book)

            books = [
                {"Title": "First", "ISBN": "91-0-010498-1", "IDLibris": "one"},
                {"Title": "Second", "ISBN": "9789100104986", "IDLibris": "two"},
            ]
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(pool.map(insert, books), [True, False])
            self.assertEqual(len(read_db_to_list(db_path)[1]), 1)


if __name__ == "__main__":
    unittest.main()
