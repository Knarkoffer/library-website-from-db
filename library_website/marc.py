import re
from collections.abc import Callable
from typing import Any

import isbnlib

from library_website.libris import validate_isbn


def extract_page_count(
    marc_object: Any, debug: Callable[[str], None] = lambda _: None
) -> int:
    """
    Extract a page count from MARC field 300 using known Libris formats.

    Libris records use several textual forms for physical descriptions. The
    parser keeps the previous matching order and returns 0 when no known page
    count pattern can be parsed.
    """
    marc_field = marc_object.get("300")
    if not marc_field:
        debug("Page count method 0: missing MARC field 300")
        return 0

    try:
        book_pagecount = str(marc_field["a"])
    except (AttributeError, KeyError, TypeError):
        debug(f"Problems converting {marc_field} to pagecount")
        return 0

    regex_match = re.search(r"\(\d+ s\.\)", book_pagecount)
    if regex_match:
        page_count = regex_match.group(0)[1 : regex_match.group(0).rfind(" ")]
        return int(page_count.strip())

    regex_match = re.search(r"\b(\d+)\s+(sidor|pages)\b", book_pagecount)
    if regex_match:
        return int(regex_match.group(1))

    regex_match = re.match(r"^(\[\d+\] s.)", book_pagecount)
    if regex_match:
        page_count = book_pagecount[1 : book_pagecount.find("]")]
        return int(page_count)

    for pattern in (r", \d+ s\., ", r", \d+ s\. ", r", \d+ s\."):
        regex_match = re.search(pattern, book_pagecount)
        if regex_match:
            page_count = regex_match.group(0)[2 : regex_match.group(0).find("s")]
            return int(page_count)

    regex_match = re.search(r", \d+, \[\d+\] s\.", book_pagecount)
    if regex_match:
        page_count = regex_match.group(0)[2 : regex_match.group(0).rfind(",")]
        return int(page_count)

    compact_pagecount = book_pagecount.replace(" ", "")
    regex_match = re.search(r"\d+,\[\d+\]s\.", compact_pagecount)
    if regex_match:
        page_count = regex_match.group(0)[: regex_match.group(0).find(",")]
        return int(page_count)

    try:
        page_count = book_pagecount.split(" ")[0].replace(",", "").strip()
        page_count = re.sub(r"(\(\d+\)s)", "", page_count)
        page_count = page_count.lower().replace("s", "")
        return int(page_count)
    except ValueError:
        debug(f"Problems converting {marc_field} to pagecount")
        return 0


def interpret_marc(
    marc_object: Any, debug: Callable[[str], None] = lambda _: None
) -> dict[str, Any]:
    """
    Extract the local database fields supported by a pymarc Record.

    The MARC fields are mapped into the small schema used by the library table:
    ISBN, title, author, DDC/DDCMaster, and page count when those values can be
    parsed from Libris data.
    """
    book_info = dict()

    if not book_info.get("ISBN", None):
        try:
            isbn_number = isbnlib.canonical(str(marc_object["020"]["a"]))
            if validate_isbn(isbn_number):
                book_info["ISBN"] = isbn_number
        except (KeyError, TypeError):
            pass

    title = str(marc_object["245"]).split("$")[1:]
    title = " ".join([part[1:] for part in title])

    if "/" in title:
        title = title.split("/")[0]

    title = title.replace(" : ", ": ")
    title = re.sub(r"\s{2,}", " ", title)
    book_info["Title"] = title.strip()

    book_author = marc_object.get("100", None)
    if book_author:
        book_info["Author"] = book_author["a"].strip().rstrip(",").strip()

    book_author = marc_object.get("700", None)
    if book_author and not book_info.get("Author", None):
        book_info["Author"] = book_author["a"].strip().rstrip(",").strip()

    if not book_info.get("Author", None):
        book_info["Author"] = "N/A"

    try:
        book_info["DDC"] = marc_object["082"]["a"].strip()
        book_info["DDCMaster"] = marc_object["082"]["a"][:1] + "00".strip()
    except (KeyError, TypeError, AttributeError):
        pass

    book_info["Pages"] = extract_page_count(marc_object, debug)

    return book_info
