"""
Persistent Workflow State Machine for the Trusted Research Workflow Agent.
Governs legal state transitions, next action determination, and enforces
strict transition invariants across the multi-stage research project lifecycle.
"""

import os
import json
import datetime
from typing import Dict, Any, Tuple, Optional, List
from .models import WorkflowState


VALID_TRANSITIONS = {
    WorkflowState.DRAFT: [WorkflowState.CONTEXT_ANALYSIS],
    WorkflowState.CONTEXT_ANALYSIS: [WorkflowState.REQUIREMENT_CHECK, WorkflowState.ESCALATED],
    WorkflowState.REQUIREMENT_CHECK: [
        WorkflowState.NEEDS_CLARIFICATION,
        WorkflowState.READY_FOR_ETHICS_HANDOFF,
        WorkflowState.ESCALATED
    ],
    WorkflowState.NEEDS_CLARIFICATION: [
        WorkflowState.REQUIREMENT_CHECK,
        WorkflowState.CONTEXT_ANALYSIS,
        WorkflowState.ESCALATED,
        WorkflowState.RETURNED_FOR_REVISION
    ],
    WorkflowState.READY_FOR_ETHICS_HANDOFF: [
        WorkflowState.ETHICS_REVIEW_PENDING,
        WorkflowState.MOCK_HANDOFF_COMPLETED,
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.NEEDS_CLARIFICATION,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.ETHICS_REVIEW_PENDING: [
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.RETURNED_FOR_REVISION,
        WorkflowState.ESCALATED,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.MOCK_HANDOFF_COMPLETED: [
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.RETURNED_FOR_REVISION,
        WorkflowState.ESCALATED,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.HUMAN_REVIEW: [
        WorkflowState.CLEARED_FOR_NEXT_STAGE,
        WorkflowState.RETURNED_FOR_REVISION,
        WorkflowState.ESCALATED,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.RETURNED_FOR_REVISION: [
        WorkflowState.DRAFT,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.ESCALATED: [
        WorkflowState.HUMAN_REVIEW,
        WorkflowState.RETURNED_FOR_REVISION,
        WorkflowState.CONTEXT_ANALYSIS
    ],
    WorkflowState.CLEARED_FOR_NEXT_STAGE: [
        WorkflowState.CONTEXT_ANALYSIS
    ]
}


class WorkflowError(Exception):
    """Raised when an invalid state transition or unauthorized workflow action is attempted."""
    pass


def get_agent_state_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_dir = os.path.join(base_dir, "data", "agent_state")
    os.makedirs(state_dir, exist_ok=True)
    return state_dir


def load_workflow_state(project_id: str) -> Dict[str, Any]:
    """Loads stored state record or initializes default DRAFT state."""
    state_file = os.path.join(get_agent_state_dir(), f"{project_id}.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Default state record
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "project_id": project_id,
        "current_state": WorkflowState.DRAFT,
        "previous_state": None,
        "last_transition_time": now_iso,
        "pending_clarifications": [],
        "answered_clarifications": [],
        "requirements_summary": [],
        "dossier_generated": False,
        "human_decision": None,
        "is_locked": False
    }


def save_workflow_state(project_id: str, state_data: Dict[str, Any]) -> None:
    """Persists workflow state record to data/agent_state/{project_id}.json."""
    state_file = os.path.join(get_agent_state_dir(), f"{project_id}.json")
    state_data["last_transition_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)


def can_transition(current_state: str, target_state: str) -> bool:
    """Validates whether a transition from current_state to target_state is allowed."""
    allowed = VALID_TRANSITIONS.get(current_state, [])
    return target_state in allowed


def transition_state(
    project_id: str,
    target_state: str,
    actor: str = "agent",
    actor_id: str = "orchestrator",
    reason: str = ""
) -> Tuple[Dict[str, Any], bool]:
    """
    Executes a guarded state transition.
    Enforces that consequential final states (e.g. CLEARED_FOR_NEXT_STAGE)
    CANNOT be initiated by actor='agent'.
    """
    state_data = load_workflow_state(project_id)
    current_state = state_data.get("current_state", WorkflowState.DRAFT)

    # Inviolable Rule: Agent cannot clear its own review or approve ethics
    if target_state == WorkflowState.CLEARED_FOR_NEXT_STAGE and actor == "agent":
        raise WorkflowError(
            "Trust Violation: The automated agent cannot transition project to CLEARED_FOR_NEXT_STAGE. "
            "This state requires authenticated human review authority."
        )

    if not can_transition(current_state, target_state):
        raise WorkflowError(
            f"Illegal state transition: Cannot move from '{current_state}' to '{target_state}'. "
            f"Allowed next states: {VALID_TRANSITIONS.get(current_state, [])}"
        )

    state_data["previous_state"] = current_state
    state_data["current_state"] = target_state
    save_workflow_state(project_id, state_data)

    return state_data, True


def determine_next_action(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates current state to determine what the agent or human should do next.
    """
    state = state_data.get("current_state", WorkflowState.DRAFT)
    pending_q = state_data.get("pending_clarifications", [])

    if state == WorkflowState.DRAFT:
        return {
            "action": "ANALYZE_PROPOSAL",
            "actor": "agent",
            "description": "Agent is ready to extract research context and evaluate regulatory triggers."
        }
    elif state == WorkflowState.CONTEXT_ANALYSIS:
        return {
            "action": "EVALUATE_REQUIREMENTS",
            "actor": "agent",
            "description": "Context extracted. Agent ready to check institutional compliance rules."
        }
    elif state == WorkflowState.REQUIREMENT_CHECK:
        if pending_q:
            return {
                "action": "REQUEST_CLARIFICATION",
                "actor": "agent",
                "description": f"Agent identified {len(pending_q)} ambiguity item(s) requiring researcher clarification."
            }
        else:
            return {
                "action": "PREPARE_DOSSIER",
                "actor": "agent",
                "description": "All parameters verified. Agent ready to synthesize Ethics Pre-Submission Dossier."
            }
    elif state == WorkflowState.NEEDS_CLARIFICATION:
        return {
            "action": "AWAIT_RESEARCHER_INPUT",
            "actor": "researcher",
            "description": "Awaiting researcher responses to targeted Socratic questions."
        }
    elif state == WorkflowState.READY_FOR_ETHICS_HANDOFF:
        return {
            "action": "DISPATCH_TO_BIOETHICS",
            "actor": "agent_or_researcher",
            "description": "Dossier compiled. Ready for dispatch to the Institutional BioEthics Portal."
        }
    elif state == WorkflowState.ETHICS_REVIEW_PENDING:
        return {
            "action": "ASSIGN_REVIEWER",
            "actor": "ethics_coordinator",
            "description": "Dossier submitted to BioEthics. Waiting for Coordinator / Reviewer intake."
        }
    elif state == WorkflowState.MOCK_HANDOFF_COMPLETED:
        return {
            "action": "AWAIT_HUMAN_REVIEW_GATE",
            "actor": "ethics_officer",
            "description": "Mock handoff completed. Dossier synthesized for local/simulated human review gate."
        }
    elif state == WorkflowState.HUMAN_REVIEW:
        return {
            "action": "REVIEW_AND_DECIDE",
            "actor": "human_reviewer",
            "description": "Human Reviewer inspecting Dossier, Evidence Trace, and Proposal text."
        }
    elif state == WorkflowState.RETURNED_FOR_REVISION:
        return {
            "action": "REVISE_PROPOSAL",
            "actor": "researcher",
            "description": "Human reviewer requested revisions. Researcher must update draft."
        }
    elif state == WorkflowState.ESCALATED:
        return {
            "action": "RESOLVE_ESCALATION",
            "actor": "institutional_officer",
            "description": "Critical ambiguity or biosecurity concern flagged. Officer intervention required."
        }
    elif state == WorkflowState.CLEARED_FOR_NEXT_STAGE:
        return {
            "action": "PROCEED_TO_VIVA_DEFENSE",
            "actor": "faculty_and_student",
            "description": "Ethical clearance verified by human reviewer. Unlocked for oral defense and grading."
        }

    return {"action": "IDLE", "actor": "none", "description": "Workflow is idle."}
