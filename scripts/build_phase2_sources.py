"""Build phase-2 hexagram source HTML from the raw CText exports."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SECTION_TITLES = {
    "判斷辭": "一、判斷辭 (Hexagram Judgment)",
    "彖傳": "二、彖傳 (Tuàn Commentary)",
    "象傳": "三、象傳 (Xiàng Commentary)",
    "爻辭": "四、爻辭 (Line Texts and Commentaries)",
    "文言": "五、文言 (Wén Yán Commentary)",
    "京氏易傳": "六、京氏易傳 (Jing Fang's Transmission)",
    "周易注": "七、周易注 (Wang Bi's Commentary)",
    "焦氏易林": "八、焦氏易林 (Forest of Fates - All 64 Transformations)",
}

LINE_RE = re.compile(r"^(?:初|六|九|上|用)[^：:]*[：:]")


def _clean_text(fragment: str) -> str:
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment)
    return re.sub(r"\s+", " ", fragment).strip()


def _extract_rows(path: Path, row_pattern: str) -> list[list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = []
    for row_html in re.findall(row_pattern, text, flags=re.S):
        cells = [
            _clean_text(cell)
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S)
        ]
        if cells:
            rows.append(cells)
    return rows


def _extract_zhou_yi(path: Path) -> tuple[dict[str, list[str]], list[tuple[int, str, str, str]], list[str]]:
    rows = _extract_rows(path, r'<tr id="[^"]+">(.*?)</tr>')
    sections = {
        "判斷辭": [],
        "彖傳": [],
        "象傳": [],
        "爻辭": [],
        "文言": [],
    }
    line_blocks: list[tuple[int, str, str, str]] = []
    line_number = 1

    if len(rows) >= 1:
        sections["判斷辭"].append(rows[0][-1])
    if len(rows) >= 2:
        sections["彖傳"].append(rows[1][-1])
    if len(rows) >= 3:
        sections["象傳"].append(rows[2][-1])

    index = 3
    while index < len(rows):
        label = rows[index][1] if len(rows[index]) > 1 else ""
        content = rows[index][-1]

        if label.startswith("文言"):
            sections["文言"].append(content)
            index += 1
            while index < len(rows):
                sections["文言"].append(rows[index][-1])
                index += 1
            break

        if LINE_RE.match(content):
            title = content.split("：", 1)[0].split(":", 1)[0]
            commentary = ""
            if index + 1 < len(rows):
                next_label = rows[index + 1][1] if len(rows[index + 1]) > 1 else ""
                next_content = rows[index + 1][-1]
                if not LINE_RE.match(next_content) and not next_label.startswith("文言"):
                    commentary = next_content
                    index += 1
            line_blocks.append((line_number, title, content, commentary))
            line_number += 1
        elif sections["文言"]:
            sections["文言"].append(content)

        index += 1

    return sections, line_blocks, sections["文言"]


def _extract_paragraphs(path: Path, row_pattern: str) -> list[str]:
    rows = _extract_rows(path, row_pattern)
    paragraphs = []
    for cells in rows:
        content = cells[-1]
        if content:
            paragraphs.append(content)
    return paragraphs


def _build_html(
    number: int,
    symbol: str,
    name: str,
    pinyin: str,
    palace: str,
    palace_position: int,
    zhou_yi: tuple[dict[str, list[str]], list[tuple[int, str, str, str]], list[str]],
    jing_fang: list[str],
    wang_bi: list[str],
    transformations: list[tuple[str, str]],
) -> str:
    sections, line_blocks, wenyan = zhou_yi
    body_sections = []

    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["判斷辭"]}</h2><div class="section">{sections["判斷辭"][0]}</div></section>'
    )
    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["彖傳"]}</h2><div class="section">{sections["彖傳"][0]}</div></section>'
    )
    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["象傳"]}</h2><div class="section">{sections["象傳"][0]}</div></section>'
    )

    line_html = []
    for line_number, title, content, commentary in line_blocks:
        line_html.append(
            "<div class=\"section\">"
            f"<h3>{html.escape(title)} (Line {line_number})</h3>"
            f"<div class=\"line-text\">{html.escape(content)}</div>"
            + (f"<div class=\"commentary\">{html.escape(commentary)}</div>" if commentary else "")
            + "</div>"
        )
    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["爻辭"]}</h2>{"".join(line_html)}</section>'
    )

    if wenyan:
        body_sections.append(
            f'<section class="section-block"><h2>{SECTION_TITLES["文言"]}</h2>'
            + "".join(f"<div class=\"section\"><p>{html.escape(p)}</p></div>" for p in wenyan)
            + "</section>"
        )

    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["京氏易傳"]}</h2>'
        + "".join(f"<div class=\"section\"><p>{html.escape(p)}</p></div>" for p in jing_fang)
        + "</section>"
    )

    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["周易注"]}</h2>'
        + "".join(f"<div class=\"section\"><p>{html.escape(p)}</p></div>" for p in wang_bi)
        + "</section>"
    )

    body_sections.append(
        f'<section class="section-block"><h2>{SECTION_TITLES["焦氏易林"]}</h2>'
        + "".join(
            "<div class=\"transformation\">"
            f"<div class=\"transformation-header\">{html.escape(title)}</div>"
            f"<p>{html.escape(poem)}</p>"
            "</div>"
            for title, poem in transformations
        )
        + "</section>"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(symbol)} {html.escape(name)} ({html.escape(pinyin)}) - Hexagram {number}</title>
  <style>
    body {{
      font-family: "Noto Serif SC", "Source Han Serif", SimSun, serif;
      font-size: 20pt;
      line-height: 2.0;
      max-width: 800px;
      margin: 40px auto;
      padding: 20px 60px;
      background-color: #fefefe;
      color: #222;
    }}
    h1 {{ font-size: 32pt; text-align: center; margin: 40px 0; }}
    h2 {{ font-size: 24pt; margin-top: 60px; margin-bottom: 20px; border-bottom: 2px solid #333; }}
    h3 {{ font-size: 20pt; margin-top: 40px; margin-bottom: 15px; color: #555; }}
    .hexagram-symbol {{ font-size: 48pt; text-align: center; margin: 20px 0; }}
    .section {{ margin: 30px 0; padding: 20px; border-left: 4px solid #ddd; }}
    .line-text {{ margin: 20px 0; padding-left: 20px; }}
    .commentary {{ margin: 10px 0 30px 40px; color: #444; font-size: 18pt; }}
    .transformation {{ margin: 25px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
    .transformation-header {{ font-weight: bold; font-size: 22pt; margin-bottom: 10px; color: #333; }}
  </style>
</head>
<body>
  <div class="hexagram-symbol">{html.escape(symbol)}</div>
  <h1>{html.escape(name)} ({html.escape(pinyin)}) - Hexagram {number}</h1>
  <p style="text-align: center; font-size: 18pt; color: #666;">Palace: {html.escape(palace)} | Position: {palace_position} ({'Pure Palace Hexagram' if palace_position == 1 else f'Position {palace_position} within {html.escape(palace)}'})</p>
  {' '.join(body_sections)}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build phase-2 source HTML files from raw CText exports")
    parser.add_argument("--numbers", required=True, help="Comma-separated hexagram numbers")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repository root directory")
    args = parser.parse_args()

    mapping = json.loads((args.repo_root / "hexagram_file_mapping.json").read_text(encoding="utf-8"))
    names = {i: mapping["hexagrams"][str(i)]["chinese_name"] for i in range(1, 65)}

    requested_numbers = []
    for token in args.numbers.split(","):
        token = token.strip()
        if token:
            requested_numbers.append(int(token))

    for number in sorted(set(requested_numbers)):
        hexagram = mapping["hexagrams"][str(number)]
        symbol = hexagram["symbol"]
        name = hexagram["chinese_name"]
        pinyin = hexagram["pinyin_name"]
        palace = hexagram["palace"]
        palace_position = hexagram["palace_position"]

        zhou_yi = _extract_zhou_yi(args.repo_root / hexagram["files"]["zhou_yi"])
        jing_fang = _extract_paragraphs(args.repo_root / hexagram["files"]["jing_fang"], r'<tr id="[^"]+">(.*?)</tr>')
        wang_bi = _extract_paragraphs(args.repo_root / hexagram["files"]["wang_bi"], r'<tr class="result"[^>]*>(.*?)</tr>')

        forest_rows = _extract_rows(args.repo_root / hexagram["files"]["forest_of_fates"], r'<tr id="[^"]+">(.*?)</tr>')
        transformations: list[tuple[str, str]] = []
        for index, row in enumerate(forest_rows, start=1):
            content = row[-1]
            target = names[index]
            poem = re.sub(r"^[^：:]+[：:]\s*", "", content)
            transformations.append((f"{name}之{target}", poem))

        output_path = args.repo_root / f"hexagram_{number:02d}_{name}.html"
        output_path.write_text(
            _build_html(
                number,
                symbol,
                name,
                pinyin,
                palace,
                palace_position,
                zhou_yi,
                jing_fang,
                wang_bi,
                transformations,
            ),
            encoding="utf-8",
        )
        print(f"[ok] Wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
