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
# Create a config.py file with your local paths (see config.example.py).
try:
    from config import BOOKNOTE_ZIP_PATH, LOGSEQ_PAGES_DIR
except ImportError:
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
    """Build the Logseq markdown content for a book's notes subpage."""
    title = book["title"].strip()
    author = book.get("author", "").strip()
    status = book.get("status", "").strip()
    rating_raw = book.get("rating", "").strip()
    rating = f"{rating_raw}/5" if rating_raw else "Unrated"
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
            f"- **Description** {description}",
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
        is_quote = tag.lower() == "quote"

        # Inline the tag and date on a single trailing line, e.g.
        # "#booknote-quote 2025-01-15".
        footer = " ".join(p for p in (logseq_tag, note_date) if p)

        content_lines = content.split("\n")

        if is_quote:
            # Prefix every line with "> " so it renders as a markdown blockquote.
            lines.append(f"  - > {content_lines[0]}")
            for extra_line in content_lines[1:]:
                lines.append(f"    > {extra_line}")
            # Blank line separates the blockquote from the footer, otherwise the
            # footer would get pulled into the blockquote when rendered.
            if footer:
                lines.append("")
                lines.append(f"    {footer}")
        else:
            # Non-quote notes: inline the footer on the first line of content
            # so it sits on the parent block (not a child continuation line).
            first_line = f"{content_lines[0]} {footer}".rstrip() if footer else content_lines[0]
            lines.append(f"  - {first_line}")
            for extra_line in content_lines[1:]:
                lines.append(f"    {extra_line}")

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
        book_pages_created = 0
        total_notes = 0

        for book in books:
            book_id = book.get("id", "").strip()
            book_notes = notes_by_book.get(book_id, [])
            if not book_notes:
                continue

            title = book["title"].strip()
            safe_title = sanitize_filename(title)

            notes_filename = f"Books___{safe_title}___notes.md"
            notes_filepath = output_path / notes_filename
            book_filename = f"Books___{safe_title}.md"
            book_filepath = output_path / book_filename

            if notes_filepath.exists():
                overwritten += 1
            else:
                created += 1

            md = build_markdown(book, book_notes)
            notes_filepath.write_text(md, encoding="utf-8")
            total_notes += len(book_notes)

            # Create the main book page as a blank reflections canvas, but
            # only if it doesn't already exist — we never want to overwrite
            # reflections the user has already written there.
            if not book_filepath.exists():
                book_filepath.write_text("", encoding="utf-8")
                book_pages_created += 1

        books_processed = created + overwritten
        print(f"Books processed: {books_processed}")
        print(f"Notes pages created: {created}")
        print(f"Notes pages overwritten: {overwritten}")
        print(f"Blank book pages created: {book_pages_created}")
        print(f"Total notes written: {total_notes}")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
