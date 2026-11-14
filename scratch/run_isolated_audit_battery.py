import os
import sys
import subprocess
import hashlib
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def hash_data_dir():
    file_hashes = {}
    for root, _, files in os.walk(DATA_DIR):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, DATA_DIR).replace("\\", "/")
            h = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
            file_hashes[relpath] = h
    return file_hashes

test_suites = [
    ("test_enhancements.py", "upload/tests/test_enhancements.py"),
    ("test_phase3b2_repairs.py", "upload/tests/test_phase3b2_repairs.py"),
    ("test_phase3b_repair.py", "upload/tests/test_phase3b_repair.py"),
    ("test_student_drafts_and_doi.py", "upload/tests/test_student_drafts_and_doi.py"),
    ("test_auth.py", "upload/tests/test_auth.py"),
    ("test_faculty_cohort_and_teams.py", "upload/tests/test_faculty_cohort_and_teams.py"),
    ("test_agent_integration_and_auth.py", "upload/tests/test_agent_integration_and_auth.py"),
    ("test_portal.py", "upload/tests/test_portal.py"),
    ("test_p0_frontend_agent_exposure.py", "upload/tests/test_p0_frontend_agent_exposure.py"),
]

def main():
    print("=" * 80)
    print("PHASE 3B.2.3 INDEPENDENT SUBPROCESS TEST ISOLATION & REGRESSION AUDIT")
    print("=" * 80)

    initial_hashes = hash_data_dir()
    print(f"Initial live data file count: {len(initial_hashes)}")

    suite_results = []

    for name, path in test_suites:
        print(f"\n--- Running {name} in isolated subprocess ---")
        pre_h = hash_data_dir()
        t0 = time.time()
        res = subprocess.run(
            [sys.executable, "-m", "unittest", path],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - t0
        post_h = hash_data_dir()

        # Check mutations
        mutated = [k for k in pre_h if pre_h[k] != post_h.get(k)]
        created = [k for k in post_h if k not in pre_h]
        deleted = [k for k in pre_h if k not in post_h]

        out = res.stdout + res.stderr
        last_lines = [l for l in out.strip().splitlines() if l.strip()][-3:]

        passed = res.returncode == 0
        suite_results.append({
            "name": name,
            "returncode": res.returncode,
            "elapsed": elapsed,
            "mutated": len(mutated),
            "created": len(created),
            "deleted": len(deleted),
            "output_tail": "\n".join(last_lines)
        })

        print(f"  Exit code: {res.returncode}")
        print(f"  Duration: {elapsed:.2f}s")
        print(f"  Mutations to live data: {len(mutated)} mut, {len(created)} created, {len(deleted)} deleted")
        print(f"  Summary output:")
        for l in last_lines:
            print(f"    {l}")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY LEDGER ACROSS ALL 9 TEST SUITES")
    print("=" * 80)

    final_hashes = hash_data_dir()
    total_mut = [k for k in initial_hashes if initial_hashes[k] != final_hashes.get(k)]
    total_cre = [k for k in final_hashes if k not in initial_hashes]
    total_del = [k for k in initial_hashes if k not in final_hashes]

    print(f"{'Suite Name':<35} | {'Status':<8} | {'Time (s)':<8} | {'Data Mutations':<15}")
    print("-" * 75)
    for sr in suite_results:
        status_str = "PASS" if sr["returncode"] == 0 else "FAIL"
        mut_str = f"{sr['mutated']}m / {sr['created']}c / {sr['deleted']}d"
        print(f"{sr['name']:<35} | {status_str:<8} | {sr['elapsed']:<8.2f} | {mut_str:<15}")

    print("-" * 75)
    print(f"Total live data modifications across entire audit: {len(total_mut)} mutated, {len(total_cre)} created, {len(total_del)} deleted.")

if __name__ == "__main__":
    main()
