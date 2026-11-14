import os
import sys
import unittest
import time
import io

os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

test_files = [
    "upload/tests/test_phase4_1_4_scientific_integrity.py",
    "upload/tests/test_phase4_1_2_scientific_integrity.py",
    "upload/tests/test_phase4_1_scientific_integrity.py",
    "upload/tests/test_student_drafts_and_doi.py",
    "upload/tests/test_breakthroughs.py",
    "upload/tests/test_phase3b_repair.py"
]

results_summary = []

for tf in test_files:
    start_time = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(tf), pattern=os.path.basename(tf))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    res = runner.run(suite)
    duration = time.time() - start_time
    
    results_summary.append({
        "file": tf,
        "collected": suite.countTestCases(),
        "run": res.testsRun,
        "passed": res.testsRun - len(res.failures) - len(res.errors),
        "failures": len(res.failures),
        "errors": len(res.errors),
        "skipped": len(res.skipped),
        "duration": round(duration, 3),
        "success": res.wasSuccessful()
    })
    print(f"{tf}: {'PASS' if res.wasSuccessful() else 'FAIL'} ({res.testsRun} run in {round(duration, 3)}s)")
    if not res.wasSuccessful():
        print(stream.getvalue()[-1000:])

print("\n--- SUMMARY TABLE ---")
for r in results_summary:
    print(f"{r['file']} | Collected: {r['collected']} | Ran: {r['run']} | Passed: {r['passed']} | Failed: {r['failures']} | Errors: {r['errors']} | Duration: {r['duration']}s")
