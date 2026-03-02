#!/usr/bin/env python3
"""Convert BookNote iOS app CSV export into Logseq markdown files."""

import csv
import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
BOOKNOTE_ZIP_PATH = "/path/to/BookNote_Books_and_Notes_Export.zip"
LOGSEQ_PAGES_DIR = "/path/to/logseq/graph/pages"
# ---------------------


def sanitize_filename(title):
    """Replace filesystem-illegal characters with hyphens and strip whitespace."""
    illegal = '/\\:*?"<>|'
    result = title
    for ch in illegal:
        result = result.replace(ch, "-")
    return result.strip()


def format_date(date_str):
    """Try to parse a date string into YYYY-MM-DD format. Return empty string on failure."""
    if not date_str or not date_str.strip():
        return ""
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def read_csv_from_zip(zip_ref, filename):
    """Read and parse a CSV file from inside a zip archive."""
    try:
        raw = zip_ref.read(filename)
    except KeyError:
        return None
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def build_markdown(book, notes):
    """Build the Logseq markdown content for a single book and its notes."""
    title = book["title"].strip()
    author = book.get("author", "").strip()
    status = book.get("status", "").strip()
    rating = book.get("rating", "").strip() or "Unrated"
    date_started = format_date(book.get("date", ""))
    date_finished = format_date(book.get("finishDate", ""))

    description = book.get("description", "").strip()

    lines = [
        f"- Book:: [[Books/{title}]]",
        f"- Author:: {author}",
        f"- Status:: {status}",
        f"- Rating:: {rating}",
        f"- Date Started:: {date_started}",
        f"- Date Finished:: {date_finished}",
    ]

    if description:
        lines += [
            "",
            "---",
            "",
            f"- {description}",
        ]

    lines += [
        "",
        "---",
        "",
        "- ## Notes",
    ]

    sorted_notes = sorted(notes, key=lambda n: n.get("date", ""))

    for note in sorted_notes:
        tag = note.get("tag", "").strip()
        logseq_tag = f"#booknote-{tag}" if tag else ""
        content = note.get("plain_text_content", "").strip()
        note_date = format_date(note.get("date", ""))

        content_lines = content.split("\n")
        first_line = content_lines[0]
        lines.append(f"  - {logseq_tag} {first_line}" if logseq_tag else f"  - {first_line}")
        for extra_line in content_lines[1:]:
            lines.append(f"    {extra_line}")
        lines.append(f"    - Date:: {note_date}")

    return "\n".join(lines) + "\n"


def main(zip_path=None, output_dir=None):
    """Run the conversion. Arguments override the config variables."""
    zip_path = zip_path or BOOKNOTE_ZIP_PATH
    output_dir = output_dir or LOGSEQ_PAGES_DIR

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Find the CSV files — they may be at the root or inside a subfolder
            names = zf.namelist()
            books_file = next((n for n in names if n.lower().endswith("books_export.csv") or n.endswith("books.csv")), None)
            notes_file = next((n for n in names if n.lower().endswith("notes_export.csv") or n.endswith("notes.csv")), None)

            if not books_file:
                print("Error: books.csv not found in the zip file.")
                return
            if not notes_file:
                print("Error: notes.csv not found in the zip file.")
                return

            books = read_csv_from_zip(zf, books_file)
            notes = read_csv_from_zip(zf, notes_file)

        if books is None or notes is None:
            print("Error: Could not read CSV files from the zip.")
            return

        # Group notes by book_id
        notes_by_book = {}
        for note in notes:
            bid = note.get("book_id", "").strip()
            if bid:
                notes_by_book.setdefault(bid, []).append(note)

        created = 0
        overwritten = 0
        total_notes = 0

        for book in books:
            book_id = book.get("id", "").strip()
            book_notes = notes_by_book.get(book_id, [])
            if not book_notes:
                continue

            title = book["title"].strip()
            safe_title = sanitize_filename(title)
            filename = f"Books___{safe_title}.md"
            filepath = output_path / filename

            if filepath.exists():
                overwritten += 1
            else:
                created += 1

            md = build_markdown(book, book_notes)
            filepath.write_text(md, encoding="utf-8")
            total_notes += len(book_notes)

        books_processed = created + overwritten
        print(f"Books processed: {books_processed}")
        print(f"Files created: {created}")
        print(f"Files overwritten: {overwritten}")
        print(f"Total notes written: {total_notes}")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
