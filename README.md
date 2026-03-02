# BookNote to Logseq Converter

A Python script that converts [BookNote](https://apps.apple.com/app/booknote/id1529758634) iOS app exports into [Logseq](https://logseq.com/)-compatible markdown files.

## What It Does

- Reads a BookNote CSV export (zip file containing books and notes)
- Generates one Logseq markdown page per book under the `Books/` namespace
- Includes book metadata (author, status, rating, dates), description, and all notes
- Tags each note with its BookNote category: `#booknote-quote`, `#booknote-reflect`, `#booknote-distill`, `#booknote-apply`
- Safe to re-run — fully overwrites existing files since BookNote exports are cumulative

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

Each book gets a file named `Books___<Title>.md` containing:

```markdown
- Book:: [[Books/Atomic Habits]]
- Author:: James Clear
- Status:: finished
- Rating:: 5
- Date Started:: 2025-01-10
- Date Finished:: 2025-02-03

---

- **Description** A groundbreaking book about building good habits...

---

- ## Notes
  - #booknote-quote You do not rise to the level of your goals...
    - Date:: 2025-01-15
  - #booknote-reflect The habit loop is cue, craving, response, reward.
    - Date:: 2025-01-22
```

## Requirements

Python 3.6+ with no third-party dependencies (stdlib only).
