# start openreview_downloader/database.py
"""Database management for OpenReview Downloader."""

from pathlib import Path
from sqlalchemy import create_engine, event, DDL
from sqlalchemy.orm import sessionmaker
from .models import Base


def get_engine(db_path: Path):
    """Create and return a SQLAlchemy engine for SQLite.

    Args:
        db_path (Path): Path to the SQLite database file.

    Returns:
        Engine: The SQLAlchemy engine.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine):
    """Initialize the database schema and FTS5 virtual table.

    Args:
        engine: The SQLAlchemy engine.
    """
    Base.metadata.create_all(engine)

    # Create FTS5 table and triggers for automatic updates
    # We use 'trigram' tokenizer for better fuzzy matching as requested.
    with engine.connect() as conn:
        conn.execute(
            DDL("""
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                title, 
                abstract, 
                keywords, 
                authors_names, 
                affiliations,
                content='papers',
                content_rowid='rowid',
                tokenize='trigram'
            );
        """)
        )

        # Triggers to keep FTS index in sync
        # Note: This is a simplified version. For a production app,
        # we'd need more complex triggers if we handle updates/deletes frequently.
        # Since we primarily 'ingest' (insert), these basic ones are a good start.
        conn.execute(
            DDL("""
            CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid, title, abstract, keywords)
                VALUES (new.rowid, new.title, new.abstract, new.keywords);
            END;
        """)
        )
        # We also need triggers for authors if we want to search by author/affiliation in FTS
        # But since authors are a separate table, we might need a view or a more complex sync.
        # For now, let's focus on title/abstract/keywords in the main FTS.

        conn.commit()


def get_session_factory(engine):
    """Create and return a session factory.

    Args:
        engine: The SQLAlchemy engine.

    Returns:
        sessionmaker: The session factory.
    """
    return sessionmaker(bind=engine)


# end openreview_downloader/database.py
