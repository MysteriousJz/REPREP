"""Parsing helpers for 焦氏易林注 commentary files."""

from __future__ import annotations

from html import unescape
from pathlib import Path
import json
import re

from config import REPO_ROOT
from html_extractor import ExtractedHexagram


_CHINESE_NUMERALS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
    "十三": 13,
    "十四": 14,
    "十五": 15,
    "十六": 16,
}

_ROW_RE = re.compile(r'<tr class="result" id="p\d+">(.*?)</tr>', re.S)
_HEADING_RE = re.compile(r"^(?:《\s*([^》]+)》|([\u4e00-\u9fff]+?)第[一二三四五六七八九十百零]+)$")

_NAME_ALIASES = {
    "遁": "遯",
    "豐": "丰",
    "歸妹": "归妹",
    "既濟": "既济",
    "未濟": "未济",
    "渙": "涣",
    "漸": "渐",
    "離": "离",
    "節": "节",
    "蠱": "蛊",
    "觀": "观",
    "頤": "颐",
    "剝": "剥",
    "複": "复",
    "復": "复",
    "無妄": "无妄",
    "訟": "讼",
    "師": "师",
    "賁": "贲",
    "謙": "谦",
    "殞": "损",
    "飾": "贲",
    "騫": "蹇",
    "隨": "随",
    "恆": "恒",
    "損": "损",
    "晉": "晋",
    "臨": "临",
    "大壯": "大壮",
    "大過": "大过",
    "小過": "小过",
    "坎": "坎",
    "兌": "兑",
    "噬嗑": "噬嗑",
    "嗑噬": "噬嗑",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _chinese_numeral_to_int(text: str) -> int:
    if text in _CHINESE_NUMERALS:
        return _CHINESE_NUMERALS[text]
    raise ValueError(f"Unsupported Chinese numeral: {text}")


def _volume_sort_key(path: Path) -> int:
    match = re.search(r"卷([一二三四五六七八九十百零]+)", path.name)
    if not match:
        return 999
    return _chinese_numeral_to_int(match.group(1))


def _extract_row_text(row_html: str) -> str:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S)
    if not cells:
        return ""
    return _normalize_text(re.sub(r"<[^>]+>", " ", cells[-1]))


def _strip_target_label(text: str) -> str:
    return re.sub(r"^[^。:：]+[。:：]\s*", "", text)


def _extract_target_label(text: str) -> str:
    return re.split(r"[。:：，,、]", text, maxsplit=1)[0].strip()


def _canonical_name(name: str) -> str:
    return _NAME_ALIASES.get(name, name)


def _extract_transformation_label(title: str) -> str:
    match = re.search(r"\(([^()]+之[^()]+)\)\s*$", title)
    if match:
        return match.group(1)

    match = re.search(r"([^\s]+之[^\s]+)\s*$", title)
    if match:
        return match.group(1)

    return title


def _known_hexagram_names(repo_root: Path) -> set[str]:
    mapping = json.loads((repo_root / "hexagram_file_mapping.json").read_text(encoding="utf-8"))
    return {str(entry.get("chinese_name", "")) for entry in mapping.get("hexagrams", {}).values() if entry.get("chinese_name")}


def load_forest_commentaries(repo_root: Path = REPO_ROOT) -> dict[int, list[tuple[str | None, str]]]:
    """Load raw commentary rows keyed by source number."""

    commentary_dir = repo_root / "焦氏易林注"
    known_names = _known_hexagram_names(repo_root)
    result: dict[int, list[tuple[str | None, str]]] = {}

    for path in sorted(commentary_dir.glob("*.html"), key=_volume_sort_key):
        text = path.read_text(encoding="utf-8", errors="ignore")
        volume = _volume_sort_key(path)
        section_index = -1
        current_rows: list[tuple[str | None, str]] = []

        for row_html in _ROW_RE.findall(text):
            row_text = _extract_row_text(row_html)
            if not row_text:
                continue

            heading_match = _HEADING_RE.match(row_text)
            if heading_match:
                if section_index >= 0 and current_rows:
                    source_number = (volume - 1) * 4 + section_index + 1
                    result[source_number] = current_rows
                section_index += 1
                current_rows = []
                continue

            if section_index < 0:
                continue

            target_label = _canonical_name(_extract_target_label(row_text))
            row_text = _strip_target_label(row_text)
            if row_text:
                current_rows.append((target_label if target_label in known_names else None, row_text))

        if section_index >= 0 and current_rows:
            source_number = (volume - 1) * 4 + section_index + 1
            result[source_number] = current_rows

    missing = [number for number in range(1, 65) if number not in result]
    if missing:
        raise ValueError(f"Missing commentary volumes for: {', '.join(str(n) for n in missing)}")

    return result


def attach_forest_commentaries(extracted: ExtractedHexagram, commentaries: dict[int, list[tuple[str | None, str]]]) -> None:
    """Attach commentary text to extracted Forest of Fates transformations."""

    raw_rows = commentaries.get(extracted.number, [])
    if not raw_rows:
        raise ValueError(f"No commentary found for hexagram {extracted.number}")

    pointer = 0
    for transformation in extracted.transformations:
        transformation_label = _extract_transformation_label(transformation.title)
        target_label = _canonical_name(_extract_target_label(transformation_label))

        chosen = ""
        for idx in range(pointer, len(raw_rows)):
            label, row_text = raw_rows[idx]
            if label == target_label:
                chosen = row_text
                pointer = idx + 1
                break

        if chosen:
            transformation.commentary = chosen
            continue

        transformation.commentary = ""
