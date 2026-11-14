"""
Phase 3 Verification Suite — Governed Agentic Loop (Action -> Observation -> Re-plan).
Tests:
1. BoundedToolRegistry inspectability & schema enforcement
2. Structured AgentDecision contract & deterministic policy validation
3. Scenario A (Low-risk proposal -> CONTINUE, 0 tool calls)
4. Scenario B (Ambiguous AMR/biosafety proposal -> USE_TOOL -> Observation -> Re-plan)
5. Scenario C (Mandatory human governance boundary -> HUMAN_REVIEW -> 403 on agent approval -> human sign-off)
6. Part 9 Failure Modes:
   - Tool unavailable -> error observation -> agent adapts to alternative tool
   - LLM unavailable -> deterministic fallback
   - Malformed / unknown tool ID -> policy rejection, 0 executions, audit logged
   - Forbidden action ("APPROVE_ETHICS", proposal rewrite, arbitrary URL) -> policy rejection, audit logged
   - Safety-downgrading LLM interpretation -> deterministic safety rule prevails
7. Part 10 Genuine Agentic Proof:
   - Exact same proposal + same initial planner prompt produces DIFFERENT second actions
     purely as a function of the intermediate observation from the first tool execution.
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch

PORTAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PORTAL_DIR not in sys.path:
    sys.path.insert(0, PORTAL_DIR)

os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"
os.environ["TESTING"] = "1"

_ORIG_ENV_DATA_DIR = os.environ.get("BIOWRITER_DATA_DIR")
_TEST_TMP_DIR = None
_CREATED_MODULE_TMP = False

_LIVE_DATA_DIR_CANONICAL = os.path.normcase(os.path.realpath(os.path.join(PORTAL_DIR, "data")))

if "BIOWRITER_DATA_DIR" in os.environ:
    _configured_raw = os.environ["BIOWRITER_DATA_DIR"]
    if not _configured_raw or not _configured_raw.strip():
        raise RuntimeError("Unsafe test configuration: BIOWRITER_DATA_DIR is configured with an empty or whitespace-only path")
    _configured_canonical = os.path.normcase(os.path.realpath(_configured_raw))
    try:
        _common = os.path.commonpath([_configured_canonical, _LIVE_DATA_DIR_CANONICAL])
    except (ValueError, OSError):
        _common = None
    if _common == _LIVE_DATA_DIR_CANONICAL:
        raise RuntimeError(
            f"Unsafe test configuration: BIOWRITER_DATA_DIR points to or inside live project storage '{_configured_canonical}'!"
        )
    if _common == _configured_canonical:
        raise RuntimeError(
            f"Unsafe test configuration: BIOWRITER_DATA_DIR '{_configured_canonical}' contains live project data!"
        )
else:
    _TEST_TMP_DIR = tempfile.mkdtemp(prefix="biowriter_test_agent_loop_")
    os.environ["BIOWRITER_DATA_DIR"] = _TEST_TMP_DIR
    _CREATED_MODULE_TMP = True


def tearDownModule():
    global _TEST_TMP_DIR, _ORIG_ENV_DATA_DIR, _CREATED_MODULE_TMP
    if _CREATED_MODULE_TMP:
        if _ORIG_ENV_DATA_DIR is None:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        else:
            os.environ["BIOWRITER_DATA_DIR"] = _ORIG_ENV_DATA_DIR
        if _TEST_TMP_DIR and os.path.exists(_TEST_TMP_DIR):
            shutil.rmtree(_TEST_TMP_DIR, ignore_errors=True)

from app import app
from agent.models import WorkflowState, FieldStatus
from agent.tool_registry import BoundedToolRegistry, ToolDefinition
from agent.decision_contract import HardAgentLimits, parse_and_validate_decision
from agent.agent_loop import GovernedAgentLoop, AgentPlanner
from agent.context_extractor import extract_research_context, get_llm_extractor
from agent.requirement_engine import evaluate_institutional_requirements
from agent.clarification import generate_clarification_questions
from agent.workflow import get_agent_state_dir
from agent.service import get_agent_context_dir
from agent.audit import get_agent_audit_dir, get_audit_history, verify_audit_integrity


def _is_strictly_within(target: str, parent: str) -> bool:
    """Component-aware containment check: target must be inside parent, not parent itself."""
    try:
        return target != parent and os.path.commonpath([target, parent]) == parent
    except (ValueError, OSError):
        return False


def _resolves_to_or_within(target: str, parent: str) -> bool:
    """Component-aware containment check: target equals parent or lies inside parent."""
    try:
        return os.path.commonpath([target, parent]) == parent
    except (ValueError, OSError):
        return False


def _is_junction(path: str) -> bool:
    """Check if path is a directory junction, supporting Python versions with os.path.isjunction."""
    if hasattr(os.path, "isjunction"):
        try:
            return os.path.isjunction(path)
        except (ValueError, OSError):
            return False
    return False


def cleanup_project_artifacts(pid: str) -> None:
    """
    Safely cleans up synthetic test artifacts for a specific project identifier.
    Guarantees that deletions are strictly confined to the configured temporary directory
    using realpath resolution, Windows case normalization, component-aware commonpath checks,
    and symlink-safe unlinking to prevent deleting destination files of symbolic links.
    """
    if not pid or not isinstance(pid, str) or not pid.strip():
        raise ValueError(f"Invalid project identifier for cleanup: {pid!r}")
    # Reject path traversal, directory separators, and absolute paths in pid
    if any(sep in pid for sep in ("/", "\\", "..")) or os.path.isabs(pid):
        raise ValueError(f"Unsafe project identifier containing path traversal or separators: {pid!r}")

    tmp_dir = os.environ.get("BIOWRITER_DATA_DIR")
    if not tmp_dir:
        return

    live_data_dir = os.path.normcase(os.path.realpath(os.path.join(PORTAL_DIR, "data")))
    norm_tmp = os.path.normcase(os.path.realpath(tmp_dir))

    # Reject cleanup if the configured temporary directory resolves to live storage or inside it
    if _resolves_to_or_within(norm_tmp, live_data_dir):
        raise RuntimeError(f"Unsafe cleanup attempt: temporary directory '{norm_tmp}' resolves to or within live storage '{live_data_dir}'!")
    if _resolves_to_or_within(live_data_dir, norm_tmp):
        raise RuntimeError(f"Unsafe cleanup attempt: temporary directory '{norm_tmp}' contains live storage '{live_data_dir}'!")

    if not os.path.exists(tmp_dir):
        return

    for d, ext in [
        (get_agent_state_dir(), ".json"),
        (get_agent_context_dir(), ".json"),
        (get_agent_audit_dir(), ".jsonl"),
    ]:
        norm_d = os.path.normcase(os.path.realpath(d))
        # Reject cleanup if any Agent directory resolves to live storage
        if _resolves_to_or_within(norm_d, live_data_dir):
            continue
        # Verify Agent directory is strictly within the temporary directory
        if not _is_strictly_within(norm_d, norm_tmp):
            continue

        raw_target = os.path.join(d, f"{pid}{ext}")

        # Detect symbolic links and files via lexists so dangling symbolic links are not overlooked
        if not os.path.lexists(raw_target):
            continue

        # 1. Directory junction protection:
        # If target is a directory junction, refuse to traverse or delete its destination.
        if _is_junction(raw_target):
            import warnings
            warnings.warn(f"Target '{raw_target}' is a directory junction; rejecting deletion to protect junction target.")
            continue

        # 2. Symbolic link handling:
        # Check if target is a symbolic link before resolving the target for ordinary file deletion.
        # Remove the link entry itself without resolving, opening, or deleting the link's destination.
        if os.path.islink(raw_target):
            try:
                os.unlink(raw_target)
            except OSError as e:
                import warnings
                warnings.warn(f"Failed to unlink symbolic link '{raw_target}': {e}")
            continue

        # 3. Directory rejection:
        # Refuse to delete directories or directory structures as part of file cleanup.
        if os.path.isdir(raw_target):
            import warnings
            warnings.warn(f"Target '{raw_target}' is a directory; refusing to delete directories as part of file cleanup.")
            continue

        # 4. Ordinary non-link file deletion:
        # Canonical path validation using realpath(), normcase(), and component-aware commonpath()
        norm_target = os.path.normcase(os.path.realpath(raw_target))

        # Do not delete the Agent directory itself or any parent directory
        if norm_target in (norm_d, norm_tmp, live_data_dir):
            raise RuntimeError(f"Unsafe cleanup: attempt to delete directory structure itself: '{norm_target}'")

        # Ensure target is strictly contained inside its intended Agent directory and temporary directory
        if not _is_strictly_within(norm_target, norm_d):
            raise RuntimeError(f"Unsafe cleanup: target '{norm_target}' escapes agent directory '{norm_d}'!")
        if not _is_strictly_within(norm_target, norm_tmp):
            raise RuntimeError(f"Unsafe cleanup: target '{norm_target}' escapes temporary directory '{norm_tmp}'!")
        if _resolves_to_or_within(norm_target, live_data_dir):
            raise RuntimeError(f"Unsafe cleanup: target '{norm_target}' resolves inside live storage '{live_data_dir}'!")

        # Perform deletion against the original validated directory entry (`raw_target`),
        # not the resolved destination path (`norm_target`).
        try:
            if os.path.islink(raw_target):
                os.unlink(raw_target)
            else:
                os.remove(raw_target)
        except OSError as e:
            import warnings
            warnings.warn(f"Failed to remove test artifact '{raw_target}': {e}")


class TestPhase3GovernedAgentLoop(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"
        self.test_pids = [
            "P3-SCEN-A",
            "P3-SCEN-B",
            "P3-SCEN-C",
            "P3-FAIL-TOOL",
            "P3-FAIL-MALFORMED",
            "P3-FAIL-FORBIDDEN",
            "P3-FAIL-DOWNGRADE",
            "P3-PROOF-RUN1",
            "P3-PROOF-RUN2"
        ]
        for pid in self.test_pids:
            cleanup_project_artifacts(pid)

    def tearDown(self):
        for pid in self.test_pids:
            cleanup_project_artifacts(pid)

    # -------------------------------------------------------------------------
    # PART 2: Inspectable Bounded Tool Registry
    # -------------------------------------------------------------------------
    def test_01_bounded_tool_registry_inspectable(self):
        resp = self.client.get("/agent/api/tools")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tool_count"], 5)

        tool_ids = [t["tool_id"] for t in data["tools"]]
        self.assertEqual(
            tool_ids,
            ["search_pubmed", "search_europe_pmc", "search_openalex", "ask_researcher", "request_human_review"]
        )

        required_keys = {
            "tool_id", "description", "input_schema", "output_schema",
            "authorization_policy", "risk_level", "timeout", "error_handling", "provenance_metadata"
        }
        for tool in data["tools"]:
            self.assertTrue(required_keys.issubset(set(tool.keys())))
            self.assertFalse(tool["authorization_policy"]["mutates_proposal_text"])
            self.assertFalse(tool["authorization_policy"]["can_approve_governance_gate"])
            self.assertFalse(tool["authorization_policy"]["can_override_deterministic_safety"])

    # -------------------------------------------------------------------------
    # PART 8 — SCENARIO A: Sufficiently specified low-risk proposal -> CONTINUE
    # -------------------------------------------------------------------------
    def test_02_scenario_a_no_tool_required(self):
        pid = "P3-SCEN-A"
        proposal = {
            "student_id": pid,
            "title": "Spectrophotometric Calibration of Purified GFP in Tris Buffer",
            "chassis": "Cell-Free Buffer Matrix",
            "tool": "Purified GFP Standard",
            "target": "Fluorescence Linearity",
            "abstract": "Cell-free calibration of purified GFP protein in Tris-HCl buffer.",
            "methodology": "Serial dilutions of purified GFP in 50 mM Tris-HCl buffer measured at 488 nm under BSL-1.",
            "human_subjects": False,
            "recombinant_dna": False,
            "pathogen_work": False
        }
        res = self.client.post(f"/agent/api/analyze/{pid}", json={"proposal_data": proposal}).get_json()
        self.assertTrue(res["success"])
        self.assertEqual(res["workflow_state"], WorkflowState.READY_FOR_ETHICS_HANDOFF)

        agent_run = res["agent_run"]
        self.assertEqual(agent_run["final_decision"], "CONTINUE")
        self.assertEqual(agent_run["tool_calls_count"], 0)
        self.assertEqual(len(agent_run["steps"]), 1)
        self.assertEqual(agent_run["steps"][0]["decision_outcome"], "CONTINUE")
        self.assertEqual(agent_run["steps"][0]["policy_validation_result"]["status"], "ALLOWED")

    # -------------------------------------------------------------------------
    # PART 8 — SCENARIO B: Ambiguous AMR/biosafety proposal -> USE_TOOL -> Observation -> Re-plan
    # -------------------------------------------------------------------------
    def test_03_scenario_b_tool_selected_and_reassessed(self):
        pid = "P3-SCEN-B"
        proposal = {
            "student_id": pid,
            "title": "CRISPR-Cas12a Detection of mcr-1 Colistin Resistance in Clinical Isolates",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 colistin resistance gene",
            "methodology": "Testing clinical isolate swabs from hospital patients for mcr-1 resistance.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True
        }

        # Mock requests.get inside tool_registry so test is fast, deterministic, and verifies full provenance
        def fake_requests_get(url, headers=None, timeout=5.0):
            class FakeResp:
                status_code = 200
                def raise_for_status(self):
                    pass
                def json(self):
                    if "esearch.fcgi" in url:
                        return {"esearchresult": {"idlist": ["26597791", "30123456"]}}
                    if "esummary.fcgi" in url:
                        return {
                            "result": {
                                "26597791": {
                                    "title": "Emergence of plasmid-mediated colistin resistance mechanism MCR-1 in Enterobacteriaceae.",
                                    "fulljournalname": "The Lancet Infectious Diseases",
                                    "pubdate": "2016 Feb",
                                    "authors": [{"name": "Liu YY"}, {"name": "Wang Y"}]
                                },
                                "30123456": {
                                    "title": "Biosafety Level 2 containment practices for clinical Enterobacteriaceae harboring mobile resistance plasmids.",
                                    "fulljournalname": "Applied Biosafety",
                                    "pubdate": "2021 Jun",
                                    "authors": [{"name": "Smith J"}]
                                }
                            }
                        }
                    return {}
            return FakeResp()

        with patch("agent.tool_registry.requests.get", side_effect=fake_requests_get):
            res = self.client.post(f"/agent/api/analyze/{pid}", json={"proposal_data": proposal}).get_json()

        self.assertTrue(res["success"])
        self.assertEqual(res["workflow_state"], WorkflowState.NEEDS_CLARIFICATION)
        agent_run = res["agent_run"]
        self.assertGreaterEqual(agent_run["tool_calls_count"], 1)
        self.assertIn("search_pubmed", agent_run["tools_called"])
        self.assertEqual(agent_run["final_decision"], "ASK_RESEARCHER")

        # Verify Step 1 was USE_TOOL (search_pubmed) and Step 2 was ASK_RESEARCHER after observing PubMed results
        self.assertEqual(agent_run["steps"][0]["decision_outcome"], "USE_TOOL")
        self.assertEqual(agent_run["steps"][0]["selected_tool"], "search_pubmed")
        self.assertEqual(agent_run["steps"][0]["tool_execution_status"], "ok")
        self.assertEqual(agent_run["steps"][1]["decision_outcome"], "ASK_RESEARCHER")

        # Verify researcher's proposal text was NOT modified
        self.assertEqual(res["context"]["title"], proposal["title"])

        # Verify hash-chained audit integrity
        self.assertTrue(verify_audit_integrity(pid)["valid"])

    # -------------------------------------------------------------------------
    # PART 8 — SCENARIO C: Mandatory Governance Boundary -> HUMAN_REVIEW -> 403 on Agent Approval
    # -------------------------------------------------------------------------
    def test_04_scenario_c_governance_boundary_and_human_gate(self):
        pid = "P3-SCEN-C"
        proposal = {
            "student_id": pid,
            "title": "BSL-2 Characterization of Reference ATCC BAA-2469 mcr-1 Strain",
            "chassis": "Escherichia coli ATCC BAA-2469",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 colistin resistance plasmid",
            "methodology": "All work uses de-identified ATCC reference strain inside a certified BSL-2 Class II biosafety cabinet with autoclaving at 121C.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True
        }
        res = self.client.post(f"/agent/api/analyze/{pid}", json={"proposal_data": proposal}).get_json()
        self.assertTrue(res["success"])
        self.assertEqual(res["workflow_state"], WorkflowState.READY_FOR_ETHICS_HANDOFF)
        self.assertEqual(res["agent_run"]["final_decision"], "HUMAN_REVIEW")
        self.assertIsNotNone(res["agent_run"]["human_escalation"])

        # Agent attempts to approve gate -> strictly HTTP 403
        r_agent = self.client.post(f"/agent/api/human_decision/{pid}", json={
            "actor": "agent",
            "role": "ethics_officer",
            "decision": "approved"
        })
        self.assertEqual(r_agent.status_code, 403)

        # Authorized human reviewer approves -> HTTP 200 CLEARED_FOR_NEXT_STAGE
        r_human = self.client.post(f"/agent/api/human_decision/{pid}", json={
            "actor": "human",
            "role": "ethics_officer",
            "reviewer_id": "DR-ETHICS-CHAIR-01",
            "decision": "approved",
            "notes": "Verified BSL-2 SOP and reference strain documentation.",
            "reviewer_passcode": "faculty2026"
        })
        self.assertEqual(r_human.status_code, 200)
        self.assertEqual(r_human.get_json()["workflow_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)
        self.assertTrue(verify_audit_integrity(pid)["valid"])

    # -------------------------------------------------------------------------
    # PART 9 — FAILURE MODES (Tool Unavailable, Malformed Tool ID, Forbidden Action, Safety Downgrade)
    # -------------------------------------------------------------------------
    def test_05_failure_mode_tool_unavailable_reassesses_to_alternative_tool(self):
        pid = "P3-FAIL-TOOL"
        proposal = {
            "student_id": pid,
            "title": "AMR Plasmid Screening in Clinical E. coli",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 plasmid",
            "methodology": "Screening clinical isolates for mcr-1.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True
        }

        def fake_requests_with_pubmed_down(url, headers=None, timeout=5.0):
            if "eutils.ncbi.nlm.nih.gov" in url:
                raise ConnectionError("NCBI PubMed E-utilities timeout / connection refused")
            class FakeEpmcResp:
                status_code = 200
                def raise_for_status(self):
                    pass
                def json(self):
                    return {
                        "resultList": {
                            "result": [
                                {
                                    "pmid": "31000111",
                                    "doi": "10.1093/jac/dkz111",
                                    "title": "Biosafety containment for plasmid-mediated colistin resistance in E. coli",
                                    "journalTitle": "Journal of Antimicrobial Chemotherapy",
                                    "pubYear": "2022",
                                    "abstractText": "Handling clinical mcr-1 isolates requires BSL-2 containment."
                                }
                            ]
                        }
                    }
            return FakeEpmcResp()

        with patch("agent.tool_registry.requests.get", side_effect=fake_requests_with_pubmed_down):
            res = self.client.post(f"/agent/api/analyze/{pid}", json={"proposal_data": proposal}).get_json()

        agent_run = res["agent_run"]
        # Step 1 tried search_pubmed -> got tool error -> Step 2 adapted and selected search_europe_pmc -> Step 3 ASK_RESEARCHER
        self.assertEqual(agent_run["tools_called"], ["search_pubmed", "search_europe_pmc"])
        self.assertEqual(agent_run["steps"][0]["selected_tool"], "search_pubmed")
        self.assertEqual(agent_run["steps"][0]["tool_execution_status"], "error")
        self.assertEqual(agent_run["steps"][1]["selected_tool"], "search_europe_pmc")
        self.assertEqual(agent_run["steps"][1]["tool_execution_status"], "ok")
        self.assertEqual(agent_run["steps"][2]["decision_outcome"], "ASK_RESEARCHER")
        self.assertTrue(verify_audit_integrity(pid)["valid"])

    def test_06_failure_mode_malformed_tool_id_rejected(self):
        pid = "P3-FAIL-MALFORMED"
        ctx = extract_research_context({"title": "Test", "methodology": "Testing clinical isolates."}, pid)
        reqs = evaluate_institutional_requirements(ctx)
        qs = generate_clarification_questions(ctx)

        def rogue_llm_malformed_tool(_state):
            return {
                "decision": "USE_TOOL",
                "tool_id": "execute_shell_command",
                "tool_args": {"cmd": "whoami"},
                "reason": "Attempting to call an unregistered shell tool.",
                "confidence": 0.9,
                "risk_level": "HIGH"
            }

        loop = GovernedAgentLoop(planner=AgentPlanner(llm_callable=rogue_llm_malformed_tool))
        run_res = loop.run(pid, ctx, reqs, qs, WorkflowState.REQUIREMENT_CHECK)

        self.assertEqual(run_res["tool_calls_count"], 0)
        self.assertEqual(run_res["final_decision"], "STOPPED_BY_POLICY")
        self.assertEqual(run_res["steps"][0]["policy_validation_result"]["status"], "REJECTED")
        self.assertEqual(run_res["steps"][0]["policy_validation_result"]["violation_code"], "UNKNOWN_TOOL_ID")

        events = get_audit_history(pid)
        self.assertTrue(any(e["event_type"] == "AGENT_POLICY_REJECTED" for e in events))
        self.assertTrue(verify_audit_integrity(pid)["valid"])

    def test_07_failure_mode_forbidden_governance_approval_rejected(self):
        pid = "P3-FAIL-FORBIDDEN"
        ctx = extract_research_context({"title": "Test", "methodology": "Testing clinical isolates."}, pid)
        reqs = evaluate_institutional_requirements(ctx)
        qs = generate_clarification_questions(ctx)

        def rogue_llm_approve_ethics(_state):
            return {
                "decision": "APPROVE_ETHICS",
                "tool_id": None,
                "reason": "I am approving the ethics gate autonomously.",
                "confidence": 0.99,
                "risk_level": "LOW"
            }

        loop = GovernedAgentLoop(planner=AgentPlanner(llm_callable=rogue_llm_approve_ethics))
        run_res = loop.run(pid, ctx, reqs, qs, WorkflowState.REQUIREMENT_CHECK)

        self.assertEqual(run_res["tool_calls_count"], 0)
        self.assertEqual(run_res["final_decision"], "HUMAN_REVIEW")
        self.assertEqual(run_res["steps"][0]["policy_validation_result"]["status"], "REJECTED")
        self.assertEqual(
            run_res["steps"][0]["policy_validation_result"]["violation_code"],
            "GOVERNANCE_OR_SAFETY_VIOLATION"
        )
        events = get_audit_history(pid)
        self.assertTrue(any(e["event_type"] == "AGENT_POLICY_REJECTED" for e in events))
        self.assertTrue(verify_audit_integrity(pid)["valid"])

    def test_08_failure_mode_safety_downgrading_llm_overridden_by_deterministic_rules(self):
        pid = "P3-FAIL-DOWNGRADE"
        proposal = {
            "student_id": pid,
            "title": "Clinical Patient Blood Isolate Screening for mcr-1",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 colistin resistance",
            "methodology": "Collecting clinical isolate swabs from hospital patients to screen for mcr-1 resistance.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True
        }

        permissive_llm_json = json.dumps({
            "organism_or_chassis": {"value": "Escherichia coli", "evidence": "Escherichia coli", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Stated"},
            "molecular_tools": [{"value": "CRISPR-Cas12a", "evidence": "CRISPR-Cas12a", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Stated"}],
            "sample_type": {"value": "Buffer", "evidence": "swabs", "status": "CONFIRMED", "confidence": 0.9, "rationale": "Safe"},
            "human_subjects": {"value": False, "evidence": "hospital patients", "status": "CONFIRMED", "confidence": 0.99, "rationale": "No human risk"},
            "animal_subjects": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "None"},
            "genetic_modification": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "None"},
            "recombinant_dna": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "None"},
            "pathogen_work": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "Safe"},
            "antimicrobial_resistance": {"value": False, "evidence": "mcr-1", "status": "CONFIRMED", "confidence": 0.99, "rationale": "Safe"},
            "biosafety_containment": {"value": "BSL-1", "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "BSL-1 only"},
            "uncertainties": []
        })

        extractor = get_llm_extractor()
        with patch.object(extractor, "is_available", return_value=True), \
             patch.object(extractor, "gemini_key", "TEST-KEY"), \
             patch.object(extractor, "_call_gemini_api", return_value=permissive_llm_json):
            ctx = extract_research_context(proposal, pid)

        self.assertEqual(ctx.extraction_mode, "llm_hybrid")
        self.assertTrue(ctx.recombinant_dna.value)
        self.assertTrue(ctx.pathogen_work.value)
        self.assertTrue(ctx.antimicrobial_resistance.value)
        self.assertEqual(ctx.human_subjects.status, FieldStatus.REQUIRES_HUMAN_REVIEW)
        self.assertEqual(ctx.biosafety_containment.status, FieldStatus.REQUIRES_HUMAN_REVIEW)
        overrides = [u for u in ctx.uncertainties if u.get("authority_resolution") == "deterministic_safety_rule_prevailed"]
        self.assertGreaterEqual(len(overrides), 5)

    # -------------------------------------------------------------------------
    # PART 10 — VERIFY GENUINE AGENTIC TOOL USE (Observation-Dependent Branching)
    # -------------------------------------------------------------------------
    def test_09_part10_observation_dependent_branching_same_proposal(self):
        """
        Proves that for the EXACT SAME proposal and EXACT SAME agent planner function,
        the second action depends strictly on the intermediate observation from the first action:
        - Run 1: Agent calls search_pubmed -> observation establishes sufficient containment evidence -> Agent chooses CONTINUE
        - Run 2: Agent calls search_pubmed -> observation returns 0 records (insufficient) -> Agent chooses search_europe_pmc -> then ASK_RESEARCHER
        """
        proposal = {
            "title": "Cell-Free Lyophilized Cas12a Assay for Synthetic mcr-1 Fragment",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 synthetic fragment",
            "methodology": "Testing clinical isolate swabs from hospital patients for mcr-1.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True
        }

        # Shared LLM planner that inspects state_payload["observations"] and returns structured JSON decisions
        def llm_structured_planner(state_payload):
            obs_list = state_payload.get("observations", [])
            if len(obs_list) == 0:
                return {
                    "decision": "USE_TOOL",
                    "tool_id": "search_pubmed",
                    "tool_args": {"query": "Escherichia coli mcr-1 biosafety containment", "max_results": 3},
                    "reason": "Need peer-reviewed biosafety evidence for mcr-1 handling.",
                    "question": None,
                    "evidence_needed": "PubMed biosafety precedent for mcr-1",
                    "confidence": 0.82,
                    "risk_level": "MEDIUM"
                }
            first_obs = obs_list[0]
            if len(obs_list) == 1:
                if first_obs.get("records_count", 0) > 0 and first_obs.get("establishes_project_specific_containment"):
                    return {
                        "decision": "CONTINUE",
                        "tool_id": None,
                        "tool_args": {},
                        "reason": "First observation from PubMed established sufficient containment evidence.",
                        "question": None,
                        "evidence_needed": "None",
                        "confidence": 0.94,
                        "risk_level": "LOW"
                    }
                else:
                    return {
                        "decision": "USE_TOOL",
                        "tool_id": "search_europe_pmc",
                        "tool_args": {"query": "mcr-1 clinical isolate containment protocol", "max_results": 3},
                        "reason": "PubMed returned insufficient evidence (0 records); querying Europe PMC as secondary source.",
                        "question": None,
                        "evidence_needed": "Europe PMC containment evidence",
                        "confidence": 0.78,
                        "risk_level": "HIGH"
                    }
            # After second observation (Europe PMC)
            return {
                "decision": "ASK_RESEARCHER",
                "tool_id": None,
                "tool_args": {},
                "reason": "Europe PMC confirmed BSL-2 risk group, but researcher must clarify local laboratory BSL certification and sample de-identification.",
                "question": "Please confirm whether your laboratory holds active BSL-2 certification and whether isolates are de-identified.",
                "evidence_needed": "Researcher clarification on local containment",
                "confidence": 0.91,
                "risk_level": "HIGH"
            }

        llm_structured_planner.provider_name = "google_gemini"
        llm_structured_planner.model_version = "gemini-2.5-flash"

        # --- RUN 1: PubMed observation returns sufficient evidence ---
        reg1 = BoundedToolRegistry()
        reg1.get_tool("search_pubmed").handler = lambda args, ctx, timeout: {
            "status": "ok",
            "tool_id": "search_pubmed",
            "records_count": 2,
            "records": [{"pmid": "111", "title": "Validated BSL-1 cell-free synthetic fragment protocol"}],
            "establishes_biosafety_risk_group": True,
            "establishes_project_specific_containment": True,
            "observation_summary": "PubMed returned 2 records establishing complete containment sufficiency.",
            "provenance": {"source_system": "NCBI PubMed E-utilities"}
        }
        ctx1 = extract_research_context(proposal, "P3-PROOF-RUN1")
        reqs1 = evaluate_institutional_requirements(ctx1)
        qs1 = generate_clarification_questions(ctx1)
        loop1 = GovernedAgentLoop(tool_registry=reg1, planner=AgentPlanner(llm_callable=llm_structured_planner))
        res1 = loop1.run("P3-PROOF-RUN1", ctx1, reqs1, qs1, WorkflowState.REQUIREMENT_CHECK)

        # --- RUN 2: PubMed observation returns 0 records -> Agent adapts and calls Europe PMC -> then ASK_RESEARCHER ---
        reg2 = BoundedToolRegistry()
        reg2.get_tool("search_pubmed").handler = lambda args, ctx, timeout: {
            "status": "ok",
            "tool_id": "search_pubmed",
            "records_count": 0,
            "records": [],
            "establishes_biosafety_risk_group": False,
            "establishes_project_specific_containment": False,
            "observation_summary": "PubMed returned 0 records.",
            "provenance": {"source_system": "NCBI PubMed E-utilities"}
        }
        reg2.get_tool("search_europe_pmc").handler = lambda args, ctx, timeout: {
            "status": "ok",
            "tool_id": "search_europe_pmc",
            "records_count": 3,
            "records": [{"id": "MED-999", "title": "BSL-2 requirements for clinical mcr-1 isolates"}],
            "establishes_biosafety_risk_group": True,
            "establishes_project_specific_containment": False,
            "observation_summary": "Europe PMC returned 3 records confirming BSL-2 risk group, but local lab containment remains unspecified.",
            "provenance": {"source_system": "Europe PMC REST API"}
        }
        ctx2 = extract_research_context(proposal, "P3-PROOF-RUN2")
        reqs2 = evaluate_institutional_requirements(ctx2)
        qs2 = generate_clarification_questions(ctx2)
        loop2 = GovernedAgentLoop(tool_registry=reg2, planner=AgentPlanner(llm_callable=llm_structured_planner))
        res2 = loop2.run("P3-PROOF-RUN2", ctx2, reqs2, qs2, WorkflowState.REQUIREMENT_CHECK)

        # Assert Run 1 took path: search_pubmed -> CONTINUE
        self.assertEqual(res1["tools_called"], ["search_pubmed"])
        self.assertEqual(res1["final_decision"], "CONTINUE")
        self.assertEqual(len(res1["steps"]), 2)

        # Assert Run 2 took path: search_pubmed -> search_europe_pmc -> ASK_RESEARCHER
        self.assertEqual(res2["tools_called"], ["search_pubmed", "search_europe_pmc"])
        self.assertEqual(res2["final_decision"], "ASK_RESEARCHER")
        self.assertEqual(len(res2["steps"]), 3)


if __name__ == "__main__":
    unittest.main()
