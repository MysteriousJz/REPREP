"""HTML extraction for CText-style classical Chinese library files."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape, unescape
from pathlib import Path
import re

from library_config import clean_site_title, normalize_label


_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_INLINE_COMMENT_RE = re.compile(r"<span[^>]*class=\"[^\"]*inlinecomment[^\"]*\"[^>]*>.*?</span>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", re.I | re.S)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_PARA_RE = re.compile(r"</p\s*>", re.I)
_P_OPEN_RE = re.compile(r"<p\b[^>]*>", re.I)
_SITE_SUFFIXES = (
    "Chinese Text Project",
    "中國哲學書電子化計劃",
)


@dataclass
class LibraryEntry:
    """One extracted text unit."""

    index: int
    title: str
    lines: list[str] = field(default_factory=list)
    label: str | None = None
    source_path: Path | None = None
    book_index: int = 0


@dataclass
class LibrarySource:
    """A single source HTML file."""

    source_path: Path
    title: str
    entries: list[LibraryEntry] = field(default_factory=list)


def _remove_markup(fragment: str) -> str:
    fragment = _INLINE_COMMENT_RE.sub("", fragment)
    fragment = _BR_RE.sub("\n", fragment)
    fragment = _PARA_RE.sub("\n", fragment)
    fragment = _P_OPEN_RE.sub("", fragment)
    fragment = _TAG_RE.sub("", fragment)
    fragment = unescape(fragment)
    fragment = fragment.replace("\u3000", " ")
    fragment = re.sub(r"[ \t\r\f\v]+", " ", fragment)
    fragment = re.sub(r"\n[ \t]+", "\n", fragment)
    fragment = re.sub(r"\n{3,}", "\n\n", fragment)
    return fragment.strip()


def _normalize_lines(fragment: str) -> list[str]:
    cleaned = _remove_markup(fragment)
    if not cleaned:
        return []
    lines = []
    for part in cleaned.splitlines():
        item = re.sub(r"\s+", " ", part).strip()
        if item:
            lines.append(item)
    if lines:
        return lines
    return [cleaned]


def _extract_title(html: str, fallback: str) -> str:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    candidates: list[str] = []
    if title_match:
        candidates.append(clean_site_title(_remove_markup(title_match.group(1))))

    section_match = re.search(r'<h2[^>]*class="[^"]*wikisectiontitle[^"]*"[^>]*>(.*?)</h2>', html, re.I | re.S)
    if section_match:
        section_text = _remove_markup(section_match.group(1))
        section_text = re.sub(r"[\[\(].*?[\]\)]", "", section_text).strip()
        candidates.append(clean_site_title(section_text))

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    if h1_match:
        candidates.append(clean_site_title(_remove_markup(h1_match.group(1))))

    for candidate in candidates:
        if candidate:
            return candidate
    return fallback


def _cell_texts(row_html: str) -> list[tuple[str, str]]:
    cells: list[tuple[str, str]] = []
    for attrs, fragment in _CELL_RE.findall(row_html):
        cells.append((attrs, fragment))
    return cells


def _cell_class(attrs: str) -> str:
    match = re.search(r'class=\"([^\"]+)\"', attrs, re.I)
    return match.group(1) if match else ""


def _is_content_row(row_html: str) -> bool:
    row_html_l = row_html.lower()
    return any(token in row_html_l for token in ('class="ctext', 'class="result', 'wikisectiontitle'))


def _pick_content_cell(cells: list[tuple[str, str]]) -> tuple[str | None, str | None]:
    if not cells:
        return None, None

    content = None
    label = None
    for attrs, fragment in cells:
        cls = _cell_class(attrs)
        text = _remove_markup(fragment)
        if "wikisectiontitle" in cls:
            return text, None
        if "ctext" in cls and "opt" not in cls:
            content = fragment
            if label is None and text and (text.isdigit() or len(text) <= 8):
                label = text

    if content is not None:
        return content, label

    if cells:
        return cells[-1][1], label
    return None, None


def _looks_like_label(text: str | None, source_title: str) -> bool:
    if not text:
        return False
    cleaned = normalize_label(text)
    source_clean = normalize_label(source_title)
    if not cleaned:
        return False
    if cleaned == source_clean:
        return False
    if cleaned in _SITE_SUFFIXES:
        return False
    if len(cleaned) <= 1 and not cleaned.isdigit():
        return False
    return True


def extract_library_source(source_path: Path) -> LibrarySource:
    """Extract all content rows from a CText HTML source file."""
    html = _SCRIPT_STYLE_RE.sub("", source_path.read_text(encoding="utf-8", errors="ignore"))
    source_title = _extract_title(html, source_path.stem)

    entries: list[LibraryEntry] = []
    row_index = 0
    for row_html in _ROW_RE.findall(html):
        if not _is_content_row(row_html):
            continue

        cells = _cell_texts(row_html)
        content_fragment, label = _pick_content_cell(cells)
        if content_fragment is None:
            continue

        lines = _normalize_lines(content_fragment)
        if not lines:
            continue

        row_index += 1
        entry_label = normalize_label(label) if _looks_like_label(label, source_title) else None
        entry_title = f"{source_title} {row_index:02d}"
        if entry_label:
            entry_title = f"{source_title} · {entry_label}"

        entries.append(
            LibraryEntry(
                index=row_index,
                title=entry_title,
                lines=lines,
                label=entry_label,
                source_path=source_path,
            )
        )

    return LibrarySource(source_path=source_path, title=source_title, entries=entries)
