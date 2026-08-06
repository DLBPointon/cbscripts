import io
import logging
import os
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from pathlib import Path

import imagehash
import pikepdf
import rarfile
from PIL import Image

from cbscripts.exceptions import ExtractionError
from cbscripts.utils import _load_scanner_dict, publisher_mapping
from cbscripts.xml_dataclass import XML_data

logger = logging.getLogger(__name__)


def _hash_page(args: tuple[str, bytes]) -> tuple[str, str]:
    """Hash one page's raw bytes. Runs inside a ThreadPoolExecutor."""
    page_path, data = args
    thread = threading.current_thread().name
    logger.debug(f"[{thread}] Starting hash: {page_path}")
    result = str(imagehash.average_hash(Image.open(io.BytesIO(data))))
    logger.debug(f"[{thread}] Done:          {page_path}")
    return page_path, result


class ComicBook:
    _ids = count(0)
    def __init__(self, file_path: Path, rename_format: str, scanner_db: Path, hash_pages=False, delimiter: str | None = None, publisher_mapping_file: Path | None = None, hash_threads: int = 2):
        self.id = next(self._ids)
        self.publisher_mapping_file = publisher_mapping_file
        self.hash_threads = max(2, min(hash_threads, 12))

        self.current_file_path = file_path.absolute()
        self.current_file_name = file_path.name
        self.file_extension = file_path.suffix
        self.delimiter = delimiter
        self.file_size = os.path.getsize(file_path) / 1024

        logger.info(f"Processing: {self.current_file_path}")
        t_start = time.perf_counter()

        if self.file_extension in (".cbz", ".cbr"):
            opener = zipfile.ZipFile if self.file_extension == ".cbz" else rarfile.RarFile
            xml_bytes, page_list, image_hashes = self._process_archive(opener, hash_pages)
            xml_data = self.get_data_from_xml(xml_bytes) if xml_bytes else {}
        elif self.file_extension == ".pdf":
            xml_data, page_list = self.read_pdf_metadata()
            image_hashes = {}
        else:
            xml_data, page_list, image_hashes = {}, [], {}

        xml_pages = xml_data.get("pages", [])
        xml_data.pop("pages", None)
        self.xml_data = XML_data(**xml_data)

        if hash_pages and image_hashes:
            self.pages, self.scanner, self.diff_hash = self.check_for_scanner_page(xml_pages, page_list, image_hashes, scanner_db)
        else:
            self.pages, self.scanner, self.diff_hash = xml_pages, "NA", None

        self.proposed_file_name, self.proposed_file_path = self.get_new_name(rename_format, delimiter=self.delimiter)

        self.processing_time = time.perf_counter() - t_start


    def __iter__(self):
        yield from self.__dict__.items()

    def __str__(self):
        txt = io.StringIO()
        txt.write(f"Series: {self.xml_data.series} - Issue: {self.id} -- {self.__class__.__name__}:\n")
        for a, b in self.__dict__.items():
            if a not in {"block", "collection", "contents", "code_data", "pages"}:
                txt.write(f"\t- {a}: {b} \n")
        for item in self.pages:
            txt.write(f"\t- {item} \n")
        txt.write(")")
        return txt.getvalue()


    def report(self) -> str:
        txt = io.StringIO()
        txt.write(f"{self.__class__.__name__}: {self.id} - Series: {self.xml_data.series}\n")
        txt.write(f"\t- Issue: {self.xml_data.issue} -- Publisher: {self.xml_data.publisher}\n")
        txt.write(f"\t- pages: {len(self.pages)} \n")
        for a, b in self.__dict__.items():
            if a in {"scanner", "diff_hash", "current_file_name", "current_file_path", "proposed_file_name", "proposed_file_path"}:
                txt.write(f"\t- {a}: {b} \n")
        txt.write(f"\t- processed in: {self.processing_time:.3f}s\n")
        return txt.getvalue()


    def get_new_name(self, rename_format: str, delimiter: str | None) -> tuple[str, str]:
        if rename_format == "N":
            return str(self.current_file_path), str(self.current_file_path)

        valid_rename_options = {
            "publisher": self.xml_data.publisher,
            "series": self.xml_data.series,
            "issue": self.xml_data.issue,
            "format": self.file_extension,
            "year": self.xml_data.year,
            "volume": self.xml_data.volume
        }

        new_file_path = rename_format.format(**valid_rename_options)
        new_file_name = new_file_path.split("/")[-1] + self.file_extension
        new_file_path_full = new_file_path + self.file_extension

        if delimiter == None:
            return new_file_name, new_file_path_full
        else:
            return delimiter.join(new_file_name.split(" ")), delimiter.join(new_file_path_full.split(" "))

    def _process_archive(self, opener, hash_pages: bool) -> tuple[bytes | None, list, dict]:
        """
        Opens the archive exactly once.
        Returns: (xml_bytes, sorted_page_list, image_hash_map)

        If hash_pages is True, pages are hashed in parallel batches of
        self.hash_threads (1-8, set in config). Each batch reads bytes
        sequentially (zipfile is not thread-safe) then hashes in a
        ThreadPoolExecutor, keeping peak memory to batch_size pages.
        """
        try:
            with opener(self.current_file_path) as archive:
                file_list = archive.namelist()
                logger.debug(file_list)
                xml_bytes = archive.read("ComicInfo.xml") if "ComicInfo.xml" in file_list else None
                if xml_bytes:
                    logger.debug(f"Reading ComicInfo.xml from {self.current_file_path}")
                else:
                    logger.debug(f"No ComicInfo.xml found in {self.current_file_path}")
                pages = self.extract_pages(file_list)

                image_hashes: dict[str, str] = {}
                if hash_pages:
                    total_batches = -(-len(pages) // self.hash_threads)  # ceiling division
                    for i in range(0, len(pages), self.hash_threads):
                        batch = pages[i:i + self.hash_threads]
                        batch_num = i // self.hash_threads + 1
                        logger.debug(f"Batch {batch_num}/{total_batches}: reading {len(batch)} pages")
                        # Read bytes sequentially — zipfile is not thread-safe
                        batch_bytes = {p: archive.read(p) for p in batch}
                        logger.debug(f"Batch {batch_num}/{total_batches}: submitting to {self.hash_threads} threads")
                        # Hash in parallel — PIL/numpy release the GIL
                        t0 = time.perf_counter()
                        with ThreadPoolExecutor(max_workers=self.hash_threads) as pool:
                            image_hashes.update(pool.map(_hash_page, batch_bytes.items()))
                        elapsed = time.perf_counter() - t0
                        logger.debug(f"Batch {batch_num}/{total_batches}: {len(batch)} pages hashed in {elapsed:.3f}s ({elapsed / len(batch):.3f}s/page avg)")

        except Exception as ex:
            logger.error(f"Exception w/ file: {self.current_file_path}\nError: {ex}")
            raise RuntimeError(f"Could not open archive: {self.current_file_path}") from ex

        return xml_bytes, pages, image_hashes


    def read_pdf_metadata(self):
        "Wrapper around extract_pdf, originally contained extra exception handling"
        xml_data, page_list = self.extract_pdf()
        return xml_data if xml_data else {}, page_list

    def extract_pdf(self) -> tuple[dict, list]:
        try:
            with pikepdf.open(self.current_file_path) as pdf:
                meta = pdf.open_metadata()

                # PDF distributed stuff just doesn't have any metadata built in!
                # So, lets check for some common fields and use those if possible
                # If not exists then we will have to None everything and figure it out later.
                xml_data = {
                    "series":  str(meta.get("dc:title")) if meta.get("dc:title") else None,
                    "writer":  str(meta.get("dc:creator")) if meta.get("dc:creator") else None,
                    "summary": str(meta.get("dc:description")) if meta.get("dc:description") else None,
                    "genre":   str(meta.get("dc:subject")) if meta.get("dc:subject") else None,
                }

                page_list = [f"page_{i}.jpg" for i in range(len(pdf.pages))] # Not the real page names, they don't have them!

                return xml_data, page_list
        except Exception as ex:
            raise ExtractionError(
                        f"Failed to extract PDF: {self.current_file_path}"
                    ) from ex


    def extract_pages(self, file_list) -> list:
        """
        Extracts image file paths from the archive.
        """
        return sorted([ i for i in file_list if i.endswith((".jpg", ".png")) ])



    def _extract_pages(self, pages_element) -> list[dict]:
        """Extract page data from Pages element and detect double pages."""
        pages = [dict(page.attrib) for page in pages_element]

        if not pages:
            return pages

        # Find the most common width (single page width)
        widths = [int(page.get('ImageWidth', 0)) for page in pages]
        single_page_width = max(set(widths), key=widths.count)  # Mode
        double_page_width = single_page_width * 2

        # Add Type for double pages
        for page in pages:
            page_width = int(page.get('ImageWidth', 0))
            # If no Type or Type is not already set, check for double page
            if ('Type' not in page or page['Type'] == '') and (page_width != 0 and page_width >= double_page_width * 0.9):  # 90% threshold for tolerance
                page['Type'] = 'DoublePage'
                logger.info(f"Double page detected: {page['Image']} | Width: {page_width} | Single Page Width: {single_page_width} | Page Type is now labelled: '{page['Type']}'")

        return pages



    def get_data_from_xml(self, data):
        """Extracts data from the ComicInfo.xml file in a CBZ archive."""
        root = ET.fromstring(data)

        # Map XML tags to dictionary keys, with optional transformations
        TAG_MAPPING = {
            "AgeRating": ("age_rating", str),
            "Series": ("series", str),
            "Publisher": ("publisher", lambda text: publisher_mapping(text, self.publisher_mapping_file)),
            "Volume": ("volume", str),
            "Year": ("year", str),
            "Month": ("month", str),
            "Day": ("day", str),
            "Number": ("issue", str),
            "Writer": ("writer", str),
            "Penciller": ("penciller", str),
            "CoverArtist": ("cover_artist", str),
            "Editor": ("editor", str),
            "Inker": ("inker", str),
            "Letterer": ("letterer", str),
            "Colorist": ("colourist", str),
            "Characters": ("characters", str),
            "Web": ("web", str),
            "PageCount": ("page_count", str),
            "Summary": ("summary", str),
            "Notes": ("notes", str),
            "Genre": ("genre", str),
            "Locations": ("locations", str),
            "LanguageISO": ("language_iso", str),
            "ScanInformation": ("scan_information", str),
            "Imprint": ("imprint", str),
            "StoryArc": ("story_arc", str),
            "SeriesGroup": ("series_group", str),
            "Teams": ("teams", str),
            "Format": ("format", str),
            "Manga": ("manga", str),
            "BlackAndWhite": ("black_and_white", str),
            "Pages": ("pages", list),
            "MainCharacterOrTeam": ("main_character_or_team", str),
            "Review": ("review", str),
            "CommunityRating": ("community_rating", str),
        }

        result = {}
        for element in root:
            if element.tag in TAG_MAPPING:
                key, processor = TAG_MAPPING[element.tag]
                if element.tag == "Pages":
                    result[key] = self._extract_pages(element)
                else:
                    result[key] = processor(element.text) if element.text else "N"

        return result

    def _parse_float(self, value: float | str) -> float | str | None:
        """
        Safely converts a value to float.
        Returns None if the value is invalid or "UNKNOWN".
        """
        if value == "UNKNOWN" or value is None:
            return "N"
        try:
            if isinstance(value, (int, float)):
                return float(value)

            # Check if it's a valid numeric string by replacing a couple of common characters
            if isinstance(value, str) and value.replace(".", "", 1).replace("-", "", 1).isdigit():
                return float(value)
        except (ValueError, AttributeError):
            pass
        return None

    def _tag_scanner_page(self, xml_dict: list, scanner_db: Path) -> tuple[list, str, int]:
        """
        Tags the scanner page in the XML dictionary if one is detected.
        """
        scanner_dict = _load_scanner_dict(scanner_db)

        for idx, page in enumerate(xml_dict):
            logger.debug(page)
            for x, y in scanner_dict.items():
                diff = imagehash.hex_to_hash(page.get("ImageHash")) - imagehash.hex_to_hash(x)
                if diff <= 10: # 0 == exact match, 1-10 == close match
                    xml_dict[idx]["Type"] = "Deleted"
                    logger.info(f"Scanner page detected: {self.xml_data.series} #{self.xml_data.issue} - Page {page['Image']} ({page['FilePath']}) == {y['scanner']} | Similarity == {abs(diff - 100)}% | Page Type is now labelled: `{page['Type']}`")
                    return xml_dict, y["scanner"], diff

        return xml_dict, "NA", 0

    def check_for_scanner_page(self, xml_dict: list, file_list: list, image_hashes: dict, scanner_db: Path) -> tuple[list, str, int]:
        """
        Annotates each page in xml_dict with its file path and pre-computed image hash,
        then delegates to _tag_scanner_page to detect and mark scanner pages.
        """
        if not isinstance(xml_dict, list) or not xml_dict:
            return [], "NA", 0

        for file_path, page_data in zip(file_list, xml_dict):
            page_data["FilePath"] = file_path
            page_data["ImageHash"] = image_hashes.get(file_path, "")
            logger.debug(f"Hash for page {page_data['Image']}: {page_data['ImageHash']}")

        return self._tag_scanner_page(xml_dict, scanner_db)


    def _to_none(self, value: str | None) -> str | None:
        """Returns None if value is UNKNOWN or empty, otherwise returns the value."""
        if value in ("UNKNOWN", "N", "", None):
            return None
        return value

    def _to_int(self, value: str) -> int | None:
        """Safely converts a string to int, returns None if not possible."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def send_to_sqlite(self, conn: sqlite3.Connection) -> None:
        """
        Inserts comic book data into SQLite database.
        Handles series, publisher, issue, pages, and M2M relationships.
        """
        x = self.xml_data
        cursor = conn.cursor()

        try:
            # 0. Check if this file already exists in the database
            cursor.execute(
                "SELECT id FROM issues WHERE file_path = ?",
                (str(self.current_file_path),)
            )
            if cursor.fetchone() is not None:
                logger.info(f"Skipping: {self.current_file_name} already exists in database")
                return

            logger.info(f"Inserting: {x.series} #{x.issue} vol.{x.volume}")

            # 1. Insert or get series
            cursor.execute(
                "INSERT OR IGNORE INTO series (title) VALUES (?)",
                (x.series,)
            )
            cursor.execute("SELECT id FROM series WHERE title = ?", (x.series,))
            series_id = cursor.fetchone()[0]

            # 2. Insert or get publisher
            publisher_id = None
            if x.publisher:
                cursor.execute(
                    "INSERT OR IGNORE INTO publishers (name, imprint) VALUES (?, ?)",
                    (x.publisher, x.imprint)
                )
                cursor.execute("SELECT id FROM publishers WHERE name = ?", (x.publisher,))
                result = cursor.fetchone()
                publisher_id = result[0] if result else None

            # 3. Insert issue
            cursor.execute(
                """INSERT INTO issues (
                    series_id, publisher_id, issue_number, volume, title,
                    publish_year, publish_month, publish_day, page_count,
                    age_rating, language_iso, community_rating, web_link,
                    scan_information, summary, notes, series_group, format,
                    is_manga, is_black_and_white, main_character_or_team, review,
                    file_path, file_name, file_extension, file_size_kb, has_scanner_page
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    series_id,
                    publisher_id,
                    x.issue,
                    self._to_int(x.volume),
                    x.series,
                    self._to_int(x.year),
                    self._to_int(x.month),
                    self._to_int(x.day),
                    self._to_int(x.page_count),
                    x.age_rating,
                    x.language_iso,
                    self._parse_float(x.community_rating),
                    x.web,
                    x.scan_information,
                    x.summary,
                    x.notes,
                    x.series_group,
                    x.format,
                    1 if x.manga == "Yes" else 0,
                    1 if x.black_and_white == "Yes" else 0,
                    x.main_character_or_team,
                    x.review,
                    str(self.current_file_path),
                    self.current_file_name,
                    self.file_extension,
                    self.file_size,
                    1 if self.scanner != "NA" else 0
                )
            )

            issue_id = cursor.lastrowid

            # 4. Insert pages
            for page in self.pages:
                cursor.execute(
                    """INSERT INTO pages (
                        issue_id, page_number, image_width, image_height,
                        image_size_bytes, page_type, image_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        issue_id,
                        self._to_int(page.get("Image")),
                        self._to_int(page.get("ImageWidth")),
                        self._to_int(page.get("ImageHeight")),
                        self._to_int(page.get("ImageSize")),
                        page.get("Type", "Story"),
                        page.get("ImageHash"),
                    )
                )

            # 5. Insert M2M relationships
            self._insert_m2m_data(cursor, issue_id, x.writer,       "writers",       "issue_writers",       "writer_id")
            self._insert_m2m_data(cursor, issue_id, x.penciller,    "pencilers",     "issue_pencilers",     "penciler_id")
            self._insert_m2m_data(cursor, issue_id, x.inker,        "inkers",        "issue_inkers",        "inker_id")
            self._insert_m2m_data(cursor, issue_id, x.colourist,    "colorists",     "issue_colorists",     "colorist_id")
            self._insert_m2m_data(cursor, issue_id, x.letterer,     "letterers",     "issue_letterers",     "letterer_id")
            self._insert_m2m_data(cursor, issue_id, x.cover_artist, "cover_artists", "issue_cover_artists", "cover_artist_id")
            self._insert_m2m_data(cursor, issue_id, x.editor,       "editors",       "issue_editors",       "editor_id")
            self._insert_m2m_data(cursor, issue_id, x.characters,   "characters",    "issue_characters",    "character_id")
            self._insert_m2m_data(cursor, issue_id, x.locations,    "locations",     "issue_locations",     "location_id")
            self._insert_m2m_data(cursor, issue_id, x.genre,        "genres",        "issue_genres",        "genre_id")
            self._insert_m2m_data(cursor, issue_id, x.teams.split(",") if x.teams else [],         "teams",      "issue_teams",      "team_id")
            self._insert_m2m_data(cursor, issue_id, x.story_arc.split(",") if x.story_arc else [], "story_arcs", "issue_story_arcs", "story_arc_id")

            conn.commit()
            logger.info(f"Successfully inserted: {x.series} #{x.issue}")

        except Exception as e:
            logger.error(f"Error inserting comic book to database: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _insert_m2m_data(self, cursor: sqlite3.Cursor, issue_id: int | None, items: list[str], table_name: str, junction_table: str, fk_column: str) -> None:
        """
        Inserts many-to-many relationships for a list of items.
        Skips UNKNOWN, empty, and whitespace-only values.
        """
        for item in items:
            item = item.strip()
            if not item or item in ("UNKNOWN", "N"):
                continue

            cursor.execute(f"INSERT OR IGNORE INTO {table_name} (name) VALUES (?)", (item,))
            cursor.execute(f"SELECT id FROM {table_name} WHERE name = ?", (item,))
            item_id = cursor.fetchone()[0]

            cursor.execute(
                f"INSERT OR IGNORE INTO {junction_table} (issue_id, {fk_column}) VALUES (?, ?)",
                (issue_id, item_id)
            )
