import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session

from cbscripts.comic_class import ComicBook
from cbscripts.db.models import (
    Character,
    Comic,
    Genre,
    IssueData,
    Issues,
    Location,
    Page,
    People,
    Publisher,
    StoryArc,
    Team,
)

logger = logging.getLogger(__name__)


def get_publisher_data(session: Session, comic: ComicBook) -> Publisher:
    """
    Organising the publisher data from the db and comicbook to make sure
    we don't have duplicate publishers in the db.
    """
    publisher_data = session.scalar(
        # Select the Publisher table and check values for existence
        sa.select(Publisher).where(Publisher.name == comic.xml_data.publisher)
    )

    if publisher_data is None:
        # If the publisher doesn't exist, create a new entry
        publisher_data = Publisher(
            name=comic.xml_data.publisher,
            imprint=comic.xml_data.imprint,
        )

    return publisher_data


def get_people(comic: ComicBook) -> list[People]:
    """
    Extracting the people data from the comicbook and converting it into
    a list of People objects.
    """
    people_dict = {
        "editor": comic.xml_data.editor,
        "writer": comic.xml_data.writer,
        "penciller": comic.xml_data.penciller,
        "inker": comic.xml_data.inker,
        "colourist": comic.xml_data.colourist,
        "letterer": comic.xml_data.letterer,
    }

    actual_people = []
    for job, people_list in people_dict.items():
        actual_people += [People(name=person, role=job) for person in people_list]
    return actual_people


def to_db(comic: ComicBook, db_session: sa.Engine) -> None:
    """
    Convert the ComicBook class into SQLAlchemy model and save it to the database.
    """

    with Session(db_session) as session:
        existing_comic = session.scalar(
            sa.select(Issues, IssueData)
            .join(IssueData, IssueData.issue_id == Issues.id)
            .where(Comic.title == comic.xml_data.series)
            .where(Issues.issue == comic.xml_data.issue)
            .where(IssueData.path == str(comic.current_file_path))
        )

        duplicate = False
        if existing_comic is not None:
            logger.info(f"Already in database: {existing_comic}")
        else:
            duplicate = True

        comic_data = session.scalar(
            sa.select(Comic).where(Comic.title == comic.xml_data.series)
        )

        if comic_data is None:
            comic_data = Comic(title=comic.xml_data.series)
            session.add(comic_data)

        publisher_data = get_publisher_data(session, comic)

        team_data = Team(name=comic.xml_data.teams) if comic.xml_data.teams else None

        story_arc_data = (
            StoryArc(name=comic.xml_data.story_arc)
            if comic.xml_data.story_arc
            else None
        )

        issue = Issues(
            issue=comic.xml_data.issue,
            volume=comic.xml_data.volume,
            year=comic.xml_data.year,
            month=comic.xml_data.month,
            day=comic.xml_data.day,
            web=comic.xml_data.web,
            page_count=comic.xml_data.page_count,
            age_rating=comic.xml_data.age_rating,
            language_iso=comic.xml_data.language_iso,
            community_rating=comic.xml_data.community_rating,
            is_manga=comic.xml_data.manga,
            is_black_and_white=comic.xml_data.black_and_white,
            main_character_or_team=comic.xml_data.main_character_or_team,
            review=comic.xml_data.review,
            scanner_group=comic.scanner,
            is_duplicate=duplicate,
            scanner_hash_difference=comic.diff_hash,
            summary=comic.xml_data.summary,
            notes=comic.xml_data.notes,
            series_group=comic.xml_data.series_group,
            series=comic_data,
            publisher=publisher_data,
            team=team_data,
            story_arc=story_arc_data,
        )

        issue.issue_data = [
            IssueData(
                path=str(comic.current_file_path),
                new_path=comic.proposed_file_path,
                name=comic.proposed_file_name,
                size_kb=comic.file_size,
                format=comic.file_extension,
            )
        ]

        issue.pages = [Page(**vars(page)) for page in comic.pages]

        issue.people = get_people(comic)

        issue.characters = [
            Character(
                name=character,
                is_main=False,
            )
            for character in comic.xml_data.characters
        ]

        issue.genres = [Genre(name=genre) for genre in comic.xml_data.genre]

        issue.locations = [
            Location(name=location) for location in comic.xml_data.locations
        ]

        session.add(issue)
        session.commit()

        print(issue)
