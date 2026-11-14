path = 'upload/tests/test_phase4_1_8_scientific_integrity.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add _CITATION_STATUS_CACHE.clear() to setUp
old_setup = """    def setUp(self):
        self.student_id = "TEST-STU-418-CONC\""""

new_setup = """    def setUp(self):
        from core.reference_service import _CITATION_STATUS_CACHE
        _CITATION_STATUS_CACHE.clear()
        self.student_id = "TEST-STU-418-CONC\""""

assert old_setup in text, "old_setup not found"
text = text.replace(old_setup, new_setup)

# In test_a09, use a specific DOI
old_a09 = """    def test_a09_submission_fails_due_to_unavailable_crossref(self):
        \"\"\"9. Submission validation fails due to unavailable CrossRef -> HTTP 400 verification_pending.\"\"\"
        mock_meta = {
            "success": False,
            "error": "504 Gateway Timeout"
        }"""

new_a09 = """    def test_a09_submission_fails_due_to_unavailable_crossref(self):
        \"\"\"9. Submission validation fails due to unavailable CrossRef -> HTTP 400 verification_pending.\"\"\"
        d = dict(self.draft_data)
        d["references"] = "Unavailable. DOI: 10.1000/timeout-doi"
        save_student_draft(self.student_id, d)
        mock_meta = {
            "success": False,
            "error": "504 Gateway Timeout"
        }"""

assert old_a09 in text, "old_a09 not found"
text = text.replace(old_a09, new_a09)

# In test_c04, use l.lower()
old_c04 = """        self.assertTrue(any("animal cohort" in l or "murine metabolic" in l for l in lims))"""
new_c04 = """        self.assertTrue(any("animal cohort" in l.lower() or "murine metabolic" in l.lower() for l in lims))"""
assert old_c04 in text, "old_c04 not found"
text = text.replace(old_c04, new_c04)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print("Updated test suite successfully!")
