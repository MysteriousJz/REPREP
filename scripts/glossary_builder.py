"""Glossary construction with §X.Y location references and pinyin sorting."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter, defaultdict
import unicodedata

from config import SECTION_NUMBERS, SECTION_ORDER
from html_extractor import ExtractedHexagram
from pinyin_converter import is_cjk
from unihan_parser import UnihanRecord


_TONE_ORDER = {
    "ā": 1, "ē": 1, "ī": 1, "ō": 1, "ū": 1, "ǖ": 1,
    "á": 2, "é": 2, "í": 2, "ó": 2, "ú": 2, "ǘ": 2,
    "ǎ": 3, "ě": 3, "ǐ": 3, "ǒ": 3, "ǔ": 3, "ǚ": 3,
    "à": 4, "è": 4, "ì": 4, "ò": 4, "ù": 4, "ǜ": 4,
}


@dataclass
class GlossaryEntry:
    char: str
    pinyin: str
    definition: str
    references: list[str]
    count: int


@dataclass
class GlossaryBuildResult:
    entries: list[GlossaryEntry]
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


def _glossary_sort_key(entry: GlossaryEntry):
    if entry.pinyin == "N/A":
        return ("zzzz", 9, ord(entry.char))
    return (_pinyin_base(entry.pinyin), _tone_number(entry.pinyin), ord(entry.char))


def _iter_section_lines(extracted: ExtractedHexagram):
    for section in SECTION_ORDER:
        for line in extracted.sections.get(section, []):
            yield section, line

    for transformation in extracted.transformations:
        yield "焦氏易林", transformation.title
        yield "焦氏易林", transformation.text


def build_glossary(
    extracted: ExtractedHexagram,
    lookup: dict[str, UnihanRecord],
) -> GlossaryBuildResult:
    """Build glossary entries and §X.Y references from extracted hexagram text."""
    per_section_counter: dict[int, Counter[str]] = {
        num: Counter() for num in SECTION_NUMBERS.values()
    }
    references: dict[str, list[str]] = defaultdict(list)
    frequencies: Counter[str] = Counter()

    for section_name, line in _iter_section_lines(extracted):
        section_num = SECTION_NUMBERS[section_name]
        for char in line:
            if not is_cjk(char):
                continue
            per_section_counter[section_num][char] += 1
            index = per_section_counter[section_num][char]
            references[char].append(f"§{section_num}.{index}")
            frequencies[char] += 1

    entries: list[GlossaryEntry] = []
    for char, count in frequencies.items():
        record = lookup.get(char, UnihanRecord())
        entries.append(
            GlossaryEntry(
                char=char,
                pinyin=record.pinyin,
                definition=record.definition,
                references=references[char],
                count=count,
            )
        )

    entries.sort(key=_glossary_sort_key)
    return GlossaryBuildResult(entries=entries, total_occurrences=sum(frequencies.values()))
