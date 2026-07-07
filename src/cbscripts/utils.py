import json
import logging
import sqlite3
from pathlib import Path

from cbscripts.sql_statements import statements

logger = logging.getLogger(__name__)

def get_comic_files(path, subdirectory_search=False):
    """
    Returns a list of comic book files in the given path.
    """
    if subdirectory_search:
        # Recursively search for comic book files in all subdirectories
        comic_files = [
            file for ext in ("*.cbz", "*.cbr", "*.pdf")
            for file in path.rglob(ext)
        ]
        counter = len(comic_files)
    else:
        # Search for comic book files in the current directory only
        comic_files = [file for file in path.iterdir() if file.is_file() and file.suffix in [".cbz", ".cbr", ".pdf"]]
        counter = len(comic_files)

    return comic_files, counter

def open_sqlite_connection(database_file: str) -> sqlite3.Connection:
    """
    Opens a connection to the SQLite database and returns the connection object.
    """
    sql_connection = sqlite3.connect(database_file)
    cursor = sql_connection.cursor()

    # Execute a query to get the SQLite version
    query = 'SELECT sqlite_version();'
    cursor.execute(query)

    result = cursor.fetchall()

    logger.info(f"SQLite ({result[0][0]}) connected @ {database_file}")

    cursor.close()

    return sql_connection

def initialize_database(sql_connection: sqlite3.Connection) -> None:
    """
    AI generated function, checked by human 26-06-2026

    Initializes the SQLite database schema if not already initialized.
    Creates all necessary tables if they don't exist.
    Dictionary is ordered to satisfy foreign key constraints.

    Args:
        sql_connection: Active SQLite connection object

    Raises:
        sqlite3.Error: If there's an error creating the schema
    """
    cursor = sql_connection.cursor()

    try:
        # Check if database is already initialized by looking for series table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='series';"
        )
        db_exists = cursor.fetchone() is not None

        if not db_exists:
            logger.info("Initializing database schema...")
            for statement in statements.values():
                cursor.execute(statement)
            sql_connection.commit()
            logger.info("Database schema created successfully")
        else:
            logger.info("Database already initialized")

    except sqlite3.Error as e:
        logger.error(f"Error initializing database schema: {e}")
        sql_connection.rollback()
        raise
    finally:
        cursor.close()

def publisher_mapping(query_publisher: str) -> str:
    """
    Maps a query publisher string to a standardized publisher name.
    If item is not found in the map, returns the original query publisher.
    """
    query_publisher_flat = "".join(query_publisher.lower().split("_"))
    publisher_map: dict = json.load(open("publisher_mapping.json"))

    return publisher_map.get(query_publisher_flat, query_publisher)
