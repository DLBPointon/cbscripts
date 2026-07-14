import json
import os
import io
import sys
import xml
import xml.etree.ElementTree as ET
import zipfile
import rarfile
import pikepdf

import logging
from itertools import count

from PIL import Image
import imagehash

from cbscripts.xml_dataclass import XML_data

logger = logging.getLogger(__name__)

class ComicBook:
    _ids = count(0)
    def __init__(self, file_path, hash_pages=False):
        self.id = next(self._ids)

        self.current_file_path = file_path.absolute()
        self.current_file_name = file_path.name
        self.file_extension = file_path.suffix
        self.file_size = os.path.getsize(file_path) / 1024

        logger.info(f"Processing: {self.current_file_path}")

        if self.file_extension == ".cbz":
            opener = zipfile.ZipFile
            xml_data, page_list = self.read_xml_data(opener)
        elif self.file_extension == ".cbr":
            opener = rarfile.RarFile
            xml_data, page_list = self.read_xml_data(opener)
        elif self.file_extension == ".pdf":
            opener = None
            xml_data, page_list = self.read_pdf_metadata()
        else:
            opener = None
            xml_data, page_list = {}, []

        xml_pages = xml_data.get("pages", [])
        # Pop pages before unpacking - already handled above
        xml_data.pop("pages", None)
        self.xml_data = XML_data(**xml_data)

        # Needs to happen after xml_data is unpacked for nicer log print out
        if hash_pages and opener:
            self.pages, self.scanner = self.check_for_scanner_page(xml_pages, page_list, opener)
        else:
            self.pages, self.scanner = xml_pages, "NA"

        self.collection = self.__iter__()


    def __iter__(self):
        yield from self.__dict__.items()

    def __str__(self):
        txt = io.StringIO()
        txt.write(f"Series: {self.xml_data.series} - Issue: {self.id} -- {self.__class__.__name__}:\n")
        [
            txt.write(f"\t- {a}: {b} \n")
            for a, b in self.collection
            if a not in ["block", "collection", "contents","code_data", "pages"]
        ]
        for item in self.pages:
            txt.write(f"\t- {item} \n")
        txt.write(")")
        return txt.getvalue()


    def read_xml_data(self, opener):
        try:
            xml_data, page_list = self.extract_archive(opener)
            return self.get_data_from_xml(xml_data) if xml_data else {}, page_list
        except Exception as ex:
            logger.error(f"Failed to read XML data: {ex}")
            return {}, []


    def read_pdf_metadata(self):
        try:
            xml_data, page_list = self.extract_pdf()
            return xml_data if xml_data else {}, page_list
        except Exception as ex:
            logger.error(f"Failed to read PDF metadata: {ex}")
            return {}, []


    def extract_pdf(self):
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
            logger.error(f"Failed to extract PDF: {ex}")
            return {}, []


    def extract_pages(self, file_list) -> list:
        return sorted([ i for i in file_list if i.endswith(".jpg") or i.endswith(".png") ])

    def extract_archive(self, opener):
        """Shared extraction logic for CBZ and CBR files."""
        try:
            with opener(self.current_file_path) as rf:
                file_list = rf.namelist()
                logger.debug(file_list)
                data = rf.read("ComicInfo.xml") if "ComicInfo.xml" in file_list else None
                if data:
                    logger.debug(f"Reading ComicInfo.xml from {self.current_file_path}")
                else:
                    logger.debug(f"No ComicInfo.xml found in {self.current_file_path}")
                pages = self.extract_pages(file_list)
        except Exception as ex:
            logger.error(f"Exception w/ file: {self.current_file_path}\nError: {ex}")
            sys.exit(1)
        return data, pages

    def _extract_pages(self, pages_element):
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
            if 'Type' not in page or page['Type'] == '':
                if page_width != 0 and page_width >= double_page_width * 0.9:  # 90% threshold for tolerance
                    page['Type'] = 'DoublePage'

        return pages



    def get_data_from_xml(self, data):
        """Extracts data from the ComicInfo.xml file in a CBZ archive."""
        root = ET.fromstring(data)

        # Map XML tags to dictionary keys, with optional transformations
        TAG_MAPPING = {
            "AgeRating": ("age_rating", str),
            "Series": ("series", str),
            "Publisher": ("publisher", self._process_publisher),
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

    def _process_publisher(self, text: str) -> str:
        """Convert publisher name to underscore format."""
        return "_".join(text.split(" ")) if text else "N"

    def _parse_float(self, value):
        """
        Safely converts a value to float.
        Returns None if the value is invalid or "UNKNOWN".
        """
        if value == "UNKNOWN" or value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Check if it's a valid numeric string
                if value.replace(".", "", 1).replace("-", "", 1).isdigit():
                    return float(value)
        except (ValueError, AttributeError):
            pass
        return None

    def _tag_scanner_page(self, xml_dict: list) -> tuple:
        """
        Tags the scanner page in the XML dictionary if one is detected.
        """

        scanner_dict = json.load(open("/home/dlbpointon/Documents/cbscripts/src/cbscripts/assets/scanner_hash.json"))

        for idx, page in enumerate(xml_dict):
            logger.debug(page)
            for x, y in scanner_dict.items():
                if x == page.get("ImageHash"):
                    xml_dict[idx]["Type"] = "Deleted"
                    logger.info(f"Scanner page detected: {self.xml_data.series} #{self.xml_data.issue} - Page {page['Image']} ({page['FilePath']}) == {y['scanner']} | Page Type is now labelled: {page['Type']}")
                    return xml_dict, y["scanner"]

        return xml_dict, "NA"

    def check_for_scanner_page(self, xml_dict: list, file_list: list, opener) -> tuple[list, str]:
        """
        Checks for scanner pages in the XML data and file list,
        marking them as deleted if found. So we arn't removing scanner information,
        instead just mark the image as deleted so it is ignored in readers.

        Scanner information is moved to the XML.
        """
        if not isinstance(xml_dict, list) or not xml_dict:
            return [], "NA"

        try:
            with opener(self.current_file_path) as z:
                for file_path, page_data in zip(file_list, xml_dict):
                    page_data["FilePath"] = file_path
                    file_hash = imagehash.average_hash(Image.open(z.open(file_path)))
                    page_data["ImageHash"] = str(file_hash)
                    logger.debug(f"Computed hash for page {page_data['Image']}: {file_hash}")
        except Exception as e:
            logger.error(f"Error computing image hashes: {e}")

        return self._tag_scanner_page(xml_dict)


    def _to_none(self, value):
        """Returns None if value is UNKNOWN or empty, otherwise returns the value."""
        if value in ("UNKNOWN", "N", "", None):
            return None
        return value

    def _to_int(self, value):
        """Safely converts a string to int, returns None if not possible."""
        if value in ("UNKNOWN", "N", "", None):
            return None

        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def send_to_sqlite(self, conn):
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

    def _insert_m2m_data(self, cursor, issue_id, items, table_name, junction_table, fk_column):
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
