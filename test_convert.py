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

        # Check files exist
        atomic = Path(out_dir) / "Books___Atomic Habits.md"
        art = Path(out_dir) / "Books___The Art of War.md"
        assert atomic.exists(), "Atomic Habits file missing"
        assert art.exists(), "The Art of War file missing"

        # Empty Book (no notes) should NOT have a file
        empty = Path(out_dir) / "Books___Empty Book.md"
        assert not empty.exists(), "Empty Book should not have a file"

        print("PASS: basic output files created correctly")
    finally:
        shutil.rmtree(tmpdir)


def test_content_format():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits.md").read_text()

        assert "- Book:: [[Books/Atomic Habits]]" in content, "Book property wrong"
        assert "- Author:: James Clear" in content, "Author wrong"
        assert "- Status:: finished" in content, "Status wrong"
        assert "- Rating:: 5" in content, "Rating wrong"
        assert "- Date Started:: 2025-01-10" in content, "Date Started wrong"
        assert "- Date Finished:: 2025-02-03" in content, "Date Finished wrong"
        assert "#booknote-quote" in content, "quote tag missing"
        assert "#booknote-reflect" in content, "reflect tag missing"
        assert "#booknote-distill" in content, "distill tag missing"

        print("PASS: content format correct")
    finally:
        shutil.rmtree(tmpdir)


def test_multiline_indent():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits.md").read_text()
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

        content = (Path(out_dir) / "Books___The Art of War.md").read_text()
        assert "#booknote-apply" in content, "apply tag missing"
        assert "- Rating:: Unrated" in content, "Unrated rating missing"
        assert "- Date Finished:: " in content, "Empty finish date missing"

        print("PASS: apply tag and unrated book correct")
    finally:
        shutil.rmtree(tmpdir)


def test_idempotent_overwrite():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")

        main(zip_path=zip_path, output_dir=out_dir)
        content1 = (Path(out_dir) / "Books___Atomic Habits.md").read_text()

        main(zip_path=zip_path, output_dir=out_dir)
        content2 = (Path(out_dir) / "Books___Atomic Habits.md").read_text()

        assert content1 == content2, "Second run produced different content"

        print("PASS: idempotent overwrite works")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_basic_output()
    test_content_format()
    test_multiline_indent()
    test_apply_tag()
    test_idempotent_overwrite()
    print("\nAll tests passed!")
