"""Configuration helpers for the Gnostic Book of Changes parser."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = REPO_ROOT
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
DEFAULT_JSON_DIR = DEFAULT_OUTPUT_DIR
DEFAULT_HTML_DIR = DEFAULT_OUTPUT_DIR / "html"
DEFAULT_GLOSSARY_PATH = DEFAULT_OUTPUT_DIR / "glossary.html"
DEFAULT_METADATA_PATH = DEFAULT_OUTPUT_DIR / "metadata.json"


TRANSLATOR_ALIASES = {
    "legge": "Legge",
    "wilhelmbaynes": "Wilhelm/Baynes",
    "blofeld": "Blofeld",
    "liu": "Liu",
    "ritsemakarcher": "Ritsema/Karcher",
    "shaughnessy": "Shaughnessy",
    "cleary1": "Cleary (1)",
    "cleary2": "Cleary (2)",
    "wu": "Wu",
    "confuciuslegge": "Confucius/Legge",
    "huachingni": "Hua Ching-Ni",
    "anthony": "Anthony",
    "siu": "Siu",
    "wing": "Wing",
    "editor": "Editor",
}


SECTION_LABELS = {
    "judgment": "Judgment",
    "image": "The Image",
    "commentary": "COMMENTARY",
    "notes_and_paraphrases": "NOTES AND PARAPHRASES",
}


SECTION_ORDER = ["judgment", "image", "commentary", "notes_and_paraphrases"]


KNOWN_GLOSSARY_TERMS = {
    "Alien",
    "Archetype",
    "Archetypes",
    "Bardo",
    "Consciousness",
    "Demiurge",
    "Dharma",
    "Ego",
    "Gnosis",
    "Gnostic",
    "Individuation",
    "Karma",
    "Kabbalah",
    "Loosh factory",
    "Plotinus",
    "Self",
    "The Alien",
    "The Demiurge",
    "The Ego",
    "The Self",
    "The Work",
    "Work",
}


@dataclass(frozen=True)
class PrintLayout:
    page_size: str = "letter"
    margin_top: str = "0.75in"
    margin_right: str = "0.5in"
    margin_bottom: str = "0.75in"
    margin_left: str = "0.75in"


PRINT_LAYOUT = PrintLayout()


def normalize_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", stripped).lower()


def canonical_translator_name(name: str) -> str:
    raw = name.strip().strip(":")
    key = normalize_key(raw)
    if key in TRANSLATOR_ALIASES:
        return TRANSLATOR_ALIASES[key]
    if key.startswith("cleary1"):
        return "Cleary (1)"
    if key.startswith("cleary2"):
        return "Cleary (2)"
    return raw


def slugify(text: str) -> str:
    cleaned = unicodedata.normalize("NFKD", text)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", cleaned.lower()).strip("_")
    return cleaned or "hexagram"


def line_output_name(number: int, title: str, extension: str) -> str:
    return f"hexagram_{number:02d}_{slugify(title)}.{extension}"

