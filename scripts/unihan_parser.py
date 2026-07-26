"""Unihan parsing utilities for pinyin and dictionary definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import re


@dataclass
class UnihanRecord:
    """Character-level Unihan record."""

    pinyin: str = "N/A"
    definition: str = "(character not found in Unihan database)"


_TONE_MARKS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
}


def _apply_tone_mark(syllable: str) -> str:
    token = syllable.strip().lower().replace("u:", "ü").replace("v", "ü")
    match = re.match(r"^([a-zü]+)([1-5])?$", token)
    if not match:
        return token

    base, tone = match.groups()
    if not tone or tone == "5":
        return base

    tone_index = int(tone) - 1
    if "a" in base:
        idx, vowel = base.index("a"), "a"
    elif "e" in base:
        idx, vowel = base.index("e"), "e"
    elif "ou" in base:
        idx, vowel = base.index("o"), "o"
    else:
        idx = -1
        vowel = ""
        for i in range(len(base) - 1, -1, -1):
            if base[i] in "aeiouü":
                idx = i
                vowel = base[i]
                break

    if idx < 0 or not vowel:
        return base

    return base[:idx] + _TONE_MARKS[vowel][tone_index] + base[idx + 1 :]


def _iter_unihan_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            yield parts[0], parts[1], "\t".join(parts[2:]).strip()


def _parse_unihan_file(path: Path, lookup: Dict[str, UnihanRecord]) -> None:
    for codepoint, field_name, value in _iter_unihan_lines(path):
        if not codepoint.startswith("U+") or not value:
            continue
        try:
            char = chr(int(codepoint[2:], 16))
        except ValueError:
            continue

        record = lookup.setdefault(char, UnihanRecord())
        if field_name == "kMandarin":
            record.pinyin = _apply_tone_mark(value.split()[0])
        elif field_name == "kDefinition":
            record.definition = value


def locate_unihan_file(candidates: list[Path], label: str) -> Optional[Path]:
    """Return the first existing file from candidate paths."""
    for path in candidates:
        if path.exists():
            return path
    return None


def build_unihan_lookup(readings_file: Path, dictionary_like_file: Optional[Path] = None) -> Dict[str, UnihanRecord]:
    """Build Unihan lookup from available files.

    Notes:
    - Current data often has both kMandarin and kDefinition in Unihan_Readings.txt.
    - Parsing both files keeps compatibility with alternate snapshots.
    """
    if not readings_file.exists():
        raise FileNotFoundError(f"Unihan readings file not found: {readings_file}")

    lookup: Dict[str, UnihanRecord] = {}
    _parse_unihan_file(readings_file, lookup)

    if dictionary_like_file and dictionary_like_file.exists():
        _parse_unihan_file(dictionary_like_file, lookup)

    if not lookup:
        raise RuntimeError("No Unihan entries were parsed. Check input files.")

    return lookup
