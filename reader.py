#!/usr/bin/env python3
"""
Interactive Journal Reader

Uses fzf to select a journal, then displays entries with navigation.
Left/Right arrows to navigate, 'q' to quit.
"""

import re
import sys
import csv
import subprocess
import curses
import textwrap
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def rough_token_estimate(text: str) -> int:
    """Estimate token count using average of two methods."""
    return int(((len(text) / 4) + (len(text.split()) * 1.33)) / 2)


def select_journal_with_fzf():
    """Use fzf to select a journal file, showing metrics from CSV."""
    data_dir = Path("data")
    csv_path = Path("journal_analysis.csv")

    # Load metrics from CSV (preserving CSV sort order)
    csv_entries = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_entries.append(
                    {
                        "filename": row["filename"],
                        "total_entries": row["total_entries"],
                        "longest_streak": row["longest_streak"],
                        "avg_words": row["avg_words_per_entry"],
                        "total_words": row["total_words"],
                        "num_streaks": row.get("num_streaks", "0"),
                        "notes": row.get("notes", ""),
                    }
                )

    if not csv_entries:
        print("No entries found in journal_analysis.csv")
        print("Run analyze_journals.py first to generate metrics")
        sys.exit(1)

    # Sort entries: journals with notes first (sorted by total_entries desc),
    # then journals without notes (sorted by total_entries desc)
    csv_entries.sort(key=lambda x: (x["notes"] == "", -int(x["total_entries"])))

    # Build fzf input with metrics
    fzf_lines = []
    for entry in csv_entries:
        m = entry
        # Truncate notes to 30 characters if they exist
        notes_display = m["notes"][:30] + "..." if len(m["notes"]) > 30 else m["notes"]
        notes_display = notes_display if notes_display else ""

        line = f"{m['filename']:<50} │ {m['total_entries']:>4} entries │ {m['longest_streak']:>3} days │ {m['num_streaks']:>3} streaks │ {m['avg_words']:>4} wds/ent │ {notes_display}"
        fzf_lines.append(line)

    file_list = "\n".join(fzf_lines)

    try:
        result = subprocess.run(
            [
                "fzf",
                "--prompt=Select journal: ",
                "--height=100%",
                "--reverse",
                "--ansi",
            ],
            input=file_list,
            text=True,
            capture_output=True,
            check=True,
        )
        # Extract filename from the selected line (first field before │)
        selected = result.stdout.strip()
        filename = selected.split("│")[0].strip()
        return data_dir / filename
    except subprocess.CalledProcessError:
        # User cancelled or fzf not found
        sys.exit(0)


def parse_date(date_str):
    """Parse date from format: DD,Month,YYYY"""
    try:
        return datetime.strptime(date_str, "%d,%B,%Y").date()
    except (ValueError, AttributeError):
        return None


def parse_journal(file_path):
    """
    Parse journal file and return entries sorted by date.

    Returns:
        - entries: list of dicts with 'date' and 'text'
        - total_entries: count of unique dates
        - longest_streak: longest consecutive sequence
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Extract dates and posts using regex
    date_pattern = r"<date>(.*?)</date>"
    post_pattern = r"<post>(.*?)</post>"

    dates = re.findall(date_pattern, content, re.DOTALL)
    posts = re.findall(post_pattern, content, re.DOTALL)

    # Group posts by date (combine multiple posts on same date)
    date_posts = defaultdict(list)

    for i, date_str in enumerate(dates):
        if i < len(posts):
            post_text = posts[i].strip()
            parsed_date = parse_date(date_str.strip())
            if parsed_date:
                date_posts[parsed_date].append(post_text)

    # Create entries list
    entries = []
    for date, post_list in date_posts.items():
        # Reverse so last post of the day appears first
        post_list.reverse()
        combined_text = "\n\n".join(post_list)
        token_count = rough_token_estimate(combined_text)
        entries.append({"date": date, "text": combined_text, "token_count": token_count})

    # Sort by date
    entries.sort(key=lambda x: x["date"])

    # Calculate longest streak
    longest_streak = 0
    if len(entries) > 1:
        current_streak = 1
        for i in range(1, len(entries)):
            prev_date = entries[i - 1]["date"]
            curr_date = entries[i]["date"]
            if curr_date == prev_date + timedelta(days=1):
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        longest_streak = max(longest_streak, current_streak)
    elif len(entries) == 1:
        longest_streak = 1

    return entries, len(entries), longest_streak


def save_note_to_csv(filename, note_text):
    """Update the notes field for a journal in the CSV file."""
    csv_path = Path("journal_analysis.csv")

    if not csv_path.exists():
        return False

    # Read all rows
    rows = []
    fieldnames = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["filename"] == filename:
                row["notes"] = note_text
            rows.append(row)

    # Write back
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True


def get_current_note(filename):
    """Get the current note for a journal from the CSV file."""
    csv_path = Path("journal_analysis.csv")

    if not csv_path.exists():
        return ""

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["filename"] == filename:
                return row.get("notes", "")

    return ""


def display_journal(stdscr, file_path, entries, total_entries, longest_streak):
    """Display journal with curses TUI and navigation."""
    # Set up curses
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()

    # Initialize colors
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)

    current_index = 0
    scroll_offset = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Header: filename
        header = f"📖 {file_path.name}"
        stdscr.addstr(0, 0, header[: width - 1], curses.color_pair(1) | curses.A_BOLD)

        # Subheader: stats
        stats = (
            f"Total Entries: {total_entries} | Longest Streak: {longest_streak} days"
        )
        stdscr.addstr(1, 0, stats[: width - 1], curses.color_pair(3))

        # Page indicator
        page_info = f"Entry {current_index + 1} of {total_entries}"
        stdscr.addstr(2, 0, page_info[: width - 1], curses.color_pair(2))

        # Separator
        stdscr.addstr(3, 0, "─" * (width - 1))

        # Current entry
        if entries:
            entry = entries[current_index]
            date_str = entry["date"].strftime("%B %d, %Y (%A)")
            text = entry["text"]
            token_count = entry.get("token_count", 0)

            # Display date
            stdscr.addstr(
                4, 0, date_str[: width - 1], curses.color_pair(2) | curses.A_BOLD
            )

            # Display post content (with scrolling if needed)
            text_lines = []
            for line in text.split("\n"):
                # Wrap long lines at word boundaries
                if len(line) == 0:
                    text_lines.append("")
                else:
                    wrapped = textwrap.wrap(
                        line,
                        width=width - 3,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                    if wrapped:
                        text_lines.extend(wrapped)
                    else:
                        # Empty or whitespace-only line
                        text_lines.append("")

            # Calculate available space for text
            content_start_row = 6
            available_rows = height - content_start_row - 2  # Leave room for footer

            # Display text with scroll offset
            for i, line in enumerate(
                text_lines[scroll_offset : scroll_offset + available_rows]
            ):
                try:
                    stdscr.addstr(content_start_row + i, 1, line[: width - 2])
                except curses.error:
                    pass  # Ignore if we run out of space

            # Footer with controls
            footer = (
                "← Prev | Next → | ↑↓ Scroll | n: Note | y: Yank | q: Back"
            )
            try:
                stdscr.addstr(height - 1, 0, footer[: width - 1], curses.A_DIM)
            except curses.error:
                pass

            # Token count on bottom right
            token_text = f"~{token_count} tokens"
            try:
                token_x = width - len(token_text) - 1
                if token_x > len(footer) + 2:  # Only show if there's space
                    stdscr.addstr(
                        height - 1, token_x, token_text,
                        curses.color_pair(4) | curses.A_DIM
                    )
            except curses.error:
                pass

        stdscr.refresh()

        # Handle keyboard input
        key = stdscr.getch()

        if key == ord("q") or key == ord("Q"):
            break
        elif key == ord("n") or key == ord("N"):
            # Add/Edit note for this journal
            # Temporarily exit curses to get input
            curses.endwin()

            # Get current note
            current_note = get_current_note(file_path.name)

            print(f"\nNote for {file_path.name}")
            if current_note:
                print(f"Current: {current_note}")
            print("Enter note (blank to remove):")

            try:
                new_note = input("> ").strip()
                # Save note to CSV
                save_note_to_csv(file_path.name, new_note)
                print(f"✓ Note {'saved' if new_note else 'removed'}")
            except (EOFError, KeyboardInterrupt):
                print("✗ Cancelled")

            # Brief pause so user can see the confirmation
            time.sleep(0.5)

            # Re-initialize curses
            stdscr.clear()
            stdscr.refresh()

        elif key == ord("y") or key == ord("Y"):
            # Yank (copy) current post to clipboard using pbcopy
            if entries:
                entry = entries[current_index]
                text = entry["text"]
                try:
                    subprocess.run(
                        ["pbcopy"],
                        input=text,
                        text=True,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    pass  # Silently fail if pbcopy not available

        elif key == curses.KEY_RIGHT and current_index < total_entries - 1:
            current_index += 1
            scroll_offset = 0  # Reset scroll when changing entries
        elif key == curses.KEY_LEFT and current_index > 0:
            current_index -= 1
            scroll_offset = 0  # Reset scroll when changing entries
        elif key == curses.KEY_DOWN:
            # Scroll down
            scroll_offset += 1
        elif key == curses.KEY_UP and scroll_offset > 0:
            # Scroll up
            scroll_offset -= 1
        elif key == ord("j"):  # Vim-style down
            scroll_offset += 1
        elif key == ord("k") and scroll_offset > 0:  # Vim-style up
            scroll_offset -= 1
        elif key == ord("l") and current_index < total_entries - 1:  # Vim-style right
            current_index += 1
            scroll_offset = 0
        elif key == ord("h") and current_index > 0:  # Vim-style left
            current_index -= 1
            scroll_offset = 0


def main():
    """Main entry point - loops to allow jumping between journals."""
    while True:
        # Select journal with fzf
        try:
            journal_path = select_journal_with_fzf()
        except SystemExit:
            # User cancelled fzf - exit program
            break

        # Parse journal
        entries, total_entries, longest_streak = parse_journal(journal_path)

        if not entries:
            print(f"No valid entries found in {journal_path.name}")
            print("Press Enter to continue...")
            input()
            continue

        # Display with curses
        curses.wrapper(
            display_journal, journal_path, entries, total_entries, longest_streak
        )

        # When user presses 'q', loop back to fzf picker


if __name__ == "__main__":
    main()
