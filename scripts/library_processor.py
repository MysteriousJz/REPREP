"""CLI entrypoint for classical Chinese library processing."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import time

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from library_config import (  # noqa: E402
    DEFAULT_LOG_DIR,
    DEFAULT_OUTPUT_DIR,
    REPO_ROOT,
    cached_slug,
    clean_site_title,
)
from library_extractor import LibraryEntry, LibrarySource, extract_library_source  # noqa: E402
from library_glossary import build_library_glossary  # noqa: E402
from library_html_generator import (  # noqa: E402
    LibraryBook,
    generate_entry_html,
    generate_glossary_html,
    generate_index_html,
    generate_merged_html,
)
from unihan_parser import build_unihan_lookup, locate_unihan_file  # noqa: E402


IGNORED_DIRECTORIES = {
    "output",
    "logs",
    "scripts",
    "auxiliary",
    "emoji",
    "extracted",
    ".git",
}


def _natural_key(path: Path):
    import re

    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def _discover_book_dirs(root: Path, recursive: bool) -> list[Path]:
    if root.is_file():
        return [root.parent]

    if not recursive:
        return [root] if any(root.glob("*.html")) else []

    discovered: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        dir_path = Path(directory)
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRECTORIES and not name.startswith(".")]
        if dir_path.name in IGNORED_DIRECTORIES:
            continue
        if any(name.lower().endswith(".html") for name in filenames):
            discovered.append(dir_path)
    discovered.sort(key=lambda p: (len(p.parts), str(p)))
    return discovered


def _load_sources(book_dir: Path) -> list[LibrarySource]:
    sources: list[LibrarySource] = []
    for html_file in sorted(book_dir.glob("*.html"), key=_natural_key):
        try:
            sources.append(extract_library_source(html_file))
        except Exception as exc:
            raise RuntimeError(f"Failed to extract {html_file}: {exc}") from exc
    return sources


def _assign_book_indices(entries: list[LibraryEntry]) -> list[LibraryEntry]:
    for idx, entry in enumerate(entries, start=1):
        entry.book_index = idx
    return entries


def _resolve_book_title(book_dir: Path, sources: list[LibrarySource], custom_name: str | None) -> str:
    if custom_name:
        return custom_name
    if len(sources) == 1:
        return sources[0].title or book_dir.name
    return clean_site_title(book_dir.name) or book_dir.name


def _prepare_book(book_dir: Path, sources: list[LibrarySource], custom_name: str | None) -> LibraryBook:
    entries: list[LibraryEntry] = []
    for source in sources:
        entries.extend(source.entries)
    _assign_book_indices(entries)
    title = _resolve_book_title(book_dir, sources, custom_name)
    return LibraryBook(
        title=title,
        slug=cached_slug(title),
        sources=sources,
        entries=entries,
    )


def _write_entry_pages(book: LibraryBook, output_dir: Path, lookup: dict[str, object]) -> list[Path]:
    generated: list[Path] = []
    for entry in book.entries:
        html = generate_entry_html(book, entry, lookup)
        output_path = output_dir / f"chapter_{entry.book_index:03d}.html"
        output_path.write_text(html, encoding="utf-8")
        generated.append(output_path)
    return generated


def _write_book_assets(book: LibraryBook, output_dir: Path, lookup: dict[str, object], glossary) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = _write_entry_pages(book, output_dir, lookup)
    index_path = output_dir / "index.html"
    index_path.write_text(generate_index_html(book), encoding="utf-8")
    glossary_path = output_dir / "glossary.html"
    glossary_path.write_text(generate_glossary_html(book, glossary), encoding="utf-8")
    generated.extend([index_path, glossary_path])
    return generated


def _write_merged_book(book: LibraryBook, output_dir: Path, lookup: dict[str, object]) -> Path:
    merged_path = output_dir / "book.html"
    merged_path.write_text(generate_merged_html(book, lookup), encoding="utf-8")
    return merged_path


def _iter_selected_roots(args: argparse.Namespace) -> list[tuple[Path, str | None]]:
    roots: list[tuple[Path, str | None]] = []

    if args.dir:
        roots.append((Path(args.dir), args.name))
    if args.dirs:
        for item in args.dirs.split(","):
            item = item.strip()
            if item:
                roots.append((Path(item), None))
    if args.all:
        for child in sorted(REPO_ROOT.iterdir(), key=lambda p: p.name.lower()):
            if child.name in IGNORED_DIRECTORIES or child.name.startswith("."):
                continue
            if child.is_dir() and any(child.glob("*.html")):
                roots.append((child, None))

    if not roots:
        raise ValueError("Please provide --dir, --dirs, or --all")
    return roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Process classical Chinese library HTML into print-ready outputs")
    selection = parser.add_mutually_exclusive_group(required=False)
    selection.add_argument("--dir", type=str, help="Process one directory")
    selection.add_argument("--dirs", type=str, help="Comma-separated list of directories")
    selection.add_argument("--all", action="store_true", help="Process all library directories in the repo")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_DIR, help="Log directory")
    parser.add_argument("--unihan", type=Path, default=REPO_ROOT, help="Path to Unihan files or repo root")
    parser.add_argument("--recursive", action="store_true", help="Process nested directories recursively")
    parser.add_argument("--merge", action="store_true", help="Also generate a merged book page")
    parser.add_argument("--name", type=str, help="Custom name for the selected directory")

    args = parser.parse_args()

    try:
        selected_roots = _iter_selected_roots(args)
    except Exception as exc:
        print(f"[error] Invalid arguments: {exc}", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    args.logs.mkdir(parents=True, exist_ok=True)

    unihan_base = args.unihan if args.unihan.exists() else REPO_ROOT
    if unihan_base.is_file():
        unihan_base = unihan_base.parent

    readings_file = locate_unihan_file([unihan_base / "Unihan_Readings.txt"], "readings")
    dict_like_file = locate_unihan_file([unihan_base / "Unihan_DictionaryLikeData.txt"], "dictionary_like")
    if readings_file is None:
        print("[error] Unihan_Readings.txt not found in configured locations.", file=sys.stderr)
        return 3

    try:
        lookup = build_unihan_lookup(readings_file, dict_like_file)
    except Exception as exc:
        print(f"[error] Failed to parse Unihan files: {exc}", file=sys.stderr)
        return 4

    started = time.time()
    all_generated: list[str] = []
    all_books: list[dict[str, object]] = []
    errors: list[str] = []
    total_entries = 0
    unique_chars: set[str] = set()

    for root, custom_name in selected_roots:
        root = root.resolve()
        if not root.exists():
            errors.append(f"Missing input path: {root}")
            continue
        if root.is_file():
            root = root.parent

        book_dirs = _discover_book_dirs(root, args.recursive)
        if not book_dirs:
            errors.append(f"No HTML files found under: {root}")
            continue

        root_name = custom_name or root.name
        for book_dir in book_dirs:
            try:
                sources = _load_sources(book_dir)
                if not sources:
                    continue
                book = _prepare_book(book_dir, sources, custom_name if book_dir == root else None)
                rel_dir = book_dir.relative_to(root) if book_dir != root else Path()
                output_dir = args.output / cached_slug(root_name)
                if rel_dir != Path():
                    output_dir = output_dir / rel_dir

                glossary = build_library_glossary(book.entries, lookup, book.slug)
                unique_chars.update(entry.char for entry in glossary.entries)
                generated_paths = _write_book_assets(book, output_dir, lookup, glossary)
                if args.merge:
                    generated_paths.append(_write_merged_book(book, output_dir, lookup))

                total_entries += len(book.entries)
                all_generated.extend(str(path) for path in generated_paths)
                all_books.append(
                    {
                        "source_directory": str(book_dir),
                        "output_directory": str(output_dir),
                        "title": book.title,
                        "slug": book.slug,
                        "sources": [str(source.source_path) for source in sources],
                        "entries": len(book.entries),
                        "characters": glossary.total_occurrences,
                        "glossary_entries": len(glossary.entries),
                    }
                )
                print(f"[ok] {book_dir} -> {output_dir} ({len(book.entries)} entries)")
            except Exception as exc:
                errors.append(f"{book_dir}: {exc}")
                print(f"[error] {book_dir}: {exc}", file=sys.stderr)

    duration = time.time() - started
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_roots": [str(path) for path, _ in selected_roots],
        "books": all_books,
        "generated_files": all_generated,
        "errors": errors,
        "statistics": {
            "books_processed": len(all_books),
            "entries_processed": total_entries,
            "unique_characters": len(unique_chars),
            "processing_seconds": round(duration, 3),
        },
    }

    log_file = args.logs / "processing_log.json"
    log_file.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] Log: {log_file}")

    return 0 if not errors else 5


if __name__ == "__main__":
    raise SystemExit(main())
