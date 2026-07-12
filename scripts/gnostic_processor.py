"""CLI for parsing James DeKorne's Gnostic Book of Changes HTML pages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gnostic_config import DEFAULT_HTML_DIR, DEFAULT_JSON_DIR, DEFAULT_METADATA_PATH, DEFAULT_SOURCE_DIR, DEFAULT_GLOSSARY_PATH, line_output_name  # noqa: E402
from gnostic_html_extractor import parse_gnostic_hexagram  # noqa: E402
from gnostic_html_generator import render_glossary_html, render_hexagram_html  # noqa: E402
from gnostic_json_generator import all_hexagrams_to_dict, build_metadata, hexagram_to_dict, write_json  # noqa: E402


def _parse_number_range(token: str) -> list[int]:
    token = token.strip()
    if not token:
        return []
    if "-" in token:
        start_text, end_text = token.split("-", 1)
        start = int(start_text)
        end = int(end_text)
        step = 1 if end >= start else -1
        return list(range(start, end + step, step))
    return [int(token)]


def _parse_selection(args: argparse.Namespace, source_dir: Path) -> list[int]:
    if args.number is not None:
        if args.number < 1 or args.number > 64:
            raise ValueError("Hexagram number must be between 1 and 64")
        return [args.number]
    if args.numbers:
        numbers: list[int] = []
        for part in args.numbers.split(","):
            numbers.extend(_parse_number_range(part))
        unique = sorted(set(numbers))
        for number in unique:
            if number < 1 or number > 64:
                raise ValueError("Hexagram number must be between 1 and 64")
        return unique
    discovered: list[int] = []
    for path in source_dir.rglob("*.htm*"):
        match = re.search(r"Hexagram\s+(\d+)", path.name, re.I) or re.search(r"hexagram(\d+)", path.name, re.I)
        if match:
            discovered.append(int(match.group(1)))
    return sorted(set(discovered))


def _find_source_file(source_dir: Path, number: int) -> Path:
    preferred_patterns = [
        f"*Hexagram {number}.htm*",
        f"*Hexagram {number:02d}.htm*",
        f"*hexagram{number}.htm*",
        f"*hex{number}.htm*",
    ]
    candidates: list[Path] = []
    for pattern in preferred_patterns:
        candidates.extend(source_dir.rglob(pattern))
    if not candidates:
        for path in source_dir.rglob("*.htm*"):
            if re.search(rf"Hexagram\s+0*{number}(?!\d)", path.name, re.I) or re.search(rf"hex{number}(?!\d)", path.name, re.I):
                candidates.append(path)
    if not candidates:
        raise FileNotFoundError(f"No source HTML found for hexagram {number}")
    candidates = sorted(set(candidates), key=lambda p: (len(p.name), p.name))
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Gnostic Book of Changes HTML into JSON and HTML outputs")
    selection = parser.add_mutually_exclusive_group(required=False)
    selection.add_argument("--number", type=int, help="Process a single hexagram")
    selection.add_argument("--numbers", type=str, help="Process a comma-separated list or ranges like 1-64")
    parser.add_argument("--dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Directory containing the source HTML files")
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_DIR, help="Output directory")
    parser.add_argument("--format", choices=["json", "html", "both"], default="both", help="Output format")
    parser.add_argument("--no-glossary", action="store_true", help="Skip glossary output")
    args = parser.parse_args()

    source_dir = args.dir.resolve()
    output_dir = args.output.resolve()
    json_dir = output_dir
    html_dir = output_dir / "html"
    json_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    numbers = _parse_selection(args, source_dir)
    if not numbers:
        print("[error] No hexagrams found", file=sys.stderr)
        return 2

    extracted: list = []
    source_files: list[str] = []
    for number in numbers:
        source_path = _find_source_file(source_dir, number)
        source_files.append(str(source_path))
        extracted.append(parse_gnostic_hexagram(source_path, number))

    metadata = build_metadata(extracted, source_files)

    if args.format in {"json", "both"}:
        for hexagram in extracted:
            write_json(json_dir / line_output_name(hexagram.number, hexagram.titles.main_title, "json"), hexagram_to_dict(hexagram))
        write_json(json_dir / "all_hexagrams.json", all_hexagrams_to_dict(extracted, metadata))
        write_json(DEFAULT_METADATA_PATH if output_dir == DEFAULT_JSON_DIR else output_dir / "metadata.json", {
            "generated_at": generated_at,
            **metadata,
        })

    if args.format in {"html", "both"}:
        for hexagram in extracted:
            html_path = html_dir / line_output_name(hexagram.number, hexagram.titles.main_title, "html")
            html_path.write_text(render_hexagram_html(hexagram), encoding="utf-8")
        if not args.no_glossary:
            (output_dir / "glossary.html").write_text(
                render_glossary_html(metadata["glossary_terms"], metadata["translators"]),
                encoding="utf-8",
            )

    print(f"[ok] Processed {len(extracted)} hexagram(s)")
    for source, hexagram in zip(source_files, extracted, strict=True):
        print(f" - {hexagram.number}: {hexagram.titles.main_title} <- {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
