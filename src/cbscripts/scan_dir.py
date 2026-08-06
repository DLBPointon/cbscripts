import logging
import sqlite3
from pathlib import Path

import typer

from cbscripts.comic_class import ComicBook
from cbscripts.utils import (
    ASSETS_DIR,
    get_comic_files,
    initialize_database,
    open_sqlite_connection,
)

logger = logging.getLogger(__name__)

def main(
    context: typer.Context,
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
    output_directory: str = "cb_sorted/",
    update_database: bool = True,
    database_file: str = "cbscripts.db",
    hash_pages: bool = True,
    scanner_db: str | None = None,
    publisher_mapping_file: str | None = None,
    hash_threads: int | None = None,
):
    # Resolve paths: CLI arg → config file value → package default
    resolved_scanner_db = Path(scanner_db) if scanner_db else (context.obj.scanner_db or ASSETS_DIR / "scanner_hash.json")
    resolved_publisher_map = Path(publisher_mapping_file) if publisher_mapping_file else (context.obj.publisher_mapping_file or ASSETS_DIR / "publisher_mapping.json")
    resolved_hash_threads = hash_threads if hash_threads is not None else context.obj.hash_threads
    logger.info(f"Scanning directory: {directory}")
    comic_files, counter = get_comic_files(Path(directory), scan_subs)
    logger.info(f"Found {counter} comic files")

    sql_connection = None
    try:

        logger.info(f"Updating database: {update_database}")
        if update_database:
            # its a .database_file here because its a object it self
            sql_connection = open_sqlite_connection(context.obj.database_file)
            initialize_database(sql_connection)

        for comic in comic_files:
            delimiter = context.obj.delimiter if context.obj.delimiter else None
            comicbook = ComicBook(comic, hash_pages=hash_pages, rename_format=context.obj.rename_format, scanner_db=resolved_scanner_db, publisher_mapping_file=resolved_publisher_map, delimiter=delimiter, hash_threads=resolved_hash_threads)
            print(comicbook.report())

            if update_database and sql_connection:
                comicbook.send_to_sqlite(sql_connection)

    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")

    finally:
        if sql_connection:
            sql_connection.close()
            logger.info('SQLite Connection closed')

    logger.info(f"Scanned directory: {directory}")
    logger.info(f"Found {counter} comic files")
