import os
from dataclasses import dataclass

from pathlib import Path
import sys
import yaml
import typer
import logging

from cbscripts.sort_cb import main as sort_comics

from cbscripts.scan_dir import main as scan_dir

app = typer.Typer()

@dataclass
class ConfigData:
    database_file: Path
    rename_format: str = "N"
    log_level: str = "INFO"


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


def load_config(config_file: str) -> ConfigData:
    config_file = os.path.expanduser(config_file)
    if not os.path.exists(config_file):
        sys.exit(f"Config file not found: {config_file}, please create it!")
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        return ConfigData(**data)


@app.callback()
def get_config(
    context: typer.Context,
    config_file: str = typer.Option(None, "--config", "-c", help="Path to Global config file", show_default=True, file_okay=True, dir_okay=False, readable=True, writable=False),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level", show_default=True),
):

    config_file = config_file if config_file else "~/.config/cbscripts/.cbscript.config"

    config_data = load_config(config_file)
    if not config_data.log_level and log_level:
        config_data.log_level = log_level

    setup_logging(log_level)

    context.obj = config_data


@app.command()
def scan(
    context: typer.Context,
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
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
    scan_dir(context, directory, dry_run, scan_subs, output_directory, update_database, database_file, hash_pages)


@app.command()
def sort(
    context: typer.Context,
    directory: str,
    dry_run: bool = False,
    scan_subs: bool = False,
    rename_files: bool = False,
    output_directory: str = "cb_sorted/",
    log_level: str = "INFO"
):
    """
    Rename comics in a given directory.
    """
    sort_comics(context, directory, dry_run, scan_subs, output_directory)


if __name__ == "__main__":
    app()
