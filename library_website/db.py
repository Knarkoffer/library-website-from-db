import re
import sqlite3
import time
from contextlib import closing
from typing import Any

import isbnlib

CULLED_NOTES_PATTERN = re.compile(
    r"(Utgallrad|Culled) [0-9]{4}-[0-9]{2}-[0-9]{2}", re.IGNORECASE
)


def is_culled_book(notes: Any) -> bool:
    """Return True when a Notes value marks a book as culled."""
    return isinstance(notes, str) and bool(CULLED_NOTES_PATTERN.search(notes))


def read_db_to_list(database_path: str) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Read the library database into table headers and book dictionaries.

    Rows with a Notes value matching the culled-book marker are excluded from
    the returned book list. Empty database values are omitted from each book dict
    so templates can treat missing values consistently.
    """
    print("Reading database to list...")
    booklist = []

    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()
        cursor.execute("select * from library")
        field_names = [field[0] for field in cursor.description]

        for state in cursor.fetchall():
            dict_item = dict(zip(field_names, state, strict=True))
            dict_item = {
                key: value for key, value in dict_item.items() if value is not None
            }

            if not is_culled_book(dict_item.get("Notes")):
                booklist.append(dict_item)

    return field_names, booklist


def _book_exists(
    connection: sqlite3.Connection, libris_id: str | None, *isbns: str | None
) -> bool:
    """Match active records, including ISBNs stored in older display formats."""
    isbn_keys = {isbnlib.to_isbn13(isbn) for isbn in isbns if isbn}
    isbn_keys.discard("")
    connection.create_function("is_culled", 1, is_culled_book)
    connection.create_function(
        "matches_isbn", 1, lambda value: isbnlib.to_isbn13(str(value)) in isbn_keys
    )
    row = connection.execute(
        """
        SELECT 1 FROM library
        WHERE (IDLibris = ? OR (? AND matches_isbn(ISBN)))
          AND NOT is_culled(Notes)
        LIMIT 1
        """,
        (libris_id, bool(isbn_keys)),
    ).fetchone()
    return row is not None


def book_exists(
    database_path: str, *, isbn: str | None = None, libris_id: str | None = None
) -> bool:
    """Check a known identifier before making a Libris request."""
    with closing(sqlite3.connect(database_path)) as connection:
        return _book_exists(connection, libris_id, isbn)


def add_book_to_db(
    database_path: str, book_item: dict[str, Any], *, submitted_isbn: str | None = None
) -> bool:
    """
    Insert one parsed book record and return False for an existing active book.

    The insert is retried when SQLite reports the database is locked, matching
    the existing workflow where the database may be open in another tool.
    """
    data_written = False

    while not data_written:
        try:
            with closing(sqlite3.connect(database_path)) as conn, conn:
                # Reserve the write before checking so competing imports serialize.
                conn.execute("BEGIN IMMEDIATE")
                if _book_exists(
                    conn,
                    book_item.get("IDLibris"),
                    book_item.get("ISBN"),
                    submitted_isbn,
                ):
                    return False
                cur = conn.cursor()

                columns = ", ".join(book_item.keys())
                placeholders = ":" + ", :".join(book_item.keys())
                query = f"INSERT INTO LIBRARY ({columns}) VALUES ({placeholders})"

                cur.execute(query, book_item)

            data_written = True
            print(f"{book_item['Title']} added to database")

        except sqlite3.OperationalError as error:
            input(f"Error: {str(error)}")
            print("DB was locked, no action taken. Sleeping 2 seconds")
            time.sleep(2)

    return data_written
