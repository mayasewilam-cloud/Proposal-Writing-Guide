import unittest, os, sys
sys.stdout.reconfigure(encoding='utf-8')
os.environ['BIOWRITER_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-32-chars-long-abc'
sys.path.insert(0, os.path.abspath('upload'))

suites = [
    'tests.test_phase4_1_6_scientific_integrity',
    'tests.test_phase4_1_4_scientific_integrity',
    'tests.test_phase4_1_2_scientific_integrity',
    'tests.test_phase4_1_scientific_integrity',
    'tests.test_student_drafts_and_doi',
    'tests.test_breakthroughs',
    'tests.test_phase3b_repair'
]

print(f"{'Suite':<45} | {'Collected'}")
print("-" * 60)
total = 0
for s in suites:
    ts = unittest.defaultTestLoader.loadTestsFromName(s)
    c = ts.countTestCases()
    total += c
    print(f"{s:<45} | {c}")
print("-" * 60)
print(f"{'TOTAL':<45} | {total}")
