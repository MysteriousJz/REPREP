"""HTML text extraction for phase-2 hexagram files."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re

from config import SECTION_ORDER


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Transformation:
    title: str
    text: str
    commentary: str = ""


@dataclass
class ExtractedHexagram:
    number: int
    name: str
    symbol: str
    title: str
    sections: dict[str, list[str]] = field(default_factory=dict)
    transformations: list[Transformation] = field(default_factory=list)


class _Phase2Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_body = False
        self.skip_depth = 0
        self.heading_depth = 0
        self.in_h2 = False
        self.h2_buf: list[str] = []

        self.in_h1 = False
        self.h1_buf: list[str] = []

        self.in_symbol_div = False
        self.symbol_buf: list[str] = []

        self.in_transform_header = False
        self.current_transform_title: str | None = None
        self.pending_transform_text: list[str] = []

        self.current_section = ""
        self.sections = {section: [] for section in SECTION_ORDER}
        self.transformations: list[Transformation] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag_l = tag.lower()
        attrs_dict = {k: (v or "") for k, v in attrs}
        class_attr = attrs_dict.get("class", "")

        if tag_l == "body":
            self.in_body = True
        if not self.in_body:
            return

        if tag_l in {"style", "script"}:
            self.skip_depth += 1

        if tag_l in {"h1", "h2", "h3"}:
            self.heading_depth += 1

        if tag_l == "h1":
            self.in_h1 = True
            self.h1_buf = []

        if tag_l == "h2":
            self.in_h2 = True
            self.h2_buf = []

        if tag_l == "div" and "hexagram-symbol" in class_attr:
            self.in_symbol_div = True
            self.symbol_buf = []

        if tag_l == "div" and "transformation-header" in class_attr:
            self.in_transform_header = True

    def handle_endtag(self, tag: str):
        tag_l = tag.lower()

        if tag_l == "body":
            self.in_body = False
            return

        if not self.in_body:
            return

        if tag_l in {"style", "script"} and self.skip_depth > 0:
            self.skip_depth -= 1

        if tag_l in {"h1", "h2", "h3"} and self.heading_depth > 0:
            self.heading_depth -= 1

        if tag_l == "h1":
            self.in_h1 = False

        if tag_l == "h2":
            heading = _normalize_text("".join(self.h2_buf))
            for section in SECTION_ORDER:
                if section in heading:
                    self.current_section = section
                    break
            self.in_h2 = False
            self.h2_buf = []

        if tag_l == "div" and self.in_symbol_div:
            self.in_symbol_div = False

        if tag_l == "div" and self.in_transform_header:
            self.in_transform_header = False
            self.current_transform_title = _normalize_text("".join(self.pending_transform_text))
            self.pending_transform_text = []

        if tag_l == "p" and self.current_section == "焦氏易林":
            text = _normalize_text("".join(self.pending_transform_text))
            if self.current_transform_title and text:
                self.transformations.append(
                    Transformation(title=self.current_transform_title, text=text)
                )
            self.pending_transform_text = []

    def handle_data(self, data: str):
        if not self.in_body or self.skip_depth > 0:
            return

        if self.in_h1:
            self.h1_buf.append(data)
            return

        if self.in_h2:
            self.h2_buf.append(data)

        if self.in_symbol_div:
            self.symbol_buf.append(data)
            return

        if self.in_transform_header or (self.current_section == "焦氏易林"):
            self.pending_transform_text.append(data)

        if self.heading_depth > 0:
            return

        line = _normalize_text(unescape(data))
        if line and self.current_section and self.current_section != "焦氏易林":
            self.sections[self.current_section].append(line)


def extract_hexagram_from_html(source_path: Path, number: int) -> ExtractedHexagram:
    """Extract section text and transformation data from a source HTML file."""
    parser = _Phase2Parser()
    parser.feed(source_path.read_text(encoding="utf-8"))

    title = _normalize_text("".join(parser.h1_buf)) or source_path.stem
    name_match = re.search(r"^\s*([\u3400-\u9fff]+)", title)
    name = name_match.group(1) if name_match else f"卦{number}"
    symbol = _normalize_text("".join(parser.symbol_buf)) or ""

    return ExtractedHexagram(
        number=number,
        name=name,
        symbol=symbol,
        title=title,
        sections=parser.sections,
        transformations=parser.transformations,
    )
