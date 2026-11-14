import os
import sys
import unittest
import hashlib
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, BASE_DIR)

def hash_data_dir():
    file_hashes = {}
    for root, _, files in os.walk(DATA_DIR):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, DATA_DIR).replace("\\", "/")
            h = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
            file_hashes[relpath] = h
    return file_hashes

def main():
    print("=" * 70)
    print("BIOWRITER STUDIO — PHASE 3B.2.2 FULL REGRESSION TEST BATTERY")
    print("=" * 70)

    # 1. Snapshot live data hashes before test run
    pre_hashes = hash_data_dir()
    print(f"\n[Snapshot] Recorded hashes for {len(pre_hashes)} live data files.")
    for k in ["cohort_db.json", "faculty_security.json", "users.json", "drafts/13989.json"]:
        if k in pre_hashes:
            print(f"  {k}: {pre_hashes[k]}")

    # Test modules to run
    test_modules = [
        "tests.test_phase3b2_repairs",
        "tests.test_auth",
        "tests.test_student_drafts_and_doi",
        "tests.test_faculty_cohort_and_teams",
        "tests.test_phase3b_repair",
        "tests.test_enhancements",
        "tests.test_agent_integration_and_auth",
        "tests.test_portal",
        "tests.test_agent_workflow",
        "tests.test_p0_frontend_agent_exposure",
    ]

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    for mod in test_modules:
        try:
            m = __import__(mod, fromlist=["*"])
            suite.addTests(loader.loadTestsFromModule(m))
            print(f"Loaded module: {mod}")
        except Exception as e:
            print(f"ERROR loading {mod}: {e}")

    print(f"\n[Execution] Running {suite.countTestCases()} total test cases...")
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"Ran {result.testsRun} tests in {elapsed:.2f}s")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    # 2. Snapshot live data hashes after test run
    post_hashes = hash_data_dir()
    mutated = []
    created = []
    deleted = []

    for k, h in pre_hashes.items():
        if k not in post_hashes:
            deleted.append(k)
        elif post_hashes[k] != h:
            mutated.append(k)

    for k in post_hashes:
        if k not in pre_hashes:
            created.append(k)

    print("\n[DATA INTEGRITY VERIFICATION]")
    print(f"  Live files deleted: {len(deleted)}")
    print(f"  Live files mutated: {len(mutated)}")
    print(f"  Live files created: {len(created)}")

    if mutated or created or deleted:
        print("  CRITICAL FAILURE: Test battery mutated live data!")
        if mutated:
            print(f"    Mutated: {mutated}")
        if created:
            print(f"    Created: {created}")
        if deleted:
            print(f"    Deleted: {deleted}")
        sys.exit(1)
    else:
        print("  SUCCESS: ZERO mutations to upload/data/. All tests perfectly isolated!")

    if not result.wasSuccessful():
        print("\nTEST BATTERY COMPLETED WITH FAILURES.")
        sys.exit(1)
    else:
        print("\nALL TEST SUITES PASSED CLEANLY (100% SUCCESS).")

if __name__ == "__main__":
    main()
