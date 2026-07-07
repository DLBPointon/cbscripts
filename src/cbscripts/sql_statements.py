"""
AI generated SQL statements for the cbscripts_v2 database schema.
Reviewed by human on 26-06-2026
"""

statements = {
    # Base tables first (no foreign key dependencies)
    "create_series_table": """
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,

    "create_publisher_table": """
        CREATE TABLE IF NOT EXISTS publishers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            imprint TEXT
        );
    """,

    # Main issue table (depends on series and publisher)
    "create_issue_table": """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            publisher_id INTEGER,
            issue_number TEXT NOT NULL,
            volume INTEGER,
            title TEXT,
            publish_year INTEGER,
            publish_month INTEGER,
            publish_day INTEGER,
            page_count INTEGER,
            age_rating TEXT,
            language_iso TEXT,
            community_rating REAL,
            web_link TEXT,
            scan_information TEXT,
            summary TEXT,
            notes TEXT,
            series_group TEXT,
            format TEXT,
            is_manga BOOLEAN DEFAULT 0,
            is_black_and_white BOOLEAN DEFAULT 0,
            main_character_or_team TEXT,
            review TEXT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_extension TEXT,
            file_size_kb REAL,
            has_scanner_page BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (series_id) REFERENCES series(id),
            FOREIGN KEY (publisher_id) REFERENCES publishers(id),
            UNIQUE(series_id, issue_number, volume, format)
        );
    """,

    # Pages table (depends on issues)
    "create_pages_table": """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            image_width INTEGER,
            image_height INTEGER,
            image_size_bytes INTEGER,
            page_type TEXT,
            image_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            UNIQUE(issue_id, page_number)
        );
    """,

    # M2M base tables (no dependencies)
    "create_writers_table": """
        CREATE TABLE IF NOT EXISTS writers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_pencilers_table": """
        CREATE TABLE IF NOT EXISTS pencilers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_inkers_table": """
        CREATE TABLE IF NOT EXISTS inkers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_colorists_table": """
        CREATE TABLE IF NOT EXISTS colorists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_letterers_table": """
        CREATE TABLE IF NOT EXISTS letterers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_cover_artists_table": """
        CREATE TABLE IF NOT EXISTS cover_artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_editors_table": """
        CREATE TABLE IF NOT EXISTS editors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_characters_table": """
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_main_character BOOLEAN DEFAULT 0
        );
    """,

    "create_locations_table": """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_teams_table": """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_story_arcs_table": """
        CREATE TABLE IF NOT EXISTS story_arcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    "create_genres_table": """
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """,

    # M2M junction tables (depend on issues and their respective base tables)
    "create_issue_writers": """
        CREATE TABLE IF NOT EXISTS issue_writers (
            issue_id INTEGER NOT NULL,
            writer_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, writer_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (writer_id) REFERENCES writers(id)
        );
    """,

    "create_issue_pencilers": """
        CREATE TABLE IF NOT EXISTS issue_pencilers (
            issue_id INTEGER NOT NULL,
            penciler_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, penciler_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (penciler_id) REFERENCES pencilers(id)
        );
    """,

    "create_issue_inkers": """
        CREATE TABLE IF NOT EXISTS issue_inkers (
            issue_id INTEGER NOT NULL,
            inker_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, inker_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (inker_id) REFERENCES inkers(id)
        );
    """,

    "create_issue_colorists": """
        CREATE TABLE IF NOT EXISTS issue_colorists (
            issue_id INTEGER NOT NULL,
            colorist_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, colorist_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (colorist_id) REFERENCES colorists(id)
        );
    """,

    "create_issue_letterers": """
        CREATE TABLE IF NOT EXISTS issue_letterers (
            issue_id INTEGER NOT NULL,
            letterer_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, letterer_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (letterer_id) REFERENCES letterers(id)
        );
    """,

    "create_issue_cover_artists": """
        CREATE TABLE IF NOT EXISTS issue_cover_artists (
            issue_id INTEGER NOT NULL,
            cover_artist_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, cover_artist_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (cover_artist_id) REFERENCES cover_artists(id)
        );
    """,

    "create_issue_editors": """
        CREATE TABLE IF NOT EXISTS issue_editors (
            issue_id INTEGER NOT NULL,
            editor_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, editor_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (editor_id) REFERENCES editors(id)
        );
    """,

    "create_issue_characters": """
        CREATE TABLE IF NOT EXISTS issue_characters (
            issue_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, character_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        );
    """,

    "create_issue_locations": """
        CREATE TABLE IF NOT EXISTS issue_locations (
            issue_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, location_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations(id)
        );
    """,

    "create_issue_teams": """
        CREATE TABLE IF NOT EXISTS issue_teams (
            issue_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, team_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
    """,

    "create_issue_story_arcs": """
        CREATE TABLE IF NOT EXISTS issue_story_arcs (
            issue_id INTEGER NOT NULL,
            story_arc_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, story_arc_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (story_arc_id) REFERENCES story_arcs(id)
        );
    """,

    "create_issue_genres": """
        CREATE TABLE IF NOT EXISTS issue_genres (
            issue_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, genre_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (genre_id) REFERENCES genres(id)
        );
    """,

    # Indexes for common queries - each as a separate statement
    "create_index_issues_series_id": """
        CREATE INDEX IF NOT EXISTS idx_issues_series_id ON issues(series_id);
    """,

    "create_index_issues_publisher_id": """
        CREATE INDEX IF NOT EXISTS idx_issues_publisher_id ON issues(publisher_id);
    """,

    "create_index_pages_issue_id": """
        CREATE INDEX IF NOT EXISTS idx_pages_issue_id ON pages(issue_id);
    """,

    "create_index_issue_writers_issue_id": """
        CREATE INDEX IF NOT EXISTS idx_issue_writers_issue_id ON issue_writers(issue_id);
    """,

    "create_index_issue_characters_issue_id": """
        CREATE INDEX IF NOT EXISTS idx_issue_characters_issue_id ON issue_characters(issue_id);
    """,
}
