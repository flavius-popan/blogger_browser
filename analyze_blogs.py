#!/usr/bin/env python3
"""
Journal Entry Analysis Script

Parses XML journal files and generates a CSV with metrics including:
- Total entries, perfect continuity, word counts, and date gaps
"""

import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def parse_filename(filename):
    """
    Extract metadata from filename.

    Expected pattern: author_id.gender.age.job.horoscope.xml
    Example: 4334776.male.24.Engineering.Aquarius.xml

    Returns dict with keys: author_id, gender, age, job, horoscope
    """
    pattern = r'(\d+)\.(male|female)\.(\d+)\.([^.]+)\.([^.]+)\.xml'
    match = re.match(pattern, filename)

    if match:
        return {
            'author_id': match.group(1),
            'gender': match.group(2),
            'age': match.group(3),
            'job': match.group(4),
            'horoscope': match.group(5)
        }
    else:
        # Use placeholder values for non-matching filenames
        return {
            'author_id': 'unknown',
            'gender': 'unknown',
            'age': 'unknown',
            'job': 'unknown',
            'horoscope': 'unknown'
        }


def parse_date(date_str):
    """
    Parse date from format: DD,Month,YYYY
    Example: 24,August,2004

    Returns datetime.date object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, '%d,%B,%Y').date()
    except (ValueError, AttributeError):
        return None


def count_words(text):
    """Count words in text by splitting on whitespace."""
    if not text:
        return 0
    return len(text.split())


def analyze_journal(file_path):
    """
    Analyze a single journal XML file.

    Returns dict with metrics:
    - total_entries: number of unique dates
    - perfect_continuity_entries: sum of all consecutive date sequences
    - avg_words_per_entry: average word count per entry
    - total_words: total word count across all entries
    - largest_entry_words: max word count in a single entry
    - date_gaps: number of discontinuities (non-consecutive dates)
    """
    # Read file as text to handle malformed XML
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path.name}: {e}")
        return None

    # Extract dates and posts using regex
    date_pattern = r'<date>(.*?)</date>'
    post_pattern = r'<post>(.*?)</post>'

    dates = re.findall(date_pattern, content, re.DOTALL)
    posts = re.findall(post_pattern, content, re.DOTALL)

    if len(dates) != len(posts):
        print(f"Warning: Mismatch in {file_path.name}: {len(dates)} dates vs {len(posts)} posts")

    # Collect posts grouped by date
    date_posts = defaultdict(list)

    # Pair dates with their corresponding posts
    for i, date_str in enumerate(dates):
        if i < len(posts):
            post_text = posts[i].strip()

            parsed_date = parse_date(date_str.strip())
            if parsed_date:
                date_posts[parsed_date].append(post_text)

    if not date_posts:
        # No valid entries found
        return {
            'total_entries': 0,
            'num_streaks': 0,
            'isolated_entries': 0,
            'longest_streak': 0,
            'avg_streak_length': 0,
            'continuity_percentage': 0,
            'date_gaps': 0,
            'total_words': 0,
            'avg_words_per_entry': 0,
            'largest_entry_words': 0
        }

    # Combine posts from same date and calculate word counts
    entries = []
    for date, post_list in date_posts.items():
        combined_text = ' '.join(post_list)
        word_count = count_words(combined_text)
        entries.append({
            'date': date,
            'words': word_count
        })

    # Sort entries by date
    entries.sort(key=lambda x: x['date'])

    # Calculate metrics
    total_entries = len(entries)
    total_words = sum(e['words'] for e in entries)
    largest_entry_words = max((e['words'] for e in entries), default=0)
    avg_words_per_entry = int(total_words / total_entries) if total_entries > 0 else 0

    # Calculate streak metrics and date gaps
    date_gaps = 0
    longest_streak = 0
    multi_day_sequences = []  # Track all sequences of 2+ days

    if total_entries > 1:
        current_sequence_length = 1  # Start with first entry

        for i in range(1, len(entries)):
            prev_date = entries[i-1]['date']
            curr_date = entries[i]['date']
            expected_next_date = prev_date + timedelta(days=1)

            if curr_date == expected_next_date:
                # Consecutive dates - extend current sequence
                current_sequence_length += 1
            else:
                # Gap found
                date_gaps += 1
                # Track sequences of 2+ consecutive days
                if current_sequence_length >= 2:
                    multi_day_sequences.append(current_sequence_length)
                    longest_streak = max(longest_streak, current_sequence_length)
                # Start new sequence
                current_sequence_length = 1

        # Add the final sequence if it's 2+ days
        if current_sequence_length >= 2:
            multi_day_sequences.append(current_sequence_length)
            longest_streak = max(longest_streak, current_sequence_length)
        elif current_sequence_length == 1:
            # Final entry is isolated, update longest_streak if we never had multi-day sequences
            longest_streak = max(longest_streak, 1) if longest_streak == 0 else longest_streak
    elif total_entries == 1:
        # Single entry in entire journal
        longest_streak = 1

    # Calculate derived metrics
    num_streaks = len(multi_day_sequences)  # Count of multi-day sequences
    streak_days_total = sum(multi_day_sequences)  # Total days within streaks
    isolated_entries = total_entries - streak_days_total
    avg_streak_length = int(streak_days_total / num_streaks) if num_streaks > 0 else 0
    continuity_percentage = int((streak_days_total / total_entries) * 100) if total_entries > 0 else 0

    return {
        'total_entries': total_entries,
        'num_streaks': num_streaks,
        'isolated_entries': isolated_entries,
        'longest_streak': longest_streak,
        'avg_streak_length': avg_streak_length,
        'continuity_percentage': continuity_percentage,
        'date_gaps': date_gaps,
        'total_words': total_words,
        'avg_words_per_entry': avg_words_per_entry,
        'largest_entry_words': largest_entry_words
    }


def main():
    """Process all XML files in data directory and output CSV."""
    data_dir = Path('data')
    output_file = 'journal_analysis.csv'

    # Find all XML files
    xml_files = sorted(data_dir.glob('*.xml'))

    if not xml_files:
        print(f"No XML files found in {data_dir}")
        return

    print(f"Found {len(xml_files)} XML files to process...")

    # Collect results
    results = []

    for xml_file in xml_files:
        print(f"Processing {xml_file.name}...")

        # Parse filename
        metadata = parse_filename(xml_file.name)

        # Analyze journal
        metrics = analyze_journal(xml_file)

        if metrics is None:
            # Skip files that couldn't be parsed
            continue

        # Combine metadata and metrics (exclude job and horoscope)
        result = {
            'filename': xml_file.name,
            'author_id': metadata['author_id'],
            'gender': metadata['gender'],
            'age': metadata['age'],
            **metrics,
            'notes': ''  # Initialize empty notes field
        }

        results.append(result)

    # Sort results:
    # 1. total_entries descending (most entries first)
    # 2. longest_streak descending (longest streaks first)
    # 3. avg_words_per_entry descending (highest word average first)
    # 4. total_words descending (most content first)
    results.sort(
        key=lambda x: (
            -x['total_entries'],        # Negative for descending
            -x['longest_streak'],       # Negative for descending
            -x['avg_words_per_entry'],  # Negative for descending
            -x['total_words']           # Negative for descending
        )
    )

    # Write CSV
    if results:
        # Organized in logical groups: Metadata → Continuity → Words → Notes
        fieldnames = [
            # Metadata
            'filename',
            'author_id',
            'gender',
            'age',
            # Continuity metrics
            'total_entries',
            'num_streaks',
            'isolated_entries',
            'longest_streak',
            'avg_streak_length',
            'continuity_percentage',
            'date_gaps',
            # Word metrics
            'total_words',
            'avg_words_per_entry',
            'largest_entry_words',
            # Notes
            'notes'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"\n✓ Analysis complete! Results written to {output_file}")
        print(f"  Processed {len(results)} journals successfully")
    else:
        print("No valid results to write")


if __name__ == '__main__':
    main()
