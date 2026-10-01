from datetime import datetime

from sqlalchemy import ForeignKey, and_, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------


class Comic(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]

    created: Mapped[datetime] = mapped_column(default=datetime.now)
    updated: Mapped[datetime] = mapped_column(default=datetime.now)

    issues: Mapped[list["Issues"]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
    )

    # Hybrid property for counting ready-to-move issues
    # This is a Python way of getting a number for Comic
    @hybrid_property
    def ready_to_move_py(self) -> int:
        """Count of associated IssueData records where path != new_path"""
        return sum(
            1
            for issue in self.issues
            for data in issue.issue_data
            if data.path != data.new_path
        )

    # Hybrid property for counting ready-to-move issues
    # This is an SQL way of doing the same this as above
    # It also uses the above as the base for the expression
    # Should be able to use it like:
    # session.query(Comic).filter(Comic.ready_to_move > 0).all()
    @ready_to_move_py.expression
    @classmethod
    def ready_to_move(cls):
        """SQL expression for querying comics by ready_to_move count"""
        return (
            select(func.count(1))
            .select_from(Issues)
            .join(IssueData)
            .where(
                and_(
                    Issues.series_id == cls.id,
                    IssueData.path != IssueData.new_path,
                )
            )
            .correlate(cls)
            .scalar_subquery()
        )

    def __repr__(self) -> str:
        return f"Comic(id={self.id!r}, title={self.title!r})"


# This will need to be searched based on the series name
# And then filtered on the year
# Similarity score might need to be a thing too.
# ---
# Can we do something with the issue.web link?
# - can we get the series information if we only have the issue.web link?
# - this would mean we can rely on that, hoping that issue.id == 1 is always correct
# - This would also mean that we expect all issues going into cbscripts to have already
# - gone through comictagger
# class ComicVine(Base):
#     __tablename__ = "comic_vine"
#
#     id: Mapped[int] = mapped_column(primary_key=True, foreign_key=foreign(Comic.id))
#     req_sent: Mapped[bool] = mapped_column(default=False)
#     updated: Mapped[datetime] = mapped_column(default=datetime.now)
#     count_of_episodes: Mapped[int] = mapped_column(default=0)


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    imprint: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        back_populates="publisher",
    )

    def __repr__(self) -> str:
        return f"Publisher(id={self.id!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


class Issues(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)

    issue: Mapped[int]
    volume: Mapped[int]
    year: Mapped[int]
    month: Mapped[int]
    day: Mapped[int]
    web: Mapped[str]
    page_count: Mapped[int]
    age_rating: Mapped[str]
    language_iso: Mapped[str]
    community_rating: Mapped[str]
    is_manga: Mapped[bool]
    is_black_and_white: Mapped[bool]
    main_character_or_team: Mapped[str]
    review: Mapped[str]
    scanner_group: Mapped[str]
    is_duplicate: Mapped[bool]
    scanner_hash_difference: Mapped[str]
    summary: Mapped[str]
    notes: Mapped[str]
    series_group: Mapped[str]

    # Foreign keys
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))

    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))

    story_arc_id: Mapped[int | None] = mapped_column(
        ForeignKey("story_arcs.id"),
        nullable=True,
    )

    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
    )

    # Relationships
    series: Mapped["Comic"] = relationship(
        back_populates="issues",
    )

    publisher: Mapped["Publisher"] = relationship(
        back_populates="issues",
    )

    story_arc: Mapped["StoryArc | None"] = relationship(
        back_populates="issues",
    )

    team: Mapped["Team | None"] = relationship(
        back_populates="issues",
    )

    issue_data: Mapped[list["IssueData"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
    )

    pages: Mapped[list["Page"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
    )

    people: Mapped[list["People"]] = relationship(
        secondary="issue_people",
        back_populates="issues",
    )

    characters: Mapped[list["Character"]] = relationship(
        secondary="issues_characters",
        back_populates="issues",
    )

    genres: Mapped[list["Genre"]] = relationship(
        secondary="issues_genres",
        back_populates="issues",
    )

    locations: Mapped[list["Location"]] = relationship(
        secondary="issues_locations",
        back_populates="issues",
    )

    def __repr__(self) -> str:
        return (
            f"Issues("
            f"id={self.id!r}, "
            f"series={self.series.title!r}, "
            f"number={self.issue!r}, "
            f"volume={self.volume!r}"
            f")"
        )


# ---------------------------------------------------------------------------
# Issue file data
# ---------------------------------------------------------------------------


class IssueData(Base):
    __tablename__ = "issue_data"

    id: Mapped[int] = mapped_column(primary_key=True)

    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"))

    path: Mapped[str]
    new_path: Mapped[str]
    name: Mapped[str]
    size_kb: Mapped[int]
    format: Mapped[str]

    issue: Mapped["Issues"] = relationship(
        back_populates="issue_data",
    )

    def __repr__(self) -> str:
        return (
            f"IssueData(id={self.id!r}, name={self.name!r}, size_kb={self.size_kb!r})"
        )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)

    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"))

    image: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    path: Mapped[str]
    size: Mapped[int]
    hash: Mapped[str] = mapped_column(nullable=True)
    type: Mapped[str]

    issue: Mapped["Issues"] = relationship(
        back_populates="pages",
    )

    def __repr__(self) -> str:
        return (
            f"Page("
            f"id={self.id!r}, "
            f"page_number={self.image!r}, "
            f"image_width={self.width!r}, "
            f"image_height={self.height!r}, "
            f"image_bytes={self.size!r}, "
            f"page_type={self.type!r}"
            f")"
        )


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class People(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        secondary="issue_people",
        back_populates="people",
    )

    def __repr__(self) -> str:
        return f"People(id={self.id!r}, name={self.name!r}, role={self.role!r})"


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    is_main: Mapped[bool]

    issues: Mapped[list["Issues"]] = relationship(
        secondary="issues_characters",
        back_populates="characters",
    )

    def __repr__(self) -> str:
        return (
            f"Character(id={self.id!r}, name={self.name!r}, is_main={self.is_main!r})"
        )


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        secondary="issues_locations",
        back_populates="locations",
    )

    def __repr__(self) -> str:
        return f"Location(id={self.id!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        back_populates="team",
    )

    def __repr__(self) -> str:
        return f"Team(id={self.id!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Story arcs
# ---------------------------------------------------------------------------


class StoryArc(Base):
    __tablename__ = "story_arcs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        back_populates="story_arc",
    )

    def __repr__(self) -> str:
        return f"StoryArc(id={self.id!r}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Genres
# ---------------------------------------------------------------------------


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    issues: Mapped[list["Issues"]] = relationship(
        secondary="issues_genres",
        back_populates="genres",
    )

    def __repr__(self) -> str:
        return f"Genre(id={self.id!r}, name={self.name!r})"


# ===========================================================================
# Association tables
# ===========================================================================


class IssuePeople(Base):
    __tablename__ = "issue_people"

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
        primary_key=True,
    )

    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id"),
        primary_key=True,
    )


class CharacterIssue(Base):
    __tablename__ = "issues_characters"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"),
        primary_key=True,
    )

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
        primary_key=True,
    )


class GenreIssue(Base):
    __tablename__ = "issues_genres"

    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id"),
        primary_key=True,
    )

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
        primary_key=True,
    )


class LocationIssue(Base):
    __tablename__ = "issues_locations"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"),
        primary_key=True,
    )

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
        primary_key=True,
    )
