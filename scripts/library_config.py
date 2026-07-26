"""Configuration helpers for classical Chinese library processing."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
import unicodedata


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
DEFAULT_LOG_DIR = REPO_ROOT / "logs"

UNIHAN_FILE_CANDIDATES = {
    "readings": [REPO_ROOT / "Unihan_Readings.txt"],
    "dictionary_like": [REPO_ROOT / "Unihan_DictionaryLikeData.txt"],
}


@dataclass(frozen=True)
class PrintLayout:
    page_size: str = "letter"
    margin_top: str = "0.75in"
    margin_right: str = "0.5in"
    margin_bottom: str = "0.75in"
    margin_left: str = "0.75in"

    body_font: str = '"Noto Serif SC", "Source Han Serif", SimSun, serif'
    sans_font: str = '"Noto Sans SC", "Source Han Sans SC", sans-serif'

    title_size: str = "26pt"
    subtitle_size: str = "14pt"
    line_chinese: str = "20pt"
    line_pinyin: str = "14pt"
    glossary_char: str = "28pt"
    glossary_pinyin: str = "14pt"
    glossary_definition: str = "12pt"
    glossary_locations: str = "10pt"


PRINT_LAYOUT = PrintLayout()


def _normalize_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", stripped).lower()


def slugify(text: str) -> str:
    """Create a filesystem-friendly slug while keeping CJK characters."""
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = re.sub(r"[\\/:*?\"<>|]+", "-", normalized)
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("._-") or "book"


def clean_site_title(text: str) -> str:
    """Remove common CText site suffixes and surrounding decoration."""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = re.sub(r"\s*-\s*Chinese Text Project.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*-\s*中國哲學書電子化計劃.*$", "", cleaned)
    cleaned = re.sub(r"\s*:\s*中國哲學書電子化計劃.*$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^[《「\[]+|[》」\]]+$", "", cleaned).strip()
    return cleaned


def normalize_label(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.rstrip(":：")


@lru_cache(maxsize=16)
def cached_slug(text: str) -> str:
    return slugify(text)

