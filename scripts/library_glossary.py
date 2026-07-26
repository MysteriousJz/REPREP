"""Glossary building for classical Chinese library texts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable
import unicodedata

from library_extractor import LibraryEntry
from library_pinyin import is_cjk
from unihan_parser import UnihanRecord


_TONE_ORDER = {
    "ā": 1,
    "ē": 1,
    "ī": 1,
    "ō": 1,
    "ū": 1,
    "ǖ": 1,
    "á": 2,
    "é": 2,
    "í": 2,
    "ó": 2,
    "ú": 2,
    "ǘ": 2,
    "ǎ": 3,
    "ě": 3,
    "ǐ": 3,
    "ǒ": 3,
    "ǔ": 3,
    "ǚ": 3,
    "à": 4,
    "è": 4,
    "ì": 4,
    "ò": 4,
    "ù": 4,
    "ǜ": 4,
}


@dataclass
class LibraryGlossaryEntry:
    char: str
    pinyin: str
    definition: str
    references: list[str]
    count: int


@dataclass
class LibraryGlossary:
    entries: list[LibraryGlossaryEntry]
    total_occurrences: int


def _tone_number(pinyin: str) -> int:
    for char in pinyin:
        if char in _TONE_ORDER:
            return _TONE_ORDER[char]
    return 5


def _pinyin_base(pinyin: str) -> str:
    normalized = unicodedata.normalize("NFD", pinyin)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace("ü", "u").lower()


def _glossary_sort_key(entry: LibraryGlossaryEntry):
    if entry.pinyin == "N/A":
        return ("zzzz", 9, ord(entry.char))
    return (_pinyin_base(entry.pinyin), _tone_number(entry.pinyin), ord(entry.char))


def build_library_glossary(
    entries: Iterable[LibraryEntry],
    lookup: dict[str, UnihanRecord],
    book_slug: str,
) -> LibraryGlossary:
    """Build a deduplicated glossary from all extracted entries."""
    references: dict[str, list[str]] = defaultdict(list)
    frequencies: Counter[str] = Counter()

    for entry in entries:
        for line_index, line in enumerate(entry.lines, start=1):
            ref = f"§{book_slug}.{entry.book_index}.{line_index}"
            for char in line:
                if not is_cjk(char):
                    continue
                if not references[char] or references[char][-1] != ref:
                    references[char].append(ref)
                frequencies[char] += 1

    result: list[LibraryGlossaryEntry] = []
    for char, count in frequencies.items():
        record = lookup.get(char, UnihanRecord())
        result.append(
            LibraryGlossaryEntry(
                char=char,
                pinyin=record.pinyin,
                definition=record.definition,
                references=references[char],
                count=count,
            )
        )

    result.sort(key=_glossary_sort_key)
    return LibraryGlossary(entries=result, total_occurrences=sum(frequencies.values()))

