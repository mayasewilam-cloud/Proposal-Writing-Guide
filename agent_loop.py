"""
Governed Agentic Loop (Phase 3): Action -> Observation -> Re-plan.
Implements a bounded, auditable, tool-using agent loop for evidence-assisted
biosafety/ethics clarification while preserving deterministic safety rules
and human governance gates.
"""

import os
import json
import time
import uuid
import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
import requests

from .models import (
    ResearchContext,
    RequirementAssessment,
    ClarificationQuestion,
    FieldStatus,
    WorkflowState
)
from .tool_registry import BoundedToolRegistry
from .decision_contract import (
    HardAgentLimits,
    AgentDecision,
    PolicyValidationResult,
    parse_and_validate_decision
)
from .audit import record_audit_event


AGENT_PLANNER_SYSTEM_PROMPT = """You are a bounded, governed research-compliance support agent.
Your role is to inspect the current extracted ResearchContext, institutional requirements, uncertainties,
and any prior tool observations from this run, and choose the single best next action from the allowed contract.

CRITICAL NON-NEGOTIABLE CONSTRAINTS:
1. You CANNOT approve ethics, clear human governance gates, or grant biosafety clearance.
2. You CANNOT rewrite or modify the researcher's proposal text.
3. You CANNOT downgrade or bypass deterministic safety rules.
4. You may ONLY select tools from the provided 'available_tools' list.
5. Do NOT output chain-of-thought or markdown prose. Output ONLY a single valid JSON object matching this exact schema:
{
  "decision": "USE_TOOL | ASK_RESEARCHER | CONTINUE | HUMAN_REVIEW | STOP",
  "tool_id": "search_pubmed | search_europe_pmc | search_openalex | ask_researcher | request_human_review | null",
  "tool_args": {},
  "reason": "Concise explanation of why this decision was chosen based on current state and observations.",
  "question": "If decision is ASK_RESEARCHER, the specific clarification question for the researcher, else null",
  "evidence_needed": "What specific biosafety, AMR, or containment evidence is being sought",
  "confidence": 0.85,
  "risk_level": "LOW | MEDIUM | HIGH"
}"""


class AgentPlanner:
    """
    Produces a structured JSON decision for each step of the Action -> Observation -> Re-plan loop.
    Uses configured LLM (Gemini / OpenAI) or an injected llm_callable, and falls back transparently
    to a stateful observation-driven deterministic planner if the LLM is unavailable.
    """

    def __init__(
        self,
        timeout: float = 6.0,
        llm_callable: Optional[Callable[[Dict[str, Any]], Any]] = None
    ):
        self.timeout = float(timeout)
        self.llm_callable = llm_callable
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

    def get_model_info(self) -> Dict[str, str]:
        if self.llm_callable is not None:
            return {
                "provider": getattr(self.llm_callable, "provider_name", "injected_llm_planner"),
                "model_version": getattr(self.llm_callable, "model_version", "structured-json-contract-v1"),
                "mode": "llm_planner"
            }
        if self.gemini_key:
            return {
                "provider": "google_gemini",
                "model_version": "gemini-2.5-flash",
                "mode": "llm_planner"
            }
        if self.openai_key:
            return {
                "provider": "openai",
                "model_version": "gpt-4o-mini",
                "mode": "llm_planner"
            }
        return {
            "provider": "deterministic_fallback",
            "model_version": "observation-driven-fallback-v1",
            "mode": "deterministic_fallback"
        }

    def _call_gemini_planner(self, state_payload: Dict[str, Any]) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": AGENT_PLANNER_SYSTEM_PROMPT},
                        {"text": f"CURRENT AGENT LOOP STATE:\n{json.dumps(state_payload, indent=2)}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return None

    def _call_openai_planner(self, state_payload: Dict[str, Any]) -> Optional[str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": AGENT_PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"CURRENT AGENT LOOP STATE:\n{json.dumps(state_payload, indent=2)}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code == 200:
            choices = resp.json().get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return None

    def _observation_driven_fallback_decision(self, state_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stateful fallback decision logic when external LLM API is unavailable.
        Inspects current uncertainties, requirements, and prior tool observations in the run.
        """
        uncertainties = state_payload.get("uncertainties", [])
        pending_clarifications = state_payload.get("pending_clarifications", [])
        requirements = state_payload.get("triggered_requirements", [])
        observations = state_payload.get("observations", [])
        called_tools = [obs.get("tool_id") for obs in observations if isinstance(obs, dict)]
        context_summary = state_payload.get("context_summary", {})

        has_high_risk_req = any(
            r.get("status") == "potentially_relevant" and r.get("category") in ("biosafety", "ethics", "institutional_review")
            for r in requirements
        )
        has_uncertainty = len(uncertainties) > 0 or len(pending_clarifications) > 0

        # Case 1: Sufficiently specified, no uncertainty, no high-risk ambiguity -> CONTINUE without tool calls
        if not has_uncertainty and not has_high_risk_req:
            return {
                "decision": "CONTINUE",
                "tool_id": None,
                "tool_args": {},
                "reason": "Proposal parameters and containment level are sufficiently specified with no unresolved biosafety or ethics ambiguities.",
                "question": None,
                "evidence_needed": "None",
                "confidence": 0.95,
                "risk_level": "LOW"
            }

        # Case 2: Mandatory human governance gate already reached with zero pending clarifications -> HUMAN_REVIEW
        if has_high_risk_req and not uncertainties and not pending_clarifications:
            return {
                "decision": "HUMAN_REVIEW",
                "tool_id": None,
                "tool_args": {},
                "reason": "All researcher clarifications are resolved, but triggered institutional biosafety/ethics requirements mandate human officer review.",
                "question": None,
                "evidence_needed": "Mandatory human governance sign-off",
                "confidence": 0.92,
                "risk_level": "HIGH"
            }

        # Build an evidence query from context
        chassis = str(context_summary.get("chassis") or "Escherichia coli").strip()
        target = str(context_summary.get("target") or "").strip()
        amr = bool(context_summary.get("antimicrobial_resistance"))
        pathogen = bool(context_summary.get("pathogen_work"))
        query_terms = [t for t in [chassis, target, "biosafety containment" if (pathogen or amr) else ""] if t]
        evidence_query = " ".join(query_terms).strip() or "Escherichia coli biosafety containment"

        # Case 3: No literature tool has been called yet -> select search_pubmed to gather biosafety/AMR evidence
        if not observations:
            return {
                "decision": "USE_TOOL",
                "tool_id": "search_pubmed",
                "tool_args": {"query": evidence_query, "max_results": 3},
                "reason": "Current proposal contains biosafety/AMR or sample-origin uncertainty; querying PubMed for peer-reviewed risk group and containment evidence.",
                "question": None,
                "evidence_needed": f"Peer-reviewed biosafety classification and containment precedent for {evidence_query}",
                "confidence": 0.78,
                "risk_level": "HIGH" if (amr or pathogen) else "MEDIUM"
            }

        # Inspect the most recent tool observation to adapt the next decision
        last_obs = observations[-1]
        last_status = last_obs.get("status")
        last_count = int(last_obs.get("records_count", 0))
        establishes_local = bool(last_obs.get("establishes_project_specific_containment", False))
        establishes_risk = bool(last_obs.get("establishes_biosafety_risk_group", False))

        # If the first literature tool failed or returned 0 records, try Europe PMC if not yet called
        if (last_status == "error" or last_count == 0) and "search_europe_pmc" not in called_tools:
            return {
                "decision": "USE_TOOL",
                "tool_id": "search_europe_pmc",
                "tool_args": {"query": evidence_query, "max_results": 3},
                "reason": f"Prior tool '{last_obs.get('tool_id')}' returned status='{last_status}' with {last_count} records; adapting plan to query Europe PMC as secondary evidence source.",
                "question": None,
                "evidence_needed": f"Secondary literature verification for {evidence_query}",
                "confidence": 0.75,
                "risk_level": "HIGH" if (amr or pathogen) else "MEDIUM"
            }

        # If observation explicitly resolved all project-specific containment & risk questions
        if last_status == "ok" and establishes_risk and establishes_local:
            return {
                "decision": "CONTINUE",
                "tool_id": None,
                "tool_args": {},
                "reason": "Retrieved literature evidence sufficiently establishes both risk group and containment parameters.",
                "question": None,
                "evidence_needed": "None",
                "confidence": 0.90,
                "risk_level": "MEDIUM"
            }

        # If literature returned records establishing general risk group, or if secondary literature also returned 0 records,
        # recognize that literature alone cannot establish the researcher's local laboratory containment / sample provenance
        if pending_clarifications or uncertainties:
            return {
                "decision": "ASK_RESEARCHER",
                "tool_id": None,
                "tool_args": {},
                "reason": "Human clarification required because retrieved literature evidence does not establish project-specific laboratory containment or sample de-identification.",
                "question": (
                    pending_clarifications[0].get("prompt")
                    if pending_clarifications
                    else f"Please specify the exact biosafety containment level (BSL-1 vs BSL-2) and strain provenance for {chassis}."
                ),
                "evidence_needed": "Researcher confirmation of local laboratory biosafety level and specimen source",
                "confidence": 0.88,
                "risk_level": "HIGH" if (amr or pathogen) else "MEDIUM"
            }

        return {
            "decision": "HUMAN_REVIEW",
            "tool_id": None,
            "tool_args": {},
            "reason": "Evidence collection complete; escalating to human reviewer for institutional governance decision.",
            "question": None,
            "evidence_needed": "Institutional officer review",
            "confidence": 0.85,
            "risk_level": "HIGH"
        }

    def decide(self, state_payload: Dict[str, Any]) -> Tuple[Any, Dict[str, str]]:
        """
        Returns (raw_decision_output, model_info_dict).
        """
        if self.llm_callable is not None:
            info = self.get_model_info()
            try:
                out = self.llm_callable(state_payload)
                return out, info
            except Exception:
                fallback_info = {
                    "provider": "deterministic_fallback",
                    "model_version": "observation-driven-fallback-v1",
                    "mode": "deterministic_fallback_after_llm_error"
                }
                return self._observation_driven_fallback_decision(state_payload), fallback_info

        if self.gemini_key:
            try:
                raw = self._call_gemini_planner(state_payload)
                if raw:
                    return raw, self.get_model_info()
            except Exception:
                pass

        if self.openai_key:
            try:
                raw = self._call_openai_planner(state_payload)
                if raw:
                    return raw, self.get_model_info()
            except Exception:
                pass

        fallback_info = {
            "provider": "deterministic_fallback",
            "model_version": "observation-driven-fallback-v1",
            "mode": "deterministic_fallback"
        }
        return self._observation_driven_fallback_decision(state_payload), fallback_info


class GovernedAgentLoop:
    """
    Executes the bounded Action -> Observation -> Re-plan loop under strict
    deterministic policy validation and records every cycle in the hash-chained audit trail.
    """

    def __init__(
        self,
        tool_registry: Optional[BoundedToolRegistry] = None,
        limits: Optional[HardAgentLimits] = None,
        planner: Optional[AgentPlanner] = None
    ):
        self.tool_registry = tool_registry or BoundedToolRegistry()
        self.limits = limits or HardAgentLimits()
        self.planner = planner or AgentPlanner()

    def run(
        self,
        project_id: str,
        context: ResearchContext,
        requirements: List[RequirementAssessment],
        pending_questions: List[ClarificationQuestion],
        current_workflow_state: str
    ) -> Dict[str, Any]:
        """
        Runs the bounded Action -> Observation -> Re-plan loop for a proposal analysis cycle.
        Preserves all deterministic safety constraints and records concise provenance for every step.
        """
        run_id = f"RUN-{str(uuid.uuid4())[:8].upper()}"
        start_time = time.perf_counter()
        input_fp = str(context.input_summary.get("input_fingerprint") or "unknown")
        available_tool_ids = self.tool_registry.get_allowed_tool_ids()
        available_tools_meta = self.tool_registry.list_tools()

        observations: List[Dict[str, Any]] = []
        tool_call_history: List[str] = []
        steps: List[Dict[str, Any]] = []
        added_questions: List[ClarificationQuestion] = []
        human_escalation: Optional[Dict[str, Any]] = None
        final_decision_outcome = "CONTINUE"

        max_iterations = self.limits.max_tool_calls_per_run + 2

        for step_idx in range(1, max_iterations + 1):
            elapsed_sec = time.perf_counter() - start_time

            state_payload = {
                "agent_run_id": run_id,
                "step_index": step_idx,
                "project_id": project_id,
                "current_workflow_state": current_workflow_state,
                "input_fingerprint": input_fp,
                "context_summary": {
                    "title": context.title,
                    "chassis": context.organism_or_chassis.value,
                    "chassis_status": context.organism_or_chassis.status,
                    "molecular_tools": [t.value for t in context.molecular_tools],
                    "target": context.input_summary.get("target", ""),
                    "human_subjects": context.human_subjects.value,
                    "human_subjects_status": context.human_subjects.status,
                    "recombinant_dna": context.recombinant_dna.value,
                    "pathogen_work": context.pathogen_work.value,
                    "antimicrobial_resistance": context.antimicrobial_resistance.value,
                    "biosafety_containment": context.biosafety_containment.value,
                    "biosafety_containment_status": context.biosafety_containment.status
                },
                "uncertainties": context.uncertainties,
                "triggered_requirements": [
                    r.to_dict() for r in requirements if r.status in ("potentially_relevant", "advisory")
                ],
                "pending_clarifications": [q.to_dict() for q in pending_questions],
                "available_tools": [
                    {"tool_id": t["tool_id"], "description": t["description"], "input_schema": t["input_schema"]}
                    for t in available_tools_meta
                ],
                "observations": observations,
                "tool_call_history": tool_call_history,
                "limits": self.limits.to_dict()
            }

            raw_decision, model_info = self.planner.decide(state_payload)
            decision_obj, policy_res = parse_and_validate_decision(
                raw_input=raw_decision,
                limits=self.limits,
                registered_tool_ids=available_tool_ids,
                tool_call_history=tool_call_history,
                elapsed_seconds=elapsed_sec
            )

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            uncertainty_summary = (
                f"{len(context.uncertainties)} uncertainty item(s); {len(pending_questions)} pending clarification(s)"
            )

            # Handle Policy Rejection or Hard Limit Stop
            if not policy_res.allowed or decision_obj is None:
                fallback_next = policy_res.enforced_fallback_action or "STOPPED_BY_POLICY"
                final_decision_outcome = fallback_next
                if fallback_next == "HUMAN_REVIEW":
                    human_escalation = {
                        "required_role": "ethics_officer",
                        "reason": policy_res.reason,
                        "triggered_by": "deterministic_policy_guard"
                    }

                attempted_decision_name = (
                    decision_obj.decision if decision_obj is not None
                    else (str(raw_decision.get("decision")) if isinstance(raw_decision, dict) else "MALFORMED")
                )
                attempted_tool_name = (
                    decision_obj.tool_id if decision_obj is not None
                    else (str(raw_decision.get("tool_id")) if isinstance(raw_decision, dict) else None)
                )

                step_record = {
                    "agent_run_id": run_id,
                    "step_index": step_idx,
                    "project_id": project_id,
                    "current_workflow_state": current_workflow_state,
                    "input_fingerprint": input_fp,
                    "available_tools": available_tool_ids,
                    "selected_tool": attempted_tool_name,
                    "tool_arguments": decision_obj.tool_args if decision_obj else {},
                    "tool_execution_status": "not_executed_policy_rejected",
                    "tool_result_provenance": None,
                    "observation_summary": f"Execution blocked by deterministic policy: {policy_res.reason}",
                    "decision_outcome": attempted_decision_name,
                    "reason": decision_obj.reason if decision_obj else "Rejected before execution.",
                    "confidence": decision_obj.confidence if decision_obj else 0.0,
                    "uncertainty": uncertainty_summary,
                    "policy_validation_result": policy_res.to_dict(),
                    "next_action": fallback_next,
                    "human_escalation": human_escalation,
                    "timestamp": now_iso,
                    "model_provider": model_info["provider"],
                    "model_version": model_info["model_version"],
                    "planner_mode": model_info["mode"],
                    "deterministic_safeguards_triggered": policy_res.safeguards_triggered,
                    "concise_provenance": (
                        f"Decision: {attempted_decision_name} | "
                        f"Action: {attempted_tool_name or 'none'} | "
                        f"Policy: {policy_res.status} ({policy_res.violation_code}) | "
                        f"Next decision: {fallback_next}"
                    )
                }
                steps.append(step_record)

                record_audit_event(
                    project_id=project_id,
                    event_type="AGENT_POLICY_REJECTED",
                    actor="system",
                    actor_id="policy_validator",
                    action=f"Blocked agent decision '{attempted_decision_name}' ({policy_res.violation_code})",
                    workflow_state=current_workflow_state,
                    evidence_reference=policy_res.reason,
                    uncertainty_status=uncertainty_summary,
                    details=step_record
                )
                break

            # Policy ALLOWED -> Process validated decision
            if decision_obj.decision == "USE_TOOL" and decision_obj.tool_id:
                tool_id = decision_obj.tool_id
                tool_args = decision_obj.tool_args
                tool_call_history.append(tool_id)

                obs = self.tool_registry.execute_tool(tool_id, tool_args, context=context)
                observations.append(obs)

                # If tool retrieved literature records, append provenance to context.evidence_log
                if obs.get("status") == "ok" and tool_id in ("search_pubmed", "search_europe_pmc", "search_openalex"):
                    context.evidence_log.append({
                        "agent_run_id": run_id,
                        "step_index": step_idx,
                        "tool_id": tool_id,
                        "query": tool_args.get("query", ""),
                        "records_count": obs.get("records_count", 0),
                        "records": obs.get("records", []),
                        "provenance": obs.get("provenance", {}),
                        "timestamp": now_iso
                    })
                elif obs.get("status") == "ok" and tool_id == "ask_researcher" and obs.get("question"):
                    q_dict = obs["question"]
                    added_questions.append(ClarificationQuestion.from_dict(q_dict))
                elif obs.get("status") == "ok" and tool_id == "request_human_review" and obs.get("escalation"):
                    human_escalation = obs["escalation"]

                next_step_label = "REASSESS_OBSERVATION"
                prov_dict = dict(obs.get("provenance") or {})
                if "records_count" not in prov_dict:
                    prov_dict["records_count"] = obs.get("records_count", 0)
                step_record = {
                    "agent_run_id": run_id,
                    "step_index": step_idx,
                    "project_id": project_id,
                    "current_workflow_state": current_workflow_state,
                    "input_fingerprint": input_fp,
                    "available_tools": available_tool_ids,
                    "selected_tool": tool_id,
                    "tool_arguments": tool_args,
                    "tool_execution_status": obs.get("status", "unknown"),
                    "records_count": obs.get("records_count", 0),
                    "tool_result_provenance": prov_dict,
                    "observation_summary": obs.get("observation_summary", ""),
                    "decision_outcome": "USE_TOOL",
                    "reason": decision_obj.reason,
                    "confidence": decision_obj.confidence,
                    "uncertainty": uncertainty_summary,
                    "policy_validation_result": policy_res.to_dict(),
                    "next_action": next_step_label,
                    "human_escalation": human_escalation,
                    "timestamp": now_iso,
                    "model_provider": model_info["provider"],
                    "model_version": model_info["model_version"],
                    "planner_mode": model_info["mode"],
                    "deterministic_safeguards_triggered": policy_res.safeguards_triggered,
                    "concise_provenance": (
                        f"Decision: {decision_obj.evidence_needed or 'Evidence required'} | "
                        f"Action: {tool_id} | "
                        f"Reason: {decision_obj.reason} | "
                        f"Policy: ALLOWED | "
                        f"Observation: {obs.get('observation_summary', '')} | "
                        f"Next decision: Reassess observation in step {step_idx + 1}"
                    )
                }
                steps.append(step_record)

                record_audit_event(
                    project_id=project_id,
                    event_type="AGENT_TOOL_EXECUTED",
                    actor="agent",
                    actor_id=f"agent_loop:{run_id}",
                    action=f"Selected and executed tool '{tool_id}': {obs.get('observation_summary', '')}",
                    workflow_state=current_workflow_state,
                    evidence_reference=json.dumps(obs.get("provenance", {})),
                    uncertainty_status=uncertainty_summary,
                    details=step_record
                )
                # Continue loop so the agent reassesses the observation on the next iteration!
                continue

            # Terminal decisions: CONTINUE, ASK_RESEARCHER, HUMAN_REVIEW, STOP
            final_decision_outcome = decision_obj.decision
            if decision_obj.decision == "ASK_RESEARCHER":
                if decision_obj.question and not pending_questions and not added_questions:
                    q_new = ClarificationQuestion(
                        question_id="CLAR-AGENT-01",
                        field="biosafety_containment",
                        prompt=decision_obj.question,
                        rationale=decision_obj.reason or "Clarification requested by governed agent loop after evidence review.",
                        context_snippet="Agent evidence reassessment"
                    )
                    added_questions.append(q_new)
                next_action_str = "AWAIT_RESEARCHER_CLARIFICATION"
            elif decision_obj.decision == "HUMAN_REVIEW":
                human_escalation = {
                    "required_role": "biosafety_officer",
                    "reason": decision_obj.reason or "Mandatory human governance gate or unresolved biosecurity risk.",
                    "risk_level": decision_obj.risk_level,
                    "autonomous_approval_blocked": True,
                    "timestamp": now_iso
                }
                next_action_str = "AWAIT_HUMAN_GOVERNANCE_REVIEW"
            elif decision_obj.decision == "CONTINUE":
                next_action_str = "PROCEED_IN_WORKFLOW"
            else:
                next_action_str = "STOPPED"

            step_record = {
                "agent_run_id": run_id,
                "step_index": step_idx,
                "project_id": project_id,
                "current_workflow_state": current_workflow_state,
                "input_fingerprint": input_fp,
                "available_tools": available_tool_ids,
                "selected_tool": None,
                "tool_arguments": {},
                "tool_execution_status": "not_applicable",
                "tool_result_provenance": None,
                "observation_summary": (
                    observations[-1].get("observation_summary", "Prior observations assessed.")
                    if observations else "Assessed extracted state directly; no external tool call required."
                ),
                "decision_outcome": decision_obj.decision,
                "reason": decision_obj.reason,
                "confidence": decision_obj.confidence,
                "uncertainty": uncertainty_summary,
                "policy_validation_result": policy_res.to_dict(),
                "next_action": next_action_str,
                "human_escalation": human_escalation,
                "timestamp": now_iso,
                "model_provider": model_info["provider"],
                "model_version": model_info["model_version"],
                "planner_mode": model_info["mode"],
                "deterministic_safeguards_triggered": policy_res.safeguards_triggered,
                "concise_provenance": (
                    f"Decision: {decision_obj.decision} | "
                    f"Action: none | "
                    f"Reason: {decision_obj.reason} | "
                    f"Policy: ALLOWED | "
                    f"Observation: {observations[-1].get('observation_summary', 'None') if observations else 'None'} | "
                    f"Next decision: {next_action_str}"
                )
            }
            steps.append(step_record)

            record_audit_event(
                project_id=project_id,
                event_type="AGENT_DECISION_RECORDED",
                actor="agent",
                actor_id=f"agent_loop:{run_id}",
                action=f"Agent loop concluded with decision '{decision_obj.decision}': {decision_obj.reason}",
                workflow_state=current_workflow_state,
                evidence_reference=f"Tool calls: {len(tool_call_history)}",
                uncertainty_status=uncertainty_summary,
                details=step_record
            )
            break

        total_elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return {
            "agent_run_id": run_id,
            "project_id": project_id,
            "input_fingerprint": input_fp,
            "planner_mode": steps[-1]["planner_mode"] if steps else "deterministic_fallback",
            "model_provider": steps[-1]["model_provider"] if steps else "deterministic_fallback",
            "model_version": steps[-1]["model_version"] if steps else "observation-driven-fallback-v1",
            "final_decision": final_decision_outcome,
            "tool_calls_count": len(tool_call_history),
            "tools_called": tool_call_history,
            "observations": observations,
            "added_clarifications": [q.to_dict() for q in added_questions],
            "human_escalation": human_escalation,
            "limits_enforced": self.limits.to_dict(),
            "elapsed_ms": total_elapsed_ms,
            "steps": steps
        }
