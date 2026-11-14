"""
Agent Orchestrator Service for the Trusted Research Workflow Agent.
Unites context extraction, requirement evaluation, clarification loops,
dossier compilation, adapter dispatch, human review gates, and audit trails.
"""

import os
import json
import datetime
import threading
from typing import Dict, Any, List, Optional, Tuple

from .models import (
    WorkflowState,
    ResearchContext,
    RequirementAssessment,
    ClarificationQuestion,
    FieldStatus
)
from .context_extractor import extract_research_context
from .requirement_engine import evaluate_institutional_requirements
from .clarification import generate_clarification_questions, apply_researcher_clarification
from .workflow import (
    load_workflow_state,
    save_workflow_state,
    transition_state,
    determine_next_action,
    WorkflowError
)
from .dossier import compile_ethics_pre_submission_dossier, render_dossier_html
from .gates import enforce_human_review_gate, UnauthorizedActionError
from .audit import record_audit_event, get_audit_history, verify_audit_integrity
from .adapter import BioEthicsAdapter
from .tool_registry import BoundedToolRegistry
from .agent_loop import GovernedAgentLoop


def get_agent_context_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ctx_dir = os.path.join(base_dir, "data", "agent_context")
    os.makedirs(ctx_dir, exist_ok=True)
    return ctx_dir


class AgentOrchestrator:
    """Central service coordinating the multi-step research workflow."""
    
    def __init__(self):
        self.adapter = BioEthicsAdapter()
        self.tool_registry = BoundedToolRegistry()
        self.agent_loop = GovernedAgentLoop(tool_registry=self.tool_registry)
        self._lock = threading.Lock()

    def get_tool_registry(self) -> List[Dict[str, Any]]:
        """Returns the inspectable bounded tool registry metadata."""
        return self.tool_registry.list_tools()

    def _save_context(self, context: ResearchContext) -> None:
        ctx_file = os.path.join(get_agent_context_dir(), f"{context.project_id}.json")
        with open(ctx_file, "w", encoding="utf-8") as f:
            json.dump(context.to_dict(), f, indent=2)

    def _load_context(self, project_id: str) -> Optional[ResearchContext]:
        ctx_file = os.path.join(get_agent_context_dir(), f"{project_id}.json")
        if os.path.exists(ctx_file):
            try:
                with open(ctx_file, "r", encoding="utf-8") as f:
                    return ResearchContext.from_dict(json.load(f))
            except Exception:
                pass
        return None

    def analyze_proposal(self, proposal_data: Dict[str, Any], project_id: str = "") -> Dict[str, Any]:
        with self._lock:
            return self._analyze_proposal_unlocked(proposal_data, project_id=project_id)

    def _analyze_proposal_unlocked(self, proposal_data: Dict[str, Any], project_id: str = "") -> Dict[str, Any]:
        """
        Step 1 & 2: Ingests proposal, extracts context, checks requirements,
        identifies ambiguities, and advances state machine.
        """
        clean_id = project_id or proposal_data.get("student_id") or "PROJECT-001"
        state = load_workflow_state(clean_id)

        # 1. State: Ensure clean transition to CONTEXT_ANALYSIS
        prev_s = state.get("current_state", WorkflowState.DRAFT)
        if prev_s != WorkflowState.CONTEXT_ANALYSIS:
            transition_state(clean_id, WorkflowState.CONTEXT_ANALYSIS, actor="agent", reason="Proposal analysis triggered.")
            state = load_workflow_state(clean_id)
            record_audit_event(
                project_id=clean_id,
                event_type="STATE_TRANSITION",
                actor="agent",
                actor_id="orchestrator",
                action="Initiate context extraction from proposal text",
                workflow_state=WorkflowState.CONTEXT_ANALYSIS,
                previous_state=prev_s,
                new_state=WorkflowState.CONTEXT_ANALYSIS
            )

        # 2. Extract context
        prev_context = self._load_context(clean_id)
        context = extract_research_context(proposal_data, clean_id)

        # Compute deterministic fingerprint of core proposal fields
        import hashlib
        fp_payload = json.dumps({
            "title": proposal_data.get("title", ""),
            "chassis": proposal_data.get("chassis", "") or proposal_data.get("system", ""),
            "tool": proposal_data.get("tool", ""),
            "target": proposal_data.get("target", ""),
            "abstract": proposal_data.get("abstract", ""),
            "methodology": proposal_data.get("methodology", ""),
            "human_subjects": proposal_data.get("human_subjects"),
            "recombinant_dna": proposal_data.get("recombinant_dna"),
            "pathogen_work": proposal_data.get("pathogen_work")
        }, sort_keys=True)
        current_fp = hashlib.sha256(fp_payload.encode("utf-8")).hexdigest()[:16]
        context.input_summary["input_fingerprint"] = current_fp

        prev_fp = (prev_context.input_summary.get("input_fingerprint") if (prev_context and isinstance(prev_context.input_summary, dict)) else None)

        # Preserve previously answered clarifications only when explicitly requested by the live UI session
        # and the underlying proposal draft fingerprint has not changed.
        if (
            proposal_data.get("preserve_clarifications")
            and not proposal_data.get("reset_clarifications")
            and prev_fp is not None
            and prev_fp == current_fp
        ):
            answered_list = state.get("answered_clarifications", [])
        else:
            answered_list = []
            state["answered_clarifications"] = []
            save_workflow_state(clean_id, state)

        for ans_q in answered_list:
            q_id = ans_q.get("question_id")
            resp_text = ans_q.get("researcher_response")
            if q_id and resp_text:
                context, _ = apply_researcher_clarification(context, q_id, resp_text)

        self._save_context(context)

        record_audit_event(
            project_id=clean_id,
            event_type="CONTEXT_EXTRACTED",
            actor="agent",
            actor_id="orchestrator",
            action=f"Extracted research parameters and regulatory triggers ({context.extraction_mode})",
            workflow_state=WorkflowState.CONTEXT_ANALYSIS,
            evidence_reference=f"Title: {context.title}; Chassis: {context.organism_or_chassis.value}",
            uncertainty_status=f"{len(context.uncertainties)} uncertainty item(s)",
            details={
                "extraction_mode": context.extraction_mode,
                "llm_available": context.llm_available,
                "checks_performed": context.checks_performed,
                "input_summary": context.input_summary,
                "chassis": context.organism_or_chassis.to_dict(),
                "human_subjects": context.human_subjects.to_dict(),
                "pathogen_work": context.pathogen_work.to_dict()
            }
        )

        # 3. State: CONTEXT_ANALYSIS -> REQUIREMENT_CHECK
        transition_state(clean_id, WorkflowState.REQUIREMENT_CHECK, actor="agent", reason="Context extraction completed.")
        record_audit_event(
            project_id=clean_id,
            event_type="STATE_TRANSITION",
            actor="agent",
            actor_id="orchestrator",
            action="Advance to compliance rule evaluation",
            workflow_state=WorkflowState.REQUIREMENT_CHECK,
            previous_state=WorkflowState.CONTEXT_ANALYSIS,
            new_state=WorkflowState.REQUIREMENT_CHECK
        )

        # 4. Evaluate requirements
        requirements = evaluate_institutional_requirements(context)
        req_dicts = [r.to_dict() for r in requirements]

        for req in requirements:
            record_audit_event(
                project_id=clean_id,
                event_type="REQUIREMENT_FLAGGED",
                actor="agent",
                actor_id="orchestrator",
                action=f"Flagged institutional requirement: {req.rule_id} ({req.title})",
                workflow_state=WorkflowState.REQUIREMENT_CHECK,
                evidence_reference=req.evidence,
                details=req.to_dict()
            )

        # 5. Check for questions or readiness (filtering out any already-answered question IDs whose field was resolved)
        answered_ids = {q.get("question_id") for q in answered_list if q.get("question_id")}
        raw_questions = generate_clarification_questions(context)
        questions = [q for q in raw_questions if q.question_id not in answered_ids]

        # 5.5 Execute Bounded Governed Agentic Loop (Action -> Observation -> Re-plan)
        agent_run_result = self.agent_loop.run(
            project_id=clean_id,
            context=context,
            requirements=requirements,
            pending_questions=questions,
            current_workflow_state=WorkflowState.REQUIREMENT_CHECK
        )
        existing_q_ids = {q.question_id for q in questions} | answered_ids
        for added_q in agent_run_result.get("added_clarifications", []):
            if isinstance(added_q, dict) and added_q.get("question_id") not in existing_q_ids:
                questions.append(ClarificationQuestion.from_dict(added_q))
                existing_q_ids.add(added_q.get("question_id"))

        # Persist context updates (such as literature evidence provenance appended by agent tools)
        self._save_context(context)

        if questions:
            transition_state(clean_id, WorkflowState.NEEDS_CLARIFICATION, actor="agent", reason="Ambiguities require clarification.")
            record_audit_event(
                project_id=clean_id,
                event_type="STATE_TRANSITION",
                actor="agent",
                actor_id="orchestrator",
                action=f"Dispatched {len(questions)} Socratic clarification question(s) to researcher",
                workflow_state=WorkflowState.NEEDS_CLARIFICATION,
                previous_state=WorkflowState.REQUIREMENT_CHECK,
                new_state=WorkflowState.NEEDS_CLARIFICATION
            )
        else:
            transition_state(clean_id, WorkflowState.READY_FOR_ETHICS_HANDOFF, actor="agent", reason="All requirements verified.")
            record_audit_event(
                project_id=clean_id,
                event_type="STATE_TRANSITION",
                actor="agent",
                actor_id="orchestrator",
                action="All parameters verified. Ready for dossier compilation.",
                workflow_state=WorkflowState.READY_FOR_ETHICS_HANDOFF,
                previous_state=WorkflowState.REQUIREMENT_CHECK,
                new_state=WorkflowState.READY_FOR_ETHICS_HANDOFF
            )

        # Update persisted state with questions, requirements, and bounded agent run trace
        state = load_workflow_state(clean_id)
        state["requirements_summary"] = req_dicts
        state["pending_clarifications"] = [q.to_dict() for q in questions]
        state["last_agent_run"] = agent_run_result
        save_workflow_state(clean_id, state)

        return {
            "project_id": clean_id,
            "workflow_state": state.get("current_state"),
            "next_action": determine_next_action(state),
            "extraction_mode": context.extraction_mode,
            "llm_available": context.llm_available,
            "checks_performed": context.checks_performed,
            "input_summary": context.input_summary,
            "context": context.to_dict(),
            "requirements": req_dicts,
            "pending_clarifications": state.get("pending_clarifications", []),
            "answered_clarifications": state.get("answered_clarifications", []),
            "uncertainties": context.uncertainties,
            "agent_run": agent_run_result,
            "available_tools": self.get_tool_registry(),
            "human_decision": state.get("human_decision"),
            "audit_integrity": verify_audit_integrity(clean_id)
        }

    def submit_clarification(self, project_id: str, question_id: str, researcher_answer: str) -> Dict[str, Any]:
        """
        Processes researcher's Socratic clarification response.
        Updates context, re-evaluates requirements, and advances state if all resolved.
        """
        context = self._load_context(project_id)
        if not context:
            return {"success": False, "error": f"Project context '{project_id}' not found."}

        state = load_workflow_state(project_id)
        current_s = state.get("current_state")

        # Apply clarification
        context, result = apply_researcher_clarification(context, question_id, researcher_answer)
        self._save_context(context)

        # Move question from pending to answered
        pending = state.get("pending_clarifications", [])
        answered = state.get("answered_clarifications", [])
        matched_q = None
        remaining_pending = []
        for q in pending:
            if q.get("question_id") == question_id:
                q["status"] = "answered"
                q["researcher_response"] = researcher_answer.strip()
                q["response_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                matched_q = q
                answered.append(q)
            else:
                remaining_pending.append(q)

        # If question_id wasn't in pending (e.g., submitted directly), still record it in answered
        if not matched_q:
            matched_q = {
                "question_id": question_id,
                "target_field": result.get("updated_field", "general"),
                "status": "answered",
                "researcher_response": researcher_answer.strip(),
                "response_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            answered.append(matched_q)

        state["pending_clarifications"] = remaining_pending
        state["answered_clarifications"] = answered
        save_workflow_state(project_id, state)

        record_audit_event(
            project_id=project_id,
            event_type="CLARIFICATION_ANSWERED",
            actor="human",
            actor_id=f"researcher:{project_id}",
            action=f"Researcher answered clarification question '{question_id}'",
            workflow_state=current_s,
            evidence_reference=researcher_answer.strip(),
            details={"question": matched_q}
        )

        # Re-evaluate requirements with updated context
        requirements = evaluate_institutional_requirements(context)
        state["requirements_summary"] = [r.to_dict() for r in requirements]
        save_workflow_state(project_id, state)

        # If all clarifications resolved, transition to READY_FOR_ETHICS_HANDOFF
        if not remaining_pending and current_s == WorkflowState.NEEDS_CLARIFICATION:
            transition_state(project_id=project_id, target_state=WorkflowState.REQUIREMENT_CHECK, actor="agent", reason="Clarification applied.")
            transition_state(project_id=project_id, target_state=WorkflowState.READY_FOR_ETHICS_HANDOFF, actor="agent", reason="All questions resolved.")
            record_audit_event(
                project_id=project_id,
                event_type="STATE_TRANSITION",
                actor="agent",
                actor_id="orchestrator",
                action="Clarification verified. State transitioned to READY_FOR_ETHICS_HANDOFF",
                workflow_state=WorkflowState.READY_FOR_ETHICS_HANDOFF,
                previous_state=WorkflowState.NEEDS_CLARIFICATION,
                new_state=WorkflowState.READY_FOR_ETHICS_HANDOFF
            )

        updated_state = load_workflow_state(project_id)
        return {
            "success": True,
            "project_id": project_id,
            "workflow_state": updated_state.get("current_state"),
            "next_action": determine_next_action(updated_state),
            "remaining_clarifications": len(remaining_pending),
            "pending_clarifications": remaining_pending,
            "answered_clarifications": updated_state.get("answered_clarifications", []),
            "context": context.to_dict(),
            "requirements": updated_state.get("requirements_summary", []),
            "uncertainties": context.uncertainties
        }

    def compile_dossier(self, project_id: str) -> Dict[str, Any]:
        """Compiles the official Ethics Pre-Submission Dossier."""
        context = self._load_context(project_id)
        if not context:
            raise ValueError(f"Project context '{project_id}' not found.")

        state = load_workflow_state(project_id)
        requirements = [RequirementAssessment.from_dict(r) for r in state.get("requirements_summary", [])]
        clarifications = state.get("answered_clarifications", [])

        dossier = compile_ethics_pre_submission_dossier(context, requirements, clarifications)
        state["dossier_generated"] = True
        save_workflow_state(project_id, state)

        record_audit_event(
            project_id=project_id,
            event_type="DOSSIER_COMPILED",
            actor="agent",
            actor_id="orchestrator",
            action="Compiled audit-ready Ethics Pre-Submission Dossier",
            workflow_state=state.get("current_state"),
            evidence_reference=dossier["dossier_id"],
            details={"annex_count": len(dossier["triggered_compliance_annexes"])}
        )

        return dossier

    def dispatch_to_bioethics(self, project_id: str, mode: str = "auto") -> Dict[str, Any]:
        """Dispatches compiled dossier to the BioEthics Portal adapter."""
        state = load_workflow_state(project_id)
        if state.get("pending_clarifications"):
            raise WorkflowError(
                f"Cannot dispatch dossier while {len(state['pending_clarifications'])} Socratic clarification(s) remain unresolved."
            )
        dossier = self.compile_dossier(project_id)
        res = self.adapter.dispatch_dossier(dossier, mode=mode)

        if res.get("success"):
            state = load_workflow_state(project_id)
            current_s = state.get("current_state")
            target_state = (
                WorkflowState.ETHICS_REVIEW_PENDING
                if res.get("mode") == "live_apps_script"
                else WorkflowState.MOCK_HANDOFF_COMPLETED
            )
            if current_s == WorkflowState.READY_FOR_ETHICS_HANDOFF:
                transition_state(
                    project_id,
                    target_state,
                    actor="agent",
                    reason=f"Dossier dispatched to BioEthics adapter ({res.get('mode')})."
                )

            record_audit_event(
                project_id=project_id,
                event_type="DOSSIER_DISPATCHED",
                actor="agent",
                actor_id="orchestrator",
                action=f"Dispatched dossier to BioEthics ({res.get('mode')})",
                workflow_state=target_state,
                previous_state=current_s,
                new_state=target_state,
                details=res
            )
            res["workflow_state"] = load_workflow_state(project_id).get("current_state")

        return res

    def record_human_decision(
        self,
        project_id: str,
        reviewer_id: str,
        role: str,
        decision: str,
        notes: str = "",
        conditions: str = "",
        actor: str = "human"
    ) -> Dict[str, Any]:
        """
        Executes a human approval/rejection gate.
        Enforces human-only authority.
        """
        state = load_workflow_state(project_id)
        current_s = state.get("current_state")

        # Enforce gate FIRST so any unauthorized actor (e.g. actor='agent') is immediately caught and logged
        try:
            gate_res = enforce_human_review_gate(
                project_id=project_id,
                actor=actor,
                role=role,
                reviewer_id=reviewer_id,
                decision=decision,
                notes=notes,
                conditions=conditions
            )
        except Exception as e:
            record_audit_event(
                project_id=project_id,
                event_type="UNAUTHORIZED_ACTION_ATTEMPTED",
                actor=actor,
                actor_id=f"{role}:{reviewer_id}",
                action=f"Blocked unauthorized decision attempt: '{decision}'",
                workflow_state=current_s,
                evidence_reference=str(e),
                details={"attempted_actor": actor, "attempted_role": role, "decision": decision}
            )
            raise

        # Cannot approve if proposal has never been analyzed or has unresolved clarifications
        if decision == "approved" and state.get("pending_clarifications"):
            raise WorkflowError(
                f"Cannot approve project '{project_id}' while {len(state['pending_clarifications'])} clarification question(s) remain unresolved."
            )
        if current_s == WorkflowState.DRAFT:
            raise WorkflowError(
                f"Cannot record institutional decision on project '{project_id}' in DRAFT state before agent analysis."
            )

        # Advance to HUMAN_REVIEW if currently in ETHICS_REVIEW_PENDING, MOCK_HANDOFF_COMPLETED, or READY_FOR_ETHICS_HANDOFF
        if current_s in [WorkflowState.ETHICS_REVIEW_PENDING, WorkflowState.MOCK_HANDOFF_COMPLETED, WorkflowState.READY_FOR_ETHICS_HANDOFF]:
            transition_state(project_id, WorkflowState.HUMAN_REVIEW, actor="human", actor_id=reviewer_id, reason="Reviewer opened dossier.")
            current_s = WorkflowState.HUMAN_REVIEW

        target_state = gate_res["target_state"]
        transition_state(
            project_id=project_id,
            target_state=target_state,
            actor="human",
            actor_id=reviewer_id,
            reason=f"Human review gate: {decision}"
        )

        state = load_workflow_state(project_id)
        state["human_decision"] = gate_res["decision_record"]
        if decision == "approved":
            state["is_locked"] = True
        save_workflow_state(project_id, state)

        record_audit_event(
            project_id=project_id,
            event_type="HUMAN_DECISION_RECORDED",
            actor="human",
            actor_id=f"{role}:{reviewer_id}",
            action=f"Recorded official human review decision: '{decision.upper()}'",
            workflow_state=target_state,
            previous_state=current_s,
            new_state=target_state,
            evidence_reference=f"Conditions: {conditions}; Notes: {notes}",
            details=gate_res["decision_record"]
        )

        return {
            "success": True,
            "project_id": project_id,
            "workflow_state": target_state,
            "decision": decision,
            "decision_record": gate_res["decision_record"],
            "recorded_by": f"{role} ({reviewer_id})",
            "message": gate_res["message"]
        }

    def get_workflow_overview(self, project_id: str) -> Dict[str, Any]:
        """Returns comprehensive state, context, dossier status, and audit history."""
        state = load_workflow_state(project_id)
        context = self._load_context(project_id)
        audit_history = get_audit_history(project_id)
        integrity = verify_audit_integrity(project_id)

        return {
            "project_id": project_id,
            "current_state": state.get("current_state", WorkflowState.DRAFT),
            "next_action": determine_next_action(state),
            "context": context.to_dict() if context else None,
            "requirements": state.get("requirements_summary", []),
            "pending_clarifications": state.get("pending_clarifications", []),
            "answered_clarifications": state.get("answered_clarifications", []),
            "last_agent_run": state.get("last_agent_run"),
            "available_tools": self.get_tool_registry(),
            "dossier_generated": state.get("dossier_generated", False),
            "human_decision": state.get("human_decision"),
            "audit_history": audit_history,
            "audit_integrity": integrity
        }
