import typer
import logging

from cbscripts.sort_cb import main as sort_comics

from cbscripts.scan_dir import main as scan_dir

app = typer.Typer()

def setup_logging(log_level: str):

    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level.upper() not in level_mapping:
        raise ValueError(f"Invalid log level: {log_level}\nSelect from {level_mapping.values()}")

    logging.basicConfig(
        level=level_mapping[log_level.upper()],
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("ComicBookScripts.log"),  # logs to file
            logging.StreamHandler(),  # logs to console
        ],
    )
    return logging.getLogger("ComicBookScripts")


@app.command()
def scan(
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
    mylar_json: bool = False,
    rename_files: bool = False,
    output_directory: str = "cb_sorted/",
    update_database: bool = True,
    database_file: str = "cbscripts.db",
    hash_pages: bool = True,
    log_level: str = "INFO"
):
    """
    Scan a given directory of comic books (in CBZ format) and insert them into a SQLite database.
    """
    setup_logging(log_level)
    scan_dir(directory, dry_run, scan_subs, mylar_json, output_directory, update_database, database_file, hash_pages)


@app.command()
def sort(
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
    mylar_json: bool = False,
    rename_files: bool = False,
    output_directory: str = "cb_sorted/",
    log_level: str = "INFO"
):
    """
    Rename comics in a given directory.
    """
    setup_logging(log_level)
    sort_comics(directory, dry_run, scan_subs, mylar_json, output_directory)


if __name__ == "__main__":
    app()
