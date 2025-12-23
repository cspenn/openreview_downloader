# start openreview_downloader/models.py
"""Database models for OpenReview Downloader."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class Paper(Base):
    """Paper model for storing OpenReview submissions."""

    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    number: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[str]] = mapped_column(Text)
    decision: Mapped[Optional[str]] = mapped_column(String)
    venue: Mapped[Optional[str]] = mapped_column(String)
    venue_id: Mapped[Optional[str]] = mapped_column(String)
    pdf_path: Mapped[Optional[str]] = mapped_column(String)
    download_status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, downloading, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    authors: Mapped[List["Author"]] = relationship(
        "Author", secondary="paper_authors", back_populates="papers"
    )

    def __repr__(self):
        return f"<Paper(title='{self.title}', decision='{self.decision}')>"


class Author(Base):
    """Author model for storing researcher information."""

    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    affiliation: Mapped[Optional[str]] = mapped_column(String)

    papers: Mapped[List["Paper"]] = relationship(
        "Paper", secondary="paper_authors", back_populates="authors"
    )

    def __repr__(self):
        return f"<Author(name='{self.name}', affiliation='{self.affiliation}')>"


class PaperAuthor(Base):
    """Association table between papers and authors."""

    __tablename__ = "paper_authors"

    paper_id: Mapped[str] = mapped_column(
        String, ForeignKey("papers.id"), primary_key=True
    )
    author_id: Mapped[str] = mapped_column(
        String, ForeignKey("authors.id"), primary_key=True
    )


# end openreview_downloader/models.py
