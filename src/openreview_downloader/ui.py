# start openreview_downloader/ui.py
"""PySide6 User Interface for OpenReview Downloader."""

import sys
import os
import logging
import subprocess  # nosec
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QLabel,
    QProgressBar,
    QMessageBox,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from sqlalchemy import text
from .config import Config
from .database import get_engine, get_session_factory, init_db
from .models import Paper
from .services import OpenReviewService, DownloadService, IngestionService
from .cli_utils import note_decision, paper_path


class LogSignalHandler(logging.Handler):
    """Log handler that emits messages via a Qt Signal."""

    def __init__(self, signal, worker):
        super().__init__()
        self.signal = signal
        self.worker = worker

    def emit(self, record):
        msg = self.format(record)
        # We only want to bubble up retry messages
        if "Retrying" in msg:
            # Emit current progress state with new message
            self.signal.emit(self.worker.last_current, self.worker.last_total, msg)


class DownloadWorker(QThread):
    """Worker thread for downloading papers without blocking the UI."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal()
    error = Signal(str)

    def __init__(self, config: Config, decisions: List[str]):
        super().__init__()
        self.config = config
        self.decisions = decisions
        self._is_paused = False
        self._is_stopped = False
        self.last_current = 0
        self.last_total = 0

    def pause(self):
        """Pause the download process."""
        self._is_paused = True

    def resume(self):
        """Resume the download process."""
        self._is_paused = False

    def stop(self):
        """Stop the download process."""
        self._is_stopped = True

    def run(self):
        """Execute the download and ingestion process."""
        # Setup log handler to capture retry messages
        services_logger = logging.getLogger("openreview_downloader.services")
        log_handler = LogSignalHandler(self.progress, self)
        services_logger.addHandler(log_handler)

        try:
            engine = get_engine(self.config.downloader.db_path)
            self.session_factory = get_session_factory(engine)
            self.or_service = OpenReviewService(self.config)
            self.dl_service = DownloadService(self.config)

            self.progress.emit(0, 100, "Fetching notes...")
            to_process = self._get_to_process()

            total = len(to_process)
            for i, (note, category, path) in enumerate(to_process):
                if not self._check_should_continue():
                    break

                self.last_current = i
                self.last_total = total
                self.progress.emit(i, total, f"Downloading {note.id}...")
                self._process_single_paper(note, category, path)

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            services_logger.removeHandler(log_handler)

    def _get_to_process(self):
        """Determine papers to download and ingest."""
        accepted, rejected = self.or_service.fetch_notes(
            self.config.downloader.venue_id, "rejected" in self.decisions
        )
        to_process = []
        requested = set(self.decisions)
        for note in accepted:
            label = note_decision(note, self.config.downloader.venue_id)
            if label in requested:
                dest = paper_path(note, label, self.config.downloader.out_dir)
                to_process.append((note, label, dest))
        for note in rejected:
            if "rejected" in requested:
                dest = paper_path(note, "rejected", self.config.downloader.out_dir)
                to_process.append((note, "rejected", dest))
        return to_process

    def _check_should_continue(self) -> bool:
        """Check if worker should stop or wait while paused."""
        if self._is_stopped:
            return False
        while self._is_paused:
            if self._is_stopped:
                return False
            self.msleep(100)
        return True

    def _process_single_paper(self, note, category, path):
        """Process a single paper: download and ingest."""
        with self.session_factory() as session:
            ingest_service = IngestionService(session, self.or_service)
            existing = session.query(Paper).filter_by(id=note.id).first()
            if existing and existing.download_status == "completed" and path.exists():
                return

            try:
                self.dl_service.download_pdf(self.or_service.client, note.id, path)
                ingest_service.ingest_paper(note, category, path)
            except Exception as e:
                self.error.emit(f"Failed {note.id}: {str(e)}")


class SearchWorker(QThread):
    """Worker thread for searching papers in the database."""

    results = Signal(list)

    def __init__(self, config: Config, query: str, mode: str):
        super().__init__()
        self.config = config
        self.query = query
        self.mode = mode  # "exact" or "fuzzy"

    def run(self):
        """Execute the search query against the database."""
        engine = get_engine(self.config.downloader.db_path)
        session_factory = get_session_factory(engine)

        with session_factory() as session:
            if self.mode == "fuzzy":
                # Use FTS5 trigram search
                # We search in the virtual table papers_fts
                sql = """
                SELECT p.id, p.title, p.pdf_path 
                FROM papers p
                JOIN papers_fts f ON p.id = f.rowid
                WHERE papers_fts MATCH :query
                ORDER BY rank
                """
                # For trigram, we might want to wrap the query or use a specific syntax
                # but FTS5 MATCH usually works well with simple terms.
                res = session.execute(text(sql), {"query": self.query}).fetchall()
            else:
                # Exact/Like search
                res = (
                    session.query(Paper)
                    .filter(Paper.title.ilike(f"%{self.query}%"))
                    .all()
                )
                res = [(p.id, p.title, p.pdf_path) for p in res]

            self.results.emit(res)


class MainWindow(QMainWindow):
    """Main window of the OpenReview Downloader application."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.worker = None
        self.search_worker = None
        self.setWindowTitle("OpenReview Downloader")
        self.resize(800, 600)
        self.apply_theme()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.setup_download_tab()
        self.setup_search_tab()

    def apply_theme(self):
        """Apply the light or dark theme based on configuration."""
        if self.config.downloader.theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #efefef; }
                QPushButton { background-color: #3c3f41; border: 1px solid #555; padding: 5px; border-radius: 3px; }
                QPushButton:hover { background-color: #4c5052; }
                QLineEdit { background-color: #3c3f41; border: 1px solid #555; color: white; padding: 5px; }
                QListWidget { background-color: #3c3f41; border: 1px solid #555; }
                QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; }
                QProgressBar::chunk { background-color: #05B8CC; }
            """)
        else:
            self.setStyleSheet("")  # Use default light theme

    def setup_download_tab(self):
        """Initialize the download management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Config section
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Venue ID:"))
        self.venue_input = QLineEdit(self.config.downloader.venue_id)
        h_layout.addWidget(self.venue_input)
        layout.addLayout(h_layout)

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Decisions:"))
        self.decisions_input = QLineEdit(",".join(self.config.downloader.decisions))
        h_layout.addWidget(self.decisions_input)
        layout.addLayout(h_layout)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Download")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.stop_btn = QPushButton("Stop")

        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.pause_btn)
        ctrl_layout.addWidget(self.resume_btn)
        ctrl_layout.addWidget(self.stop_btn)
        layout.addLayout(ctrl_layout)

        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        self.tabs.addTab(tab, "Download")

        # Events
        self.start_btn.clicked.connect(self.start_download)
        self.pause_btn.clicked.connect(self.pause_download)
        self.resume_btn.clicked.connect(self.resume_download)
        self.stop_btn.clicked.connect(self.stop_download)

    def setup_search_tab(self):
        """Initialize the paper search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search titles, abstracts, authors...")
        self.search_btn = QPushButton("Search")
        self.search_mode = QComboBox()
        self.search_mode.addItems(["Fuzzy (FTS5)", "Exact"])
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_mode)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.open_pdf_btn = QPushButton("Open PDF")
        layout.addWidget(self.open_pdf_btn)

        self.tabs.addTab(tab, "Search")

        # Events
        self.search_btn.clicked.connect(self.perform_search)
        self.open_pdf_btn.clicked.connect(self.open_selected_pdf)

    def start_download(self):
        """Start the background download worker."""
        decisions = [
            d.strip() for d in self.decisions_input.text().split(",") if d.strip()
        ]
        self.worker = DownloadWorker(self.config, decisions)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.download_finished)

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.worker.start()

    def pause_download(self):
        """Pause the active download worker."""
        if self.worker:
            self.worker.pause()
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
            self.status_label.setText("Paused")

    def resume_download(self):
        """Resume the paused download worker."""
        if self.worker:
            self.worker.resume()
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.status_label.setText("Resuming...")

    def stop_download(self):
        """Stop the active download worker."""
        if self.worker:
            self.worker.stop()
            self.status_label.setText("Stopping...")

    def update_progress(self, current, total, message):
        """Update the progress bar and status label."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def handle_error(self, message):
        """Show an error message box."""
        QMessageBox.critical(self, "Error", message)

    def download_finished(self):
        """Handle download completion."""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Finished")

    def perform_search(self):
        """Start the background search worker."""
        query = self.search_input.text()
        if not query:
            return
        mode = "fuzzy" if "Fuzzy" in self.search_mode.currentText() else "exact"
        self.search_worker = SearchWorker(self.config, query, mode)
        self.search_worker.results.connect(self.update_results)
        self.search_worker.start()

    def update_results(self, results):
        """Update the search results list widget."""
        self.results_list.clear()
        for _, title, path in results:
            item = QListWidgetItem(f"{title}")
            item.setData(Qt.UserRole, path)
            self.results_list.addItem(item)

    def open_selected_pdf(self):
        """Open the PDF of the selected paper in the system viewer."""
        item = self.results_list.currentItem()
        if not item:
            return
        path = item.data(Qt.UserRole)
        if path and Path(path).exists():
            if sys.platform == "win32":
                os.startfile(path)  # nosec
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)  # nosec
            else:
                subprocess.run(["xdg-open", path], check=False)  # nosec
        else:
            QMessageBox.warning(
                self, "File Not Found", f"The PDF file does not exist at: {path}"
            )


def main():
    """Entry point for the UI application."""
    config = Config.load(Path("config.yml"), Path("credentials.yml"))

    # Initialize database
    engine = get_engine(config.downloader.db_path)
    init_db(engine)

    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
# end openreview_downloader/ui.py
