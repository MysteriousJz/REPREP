"""HTML generation for classical Chinese library outputs."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from library_config import PRINT_LAYOUT
from library_extractor import LibraryEntry, LibrarySource
from library_glossary import LibraryGlossary
from library_pinyin import to_pinyin_block
from unihan_parser import UnihanRecord


@dataclass
class LibraryBook:
    title: str
    slug: str
    sources: list[LibrarySource]
    entries: list[LibraryEntry]


def _render_entry_lines(entry: LibraryEntry, lookup: dict[str, UnihanRecord]) -> str:
    lines = []
    pinyin_lines = to_pinyin_block(entry.lines, lookup)
    for zh, py in zip(entry.lines, pinyin_lines, strict=False):
        lines.append(
            "<div class=\"text-row\">"
            f"<div class=\"zh\">{escape(zh)}</div>"
            f"<div class=\"py\">{escape(py)}</div>"
            "</div>"
        )
    return "\n".join(lines)


def _render_glossary(glossary: LibraryGlossary) -> str:
    entries = []
    for entry in glossary.entries:
        entries.append(
            "<div class=\"glossary-entry\">"
            f"<div class=\"glossary-char\">{escape(entry.char)}</div>"
            f"<div class=\"glossary-pinyin\">{escape(entry.pinyin)}</div>"
            f"<div class=\"glossary-definition\">{escape(entry.definition)}</div>"
            "</div>"
        )
    return "\n".join(entries)


def _base_head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{escape(title)}</title>
  <style>
    @page {{
      size: {PRINT_LAYOUT.page_size};
      margin: {PRINT_LAYOUT.margin_top} {PRINT_LAYOUT.margin_right} {PRINT_LAYOUT.margin_bottom} {PRINT_LAYOUT.margin_left};
    }}

    * {{ box-sizing: border-box; }}
    body {{
      font-family: {PRINT_LAYOUT.body_font};
      color: #111;
      margin: 0;
      line-height: 1.5;
    }}

    h1 {{
      text-align: center;
      margin: 0 0 0.3in 0;
      font-size: {PRINT_LAYOUT.title_size};
    }}

    h2 {{
      font-size: 18pt;
      border-bottom: 1px solid #333;
      margin: 0 0 0.15in 0;
    }}

    .subtitle {{
      text-align: center;
      color: #555;
      margin: -0.2in 0 0.2in 0;
      font-size: {PRINT_LAYOUT.subtitle_size};
    }}

    .text-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      column-gap: 0.35in;
      padding: 0.06in 0;
      border-bottom: 1px dotted #ddd;
    }}

    .text-row .zh {{ font-size: {PRINT_LAYOUT.line_chinese}; letter-spacing: 0.02em; }}
    .text-row .py {{ font-size: {PRINT_LAYOUT.line_pinyin}; color: #444; }}

    .entry-card {{
      margin-bottom: 0.18in;
      padding-bottom: 0.1in;
      border-bottom: 1px solid #eee;
    }}

    .entry-card h3 {{
      margin: 0 0 0.08in 0;
      font-size: 16pt;
    }}

    .glossary-grid {{
      column-count: 3;
      column-gap: 0.2in;
    }}

    .glossary-entry {{
      display: inline-block;
      width: 100%;
      margin: 0 0 0.14in 0;
      border: 1px solid #ddd;
      padding: 0.08in;
      border-radius: 4px;
      background: #fafafa;
    }}

    .glossary-char {{ font-size: {PRINT_LAYOUT.glossary_char}; font-weight: 700; line-height: 1; }}
    .glossary-pinyin {{ font-size: {PRINT_LAYOUT.glossary_pinyin}; color: #555; margin-top: 0.03in; }}
    .glossary-definition {{ font-size: {PRINT_LAYOUT.glossary_definition}; margin-top: 0.03in; }}
  </style>
</head>
<body>
"""


def generate_entry_html(book: LibraryBook, entry: LibraryEntry, lookup: dict[str, UnihanRecord]) -> str:
    body = [
        f"<h1>{escape(book.title)}</h1>",
        f"<div class=\"subtitle\">{escape(entry.title)}</div>",
        "<section class=\"major-section\">",
        _render_entry_lines(entry, lookup),
        "</section>",
    ]
    return _base_head(entry.title) + "\n".join(body) + "\n</body>\n</html>"


def generate_index_html(book: LibraryBook) -> str:
    items = []
    for entry in book.entries:
        filename = f"chapter_{entry.book_index:03d}.html"
        items.append(f'<a href="{escape(filename)}">{escape(entry.title)}</a>')
    body = [
        f"<h1>{escape(book.title)}</h1>",
        f"<div class=\"subtitle\">{len(book.entries)} chapter page(s)</div>",
        "<section class=\"major-section\">",
        "<div class=\"toc\">",
        "\n".join(items),
        "</div>",
        "</section>",
        '<section class="major-section">',
        '<h2>Glossary</h2>',
        '<p><a href="glossary.html">Open glossary</a></p>',
        "</section>",
    ]
    return _base_head(book.title) + "\n".join(body) + "\n</body>\n</html>"


def generate_glossary_html(book: LibraryBook, glossary: LibraryGlossary) -> str:
    body = [
        f"<h1>{escape(book.title)}</h1>",
        f"<div class=\"subtitle\">{len(glossary.entries)} unique characters</div>",
        "<section class=\"major-section\">",
        '<h2>Character Glossary</h2>',
        '<div class="glossary-grid">',
        _render_glossary(glossary),
        "</div>",
        "</section>",
    ]
    return _base_head(f"{book.title} · Glossary") + "\n".join(body) + "\n</body>\n</html>"


def generate_merged_html(book: LibraryBook, lookup: dict[str, UnihanRecord], glossary: LibraryGlossary) -> str:
    sections = [
        f"<h1>{escape(book.title)}</h1>",
        f"<div class=\"subtitle\">{len(book.entries)} chapter page(s) · {len(glossary.entries)} glossary entries</div>",
    ]
    for entry in book.entries:
        sections.append(
            '<section class="major-section entry-card">'
            f"<h3>{escape(entry.title)}</h3>"
            f"{_render_entry_lines(entry, lookup)}"
            "</section>"
        )
    sections.extend(
        [
            '<section class="major-section" id="glossary">',
            "<h2>Glossary</h2>",
            '<div class="glossary-grid">',
            _render_glossary(glossary),
            "</div>",
            "</section>",
        ]
    )
    return _base_head(book.title) + "\n".join(sections) + "\n</body>\n</html>"
