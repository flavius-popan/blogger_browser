#!/usr/bin/env python3
"""
Test script for export functionality.
Tests that export combines multiple posts per date (like the reader).
"""

import re
import sys
import shutil
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from reader import export_journal, apply_cleaners, parse_date


def count_unique_dates(content):
    """Count unique dates in XML content."""
    date_pattern = r"<date>(.*?)</date>"
    dates = re.findall(date_pattern, content, re.DOTALL)
    unique_dates = set()
    for date_str in dates:
        parsed = parse_date(date_str.strip())
        if parsed:
            unique_dates.add(parsed)
    return len(unique_dates)


def test_export_combines_posts():
    """Test that export combines multiple posts on the same date."""
    print("Testing post combination...")

    # Get a test file
    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    # Read original to count unique dates vs total date tags
    with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
        original_content = f.read()

    original_date_tags = len(re.findall(r"<date>", original_content))
    unique_dates = count_unique_dates(original_content)

    # Export (original mode to test combination without cleaning)
    export_path = export_journal(test_file, cleaned_mode=False)

    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    exported_date_tags = len(re.findall(r"<date>", exported_content))
    exported_post_tags = len(re.findall(r"<post>", exported_content))

    # Exported should have one date/post pair per unique date
    if exported_date_tags != unique_dates:
        print(f"FAILED: Expected {unique_dates} dates, got {exported_date_tags}")
        return False

    if exported_post_tags != unique_dates:
        print(f"FAILED: Expected {unique_dates} posts, got {exported_post_tags}")
        return False

    print(f"PASSED: Combined {original_date_tags} entries into {unique_dates} unique dates")
    return True


def test_export_original_mode():
    """Test exporting in original mode (combined but not cleaned)."""
    print("\nTesting export in original mode...")

    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    export_path = export_journal(test_file, cleaned_mode=False)

    if not export_path.exists():
        print(f"FAILED: Export file not created at {export_path}")
        return False

    # Should NOT have _clean suffix
    if "_clean" in export_path.name:
        print(f"FAILED: Original mode should not have _clean suffix")
        return False

    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    # urlLink should still be present (not cleaned)
    if "urlLink" not in exported_content:
        # Check if original has urlLink
        with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
            if "urlLink" in f.read():
                print("FAILED: Original mode should preserve urlLink markers")
                return False

    print(f"PASSED: File exported to {export_path.name}")
    return True


def test_export_cleaned_mode():
    """Test exporting in cleaned mode (combined and cleaned)."""
    print("\nTesting export in cleaned mode...")

    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    export_path = export_journal(test_file, cleaned_mode=True)

    if not export_path.exists():
        print(f"FAILED: Export file not created at {export_path}")
        return False

    if not export_path.name.endswith("_clean.xml"):
        print(f"FAILED: Export file doesn't have _clean suffix: {export_path.name}")
        return False

    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    # urlLink should be removed
    if "urlLink" in exported_content:
        print("FAILED: urlLink not removed in cleaned mode")
        return False

    # Should have valid XML structure
    post_count = len(re.findall(r"<post>", exported_content))
    date_count = len(re.findall(r"<date>", exported_content))

    if post_count != date_count:
        print(f"FAILED: Mismatched post/date count: {post_count} vs {date_count}")
        return False

    if post_count == 0:
        print("FAILED: No posts in exported file")
        return False

    print(f"PASSED: File exported to {export_path.name}")
    print(f"  - Unique dates: {date_count}")
    print(f"  - urlLink markers removed")
    return True


def test_chronological_order():
    """Test that exported entries are in chronological order."""
    print("\nTesting chronological ordering...")

    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    export_path = export_journal(test_file, cleaned_mode=False)

    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    dates = re.findall(r"<date>(.*?)</date>", exported_content, re.DOTALL)
    parsed_dates = [parse_date(d.strip()) for d in dates]
    parsed_dates = [d for d in parsed_dates if d is not None]

    # Check if sorted
    if parsed_dates != sorted(parsed_dates):
        print("FAILED: Dates are not in chronological order")
        return False

    print(f"PASSED: {len(parsed_dates)} entries in chronological order")
    return True


def cleanup():
    """Clean up test exports."""
    exports_dir = Path("exports")
    if exports_dir.exists():
        shutil.rmtree(exports_dir)
        print("\nCleaned up exports directory")


if __name__ == '__main__':
    try:
        success1 = test_export_combines_posts()
        success2 = test_export_original_mode()
        success3 = test_export_cleaned_mode()
        success4 = test_chronological_order()

        print("\n" + "="*60)
        if all([success1, success2, success3, success4]):
            print("All export tests PASSED")
            print("="*60)
        else:
            print("Some export tests FAILED")
            print("="*60)
            exit(1)
    finally:
        cleanup()
