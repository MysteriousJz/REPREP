"""Print-ready HTML generation for Gnostic hexagrams."""

from __future__ import annotations

from html import escape
from pathlib import Path

from gnostic_config import PRINT_LAYOUT
from gnostic_data_model import GnosticHexagram


def _render_kv_rows(items: dict[str, str]) -> str:
    return "\n".join(
        f'<div class="text-row"><div class="translator">{escape(key)}</div><div class="text">{escape(value)}</div></div>'
        for key, value in items.items()
    )


def _render_notes(notes: list[str]) -> str:
    if not notes:
        return ""
    return "<ul>" + "".join(f"<li>{escape(note)}</li>" for note in notes) + "</ul>"


def render_hexagram_html(hexagram: GnosticHexagram) -> str:
    sections = [
        ("Judgment", hexagram.judgment.translations),
        ("The Image", hexagram.image.translations),
        ("Commentary", hexagram.commentary.translations),
    ]

    body_sections = []
    if hexagram.titles.alt_titles:
        body_sections.append(
            f'<p class="subtitle">Alternate titles: {escape(", ".join(hexagram.titles.alt_titles))}</p>'
        )

    for heading, items in sections:
        if not items and heading != "Commentary":
            continue
        body_sections.append(
            "<section class=\"major-section\">"
            f"<h2>{escape(heading)}</h2>"
            f"{_render_kv_rows(items)}"
            "</section>"
        )

    if hexagram.notes_and_paraphrases:
        body_sections.append(
            "<section class=\"major-section\">"
            "<h2>Notes and Paraphrases</h2>"
            f"<div class=\"notes\">{escape(hexagram.notes_and_paraphrases).replace(chr(10), '<br>')}</div>"
            "</section>"
        )

    for line in hexagram.lines:
        line_parts = [
            "<section class=\"major-section line-section\">",
            f"<h2>Line {line.number}</h2>",
        ]
        if line.translations:
            line_parts.append(_render_kv_rows(line.translations))
        if line.commentaries:
            line_parts.append('<div class="commentary"><h3>Commentary</h3>' + _render_kv_rows(line.commentaries) + "</div>")
        if line.notes:
            line_parts.append('<div class="notes"><h3>Notes</h3>' + _render_notes(line.notes) + "</div>")
        line_parts.append("</section>")
        body_sections.append("".join(line_parts))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(str(hexagram.number))} — {escape(hexagram.titles.main_title)} — Gnostic Book of Changes</title>
  <style>
    @page {{ size: {PRINT_LAYOUT.page_size}; margin: {PRINT_LAYOUT.margin_top} {PRINT_LAYOUT.margin_right} {PRINT_LAYOUT.margin_bottom} {PRINT_LAYOUT.margin_left}; }}
    body {{ font-family: Georgia, serif; color: #111; line-height: 1.5; margin: 0; padding: 0; }}
    main {{ padding: 0.2in 0; }}
    h1 {{ text-align: center; margin: 0 0 0.2in 0; }}
    .subtitle {{ text-align: center; color: #444; margin: 0 0 0.25in 0; }}
    .major-section {{ margin: 0 0 0.22in 0; break-inside: avoid; }}
    h2 {{ font-size: 18pt; margin: 0 0 0.08in 0; border-bottom: 1px solid #444; }}
    h3 {{ font-size: 13pt; margin: 0.06in 0; }}
    .text-row {{ display: grid; grid-template-columns: 1.2in 1fr; gap: 0.12in; padding: 0.05in 0; border-bottom: 1px dotted #ddd; }}
    .translator {{ font-weight: bold; }}
    .notes ul {{ margin: 0.05in 0 0 0.18in; padding: 0; }}
    .notes li {{ margin-bottom: 0.04in; }}
    .commentary {{ margin-top: 0.08in; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(str(hexagram.number))} — {escape(hexagram.titles.main_title)}</h1>
    {"".join(body_sections)}
  </main>
</body>
</html>"""


def render_glossary_html(terms: list[str], translators: list[str]) -> str:
    term_items = "".join(f"<li>{escape(term)}</li>" for term in terms)
    translator_items = "".join(f"<li>{escape(name)}</li>" for name in translators)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gnostic Glossary</title>
  <style>
    body {{ font-family: Georgia, serif; padding: 0.5in; }}
    h1, h2 {{ margin-top: 0; }}
    ul {{ columns: 2; column-gap: 0.5in; }}
  </style>
</head>
<body>
  <h1>Gnostic Glossary</h1>
  <h2>Key Terms</h2>
  <ul>{term_items}</ul>
  <h2>Translators</h2>
  <ul>{translator_items}</ul>
</body>
</html>"""

