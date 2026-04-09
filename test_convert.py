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

        # Both the blank main book page and the notes subpage should exist
        atomic_book = Path(out_dir) / "Books___Atomic Habits.md"
        atomic_notes = Path(out_dir) / "Books___Atomic Habits___notes.md"
        art_book = Path(out_dir) / "Books___The Art of War.md"
        art_notes = Path(out_dir) / "Books___The Art of War___notes.md"
        assert atomic_book.exists(), "Atomic Habits book page missing"
        assert atomic_notes.exists(), "Atomic Habits notes subpage missing"
        assert art_book.exists(), "The Art of War book page missing"
        assert art_notes.exists(), "The Art of War notes subpage missing"

        # Main book pages should be blank (reflections placeholder)
        assert atomic_book.read_text() == "", "Atomic Habits book page should be blank"
        assert art_book.read_text() == "", "The Art of War book page should be blank"

        # Empty Book (no notes) should NOT have either file
        empty_book = Path(out_dir) / "Books___Empty Book.md"
        empty_notes = Path(out_dir) / "Books___Empty Book___notes.md"
        assert not empty_book.exists(), "Empty Book page should not be created"
        assert not empty_notes.exists(), "Empty Book notes subpage should not be created"

        print("PASS: basic output files created correctly")
    finally:
        shutil.rmtree(tmpdir)


def test_content_format():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()

        assert "- Book:: [[Books/Atomic Habits]]" in content, "Book property wrong"
        assert "- Author:: James Clear" in content, "Author wrong"
        assert "- Status:: finished" in content, "Status wrong"
        assert "- Rating:: 5/5" in content, "Rating wrong"
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

        content = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()
        lines = content.split("\n")

        # Find the distill note by its first line of content
        distill_idx = next(i for i, l in enumerate(lines) if "Identity-based habits:" in l)
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

        content = (Path(out_dir) / "Books___The Art of War___notes.md").read_text()
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
        content1 = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()

        main(zip_path=zip_path, output_dir=out_dir)
        content2 = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()

        assert content1 == content2, "Second run produced different notes content"

        print("PASS: idempotent overwrite works")
    finally:
        shutil.rmtree(tmpdir)


def test_quote_formatting():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()
        lines = content.split("\n")

        # The quote note should start with a "> " blockquote prefix
        quote_idx = next(
            i for i, l in enumerate(lines) if "You do not rise to the level of your goals" in l
        )
        assert "> You do not rise" in lines[quote_idx], (
            f"Quote missing `>` prefix: {lines[quote_idx]!r}"
        )

        # There should be a blank line between the quote and its tag
        tag_idx = next(
            i for i in range(quote_idx, len(lines)) if "#booknote-quote" in lines[i]
        )
        assert lines[tag_idx - 1] == "", (
            f"Blank line missing before quote tag: {lines[tag_idx - 1]!r}"
        )

        print("PASS: quote formatting correct")
    finally:
        shutil.rmtree(tmpdir)


def test_tag_at_end_of_note():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()
        lines = content.split("\n")

        # Non-quote notes: the tag should be inlined on the same line as the
        # content, and appear after the note text.
        reflect_line = next(l for l in lines if "habit loop" in l)
        assert "#booknote-reflect" in reflect_line, (
            f"Tag should be inlined on the content line: {reflect_line!r}"
        )
        assert reflect_line.index("habit loop") < reflect_line.index("#booknote-reflect"), (
            "Tag should come after note content on the same line"
        )

        # Quote notes: the tag should still be on its own line (not inlined)
        quote_content_line = next(l for l in lines if "You do not rise" in l)
        assert "#booknote-quote" not in quote_content_line, (
            "Quote tag should not be inlined with quote content"
        )

        print("PASS: tag appears at end of note")
    finally:
        shutil.rmtree(tmpdir)


def test_inline_date_with_tag():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")
        main(zip_path=zip_path, output_dir=out_dir)

        content = (Path(out_dir) / "Books___Atomic Habits___notes.md").read_text()

        # Date should be inlined after the tag on the same line
        assert "#booknote-quote 2025-01-15" in content, "Date not inlined with quote tag"
        assert "#booknote-reflect 2025-01-22" in content, "Date not inlined with reflect tag"
        assert "#booknote-distill 2025-02-01" in content, "Date not inlined with distill tag"

        # The old per-note "- Date::" sub-bullet should be gone
        assert "- Date:: 2025-01-15" not in content, "Old per-note Date:: sub-bullet still present"
        assert "- Date:: 2025-01-22" not in content, "Old per-note Date:: sub-bullet still present"
        assert "- Date:: 2025-02-01" not in content, "Old per-note Date:: sub-bullet still present"

        print("PASS: date inlined with tag")
    finally:
        shutil.rmtree(tmpdir)


def test_main_page_preserves_reflections():
    tmpdir = tempfile.mkdtemp()
    try:
        zip_path = make_test_zip(tmpdir)
        out_dir = os.path.join(tmpdir, "pages")

        main(zip_path=zip_path, output_dir=out_dir)

        # Simulate the user adding reflections to the main book page
        book_page = Path(out_dir) / "Books___Atomic Habits.md"
        reflections = "- My takeaway: start small and be consistent.\n"
        book_page.write_text(reflections, encoding="utf-8")

        # Re-running the converter must not overwrite the reflections
        main(zip_path=zip_path, output_dir=out_dir)
        assert book_page.read_text() == reflections, "Reflections were overwritten"

        print("PASS: main book page preserves reflections")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_basic_output()
    test_content_format()
    test_multiline_indent()
    test_apply_tag()
    test_idempotent_overwrite()
    test_quote_formatting()
    test_tag_at_end_of_note()
    test_inline_date_with_tag()
    test_main_page_preserves_reflections()
    print("\nAll tests passed!")
