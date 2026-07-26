"""Data models for James DeKorne Gnostic hexagram parsing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GnosticTitles:
    main_title: str = ""
    alt_titles: list[str] = field(default_factory=list)
    number: int = 0


@dataclass
class GnosticSection:
    translations: dict[str, str] = field(default_factory=dict)


@dataclass
class GnosticLine:
    number: int
    title: str = ""
    translations: dict[str, str] = field(default_factory=dict)
    commentaries: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class GnosticHexagram:
    number: int
    titles: GnosticTitles = field(default_factory=GnosticTitles)
    judgment: GnosticSection = field(default_factory=GnosticSection)
    image: GnosticSection = field(default_factory=GnosticSection)
    commentary: GnosticSection = field(default_factory=GnosticSection)
    notes_and_paraphrases: str = ""
    lines: list[GnosticLine] = field(default_factory=list)
    editor_notes: list[str] = field(default_factory=list)

