# Library Website From DB

A small Flask web app for browsing and maintaining a personal library catalog stored in a local SQLite database. It renders searchable book lists, collection statistics, and Dewey Decimal Classification references, and can add Swedish books by resolving ISBNs through Libris MARC records.

## Features

- Browse the local library database in a sortable, filterable web table.
- Filter the catalog by Dewey Decimal Classification (`DDC`) or top-level `DDCMaster` category.
- View collection statistics for languages, DDC categories, purchase years, top authors, paid totals, and estimated reading time.
- Browse Dewey Decimal reference data in English or Swedish.
- Add books by ISBN or Libris ID using Libris MARC XML data.
- Cache downloaded MARC XML files under the configured library folder.
- Hide culled books when `Notes` matches `Culled YYYY-MM-DD` or `Utgallrad YYYY-MM-DD`.

## Requirements

- Python 3.10 or newer
- A SQLite database with a `library` table
- A `config.yml` file based on `config.example.yml`
- Local TLS certificate and key files, configured in `config.yml`
- The `sv_SE` locale installed on the host, used for number formatting

Install Python dependencies with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```


## Configuration

Copy the example config and update the paths and bind address:

```bash
cp config.example.yml config.yml
```

```yaml
general:
    library_name: My Library
    library_path: /path/to/library
    database_name: Library.db
web:
    ip: 127.0.0.1
    port: 5149
    debug_mode: false
    ssl_cert: /path/to/cert.pem
    ssl_key: /path/to/key.pem
```

`library_name` is displayed in page titles and headings. `library_path` should point to the directory that contains the SQLite database. The app also expects a `MARC-files` directory inside that same library path for cached Libris MARC XML records.

## Running

```bash
library-website
```

The app starts on the configured HTTPS host and port. With the example settings, open:

```text
https://127.0.0.1:5149/
```

## Routes

- `/` - catalog table with search, sorting, DDC filtering, and add-book form
- `/statistics` - aggregate collection statistics and charts
- `/ddc_codes` - Dewey Decimal category reference
- `/ddc_codes?language=sv` - Swedish Dewey Decimal category reference

## Database Notes

The code expects a `library` table with columns used by the templates and import flow, including fields such as `Number`, `Title`, `Author`, `ISBN`, `IDLibris`, `OCLCWorkID`, `DDC`, `DDCMaster`, `LibraryOrigin`, `Language`, `PurchaseInfo`, `Pages`, and `Notes`.

When adding a book, the app currently supports Swedish ISBNs through Libris lookup. Other ISBN countries are detected but not imported automatically.

## License

MIT
