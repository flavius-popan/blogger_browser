#!/usr/bin/env python3
"""
Test script for export functionality.
"""

import re
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from reader import export_journal, apply_cleaners


def test_export_original_mode():
    """Test exporting in original mode (direct copy)."""
    print("Testing export in original mode...")

    # Get a test file
    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    # Export in original mode
    export_path = export_journal(test_file, cleaned_mode=False)

    # Verify the file was copied
    if not export_path.exists():
        print(f"FAILED: Export file not created at {export_path}")
        return False

    # Verify it's an exact copy
    with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
        original_content = f.read()

    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    if original_content != exported_content:
        print("FAILED: Exported file content doesn't match original")
        return False

    print(f"PASSED: File exported to {export_path.name}")
    return True


def test_export_cleaned_mode():
    """Test exporting in cleaned mode (with cleaning applied)."""
    print("\nTesting export in cleaned mode...")

    # Get a test file
    test_file = Path("data/8173.male.42.indUnk.Capricorn.xml")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False

    # Export in cleaned mode
    export_path = export_journal(test_file, cleaned_mode=True)

    # Verify the file was created with _clean suffix
    if not export_path.exists():
        print(f"FAILED: Export file not created at {export_path}")
        return False

    if not export_path.name.endswith("_clean.xml"):
        print(f"FAILED: Export file doesn't have _clean suffix: {export_path.name}")
        return False

    # Read the exported content
    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
        exported_content = f.read()

    # Verify posts have been cleaned
    # Extract a sample post to check
    post_pattern = r"<post>(.*?)</post>"
    posts = re.findall(post_pattern, exported_content, re.DOTALL)

    if not posts:
        print("FAILED: No posts found in exported file")
        return False

    # Check that urlLink has been removed from at least one post (if it existed)
    # Read original to compare
    with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
        original_content = f.read()

    original_posts = re.findall(post_pattern, original_content, re.DOTALL)

    # Check if cleaning was applied
    cleaned_correctly = True
    for i, (orig, cleaned) in enumerate(zip(original_posts, posts)):
        if "urlLink" in orig:
            if "urlLink" in cleaned:
                print(f"FAILED: urlLink not removed from post {i}")
                cleaned_correctly = False
                break

    # Also verify structure is preserved (same number of posts, dates, etc.)
    date_pattern = r"<date>(.*?)</date>"
    original_dates = re.findall(date_pattern, original_content, re.DOTALL)
    exported_dates = re.findall(date_pattern, exported_content, re.DOTALL)

    if len(original_dates) != len(exported_dates):
        print(f"FAILED: Date count mismatch: {len(original_dates)} vs {len(exported_dates)}")
        return False

    if len(original_posts) != len(posts):
        print(f"FAILED: Post count mismatch: {len(original_posts)} vs {len(posts)}")
        return False

    print(f"PASSED: File exported to {export_path.name}")
    print(f"  - Posts cleaned: {len(posts)}")
    print(f"  - Dates preserved: {len(exported_dates)}")

    return cleaned_correctly


def test_multiline_regex():
    """Test that the regex handles multiline content correctly."""
    print("\nTesting multiline regex handling...")

    test_content = """<date>01,January,2004</date>
<post>First line
Second line with urlLink here
Third line</post>
<date>02,January,2004</date>
<post>Another post
With multiple
Lines and urlLink content</post>"""

    def clean_post(match):
        post_content = match.group(1)
        cleaned_content = apply_cleaners(post_content)
        return f"<post>{cleaned_content}</post>"

    cleaned_content = re.sub(r"<post>(.*?)</post>", clean_post, test_content, flags=re.DOTALL)

    # Verify urlLink was removed
    if "urlLink" in cleaned_content:
        print("FAILED: urlLink not removed from multiline content")
        return False

    # Verify structure preserved
    if cleaned_content.count("<post>") != 2:
        print("FAILED: Post tags not preserved")
        return False

    if cleaned_content.count("<date>") != 2:
        print("FAILED: Date tags not preserved")
        return False

    print("PASSED: Multiline regex handling works correctly")
    return True


def cleanup():
    """Clean up test exports."""
    exports_dir = Path("exports")
    if exports_dir.exists():
        shutil.rmtree(exports_dir)
        print("\nCleaned up exports directory")


if __name__ == '__main__':
    try:
        success1 = test_multiline_regex()
        success2 = test_export_original_mode()
        success3 = test_export_cleaned_mode()

        print("\n" + "="*60)
        if success1 and success2 and success3:
            print("All export tests PASSED")
            print("="*60)
        else:
            print("Some export tests FAILED")
            print("="*60)
            exit(1)
    finally:
        cleanup()
