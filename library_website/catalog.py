from collections.abc import Callable
from typing import Any


def sortkeypicker(keynames: list[str]) -> Callable[[dict[str, Any]], list[Any]]:
    """
    Return a key function for sorting dictionaries by multiple fields.

    Prefix a field name with "-" to sort numeric values in descending order for
    that field. Missing values sort as empty strings.
    """
    normalized_keynames = []
    negate = set()
    for keyname in keynames:
        if keyname[:1] == "-":
            normalized_keynames.append(keyname[1:])
            negate.add(keyname[1:])
        else:
            normalized_keynames.append(keyname)

    def getit(adict: dict[str, Any]) -> list[Any]:
        composite = [adict.get(keyname, "") for keyname in normalized_keynames]
        for index, (keyname, value) in enumerate(
            zip(normalized_keynames, composite, strict=True)
        ):
            if keyname in negate:
                try:
                    composite[index] = -value
                except TypeError:
                    composite[index] = value
        return composite

    return getit


def ddc_filter_type(ddc_filter: str | None) -> str | None:
    """Return the database field that should be used for a DDC filter."""
    try:
        if int(float(ddc_filter)) % 100 == 0:
            return "DDCMaster"
    except (TypeError, ValueError):
        return None

    return "DDC"


def filter_books_by_ddc(
    books: list[dict[str, Any]], ddc_filter: str | None
) -> list[dict[str, Any]]:
    """Filter books by DDC/DDCMaster and sort matching rows by DDC and author."""
    filter_type = ddc_filter_type(ddc_filter)
    if not ddc_filter or filter_type is None:
        return list(books)

    filtered_books = [
        book
        for book in books
        if str(book.get(filter_type) or "").startswith(str(ddc_filter))
    ]

    return sorted(filtered_books, key=sortkeypicker(["DDC", "Author"]))
