import sys
import os
import json
import tempfile
import shutil

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

temp_dir = tempfile.mkdtemp(prefix="biowriter_audit_419_lock_api_")
os.environ["BIOWRITER_DATA_DIR"] = temp_dir
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

from app import app
app.config["TESTING"] = True

from core.draft_store import save_student_draft, get_student_draft
from core.reference_service import CitationStatusCache

def run_api_audit():
    client = app.test_client()
    results = []

    def record(name, passed, details):
        results.append({"name": name, "passed": passed, "details": details})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} - {details}")

    sid = "TEST-API-AUDIT-SID"
    save_student_draft(sid, {
        "student_id": sid,
        "title": "API Audit Draft",
        "references": "Clean paper. DOI: 10.1126/science.aar6245"
    })

    # Cache clean lookup so we don't hit external network
    cache = CitationStatusCache()
    cache.set("10.1126/science.aar6245", {
        "success": True,
        "doi": "10.1126/science.aar6245",
        "is_retracted": False,
        "is_expression_of_concern": False
    })

    # 1. Explicit JSON boolean true
    r_true = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
    d1 = get_student_draft(sid)
    record("1. Explicit boolean true", r_true.status_code == 200 and d1.get("is_locked_for_grading") is True, f"HTTP {r_true.status_code}, locked={d1.get('is_locked_for_grading')}")

    # 2. Explicit JSON boolean false (unlock)
    r_false = client.post("/api/student/lock", json={"student_id": sid, "is_locked": False})
    d2 = get_student_draft(sid)
    record("2. Explicit boolean false (unlock)", r_false.status_code == 200 and d2.get("is_locked_for_grading") is False, f"HTTP {r_false.status_code}, locked={d2.get('is_locked_for_grading')}")

    # 3. Legacy parameter 'lock': True
    r_leg_t = client.post("/api/student/toggle_lock", json={"student_id": sid, "lock": True})
    d3 = get_student_draft(sid)
    record("3. Legacy 'lock': True", r_leg_t.status_code == 200 and d3.get("is_locked_for_grading") is True, f"HTTP {r_leg_t.status_code}, locked={d3.get('is_locked_for_grading')}")

    # 4. Legacy parameter 'lock': False
    r_leg_f = client.post("/api/student/toggle_lock", json={"student_id": sid, "lock": False})
    d4 = get_student_draft(sid)
    record("4. Legacy 'lock': False", r_leg_f.status_code == 200 and d4.get("is_locked_for_grading") is False, f"HTTP {r_leg_f.status_code}, locked={d4.get('is_locked_for_grading')}")

    # 5. String values: 'true', 'false', 'INVALID', '0', '1' -> all 400
    str_vals = ["true", "false", "INVALID", "0", "1"]
    all_str_rejected = True
    for sv in str_vals:
        res = client.post("/api/student/lock", json={"student_id": sid, "is_locked": sv})
        if res.status_code != 400 or res.get_json().get("status") != "invalid_lock_parameter":
            all_str_rejected = False
    record("5. String values rejected (400)", all_str_rejected, f"Tested {str_vals}")

    # 6. Numeric values: 0, 1 -> all 400
    num_vals = [0, 1, -1, 100]
    all_num_rejected = True
    for nv in num_vals:
        res = client.post("/api/student/lock", json={"student_id": sid, "is_locked": nv})
        if res.status_code != 400 or res.get_json().get("status") != "invalid_lock_parameter":
            all_num_rejected = False
    record("6. Numeric values rejected (400)", all_num_rejected, f"Tested {num_vals}")

    # 7. Null value -> 400
    r_null = client.post("/api/student/lock", json={"student_id": sid, "is_locked": None})
    record("7. Null value rejected (400)", r_null.status_code == 400 and r_null.get_json().get("status") == "invalid_lock_parameter", f"HTTP {r_null.status_code}")

    # 8. Empty array and object -> 400
    r_arr = client.post("/api/student/lock", json={"student_id": sid, "is_locked": []})
    r_obj = client.post("/api/student/lock", json={"student_id": sid, "is_locked": {}})
    record("8. Array and object rejected (400)", r_arr.status_code == 400 and r_obj.status_code == 400, f"arr={r_arr.status_code}, obj={r_obj.status_code}")

    # 9. Missing lock parameters -> 400
    r_miss = client.post("/api/student/lock", json={"student_id": sid})
    record("9. Missing lock parameter rejected (400)", r_miss.status_code == 400 and r_miss.get_json().get("status") == "invalid_lock_parameter", f"HTTP {r_miss.status_code}")

    # 10. Both is_locked and lock supplied together with matching values
    r_both_match = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True, "lock": True})
    record("10. Both supplied with matching values", r_both_match.status_code == 200, f"HTTP {r_both_match.status_code}")

    # 11. Both supplied with conflicting values (e.g. is_locked=False, lock=True)
    # The contract prioritizes is_locked if present
    r_both_conf = client.post("/api/student/lock", json={"student_id": sid, "is_locked": False, "lock": True})
    d_conf = get_student_draft(sid)
    record("11. Conflicting keys: is_locked prioritized", r_both_conf.status_code == 200 and d_conf.get("is_locked_for_grading") is False, f"locked={d_conf.get('is_locked_for_grading')} (is_locked=False took precedence)")

    # 12. Unauthorized and cross-student request
    with client.session_transaction() as sess:
        sess["student_id"] = "OTHER-STUDENT-ID"
        sess["faculty_authenticated"] = False
    r_unauth = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
    record("12. Cross-student lock blocked (403)", r_unauth.status_code == 403, f"HTTP {r_unauth.status_code}")

    # 13. Repeated requests against already locked draft
    with client.session_transaction() as sess:
        sess.clear()
    client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
    r_rep = client.post("/api/student/lock", json={"student_id": sid, "is_locked": True})
    record("13. Repeated lock against already locked draft", r_rep.status_code == 200, f"HTTP {r_rep.status_code}")

    # 14. Confirm invalid requests do not modify stored draft lock state
    client.post("/api/student/lock", json={"student_id": sid, "is_locked": False})
    before_state = get_student_draft(sid).get("is_locked_for_grading")
    client.post("/api/student/lock", json={"student_id": sid, "is_locked": "INVALID_CORRUPT"})
    after_state = get_student_draft(sid).get("is_locked_for_grading")
    record("14. Invalid request leaves state unmodified", before_state == after_state, f"before={before_state}, after={after_state}")

    shutil.rmtree(temp_dir, ignore_errors=True)
    all_ok = all(r["passed"] for r in results)
    print(f"\nAUDIT D TOTAL: {sum(1 for r in results if r['passed'])}/{len(results)} PASSED (all_ok={all_ok})")

if __name__ == "__main__":
    run_api_audit()
