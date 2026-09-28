import functools
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"


def get_comic_files(
    path, subdirectory_search=False
) -> tuple[list[Path], int, list[Path], int]:
    """
    Returns a list of comic book files in the given path.
    """
    valid_format_files = []
    invalid_format_files = []

    # if subdirectory_search, recursively search for comic book files in all subdirectories
    all_files = list(path.rglob("*")) if subdirectory_search else list(path.iterdir())

    valid_formats = (".cbz", ".cbr")

    for i in all_files:
        if i.is_file() and i.suffix in valid_formats:
            all_files.remove(i)
            valid_format_files.append(i)
        elif i.is_file() and i.suffix not in valid_formats:
            all_files.remove(i)
            invalid_format_files.append(i)

    return (
        valid_format_files,
        len(valid_format_files),
        invalid_format_files,
        len(invalid_format_files),
    )


@functools.cache
def _load_publisher_map(path: Path) -> dict:
    resolved = path or (ASSETS_DIR / "publisher_mapping.json")
    with open(resolved) as f:
        entries = json.load(f)
    result = {}
    for entry in entries:
        for alias in entry["aliases"]:
            key = alias.lower().replace(" ", "").replace("_", "")
            result[key] = entry["canonical"]
    return result


def publisher_mapping(query_publisher: str, mapping_file: Path) -> str:
    key = query_publisher.lower().replace(" ", "").replace("_", "")
    return _load_publisher_map(mapping_file).get(key, query_publisher)


@functools.cache
def _load_scanner_dict(scanner_db) -> dict:
    with open(scanner_db) as f:
        return json.load(f)
