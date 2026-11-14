import re

path = 'upload/app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add compute_draft_fingerprint to core.draft_store import
old_import = '''from core.draft_store import (
    save_student_draft,
    get_student_draft,
    list_student_drafts,
    seed_default_drafts,
    toggle_draft_lock,
    dispatch_faculty_feedback,
    delete_student_draft
)'''

new_import = '''from core.draft_store import (
    save_student_draft,
    get_student_draft,
    list_student_drafts,
    seed_default_drafts,
    toggle_draft_lock,
    dispatch_faculty_feedback,
    delete_student_draft,
    compute_draft_fingerprint
)'''

assert old_import in content, "old_import not found in app.py"
content = content.replace(old_import, new_import)

old_toggle_pattern = r'@app\.route\("/api/student/lock", methods=\["POST"\]\)\n@app\.route\("/api/student/toggle_lock", methods=\["POST"\]\)\ndef api_student_toggle_lock\(\):.*?(?=\n\n@app\.route\("/api/student/drafts")'

new_toggle = '''@app.route("/api/student/lock", methods=["POST"])
@app.route("/api/student/toggle_lock", methods=["POST"])
def api_student_toggle_lock():
    data = request.get_json() or {}
    session_sid = (session.get("student_id") or "").strip()
    is_faculty = bool(session.get("faculty_authenticated") and session.get("role") == "faculty")

    if session_sid and not is_faculty:
        student_id = session_sid
    else:
        student_id = data.get("student_id", "").strip() or session.get("student_id", "") or session.get("guest_draft_id", "")

    if not student_id:
        return jsonify({"success": False, "error": "Student ID required."}), 400
    if not _is_authorized_for_student_draft(student_id, write_access=True):
        return jsonify({"success": False, "error": "Unauthorized: Cannot modify lock state for this draft."}), 403

    # REPAIR D: Strict lock-state input validation.
    # Accept explicit booleans only. Reject arbitrary strings, 'INVALID', null, 0, arrays, objects.
    # Support documented legacy payload parameter 'lock' if 'is_locked' is omitted.
    raw_lock = data.get("is_locked")
    if raw_lock is None and "lock" in data:
        raw_lock = data.get("lock")

    if raw_lock is None or not isinstance(raw_lock, bool):
        return jsonify({
            "success": False,
            "error": "Invalid lock state. Expected an explicit boolean (true or false). Strings, numbers, nulls, arrays, and objects are not permitted.",
            "status": "invalid_lock_parameter"
        }), 400

    is_locked = raw_lock

    # If submitting proposal (locking for grading), strictly re-evaluate current authoritative references
    if is_locked:
        existing_draft = get_student_draft(student_id)
        if not existing_draft:
            return jsonify({"success": False, "error": f"Student draft '{student_id}' not found."}), 404

        # Capture snapshot version and content fingerprint BEFORE network validation
        snapshot_version = existing_draft.get("version", 1)
        snapshot_fingerprint = existing_draft.get("content_fingerprint") or compute_draft_fingerprint(existing_draft)

        # Retrieve canonical reference content directly from authoritative draft snapshot
        ref_text = existing_draft.get("references")
        if not ref_text and existing_draft.get("references_text"):
            ref_text = existing_draft.get("references_text")
        if not ref_text and existing_draft.get("bibliography"):
            ref_text = existing_draft.get("bibliography")

        # Perform live re-validation against current citation service (never hold file lock across network requests)
        val = validate_citation_text(ref_text or "", use_network=True)
        gate = evaluate_submission_gate(val)

        if not gate["allow_submission"]:
            if gate.get("status") == "blocked_retraction":
                return jsonify({
                    "success": False,
                    "error": "Submission blocked: Proposal contains 1 or more retracted or withdrawn citations. Retracted publications must be removed or replaced before official submission for grading.",
                    "status": "blocked_retraction",
                    "retracted_citations": gate.get("retracted_citations", []),
                    "citation_validation": val
                }), 400

            if gate.get("verification_pending"):
                return jsonify({
                    "success": False,
                    "error": "Submission pending: Citation verification could not be completed (external verification service unreachable or status unknown). The draft remains safely saved, but cannot be officially locked for grading until citation integrity is verified.",
                    "status": "verification_pending",
                    "verification_pending": True,
                    "unknown_citations": gate.get("unknown_citations", []),
                    "citation_validation": val
                }), 400

            return jsonify({
                "success": False,
                "error": "Submission blocked: " + "; ".join(gate.get("reasons", ["Citation integrity check failed."])),
                "status": gate.get("status", "blocked"),
                "citation_validation": val
            }), 400

        # REPAIR A: Concurrency-Safe Atomic Commit with Optimistic Concurrency Control
        # Commits validation results and lock state ONLY if draft version and fingerprint match the snapshot
        res = toggle_draft_lock(
            student_id,
            is_locked=True,
            expected_version=snapshot_version,
            expected_fingerprint=snapshot_fingerprint,
            validation_data=val
        )

        if not res.get("success"):
            if res.get("conflict") or res.get("status") == "draft_changed_retry":
                return jsonify(res), 409
            return jsonify(res), 400

        return jsonify(res), 200

    else:
        # Unlocking for revisions
        res = toggle_draft_lock(student_id, is_locked=False)
        if not res.get("success"):
            return jsonify(res), 400
        return jsonify(res), 200'''

m = re.search(old_toggle_pattern, content, flags=re.DOTALL)
assert m, "old_toggle_pattern not found in app.py"
content = content[:m.start()] + new_toggle + content[m.end():]

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Successfully patched app.py with strict input validation and concurrency-safe submission!")
