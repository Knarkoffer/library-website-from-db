#!/usr/bin/env python3

import datetime
import json
import locale
import os
import re
import sys
from typing import Any

import isbnlib
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from pymarc import parse_xml_to_array
from werkzeug.serving import WSGIRequestHandler

from library_website.catalog import ddc_filter_type, filter_books_by_ddc
from library_website.config import load_app_config
from library_website.db import add_book_to_db, read_db_to_list
from library_website.libris import (
    download_marc_object,
    isbn_to_librisid,
    validate_isbn,
)
from library_website.marc import interpret_marc
from library_website.statistics import get_library_statistics


class EmptyServerHeaderRequestHandler(WSGIRequestHandler):
    """Suppress Werkzeug's default Server header in local HTTP responses."""

    def version_string(self) -> str:
        """Return an empty server version string for the Server header."""
        return ""


settings = load_app_config()

LIBRARY_NAME = settings.library_name
LIBRARY_PATH = settings.library_path
LIBRARY_DATABASE_PATH = settings.library_database_path
MARC_PATH = settings.marc_path
HOST_IP = settings.host_ip
HOST_PORT = settings.host_port
DEBUG_MODE = settings.debug_mode
SSL_CERT = settings.ssl_cert
SSL_KEY = settings.ssl_key

app = Flask(__name__)


@app.context_processor
def inject_template_config() -> dict[str, str]:
    """Make site-wide config values available to every template."""
    return {"library_name": LIBRARY_NAME}


def debug_print(out_string: str) -> None:
    """Print diagnostic output only when debug mode is enabled in config.yml."""
    if DEBUG_MODE:
        print(out_string)


def toggle_info_box(box_type: str, box_visible: bool, box_message: str) -> None:
    """
    Store notification state in the Flask session for the next rendered page.

    box_type controls the template styling and should be one of ERROR, INFO, or
    SUCCESS. box_visible decides whether the notification is shown, and
    box_message may contain the small amount of HTML already used by templates.
    """
    print(f"Type: {box_type} | Visible: {box_visible} | Box message: {box_message}")

    session["info_type"] = box_type
    session["info_show"] = box_visible
    session["info_message"] = box_message
    session.modified = True


def load_dewey_data() -> dict[str, Any]:
    """Load Dewey Decimal reference data used by the /ddc_codes route."""
    ddc_codes_file = r"./static/dewey.json"
    if os.path.isfile(ddc_codes_file):
        with open(ddc_codes_file, encoding="utf-8") as json_file:
            return json.load(json_file)

    sys.exit(f"File {ddc_codes_file} not accessible")


def refresh_library_cache_if_needed() -> tuple[list[str], list[dict[str, Any]]]:
    """Refresh the in-memory library cache when the SQLite file has changed."""
    global all_books
    global all_field_names
    global db_readtime

    db_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(LIBRARY_DATABASE_PATH))
    if not db_readtime or db_mtime > db_readtime:
        print("DB changed or data not read earlier")
        all_field_names, all_books = read_db_to_list(LIBRARY_DATABASE_PATH)
        db_readtime = datetime.datetime.now()

    return all_field_names, all_books


def shutdown_server() -> None:
    """
    Stop the Werkzeug development server when running under that server.

    This helper is currently not exposed as a route, but is kept for local
    shutdown/debug flows.
    """
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    sys.exit("EXIT!!!")


print("Script initiated")
all_field_names: list[str] = []
all_books: list[dict[str, Any]] = []
db_readtime: datetime.datetime | None = None
DEWEY_DATA = load_dewey_data()

print(f"https://{HOST_IP}:{HOST_PORT}/")

# Changes the locale
locale.setlocale(locale.LC_ALL, "sv_SE")


@app.before_request
def before_request() -> Any:
    """Redirect plain HTTP requests to the local HTTPS endpoint."""
    if request.url.startswith("http://"):
        return redirect(f"https://{request.url[len('http://'):]}", code=301)

    return None


@app.route("/favicon.ico")
@app.route("/robots.txt")
def static_from_root() -> Any:
    """
    Serve root-level browser metadata files from the static directory.

    Flask normally serves these below /static; these routes keep the common
    /favicon.ico and /robots.txt URLs working.
    """
    return send_from_directory(app.static_folder, request.path[1:])


@app.route("/")
def render_library(go_to_bottom: bool = False) -> Any:
    """
    Render the library table, refreshing the in-memory cache when the DB changes.

    An optional ddc query parameter filters the list by either DDC or DDCMaster,
    depending on whether the supplied value represents a top-level hundred.
    """
    field_names, books = refresh_library_cache_if_needed()
    ddc_filter = request.args.get("ddc")

    if ddc_filter:
        print(f"Filtering on books with DDC {ddc_filter}")
        if ddc_filter_type(ddc_filter) is None:
            print("Improperly formated DDC supplied :-(")
            filtered_books = books
        else:
            filtered_books = filter_books_by_ddc(books, ddc_filter)
    else:
        print("No ddc ddc_filter, list all books")
        filtered_books = books

    return render_template(
        "library.html",
        table_headers=field_names,
        booklist=filtered_books,
        go_to_bottom=go_to_bottom,
    )


@app.route("/statistics")
def render_statistics() -> Any:
    """Render the statistics page from freshly calculated library aggregates."""
    print("rendering stats")
    _, books = refresh_library_cache_if_needed()
    return render_template(
        "statistics.html", library_statistics=get_library_statistics(books)
    )


@app.route("/ddc_codes")
def ddc_codes() -> Any:
    """Render the Dewey Decimal reference page in the requested language."""
    ddc_lang = request.args.get("language")
    if not ddc_lang:
        ddc_lang = "en"

    return render_template("ddc_codes.html", dewey_data=DEWEY_DATA, ddc_lang=ddc_lang)


@app.route("/mute_notification", methods=["POST"])
def mute_notification() -> Any:
    """Hide the current session notification and return the home template."""
    print("Muting notifications")
    toggle_info_box(
        box_type="INFO", box_visible=False, box_message="Notification muted..."
    )
    return redirect(url_for("render_library"))


@app.route("/add_book", methods=["POST"])
def add_book() -> Any:
    """
    Add a book by ISBN or Libris ID from the library page form.

    The handler validates duplicate input, resolves Swedish ISBNs through
    Libris, downloads the MARC XML record, parses it into local fields, and
    inserts the result into the database.
    """
    global db_readtime

    libris_id = None
    libris_id_found = False
    is_duplicate = False
    _, books = refresh_library_cache_if_needed()

    textbox_isbn = (request.form.get("tbx_isbn") or "").strip()
    textbox_librisid = (request.form.get("tbx_librisid") or "").strip()

    if textbox_isbn:
        print(f"Will now check if {textbox_isbn} is already in lib...")
        if any(book.get("ISBN", None) == textbox_isbn for book in books):
            is_duplicate = True
            toggle_info_box("ERROR", True, f"ISBN {textbox_isbn} already in DB")

    debug_print(f"Dupe status 1 (ISBN): {is_duplicate}")

    if not is_duplicate and textbox_isbn:
        debug_print("add by isbn")
        if validate_isbn(textbox_isbn):
            if isbnlib.info(textbox_isbn) == "Sweden":
                libris_id_found, libris_id = isbn_to_librisid(textbox_isbn, debug_print)
            else:
                print(f"Country is {isbnlib.info(textbox_isbn)}, unsupported for now")
                toggle_info_box(
                    "ERROR",
                    True,
                    f"{isbnlib.info(textbox_isbn)} is unsupported for now",
                )
        else:
            print(f"ISBN {textbox_isbn} is not valid")
            toggle_info_box("ERROR", True, "Invalid ISBN")

    elif not is_duplicate and textbox_librisid:
        debug_print("add by libris")
        libris_id = textbox_librisid
        if re.match("(^[A-Za-z0-9]+$)", libris_id) is not None:
            libris_id_found = True
        else:
            print("Not fitting parameters of a valid Libris ID")

        if any(book.get("IDLibris", None) == libris_id for book in books):
            is_duplicate = True
            toggle_info_box("ERROR", True, f"LibrisID <b>{libris_id}</b> already in DB")

    else:
        print("Nothing in either field :-(")

    if libris_id_found and not is_duplicate:
        print("Fetching corresponding MARC file")

        if download_marc_object(libris_id, MARC_PATH, debug_print):
            marc_file_path = os.path.join(MARC_PATH, libris_id + ".xml")

            print(f"Loading file {marc_file_path}")
            try:
                book_marc_object = parse_xml_to_array(marc_file_path)[0]
                book = interpret_marc(book_marc_object, debug_print)
                book["IDLibris"] = libris_id
                book["Language"] = "Swedish"

            except IndexError:
                print("Problems reading MARC-file...")
                book = None

            if book:
                if add_book_to_db(LIBRARY_DATABASE_PATH, book):
                    db_readtime = None
                    print("Added successful, updating session info...")

                    toggle_info_box(
                        box_type="SUCCESS",
                        box_visible=True,
                        box_message=f"<i>{book['Title']}</i> added to database!",
                    )
        else:
            print(f"Download failed for LibrisID {libris_id}")
            toggle_info_box(
                box_type="ERROR",
                box_visible=True,
                box_message=(
                    f"Could not download the MARC record for LibrisID "
                    f"<b>{libris_id}</b>. Libris may be unavailable or the record "
                    "may not exist. Please try again later."
                ),
            )

    return redirect(url_for("render_library"))


def main() -> None:
    """Run the configured Flask development server."""
    app.config.update(SECRET_KEY=os.urandom(12), SESSION_COOKIE_SECURE=True)

    app.run(
        host=HOST_IP,
        debug=DEBUG_MODE,
        port=HOST_PORT,
        threaded=True,
        ssl_context=(SSL_CERT, SSL_KEY) if SSL_CERT and SSL_KEY else None,
        request_handler=EmptyServerHeaderRequestHandler,
    )


if __name__ == "__main__":
    main()
