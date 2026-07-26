"""Convert James DeKorne Gnostic HTML pages into print-ready HTML."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"

TITLE_RE = re.compile(r"(?P<number>\d+)\s*[-–—]{1,2}\s*(?P<title>.+?)\s*[-–—]?\s*(?P<number2>\d+)\s*$", re.S)
LINE_RE = re.compile(r"^line[\s\-]*(?P<number>one|two|three|four|five|six|\d+)\s*$", re.I)
HEXAGRAM_CONTAINER_RE = re.compile(r"^hex\d+$", re.I)

KNOWN_LABELS = [
    "Legge",
    "Wilhelm/Baynes",
    "Blofeld",
    "Liu",
    "Ritsema/Karcher",
    "Shaughnessy",
    "Cleary (1)",
    "Cleary (2)",
    "Wu",
    "Confucius/Legge",
    "Siu",
    "Wing",
    "Editor",
    "Anthony",
    "Hua Ching-Ni",
]

LABEL_NORMALIZED = {
    re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", label).lower(): label for label in KNOWN_LABELS
}


@dataclass
class Entry:
    author: str
    text: str


@dataclass
class Section:
    entries: list[Entry] = field(default_factory=list)


@dataclass
class LineSection:
    number: int
    translations: list[Entry] = field(default_factory=list)
    commentaries: list[Entry] = field(default_factory=list)
    notes: list[Entry] = field(default_factory=list)


@dataclass
class HexagramPage:
    number: int
    title: str
    alternate_titles: list[str] = field(default_factory=list)
    judgment: Section = field(default_factory=Section)
    image: Section = field(default_factory=Section)
    commentary: Section = field(default_factory=Section)
    notes_and_paraphrases: Section = field(default_factory=Section)
    lines: list[LineSection] = field(default_factory=list)


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip()


def _canonical_label(text: str) -> str | None:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()
    return LABEL_NORMALIZED.get(key)


def _is_hexagram_container(div: Tag) -> bool:
    return isinstance(div, Tag) and HEXAGRAM_CONTAINER_RE.match(div.get("id", "") or "") is not None


def _extract_title(container: Tag) -> tuple[int, str]:
    for p in container.find_all("p"):
        text = _clean(p.get_text(" ", strip=True))
        match = TITLE_RE.match(text)
        if match:
            title = _clean(match.group("title")).strip(" -–—")
            return int(match.group("number")), title
    raise ValueError("Hexagram title not found")


def _extract_other_titles(text: str) -> list[str]:
    if ":" not in text:
        return []
    tail = text.split(":", 1)[1].strip()
    tail = tail.split("--", 1)[0].strip()
    return [part.strip(" ;.") for part in tail.split(",") if part.strip(" ;.")]


def _parse_line_number(text: str) -> int | None:
    match = LINE_RE.match(text)
    if not match:
        return None
    token = match.group("number").lower()
    if token.isdigit():
        return int(token)
    return {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}.get(token)


def _heading_kind(text: str) -> str | None:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()
    if key == "judgment":
        return "judgment"
    if key in {"theimage", "image"}:
        return "image"
    if key == "commentary":
        return "commentary"
    if key == "notesandparaphrases":
        return "notes"
    return None


def _split_labeled_segments(p: Tag) -> list[Entry]:
    segments: list[Entry] = []
    current_label: str | None = None
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_parts
        if current_label is not None:
            text = _clean("".join(current_parts)).lstrip(": ").strip()
            if text:
                segments.append(Entry(current_label, text))
        current_label = None
        current_parts = []

    for child in p.children:
        if isinstance(child, NavigableString):
            current_parts.append(str(child))
            continue
        if not isinstance(child, Tag):
            continue
        if child.name == "strong":
            strong_text = _clean(child.get_text(" ", strip=True))
            label_text, sep, remainder = strong_text.partition(":")
            canonical = _canonical_label(label_text if sep else strong_text)
            if canonical:
                flush()
                current_label = canonical
                if remainder.strip():
                    current_parts.append(f" {remainder.strip()} ")
                continue
        current_parts.append(f" {child.get_text(' ', strip=True)} ")

    flush()
    if segments:
        return segments
    text = _clean(p.get_text(" ", strip=True))
    return [Entry("Note", text)] if text else []


def _append_section_entry(section: Section, entry: Entry) -> None:
    if section.entries and section.entries[-1].author == entry.author and entry.author == "Note":
        section.entries[-1].text = f"{section.entries[-1].text} {entry.text}".strip()
    else:
        section.entries.append(entry)


def _append_line_entry(entries: list[Entry], entry: Entry) -> None:
    if entries and entries[-1].author == entry.author and entry.author == "Note":
        entries[-1].text = f"{entries[-1].text} {entry.text}".strip()
    else:
        entries.append(entry)


def parse_hexagram(source_path: Path) -> HexagramPage:
    html = source_path.read_text(encoding="latin-1")
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(lambda tag: _is_hexagram_container(tag) if isinstance(tag, Tag) else False)
    if container is None:
        raise ValueError("No hexagram container found")

    number, title = _extract_title(container)
    page = HexagramPage(number=number, title=title)

    current_section: str | None = None
    current_line: LineSection | None = None
    current_line_mode: str | None = None

    for p in container.find_all("p"):
        text = _clean(p.get_text(" ", strip=True))
        if not text:
            continue

        if text.lower().startswith("other titles"):
            page.alternate_titles = _extract_other_titles(text)
            continue

        line_number = _parse_line_number(text)
        if line_number is not None:
            current_line = LineSection(number=line_number)
            page.lines.append(current_line)
            current_line_mode = "translations"
            current_section = None
            continue

        heading = _heading_kind(text)
        if heading:
            if current_line is not None:
                current_line_mode = heading
            else:
                current_section = heading
            continue

        entries = _split_labeled_segments(p)
        if current_line is not None:
            target = {
                "translations": current_line.translations,
                "commentary": current_line.commentaries,
                "notes": current_line.notes,
            }.get(current_line_mode or "translations", current_line.translations)
            if entries and entries[0].author != "Note":
                for entry in entries:
                    _append_line_entry(target, entry)
            else:
                note_entry = entries[0] if entries else Entry("Note", text)
                _append_line_entry(target, note_entry)
            continue

        if current_section in {"judgment", "image", "commentary", "notes"}:
            section_obj = {
                "judgment": page.judgment,
                "image": page.image,
                "commentary": page.commentary,
                "notes": page.notes_and_paraphrases,
            }[current_section]
            if entries and entries[0].author != "Note":
                for entry in entries:
                    _append_section_entry(section_obj, entry)
            else:
                note_entry = entries[0] if entries else Entry("Note", text)
                _append_section_entry(section_obj, note_entry)
            continue

    return page


def slugify(text: str) -> str:
    import unicodedata

    cleaned = unicodedata.normalize("NFKD", text)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", cleaned.lower()).strip("_")
    return cleaned or "hexagram"


def output_name(number: int, title: str) -> str:
    return f"hexagram_{number:02d}_{slugify(title)}.html"


def render_rows(entries: list[Entry]) -> str:
    return "\n".join(
        f'<div class="text-row"><div class="translator">{escape(entry.author)}</div><div class="text">{escape(entry.text)}</div></div>'
        for entry in entries
    )


def render_line_section(line: LineSection) -> str:
    parts = [f'<section class="line-block"><h3>Line {line.number}</h3>']
    if line.translations:
        parts.append(render_rows(line.translations))
    if line.commentaries:
        parts.append('<div class="subsection"><h4>Commentary</h4>')
        parts.append(render_rows(line.commentaries))
        parts.append("</div>")
    if line.notes:
        parts.append('<div class="subsection"><h4>Notes</h4>')
        parts.append(render_rows(line.notes))
        parts.append("</div>")
    parts.append("</section>")
    return "".join(parts)


def render_page(page: HexagramPage) -> str:
    title_line = f"{page.number} — {page.title}"
    sections = [
        ("Judgment", page.judgment.entries),
        ("The Image", page.image.entries),
        ("COMMENTARY", page.commentary.entries),
        ("NOTES & PARAPHRASES", page.notes_and_paraphrases.entries),
    ]

    body: list[str] = [f"<h1>{escape(title_line)}</h1>"]
    if page.alternate_titles:
        body.append(f'<p class="subtitle">Other titles: {escape(", ".join(page.alternate_titles))}</p>')

    for heading, entries in sections:
        if not entries:
            continue
        body.append(f'<section class="major-section"><h2>{escape(heading)}</h2>')
        body.append(render_rows(entries))
        body.append("</section>")

    if page.lines:
        body.append('<section class="major-section"><h2>Lines 1-6</h2>')
        for line in page.lines:
            body.append(render_line_section(line))
        body.append("</section>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title_line)} — Print Edition</title>
  <style>
    @page {{ size: letter; margin: 0.75in 0.5in 0.75in 0.75in; }}
    body {{ font-family: Georgia, serif; color: #111; line-height: 1.45; margin: 0; }}
    main {{ padding: 0; }}
    h1 {{ font-size: 28pt; text-align: center; margin: 0 0 0.2in 0; }}
    h2 {{ font-size: 18pt; border-bottom: 2px solid #333; margin: 0.16in 0 0.08in; padding-bottom: 0.03in; }}
    h3 {{ font-size: 13pt; margin: 0.12in 0 0.06in; }}
    h4 {{ font-size: 11pt; margin: 0.08in 0 0.04in; }}
    .subtitle {{ text-align: center; margin: 0 0 0.18in 0; color: #555; }}
    .major-section, .line-block {{ break-inside: avoid; page-break-inside: avoid; }}
    .major-section {{ margin-bottom: 0.18in; }}
    .line-block {{ margin-bottom: 0.14in; }}
    .text-row {{ display: grid; grid-template-columns: 1.2in 1fr; gap: 0.2in; margin: 0 0 0.05in 0; }}
    .translator {{ font-weight: 700; }}
    .text {{ white-space: normal; }}
    .subsection {{ margin-left: 0.1in; }}
  </style>
</head>
<body>
  <main>
    {"".join(body)}
  </main>
</body>
</html>"""


def render_index(pages: list[HexagramPage]) -> str:
    items = "\n".join(
        f'<li><a href="{escape(output_name(page.number, page.title))}">{escape(f"{page.number} — {page.title}")}</a></li>'
        for page in sorted(pages, key=lambda item: item.number)
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gnostic Book of Changes Index</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 0.75in; color: #111; }}
    h1 {{ text-align: center; margin-top: 0; }}
    ol {{ columns: 2; column-gap: 0.5in; padding-left: 1.2em; }}
    li {{ margin: 0 0 0.12in 0; break-inside: avoid; }}
    a {{ color: inherit; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>Gnostic Book of Changes</h1>
  <ol>{items}</ol>
</body>
</html>"""


def discover_source_files(input_dir: Path, output_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in input_dir.rglob("*.html"):
        try:
            path.relative_to(output_dir)
            continue
        except ValueError:
            pass
        files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Gnostic HTML pages into print-ready HTML")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_DIR, help="Folder containing source HTML files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Folder for generated HTML files")
    args = parser.parse_args()

    input_dir = args.input.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pages: list[HexagramPage] = []
    skipped = 0
    for source_path in discover_source_files(input_dir, output_dir):
        try:
            page = parse_hexagram(source_path)
        except Exception:
            skipped += 1
            continue
        pages.append(page)
        out_path = output_dir / output_name(page.number, page.title)
        out_path.write_text(render_page(page), encoding="utf-8")

    if not pages:
        print("[error] No Gnostic hexagram pages found")
        return 2

    (output_dir / "index.html").write_text(render_index(pages), encoding="utf-8")
    print(f"[ok] Processed {len(pages)} pages; skipped {skipped} other HTML files")
    print(f"[ok] Wrote output to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
