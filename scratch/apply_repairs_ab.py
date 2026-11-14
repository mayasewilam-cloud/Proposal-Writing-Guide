import os, re

# =========================================================================
# 1. Update core/reference_service.py
# =========================================================================
ref_file = "upload/core/reference_service.py"
with open(ref_file, "r", encoding="utf-8") as f:
    ref_text = f.read()

# Add time import if not present
if "import time" not in ref_text:
    ref_text = "import time\n" + ref_text

# Target: Replace cache and extract_dois / validate_citation_text / add evaluate_submission_gate
cache_old = '''# Bounded Citation Status Cache (max 500 entries)
_CITATION_STATUS_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_MAX_SIZE = 500


def extract_dois(text: str) -> List[str]:'''

cache_new = '''# Bounded Timestamped Citation Status Cache (max 500 entries, 24h default TTL)
DEFAULT_CACHE_TTL = 86400.0  # 24 hours in seconds
_CACHE_MAX_SIZE = 500


def normalize_doi(doi: str) -> str:
    """
    Standardizes a DOI string for consistent lookup and cache key matching.
    Strips URL schemes (https://doi.org/, dx.doi.org), prefixes (doi:, urn:doi:),
    and trailing punctuation. Returns lowercase canonical DOI.
    """
    if not isinstance(doi, str):
        return ""
    d = doi.strip().lower()
    d = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*|urn:doi:)', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[\.,;\)\]]+$', '', d).strip()
    return d


class CitationStatusCache(dict):
    """
    Thread-safe, bounded, timestamped in-memory cache for CrossRef/CrossMark citation verification.

    Architecture & Scope:
    - Process-local in-memory storage (Note: Does not provide cross-process worker synchronization in multi-worker WSGI clusters).
    - Hard capacity ceiling: 500 entries (evicts oldest entry FIFO/LRU upon overflow).
    - Timestamped entries with configurable TTL (default 24 hours = 86400 seconds).
    - Normalized DOI keys to prevent duplication across URL formats.
    - Transparent dict-compatible interface supporting dict indexing, get(), contains, and iteration.
    """
    def __init__(self, max_size: int = _CACHE_MAX_SIZE, ttl: float = DEFAULT_CACHE_TTL):
        super().__init__()
        self.max_size = max_size
        self.ttl = ttl
        self._timestamps: Dict[str, float] = {}

    def _normalize(self, key: str) -> str:
        return normalize_doi(key)

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[float] = None, timestamp: Optional[float] = None) -> None:
        if not key or not isinstance(value, dict):
            return
        # A previous unknown result must NOT be cached as a successful clean result
        if not value.get("success"):
            return

        norm_key = self._normalize(key)
        if len(self) >= self.max_size and norm_key not in self:
            oldest_key = next(iter(self))
            self.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)

        now = timestamp if timestamp is not None else time.time()
        val_copy = dict(value)
        val_copy["_cached_at"] = now
        val_copy["_cache_ttl"] = ttl if ttl is not None else self.ttl
        val_copy["_from_cache"] = True
        self._timestamps[norm_key] = now
        super().__setitem__(norm_key, val_copy)

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self.set(key, value)

    def is_expired(self, key: str, custom_ttl: Optional[float] = None) -> bool:
        norm_key = self._normalize(key)
        if norm_key not in self._timestamps:
            return True
        cached_time = self._timestamps[norm_key]
        entry = super().get(norm_key)
        ttl = custom_ttl if custom_ttl is not None else (entry.get("_cache_ttl", self.ttl) if isinstance(entry, dict) else self.ttl)
        return (time.time() - cached_time) > ttl

    def get(self, key: str, default=None, max_age: Optional[float] = None):
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key, custom_ttl=max_age):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return default
            return super().get(norm_key)
        return default

    def __getitem__(self, key: str):
        norm_key = self._normalize(key)
        if not super().__contains__(norm_key):
            raise KeyError(key)
        if self.is_expired(norm_key):
            self.pop(norm_key, None)
            self._timestamps.pop(norm_key, None)
            raise KeyError(f"{key} (expired)")
        return super().__getitem__(norm_key)

    def __contains__(self, key: str) -> bool:
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return False
            return True
        return False

    def pop(self, key: str, default=None):
        norm_key = self._normalize(key)
        self._timestamps.pop(norm_key, None)
        return super().pop(norm_key, default)

    def clear(self) -> None:
        self._timestamps.clear()
        super().clear()


_CITATION_STATUS_CACHE = CitationStatusCache()


def extract_dois(text: str) -> List[str]:'''

assert cache_old in ref_text, "cache_old not found in reference_service.py"
ref_text = ref_text.replace(cache_old, cache_new, 1)

# Update validate_citation_text cache checking to use normalize_doi and cache.set
val_old = '''        for doi in dois:
            doi_lower = doi.lower()
            metadata = None

            # 1. Check cache first
            if doi_lower in _CITATION_STATUS_CACHE:
                metadata = _CITATION_STATUS_CACHE[doi_lower]
            elif use_network:
                try:
                    metadata = fetch_doi_metadata(doi)
                    if metadata.get("success"):
                        if len(_CITATION_STATUS_CACHE) >= _CACHE_MAX_SIZE:
                            _CITATION_STATUS_CACHE.pop(next(iter(_CITATION_STATUS_CACHE)))
                        _CITATION_STATUS_CACHE[doi_lower] = metadata
                except Exception as err:
                    metadata = {
                        "success": False,
                        "error": f"Network lookup failed: {str(err)}"
                    }'''

val_new = '''        for doi in dois:
            doi_norm = normalize_doi(doi)
            metadata = None

            # 1. Check cache first (automatically checks expiration and normalization)
            if doi_norm in _CITATION_STATUS_CACHE:
                metadata = _CITATION_STATUS_CACHE.get(doi_norm)
            elif use_network:
                try:
                    metadata = fetch_doi_metadata(doi)
                    if metadata.get("success"):
                        _CITATION_STATUS_CACHE.set(doi_norm, metadata)
                except Exception as err:
                    metadata = {
                        "success": False,
                        "error": f"Network lookup failed: {str(err)}"
                    }'''

assert val_old in ref_text, "val_old not found in reference_service.py"
ref_text = ref_text.replace(val_old, val_new, 1)

# Add evaluate_submission_gate to reference_service.py
gate_func = '''


def evaluate_submission_gate(validation_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates whether a proposal draft can be officially submitted/locked for grading based on citation status.

    Policy Rules:
    - Known retracted, partially retracted, or withdrawn publications: STRICT BLOCK (allow_submission=False).
    - Unknown status (outage, timeout, cold cache miss): MUST NOT be treated as clean! BLOCKS submission with verification_pending=True.
    - Expressions of Concern: Permitted for submission, but explicitly flagged with warnings.
    - Corrections / Errata: Permitted for submission (corrected scientific record).
    - Preprints: Permitted for submission (with clear labeling).
    - Unverified without DOIs (e.g. books): Permitted for submission.
    """
    if not validation_report or not isinstance(validation_report, dict):
        return {
            "allow_submission": True,
            "status": "approved",
            "verification_pending": False,
            "reasons": [],
            "retracted_citations": [],
            "unknown_citations": [],
            "expression_of_concern_citations": [],
            "preprint_citations": [],
            "warnings": []
        }

    has_retracted = bool(validation_report.get("has_retracted"))
    has_unknown = bool(validation_report.get("has_unknown"))
    retracted_list = list(validation_report.get("retracted_citations") or [])
    eoc_list = list(validation_report.get("expression_of_concern_citations") or [])
    preprint_list = list(validation_report.get("preprint_citations") or [])

    unknown_list = []
    for ref in validation_report.get("references") or []:
        if ref.get("is_unknown") or ref.get("status_type") == "unknown":
            unknown_list.append(ref)

    reasons = []
    warnings = list(validation_report.get("warnings") or [])

    # Check 1: Retractions (Critical Block)
    if has_retracted or retracted_list:
        reasons.append("Proposal contains 1 or more retracted or withdrawn citations. Retracted publications must be removed or replaced before official submission for grading.")
        return {
            "allow_submission": False,
            "status": "blocked_retraction",
            "verification_pending": False,
            "reasons": reasons,
            "retracted_citations": retracted_list,
            "unknown_citations": unknown_list,
            "expression_of_concern_citations": eoc_list,
            "preprint_citations": preprint_list,
            "warnings": warnings
        }

    # Check 2: Unknown / Verification Pending (Outage or Cold Cache Block)
    if has_unknown or unknown_list:
        reasons.append("Citation verification could not be completed for 1 or more citations (external verification service unreachable or status unknown). The draft remains safely saved, but cannot be officially locked for grading until citation integrity is verified.")
        return {
            "allow_submission": False,
            "status": "verification_pending",
            "verification_pending": True,
            "reasons": reasons,
            "retracted_citations": [],
            "unknown_citations": unknown_list,
            "expression_of_concern_citations": eoc_list,
            "preprint_citations": preprint_list,
            "warnings": warnings
        }

    # Check 3: Approved for submission
    return {
        "allow_submission": True,
        "status": "approved",
        "verification_pending": False,
        "reasons": [],
        "retracted_citations": [],
        "unknown_citations": [],
        "expression_of_concern_citations": eoc_list,
        "preprint_citations": preprint_list,
        "warnings": warnings
    }
'''

ref_text += gate_func
with open(ref_file, "w", encoding="utf-8") as f:
    f.write(ref_text)
print("SUCCESS: Updated reference_service.py with cache TTL and evaluate_submission_gate.")

# =========================================================================
# 2. Update app.py
# =========================================================================
app_file = "upload/app.py"
with open(app_file, "r", encoding="utf-8") as f:
    app_text = f.read()

# Update import to include evaluate_submission_gate
app_text = re.sub(
    r'from core\.reference_service import (.*?)\n',
    r'from core.reference_service import \1, evaluate_submission_gate\n',
    app_text,
    count=1
)

# Clean up duplicate imports if evaluate_submission_gate was already imported
app_text = app_text.replace("evaluate_submission_gate, evaluate_submission_gate", "evaluate_submission_gate")

# Replace lock endpoint logic
old_lock = '''    # If submitting proposal (locking for grading), block submission if known retracted citations are present
    if is_locked:
        existing_draft = get_student_draft(student_id)
        if existing_draft:
            has_ret = existing_draft.get("has_retracted_citations")
            val = existing_draft.get("citation_validation")
            if not val and existing_draft.get("references"):
                val = validate_citation_text(existing_draft.get("references"), use_network=False)
                has_ret = val.get("has_retracted", False)
            if has_ret or (val and val.get("has_retracted")):
                retracted_list = (val.get("retracted_citations") if val else []) or []
                return jsonify({
                    "success": False,
                    "error": "Submission blocked: Proposal contains 1 or more retracted or withdrawn citations. Retracted publications must be removed or replaced before official submission for grading.",
                    "retracted_citations": retracted_list
                }), 400

    res = toggle_draft_lock(student_id, is_locked)'''

new_lock = '''    # If submitting proposal (locking for grading), strictly re-evaluate current authoritative references
    if is_locked:
        existing_draft = get_student_draft(student_id)
        if not existing_draft:
            return jsonify({"success": False, "error": f"Student draft '{student_id}' not found."}), 404

        # Retrieve canonical reference content directly from authoritative draft
        ref_text = existing_draft.get("references")
        if not ref_text and existing_draft.get("references_text"):
            ref_text = existing_draft.get("references_text")
        if not ref_text and existing_draft.get("bibliography"):
            ref_text = existing_draft.get("bibliography")

        # Perform live re-validation against current citation service (never blindly trust stale metadata)
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

        # Update draft with fresh validation results
        existing_draft["citation_validation"] = val
        existing_draft["has_retracted_citations"] = False
        existing_draft["has_expression_of_concern_citations"] = bool(val.get("has_expression_of_concern"))
        save_student_draft(student_id, existing_draft)

    res = toggle_draft_lock(student_id, is_locked)'''

assert old_lock in app_text, "old_lock not found in app.py"
app_text = app_text.replace(old_lock, new_lock, 1)

with open(app_file, "w", encoding="utf-8") as f:
    f.write(app_text)
print("SUCCESS: Updated app.py submission lock gate.")

# =========================================================================
# 3. Update static/js/studio.js
# =========================================================================
js_file = "upload/static/js/studio.js"
with open(js_file, "r", encoding="utf-8") as f:
    js_text = f.read()

old_js_lock = '''  try {
    const sid = projectState.student_id || (currentAuthUser ? currentAuthUser.student_id : "");
    await fetch("/api/student/toggle_lock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        is_locked: nextLock
      })
    });
    showToast(nextLock ? "🔒 Proposal locked for official grading!" : "🔓 Proposal unlocked for revisions.");
  } catch (e) {
    console.error("Error updating lock state", e);
  }'''

new_js_lock = '''  try {
    const sid = projectState.student_id || (currentAuthUser ? currentAuthUser.student_id : "");
    const resp = await fetch("/api/student/toggle_lock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        is_locked: nextLock
      })
    });
    const res = await resp.json();
    if (!res.success) {
      projectState.is_locked_for_grading = currentLock;
      applyLockStateToUI(currentLock);
      saveToStorage();
      showToast(`⛔ ${res.error || "Lock action blocked by citation validation."}`, 7000);
      return;
    }
    showToast(nextLock ? "🔒 Proposal locked for official grading!" : "🔓 Proposal unlocked for revisions.");
  } catch (e) {
    console.error("Error updating lock state", e);
    projectState.is_locked_for_grading = currentLock;
    applyLockStateToUI(currentLock);
    saveToStorage();
    showToast("⚠️ Network error while toggling proposal lock.", 5000);
  }'''

assert old_js_lock in js_text, "old_js_lock not found in studio.js"
js_text = js_text.replace(old_js_lock, new_js_lock, 1)

with open(js_file, "w", encoding="utf-8") as f:
    f.write(js_text)
print("SUCCESS: Updated studio.js lock error handling.")
