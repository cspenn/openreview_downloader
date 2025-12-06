[![PyPI - Version](https://img.shields.io/pypi/v/openreview-downloader)](https://pypi.org/project/openreview-downloader/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OpenReview Paper Downloader

Simple download of all oral, spotlight, accepted, or rejected papers from OpenReview into tidy folders by decision.

Despite the name, this works for **any** OpenReview-hosted conference (NeurIPS, ICLR, ICML, etc.).

## Installation

```bash
pip install openreview_downloader
```

## Usage

The CLI saves PDFs into `downloads/<venue>/<decision>/` with sanitized filenames.

**Available decisions:**
- `oral` – Oral presentations
- `spotlight` – Spotlight presentations
- `accepted` – All accepted papers
- `rejected` – Rejected papers

### Basic examples (NeurIPS)

Download all NeurIPS oral papers:

```bash
ordl oral --venue-id NeurIPS.cc/2025/Conference
```

Download Output:

```
downloads
└── neurips2025
    └── oral
        ├── 27970_Deep_Compositional_Phase_Diffusion.pdf
        ...
        └── 28928_Generalized_Linear_Mode_Connectivity.pdf
```


Download all NeurIPS oral and spotlight papers:

```bash
ordl oral,spotlight --venue-id NeurIPS.cc/2025/Conference
```

Download all accepted NeurIPS papers (any presentation type):

```bash
ordl accepted --venue-id NeurIPS.cc/2025/Conference
```

See decision counts without downloading:

```bash
ordl --info --venue-id NeurIPS.cc/2025/Conference
```

Example output:

```
NeurIPS 2025
---
Oral: 77
Spotlight: 687
Accepted: 5287
Rejected: 255
```

### Other Conferences (ICLR, ICML, etc.)

Just change the `--venue-id` to the appropriate OpenReview handle.

**ICLR 2025 orals only:**

```bash
ordl oral --venue-id ICLR.cc/2025/Conference
```

**ICLR 2025 accepted papers (all formats):**

```bash
ordl accepted --venue-id ICLR.cc/2025/Conference
```

**ICML 2025 oral + spotlight:**

```bash
ordl oral,spotlight --venue-id ICML.cc/2025/Conference
```

You can use any other OpenReview venue ID in the same way.


### CLI Options

- **`DECISIONS`** (positional) – Comma-separated list of decisions to download (`oral`, `spotlight`, `accepted`, `rejected`)
- **`--venue-id`** – OpenReview venue ID (default: `NeurIPS.cc/2025/Conference` or env `VENUE_ID`)
- **`--out-dir`** – Custom output directory (default: `downloads/<venue>/`)
- **`--no-skip-existing`** – Re-download even if the PDF is already present
- **`--info`** – Print decision counts for the venue and exit

## Development

Install in editable mode with development dependencies:

```bash
pip install -e '.[dev]'
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
