import runpy
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from library_website.config import AppConfig

ISBN = "9789100104986"
FORMATTED_ISBN = "978-91-0-010498-6"


class AddBookTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.db = self.root / "Library.db"
        shutil.copyfile(
            Path(__file__).resolve().parents[1] / "Library.example.db", self.db
        )
        settings = AppConfig(
            library_name="Test Library",
            library_path=directory.name,
            library_database_path=str(self.db),
            marc_path=directory.name,
            host_ip="127.0.0.1",
            host_port=5149,
            debug_mode=True,
            ssl_cert=None,
            ssl_key=None,
        )
        with (
            patch("library_website.config.load_app_config", return_value=settings),
            patch("locale.setlocale"),
        ):
            app = runpy.run_module("library_web")["app"]
        app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = app.test_client()

    def submit(self, **fields):
        response = self.client.post(
            "/add_book",
            data=fields,
            base_url="https://localhost",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def cache_record(self, libris_id, isbn=None):
        isbn_field = (
            '<datafield tag="020" ind1=" " ind2=" ">'
            f'<subfield code="a">{isbn}</subfield></datafield>'
            if isbn
            else ""
        )
        (self.root / f"{libris_id}.xml").write_text(
            '<collection xmlns="http://www.loc.gov/MARC21/slim"><record>'
            "<leader>00000nam a2200000 a 4500</leader>"
            '<datafield tag="245" ind1="1" ind2="0">'
            '<subfield code="a">Test book</subfield></datafield>'
            + isbn_field
            + "</record></collection>",
            encoding="utf-8",
        )

    @patch("library_website.libris.requests.get")
    @patch("builtins.print")
    def test_isbn_form_uses_normalized_input_and_resolved_id(self, console, get):
        get.return_value = Mock(
            text='{"xsearch":{"records":1,"list":[{"identifier":"/one"}]}}'
        )
        self.cache_record("one")
        self.assertIn("added to database", self.submit(tbx_isbn=FORMATTED_ISBN))
        console.assert_any_call("Dupe status 1 (ISBN): False")
        self.assertIn(ISBN, get.call_args.args[0])
        get.reset_mock()
        console.reset_mock()
        self.assertIn("already in DB", self.submit(tbx_isbn="91-0-010498-1"))
        console.assert_any_call("Dupe status 1 (ISBN): True")
        get.assert_not_called()

        with sqlite3.connect(self.db) as connection:
            self.assertEqual(
                connection.execute("SELECT ISBN FROM library").fetchall(), [(ISBN,)]
            )
            connection.execute("UPDATE library SET ISBN = NULL")
        self.assertIn("already in DB", self.submit(tbx_isbn=ISBN))
        get.assert_called_once()
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM library").fetchone()[0], 1
            )

    @patch("library_website.libris.requests.get")
    def test_libris_form_checks_marc_isbn_and_allows_replacing_culled_book(self, get):
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "INSERT INTO library (ISBN, IDLibris) VALUES (?, ?)",
                ("91-0-010498-1", "old"),
            )
        self.cache_record("new", ISBN)
        self.assertIn("already in DB", self.submit(tbx_librisid="new"))
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE library SET Notes = 'Culled 2026-01-01'")
        self.assertIn("added to database", self.submit(tbx_librisid="new"))
        self.assertIn("already in DB", self.submit(tbx_librisid="new"))
        with sqlite3.connect(self.db) as connection:
            self.assertCountEqual(
                connection.execute("SELECT IDLibris FROM library"), [("old",), ("new",)]
            )
        get.assert_not_called()
