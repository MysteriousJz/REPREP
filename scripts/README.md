# Gnostic Book of Changes Scripts

These scripts parse James DeKorne's Gnostic Book of Changes HTML pages into structured JSON and print-ready HTML.

## Files

- `gnostic_data_model.py` - dataclasses for hexagrams, titles, lines, and sections
- `gnostic_config.py` - paths, translator normalization, and output naming helpers
- `gnostic_html_extractor.py` - BeautifulSoup parser for the source HTML pages
- `gnostic_json_generator.py` - JSON serialization and metadata helpers
- `gnostic_html_generator.py` - print-ready HTML and glossary rendering
- `gnostic_processor.py` - CLI entrypoint

## Requirements

- Python 3.10+
- `beautifulsoup4`
- `lxml` (optional, retained for compatibility)

## Usage

From the repository root:

```bash
python scripts/gnostic_processor.py --dir . --output output
```

Process one hexagram:

```bash
python scripts/gnostic_processor.py --number 56 --dir . --output output
```

Process a range:

```bash
python scripts/gnostic_processor.py --numbers 23,30,45,56 --dir . --output output
```

Process all matching hexagrams in a directory:

```bash
python scripts/gnostic_processor.py --dir ./GnosticBookOfChanges --output output
```

Formats:

- `--format json`
- `--format html`
- `--format both`

Outputs:

- `output/hexagram_56_transition.json`
- `output/html/hexagram_56_transition.html`
- `output/all_hexagrams.json`
- `output/metadata.json`
- `output/glossary.html`

