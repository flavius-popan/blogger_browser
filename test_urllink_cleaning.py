#!/usr/bin/env python3
"""
Test script for urlLink cleaning function.
Tests against real patterns found in the Blog Authorship Corpus.
"""

import re
import sys
sys.path.insert(0, '.')

from reader import clean_urllink, apply_cleaners


def test_cleaning():
    """Test various urlLink patterns found in the corpus."""

    test_cases = [
        # Empty/blank urlLinks
        (
            "This is Paul...he's my boyfriend! yay Paul!  urlLink ",
            "This is Paul...he's my boyfriend! yay Paul!"
        ),

        # Actual URLs (should be preserved as plain text to match corpus style)
        (
            "Check it out at urlLink www.onpointmediagroup.com .",
            "Check it out at www.onpointmediagroup.com."
        ),
        (
            "Visit urlLink http://example.com for more",
            "Visit http://example.com for more"
        ),
        (
            "urlLink bencarrfamily.com has the info",
            "bencarrfamily.com has the info"
        ),

        # Generic anchor text (keep the text)
        (
            "Check it out urlLink here .",
            "Check it out here."
        ),
        (
            "Click urlLink here for details",
            "Click here for details"
        ),
        (
            "urlLink see this link",
            "see this link"
        ),

        # Descriptive anchor text (keep the text)
        (
            "urlLink Marshall Whitman rocks my world.",
            "Marshall Whitman rocks my world."
        ),
        (
            "urlLink The Beatles were amazing",
            "The Beatles were amazing"
        ),
        (
            "I read urlLink Mirkin's article yesterday",
            "I read Mirkin's article yesterday"
        ),

        # Multiple urlLinks in one text
        (
            "urlLink In 1999, Dr. Mirkin published an article in an obscure academic journal likening the \"moral panic\" surrounding pedophilia to the outrage of previous generations over feminism and homosexuality. urlLink Mirkin's article , via urlLink Metafilter .",
            "In 1999, Dr. Mirkin published an article in an obscure academic journal likening the \"moral panic\" surrounding pedophilia to the outrage of previous generations over feminism and homosexuality. Mirkin's article, via Metafilter."
        ),

        # Mixed patterns
        (
            "Visit urlLink www.example.com or click urlLink here for more info.",
            "Visit www.example.com or click here for more info."
        ),

        # Edge cases
        (
            "text urlLink urlLink more text",
            "text more text"
        ),
        (
            "urlLink ",
            ""
        ),
    ]

    print("Testing urlLink cleaning function...\n")
    passed = 0
    failed = 0

    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = clean_urllink(input_text)

        if result == expected:
            print(f"✓ Test {i} passed")
            passed += 1
        else:
            print(f"✗ Test {i} FAILED")
            print(f"  Input:    {repr(input_text)}")
            print(f"  Expected: {repr(expected)}")
            print(f"  Got:      {repr(result)}")
            print()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'='*60}")

    return failed == 0


def test_real_examples():
    """Test with actual examples from the corpus."""

    print("\n\nTesting with real corpus examples...\n")

    real_examples = [
        # From 584088.male.33.Education.Pisces.xml
        'urlLink In 1999, Dr. Mirkin published an article in an obscure academic journal likening the "moral panic" surrounding pedophilia to the outrage of previous generations over feminism and homosexuality...Last week, the Missouri Legislature voted to cut $100,000 from the university\'s budget, saying taxpayers did not want to finance such perversity.',

        # From 2844168.female.27.Marketing.Aquarius.xml
        "President Bush took the advice of the intelligence community and the United Nations that Iraq had chemical and biological weapons. He chose to trust information from the world and our best and brightest rather than that of a mass murderer. Since our invasion we have not found what we had been led to believe...Until now - could we be seeing evidence of these weapons? Check the link to see this breaking story. urlLink WMD news",

        # From same file
        "I think Ked just put up the new onPO!NT Media Group site. Check it out at urlLink www.onpointmediagroup.com . It's a sweet site and gives a good picture of what Ked is capable of designing.",
    ]

    for i, example in enumerate(real_examples, 1):
        print(f"Example {i}:")
        print(f"Before: {example[:100]}...")
        cleaned = clean_urllink(example)
        print(f"After:  {cleaned[:100]}...")
        print()


def test_apply_cleaners_integration():
    """Test that apply_cleaners includes urlLink cleaning."""

    print("\n\nTesting apply_cleaners() integration...\n")

    test_cases = [
        # urlLink cleaning
        (
            "Check it out at urlLink www.example.com for more info.",
            "Check it out at www.example.com for more info."
        ),
        # Double spaces
        (
            "This  has   extra    spaces",
            "This has extra spaces"
        ),
        # Multiple newlines
        (
            "Line 1\n\n\n\nLine 2",
            "Line 1\n\nLine 2"
        ),
        # Combined: urlLink + double spaces + newlines
        (
            "urlLink Here  is some  text\n\n\n\nMore  urlLink content",
            "Here is some text\n\nMore content"
        ),
    ]

    passed = 0
    failed = 0

    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = apply_cleaners(input_text)

        if result == expected:
            print(f"✓ Test {i} passed")
            passed += 1
        else:
            print(f"✗ Test {i} FAILED")
            print(f"  Input:    {repr(input_text)}")
            print(f"  Expected: {repr(expected)}")
            print(f"  Got:      {repr(result)}")
            print()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Integration tests: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    return failed == 0


if __name__ == '__main__':
    success1 = test_cleaning()
    test_real_examples()
    success2 = test_apply_cleaners_integration()

    if not (success1 and success2):
        exit(1)
