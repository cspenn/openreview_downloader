[![PyPI - Version](https://img.shields.io/pypi/v/openreview-downloader)](https://pypi.org/project/openreview-downloader/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OpenReview Paper Downloader

Download and manage papers from OpenReview-hosted conferences (NeurIPS, ICLR, ICML, etc.) organized by decision type.

Features both a command-line interface and a graphical user interface with paper tracking via SQLite database.

## Installation

```bash
pip install openreview_downloader
```

For GUI support, install with PySide6:

```bash
pip install openreview_downloader[gui]
```

## Quick Start

### Command Line

Download all NeurIPS oral papers:

```bash
ordl oral --venue-id NeurIPS.cc/2025/Conference
```

Download multiple decision types:

```bash
ordl oral,spotlight --venue-id NeurIPS.cc/2025/Conference
```

See decision counts without downloading:

```bash
ordl --info --venue-id NeurIPS.cc/2025/Conference
```

### Graphical Interface

Launch the GUI:

```bash
ordl-gui
```

The GUI provides:
- Visual paper browsing and filtering
- Download progress tracking
- Paper database management
- Dark/light theme support

## Configuration

### Config File (config.yml)

```yaml
venue_id: "NeurIPS.cc/2025/Conference"
decisions:
  - oral
  - spotlight
  - accepted
out_dir: "downloads"
db_path: "data/ordl.db"
retry_attempts: 5
retry_backoff_factor: 2.0
theme: "dark"
```

### Credentials (credentials.yml)

For authenticated access to OpenReview:

```yaml
username: "your_username"
password: "your_password"
```

Copy `credentials.yml.dist` to `credentials.yml` and fill in your credentials.

Alternatively, use environment variables:
- `OPENREVIEW_USERNAME`
- `OPENREVIEW_PASSWORD`

## CLI Reference

**Available decisions:**
- `oral` - Oral presentations
- `spotlight` - Spotlight presentations
- `accepted` - All accepted papers
- `rejected` - Rejected papers

**Options:**
- `DECISIONS` (positional) - Comma-separated list of decisions to download
- `--venue-id` - OpenReview venue ID (default: `NeurIPS.cc/2025/Conference` or env `VENUE_ID`)
- `--out-dir` - Custom output directory (default: `downloads/<venue>/`)
- `--no-skip-existing` - Re-download even if the PDF already exists
- `--info` - Print decision counts and exit

## Output Structure

```
downloads/
└── neurips2025/
    ├── oral/
    │   ├── 27970_Deep_Compositional_Phase_Diffusion.pdf
    │   └── ...
    ├── spotlight/
    │   └── ...
    └── accepted/
        └── ...
```

## Architecture

The project uses a modular architecture:

```
src/openreview_downloader/
├── cli.py          # Command-line interface
├── cli_utils.py    # CLI helper functions
├── config.py       # YAML configuration loader
├── database.py     # SQLAlchemy database setup
├── models.py       # Paper data models
├── services.py     # OpenReview API & download services
└── ui.py           # PySide6 graphical interface
```

## Development

Install in editable mode with development dependencies:

```bash
pip install -e '.[dev]'
```

Run linting:

```bash
pylint src/openreview_downloader
```

Run tests:

```bash
pytest
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
