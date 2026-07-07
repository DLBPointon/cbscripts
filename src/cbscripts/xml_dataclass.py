from dataclasses import dataclass, field


@dataclass
class XML_data:
    # Simple string fields - match keys from TAG_MAPPING in get_data_from_xml
    series:                 str = None
    issue:                  str = None
    volume:                 str = None
    publisher:              str = None
    imprint:                str = None
    year:                   str = None
    month:                  str = None
    day:                    str = None
    age_rating:             str = None
    page_count:             str = None
    web:                    str = None
    language_iso:           str = None
    main_character_or_team: str = None
    review:                 str = None
    community_rating:       str = None
    scan_information:       str = None
    manga:                  str = None
    black_and_white:        str = None
    format:                 str = None
    series_group:           str = None
    summary:                str = None
    notes:                  str = None
    story_arc:              str = None
    teams:                  str = None

    # M2M fields - received as comma-separated strings, split in __post_init__
    writer:       list = field(default_factory=list)
    penciller:    list = field(default_factory=list)
    cover_artist: list = field(default_factory=list)
    editor:       list = field(default_factory=list)
    inker:        list = field(default_factory=list)
    letterer:     list = field(default_factory=list)
    colourist:    list = field(default_factory=list)
    characters:   list = field(default_factory=list)
    locations:    list = field(default_factory=list)
    genre:        list = field(default_factory=list)

    # Pages is a list of dicts, handled separately before instantiation
    pages: list = field(default_factory=list)

    def __post_init__(self):
        # Normalise string fields - convert "N" placeholder to None
        for f in [
            "series", "issue", "volume", "publisher", "imprint", "year", "month",
            "day", "age_rating", "page_count", "web", "language_iso",
            "main_character_or_team", "review", "community_rating", "scan_information",
            "manga", "black_and_white", "format", "series_group", "summary", "notes",
            "story_arc", "teams",
        ]:
            if getattr(self, f) in ("N", "UNKNOWN", ""):
                setattr(self, f, None)

        # Split comma-separated string fields into clean lists for Many 2 Many relationships in DB
        # e.g. "writer1, writer2" -> ["writer1", "writer2"]
        for f in ["writer", "penciller", "cover_artist", "editor", "inker",
                  "letterer", "colourist", "characters", "locations", "genre"]:
            value = getattr(self, f)
            if isinstance(value, str):
                setattr(self, f, [
                    v.strip() for v in value.split(",")
                    if v.strip() and v.strip() not in ("N", "UNKNOWN")
                ])
            elif value is None:
                setattr(self, f, [])
