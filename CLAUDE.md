# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a blog/journal analysis tool for the Blog Authorship Corpus dataset. The corpus contains 19,320 blogs from blogger.com (August 2004), with each blog representing a single user's posts. This project filters for large blogs (>100kb) and provides tools to analyze writing patterns, continuity metrics, and interactively read journal entries.

## Dataset Context

- **Source**: Blog Authorship Corpus from HuggingFace
- **Filtering**:
  - Only blogs >100kb are kept in `/data` directory
  - CSV output excludes journals with <30 total entries
- **Format**: XML files named as `author_id.gender.age.job.horoscope.xml`
  - Example: `4334776.male.24.Engineering.Aquarius.xml`
- **Content**: Each file contains `<date>` and `<post>` tags with blog entries
  - Dates formatted as: `DD,Month,YYYY` (e.g., `24,August,2004`)
  - Posts may have multiple entries per date
  - Links denoted by `urllink` label

## Key Commands

### Automated Setup (Recommended)
```bash
# Run complete setup: download, extract, filter, analyze, and launch reader
./setup.sh

# Available options:
./setup.sh --help          # Show all options
./setup.sh --force         # Force re-analysis even if CSV exists
./setup.sh --keep-source   # Keep blogs.zip and blogs/ after filtering
```

The setup script is idempotent and handles:
- Downloading dataset from HuggingFace (~300MB)
- Extracting blogs.zip
- Filtering to files >100kb (configurable via `MIN_FILE_SIZE` variable)
- Dependency checking and optional fzf installation
- Running analysis
- Launching the reader

### Manual Analysis Pipeline
```bash
# 1. Analyze all journals and generate CSV with metrics
python analyze_blogs.py

# 2. Interactively read journals with fzf picker and curses TUI
python reader.py
```

### Dependencies
- **Standard library only** for `analyze_blogs.py`
- `reader.py` requires:
  - `fzf` (command-line fuzzy finder)
  - `curses` (terminal UI, standard library on Unix)
- `setup.sh` requires:
  - `curl` (for downloading dataset)
  - `unzip` (for extracting archive)
  - `brew` (optional, for installing fzf)

## Code Architecture

### analyze_blogs.py (Lines 1-295)
Parses all XML files in `/data` and generates `journal_analysis.csv` with comprehensive metrics.

**Key Functions**:
- `parse_filename()`: Extracts metadata from filename pattern
- `parse_date()`: Converts `DD,Month,YYYY` to datetime.date
- `analyze_journal()`: Core analysis engine that calculates:
  - **Continuity metrics**: total_entries, num_streaks, isolated_entries, longest_streak, avg_streak_length, continuity_percentage, date_gaps
  - **Word metrics**: total_words, avg_words_per_entry, largest_entry_words
  - Groups multiple posts by date and combines them

**Filtering**: Journals with fewer than 30 total entries are excluded from CSV output (Lines 231-233)

**Output**: `journal_analysis.csv` sorted by:
1. total_entries (descending)
2. longest_streak (descending)
3. avg_words_per_entry (descending)
4. total_words (descending)

**Streak Calculation Logic** (Lines 143-186):
- Only sequences of 2+ consecutive days count as "streaks"
- `num_streaks`: count of multi-day sequences
- `isolated_entries`: entries not part of any streak
- `continuity_percentage`: percentage of entries within streaks
- Gaps occur when dates are not consecutive (expected_date != curr_date)

### reader.py (Lines 1-541)
Interactive journal reader with fzf selection and curses navigation.

**Key Functions**:
- `select_journal_with_fzf()`: Presents sorted list with metrics (entries, longest streak, num streaks, avg words), prioritizes journals with notes
- `parse_journal()`: Parses XML and returns chronologically sorted entries with metrics (tokens, chars, words)
- `display_journal()`: Curses TUI with navigation and scrolling
- `save_note_to_csv()` / `get_current_note()`: Persist notes field in CSV
- `rough_token_estimate()`: Estimates token count using average of char/4 and word*1.33 methods

**Text Cleaning System**:
The reader includes a modular text cleaning pipeline to improve readability:
- `remove_control_characters()`: Removes XML 1.0 invalid control chars (0x00-0x08, 0x0B-0x0C, 0x0E-0x1F)
- `fix_ampersands()`: Escapes raw `&` to `&amp;` while preserving valid XML entities
- `clean_urllink()`: Removes `urlLink` markers while preserving URLs and anchor text
  - Handles empty urlLinks, plain URLs, and descriptive anchor text
  - Cleans up spacing and punctuation artifacts
- `remove_double_spaces()`: Collapses multiple consecutive spaces to single space
- `normalize_newlines()`: Reduces multiple blank lines to maximum one blank line
  - Handles blank lines containing only whitespace (spaces/tabs)
- `apply_cleaners()`: Applies all cleaning functions in sequence

**Cleaned Text Features**:
- Cleaned mode is the default view (toggle with 'c' to see original)
- Cleaned text cached per entry for performance
- Metrics (tokens, chars, words) recalculated for cleaned text
- Yank ('y') copies cleaned text when in cleaned mode, original when not
- Export ('e') respects the current view mode

**Navigation Controls**:
- Arrow keys or hjkl (vim-style): navigate entries and scroll
- `n`: Add/edit note for current journal
- `c`: Toggle between cleaned and original text view
- `y`: Yank (copy) current entry to clipboard via pbcopy
- `e`: Export entire journal to `exports/` directory
- `q`: Return to fzf picker

**Display Logic**:
- Multiple posts on same date are combined with `\n\n` separator
- Posts from same date are reversed (last post appears first)
- Text wrapping respects word boundaries at terminal width
- Scrolling when content exceeds screen height
- Footer displays metrics: token estimate, character count, and word count for current entry
- Metrics update dynamically when toggling between cleaned/original text

## File Structure

```
.
├── data/                       # XML journal files (gitignored)
├── exports/                    # Exported journals (gitignored)
├── img/                        # Screenshots for documentation
├── tests/                      # Test suite
│   ├── test_urllink_cleaning.py    # Text cleaning tests
│   └── test_export.py              # Export functionality tests
├── setup.sh                    # Automated setup script (download, filter, analyze, launch)
├── analyze_blogs.py            # Journal analysis script
├── reader.py                   # Interactive journal reader
├── journal_analysis.csv        # Generated metrics (gitignored)
├── README.md                   # Dataset documentation
└── CLAUDE.md                   # Project documentation (this file)
```

## Important Implementation Details

### Date Parsing Edge Cases
- Invalid dates return `None` and are silently skipped
- Files with date/post mismatches issue warnings but continue processing
- Encoding errors handled with `errors='ignore'` in file reading

### CSV Notes Field
- Added during analysis as empty string
- Updated via `reader.py` when user presses 'n'
- Used by fzf picker to prioritize annotated journals
- Truncated to 30 chars in fzf display

### Curses TUI Pattern
- `curses.wrapper()` handles setup/teardown (reader.py:532-534)
- Temporarily exits curses for note input (reader.py:424)
- Must re-initialize after `curses.endwin()` (reader.py:445-447)
- Handles terminal resize via `getmaxyx()` on each refresh

### Token Estimation
- `rough_token_estimate()` uses hybrid approach: `((chars/4) + (words*1.33)) / 2`
- Provides rough approximation without external dependencies
- Displayed in footer along with exact character and word counts
- Recalculated when toggling between cleaned/original text

### Clipboard Integration (macOS)
- 'y' key yanks current entry to clipboard using `pbcopy`
- Works with both cleaned and original text modes
- Silently fails if pbcopy unavailable

### Export Feature
- 'e' key exports the entire journal to `exports/` directory
- Combines multiple posts on the same date into single entries (like the reader)
- Entries are sorted chronologically
- Respects current view mode:
  - Cleaned mode: exports with `_clean` suffix, all posts cleaned
  - Original mode: posts combined but not cleaned
- Creates `exports/` directory automatically if needed
- Shows flash confirmation message for 2 seconds

## Testing Approach

### Testing Analysis Logic
When modifying `analyze_blogs.py`:
1. Test with a known journal file
2. Verify metrics match manual calculation
3. Check edge cases: single entry, no consecutive dates, multiple posts per day

### Testing Reader
When modifying `reader.py`:
1. Test with various terminal sizes
2. Verify scrolling behavior with long entries
3. Check note persistence in CSV
4. Test cleaned text mode toggle functionality
5. Test export in both modes (verify `_clean` suffix and file content)

### Running Tests
All tests are in the `tests/` directory. Run from project root:
```bash
python tests/test_urllink_cleaning.py  # Text cleaning tests
python tests/test_export.py            # Export functionality tests
```

**test_urllink_cleaning.py**:
- Tests `clean_urllink()` against real corpus patterns
- Tests `apply_cleaners()` integration
- Covers edge cases: empty urlLinks, URLs, anchor text, multiple urlLinks

**test_export.py**:
- Tests post combination (multiple posts per date merged)
- Tests export in original and cleaned modes
- Verifies chronological ordering
- Confirms XML structure preservation
