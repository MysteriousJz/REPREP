"""Chinese-to-pinyin helpers for library processing."""

from __future__ import annotations

from unihan_parser import UnihanRecord


def is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0x20000 <= codepoint <= 0x2A6DF
        or 0x2A700 <= codepoint <= 0x2B73F
        or 0x2B740 <= codepoint <= 0x2B81F
        or 0x2B820 <= codepoint <= 0x2CEAF
        or 0x2CEB0 <= codepoint <= 0x2EBEF
        or 0x30000 <= codepoint <= 0x3134F
    )


def to_pinyin_line(text: str, lookup: dict[str, UnihanRecord]) -> str:
    """Convert one line of mixed Chinese text to pinyin."""
    out: list[str] = []
    in_word = False

    for char in text:
        if is_cjk(char):
            pinyin = lookup.get(char, UnihanRecord()).pinyin
            if in_word:
                out.append(" ")
            out.append(pinyin)
            in_word = True
            continue

        if char.isspace():
            out.append(" ")
            in_word = False
            continue

        out.append(char)
        in_word = False

    return "".join(out).strip()


def to_pinyin_block(lines: list[str], lookup: dict[str, UnihanRecord]) -> list[str]:
    """Convert multiple lines while preserving line boundaries."""
    return [to_pinyin_line(line, lookup) for line in lines]

