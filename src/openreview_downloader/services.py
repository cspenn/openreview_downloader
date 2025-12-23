# start openreview_downloader/services.py
"""Business logic and services for OpenReview Downloader."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import openreview  # type: ignore[import-untyped]
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from .models import Paper, Author
from .config import Config

RETRY_CONFIG = {
    "wait": wait_exponential(multiplier=1, min=4, max=60),
    "stop": stop_after_attempt(5),
    "reraise": True,
}


def is_retryable_exception(exception):
    """Determine if an exception should trigger a retry.

    Retries on 429 (Rate Limit), 403, 404, and 5xx errors.
    """
    if not hasattr(exception, "status"):
        # If it's a dict-like exception representation in the message
        msg = str(exception)
        return any(
            f"'status': {code}" in msg for code in [429, 403, 404, 500, 502, 503, 504]
        )

    status = getattr(exception, "status", None)
    return status in [429, 403, 404, 500, 502, 503, 504]


def log_before_sleep(retry_state):
    """Log a warning before sleeping for a retry."""
    if retry_state.outcome.failed:
        ex = retry_state.outcome.exception()
        sleep = getattr(retry_state.next_action, "sleep", 0)
        msg = f"Retrying in {sleep:.1f}s..."
        if "RateLimitError" in str(ex):
            msg = f"Rate limit hit. {msg}"
        logger.warning(msg)


logger = logging.getLogger(__name__)


class OpenReviewService:
    """Service for interacting with the OpenReview API."""

    def __init__(self, config: Config):
        self.config = config
        self.client = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net",
            username=config.credentials.username,
            password=config.credentials.password,
        )

    @retry(
        retry=retry_if_exception(is_retryable_exception),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(10),
        reraise=True,
        before_sleep=log_before_sleep,
    )
    def fetch_notes(self, venue_id: str, need_rejected: bool) -> Tuple[List, List]:
        """Fetch accepted and optionally rejected notes for a venue.

        Args:
            venue_id (str): The OpenReview venue ID.
            need_rejected (bool): Whether to also fetch rejected notes.

        Returns:
            Tuple[List, List]: A tuple of (accepted_notes, rejected_notes).
        """
        accepted = self.client.get_all_notes(content={"venueid": venue_id})
        rejected = []
        if need_rejected:
            # Replaced REJECTED_SUFFIXES from cli.py
            for suffix in ["Rejected_Submission", "Desk_Rejected"]:
                rejected.extend(
                    self.client.get_all_notes(
                        content={"venueid": f"{venue_id}/{suffix}"}
                    )
                )
        return accepted, rejected

    @retry(
        retry=retry_if_exception(is_retryable_exception),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def get_author_profiles(self, author_ids: List[str]) -> Dict[str, Dict]:
        """Fetch profiles for authors to get affiliations.

        Args:
            author_ids (List[str]): List of author profile IDs or emails.

        Returns:
            Dict[str, Dict]: Dictionary mapping author ID to profile data.
        """
        profiles: Dict[str, Dict] = {}
        if not author_ids:
            return profiles

        # OpenReview API supports fetching multiple profiles
        # OpenReview API supports fetching multiple profiles
        profile_list = self.client.search_profiles(ids=author_ids)
        for profile in profile_list:
            profiles[profile.id] = {
                "name": profile.get_preferred_name(),
                "affiliation": self._extract_affiliation(profile),
            }

        return profiles

    def _extract_affiliation(self, profile) -> Optional[str]:
        """Extract current affiliation from profile."""
        if hasattr(profile, "content") and "history" in profile.content:
            history = profile.content["history"]
            if history:
                # Usually the first entry is the most recent
                current = history[0]
                institution = current.get("institution", {})
                return institution.get("name")
        return None


class DownloadService:
    """Service for downloading paper PDFs with retry logic."""

    def __init__(self, config: Config):
        self.config = config

    @retry(
        retry=retry_if_exception(is_retryable_exception),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(10),
        reraise=True,
        before_sleep=log_before_sleep,
    )
    def download_pdf(
        self, client: openreview.api.OpenReviewClient, note_id: str, dest_path: Path
    ):
        """Download PDF using OpenReview client with retry logic."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        pdf_bytes = client.get_attachment(field_name="pdf", id=note_id)
        tmp_path.write_bytes(pdf_bytes)
        tmp_path.replace(dest_path)


class IngestionService:
    """Service for ingesting paper metadata and authors into the database."""

    def __init__(self, db_session: Session, or_service: OpenReviewService):
        self.db_session = db_session
        self.or_service = or_service

    def ingest_paper(self, note, category: str, pdf_path: Path):
        """Ingest paper metadata and authors into database.

        Args:
            note: The OpenReview note object.
            category (str): The paper category/decision.
            pdf_path (Path): Path to the saved PDF file.
        """
        metadata = self._extract_metadata(note)

        # Check if paper already exists
        paper = self.db_session.query(Paper).filter_by(id=note.id).first()
        if not paper:
            paper = Paper(
                id=note.id,
                number=metadata["number"],
                title=metadata["title"],
                abstract=metadata["abstract"],
                keywords=metadata["keywords"],
                decision=category,
                venue=metadata["venue"],
                venue_id=metadata["venue_id"],
                pdf_path=str(pdf_path),
                download_status="completed",
            )
            self.db_session.add(paper)
        else:
            paper.download_status = "completed"
            paper.pdf_path = str(pdf_path)

        # Handle authors
        self._process_authors(paper, metadata["author_ids"], metadata["author_names"])
        self.db_session.commit()

    def _extract_metadata(self, note) -> Dict:
        """Extract metadata from an OpenReview note."""
        content = note.content

        def get_val(key):
            val = content.get(key, "")
            return val.get("value") if isinstance(val, dict) else val

        keywords = get_val("keywords")
        if isinstance(keywords, list):
            keywords_str = ", ".join(keywords)
        else:
            keywords_str = str(keywords) if keywords else ""

        return {
            "title": get_val("title"),
            "abstract": get_val("abstract"),
            "keywords": keywords_str,
            "venue": get_val("venue"),
            "venue_id": get_val("venueid"),
            "number": int(getattr(note, "number", 0))
            if getattr(note, "number", None)
            else None,
            "author_ids": get_val("authorids") or [],
            "author_names": get_val("authors") or [],
        }

    def _process_authors(
        self, paper: Paper, author_ids: List[str], author_names: List[str]
    ):
        """Process and link authors to a paper."""
        profiles: Dict[str, Dict] = {}
        if author_ids:
            profiles = self.or_service.get_author_profiles(author_ids)

        for i, aid in enumerate(author_ids):
            name = author_names[i] if i < len(author_names) else aid
            author = self.db_session.query(Author).filter_by(id=aid).first()

            profile_data = profiles.get(aid, {})
            affiliation = profile_data.get("affiliation")

            if not author:
                author = Author(id=aid, name=name, affiliation=affiliation)
                self.db_session.add(author)
            elif affiliation:
                author.affiliation = affiliation

            # Link paper and author
            if author not in paper.authors:
                paper.authors.append(author)


# end openreview_downloader/services.py
