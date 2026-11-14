import os
import sys
import json
import time
import tempfile
import shutil
import threading
import multiprocessing
import hashlib
from contextlib import contextmanager
from unittest.mock import patch

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

temp_dir = tempfile.mkdtemp(prefix="biowriter_audit_419_atomicity_")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

from app import app
app.config["TESTING"] = True

from core.draft_store import (
    save_student_draft,
    get_student_draft,
    toggle_draft_lock,
    compute_draft_fingerprint,
    draft_store_lock,
    _atomic_write_draft
)
from core.reference_service import CitationStatusCache, validate_citation_text

print(f"Isolated Data Dir for Audit: {temp_dir}")

def proc_save_worker(p_id, t_dir, student_id):
    os.environ["BIOWRITER_DATA_DIR"] = t_dir
    os.environ["BIOWRITER_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"
    for i in range(5):
        save_student_draft(student_id, {"title": f"Proc {p_id} Iter {i}"})
        time.sleep(0.01)

def proc_sub_worker(p_id, t_dir, student_id, res_list):
    os.environ["BIOWRITER_DATA_DIR"] = t_dir
    os.environ["BIOWRITER_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"
    app.config["TESTING"] = True
    c = CitationStatusCache()
    c.set("10.1126/science.aar6245", {"success": True, "doi": "10.1126/science.aar6245", "is_retracted": False})
    with app.test_client() as cl:
        r = cl.post("/api/student/lock", json={"student_id": student_id, "is_locked": True})
        res_list.append((p_id, r.status_code))

@contextmanager
def unittest_mock_meta(doi, is_retracted):
    meta = {
        "success": True,
        "doi": doi,
        "title": "Mock Title",
        "is_retracted": is_retracted,
        "is_expression_of_concern": False
    }
    with patch("core.reference_service.fetch_doi_metadata", return_value=meta):
        yield

def run_tests():
    client = app.test_client()
    test_results = []

    def record(name, passed, details):
        test_results.append({"name": name, "passed": passed, "details": details})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} - {details}")

    # Scenario 1: Clean draft validated and locked successfully
    sid = "TEST-419-01"
    save_student_draft(sid, {"student_id": sid, "title": "Initial", "references": "Chen et al. 2018. DOI: 10.1126/science.aar6245"})
    with app.test_client() as c:
        with unittest_mock_meta("10.1126/science.aar6245", False):
            resp = c.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
            d = get_student_draft(sid)
            record("1. Clean draft validation & lock", resp.status_code == 200 and d.get("is_locked_for_grading") is True, f"HTTP {resp.status_code}, locked={d.get('is_locked_for_grading')}")

    # Scenario 2: Save that changes references but not other proposal fields during validation
    sid = "TEST-419-02"
    save_student_draft(sid, {"student_id": sid, "title": "Stable Title", "references": "Clean. DOI: 10.1126/science.aar6245"})
    snap = get_student_draft(sid)
    # Simulate interim edit of references
    interim = dict(snap)
    interim["references"] = "Changed. DOI: 10.1016/j.cell.new"
    save_student_draft(sid, interim)
    # Commit with stale snapshot
    res = toggle_draft_lock(sid, True, expected_version=snap["version"], expected_fingerprint=snap["content_fingerprint"])
    final = get_student_draft(sid)
    record("2. References changed in interim", res.get("status") == "draft_changed_retry" and final.get("is_locked_for_grading") is False, f"status={res.get('status')}, locked={final.get('is_locked_for_grading')}")

    # Scenario 3: Save that changes proposal text but leaves references unchanged during validation
    sid = "TEST-419-03"
    save_student_draft(sid, {"student_id": sid, "title": "Old Title", "references": "Clean. DOI: 10.1126/science.aar6245"})
    snap = get_student_draft(sid)
    interim = dict(snap)
    interim["title"] = "New Title"
    save_student_draft(sid, interim)
    res = toggle_draft_lock(sid, True, expected_version=snap["version"], expected_fingerprint=snap["content_fingerprint"])
    final = get_student_draft(sid)
    record("3. Text changed with unchanged refs", res.get("status") == "draft_changed_retry" and final.get("is_locked_for_grading") is False, f"status={res.get('status')}, locked={final.get('is_locked_for_grading')}")

    # Scenario 4: Legacy draft without version or fingerprint fields
    sid = "TEST-419-04"
    fpath = os.path.join(temp_dir, "drafts", f"{sid}.json")
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump({"student_id": sid, "title": "Legacy Proposal", "references": "10.1126/science.aar6245"}, f)
    loaded = get_student_draft(sid)
    record("4. Legacy draft defaults", loaded.get("version") == 1 and bool(loaded.get("content_fingerprint")), f"version={loaded.get('version')}, fp={loaded.get('content_fingerprint')[:8]}...")

    # Scenario 5: Stored fingerprint tampered with
    sid = "TEST-419-05"
    save_student_draft(sid, {"student_id": sid, "title": "Tamper Test", "references": "10.1126/science.aar6245"})
    snap = get_student_draft(sid)
    with open(os.path.join(temp_dir, "drafts", f"{sid}.json"), "r+", encoding="utf-8") as f:
        d = json.load(f)
        d["content_fingerprint"] = "corrupted_fake_fingerprint"
        f.seek(0)
        json.dump(d, f)
        f.truncate()
    res = toggle_draft_lock(sid, True, expected_version=snap["version"], expected_fingerprint=snap["content_fingerprint"])
    record("5. Tampered fingerprint rejected", res.get("status") == "draft_changed_retry", f"status={res.get('status')}")

    # Scenario 6: Concurrent save immediately after rejected submission
    sid = "TEST-419-06"
    save_student_draft(sid, {"student_id": sid, "title": "Rejected Sub Test", "references": "10.1016/j.cell.retracted"})
    with unittest_mock_meta("10.1016/j.cell.retracted", True):
        resp = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
        save_res = save_student_draft(sid, {"student_id": sid, "title": "Post Rejection Edit"})
        after = get_student_draft(sid)
        record("6. Save after rejection works cleanly", resp.status_code == 400 and save_res["success"] and after["title"] == "Post Rejection Edit", f"reject_code={resp.status_code}, new_title={after['title']}")

    # Scenario 7: Repeated submission request after successful lock
    sid = "TEST-419-07"
    save_student_draft(sid, {"student_id": sid, "title": "Locked Draft", "references": "10.1126/science.aar6245"})
    with unittest_mock_meta("10.1126/science.aar6245", False):
        r1 = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
        r2 = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
        record("7. Repeated submission idempotent", r1.status_code == 200 and r2.status_code == 200, f"r1={r1.status_code}, r2={r2.status_code}")

    # Scenario 8: Alternate internal function save (e.g. cohort team sync)
    sid = "TEST-419-08"
    save_student_draft(sid, {"student_id": sid, "title": "Team Member Draft", "references": "10.1126/science.aar6245"})
    snap = get_student_draft(sid)
    save_student_draft(sid, {"student_id": sid, "title": "Synced by Team Workspace"})
    res = toggle_draft_lock(sid, True, expected_version=snap["version"], expected_fingerprint=snap["content_fingerprint"])
    record("8. Team sync write invalidates stale submission", res.get("status") == "draft_changed_retry", f"status={res.get('status')}")

    # Scenario 9: Two separate OS worker processes saving concurrently
    sid = "TEST-419-09"
    save_student_draft(sid, {"student_id": sid, "title": "Process Test Base"})
    p1 = multiprocessing.Process(target=proc_save_worker, args=(1, temp_dir, sid))
    p2 = multiprocessing.Process(target=proc_save_worker, args=(2, temp_dir, sid))
    p1.start()
    p2.start()
    p1.join(timeout=10.0)
    p2.join(timeout=10.0)

    final_d = get_student_draft(sid)
    record("9. Multi-process concurrent saves serial consistency", final_d.get("version") >= 10, f"final_version={final_d.get('version')}")

    # Scenario 10: Multi-process submission race
    sid = "TEST-419-10"
    save_student_draft(sid, {"student_id": sid, "title": "Process Sub Race", "references": "10.1126/science.aar6245"})
    manager = multiprocessing.Manager()
    res_list = manager.list()
    p1 = multiprocessing.Process(target=proc_sub_worker, args=(1, temp_dir, sid, res_list))
    p2 = multiprocessing.Process(target=proc_sub_worker, args=(2, temp_dir, sid, res_list))
    p1.start()
    p2.start()
    p1.join(timeout=10.0)
    p2.join(timeout=10.0)

    codes = [r[1] for r in res_list]
    record("10. Multi-process submission serialization", 200 in codes, f"codes={codes}")

    shutil.rmtree(temp_dir, ignore_errors=True)
    return test_results

if __name__ == "__main__":
    results = run_tests()
    all_ok = all(r["passed"] for r in results)
    print(f"\nAUDIT A TOTAL: {sum(1 for r in results if r['passed'])}/{len(results)} PASSED (all_ok={all_ok})")
