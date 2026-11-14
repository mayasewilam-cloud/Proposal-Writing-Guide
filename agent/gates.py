"""
Human Authorization Gates for the Trusted Research Workflow Agent.
Enforces non-delegable human control over consequential academic,
ethical, and regulatory decisions.
"""

from typing import Dict, Any, Optional
import datetime
from .workflow import WorkflowState, WorkflowError


class UnauthorizedActionError(WorkflowError):
    """Raised when an automated agent or unauthorized role attempts a consequential action."""
    pass


AUTHORIZED_HUMAN_ROLES = [
    "ethics_officer",
    "biosafety_officer",
    "faculty_instructor",
    "committee_chair",
    "course_coordinator"
]


def enforce_human_review_gate(
    project_id: str,
    actor: str,
    role: str,
    reviewer_id: str,
    decision: str,  # approved | revisions_requested | rejected
    notes: str = "",
    conditions: str = ""
) -> Dict[str, Any]:
    """
    Validates and executes a human review decision gate.
    Guarantees that actor='agent' is strictly blocked from issuing approvals.
    """
    # 1. Enforce actor identity
    if actor != "human":
        raise UnauthorizedActionError(
            f"Security Violation: Actor '{actor}' is not authorized to execute review gates. "
            "Only authenticated human officers may sign off on compliance decisions."
        )

    # 2. Enforce human role
    clean_role = (role or "").strip().lower()
    if clean_role not in AUTHORIZED_HUMAN_ROLES:
        raise UnauthorizedActionError(
            f"Role Violation: Role '{clean_role}' is not in authorized human review roles: {AUTHORIZED_HUMAN_ROLES}"
        )

    # 3. Enforce valid decision
    clean_decision = (decision or "").strip().lower()
    if clean_decision not in ["approved", "revisions_requested", "rejected"]:
        raise ValueError(f"Invalid decision: '{clean_decision}'. Must be 'approved', 'revisions_requested', or 'rejected'.")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    decision_record = {
        "project_id": project_id,
        "reviewer_id": reviewer_id or "anonymous_officer",
        "role": clean_role,
        "decision": clean_decision,
        "notes": notes.strip(),
        "conditions": conditions.strip(),
        "recorded_at": now_iso,
        "is_human_signed": True
    }

    # Determine resultant state
    if clean_decision == "approved":
        target_state = WorkflowState.CLEARED_FOR_NEXT_STAGE
    elif clean_decision == "revisions_requested":
        target_state = WorkflowState.RETURNED_FOR_REVISION
    else:
        target_state = WorkflowState.ESCALATED

    return {
        "success": True,
        "decision_record": decision_record,
        "target_state": target_state,
        "message": f"Human review decision '{clean_decision}' recorded by {clean_role} ({reviewer_id})."
    }
