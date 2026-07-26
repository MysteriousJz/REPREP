"""JSON serialization helpers for Gnostic hexagram data."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from gnostic_config import KNOWN_GLOSSARY_TERMS
from gnostic_data_model import GnosticHexagram


def _collect_terms(hexagrams: list[GnosticHexagram]) -> list[str]:
    terms = set(KNOWN_GLOSSARY_TERMS)
    for hexagram in hexagrams:
        terms.add(hexagram.titles.main_title)
        terms.update(hexagram.titles.alt_titles)
        for line in hexagram.lines:
            terms.update(line.translations)
            terms.update(line.commentaries)
    return sorted(term for term in terms if term)


def build_metadata(hexagrams: list[GnosticHexagram], source_files: list[str]) -> dict[str, object]:
    translators = sorted({
        key
        for hexagram in hexagrams
        for section in (hexagram.judgment, hexagram.image, hexagram.commentary)
        for key in section.translations
    } | {
        key
        for hexagram in hexagrams
        for line in hexagram.lines
        for key in list(line.translations) + list(line.commentaries)
    })
    return {
        "hexagram_count": len(hexagrams),
        "source_files": source_files,
        "translators": translators,
        "glossary_terms": _collect_terms(hexagrams),
    }


def hexagram_to_dict(hexagram: GnosticHexagram) -> dict[str, object]:
    return {
        "hexagram": {
            "number": hexagram.number,
            "main_title": hexagram.titles.main_title,
            "alternate_titles": hexagram.titles.alt_titles,
            "judgment": hexagram.judgment.translations,
            "image": hexagram.image.translations,
            "commentary": hexagram.commentary.translations,
            "notes_and_paraphrases": hexagram.notes_and_paraphrases,
            "lines": [asdict(line) for line in hexagram.lines],
            "editor_notes": hexagram.editor_notes,
        }
    }


def all_hexagrams_to_dict(hexagrams: list[GnosticHexagram], metadata: dict[str, object]) -> dict[str, object]:
    return {
        "hexagrams": [hexagram_to_dict(hexagram)["hexagram"] for hexagram in hexagrams],
        "metadata": metadata,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

