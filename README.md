# BookNote to Logseq Converter

A Python script that converts [BookNote](https://apps.apple.com/app/booknote/id1529758634) iOS app exports into [Logseq](https://logseq.com/)-compatible markdown files.

## What It Does

- Reads a BookNote CSV export (zip file containing books and notes)
- For each book, generates a Logseq `Books/<Title>/notes` subpage with all metadata and notes
- Also creates a blank `Books/<Title>` page the first time it runs — a reflections canvas you can fill in yourself. Re-runs will never overwrite this page.
- Includes book metadata (author, status, rating out of 5, dates) and description on the notes subpage
- Tags each note with its BookNote category: `#booknote-quote`, `#booknote-reflect`, `#booknote-distill`, `#booknote-apply`
- Renders `quote`-tagged notes as markdown blockquotes so they stand out when imported into Logseq
- Safe to re-run — the notes subpages are fully overwritten (BookNote exports are cumulative), while your reflection pages are preserved

## Setup

1. Clone this repo
2. Copy `config.example.py` to `config.py` and fill in your paths:

```python
BOOKNOTE_ZIP_PATH = "/path/to/BookNote_Books_and_Notes_Export.zip"
LOGSEQ_PAGES_DIR = "/path/to/logseq/graph/pages"
```

For Logseq on iCloud, the pages directory is typically:
```
~/Library/Mobile Documents/iCloud~com~logseq~logseq/Documents/<YourGraph>/pages/
```

## Usage

```bash
python3 convert.py
```

The script will print a summary of how many books and notes were processed.

## Output Format

Each book produces two files:

- `Books___<Title>.md` — a blank page for your own reflections (created only if missing; never overwritten)
- `Books___<Title>___notes.md` — the metadata + notes subpage, which looks like this:

```markdown
- Book:: [[Books/Atomic Habits]]
- Author:: James Clear
- Status:: finished
- Rating:: 5/5
- Date Started:: 2025-01-10
- Date Finished:: 2025-02-03

---

- **Description** A groundbreaking book about building good habits...

---

- ## Notes
  - > You do not rise to the level of your goals, you fall to the level of your systems.

    #booknote-quote 2025-01-15
  - The habit loop is cue, craving, response, reward. #booknote-reflect 2025-01-22
```

Notes tagged `quote` are prefixed with `>` so they render as markdown blockquotes, with a blank line separating them from the tag. All other notes inline the tag (and date) at the end of the note content on the same line.

## Requirements

Python 3.6+ with no third-party dependencies (stdlib only).
