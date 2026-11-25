import unittest

from library_website.catalog import ddc_filter_type, filter_books_by_ddc, sortkeypicker


class CatalogTests(unittest.TestCase):
    def test_ddc_filter_type_handles_master_specific_and_invalid_values(self) -> None:
        self.assertEqual(ddc_filter_type("100"), "DDCMaster")
        self.assertEqual(ddc_filter_type("123"), "DDC")
        self.assertIsNone(ddc_filter_type("not-a-number"))
        self.assertIsNone(ddc_filter_type(None))

    def test_invalid_ddc_filter_returns_all_books(self) -> None:
        books = [{"Title": "One", "DDC": "123"}, {"Title": "Two", "DDC": "456"}]

        self.assertEqual(filter_books_by_ddc(books, "abc"), books)

    def test_ddc_filter_tolerates_missing_fields(self) -> None:
        books = [
            {"Title": "One", "DDC": "123", "Author": "B"},
            {"Title": "Two", "Author": "A"},
            {"Title": "Three", "DDC": "123.4"},
        ]

        filtered = filter_books_by_ddc(books, "123")

        self.assertEqual([book["Title"] for book in filtered], ["One", "Three"])

    def test_sortkeypicker_does_not_mutate_input_keys(self) -> None:
        keys = ["DDC", "Author"]
        sorter = sortkeypicker(keys)

        sorter({"DDC": "123", "Author": "A"})

        self.assertEqual(keys, ["DDC", "Author"])


if __name__ == "__main__":
    unittest.main()
