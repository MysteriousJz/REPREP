"""Configuration settings and lookup helpers for hexagram processing scripts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import re
import unicodedata


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
DEFAULT_LOG_DIR = REPO_ROOT / "logs"
HEXAGRAM_MAPPING_FILE = REPO_ROOT / "hexagram_file_mapping.json"

UNIHAN_FILE_CANDIDATES = {
    "readings": [
        REPO_ROOT / "Unihan_Readings.txt",
    ],
    "dictionary_like": [
        REPO_ROOT / "Unihan_DictionaryLikeData.txt",
    ],
}

SECTION_NUMBERS = {
    "判斷辭": 1,
    "彖傳": 2,
    "象傳": 3,
    "爻辭": 4,
    "文言": 5,
    "京氏易傳": 6,
    "周易注": 7,
    "焦氏易林": 8,
}

SECTION_ORDER = [
    "判斷辭",
    "彖傳",
    "象傳",
    "爻辭",
    "文言",
    "京氏易傳",
    "周易注",
    "焦氏易林",
]

SECTION_TITLES = {
    "判斷辭": "一、判斷辭",
    "彖傳": "二、彖傳",
    "象傳": "三、象傳",
    "爻辭": "四、爻辭",
    "文言": "五、文言",
    "京氏易傳": "六、京氏易傳",
    "周易注": "七、周易注",
    "焦氏易林": "八、焦氏易林",
}


@dataclass(frozen=True)
class PrintLayout:
    """Print layout and font hierarchy for final output."""

    page_size: str = "letter"
    margin_top: str = "0.75in"
    margin_right: str = "0.5in"
    margin_bottom: str = "0.75in"
    margin_left: str = "0.75in"

    section_1_2_chinese: str = "24pt"
    section_1_2_pinyin: str = "16pt"

    section_3_7_chinese: str = "20pt"
    section_3_7_pinyin: str = "14pt"

    section_8_chinese: str = "18pt"
    section_8_pinyin: str = "12pt"

    glossary_char: str = "28pt"
    glossary_pinyin: str = "14pt"
    glossary_definition: str = "12pt"
    glossary_locations: str = "10pt"


PRINT_LAYOUT = PrintLayout()


def resolve_source_file(repo_root: Path, hexagram_number: int) -> Path:
    """Resolve source Phase-2 HTML file path for a given hexagram number."""
    mapping = load_hexagram_mapping(repo_root)
    hexagram_entry = mapping.get("hexagrams", {}).get(str(hexagram_number), {})
    exact_name = str(hexagram_entry.get("chinese_name", "")).strip()
    if exact_name:
        exact_path = repo_root / f"hexagram_{hexagram_number:02d}_{exact_name}.html"
        if exact_path.exists():
            return exact_path

    candidates = sorted(
        repo_root.glob(f"hexagram_{hexagram_number:02d}_*.html"),
        key=lambda p: p.name,
    )
    filtered = [p for p in candidates if "with_glossary" not in p.name]
    if filtered:
        return filtered[0]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"No source HTML found for hexagram {hexagram_number:02d} in {repo_root}"
    )


@lru_cache(maxsize=8)
def load_hexagram_mapping(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    """Load the repository's hexagram mapping file."""

    mapping_file = repo_root / "hexagram_file_mapping.json"
    if not mapping_file.exists():
        raise FileNotFoundError(f"Hexagram mapping file not found: {mapping_file}")
    return json.loads(mapping_file.read_text(encoding="utf-8"))


def all_hexagram_numbers(repo_root: Path = REPO_ROOT) -> list[int]:
    """Return all hexagram numbers with source HTML available."""

    mapping = load_hexagram_mapping(repo_root)
    hexagrams = mapping.get("hexagrams", {})
    numbers: list[int] = []
    for number_text in sorted(hexagrams, key=int):
        number = int(number_text)
        try:
            resolve_source_file(repo_root, number)
        except FileNotFoundError:
            continue
        numbers.append(number)
    return numbers


def _normalize_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", stripped).lower()


def _palace_aliases(palace: str) -> set[str]:
    aliases = {_normalize_key(palace)}
    aliases.add(_normalize_key(palace.split("(", 1)[0]))
    aliases.add(_normalize_key(palace.split()[0]))

    chinese_match = re.search(r"[（(]([\u4e00-\u9fff]+)[）)]", palace)
    if chinese_match:
        aliases.add(_normalize_key(chinese_match.group(1)))

    return {alias for alias in aliases if alias}


def numbers_for_palace(palace_query: str, repo_root: Path = REPO_ROOT) -> list[int]:
    """Return hexagram numbers for a named palace in palace sequence order."""

    query = _normalize_key(palace_query)
    if not query:
        raise ValueError("Palace name cannot be empty.")

    mapping = load_hexagram_mapping(repo_root)
    matches: list[tuple[int, int]] = []
    for number_text, entry in mapping.get("hexagrams", {}).items():
        palace = str(entry.get("palace", ""))
        aliases = _palace_aliases(palace)
        if query in aliases:
            matches.append((int(entry.get("palace_position", 0)), int(number_text)))

    if not matches:
        raise ValueError(f"No hexagrams found for palace: {palace_query}")

    return [number for _, number in sorted(matches)]
