"""HTML generation with print-first formatting and column layouts."""

from __future__ import annotations

from html import escape

from config import PRINT_LAYOUT, SECTION_ORDER, SECTION_TITLES
from glossary_builder import GlossaryBuildResult
from html_extractor import ExtractedHexagram
from pinyin_converter import to_pinyin_line
from unihan_parser import UnihanRecord


def _render_rows(lines: list[str], lookup: dict[str, UnihanRecord]) -> str:
    rows = []
    for line in lines:
        rows.append(
            "<div class=\"text-row\">"
            f"<div class=\"zh\">{escape(line)}</div>"
            f"<div class=\"py\">{escape(to_pinyin_line(line, lookup))}</div>"
            "</div>"
        )
    return "\n".join(rows)


def _render_transformations(extracted: ExtractedHexagram, lookup: dict[str, UnihanRecord]) -> str:
    cards = []
    for item in extracted.transformations:
        cards.append(
            "<div class=\"transformation-card\">"
            f"<h3>{escape(item.title)}</h3>"
            "<div class=\"text-row section8\">"
            f"<div class=\"zh\">{escape(item.text)}</div>"
            f"<div class=\"py\">{escape(to_pinyin_line(item.text, lookup))}</div>"
            "</div>"
            "</div>"
        )
    return "\n".join(cards)


def _render_glossary(glossary: GlossaryBuildResult) -> str:
    entries = []
    for entry in glossary.entries:
        entries.append(
            "<div class=\"glossary-entry\">"
            f"<div class=\"glossary-char\">{escape(entry.char)}</div>"
            f"<div class=\"glossary-pinyin\">{escape(entry.pinyin)}</div>"
            f"<div class=\"glossary-definition\">{escape(entry.definition)}</div>"
            f"<div class=\"glossary-locations\">{escape(', '.join(entry.references))}</div>"
            "</div>"
        )
    return "\n".join(entries)


def generate_html(
    extracted: ExtractedHexagram,
    lookup: dict[str, UnihanRecord],
    glossary: GlossaryBuildResult,
) -> str:
    """Generate complete print-ready HTML for one hexagram."""

    section_blocks: list[str] = []
    for section in SECTION_ORDER[:-1]:
        css_class = "section12" if section in {"判斷辭", "彖傳"} else "section37"
        section_blocks.append(
            "<section class=\"major-section\">"
            f"<h2>{escape(SECTION_TITLES[section])}</h2>"
            f"<div class=\"section-grid {css_class}\">{_render_rows(extracted.sections.get(section, []), lookup)}</div>"
            "</section>"
        )

    section_blocks.append(
        "<section class=\"major-section\">"
        f"<h2>{escape(SECTION_TITLES['焦氏易林'])}</h2>"
        "<div class=\"transformations-grid\">"
        f"{_render_transformations(extracted, lookup)}"
        "</div>"
        "</section>"
    )

    section_blocks.append(
        "<section class=\"major-section glossary-section\">"
        "<h2>九、字典 (Character Glossary)</h2>"
        "<div class=\"glossary-grid\">"
        f"{_render_glossary(glossary)}"
        "</div>"
        "</section>"
    )

    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{escape(extracted.symbol)} {escape(extracted.title)}</title>
  <style>
    @page {{
      size: {PRINT_LAYOUT.page_size};
      margin: {PRINT_LAYOUT.margin_top} {PRINT_LAYOUT.margin_right} {PRINT_LAYOUT.margin_bottom} {PRINT_LAYOUT.margin_left};
    }}

    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Noto Serif SC", "Source Han Serif", SimSun, serif;
      color: #111;
      margin: 0;
      line-height: 1.5;
    }}

    h1 {{
      text-align: center;
      margin: 0 0 0.35in 0;
      font-size: 28pt;
    }}

    h2 {{
      font-size: 18pt;
      border-bottom: 1px solid #333;
      margin: 0 0 0.15in 0;
    }}

    .section-grid {{
      display: grid;
      gap: 0.1in;
    }}

    .text-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      column-gap: 0.4in;
      border-bottom: 1px dotted #ddd;
      padding: 0.06in 0;
    }}

    .text-row .zh {{ letter-spacing: 0.02em; }}
    .text-row .py {{ color: #444; }}

    .section12 .zh {{ font-size: {PRINT_LAYOUT.section_1_2_chinese}; }}
    .section12 .py {{ font-size: {PRINT_LAYOUT.section_1_2_pinyin}; }}

    .section37 .zh {{ font-size: {PRINT_LAYOUT.section_3_7_chinese}; }}
    .section37 .py {{ font-size: {PRINT_LAYOUT.section_3_7_pinyin}; }}

    .transformations-grid {{
      column-count: 2;
      column-gap: 0.3in;
    }}

    .transformation-card {{
      display: inline-block;
      width: 100%;
      border: 1px solid #ccc;
      border-radius: 6px;
      margin: 0 0 0.16in 0;
      padding: 0.08in;
      background: #fcfcfc;
    }}

    .transformation-card h3 {{
      margin: 0 0 0.08in 0;
      font-size: 14pt;
      color: #333;
    }}

    .section8 .zh {{ font-size: {PRINT_LAYOUT.section_8_chinese}; }}
    .section8 .py {{ font-size: {PRINT_LAYOUT.section_8_pinyin}; }}

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
    .glossary-locations {{ font-size: {PRINT_LAYOUT.glossary_locations}; color: #666; margin-top: 0.03in; font-family: monospace; }}

  </style>
</head>
<body>
  <h1>{escape(extracted.symbol)} {escape(extracted.title)}</h1>
  {'\n'.join(section_blocks)}
</body>
</html>
"""
