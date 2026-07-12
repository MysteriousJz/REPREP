"""BeautifulSoup-based extraction for Gnostic Book of Changes HTML files."""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from gnostic_config import canonical_translator_name, normalize_key
from gnostic_data_model import GnosticHexagram, GnosticLine, GnosticSection, GnosticTitles


TITLE_RE = re.compile(r"(?P<number>\d+)\s*--\s*(?P<title>.+?)\s*--\s*(?P<number2>\d+)", re.S)
LINE_RE = re.compile(r"^line[\s\-]*(?P<number>one|two|three|four|five|six|\d+)\s*$", re.I)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _parse_line_number(text: str) -> int | None:
    match = LINE_RE.search(text)
    if not match:
        return None
    token = match.group("number").lower()
    if token.isdigit():
        return int(token)
    return {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
    }.get(token)


def _container_for_number(soup: BeautifulSoup, number: int) -> Tag | None:
    hex_id = f"hex{number}"
    for div in soup.find_all("div"):
        classes = div.get("class") or []
        if div.get("id") == hex_id or hex_id in classes:
            return div
    return soup.body if soup.body else None


def _extract_title_paragraph(p: Tag) -> tuple[int, str] | None:
    text = _clean(p.get_text(" ", strip=True))
    match = TITLE_RE.search(text)
    if not match:
        return None
    return int(match.group("number")), _clean(match.group("title"))


def _extract_other_titles(text: str) -> list[str]:
    if ":" not in text:
        return []
    tail = text.split(":", 1)[1]
    tail = tail.split("--", 1)[0]
    parts = [part.strip(" ;.") for part in tail.split(",")]
    return [part for part in parts if part]


def _heading_kind(text: str) -> str | None:
    key = normalize_key(text)
    if key == "judgment":
        return "judgment"
    if key in {"theimage", "image"}:
        return "image"
    if key == "commentary":
        return "commentary"
    if key == "notesandparaphrases":
        return "notes_and_paraphrases"
    return None


def _extract_label_segments(p: Tag) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    current_label: str | None = None
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_parts
        if current_label is not None:
            text = _clean("".join(current_parts))
            if text:
                segments.append((current_label, text))
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
            if ":" in strong_text:
                flush()
                label = strong_text.split(":", 1)[0]
                current_label = canonical_translator_name(label)
                continue
            current_parts.append(strong_text)
            continue
        current_parts.append(child.get_text(" ", strip=True))

    flush()
    return segments


def _is_editor_marker(text: str) -> bool:
    key = normalize_key(text)
    return key.startswith("notes") or key.startswith("editor")


def parse_gnostic_hexagram(source_path: Path, number: int) -> GnosticHexagram:
    html = source_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    container = _container_for_number(soup, number)
    if container is None:
        raise ValueError(f"Could not locate hexagram container for {number}")

    titles = GnosticTitles(number=number)
    judgment = GnosticSection()
    image = GnosticSection()
    commentary = GnosticSection()
    notes_and_paraphrases = []
    editor_notes: list[str] = []
    lines: list[GnosticLine] = []

    current_major: str | None = None
    current_line: GnosticLine | None = None
    current_line_mode: str | None = None
    last_major_key: str | None = None
    last_line_key: str | None = None
    notes_role = "general"

    for p in container.find_all("p"):
        text = _clean(p.get_text(" ", strip=True))
        if not text:
            continue

        title_info = _extract_title_paragraph(p)
        if title_info and not titles.main_title:
            titles.number, titles.main_title = title_info
            continue

        if text.lower().startswith("other titles"):
            titles.alt_titles = _extract_other_titles(text)
            continue

        line_number = _parse_line_number(text)
        if line_number is not None:
            current_line = GnosticLine(number=line_number, title=f"Line-{line_number}")
            lines.append(current_line)
            current_line_mode = "translations"
            last_line_key = None
            last_major_key = None
            continue

        if current_line is not None:
            line_heading = _heading_kind(text)
            if line_heading == "commentary":
                current_line_mode = "commentaries"
                last_line_key = None
                continue
            if line_heading == "notes_and_paraphrases":
                current_line_mode = "notes"
                last_line_key = None
                continue

            if current_line_mode in {"translations", "commentaries"}:
                segments = _extract_label_segments(p)
                target = current_line.translations if current_line_mode == "translations" else current_line.commentaries
                if segments:
                    for key, value in segments:
                        target[key] = value
                        last_line_key = key
                elif last_line_key and last_line_key in target:
                    target[last_line_key] = f"{target[last_line_key]} {text}".strip()
                continue

            if current_line_mode == "notes":
                current_line.notes.append(text)
                continue

        heading = _heading_kind(text)
        if heading:
            current_major = heading
            current_line = None
            current_line_mode = None
            last_major_key = None
            if heading == "notes_and_paraphrases":
                notes_role = "general"
            continue

        if current_major in {"judgment", "image", "commentary"}:
            target = {"judgment": judgment, "image": image, "commentary": commentary}[current_major].translations
            segments = _extract_label_segments(p)
            if segments:
                for key, value in segments:
                    target[key] = value
                    last_major_key = key
                continue
            if last_major_key and last_major_key in target:
                target[last_major_key] = f"{target[last_major_key]} {text}".strip()
            continue

        if current_major == "notes_and_paraphrases":
            if notes_role == "general" and _is_editor_marker(text):
                notes_role = "editor"
            if notes_role == "editor":
                editor_notes.append(text)
            else:
                notes_and_paraphrases.append(text)
            continue

    return GnosticHexagram(
        number=titles.number or number,
        titles=titles,
        judgment=judgment,
        image=image,
        commentary=commentary,
        notes_and_paraphrases="\n\n".join(notes_and_paraphrases).strip(),
        lines=lines,
        editor_notes=editor_notes,
    )
