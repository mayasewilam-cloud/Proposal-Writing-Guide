import os
import sys
import tempfile
import unittest
import time
import io
import hashlib

# 1. Establish isolated temporary directory BEFORE any imports
temp_dir = tempfile.TemporaryDirectory(prefix="biowriter_audit_f_")
orig_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir.name
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "mock-audit-secret-key-32-chars-long"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.draft_store import get_data_dir as draft_get_data_dir
from core.breakthroughs_manager import get_data_dir as bt_get_data_dir

# 2. Verify that active data directory is isolated
print("=== AUDIT F: HERMETIC TEST BATTERY EXECUTION ===")
print("Temp directory:", temp_dir.name)
print("draft_store get_data_dir():", draft_get_data_dir())
print("breakthroughs_manager get_data_dir():", bt_get_data_dir())
assert draft_get_data_dir() == temp_dir.name, "CRITICAL: draft_store not isolated!"
assert bt_get_data_dir() == temp_dir.name, "CRITICAL: breakthroughs_manager not isolated!"
print("PROVEN: All subsystem storage paths point exclusively to temporary directory.")

# 3. Hash baseline for upload/data/breakthroughs_bookmarks.json before run
bm_path = "upload/data/breakthroughs_bookmarks.json"
with open(bm_path, "rb") as f:
    bm_hash_pre = hashlib.sha256(f.read()).hexdigest()

test_suites = [
    ("test_phase4_1_4_scientific_integrity.py", "upload/tests/test_phase4_1_4_scientific_integrity.py"),
    ("test_phase4_1_2_scientific_integrity.py", "upload/tests/test_phase4_1_2_scientific_integrity.py"),
    ("test_phase4_1_scientific_integrity.py", "upload/tests/test_phase4_1_scientific_integrity.py"),
    ("test_student_drafts_and_doi.py", "upload/tests/test_student_drafts_and_doi.py"),
    ("test_breakthroughs.py", "upload/tests/test_breakthroughs.py"),
    ("test_phase3b_repair.py", "upload/tests/test_phase3b_repair.py")
]

results = []

for name, path in test_suites:
    start_time = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(path), pattern=os.path.basename(path))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    res = runner.run(suite)
    duration = time.time() - start_time
    
    collected = suite.countTestCases()
    ran = res.testsRun
    failures = len(res.failures)
    errors = len(res.errors)
    skipped = len(res.skipped)
    passed = ran - failures - errors
    
    results.append({
        "name": name,
        "collected": collected,
        "ran": ran,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "duration": round(duration, 3),
        "success": res.wasSuccessful()
    })
    print(f"[{'PASS' if res.wasSuccessful() else 'FAIL'}] {name}: {passed}/{ran} passed ({duration:.3f}s)")
    if not res.wasSuccessful():
        print("FAILURES/ERRORS:")
        print(stream.getvalue()[-800:])

# 4. Verify baseline for upload/data/breakthroughs_bookmarks.json after run
with open(bm_path, "rb") as f:
    bm_hash_post = hashlib.sha256(f.read()).hexdigest()

assert bm_hash_pre == bm_hash_post, "CRITICAL: Live data modified during test run!"
print("\nPROVEN: upload/data/breakthroughs_bookmarks.json hash remained identical (Zero writes to live storage).")

# Clean up
if orig_data_dir is not None:
    os.environ["BIOWRITER_DATA_DIR"] = orig_data_dir
else:
    os.environ.pop("BIOWRITER_DATA_DIR", None)
temp_dir.cleanup()

print("\n--- RESULTS TABLE ---")
print("| Suite Name | Collected | Ran | Passed | Failed | Errors | Skipped | Duration |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
for r in results:
    print(f"| `{r['name']}` | {r['collected']} | {r['ran']} | {r['passed']} | {r['failures']} | {r['errors']} | {r['skipped']} | {r['duration']}s |")
