# start openreview_downloader/cli_utils.py
from pathlib import Path
from typing import Optional


def sanitize_title(title: str) -> str:
    cleaned = "".join(c for c in title if c.isalnum() or c in " _-")
    cleaned = "_".join(cleaned.split())
    return cleaned[:120] or "paper"


def content_value(note, key: str) -> str:
    raw_value = note.content.get(key, "")
    if isinstance(raw_value, dict):
        raw_value = raw_value.get("value") or ""
    return str(raw_value) if raw_value else ""


def presentation_type(note) -> Optional[str]:
    """Return 'oral' or 'spotlight' if the note matches, else None."""
    venue_text = content_value(note, "venue").lower()
    decision_text = content_value(note, "decision").lower()
    combined = f"{venue_text} {decision_text}"
    if "oral" in combined:
        return "oral"
    if "spotlight" in combined:
        return "spotlight"
    return None


def note_decision(note, venue_id: str) -> Optional[str]:
    venueid = content_value(note, "venueid")
    label = presentation_type(note)

    if venueid == venue_id:
        return label or "accepted"

    lowered_vid = venueid.lower()
    if venueid.startswith(f"{venue_id}/") and (
        "reject" in lowered_vid or "desk" in lowered_vid
    ):
        return "rejected"

    combined_text = (
        f"{content_value(note, 'venue')} {content_value(note, 'decision')}".lower()
    )
    if "reject" in combined_text:
        return "rejected"

    return label


def paper_path(note, category: str, base_dir: Path) -> Path:
    """Generate the local file path for a paper note.

    Args:
        note: The OpenReview note object.
        category: The decision category (e.g., 'accepted').
        base_dir: The base download directory.

    Returns:
        Path: The full local path to the PDF.
    """
    title = content_value(note, "title")
    fname_parts = []
    if getattr(note, "number", None) is not None:
        fname_parts.append(f"{note.number:05d}")
    safe_title = sanitize_title(title)
    fname_parts.append(safe_title)
    fname = "_".join([p for p in fname_parts if p]) + ".pdf"
    return base_dir / category / fname


# end openreview_downloader/cli_utils.py
