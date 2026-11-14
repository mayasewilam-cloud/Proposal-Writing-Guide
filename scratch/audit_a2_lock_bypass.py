import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

temp_dir = tempfile.TemporaryDirectory()
os.environ["BIOWRITER_DATA_DIR"] = temp_dir.name
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

from app import app
from core.reference_service import _CITATION_STATUS_CACHE
from core.draft_store import save_student_draft, get_student_draft

app.config["TESTING"] = True
app.testing = True
client = app.test_client()

print("=== AUDIT A.2: DRAFT SAVING & SUBMISSION ENFORCEMENT TRACE ===")

# Clear citation cache to simulate cold server start
_CITATION_STATUS_CACHE.clear()

# Scenario 1: Direct save of draft with a retracted DOI (Cold cache, mock offline or unresolvable)
# Suppose the draft was saved without citation_validation or citation_validation was None
draft_id = "TEST-AUDIT-STUDENT-01"
student_data = {
    "title": "Bypass Audit Project",
    "references": "10.1016/j.cell.2020.12.001 (Fabricated Retracted Paper)",
    "citation_validation": None,  # Not validated yet
    "has_retracted_citations": False
}
save_student_draft(draft_id, student_data)

# Now student calls /api/student/lock with cold cache
lock_resp = client.post("/api/student/lock", json={
    "student_id": draft_id,
    "is_locked": True
})

print("Scenario 1 (Cold cache, unvalidated draft lock attempt):")
print("  Status code:", lock_resp.status_code)
print("  Response JSON:", lock_resp.get_json())

# Scenario 2: What if student tampers with save payload:
# What if client sends has_retracted_citations=False in /api/student/save_draft?
_CITATION_STATUS_CACHE["10.1016/j.cell.2020.12.001"] = {
    "success": True,
    "is_retracted": True,
    "is_expression_of_concern": False,
    "is_preprint": False,
    "is_corrected": False,
    "title": "Retracted Paper"
}

save_resp2 = client.post("/api/student/save_draft", json={
    "student_id": "TEST-AUDIT-STUDENT-02",
    "student_data": {
        "title": "Tampered Save Project",
        "references": "10.1016/j.cell.2020.12.001",
        "has_retracted_citations": False,
        "citation_validation": {"has_retracted": False}
    }
})

print("\nScenario 2 (Tampered save payload when DOI is in cache):")
print("  Save status code:", save_resp2.status_code)
saved_draft2 = get_student_draft("TEST-AUDIT-STUDENT-02")
print("  Server overwritten has_retracted_citations:", saved_draft2.get("has_retracted_citations"))
print("  Server overwritten val['has_retracted']:", saved_draft2.get("citation_validation", {}).get("has_retracted"))

lock_resp2 = client.post("/api/student/lock", json={
    "student_id": "TEST-AUDIT-STUDENT-02",
    "is_locked": True
})
print("  Lock attempt status code:", lock_resp2.status_code)
print("  Lock attempt JSON:", lock_resp2.get_json())

# Scenario 3: What if draft was saved during CrossRef outage (has_unknown=True), then submitted when CrossRef is back?
# Does /api/student/lock ever perform a network check if val exists?
_CITATION_STATUS_CACHE.clear()
saved_outage_draft = {
    "title": "Outage Draft",
    "references": "10.1016/j.cell.2020.12.001",
    "citation_validation": {
        "total_citations": 1,
        "has_retracted": False,
        "has_unknown": True,
        "retracted_citations": [],
        "references": [{"doi": "10.1016/j.cell.2020.12.001", "status_type": "unknown"}]
    },
    "has_retracted_citations": False
}
save_student_draft("TEST-AUDIT-STUDENT-03", saved_outage_draft)

# Pre-seed cache to simulate CrossRef being back online and knowing it's retracted
_CITATION_STATUS_CACHE["10.1016/j.cell.2020.12.001"] = {
    "success": True,
    "is_retracted": True,
    "is_expression_of_concern": False
}

lock_resp3 = client.post("/api/student/lock", json={
    "student_id": "TEST-AUDIT-STUDENT-03",
    "is_locked": True
})

print("\nScenario 3 (Draft saved during outage with has_unknown=True, submitted after cache updated):")
print("  Lock attempt status code:", lock_resp3.status_code)
print("  Lock attempt JSON:", lock_resp3.get_json())

temp_dir.cleanup()
