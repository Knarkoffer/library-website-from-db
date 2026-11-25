import os
import sys
from dataclasses import dataclass
from typing import Any

import yaml

DEFAULT_CONFIG_FILE = "config.yml"


@dataclass(frozen=True)
class AppConfig:
    """Resolved application configuration."""

    library_name: str
    library_path: str
    library_database_path: str
    marc_path: str
    host_ip: str
    host_port: int
    debug_mode: bool
    ssl_cert: str | None
    ssl_key: str | None


def load_config(config_file: str = DEFAULT_CONFIG_FILE) -> dict[str, Any]:
    """
    Load the required application configuration from config.yml.

    Startup exits early if the file is missing, empty, or not valid YAML so
    later path lookups fail predictably.
    """
    if not os.path.isfile(config_file):
        sys.exit(f"No config file found. Create {config_file} from config.example.yml")

    with open(config_file, encoding="utf-8") as ymlfile:
        loaded_config = yaml.safe_load(ymlfile)

    if not loaded_config:
        sys.exit(f"Config file {config_file} is empty or invalid")

    return loaded_config


def load_app_config(config_file: str = DEFAULT_CONFIG_FILE) -> AppConfig:
    """Load config.yml and resolve derived application paths."""
    config = load_config(config_file)

    library_name = config["general"].get("library_name", "Library")
    library_path = config["general"]["library_path"]
    library_database_path = os.path.join(
        library_path, config["general"]["database_name"]
    )
    marc_path = os.path.join(library_path, "MARC-files")

    if not os.path.isfile(library_database_path):
        sys.exit(f"File {library_database_path} not accessible")

    return AppConfig(
        library_name=library_name,
        library_path=library_path,
        library_database_path=library_database_path,
        marc_path=marc_path,
        host_ip=config["web"]["ip"],
        host_port=config["web"]["port"],
        debug_mode=config["web"]["debug_mode"],
        ssl_cert=config["web"].get("ssl_cert"),
        ssl_key=config["web"].get("ssl_key"),
    )
