import logging
import sqlite3
from pathlib import Path
from turtle import up

from cbscripts.comic_class import ComicBook
from cbscripts.utils import get_comic_files, open_sqlite_connection, initialize_database

logger = logging.getLogger(__name__)

def main(
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
    mylar_json: bool = False,
    output_directory: str = "cb_sorted/",
    update_database: bool = True,
    database_file: str = "cbscripts.db",
    hash_pages: bool = True
):
    logger.info(f"Scanning directory: {directory}")
    comic_files, counter = get_comic_files(Path(directory), scan_subs)
    logger.info(f"Found {counter} comic files")

    sql_connection = None
    try:

        logger.info(f"Updating database: {update_database}")
        if update_database:
            sql_connection = open_sqlite_connection(database_file)
            initialize_database(sql_connection)

        for comic in comic_files:
            comicbook = ComicBook(comic, hash_pages=hash_pages)
            comicbook.send_to_sqlite(sql_connection) if update_database else None

    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")

    finally:
        if sql_connection:
            sql_connection.close()
            logger.info('SQLite Connection closed')
