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

### Analysis Pipeline
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

### reader.py (Lines 1-378)
Interactive journal reader with fzf selection and curses navigation.

**Key Functions**:
- `select_journal_with_fzf()`: Presents sorted list with metrics, prioritizes journals with notes
- `parse_journal()`: Parses XML and returns chronologically sorted entries
- `display_journal()`: Curses TUI with navigation and scrolling
- `save_note_to_csv()` / `get_current_note()`: Persist notes field in CSV

**Navigation Controls**:
- Arrow keys or hjkl (vim-style): navigate entries and scroll
- `n`: Add/edit note for current journal
- `q`: Return to fzf picker

**Display Logic**:
- Multiple posts on same date are combined with `\n\n` separator
- Posts from same date are reversed (last post appears first)
- Text wrapping respects word boundaries at terminal width
- Scrolling when content exceeds screen height

## File Structure

```
.
├── data/                     # XML journal files (gitignored)
├── analyze_blogs.py          # Journal analysis script
├── reader.py                 # Interactive journal reader
├── journal_analysis.csv      # Generated metrics (gitignored)
└── README.md                 # Dataset documentation
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
- `curses.wrapper()` handles setup/teardown (reader.py:369-371)
- Temporarily exits curses for note input (reader.py:300)
- Must re-initialize after `curses.endwin()` (reader.py:321-323)
- Handles terminal resize via `getmaxyx()` on each refresh

## Testing Approach

When modifying analysis logic:
1. Test with a known journal file
2. Verify metrics match manual calculation
3. Check edge cases: single entry, no consecutive dates, multiple posts per day

When modifying reader:
1. Test with various terminal sizes
2. Verify scrolling behavior with long entries
3. Check note persistence in CSV
