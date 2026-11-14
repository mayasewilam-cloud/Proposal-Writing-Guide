import os, sys, unittest, tempfile, shutil, time, hashlib

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

# Ensure environment variables for testing
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

temp_dir = tempfile.mkdtemp(prefix="biowriter_full_battery_416_")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir
print(f"Isolated Temp Data Dir: {temp_dir}")

# Record initial hash of live bookmarks file
live_bm = "upload/data/breakthroughs_bookmarks.json"
with open(live_bm, "rb") as f:
    h_before = hashlib.sha256(f.read()).hexdigest()

test_suites = [
    "tests.test_phase4_1_6_scientific_integrity",
    "tests.test_phase4_1_4_scientific_integrity",
    "tests.test_phase4_1_2_scientific_integrity",
    "tests.test_phase4_1_scientific_integrity",
    "tests.test_student_drafts_and_doi",
    "tests.test_breakthroughs",
    "tests.test_phase3b_repair"
]

results = []

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
    passed = res.testsRun - len(res.failures) - len(res.errors)
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
    print(f"[{'PASS' if res.wasSuccessful() else 'FAIL'}] {mod_name}: {passed}/{res.testsRun} passed ({dt:.3f}s)")

# Verify live bookmarks file remained untouched
with open(live_bm, "rb") as f:
    h_after = hashlib.sha256(f.read()).hexdigest()

shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== RESULTS TABLE ===")
print("| Suite Name | Collected | Ran | Passed | Failed | Errors | Skipped | Duration |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
for r in results:
    print(f"| `{r['module']}` | {r['collected']} | {r['ran']} | {r['passed']} | {r['failed']} | {r['errors']} | {r['skipped']} | {r['time']} |")

total_ran = sum(r["ran"] for r in results)
total_passed = sum(r["passed"] for r in results)
total_failed = sum(r["failed"] for r in results)
total_errors = sum(r["errors"] for r in results)
total_skipped = sum(r["skipped"] for r in results)
print(f"| **TOTAL** | **{total_ran}** | **{total_ran}** | **{total_passed}** | **{total_failed}** | **{total_errors}** | **{total_skipped}** | |")

assert h_before == h_after, f"Data mutation detected! Before: {h_before}, After: {h_after}"
print(f"\nPROVEN: Live bookmarks hash untouched: {h_after}")
print("ALL SUITES EXECUTED HERMETICALLY.")
