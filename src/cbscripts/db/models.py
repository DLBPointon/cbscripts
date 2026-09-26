from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm.properties import ForeignKey


class Base(DeclarativeBase):
    pass


class Comic(Base):
    __tablename__ = "series"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    created: Mapped[datetime] = mapped_column(default=datetime.now)
    updated: Mapped[datetime] = mapped_column(default=datetime.now)

    def __repr__(self) -> str:
        return f"Comic(id={self.id!r}, title={self.title!r})"


class Publisher(Base):
    __tablename__ = "publishers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    imprint: Mapped[str]


class Issues(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    number: Mapped[int]
    volume: Mapped[int]
    published_year: Mapped[int]
    published_month: Mapped[int]
    published_day: Mapped[int]
    page_count: Mapped[int]
    age_rating: Mapped[str]
    language_iso: Mapped[str]
    community_rating: Mapped[str]
    is_manga: Mapped[bool]
    is_black_and_white: Mapped[bool]
    main_character_or_team: Mapped[str]
    review: Mapped[str]
    scanner_page: Mapped[bool]
    is_duplicate: Mapped[bool]
    weblink: Mapped[str]
    scan_information: Mapped[str]
    summary: Mapped[str]
    notes: Mapped[str]
    series_group: Mapped[str]
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
    created: Mapped[datetime] = mapped_column(default=datetime.now)
    updated: Mapped[datetime] = mapped_column(default=datetime.now)

    def __repr__(self) -> str:
        return f"Issues(id={self.id!r}, title={self.title!r}, number={self.number!r}, volume={self.volume!r})"


class IssueData(Base):
    __tablename__ = "issue_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"))
    path: Mapped[str]
    new_path: Mapped[str]
    name: Mapped[str]
    size_kb: Mapped[int]
    format: Mapped[str]

    def __repr__(self) -> str:
        return (
            f"IssueData(id={self.id!r}, name={self.name!r}, size_kb={self.size_kb!r})"
        )


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"))
    page_number: Mapped[int]
    image_width: Mapped[int]
    image_height: Mapped[int]
    image_bytes: Mapped[int]
    page_type: Mapped[str]

    def __repr__(self) -> str:
        return f"Page(id={self.id!r}, page_number={self.page_number!r}, image_width={self.image_width!r}, image_height={self.image_height!r}, image_bytes={self.image_bytes!r}, page_type={self.page_type!r})"


class People(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]

    def __repr__(self) -> str:
        return f"People(id={self.id!r}, name={self.name!r}, role={self.role!r})"


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    is_main: Mapped[bool]

    def __repr__(self) -> str:
        return (
            f"Character(id={self.id!r}, name={self.name!r}, is_main={self.is_main!r})"
        )


class GenericMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Location(Base, GenericMixin):
    __tablename__ = "locations"

    def __repr__(self) -> str:
        return f"Location(id={self.id!r}, name={self.name!r})"


class Team(Base, GenericMixin):
    __tablename__ = "teams"

    def __repr__(self) -> str:
        return f"Team(id={self.id!r}, name={self.name!r})"


class StoryArc(Base, GenericMixin):
    __tablename__ = "story_arcs"

    def __repr__(self) -> str:
        return f"StoryArc(id={self.id!r}, name={self.name!r})"


class Genre(Base, GenericMixin):
    __tablename__ = "genres"

    def __repr__(self) -> str:
        return f"Genre(id={self.id!r}, name={self.name!r})"


# M2M Junction Tables


class IssuePeople(Base):
    __tablename__ = "issue_people"
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), primary_key=True)


class CharacterIssue(Base):
    __tablename__ = "issues_characters"
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"), primary_key=True
    )
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), primary_key=True)


class GenreIssue(Base):
    __tablename__ = "issues_genres"
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id"), primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), primary_key=True)
