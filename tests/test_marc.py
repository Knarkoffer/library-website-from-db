import unittest

from library_website.marc import extract_page_count, interpret_marc


class FakeField(dict):
    def __init__(self, display: str = "", **subfields: str) -> None:
        super().__init__(subfields)
        self.display = display

    def __str__(self) -> str:
        return self.display


class MarcTests(unittest.TestCase):
    def test_extract_page_count_supports_common_formats(self) -> None:
        self.assertEqual(extract_page_count({"300": {"a": "123 sidor"}}), 123)
        self.assertEqual(extract_page_count({"300": {"a": "123 pages"}}), 123)
        self.assertEqual(extract_page_count({"300": {"a": "[42] s."}}), 42)

    def test_extract_page_count_returns_zero_for_missing_or_unknown_values(
        self,
    ) -> None:
        self.assertEqual(extract_page_count({}), 0)
        self.assertEqual(extract_page_count({"300": {"a": "opaginerad"}}), 0)

    def test_interpret_marc_extracts_core_fields(self) -> None:
        marc_record = {
            "020": {"a": "9780306406157"},
            "245": FakeField("$aTitel : $bundertitel / författare"),
            "100": {"a": "Author, Test,"},
            "082": {"a": "839.78"},
            "300": {"a": "123 sidor"},
        }

        book_info = interpret_marc(marc_record)

        self.assertEqual(book_info["ISBN"], "9780306406157")
        self.assertEqual(book_info["Title"], "Titel: undertitel")
        self.assertEqual(book_info["Author"], "Author, Test")
        self.assertEqual(book_info["DDC"], "839.78")
        self.assertEqual(book_info["DDCMaster"], "800")
        self.assertEqual(book_info["Pages"], 123)


if __name__ == "__main__":
    unittest.main()
