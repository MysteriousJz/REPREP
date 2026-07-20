"""Build print-ready anthology HTML files for selected classical Chinese texts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
import sys
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from library_config import DEFAULT_LOG_DIR, DEFAULT_OUTPUT_DIR, PRINT_LAYOUT, REPO_ROOT  # noqa: E402
from library_extractor import LibraryEntry, LibrarySource, extract_library_source  # noqa: E402
from library_pinyin import to_pinyin_block  # noqa: E402
from unihan_parser import build_unihan_lookup, locate_unihan_file  # noqa: E402


@dataclass(frozen=True)
class SourceSpec:
    path: Path


@dataclass(frozen=True)
class PairedChapterSpec:
    title: str
    chapter_count: int
    sources: tuple[SourceSpec, ...]
    note: str
    chapter_label_format: str = "第{n}章"


@dataclass(frozen=True)
class FileSectionSpec:
    title: str
    sources: tuple[SourceSpec, ...]
    recursive: bool = False


@dataclass(frozen=True)
class DocumentSpec:
    filename: str
    title: str
    sections: tuple[PairedChapterSpec | FileSectionSpec, ...]


def _natural_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def _xtra_file(pattern: str) -> Path:
    return next((REPO_ROOT / "xtra").glob(pattern))


def _gather_files(spec: SourceSpec, recursive: bool = False) -> list[Path]:
    path = spec.path
    if path.is_file():
        return [path]
    if recursive:
        return sorted(path.rglob("*.html"), key=lambda p: (str(p.parent), _natural_key(p)))
    return sorted(path.glob("*.html"), key=_natural_key)


def _load_sources(specs: Iterable[SourceSpec], recursive: bool = False) -> list[LibrarySource]:
    sources: list[LibrarySource] = []
    for spec in specs:
        for html_file in _gather_files(spec, recursive=recursive):
            sources.append(extract_library_source(html_file))
    return sources


def _render_text_rows(lines: list[str], lookup: dict[str, object]) -> str:
    rows = []
    pinyin_lines = to_pinyin_block(lines, lookup)
    for zh, py in zip(lines, pinyin_lines, strict=True):
        rows.append(
            "<div class=\"text-row\">"
            f"<div class=\"zh\">{escape(zh)}</div>"
            f"<div class=\"py\">{escape(py)}</div>"
            "</div>"
        )
    return "\n".join(rows)


def _render_entry(entry: LibraryEntry, lookup: dict[str, object]) -> str:
    return (
        '<article class="entry-card">'
        f"<h4>{escape(entry.title)}</h4>"
        f"{_render_text_rows(entry.lines, lookup)}"
        "</article>"
    )


def _render_source(source: LibrarySource, lookup: dict[str, object]) -> str:
    entries = "\n".join(_render_entry(entry, lookup) for entry in source.entries)
    return (
        '<section class="source-block">'
        f"<h3>{escape(source.title)}</h3>"
        f"{entries}"
        "</section>"
    )


def _render_file_section(title: str, sources: list[LibrarySource], lookup: dict[str, object]) -> str:
    body = "\n".join(_render_source(source, lookup) for source in sources)
    return (
        '<section class="major-section file-section">'
        f"<h2>{escape(title)}</h2>"
        f"{body}"
        "</section>"
    )


def _render_paired_chapters(spec: PairedChapterSpec, lookup: dict[str, object]) -> str:
    sources: list[LibrarySource] = []
    for source in spec.sources:
        loaded = _load_sources((source,), recursive=False)
        if not loaded:
            raise FileNotFoundError(f"No HTML files found for paired source: {source.path}")
        sources.append(loaded[0])
    chapter_rows = []
    for chapter_index in range(spec.chapter_count):
        chapter_blocks = []
        for source in sources:
            if chapter_index >= len(source.entries):
                continue
            chapter_blocks.append(_render_source(
                LibrarySource(
                    source_path=source.source_path,
                    title=source.title,
                    entries=[source.entries[chapter_index]],
                ),
                lookup,
            ))
        chapter_rows.append(
            '<section class="paired-chapter">'
            f"<h3>{escape(spec.chapter_label_format.format(n=chapter_index + 1))}</h3>"
            f"<p class=\"chapter-note\">{escape(spec.note)}</p>"
            + "\n".join(chapter_blocks)
            + "</section>"
        )
    return (
        '<section class="major-section paired-section">'
        f"<h2>{escape(spec.title)}</h2>"
        + "\n".join(chapter_rows)
        + "</section>"
    )


def _render_document(spec: DocumentSpec, lookup: dict[str, object]) -> str:
    blocks = []
    for section in spec.sections:
        if isinstance(section, PairedChapterSpec):
            blocks.append(_render_paired_chapters(section, lookup))
        else:
            sources = _load_sources(section.sources, recursive=section.recursive)
            blocks.append(_render_file_section(section.title, sources, lookup))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(spec.title)}</title>
  <style>
    @page {{
      size: {PRINT_LAYOUT.page_size};
      margin: {PRINT_LAYOUT.margin_top} {PRINT_LAYOUT.margin_right} {PRINT_LAYOUT.margin_bottom} {PRINT_LAYOUT.margin_left};
    }}

    * {{ box-sizing: border-box; }}
    body {{
      font-family: {PRINT_LAYOUT.body_font};
      margin: 0;
      color: #111;
      line-height: 1.5;
    }}

    h1 {{
      text-align: center;
      margin: 0 0 0.25in 0;
      font-size: {PRINT_LAYOUT.title_size};
    }}

    h2 {{
      margin: 0 0 0.12in 0;
      padding-bottom: 0.04in;
      border-bottom: 1px solid #333;
      font-size: 18pt;
    }}

    h3 {{
      margin: 0 0 0.08in 0;
      font-size: 15pt;
    }}

    h4 {{
      margin: 0 0 0.06in 0;
      font-size: 13pt;
    }}

    .major-section {{
      margin: 0 0 0.25in 0;
      break-inside: avoid;
    }}

    .file-section, .paired-section {{
      break-before: page;
    }}

    .file-section:first-of-type, .paired-section:first-of-type {{
      break-before: auto;
    }}

    .source-block {{
      margin: 0 0 0.18in 0;
      padding: 0.08in 0 0.02in 0;
      break-inside: avoid;
    }}

    .entry-card {{
      margin: 0 0 0.14in 0;
      padding: 0.08in 0 0.02in 0;
      border-top: 1px dotted #ddd;
      break-inside: avoid;
    }}

    .text-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.35in;
      padding: 0.04in 0;
      border-bottom: 1px dotted #eee;
    }}

    .zh {{ font-size: {PRINT_LAYOUT.line_chinese}; letter-spacing: 0.02em; }}
    .py {{ font-size: {PRINT_LAYOUT.line_pinyin}; color: #444; }}

    .chapter-note {{
      margin: -0.04in 0 0.08in 0;
      color: #666;
      font-size: 10.5pt;
    }}
  </style>
</head>
<body>
  <h1>{escape(spec.title)}</h1>
  {"".join(blocks)}
</body>
</html>"""


DOCUMENTS = (
    DocumentSpec(
        filename="daodejing_collection.html",
        title="Daodejing Collection",
        sections=(
            # The scanned 老子道德經 pages are OCR-heavy and do not align cleanly by chapter,
            # so the chapter-by-chapter merge uses the cleaner Wang Bi edition in xtra/.
            # Paired by chapter order; first source preserves Wang Bi text and commentary, second source preserves Heshang Gong commentary.
            PairedChapterSpec(
                title="老子道德經（81章）",
                chapter_count=81,
                sources=(
                    SourceSpec(_xtra_file("道德真經註 - Chinese Text Project.html")),
                    SourceSpec(_xtra_file("河上公老子注 - 中國哲學書電子化計劃.html")),
                ),
                note="按章節順序配對；第一個來源保留王弼本正文與注解，第二個來源保留河上公注。",
            ),
            FileSectionSpec("孝經", (SourceSpec(REPO_ROOT / "孝經"),)),
            FileSectionSpec("洪範", (SourceSpec(REPO_ROOT / "洪範"),)),
            FileSectionSpec("列子", (SourceSpec(REPO_ROOT / "道可道/列子"),)),
            FileSectionSpec("莊子（內篇、外篇、雜篇）", (SourceSpec(REPO_ROOT / "道可道/莊子"),), recursive=True),
            FileSectionSpec("鶡冠子", (SourceSpec(REPO_ROOT / "道可道/鶡冠子"),)),
        ),
    ),
    DocumentSpec(
        filename="yijing_commentaries_anthology.html",
        title="Yijing Commentaries Anthology",
        sections=(
            FileSectionSpec(
                "十翼與相關注疏",
                (
                    SourceSpec(_xtra_file("周易 _ 序卦 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易 _ 雜卦 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易注 _ 系辭上卷七周易系辭上第七 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易注 _ 系辭下卷八周易系辭下第八 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易注 _ 說卦卷九說卦第九 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易注 _ 說卦卷九《周易·序卦》第十 - 中國哲學書電子化計劃.html")),
                    SourceSpec(_xtra_file("周易注 _ 說卦卷九周易·雜卦》第十一 - 中國哲學書電子化計劃.html")),
                ),
            ),
        ),
    ),
    DocumentSpec(
        filename="tcm_classics_collection.html",
        title="TCM Classics Collection",
        sections=(
            FileSectionSpec("黃帝內經", (SourceSpec(REPO_ROOT / "黃帝內經"),), recursive=True),
            FileSectionSpec("難經", (SourceSpec(REPO_ROOT / "難經"),), recursive=True),
            FileSectionSpec("傷寒論", (SourceSpec(REPO_ROOT / "傷寒論"),), recursive=True),
            FileSectionSpec("金匱要略", (SourceSpec(REPO_ROOT / "金匱要略"),), recursive=True),
        ),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate print-ready classical Chinese anthologies")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_DIR, help="Log directory")
    parser.add_argument("--unihan", type=Path, default=REPO_ROOT, help="Path to Unihan files or repo root")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    args.logs.mkdir(parents=True, exist_ok=True)

    unihan_base = args.unihan
    if not unihan_base.exists():
        unihan_base = REPO_ROOT
    elif unihan_base.is_file():
        unihan_base = unihan_base.parent

    readings_file = locate_unihan_file([unihan_base / "Unihan_Readings.txt"], "readings")
    dict_like_file = locate_unihan_file([unihan_base / "Unihan_DictionaryLikeData.txt"], "dictionary_like")
    if readings_file is None:
        print("[error] Unihan_Readings.txt not found", file=sys.stderr)
        return 3

    try:
        lookup = build_unihan_lookup(readings_file, dict_like_file)
    except Exception as exc:
        print(f"[error] Failed to parse Unihan files: {exc}", file=sys.stderr)
        return 4

    started = datetime.now(timezone.utc)
    summary: list[dict[str, object]] = []
    assumptions = [
        "The repository includes OCR-heavy 老子道德經 pages, but they do not split cleanly by chapter; the Laozi pairing uses the cleaner xtra/道德真經註 edition plus xtra/河上公老子注 instead.",
        "The Ten Wings anthology uses the dedicated xtra files present in this snapshot; the repository does not contain standalone xtra files for every named subsection.",
    ]

    for document in DOCUMENTS:
        html = _render_document(document, lookup)
        output_path = args.output / document.filename
        output_path.write_text(html, encoding="utf-8")
        summary.append(
            {
                "filename": str(output_path),
                "title": document.title,
                "sections": len(document.sections),
            }
        )
        print(f"[ok] {output_path}")

    log_payload = {
        "timestamp": started.isoformat(),
        "documents": summary,
        "assumptions": assumptions,
    }
    log_file = args.logs / "classics_collections_log.json"
    log_file.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] Log: {log_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
