import unittest

from library_website.statistics import get_display_time, get_library_statistics


class StatisticsTests(unittest.TestCase):
    def test_get_display_time_formats_compact_duration(self) -> None:
        self.assertEqual(get_display_time(400), "1 year, 1 month, 5 days")

    def test_get_library_statistics_builds_template_data(self) -> None:
        books = [
            {
                "Title": "Expensive",
                "Language": "Swedish",
                "DDCMaster": "800",
                "Author": "Doe, Jane",
                "PurchaseInfo": "2024-01-02 | Store | 300 SEK",
                "Pages": 100,
            },
            {
                "Title": "Cheap",
                "Language": "Swedish",
                "DDCMaster": "500",
                "Author": "N/A",
                "PurchaseInfo": "2023-01-02 | Store | 100 SEK",
                "Pages": 10,
                "Notes": "Barn",
            },
            {
                "Title": "Unknown",
                "Language": "English",
                "DDCMaster": "800",
                "Author": "Doe, Jane",
            },
        ]

        stats = get_library_statistics(books)

        self.assertEqual(stats["Languages"][0], {"language": "Swedish", "count": 2})
        self.assertEqual(stats["DDCMaster"][0], {"DDCMaster": "800", "count": 2})
        self.assertEqual(stats["Prices"][0], {"Title": "Expensive", "Price": 300})
        self.assertEqual(stats["Paid"], "400")
        self.assertIn({"year": "Pre-2018", "count": 1}, stats["YearIn"])
        self.assertEqual(
            stats["Top Authors"][0],
            {"AuthorSort": "Doe, Jane", "Author": "Jane Doe", "Count": 2},
        )


if __name__ == "__main__":
    unittest.main()
