import logging
import sqlite3
from pathlib import Path

import typer

from cbscripts.comic_class import ComicBook
from cbscripts.db.utils import create_database
from cbscripts.to_database import to_db
from cbscripts.utils import (
    ASSETS_DIR,
    get_comic_files,
)

logger = logging.getLogger(__name__)


def main(
    context: typer.Context,
    directory: str,
    scan_subs: bool = False,
    update_database: bool = True,
    hash_pages: bool = True,
    scanner_db: str | None = None,
    publisher_mapping_file: str | None = None,
    hash_threads: int | None = None,
):
    # Resolve paths: CLI arg → config file value → package default
    resolved_scanner_db = (
        Path(scanner_db)
        if scanner_db
        else (context.obj.scanner_db or ASSETS_DIR / "scanner_hash.json")
    )
    resolved_publisher_map = (
        Path(publisher_mapping_file)
        if publisher_mapping_file
        else (
            context.obj.publisher_mapping_file or ASSETS_DIR / "publisher_mapping.json"
        )
    )
    resolved_hash_threads = (
        hash_threads if hash_threads is not None else context.obj.hash_threads
    )
    logger.info(f"Scanning directory: {directory}")

    comic_files, counter, invalid_files, invalid_counter = get_comic_files(
        Path(directory), scan_subs
    )

    logger.info(f"Found {counter} comic files")

    sql_connection = None

    try:
        logger.info(f"Updating database: {update_database}")
        if update_database:
            # its a .database_file here because its a object it self
            sql_connection = create_database(context.obj.database_file)

        for comic in sorted(comic_files):
            delimiter = context.obj.delimiter if context.obj.delimiter else None
            comicbook = ComicBook(
                comic,
                hash_pages=hash_pages,
                rename_format=context.obj.rename_format,
                scanner_db=resolved_scanner_db,
                publisher_mapping_file=resolved_publisher_map,
                delimiter=delimiter,
                hash_threads=resolved_hash_threads,
            )

            if update_database and sql_connection:
                to_db(comicbook, sql_connection)

        if ComicBook._no_xmls:
            logger.warning(f"{len(ComicBook._no_xmls)} comic(s) had no ComicInfo.xml:")
            for path in ComicBook._no_xmls:
                logger.warning(f"  - {path}")

        if invalid_counter != 0:
            logger.warning(f"{invalid_counter} comic(s) had invalid format:")
            logger.warning(invalid_files)
            with open("invalid_files.txt", "w") as f:
                f.write("\n".join(str(i) for i in invalid_files))

    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")

    # finally:
    # if sql_connection:
    #   sql_connection.close()
    #  logger.info("SQLite Connection closed")

    logger.info(f"Scanned directory: {directory}")
    logger.info(f"Found {counter} comic files")
