import os
import re

path = 'upload/core/draft_store.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

imports_pattern = 'import os\nimport re\nimport json\nimport datetime\nfrom typing import Dict, Any, List, Optional'
new_imports = '''import os
import re
import json
import datetime
import hashlib
import threading
import time
import contextlib
from typing import Dict, Any, List, Optional

try:
    import msvcrt
    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

_draft_thread_locks: Dict[str, threading.RLock] = {}
_draft_global_lock = threading.Lock()
_process_draft_depths: Dict[str, int] = {}
_process_draft_files: Dict[str, Any] = {}


def _get_draft_thread_lock(clean_id: str) -> threading.RLock:
    with _draft_global_lock:
        if clean_id not in _draft_thread_locks:
            _draft_thread_locks[clean_id] = threading.RLock()
        return _draft_thread_locks[clean_id]


@contextlib.contextmanager
def draft_store_lock(student_id: str, timeout: float = 15.0):
    """
    Cross-process and reentrant thread exclusive lock for a specific student draft.
    Serializes concurrent saves and submissions for the same student draft without
    blocking other students or holding locks during network requests.
    """
    clean_id = sanitize_student_id(student_id)
    thread_lock = _get_draft_thread_lock(clean_id)
    with thread_lock:
        depth = _process_draft_depths.get(clean_id, 0)
        if depth == 0:
            target_dir = get_drafts_dir()
            os.makedirs(target_dir, exist_ok=True)
            lock_path = os.path.join(target_dir, f"{clean_id}.lock")
            if not os.path.exists(lock_path):
                try:
                    with open(lock_path, "wb") as f_init:
                        f_init.write(b"\\x00")
                except Exception:
                    pass
            start = time.time()
            f = open(lock_path, "r+b")
            acquired = False
            while time.time() - start < timeout:
                try:
                    if _HAS_MSVCRT:
                        f.seek(0)
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    elif _HAS_FCNTL:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    else:
                        acquired = True
                        break
                except (OSError, IOError):
                    time.sleep(0.02)
            if not acquired:
                f.close()
                raise TimeoutError(f"Could not acquire draft store lock for '{clean_id}' within {timeout}s")
            _process_draft_files[clean_id] = f
            _process_draft_depths[clean_id] = 1
            try:
                yield
            finally:
                _process_draft_depths[clean_id] = 0
                f_to_close = _process_draft_files.pop(clean_id, None)
                if f_to_close:
                    try:
                        if _HAS_MSVCRT:
                            f_to_close.seek(0)
                            msvcrt.locking(f_to_close.fileno(), msvcrt.LK_UNLCK, 1)
                        elif _HAS_FCNTL:
                            fcntl.flock(f_to_close.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                    try:
                        f_to_close.close()
                    except Exception:
                        pass
        else:
            _process_draft_depths[clean_id] = depth + 1
            try:
                yield
            finally:
                _process_draft_depths[clean_id] -= 1


def compute_draft_fingerprint(data: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 fingerprint over student-editable draft contents."""
    content_fields = {
        "title": str(data.get("title", "")),
        "abstract": str(data.get("abstract", "")),
        "methodology": str(data.get("methodology", "")),
        "references": str(data.get("references", "")),
        "references_text": str(data.get("references_text", "")),
        "bibliography": str(data.get("bibliography", "")),
        "chassis": str(data.get("chassis", "")),
        "system": str(data.get("system", "")),
        "tool": str(data.get("tool", "")),
        "query": str(data.get("query", "")),
        "target": str(data.get("target", "")),
        "matrix": data.get("matrix", {}),
        "funnel": data.get("funnel", {}),
        "aims": data.get("aims", {}),
        "impact_data": data.get("impact_data", {}),
        "competitor_data": data.get("competitor_data", {}),
        "swot": data.get("swot", {}),
        "rhev_data": data.get("rhev_data", {}),
    }
    dumped = json.dumps(content_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _atomic_write_draft(clean_id: str, data: Dict[str, Any]) -> None:
    """Writes draft JSON file atomically using a temporary file and os.replace."""
    target_dir = get_drafts_dir()
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    tmp_path = os.path.join(target_dir, f"{clean_id}.tmp.{os.getpid()}_{threading.get_ident()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp_path, filepath)


def _load_draft_raw(clean_id: str) -> Optional[Dict[str, Any]]:
    """Loads raw draft dictionary from disk, assigning baseline version and fingerprint if missing."""
    target_dir = get_drafts_dir()
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    if not os.path.exists(filepath):
        bundled = os.path.join(BASE_DIR, "data", "drafts", f"{clean_id}.json")
        if os.path.exists(bundled):
            filepath = bundled
        else:
            if os.path.exists(target_dir):
                for fname in os.listdir(target_dir):
                    if fname.lower().endswith(".json") and fname[:-5].lower() == clean_id.lower():
                        filepath = os.path.join(target_dir, fname)
                        break
                else:
                    return None
            else:
                return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "version" not in data:
                data["version"] = 1
            if "content_fingerprint" not in data:
                data["content_fingerprint"] = compute_draft_fingerprint(data)
            return data
    except Exception:
        return None'''

assert imports_pattern in content, "imports_pattern not found"
content = content.replace(imports_pattern, new_imports)

# Replace save_student_draft, get_student_draft, toggle_draft_lock
old_block_pattern = r'def save_student_draft\(student_id: str, data: Dict\[str, Any\]\) -> Dict\[str, Any\]:.*?(?=\ndef dispatch_faculty_feedback)'

new_block = '''def save_student_draft(student_id: str, data: Dict[str, Any], expected_version: Optional[int] = None) -> Dict[str, Any]:
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id or data.get("student_id", ""))
    with draft_store_lock(clean_id):
        existing = _load_draft_raw(clean_id)
        if expected_version is not None and existing is not None:
            existing_ver = existing.get("version", 1)
            if existing_ver != expected_version:
                return {
                    "success": False,
                    "error": f"Draft conflict: Current draft version is {existing_ver}, but expected version {expected_version}.",
                    "status": "draft_changed_retry",
                    "conflict": True,
                    "current_version": existing_ver,
                    "expected_version": expected_version
                }

        now_iso = datetime.datetime.now().isoformat()
        now_readable = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")

        data["student_id"] = clean_id
        data["student_name"] = data.get("student_name", "BT_301 Student")
        data["updated_at"] = now_iso
        data["updated_at_readable"] = now_readable

        # SECURITY & ISOLATION: A student client MUST NEVER be able to inject or forge faculty_review.
        if existing and existing.get("faculty_review"):
            data["faculty_review"] = existing["faculty_review"]
        else:
            data["faculty_review"] = None

        # Monotonically increasing version
        current_ver = existing.get("version", 0) if existing else 0
        data["version"] = int(current_ver) + 1
        data["content_fingerprint"] = compute_draft_fingerprint(data)

        summary = calculate_draft_summary(data)
        data["summary"] = summary

        _atomic_write_draft(clean_id, data)

        return {
            "success": True,
            "student_id": clean_id,
            "student_name": data["student_name"],
            "title": data.get("title", "Untitled Proposal"),
            "updated_at": now_readable,
            "version": data["version"],
            "content_fingerprint": data["content_fingerprint"],
            "summary": summary
        }


def get_student_draft(student_id: str) -> Optional[Dict[str, Any]]:
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    with draft_store_lock(clean_id):
        data = _load_draft_raw(clean_id)
        if data:
            data["summary"] = calculate_draft_summary(data)
        return data


def toggle_draft_lock(
    student_id: str,
    is_locked: bool,
    expected_version: Optional[int] = None,
    expected_fingerprint: Optional[str] = None,
    validation_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Toggles or sets the proposal lock for official grading with optimistic concurrency control.
    When expected_version is provided, verifies that draft has not changed since snapshot.
    If draft changed in the interim, returns conflict status 'draft_changed_retry' without modifying draft.
    """
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    with draft_store_lock(clean_id):
        draft = _load_draft_raw(clean_id)
        if not draft:
            return {"success": False, "error": f"Student draft '{clean_id}' not found."}

        current_version = draft.get("version", 1)
        current_fingerprint = draft.get("content_fingerprint") or compute_draft_fingerprint(draft)

        if expected_version is not None and current_version != expected_version:
            return {
                "success": False,
                "error": f"Submission conflict: The proposal draft was modified (version changed from {expected_version} to {current_version}) while citation verification was in progress. Please review the updated draft and retry submission.",
                "status": "draft_changed_retry",
                "conflict": True,
                "current_version": current_version,
                "submitted_version": expected_version
            }

        if expected_fingerprint is not None and current_fingerprint != expected_fingerprint:
            return {
                "success": False,
                "error": "Submission conflict: The proposal draft content was modified while citation verification was in progress. Please review the updated draft and retry submission.",
                "status": "draft_changed_retry",
                "conflict": True,
                "current_version": current_version,
                "submitted_version": expected_version
            }

        if validation_data is not None:
            draft["citation_validation"] = validation_data
            draft["has_retracted_citations"] = False
            draft["has_expression_of_concern_citations"] = bool(validation_data.get("has_expression_of_concern"))

        draft["is_locked_for_grading"] = bool(is_locked)
        draft["locked_at"] = datetime.datetime.now().strftime("%b %d, %Y - %H:%M") if is_locked else None
        draft["version"] = int(current_version) + 1
        draft["content_fingerprint"] = compute_draft_fingerprint(draft)

        _atomic_write_draft(clean_id, draft)

        return {
            "success": True,
            "student_id": clean_id,
            "is_locked_for_grading": bool(is_locked),
            "version": draft["version"],
            "message": "Proposal successfully locked for faculty grading." if is_locked else "Proposal unlocked for revisions."
        }
'''

m = re.search(old_block_pattern, content, flags=re.DOTALL)
assert m, "old_block_pattern not found in draft_store.py"
content = content[:m.start()] + new_block + content[m.end():]

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Successfully patched draft_store.py with per-draft locking, atomic writes, versioning, and optimistic concurrency!")
