import os, sys, unittest, tempfile, shutil, json
from unittest.mock import patch, MagicMock

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

temp_dir = tempfile.mkdtemp(prefix="biowriter_audit_a2_")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir

from app import app
from core.reference_service import _CITATION_STATUS_CACHE, CitationStatusCache
from core.draft_store import save_student_draft, get_student_draft, toggle_draft_lock

app.config["TESTING"] = True
client = app.test_client()

results = []

def run_scenario(sid, name, initial_refs, initial_val, lock_payload, mock_meta=None, session_user=None):
    _CITATION_STATUS_CACHE.clear()
    
    # Save draft
    save_student_draft(sid, {
        "title": f"Draft {sid}",
        "references": initial_refs,
        "citation_validation": initial_val,
        "is_locked_for_grading": False
    })
    
    # Setup session
    if session_user:
        with client.session_transaction() as sess:
            sess["student_id"] = session_user
            sess["role"] = "student"
    else:
        with client.session_transaction() as sess:
            sess.clear()
            
    # Execute request
    if mock_meta is not None:
        with patch("core.reference_service.fetch_doi_metadata") as mock_fetch:
            mock_fetch.side_effect = mock_meta if callable(mock_meta) else lambda doi: mock_meta
            resp = client.post("/api/student/lock", json=lock_payload)
    else:
        resp = client.post("/api/student/lock", json=lock_payload)
        
    status_code = resp.status_code
    body = resp.get_json() or {}
    
    # Check post-state
    post_draft = get_student_draft(sid)
    final_lock = post_draft.get("is_locked_for_grading", False) if post_draft else None
    post_refs = post_draft.get("references") if post_draft else None
    refs_unchanged = (post_refs == initial_refs)
    
    results.append({
        "scenario": name,
        "status_code": status_code,
        "success": body.get("success"),
        "error_or_status": body.get("status") or body.get("error", "")[:60],
        "final_lock": final_lock,
        "refs_unchanged": refs_unchanged
    })

# --- 20 SCENARIOS ---

# 1. Clean references with fresh successful verification
_CITATION_STATUS_CACHE["10.1038/s41586-clean"] = {"success": True, "doi": "10.1038/s41586-clean", "is_retracted": False}
run_scenario("TEST-01", "1. Clean fresh verification", "10.1038/s41586-clean", None, {"student_id": "TEST-01", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1038/s41586-clean", "is_retracted": False})

# 2. Known retracted DOI
run_scenario("TEST-02", "2. Known retracted DOI", "10.1016/j.cell.retracted", None, {"student_id": "TEST-02", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1016/j.cell.retracted", "is_retracted": True, "status_type": "retracted"})

# 3. Withdrawn publication
run_scenario("TEST-03", "3. Withdrawn publication", "10.1016/j.cell.withdrawn", None, {"student_id": "TEST-03", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1016/j.cell.withdrawn", "is_retracted": True, "status_type": "retracted", "retraction_notice": "Withdrawn by publisher"})

# 4. Expression of concern
run_scenario("TEST-04", "4. Expression of concern", "10.1126/science.concern", None, {"student_id": "TEST-04", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1126/science.concern", "is_retracted": False, "is_expression_of_concern": True, "status_type": "expression_of_concern"})

# 5. Corrected publication
run_scenario("TEST-05", "5. Corrected publication", "10.1038/s41586-corrected", None, {"student_id": "TEST-05", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1038/s41586-corrected", "is_retracted": False, "is_corrected": True, "status_type": "corrected"})

# 6. Preprint
run_scenario("TEST-06", "6. Preprint record", "10.1101/2023.01.01.522415", None, {"student_id": "TEST-06", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1101/2023.01.01.522415", "is_retracted": False, "is_preprint": True, "status_type": "preprint"})

# 7. DOI that cannot be resolved (404)
run_scenario("TEST-07", "7. Unresolved DOI (404)", "10.1000/nonexistent", None, {"student_id": "TEST-07", "is_locked": True},
             mock_meta={"success": False, "error": "CrossRef returned status 404"})

# 8. Network timeout
run_scenario("TEST-08", "8. Network timeout", "10.1000/timeout", None, {"student_id": "TEST-08", "is_locked": True},
             mock_meta={"success": False, "error": "Connection error: HTTPSConnectionPool timeout"})

# 9. HTTP 429 response (Rate limit)
run_scenario("TEST-09", "9. HTTP 429 Rate limit", "10.1000/ratelimit", None, {"student_id": "TEST-09", "is_locked": True},
             mock_meta={"success": False, "error": "CrossRef returned status 429"})

# 10. HTTP 5xx response (Server error)
run_scenario("TEST-10", "10. HTTP 500 Server error", "10.1000/servererr", None, {"student_id": "TEST-10", "is_locked": True},
             mock_meta={"success": False, "error": "CrossRef returned status 500"})

# 11. Malformed DOI (no valid DOI syntax in text)
run_scenario("TEST-11", "11. Malformed / Non-DOI text", "Smith et al. 2024. No DOI here.", None, {"student_id": "TEST-11", "is_locked": True})

# 12. Cold cache with clean DOI
run_scenario("TEST-12", "12. Cold cache clean DOI", "10.1038/cold-clean", None, {"student_id": "TEST-12", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1038/cold-clean", "is_retracted": False})

# 13. Expired previously clean cache entry
def test_13_expired():
    _CITATION_STATUS_CACHE.set("10.1038/expired-clean", {"success": True, "is_retracted": False}, ttl=0.01)
    import time
    time.sleep(0.02)
    # Revalidation finds it retracted
    run_scenario("TEST-13", "13. Expired cache retracted reval", "10.1038/expired-clean", None, {"student_id": "TEST-13", "is_locked": True},
                 mock_meta={"success": True, "doi": "10.1038/expired-clean", "is_retracted": True, "status_type": "retracted"})
test_13_expired()

# 14. Forged client payload claiming retracted DOI is clean
run_scenario("TEST-14", "14. Forged client payload", "10.1016/j.cell.retracted-forge", None,
             {"student_id": "TEST-14", "is_locked": True, "has_retracted_citations": False, "citation_validation": {"has_retracted": False}},
             mock_meta={"success": True, "doi": "10.1016/j.cell.retracted-forge", "is_retracted": True, "status_type": "retracted"})

# 15. Stale clean metadata with changed references
run_scenario("TEST-15", "15. Stale clean metadata changed refs", "10.1016/j.cell.retracted-new",
             {"has_retracted": False, "references": []},
             {"student_id": "TEST-15", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1016/j.cell.retracted-new", "is_retracted": True, "status_type": "retracted"})

# 16. Draft with missing validation metadata
run_scenario("TEST-16", "16. Missing validation metadata", "10.1038/s41586-missing-val", None, {"student_id": "TEST-16", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1038/s41586-missing-val", "is_retracted": False})

# 17. Direct API submission bypassing frontend
run_scenario("TEST-17", "17. Direct API submission", "10.1038/s41586-direct", None, {"student_id": "TEST-17", "is_locked": True},
             mock_meta={"success": True, "doi": "10.1038/s41586-direct", "is_retracted": False})

# 18. Request attempting to lock draft belonging to another user
run_scenario("TEST-18", "18. Lock another student draft", "10.1038/clean", None, {"student_id": "TEST-18", "is_locked": True},
             mock_meta={"success": True, "is_retracted": False}, session_user="TEST-ATTACKER")

# 19. Request attempting to unlock an already locked draft
save_student_draft("TEST-19", {"title": "Draft 19", "references": "10.1016/retracted", "is_locked_for_grading": True})
toggle_draft_lock("TEST-19", True)
run_scenario("TEST-19", "19. Unlock already locked draft", "10.1016/retracted", None, {"student_id": "TEST-19", "is_locked": False})

# 20. Unexpected or malformed lock-state value
run_scenario("TEST-20", "20. Malformed lock-state value", "10.1038/s41586-clean20", None, {"student_id": "TEST-20", "is_locked": "INVALID_VALUE"},
             mock_meta={"success": True, "doi": "10.1038/s41586-clean20", "is_retracted": False})

shutil.rmtree(temp_dir, ignore_errors=True)

print(f"{'#':<3} | {'Scenario':<38} | {'HTTP':<5} | {'Gate Outcome':<24} | {'Locked?':<8} | {'Refs Untouched?'}")
print("-" * 95)
for i, r in enumerate(results, 1):
    locked_str = "LOCKED" if r['final_lock'] else "UNLOCKED"
    refs_str = "YES" if r['refs_unchanged'] else "MODIFIED"
    print(f"{i:<3} | {r['scenario']:<38} | {r['status_code']:<5} | {str(r['error_or_status'])[:24]:<24} | {locked_str:<8} | {refs_str}")
