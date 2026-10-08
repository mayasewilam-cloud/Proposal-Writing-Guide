"""
Structured Agent Decision Contract & Deterministic Policy Validator (Phase 3).
Enforces that all agent decisions conform to a strict JSON schema and obey
hard safety, governance, and autonomy limits before any action is executed.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple


ALLOWED_DECISION_TYPES = (
    "USE_TOOL",
    "ASK_RESEARCHER",
    "CONTINUE",
    "HUMAN_REVIEW",
    "STOP"
)

ALLOWED_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

FORBIDDEN_DECISION_KEYWORDS = (
    "APPROVE",
    "CLEAR_GATE",
    "CLEARED_FOR_NEXT_STAGE",
    "BYPASS",
    "OVERRIDE_SAFETY",
    "REWRITE_PROPOSAL",
    "OVERWRITE_PROPOSAL",
    "GRANT_CLEARANCE",
    "SELF_APPROVE"
)

FORBIDDEN_ARG_KEYS = (
    "proposal_text",
    "rewrite_proposal",
    "overwrite_methodology",
    "modify_title",
    "approve_ethics",
    "clear_gate",
    "human_decision",
    "is_locked",
    "override_safety",
    "downgrade_bsl",
    "bypass_rules",
    "url",
    "endpoint",
    "code",
    "exec",
    "eval"
)


class HardAgentLimits:
    """Bounded autonomy limits for a single governed agent run."""

    def __init__(
        self,
        max_tool_calls_per_run: int = 3,
        max_execution_time_sec: float = 15.0,
        max_repeated_calls_same_tool: int = 1,
        allowed_tool_whitelist: Tuple[str, ...] = (
            "search_pubmed",
            "search_europe_pmc",
            "search_openalex",
            "ask_researcher",
            "request_human_review"
        )
    ):
        self.max_tool_calls_per_run = int(max_tool_calls_per_run)
        self.max_execution_time_sec = float(max_execution_time_sec)
        self.max_repeated_calls_same_tool = int(max_repeated_calls_same_tool)
        self.allowed_tool_whitelist = tuple(allowed_tool_whitelist)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_tool_calls_per_run": self.max_tool_calls_per_run,
            "max_execution_time_sec": self.max_execution_time_sec,
            "max_repeated_calls_same_tool": self.max_repeated_calls_same_tool,
            "allowed_tool_whitelist": list(self.allowed_tool_whitelist),
            "no_arbitrary_urls": True,
            "no_arbitrary_code_execution": True,
            "no_proposal_rewriting": True,
            "no_governance_approval": True,
            "no_modification_of_human_gate_state": True,
            "no_bypassing_deterministic_safety_checks": True
        }


class AgentDecision:
    """Typed representation of the structured JSON decision contract."""

    def __init__(
        self,
        decision: str,
        tool_id: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        reason: str = "",
        question: Optional[str] = None,
        evidence_needed: str = "",
        confidence: float = 0.0,
        risk_level: str = "LOW"
    ):
        self.decision = str(decision or "").strip().upper()
        self.tool_id = str(tool_id).strip() if tool_id is not None and str(tool_id).strip() else None
        self.tool_args = dict(tool_args) if isinstance(tool_args, dict) else {}
        self.reason = str(reason or "").strip()
        self.question = str(question).strip() if question is not None and str(question).strip() else None
        self.evidence_needed = str(evidence_needed or "").strip()
        try:
            self.confidence = max(0.0, min(1.0, float(confidence)))
        except Exception:
            self.confidence = 0.0
        rl = str(risk_level or "LOW").strip().upper()
        self.risk_level = rl if rl in ALLOWED_RISK_LEVELS else "MEDIUM"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "tool_id": self.tool_id,
            "tool_args": self.tool_args,
            "reason": self.reason,
            "question": self.question,
            "evidence_needed": self.evidence_needed,
            "confidence": round(self.confidence, 2),
            "risk_level": self.risk_level
        }


class PolicyValidationResult:
    """Result of deterministic policy validation on a proposed AgentDecision."""

    def __init__(
        self,
        allowed: bool,
        status: str,
        reason: str,
        violation_code: Optional[str] = None,
        enforced_fallback_action: Optional[str] = None,
        safeguards_triggered: Optional[List[str]] = None
    ):
        self.allowed = bool(allowed)
        self.status = status  # ALLOWED | REJECTED | STOPPED_BY_POLICY
        self.reason = reason
        self.violation_code = violation_code
        self.enforced_fallback_action = enforced_fallback_action
        self.safeguards_triggered = list(safeguards_triggered or [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "status": self.status,
            "reason": self.reason,
            "violation_code": self.violation_code,
            "enforced_fallback_action": self.enforced_fallback_action,
            "safeguards_triggered": self.safeguards_triggered
        }


def parse_and_validate_decision(
    raw_input: Any,
    limits: HardAgentLimits,
    registered_tool_ids: List[str],
    tool_call_history: List[str],
    elapsed_seconds: float
) -> Tuple[Optional[AgentDecision], PolicyValidationResult]:
    """
    Parses raw LLM/planner output into an AgentDecision and validates it against
    the structured decision contract and hard autonomy/governance limits.
    """
    safeguards: List[str] = []

    # 1. Execution time limit check
    if elapsed_seconds > limits.max_execution_time_sec:
        safeguards.append("MAX_EXECUTION_TIME_EXCEEDED")
        return None, PolicyValidationResult(
            allowed=False,
            status="STOPPED_BY_POLICY",
            reason=f"Execution time ({elapsed_seconds:.2f}s) exceeded limit ({limits.max_execution_time_sec:.2f}s).",
            violation_code="MAX_EXECUTION_TIME_EXCEEDED",
            enforced_fallback_action="HUMAN_REVIEW",
            safeguards_triggered=safeguards
        )

    # 2. Parse JSON if string
    data: Any = raw_input
    if isinstance(raw_input, str):
        cleaned = raw_input.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            data = json.loads(cleaned.strip())
        except Exception as exc:
            safeguards.append("MALFORMED_JSON_DECISION")
            return None, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Agent output is not valid JSON: {str(exc)}",
                violation_code="MALFORMED_DECISION",
                enforced_fallback_action="STOPPED_BY_POLICY",
                safeguards_triggered=safeguards
            )

    if not isinstance(data, dict):
        safeguards.append("NON_OBJECT_DECISION")
        return None, PolicyValidationResult(
            allowed=False,
            status="REJECTED",
            reason="Agent decision payload must be a JSON object.",
            violation_code="MALFORMED_DECISION",
            enforced_fallback_action="STOPPED_BY_POLICY",
            safeguards_triggered=safeguards
        )

    raw_decision_val = str(data.get("decision") or "").strip().upper()
    if not raw_decision_val:
        safeguards.append("MISSING_DECISION_FIELD")
        return None, PolicyValidationResult(
            allowed=False,
            status="REJECTED",
            reason="Decision payload is missing required 'decision' field.",
            violation_code="MALFORMED_DECISION",
            enforced_fallback_action="STOPPED_BY_POLICY",
            safeguards_triggered=safeguards
        )

    # 3. Check for forbidden governance approval / safety bypass / proposal rewrite decisions
    for kw in FORBIDDEN_DECISION_KEYWORDS:
        if kw in raw_decision_val:
            safeguards.append(f"FORBIDDEN_DECISION_BLOCKED:{raw_decision_val}")
            return None, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Forbidden agent decision '{raw_decision_val}': Agent cannot approve ethics, clear gates, rewrite proposals, or bypass safety rules.",
                violation_code="GOVERNANCE_OR_SAFETY_VIOLATION",
                enforced_fallback_action="HUMAN_REVIEW",
                safeguards_triggered=safeguards
            )

    if raw_decision_val not in ALLOWED_DECISION_TYPES:
        safeguards.append(f"INVALID_DECISION_ENUM:{raw_decision_val}")
        return None, PolicyValidationResult(
            allowed=False,
            status="REJECTED",
            reason=f"Decision '{raw_decision_val}' is not in allowed contract {ALLOWED_DECISION_TYPES}.",
            violation_code="MALFORMED_DECISION",
            enforced_fallback_action="STOPPED_BY_POLICY",
            safeguards_triggered=safeguards
        )

    # 4. Inspect top-level keys and tool_args for forbidden mutations (proposal rewrite, safety downgrade, gate approval)
    tool_args = data.get("tool_args") if isinstance(data.get("tool_args"), dict) else {}
    combined_keys = set(str(k).lower() for k in data.keys()) | set(str(k).lower() for k in tool_args.keys())
    for forbidden_key in FORBIDDEN_ARG_KEYS:
        if forbidden_key in combined_keys:
            safeguards.append(f"FORBIDDEN_PARAMETER_BLOCKED:{forbidden_key}")
            return None, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Forbidden parameter '{forbidden_key}' detected in agent decision payload.",
                violation_code="FORBIDDEN_ACTION_PARAMETER",
                enforced_fallback_action="HUMAN_REVIEW",
                safeguards_triggered=safeguards
            )

    # 5. Inspect string values in tool_args for arbitrary URLs or code execution attempts
    for k, v in tool_args.items():
        s_val = str(v or "")
        if re.search(r"(https?://|file://|ftp://)", s_val, re.IGNORECASE):
            safeguards.append("ARBITRARY_URL_BLOCKED")
            return None, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Arbitrary URL in tool argument '{k}' is prohibited by bounded tool policy.",
                violation_code="ARBITRARY_URL_FORBIDDEN",
                enforced_fallback_action="STOPPED_BY_POLICY",
                safeguards_triggered=safeguards
            )
        if re.search(r"(__import__|eval\s*\(|exec\s*\(|os\.system|subprocess)", s_val, re.IGNORECASE):
            safeguards.append("ARBITRARY_CODE_BLOCKED")
            return None, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Code execution pattern in tool argument '{k}' is strictly prohibited.",
                violation_code="CODE_EXECUTION_FORBIDDEN",
                enforced_fallback_action="STOPPED_BY_POLICY",
                safeguards_triggered=safeguards
            )

    decision_obj = AgentDecision(
        decision=raw_decision_val,
        tool_id=data.get("tool_id"),
        tool_args=tool_args,
        reason=str(data.get("reason") or ""),
        question=data.get("question"),
        evidence_needed=str(data.get("evidence_needed") or ""),
        confidence=float(data.get("confidence", 0.8) if data.get("confidence") is not None else 0.8),
        risk_level=str(data.get("risk_level") or "LOW")
    )

    # 6. Validate USE_TOOL specifics
    if decision_obj.decision == "USE_TOOL":
        if not decision_obj.tool_id:
            safeguards.append("MISSING_TOOL_ID")
            return decision_obj, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason="Decision 'USE_TOOL' requires a valid 'tool_id'.",
                violation_code="MISSING_TOOL_ID",
                enforced_fallback_action="STOPPED_BY_POLICY",
                safeguards_triggered=safeguards
            )

        if decision_obj.tool_id not in limits.allowed_tool_whitelist or decision_obj.tool_id not in registered_tool_ids:
            safeguards.append(f"UNKNOWN_OR_UNWHITELISTED_TOOL:{decision_obj.tool_id}")
            return decision_obj, PolicyValidationResult(
                allowed=False,
                status="REJECTED",
                reason=f"Tool '{decision_obj.tool_id}' is not in the allowed bounded tool registry {list(limits.allowed_tool_whitelist)}.",
                violation_code="UNKNOWN_TOOL_ID",
                enforced_fallback_action="STOPPED_BY_POLICY",
                safeguards_triggered=safeguards
            )

        # Check max tool calls per run
        if len(tool_call_history) >= limits.max_tool_calls_per_run:
            safeguards.append("MAX_TOOL_CALLS_PER_RUN_REACHED")
            return decision_obj, PolicyValidationResult(
                allowed=False,
                status="STOPPED_BY_POLICY",
                reason=f"Maximum tool calls per run ({limits.max_tool_calls_per_run}) reached.",
                violation_code="MAX_TOOL_CALLS_EXCEEDED",
                enforced_fallback_action="HUMAN_REVIEW",
                safeguards_triggered=safeguards
            )

        # Check repeated calls to same tool
        same_tool_count = sum(1 for t in tool_call_history if t == decision_obj.tool_id)
        if same_tool_count >= limits.max_repeated_calls_same_tool:
            safeguards.append(f"MAX_REPEATED_TOOL_CALL_REACHED:{decision_obj.tool_id}")
            return decision_obj, PolicyValidationResult(
                allowed=False,
                status="STOPPED_BY_POLICY",
                reason=f"Tool '{decision_obj.tool_id}' has already been called {same_tool_count} time(s) (limit: {limits.max_repeated_calls_same_tool}).",
                violation_code="REPEATED_TOOL_CALL_EXCEEDED",
                enforced_fallback_action="HUMAN_REVIEW",
                safeguards_triggered=safeguards
            )

        # Ensure search tools have a non-empty query
        if decision_obj.tool_id in ("search_pubmed", "search_europe_pmc", "search_openalex"):
            if not str(decision_obj.tool_args.get("query") or "").strip():
                # Populate from evidence_needed if provided
                if decision_obj.evidence_needed:
                    decision_obj.tool_args["query"] = decision_obj.evidence_needed[:200]
                else:
                    safeguards.append("EMPTY_SEARCH_QUERY")
                    return decision_obj, PolicyValidationResult(
                        allowed=False,
                        status="REJECTED",
                        reason=f"Tool '{decision_obj.tool_id}' requires a non-empty 'query' argument.",
                        violation_code="INVALID_TOOL_ARGUMENTS",
                        enforced_fallback_action="STOPPED_BY_POLICY",
                        safeguards_triggered=safeguards
                    )

    return decision_obj, PolicyValidationResult(
        allowed=True,
        status="ALLOWED",
        reason="Decision conforms to structured contract and bounded governance policy.",
        violation_code=None,
        enforced_fallback_action=None,
        safeguards_triggered=safeguards
    )
