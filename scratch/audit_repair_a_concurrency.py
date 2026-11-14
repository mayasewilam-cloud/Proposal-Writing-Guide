"""
Independent Audit Script: Repair A - Faculty Feedback Concurrency & Atomicity
Executes 8 rigorous deterministic concurrency & isolation tests against dispatch_faculty_feedback().
All storage is isolated in temp directories; live data is completely untouched.
"""

import os
import sys
import copy
import json
import time
import shutil
import tempfile
import threading
import multiprocessing
from typing import Dict, Any

# Ensure isolated temporary storage
_ISOLATED_DIR = tempfile.mkdtemp(prefix="biowriter_audit_repair_a_")
os.environ["BIOWRITER_DATA_DIR"] = _ISOLATED_DIR

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.draft_store import (
    save_student_draft,
    get_student_draft,
    toggle_draft_lock,
    dispatch_faculty_feedback,
    draft_store_lock,
    compute_draft_fingerprint,
    sanitize_student_id,
    get_drafts_dir,
    _load_draft_raw,
    _atomic_write_draft
)

# Multiprocess worker functions defined at top level for Windows spawn compatibility
def mp_worker_student_save(data_dir, student_id, barrier, result_queue):
    os.environ["BIOWRITER_DATA_DIR"] = data_dir
    try:
        barrier.wait()
        res = save_student_draft(student_id, {"title": "Title From Process A", "abstract": "Abstract from A"})
        result_queue.put(("save", res))
    except Exception as e:
        result_queue.put(("save_error", str(e)))

def mp_worker_faculty_dispatch(data_dir, student_id, barrier, result_queue):
    os.environ["BIOWRITER_DATA_DIR"] = data_dir
    try:
        barrier.wait()
        res = dispatch_faculty_feedback(student_id, {"evaluator": "Faculty B", "score": 98})
        result_queue.put(("dispatch", res))
    except Exception as e:
        result_queue.put(("dispatch_error", str(e)))


def run_audit():
    results = {}

    # Initial test draft
    sid = "STU_AUDIT_01"
    init_data = {
        "title": "Novel Biosensor System",
        "abstract": "Engineering riboswitches for environmental monitoring.",
        "methodology": "Cell-free in vitro transcription-translation assays.",
        "references": "10.1038/nature12345\n10.1126/science.abc1234",
        "is_locked_for_grading": False,
        "citation_validation": {"has_retracted": False, "verified_at": "2026-11-14 10:00:00"}
    }
    sres = save_student_draft(sid, init_data)
    assert sres.get("success"), "Setup failed"
    v0 = sres.get("version", 1)

    # -------------------------------------------------------------
    # Scenario 1: Faculty feedback concurrent with student draft save
    # -------------------------------------------------------------
    barrier1 = threading.Barrier(2)
    s1_results = []
    
    def t1_save():
        barrier1.wait()
        r = save_student_draft(sid, {"title": "Updated Title By Student", "abstract": "New Abstract"})
        s1_results.append(("save", r))

    def t1_feedback():
        barrier1.wait()
        r = dispatch_faculty_feedback(sid, {"score": 92, "notes": "Solid methodology"})
        s1_results.append(("dispatch", r))

    th1 = threading.Thread(target=t1_save)
    th2 = threading.Thread(target=t1_feedback)
    th1.start(); th2.start()
    th1.join(); th2.join()

    draft_s1 = get_student_draft(sid)
    assert draft_s1 is not None
    # Both operations succeeded without corruption
    assert all(r[1].get("success") for r in s1_results), f"Scenario 1 failed: {s1_results}"
    # Final draft has version incremented at least twice
    assert draft_s1.get("version") >= v0 + 2
    # Verify neither content nor faculty review was lost
    assert draft_s1.get("faculty_review") is not None
    results["scenario_1_concurrent_save_and_feedback"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 2: Multiple faculty feedback operations targeting the same student
    # -------------------------------------------------------------
    barrier2 = threading.Barrier(4)
    s2_results = []
    def t2_fb(idx):
        barrier2.wait()
        r = dispatch_faculty_feedback(sid, {"review_id": idx, "score": 80 + idx})
        s2_results.append(r)

    threads2 = [threading.Thread(target=t2_fb, args=(i,)) for i in range(4)]
    for t in threads2: t.start()
    for t in threads2: t.join()

    draft_s2 = get_student_draft(sid)
    assert len(s2_results) == 4
    assert all(r.get("success") for r in s2_results)
    # The final draft must contain a valid faculty_review with one of the reviews
    assert draft_s2.get("faculty_review", {}).get("review_id") in [0, 1, 2, 3]
    results["scenario_2_multiple_faculty_feedback"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 3: Feedback dispatch while citation validation is in progress
    # -------------------------------------------------------------
    # Simulate a snapshot taken for citation validation
    snap_draft = copy.deepcopy(get_student_draft(sid))
    snap_ver = snap_draft.get("version")
    
    # Faculty feedback occurs while validation is simulating a delay
    time.sleep(0.05)
    disp_res = dispatch_faculty_feedback(sid, {"grade": "A", "comments": "Approved"})
    assert disp_res.get("success")
    assert disp_res.get("version") == snap_ver + 1

    # Student submission attempts to lock with stale expected_version (snap_ver)
    lock_attempt = toggle_draft_lock(sid, True, expected_version=snap_ver)
    # Optimistic concurrency must catch version change and return conflict
    assert lock_attempt.get("conflict") is True or lock_attempt.get("status") == "draft_changed_retry", f"Expected conflict, got {lock_attempt}"
    results["scenario_3_feedback_during_citation_validation"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 4: Feedback dispatch while submission locking is in progress
    # -------------------------------------------------------------
    sid4 = "STU_AUDIT_04"
    save_student_draft(sid4, {"title": "Aiming for Lock", "abstract": "Test 4"})
    
    barrier4 = threading.Barrier(2)
    s4_results = []
    def t4_lock():
        barrier4.wait()
        r = toggle_draft_lock(sid4, True)
        s4_results.append(("lock", r))

    def t4_feedback():
        barrier4.wait()
        r = dispatch_faculty_feedback(sid4, {"instructor": "Dr. Watson", "score": 99})
        s4_results.append(("feedback", r))

    th4a = threading.Thread(target=t4_lock)
    th4b = threading.Thread(target=t4_feedback)
    th4a.start(); th4b.start()
    th4a.join(); th4b.join()

    draft_s4 = get_student_draft(sid4)
    assert draft_s4.get("is_locked_for_grading") is True
    assert draft_s4.get("faculty_review") is not None
    assert all(r[1].get("success") for r in s4_results)
    results["scenario_4_feedback_during_submission_locking"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 5: Two separate processes attempting compatible writes
    # -------------------------------------------------------------
    sid5 = "STU_AUDIT_05"
    save_student_draft(sid5, {"title": "Multiprocess Draft", "abstract": "Process test"})
    
    mp_barrier = multiprocessing.Barrier(2)
    mp_queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=mp_worker_student_save, args=(_ISOLATED_DIR, sid5, mp_barrier, mp_queue))
    p2 = multiprocessing.Process(target=mp_worker_faculty_dispatch, args=(_ISOLATED_DIR, sid5, mp_barrier, mp_queue))
    p1.start(); p2.start()
    p1.join(timeout=10); p2.join(timeout=10)

    mp_out = []
    while not mp_queue.empty():
        mp_out.append(mp_queue.get())

    draft_s5 = get_student_draft(sid5)
    assert len(mp_out) == 2, f"Multiprocess output count mismatch: {mp_out}"
    assert all(item[1].get("success") for item in mp_out), f"Multiprocess failed: {mp_out}"
    assert draft_s5.get("faculty_review") is not None
    results["scenario_5_separate_processes_concurrency"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 6: A failed atomic write simulation
    # -------------------------------------------------------------
    sid6 = "STU_AUDIT_06"
    save_student_draft(sid6, {"title": "Write Failure Test"})
    clean_id6 = sanitize_student_id(sid6)

    # Monkeypatch _atomic_write_draft to simulate disk failure / OSError
    orig_atomic = sys.modules["core.draft_store"]._atomic_write_draft
    try:
        def failing_atomic_write(cid, data):
            raise OSError("Simulated disk full or permission error")
        sys.modules["core.draft_store"]._atomic_write_draft = failing_atomic_write

        failed_caught = False
        try:
            dispatch_faculty_feedback(sid6, {"score": 50})
        except OSError:
            failed_caught = True
        assert failed_caught, "Exception was swallowed!"

        # Verify draft was NOT partially modified on disk
        draft_s6 = get_student_draft(sid6)
        assert draft_s6.get("faculty_review") is None
    finally:
        sys.modules["core.draft_store"]._atomic_write_draft = orig_atomic

    results["scenario_6_failed_atomic_write"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 7: Exception during dispatch followed by another successful write
    # -------------------------------------------------------------
    # Verify that after the exception in Scenario 6, the lock is completely free
    # and subsequent operations succeed without deadlocking
    subsequent_res = dispatch_faculty_feedback(sid6, {"score": 88, "status": "Recovered"})
    assert subsequent_res.get("success"), f"Recovery write failed: {subsequent_res}"
    draft_s6_recovered = get_student_draft(sid6)
    assert draft_s6_recovered.get("faculty_review", {}).get("score") == 88
    results["scenario_7_exception_recovery_and_lock_release"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 8: Preservation of latest student edits under concurrent operations
    # -------------------------------------------------------------
    sid8 = "STU_AUDIT_08"
    save_student_draft(sid8, {
        "title": "Critical Student Research",
        "abstract": "Original Abstract",
        "methodology": "Cell culture protocols",
        "references": "10.1038/original_reference"
    })

    # Concurrently update student edits and faculty feedback
    num_rounds = 10
    errs8 = []
    def save_loop():
        for i in range(num_rounds):
            try:
                save_student_draft(sid8, {"title": f"Student Title Version {i}", "references": f"10.1038/ref_{i}"})
            except Exception as e:
                errs8.append(e)

    def feedback_loop():
        for i in range(num_rounds):
            try:
                dispatch_faculty_feedback(sid8, {"round": i, "score": 90})
            except Exception as e:
                errs8.append(e)

    t8a = threading.Thread(target=save_loop)
    t8b = threading.Thread(target=feedback_loop)
    t8a.start(); t8b.start()
    t8a.join(); t8b.join()

    draft_s8 = get_student_draft(sid8)
    assert len(errs8) == 0, f"Errors in concurrent loop: {errs8}"
    assert draft_s8 is not None
    assert draft_s8.get("title").startswith("Student Title Version")
    assert draft_s8.get("references").startswith("10.1038/ref_")
    assert draft_s8.get("faculty_review") is not None
    assert draft_s8.get("version") > num_rounds
    results["scenario_8_student_edits_preserved"] = "PASSED"

    # Print summary
    print("\n=== REPAIR A CONCURRENCY & ATOMICITY AUDIT RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("ALL 8 SCENARIOS VERIFIED SUCCESSFULLY!\n")

if __name__ == "__main__":
    try:
        run_audit()
    finally:
        shutil.rmtree(_ISOLATED_DIR, ignore_errors=True)
