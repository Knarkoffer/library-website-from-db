import binascii
import json
import os
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import isbnlib
import requests

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def get_libris_headers(accept: str | None = None) -> dict[str, str]:
    """
    Build request headers for Libris calls.

    Libris is queried as a normal browser client. The optional Accept header
    lets each caller request the response format it can parse.
    """
    headers = {"User-Agent": BROWSER_USER_AGENT}
    if accept:
        headers["Accept"] = accept
    return headers


def get_file_crc(file_path: str) -> str:
    """Return the CRC32 checksum of a file as an eight-character hex string."""
    with open(file_path, "rb") as file_handle:
        buf = file_handle.read()
    buf = binascii.crc32(buf) & 0xFFFFFFFF
    return f"{buf:08X}"


def validate_isbn(isbn: str) -> bool:
    """Return True when an input string is a valid ISBN-10 or ISBN-13 value."""
    isbn = isbnlib.canonical(isbn)

    return isbnlib.is_isbn10(isbn) or isbnlib.is_isbn13(isbn)


def libris_isbn_search(
    isbn: str, debug: Callable[[str], None] = lambda _: None
) -> dict[str, Any]:
    """
    Search Libris for a single ISBN and return the decoded JSON response.

    Network errors and invalid JSON are logged in debug mode and represented as
    an empty dictionary so callers can handle "no usable result" uniformly.
    """
    built_url = "https://libris.kb.se/xsearch?query=numm%3a" + isbn + "&format=json"
    try:
        libris_request = requests.get(
            built_url,
            headers=get_libris_headers("application/json,*/*;q=0.8"),
            timeout=30,
        )
        libris_request.raise_for_status()
        return json.loads(libris_request.text)
    except (requests.RequestException, json.JSONDecodeError) as error:
        debug(f"Libris ISBN search failed for {isbn}: {error}")
        return {}


def isbn_to_librisid(
    isbn: str, debug: Callable[[str], None] = lambda _: None
) -> tuple[bool, str | None]:
    """
    Resolve an ISBN to one Libris identifier when Libris has exactly one match.

    Returns a (found, libris_id) tuple. Multiple or zero matches are treated as
    unresolved because adding the wrong record would be worse than adding none.
    """
    search_results = libris_isbn_search(isbn, debug)
    if not search_results:
        print("No matches for ISBN")
        return False, None

    records = search_results.get("xsearch", {}).get("records")
    if records == 1:
        libris_id = search_results["xsearch"]["list"][0]["identifier"].split("/")[-1]
        print(f"Found matching Libris entry ({libris_id}) for isbn {isbn}")
        return True, libris_id

    if records == 0:
        debug(f"No Libris matches for ISBN {isbn}: {search_results}")
    else:
        debug(
            f"Too many Libris matches for ISBN {isbn}: "
            f"{search_results.get('xsearch')}"
        )

    return False, None


def download_marc_object(
    libris_id: str,
    marc_path: str,
    debug: Callable[[str], None] = lambda _: None,
) -> bool:
    """
    Download and cache a MARC XML record from Libris for one Libris ID.

    libris_id is the Libris record identifier, without the
    URL prefix. Numeric legacy IDs use http://libris.kb.se/bib/{id}; modern
    alphanumeric IDs use https://libris.kb.se/{id}. The export endpoint resolves
    these exact record URIs, even though the request itself always uses HTTPS.
    """
    download_successful = False

    marc_file_path = os.path.join(marc_path, libris_id + ".xml")

    if os.path.isfile(marc_file_path):
        print("File downloaded previously")
        return True

    record_uri = (
        f"http://libris.kb.se/bib/{libris_id}"
        if libris_id.isdecimal()
        else f"https://libris.kb.se/{libris_id}"
    )
    query_string = urlencode(
        {
            "library": "Foo",
            "id": record_uri,
            "format": "marcxml",
        }
    )
    build_url = f"https://libris.kb.se/_compilemarc?{query_string}"

    try:
        marc_request = requests.get(
            build_url,
            headers=get_libris_headers("application/xml,*/*;q=0.8"),
            timeout=30,
        )
        marc_request.raise_for_status()
    except requests.RequestException as error:
        debug(f"Could not download MARC XML for {libris_id}: {error}")
        return False

    content_start = marc_request.content.lstrip()
    if not (
        content_start.startswith(b"<?xml") or content_start.startswith(b"<collection")
    ):
        debug(f"Libris returned a non-XML response for {libris_id}")
        return False

    if b"<record" not in marc_request.content:
        debug(f"Libris returned XML without a MARC record for {libris_id}")
        return False

    with open(marc_file_path, mode="wb") as file_handle:
        file_handle.write(marc_request.content)

    if os.path.isfile(marc_file_path):
        if get_file_crc(marc_file_path) == "49F460FE":
            debug(
                f"File downloaded, but empty "
                f"(This means {libris_id} is an invalid LibrisID)"
            )
            debug("Cleans up file")
            os.remove(marc_file_path)
        else:
            download_successful = True

    return download_successful
