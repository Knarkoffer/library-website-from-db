import os
import tempfile
import unittest

import yaml

from library_website.config import load_app_config


class ConfigTests(unittest.TestCase):
    def write_config(
        self, temp_dir: str, config: dict[str, object], database_name: str
    ) -> str:
        db_path = os.path.join(temp_dir, database_name)
        open(db_path, "a", encoding="utf-8").close()

        config_path = os.path.join(temp_dir, "config.yml")
        with open(config_path, "w", encoding="utf-8") as config_file:
            yaml.safe_dump(config, config_file)

        return config_path

    def test_load_app_config_reads_library_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "general": {
                        "library_name": "Test Library",
                        "library_path": temp_dir,
                        "database_name": "library.sqlite",
                    },
                    "web": {
                        "ip": "127.0.0.1",
                        "port": 5149,
                        "debug_mode": False,
                    },
                },
                "library.sqlite",
            )

            config = load_app_config(config_path)

        self.assertEqual(config.library_name, "Test Library")

    def test_load_app_config_defaults_library_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "general": {
                        "library_path": temp_dir,
                        "database_name": "library.sqlite",
                    },
                    "web": {
                        "ip": "127.0.0.1",
                        "port": 5149,
                        "debug_mode": False,
                    },
                },
                "library.sqlite",
            )

            config = load_app_config(config_path)

        self.assertEqual(config.library_name, "Library")


if __name__ == "__main__":
    unittest.main()
