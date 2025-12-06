# neurips_downloader

Download oral, spotlight, accepted, or rejected papers from OpenReview into tidy folders by decision.

Despite the name, this works for **any** OpenReview-hosted conference (NeurIPS, ICLR, ICML, etc.).

## Install

```bash
pip install neurips_downloader
```

## Use

The CLI saves PDFs into `downloads/<venue>/<decision>/` with sanitized filenames.

The first positional argument is a comma-separated list of decisions:
- oral
- spotlight
- accepted
- rejected

Basic examples (NeurIPS)

Download all NeurIPS oral papers:

```bash
neurips oral --venue-id NeurIPS.cc/2025/Conference
```

Download all NeurIPS oral and spotlight papers:

```bash
neurips oral,spotlight --venue-id NeurIPS.cc/2025/Conference
```

Download all accepted NeurIPS papers (any presentation type):

```bash
neurips accepted --venue-id NeurIPS.cc/2025/Conference
```

Download all rejected submissions (use with care 🙂):

```bash
neurips rejected --venue-id NeurIPS.cc/2025/Conference
```

By default, existing files are skipped so you can resume interrupted runs just by re-running the same command. To force re-downloads:

```bash
neurips oral,spotlight --venue-id NeurIPS.cc/2025/Conference --no-skip-existing
```

Other conferences (ICLR, ICML, …)

Just change the `--venue-id` to the appropriate OpenReview handle.

ICLR 2025 orals only:

```bash
neurips oral --venue-id ICLR.cc/2025/Conference
```

ICLR 2025 accepted papers (all formats):

```bash
neurips accepted --venue-id ICLR.cc/2025/Conference
```

ICML 2025 oral + spotlight:

```bash
neurips oral,spotlight --venue-id ICML.cc/2025/Conference
```

You can use any other OpenReview venue id in the same way.

See decision counts without downloading:

```bash
neurips --info --venue-id NeurIPS.cc/2025/Conference
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

### Options

- `DECISIONS` (positional) – comma-separated list of decisions to download (oral, spotlight, accepted, rejected)
- `--venue-id` – OpenReview venue id (default: `NeurIPS.cc/2025/Conference` or env `VENUE_ID`)
- `--out-dir` – custom output directory (default: `downloads/<venue>/`)
- `--no-skip-existing` – re-download even if the PDF is already present
- `--info` – print decision counts for the venue and exit

### Optional auth

Set `OPENREVIEW_USERNAME` and `OPENREVIEW_PASSWORD` to use an authenticated OpenReview client (helps avoid rate limits). The CLI also reads `VENUE_ID` if you want a different conference as the default.

You can swap `neurips` for whatever short executable name you wire up in `pyproject.toml`; the README examples follow that interface.

## Development

```bash
pip install -e '.[dev]'
```

Use `bump2version patch|minor|major` to bump the version in `pyproject.toml` and `neurips_downloader/__init__.py`.
