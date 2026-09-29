import io
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import imagehash
import typer
from PIL import Image

from cbscripts.utils import ASSETS_DIR


@dataclass
class Scanner:
    """
    Small dataclass representing a scanner with a name, hash, and path.
    """

    name: str
    hash: str
    path: str


LOGGER = logging.getLogger(__name__)


def logger_decorator(func):
    def wrapper(*args, **kwargs):
        """
        Quick logger decorator that logs the function name and file input.
        """
        LOGGER.info(f"{func.__name__} - {args[0]}")
        return func(*args, **kwargs)

    return wrapper


@logger_decorator
def get_scanner_hashs(file: Path) -> str:
    """
    Inputs a file path, we need the bytes of that file to hash it.
    This is why we open it like this.

    Returns the hash of the file as a string.
    """
    with open(file, "rb") as f:
        hash = str(imagehash.average_hash(Image.open(io.BytesIO(f.read()))))

    return hash


def generate_json_output(scanners: list[Scanner], output: Path) -> None:
    """
    Writes the scanner hash table to a JSON file after reformating the Scanner dataclass.
    """
    with open(output, "w") as f:
        json.dump(
            {i.hash: {"scanner": i.name, "path": i.path} for i in scanners}, f, indent=4
        )


def main(
    context: typer.Context,
    scanner_directory: Path,
    terminal: bool,
    replace_default: bool = False,
) -> None:
    """
    Main

    This command:
       - finds the scanner directory,
       - hashes all the files in there
       - uses the basename as the scanner name
       - and writes the hash table to a JSON file.

    Optionally, the final result can be used to re-write the default scanner database.
    """
    scanners: list[Scanner] = []
    for file in scanner_directory.glob("*"):
        hash = get_scanner_hashs(file)
        scanners.append(Scanner(name=file.stem, hash=hash, path=str(file)))

    resolved_scanner_db = (
        Path(context.obj.scanner_db)
        if context.obj.scanner_db
        else (context.obj.scanner_db or ASSETS_DIR / "scanner_hash.json")
    )

    if terminal:
        data = {i.hash: {"scanner": i.name, "path": i.path} for i in scanners}
        LOGGER.info(f"Hash table:\n{data}")

    if replace_default:
        LOGGER.info(f"Writing scanner database to {resolved_scanner_db}")
        generate_json_output(scanners, resolved_scanner_db)
        generate_json_output(scanners, Path("scanner_hash.json"))
