import locale
from collections import Counter
from typing import Any

UNGRAPHABLE_AUTHORS = ["N/A"]


def format_with_separators(input_number: int) -> str:
    """Format an integer using the active locale's thousands separators."""
    return locale.format_string("%d", input_number, grouping=True)


def get_display_time(days: int) -> str:
    """
    Convert a number of days into a compact human-readable duration.

    The conversion uses approximate month and year lengths because the value is
    shown as an estimate, not as a calendar-accurate date interval.
    """
    intervals = (
        ("years", 365),
        ("months", 30),
        ("weeks", 7),
        ("days", 1),
    )

    result = []

    for name, count in intervals:
        value = days // count
        if value:
            days -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append(f"{value} {name}")
    return ", ".join(result)


def get_most_frequent_authors(
    target_size: int, input_list: list[str]
) -> list[dict[str, Any]]:
    """
    Return the most common graphable authors from a sequence of author names.

    Author names stored as "Last, First" are converted to display form, and
    values listed in UNGRAPHABLE_AUTHORS are skipped so placeholder authors do
    not appear in statistics charts.
    """
    output_list = list()
    common_with_counter = Counter(input_list).most_common(
        target_size + len(UNGRAPHABLE_AUTHORS)
    )

    for item in common_with_counter:
        dict_item = dict()
        dict_item["AuthorSort"] = str(item[0])

        if "," in dict_item["AuthorSort"]:
            author = str(item[0])
            author = (
                author[author.rfind(",") + 1 :].strip()
                + " "
                + author[: author.rfind(",")].strip()
            )
            dict_item["Author"] = author
        else:
            dict_item["Author"] = dict_item["AuthorSort"]

        dict_item["Count"] = item[1]

        if dict_item["AuthorSort"] not in UNGRAPHABLE_AUTHORS:
            output_list.append(dict_item)

    return output_list


def _counter_to_template_list(
    counter: Counter[str], value_key: str
) -> list[dict[str, Any]]:
    return [
        {value_key: value, "count": count} for value, count in counter.most_common()
    ]


def get_library_statistics(books: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build aggregate statistics for the currently loaded library.

    The result feeds the statistics template with language counts, DDC category
    counts, top authors, paid totals, purchase-year counts, and rough reading
    time estimates.
    """
    language_counter: Counter[str] = Counter()
    ddcmaster_counter: Counter[str] = Counter()
    purchase_year_counter: Counter[str] = Counter()
    all_authors = []
    prices = []
    total_wordcount = 0

    for book in books:
        book_language = book.get("Language", None)
        if book_language:
            language_counter[book_language] += 1

        book_author = book.get("Author", None)
        if book_author:
            all_authors.append(book_author)

        book_ddcmaster = book.get("DDCMaster", None)
        if book_ddcmaster:
            ddcmaster_counter[book_ddcmaster] += 1

        book_addinfo = book.get("PurchaseInfo", None)

        if (
            book_addinfo
            and book_addinfo.count("|") == 2
            and book_addinfo.strip().upper().endswith("SEK")
        ):
            book_price = book_addinfo.split("|")[-1].replace("SEK", "").strip()
            if book_price.isdigit() and int(book_price) > 0:
                prices.append({"Title": book["Title"], "Price": int(book_price)})

        page_count = book.get("Pages", None)
        if page_count:
            if book.get("Notes", None) == "Barn":
                total_wordcount += round(29.3 * (page_count * 0.8))
            else:
                total_wordcount += round(293 * (page_count * 0.8))

        if book_addinfo:
            purchase_date = book_addinfo.strip().split("|")[0].strip()
            book_year = purchase_date[:4]
            if book_year.isdigit() and int(book_year) > 0:
                purchase_year_counter[book_year] += 1
        else:
            purchase_year_counter["0"] += 1

    total_price = sum(book["Price"] for book in prices)
    prices = sorted(prices, key=lambda book: book["Price"], reverse=True)[:10]

    year_in = [
        {"year": "Pre-2018" if year == "0" else year, "count": count}
        for year, count in sorted(purchase_year_counter.items())
    ]

    my_reading_speed = 300
    readtime_hours = round(total_wordcount / (my_reading_speed * 60))
    readtime_days = round(total_wordcount / (my_reading_speed * 60) / 8)

    return {
        "Languages": _counter_to_template_list(language_counter, "language"),
        "DDCMaster": _counter_to_template_list(ddcmaster_counter, "DDCMaster"),
        "Prices": prices,
        "Paid": format_with_separators(total_price),
        "Words": format_with_separators(total_wordcount),
        "ReadtimeHours": format_with_separators(readtime_hours),
        "ReadtimeCalculated": get_display_time(readtime_days),
        "YearIn": year_in,
        "Top Authors": get_most_frequent_authors(5, all_authors),
    }
