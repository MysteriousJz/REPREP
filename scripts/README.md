# Hexagram Processing Scripts

This directory contains standalone scripts for local processing of hexagram HTML files into print-ready outputs with pinyin and glossary references.

## Files

- `config.py` - central configuration (paths, section mapping, print fonts/margins)
- `unihan_parser.py` - parses Unihan files into a character lookup dictionary
- `html_extractor.py` - extracts section text and transformations from source HTML
- `pinyin_converter.py` - converts Chinese lines into pinyin via lookup
- `glossary_builder.py` - builds glossary with `§X.Y` location references
- `html_generator.py` - renders final print-formatted multi-column HTML
- `process_hexagram.py` - command-line orchestration script
- `build_phase2_sources.py` - builds phase-2 source HTML from the raw CText pages
- `library_config.py` - library-wide paths, print layout, and slug helpers
- `library_extractor.py` - extracts verse/paragraph rows from CText library pages
- `library_pinyin.py` - converts Chinese lines to pinyin
- `library_glossary.py` - builds a pinyin-sorted character glossary
- `library_html_generator.py` - renders book pages, indexes, and glossaries
- `library_processor.py` - CLI for processing whole text collections recursively

## Requirements

- Python 3.10+
- Repository root contains source files such as `hexagram_01_qian.html`
- Unihan file available at: `Unihan_Readings.txt`
  - Optional: `Unihan_DictionaryLikeData.txt`

## Usage

From repository root:

```bash
python scripts/process_hexagram.py --number 1 --output output
```

Batch processing by palace:

```bash
python scripts/process_hexagram.py --palace qian --output output
```

Process every hexagram:

```bash
python scripts/process_hexagram.py --all --output output
```

Build phase-2 source pages from the raw CText exports:

```bash
python scripts/build_phase2_sources.py --numbers 1,2,3
```

Process a classical Chinese library collection:

```bash
python scripts/library_processor.py --dir 道可道 --output output
python scripts/library_processor.py --dir 道可道 --recursive --output output
python scripts/library_processor.py --all --output output
```

Optional arguments:

- `--logs logs` (default: `logs/`)
- `--repo-root /path/to/repo`
- `--number N` or `--numbers N1,N2,...`
- `--palace qian` for the Qián Palace sequence
- `--all` to process every mapped hexagram
- `--recursive` to process nested library directories
- `--merge` to also emit a combined `book.html` page per directory
- `--name "Custom Name"` to override the output title for a selected directory

## Outputs

- `output/hexagram_XX_<name>.html`
- `logs/phase3_processing_log.json`
- `output/<collection>/.../index.html`
- `output/<collection>/.../chapter_XXX.html`
- `output/<collection>/.../glossary.html`
- `logs/processing_log.json`

## Notes

- Output uses print CSS for US Letter (8.5"×11") and binding-friendly left margin.
- Sections 1-8 are rendered in Chinese/Pinyin dual columns.
- Focus transformations are rendered in two columns.
- Glossary is rendered in three columns and sorted by pinyin (tone-aware).
- Library outputs reuse the same print-first layout and glossary conventions.
