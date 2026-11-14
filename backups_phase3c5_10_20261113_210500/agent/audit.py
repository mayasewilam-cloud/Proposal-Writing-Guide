"""
Append-Only Event Ledger & Audit Logger for the Trusted Research Workflow Agent.
Maintains a tamper-evident, chronologically chained JSONL history of all
agent observations, requirement checks, state transitions, and human decisions.
"""

import os
import json
import hashlib
import datetime
import uuid
import threading
from typing import List, Dict, Any, Optional

_AUDIT_LOCK = threading.Lock()


def get_agent_audit_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audit_dir = os.path.join(base_dir, "data", "agent_audit")
    os.makedirs(audit_dir, exist_ok=True)
    return audit_dir


def record_audit_event(
    project_id: str,
    event_type: str,
    actor: str,  # agent | human | system
    actor_id: str,
    action: str,
    workflow_state: str,
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
    evidence_reference: str = "",
    uncertainty_status: str = "none",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Appends a new audit event record to data/agent_audit/{project_id}.jsonl.
    Chains the SHA-256 hash of the preceding line to detect any retroactive tampering.
    """
    audit_dir = get_agent_audit_dir()
    log_file = os.path.join(audit_dir, f"{project_id}.jsonl")

    with _AUDIT_LOCK:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        prev_hash = "GENESIS_BLOCK"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        last_line = lines[-1]
                        prev_hash = hashlib.sha256(last_line.encode("utf-8")).hexdigest()
            except Exception:
                prev_hash = "UNKNOWN_PREV"

        event_record = {
            "event_id": str(uuid.uuid4())[:8],
            "timestamp": now_iso,
            "project_id": project_id,
            "event_type": event_type,
            "actor": actor,
            "actor_id": actor_id,
            "action": action,
            "workflow_state": workflow_state,
            "previous_state": previous_state,
            "new_state": new_state,
            "evidence_reference": evidence_reference,
            "uncertainty_status": uncertainty_status,
            "details": details or {},
            "prev_hash": prev_hash
        }

        # Append to JSONL file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_record) + "\n")

    return event_record


def get_audit_history(project_id: str) -> List[Dict[str, Any]]:
    """Returns chronological list of all audit records for a project."""
    log_file = os.path.join(get_agent_audit_dir(), f"{project_id}.jsonl")
    if not os.path.exists(log_file):
        return []

    history = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                try:
                    record = json.loads(stripped)
                    record["event_hash"] = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
                    history.append(record)
                except Exception:
                    pass
    return history


def verify_audit_integrity(project_id: str) -> Dict[str, Any]:
    """
    Verifies that the audit log hash-chain is intact and has not been altered.
    """
    log_file = os.path.join(get_agent_audit_dir(), f"{project_id}.jsonl")
    if not os.path.exists(log_file):
        return {"valid": True, "event_count": 0, "message": "No events recorded."}

    lines = []
    with open(log_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    if not lines:
        return {"valid": True, "event_count": 0, "message": "Log file is empty."}

    for idx in range(1, len(lines)):
        current_event = json.loads(lines[idx])
        expected_prev_hash = hashlib.sha256(lines[idx - 1].encode("utf-8")).hexdigest()
        if current_event.get("prev_hash") != expected_prev_hash:
            return {
                "valid": False,
                "event_count": len(lines),
                "corrupted_index": idx,
                "message": f"Tampering detected at event index {idx}."
            }

    return {
        "valid": True,
        "event_count": len(lines),
        "message": "Audit chain integrity verified. All event hashes match."
    }
