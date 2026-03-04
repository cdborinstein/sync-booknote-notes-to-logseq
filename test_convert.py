#!/usr/bin/env python3
"""Tests for the BookNote-to-Logseq converter using synthetic data."""

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from convert import main

BOOKS_CSV = """\
id,title,author,pageCount,status,date,finishDate,rating,cover,trackPages,useJustPercentage,isbn,isbn13,description,note_ids
1,Atomic Habits,James Clear,320,finished,2025-01-10,2025-02-03,5,,,,,,,"101,102,103"
2,The Art of War,Sun Tzu,80,reading,2025-03-01,,,,,,,,,"201"
3,Empty Book,No Author,100,finished,2025-01-01,2025-01-05,3,,,,,,,
"""

NOTES_CSV = """\
id,book_id,book_title,book_author,content_string,plain_text_content,date,tag,status
101,1,Atomic Habits,James Clear,x,"You do not rise to the level of your goals, you fall to the level of your systems.",2025-01-15,quote,active
102,1,Atomic Habits,James Clear,x,The habit loop is really just cue craving response reward.,2025-01-22,reflect,active
103,1,Atomic Habits,James Clear,x,"Identity-based habits:
- Start with who you want to become
- Let your identity drive your habits",2025-02-01,distill,active
201,2,The Art of War,Sun Tzu,x,All warfare is based on deception.,2025-03-05,apply,active
"""


def make_test_zip(tmpdir):
    """Create a test zip file with synthetic CSV data."""
    zip_path = os.path.join(tmpdir, "export.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("books.csv", BOOKS_CSV)
        zf.writestr("notes.csv", NOTES_CSV)
    return zip_path


def test_basic_output():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")

        main(zip_path=zip_path, output_dir=out_dir)

        # Check both main page and notes sub-page exist
        atomic_book = Path(out_dir) / "Books___Atomic Habits.md"
        atomic_notes = Path(out_dir) / "Books___Atomic Habits___Notes.md"
        art_book = Path(out_dir) / "Books___The Art of War.md"
        art_notes = Path(out_dir) / "Books___The Art of War___Notes.md"
        assert atomic_book.exists(), "Atomic Habits book page missing"
        assert atomic_notes.exists(), "Atomic Habits notes page missing"
        assert art_book.exists(), "The Art of War book page missing"
        assert art_notes.exists(), "The Art of War notes page missing"

        # Empty Book (no notes) should NOT have any files
        assert not (Path(out_dir) / "Books___Empty Book.md").exists(), "Empty Book should not have a file"

        print("PASS: basic output files created correctly")
    finally:
        shutil.rmtree(tmpdir)


def test_book_page_format():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits.md").read_text()

        assert "- Author:: James Clear" in content, "Author wrong"
        assert "- Status:: finished" in content, "Status wrong"
        assert "- Rating:: 5" in content, "Rating wrong"
        assert "- Date Started:: 2025-01-10" in content, "Date Started wrong"
        assert "- Date Finished:: 2025-02-03" in content, "Date Finished wrong"
        assert "- Notes:: [[Books/Atomic Habits/Notes]]" in content, "Notes link missing"

        # Notes should NOT be on the main book page
        assert "#booknote-quote" not in content, "notes should not appear on book page"

        print("PASS: book page format correct")
    finally:
        shutil.rmtree(tmpdir)


def test_notes_page_format():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___Notes.md").read_text()

        assert "#booknote-quote" in content, "quote tag missing"
        assert "#booknote-reflect" in content, "reflect tag missing"
        assert "#booknote-distill" in content, "distill tag missing"
        assert "> You do not rise" in content, "quote blockquote prefix missing"
        assert content.index("> You do not rise") < content.index("#booknote-quote"), "tag should appear after quote content"

        # Metadata should NOT be on the notes page
        assert "- Author::" not in content, "metadata should not appear on notes page"

        print("PASS: notes page format correct")
    finally:
        shutil.rmtree(tmpdir)


def test_multiline_indent():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___Notes.md").read_text()
        lines = content.split("\n")

        # Find the distill note — it has multi-line content
        distill_idx = next(i for i, l in enumerate(lines) if "#booknote-distill" in l)
        # The next line should be the continuation, indented with 4 spaces
        next_line = lines[distill_idx + 1]
        assert next_line.startswith("    "), f"Multi-line continuation not indented correctly: {next_line!r}"

        print("PASS: multi-line content indented correctly")
    finally:
        shutil.rmtree(tmpdir)


def test_apply_tag():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        notes_content = (Path(out_dir) / "Books___The Art of War___Notes.md").read_text()
        book_content = (Path(out_dir) / "Books___The Art of War.md").read_text()
        assert "#booknote-apply" in notes_content, "apply tag missing"
        assert "- Rating:: Unrated" in book_content, "Unrated rating missing"
        assert "- Date Finished:: " in book_content, "Empty finish date missing"

        print("PASS: apply tag and unrated book correct")
    finally:
        shutil.rmtree(tmpdir)


def test_book_page_not_overwritten():
    """Main book page should never be overwritten once created."""
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")

        main(zip_path=zip_path, output_dir=out_dir)

        # Simulate user edits on the main page
        book_filepath = Path(out_dir) / "Books___Atomic Habits.md"
        book_filepath.write_text("my own thoughts", encoding="utf-8")

        main(zip_path=zip_path, output_dir=out_dir)

        assert book_filepath.read_text() == "my own thoughts", "Book page was overwritten"

        print("PASS: book page not overwritten on second run")
    finally:
        shutil.rmtree(tmpdir)


def test_notes_page_always_overwritten():
    """Notes sub-page should always be refreshed."""
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")

        main(zip_path=zip_path, output_dir=out_dir)
        notes_content1 = (Path(out_dir) / "Books___Atomic Habits___Notes.md").read_text()

        main(zip_path=zip_path, output_dir=out_dir)
        notes_content2 = (Path(out_dir) / "Books___Atomic Habits___Notes.md").read_text()

        assert notes_content1 == notes_content2, "Notes page content changed unexpectedly"

        print("PASS: notes page idempotent overwrite works")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_basic_output()
    test_book_page_format()
    test_notes_page_format()
    test_multiline_indent()
    test_apply_tag()
    test_book_page_not_overwritten()
    test_notes_page_always_overwritten()
    print("\nAll tests passed!")
