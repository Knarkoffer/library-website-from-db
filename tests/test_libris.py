import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import requests
from pymarc import parse_xml_to_array

from library_website.libris import download_marc_object, isbn_to_librisid
from library_website.marc import interpret_marc

MARC_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<collection xmlns="http://www.loc.gov/MARC21/slim">
  <record>
    <leader>00000nam a2200000 a 4500</leader>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">9780306406157</subfield>
    </datafield>
    <datafield tag="245" ind1="1" ind2="0">
      <subfield code="a">Test book</subfield>
    </datafield>
    <datafield tag="100" ind1="1" ind2=" ">
      <subfield code="a">Author, Test</subfield>
    </datafield>
    <datafield tag="300" ind1=" " ind2=" ">
      <subfield code="a">123 sidor</subfield>
    </datafield>
  </record>
</collection>"""


class LibrisTests(unittest.TestCase):
    @patch("library_website.libris.libris_isbn_search")
    def test_disambiguates_only_when_exactly_one_record_lists_the_isbn(self, search):
        isbn = "9780306406157"
        matching = {"identifier": "/a", "isbn": ["9780306406164", "0-306-40615-2"]}
        other = {"identifier": "/b", "isbn": "9780306406164"}
        for records, rows, expected in [
            (2, [matching, other], (True, "a")),
            (2, [matching, {"identifier": "/b", "isbn": isbn}], (False, None)),
            (2, [other, {"identifier": "/c"}], (False, None)),
            (3, [matching, other], (False, None)),
        ]:
            with self.subTest(records=records, rows=rows):
                search.return_value = {"xsearch": {"records": records, "list": rows}}
                self.assertEqual(isbn_to_librisid(isbn), expected)

    @patch("library_website.libris.requests.get")
    def test_isbn_lookup_downloads_and_parses_a_legacy_record(self, get: Mock) -> None:
        get.side_effect = [
            Mock(
                text='{"xsearch":{"records":1,"list":'
                '[{"identifier":"http://libris.kb.se/bib/123456"}]}}'
            ),
            Mock(content=MARC_XML),
        ]

        found, libris_id = isbn_to_librisid("9780306406157")
        self.assertTrue(found)
        self.assertEqual(libris_id, "123456")
        with tempfile.TemporaryDirectory() as marc_path:
            self.assertTrue(download_marc_object(libris_id, marc_path))
            records = parse_xml_to_array(str(Path(marc_path, "123456.xml")))
            book = interpret_marc(records[0])

        url = urlsplit(get.call_args.args[0])
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.netloc, "libris.kb.se")
        self.assertEqual(url.path, "/_compilemarc")
        self.assertEqual(parse_qs(url.query)["id"], ["http://libris.kb.se/bib/123456"])
        self.assertEqual(parse_qs(url.query)["format"], ["marcxml"])
        self.assertEqual(book["ISBN"], "9780306406157")
        self.assertEqual(book["Title"], "Test book")
        self.assertEqual(book["Author"], "Author, Test")
        self.assertEqual(book["Pages"], 123)

    @patch("library_website.libris.requests.get")
    def test_modern_record_uses_its_https_uri(self, get: Mock) -> None:
        get.return_value = Mock(content=MARC_XML)

        with tempfile.TemporaryDirectory() as marc_path:
            self.assertTrue(download_marc_object("abc123def456", marc_path))

        query = parse_qs(urlsplit(get.call_args.args[0]).query)
        self.assertEqual(query["id"], ["https://libris.kb.se/abc123def456"])

    @patch("library_website.libris.requests.get")
    def test_cached_record_does_not_need_a_download(self, get: Mock) -> None:
        with tempfile.TemporaryDirectory() as marc_path:
            cached_file = Path(marc_path, "123456.xml")
            cached_file.write_bytes(MARC_XML)

            self.assertTrue(download_marc_object("123456", marc_path))
            self.assertEqual(cached_file.read_bytes(), MARC_XML)

        get.assert_not_called()

    @patch("library_website.libris.requests.get")
    def test_http_error_does_not_cache_an_error_response(self, get: Mock) -> None:
        get.return_value.raise_for_status.side_effect = requests.HTTPError("400")
        messages = []

        with tempfile.TemporaryDirectory() as marc_path:
            self.assertFalse(download_marc_object("123456", marc_path, messages.append))
            self.assertFalse(Path(marc_path, "123456.xml").exists())

        self.assertIn("Could not download MARC XML for 123456", messages[0])

    @patch("library_website.libris.requests.get")
    def test_unusable_responses_are_not_cached(self, get: Mock) -> None:
        for content in (
            b"<html>Service unavailable</html>",
            b'<?xml version="1.0"?><collection/>',
        ):
            with self.subTest(content=content):
                get.return_value = Mock(content=content)
                with tempfile.TemporaryDirectory() as marc_path:
                    self.assertFalse(download_marc_object("123456", marc_path))
                    self.assertFalse(Path(marc_path, "123456.xml").exists())


if __name__ == "__main__":
    unittest.main()
