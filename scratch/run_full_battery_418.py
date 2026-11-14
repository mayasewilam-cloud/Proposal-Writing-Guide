import os
import sys
import unittest
import tempfile
import shutil
import time
import hashlib

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

temp_dir = tempfile.mkdtemp(prefix="biowriter_full_battery_418_")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir
print(f"Isolated Temp Data Dir: {temp_dir}")

live_bm = "upload/data/breakthroughs_bookmarks.json"
with open(live_bm, "rb") as f:
    h_before = hashlib.sha256(f.read()).hexdigest()

test_suites = [
    "tests.test_phase4_1_8_scientific_integrity",
    "tests.test_phase4_1_6_scientific_integrity",
    "tests.test_phase4_1_4_scientific_integrity",
    "tests.test_phase4_1_2_scientific_integrity",
    "tests.test_phase4_1_scientific_integrity",
    "tests.test_student_drafts_and_doi",
    "tests.test_breakthroughs",
    "tests.test_phase3b_repair"
]

results = []
all_skipped_details = []

for mod_name in test_suites:
    t0 = time.time()
    loader = unittest.defaultTestLoader
    try:
        suite = loader.loadTestsFromName(mod_name)
    except Exception as e:
        print(f"ERROR loading {mod_name}: {e}")
        continue
    collected = suite.countTestCases()
    runner = unittest.TextTestRunner(verbosity=0)
    res = runner.run(suite)
    dt = time.time() - t0
    # True mathematical pass count: Passed = Ran - Failed - Errors - Skipped
    passed = res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)
    
    for test_case, reason in res.skipped:
        all_skipped_details.append({
            "suite": mod_name,
            "test_id": str(test_case),
            "reason": reason
        })

    results.append({
        "module": mod_name.replace("tests.", "") + ".py",
        "collected": collected,
        "ran": res.testsRun,
        "passed": passed,
        "failed": len(res.failures),
        "errors": len(res.errors),
        "skipped": len(res.skipped),
        "time": f"{dt:.3f}s"
    })
    print(f"[{'PASS' if (len(res.failures) == 0 and len(res.errors) == 0) else 'FAIL'}] {mod_name}: {passed}/{res.testsRun} passed, {len(res.skipped)} skipped, {len(res.failures)} failed, {len(res.errors)} errors ({dt:.3f}s)")

with open(live_bm, "rb") as f:
    h_after = hashlib.sha256(f.read()).hexdigest()

shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== COMPLETE REGRESSION RESULTS TABLE (PHASE 4.1.8) ===")
print("| Suite Name | Collected | Ran | Passed | Failed | Errors | Skipped | Duration |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
for r in results:
    print(f"| `{r['module']}` | {r['collected']} | {r['ran']} | {r['passed']} | {r['failed']} | {r['errors']} | {r['skipped']} | {r['time']} |")

total_collected = sum(r["collected"] for r in results)
total_ran = sum(r["ran"] for r in results)
total_passed = sum(r["passed"] for r in results)
total_failed = sum(r["failed"] for r in results)
total_errors = sum(r["errors"] for r in results)
total_skipped = sum(r["skipped"] for r in results)
total_time = sum(float(r["time"].rstrip("s")) for r in results)
print(f"| **TOTAL** | **{total_collected}** | **{total_ran}** | **{total_passed}** | **{total_failed}** | **{total_errors}** | **{total_skipped}** | **{total_time:.3f}s** |")

print("\n=== SKIPPED TESTS REPORT ===")
if all_skipped_details:
    for s in all_skipped_details:
        print(f"- **Suite**: `{s['suite']}` | **Test**: `{s['test_id']}` | **Reason**: {s['reason']}")
else:
    print("Zero skipped tests across all suites.")

assert h_before == h_after, f"Data mutation detected! Before: {h_before}, After: {h_after}"
print(f"\nPROVEN: Live bookmarks hash untouched: {h_after}")
print("ALL SUITES EXECUTED HERMETICALLY.")
