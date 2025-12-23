# start openreview_downloader/cli.py
"""CLI module for OpenReview Downloader."""

import argparse
import logging
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm

from .config import Config
from .database import get_engine, init_db, get_session_factory
from .services import OpenReviewService, DownloadService, IngestionService
from .cli_utils import note_decision, paper_path

# Setup logging according to standards
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_dir / "ordl.log")],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Download OpenReview papers by decision."
    )
    parser.add_argument(
        "decisions",
        nargs="?",
        help="Comma-separated list of decisions to download (oral,spotlight,accepted,rejected).",
    )
    parser.add_argument(
        "--venue-id",
        help="OpenReview venue id.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Output directory.",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print decision counts for the venue and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    # Load configuration
    config = Config.load(Path("config.yml"), Path("credentials.yml"))
    args = parse_args()

    _merge_cli_args(config, args)

    # Initialize database
    engine = get_engine(config.downloader.db_path)
    init_db(engine)
    session_factory = get_session_factory(engine)

    # Initialize services
    or_service = OpenReviewService(config)
    dl_service = DownloadService(config)

    logger.info("🟢 Fetching submissions for %s...", config.downloader.venue_id)
    need_rejected = args.info or "rejected" in config.downloader.decisions
    accepted, rejected = or_service.fetch_notes(
        config.downloader.venue_id, need_rejected
    )

    if args.info:
        _print_venue_info(config, accepted, rejected)
        return

    to_process = _filter_targets(config, accepted, rejected)
    logger.info("🟢 Found %d papers to process.", len(to_process))

    _process_targets(to_process, session_factory, or_service, dl_service)
    logger.info("✅ Done. Files saved and metadata ingested.")


def _merge_cli_args(config: Config, args: argparse.Namespace):
    """Override config with CLI arguments."""
    if args.venue_id:
        config.downloader.venue_id = args.venue_id
    if args.out_dir:
        config.downloader.out_dir = args.out_dir
    if args.decisions:
        config.downloader.decisions = [d.strip() for d in args.decisions.split(",")]


def _print_venue_info(config, accepted, rejected):
    """Print summary information about the venue."""
    print(f"Venue: {config.downloader.venue_id}")
    print(f"Accepted: {len(accepted)}")
    print(f"Rejected: {len(rejected)}")


def _filter_targets(config, accepted, rejected) -> List[Tuple]:
    """Filter and determine which notes to process."""
    to_process = []
    requested = set(config.downloader.decisions)

    for note in accepted:
        label = note_decision(note, config.downloader.venue_id)
        if label and label in requested:
            dest = paper_path(note, label, config.downloader.out_dir)
            to_process.append((note, label, dest))

    for note in rejected:
        if "rejected" in requested:
            dest = paper_path(note, "rejected", config.downloader.out_dir)
            to_process.append((note, "rejected", dest))

    return to_process


def _process_targets(to_process, session_factory, or_service, dl_service):
    """Process all target papers in a loop."""
    with session_factory() as session:
        ingest_service = IngestionService(session, or_service)
        for note, category, path in tqdm(to_process, desc="Processing", unit="paper"):
            # Check if already completed in DB
            from .models import Paper

            existing = session.query(Paper).filter_by(id=note.id).first()
            if existing and existing.download_status == "completed" and path.exists():
                continue

            try:
                # 1. Download
                dl_service.download_pdf(or_service.client, note.id, path)
                # 2. Ingest
                ingest_service.ingest_paper(note, category, path)
            except Exception as e:
                logger.error("🛑 Failed to process %s: %s", note.id, e)


if __name__ == "__main__":
    main()
# end openreview_downloader/cli.py


if __name__ == "__main__":
    main()
