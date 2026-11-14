import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.reference_service import extract_dois

test_cases = [
    # 1. Standard URL schemes
    ("https://doi.org/10.1038/s41586-020-2012-7", ["10.1038/s41586-020-2012-7"], "Standard https doi.org URL"),
    ("http://dx.doi.org/10.1016/j.cell.2020.12.001", ["10.1016/j.cell.2020.12.001"], "Standard http dx.doi.org URL"),
    ("doi: 10.1126/science.1234567", ["10.1126/science.1234567"], "doi: prefix with space"),
    ("doi:10.1073/pnas.1234567890", ["10.1073/pnas.1234567890"], "doi: prefix without space"),
    ("10.1038/nature12345", ["10.1038/nature12345"], "Raw DOI without prefix"),

    # 2. Trailing punctuation and brackets
    ("Smith et al. (2020). Nature, https://doi.org/10.1038/s41586-020-2012-7.", ["10.1038/s41586-020-2012-7"], "Trailing period"),
    ("Jones et al. [doi: 10.1126/science.1234567];", ["10.1126/science.1234567"], "Trailing bracket and semicolon"),
    ("Reference (10.1016/j.cell.2020.12.001),", ["10.1016/j.cell.2020.12.001"], "Trailing parenthesis and comma"),
    ("See [https://doi.org/10.1073/pnas.2000000117]", ["10.1073/pnas.2000000117"], "Surrounded by square brackets"),

    # 3. Multiple and duplicate DOIs with differing casing
    ("First: 10.1038/S41586-020. Second: 10.1016/j.cell.2020.", ["10.1038/s41586-020", "10.1016/j.cell.2020"], "Multiple DOIs in one text"),
    ("Upper: 10.1038/S41586-ABC and lower: 10.1038/s41586-abc", ["10.1038/S41586-ABC"], "Duplicate DOI with different casing"),

    # 4. Embedded in citation prose
    ("According to Tournier et al. (doi:10.1038/s41586-020-2149-4) PETase can be engineered.", ["10.1038/s41586-020-2149-4"], "Embedded in prose"),

    # 5. Malformed DOI-like strings
    ("10.999/not-a-valid-doi-prefix", [], "Invalid registrant prefix (only 3 digits)"),
    ("10.1234567890/toolongprefix", [], "Invalid prefix (>9 digits)"),
    ("10.1038/", [], "Missing suffix"),
    ("10.1038", [], "Prefix only without slash"),
    ("Random string 123.456/789", [], "Non-DOI numbers"),

    # 6. Complex valid DOIs containing parentheses, slashes, or special characters
    ("10.1002/(sici)1097-0258(19980815)17:15<1661::aid-sim879>3.0.co;2-g", ["10.1002/(sici)1097-0258(19980815)17:15<1661::aid-sim879>3.0.co;2-g"], "Wiley SICI DOI with parentheses and angle brackets"),
    ("10.1021/ja01569a008", ["10.1021/ja01569a008"], "Classic ACS DOI"),
    ("10.1000/182(2)", ["10.1000/182(2)"], "DOI with trailing parenthesis as part of the identifier"),

    # 7. Edge cases: Empty, non-string, long strings
    ("", [], "Empty string"),
    (None, [], "NoneType"),
    (12345, [], "Integer"),
    ("a" * 10000, [], "Very long string with no DOI")
]

print("=== AUDIT A.1: extract_dois() EVALUATION ===")
passed = 0
for text, expected, desc in test_cases:
    actual = extract_dois(text)
    # Check if case-insensitive equal or identical
    actual_lower = [a.lower() for a in actual]
    expected_lower = [e.lower() for e in expected]
    match = actual_lower == expected_lower
    if match:
        passed += 1
        print(f"[PASS] {desc}: {actual}")
    else:
        print(f"[NOTE/DIFF] {desc}:")
        print(f"       Input:    {repr(text[:80]) if text else repr(text)}")
        print(f"       Expected: {expected}")
        print(f"       Actual:   {actual}")

print(f"\nSummary: {passed}/{len(test_cases)} tests passed perfectly.")
