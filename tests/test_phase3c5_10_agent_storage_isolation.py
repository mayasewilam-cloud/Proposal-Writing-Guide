"""
BioWriter Studio — Phase 3C.5.10: Agent Subsystem Data Directory Isolation Verification Suite.

Validates that:
1. Agent audit directory respects BIOWRITER_DATA_DIR.
2. Agent context directory respects BIOWRITER_DATA_DIR.
3. Agent state directory respects BIOWRITER_DATA_DIR.
4. Default paths remain unchanged when the environment variable is absent.
5. Missing configured temporary directories do not trigger fallback to live storage.
6. Agent audit writes occur only in temporary storage.
7. Agent context writes occur only in temporary storage.
8. Agent state writes occur only in temporary storage.
9. Cleanup functions operate only within the configured temporary directory.
10. Environment and module-level path restoration works after tests.
11. Import-order variations do not produce stale or inconsistent storage paths.
12. Existing Agent workflow functionality remains intact.
13. Repaired test_agent_workflow.py execution produces zero writes to live storage.
14. Repaired test_phase3_governed_agent_loop.py execution produces zero writes to live storage.
"""

import os
import sys
import json
import shutil
import hashlib
import tempfile
import unittest
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"
os.environ["TESTING"] = "1"

from agent.audit import (
    get_agent_audit_dir,
    get_agent_data_dir,
    record_audit_event,
    get_audit_history,
    verify_audit_integrity
)
from agent.service import (
    get_agent_context_dir,
    AgentOrchestrator
)
from agent.workflow import (
    get_agent_state_dir,
    load_workflow_state,
    save_workflow_state,
    transition_state,
    can_transition,
    WorkflowState,
    WorkflowError
)


def _snapshot_dir(dir_path: str):
    """Computes a SHA-256 fingerprint dictionary of all files in a directory."""
    manifest = {}
    if not os.path.exists(dir_path):
        return manifest
    for root, _, files in os.walk(dir_path):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dir_path).replace("\\", "/")
            h = hashlib.sha256()
            try:
                with open(p, "rb") as fh:
                    while chunk := fh.read(65536):
                        h.update(chunk)
                manifest[rel] = h.hexdigest()
            except Exception:
                pass
    return manifest


class TestPhase3C510AgentStorageIsolation(unittest.TestCase):
    """Comprehensive regression suite for Agent subsystem storage isolation."""

    def setUp(self):
        self._orig_env = os.environ.get("BIOWRITER_DATA_DIR")
        self.tmp_dir = tempfile.mkdtemp(prefix="biowriter_test_p3c510_")
        self.live_data_dir = os.path.abspath(os.path.join(BASE_DIR, "data"))

    def tearDown(self):
        if self._orig_env is None:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        else:
            os.environ["BIOWRITER_DATA_DIR"] = self._orig_env
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Test 1: Agent audit directory respects BIOWRITER_DATA_DIR
    # -------------------------------------------------------------------------
    def test_01_agent_audit_dir_respects_biowriter_data_dir(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        audit_dir = get_agent_audit_dir()
        expected = os.path.abspath(os.path.join(self.tmp_dir, "agent_audit"))
        self.assertEqual(os.path.abspath(audit_dir), expected)
        self.assertTrue(os.path.isdir(audit_dir))
        self.assertFalse(audit_dir.startswith(self.live_data_dir))

    # -------------------------------------------------------------------------
    # Test 2: Agent context directory respects BIOWRITER_DATA_DIR
    # -------------------------------------------------------------------------
    def test_02_agent_context_dir_respects_biowriter_data_dir(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        ctx_dir = get_agent_context_dir()
        expected = os.path.abspath(os.path.join(self.tmp_dir, "agent_context"))
        self.assertEqual(os.path.abspath(ctx_dir), expected)
        self.assertTrue(os.path.isdir(ctx_dir))
        self.assertFalse(ctx_dir.startswith(self.live_data_dir))

    # -------------------------------------------------------------------------
    # Test 3: Agent state directory respects BIOWRITER_DATA_DIR
    # -------------------------------------------------------------------------
    def test_03_agent_state_dir_respects_biowriter_data_dir(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        state_dir = get_agent_state_dir()
        expected = os.path.abspath(os.path.join(self.tmp_dir, "agent_state"))
        self.assertEqual(os.path.abspath(state_dir), expected)
        self.assertTrue(os.path.isdir(state_dir))
        self.assertFalse(state_dir.startswith(self.live_data_dir))

    # -------------------------------------------------------------------------
    # Test 4: Default paths remain unchanged when environment variable absent
    # -------------------------------------------------------------------------
    def test_04_default_paths_remain_unchanged_when_env_absent(self):
        os.environ.pop("BIOWRITER_DATA_DIR", None)
        expected_audit = os.path.abspath(os.path.join(self.live_data_dir, "agent_audit"))
        expected_ctx = os.path.abspath(os.path.join(self.live_data_dir, "agent_context"))
        expected_state = os.path.abspath(os.path.join(self.live_data_dir, "agent_state"))

        self.assertEqual(os.path.abspath(get_agent_audit_dir()), expected_audit)
        self.assertEqual(os.path.abspath(get_agent_context_dir()), expected_ctx)
        self.assertEqual(os.path.abspath(get_agent_state_dir()), expected_state)

    # -------------------------------------------------------------------------
    # Test 5: Missing configured temporary directories do not trigger fallback
    # -------------------------------------------------------------------------
    def test_05_missing_configured_temp_dir_does_not_fallback(self):
        nonexistent = os.path.join(self.tmp_dir, "sub", "nonexistent_storage_path")
        self.assertFalse(os.path.exists(nonexistent))
        os.environ["BIOWRITER_DATA_DIR"] = nonexistent

        audit_dir = get_agent_audit_dir()
        ctx_dir = get_agent_context_dir()
        state_dir = get_agent_state_dir()

        # Directories must be created under the configured path and NOT fall back to live data
        self.assertTrue(os.path.abspath(audit_dir).startswith(os.path.abspath(nonexistent)))
        self.assertTrue(os.path.abspath(ctx_dir).startswith(os.path.abspath(nonexistent)))
        self.assertTrue(os.path.abspath(state_dir).startswith(os.path.abspath(nonexistent)))

        self.assertFalse(os.path.abspath(audit_dir).startswith(self.live_data_dir))
        self.assertFalse(os.path.abspath(ctx_dir).startswith(self.live_data_dir))
        self.assertFalse(os.path.abspath(state_dir).startswith(self.live_data_dir))

    # -------------------------------------------------------------------------
    # Test 6: Agent audit writes occur only in temporary storage
    # -------------------------------------------------------------------------
    def test_06_agent_audit_writes_occur_only_in_temp_storage(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-AUDIT-ISOLATION-01"

        record_audit_event(
            project_id=synth_pid,
            event_type="TEST_ISOLATION_EVENT",
            actor="agent",
            actor_id="test_runner",
            action="Verify zero write to live storage",
            workflow_state=WorkflowState.DRAFT
        )

        temp_audit_file = os.path.join(self.tmp_dir, "agent_audit", f"{synth_pid}.jsonl")
        live_audit_file = os.path.join(self.live_data_dir, "agent_audit", f"{synth_pid}.jsonl")

        self.assertTrue(os.path.exists(temp_audit_file), "Audit record must exist in temp directory.")
        self.assertFalse(os.path.exists(live_audit_file), "Audit record must NEVER exist in live directory.")

        # Verify integrity in temp directory
        integ = verify_audit_integrity(synth_pid)
        self.assertTrue(integ["valid"])
        self.assertEqual(integ["event_count"], 1)

    # -------------------------------------------------------------------------
    # Test 7: Agent context writes occur only in temporary storage
    # -------------------------------------------------------------------------
    def test_07_agent_context_writes_occur_only_in_temp_storage(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-CTX-ISOLATION-01"

        orchestrator = AgentOrchestrator()
        synth_proposal = {
            "student_id": synth_pid,
            "title": "Synthetic Isolation Test Proposal",
            "chassis": "Cell-free in vitro system",
            "tool": "Synthetic Aptamer",
            "target": "Fluorophore detection",
            "methodology": "Standard in vitro fluorescence assay."
        }

        res = orchestrator.analyze_proposal(synth_proposal, project_id=synth_pid)
        self.assertIn("workflow_state", res)

        temp_ctx_file = os.path.join(self.tmp_dir, "agent_context", f"{synth_pid}.json")
        live_ctx_file = os.path.join(self.live_data_dir, "agent_context", f"{synth_pid}.json")

        self.assertTrue(os.path.exists(temp_ctx_file), "Context file must exist in temp directory.")
        self.assertFalse(os.path.exists(live_ctx_file), "Context file must NEVER exist in live directory.")

    # -------------------------------------------------------------------------
    # Test 8: Agent state writes occur only in temporary storage
    # -------------------------------------------------------------------------
    def test_08_agent_state_writes_occur_only_in_temp_storage(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-STATE-ISOLATION-01"

        save_workflow_state(synth_pid, {
            "project_id": synth_pid,
            "current_state": WorkflowState.REQUIREMENT_CHECK,
            "previous_state": WorkflowState.CONTEXT_ANALYSIS,
            "pending_clarifications": []
        })

        temp_state_file = os.path.join(self.tmp_dir, "agent_state", f"{synth_pid}.json")
        live_state_file = os.path.join(self.live_data_dir, "agent_state", f"{synth_pid}.json")

        self.assertTrue(os.path.exists(temp_state_file), "State file must exist in temp directory.")
        self.assertFalse(os.path.exists(live_state_file), "State file must NEVER exist in live directory.")

        loaded = load_workflow_state(synth_pid)
        self.assertEqual(loaded["current_state"], WorkflowState.REQUIREMENT_CHECK)

    # -------------------------------------------------------------------------
    # Test 9: Cleanup functions operate only within configured temporary directory
    # -------------------------------------------------------------------------
    def test_09_cleanup_functions_operate_only_within_temp_dir(self):
        from tests.test_phase3_governed_agent_loop import cleanup_project_artifacts

        # 1. When in temp directory, cleanup successfully removes files
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-CLEANUP-01"

        save_workflow_state(synth_pid, {"project_id": synth_pid, "current_state": WorkflowState.DRAFT})
        record_audit_event(synth_pid, "DRAFT_SAVED", "agent", "orch", "Action", WorkflowState.DRAFT)
        t_state = os.path.join(self.tmp_dir, "agent_state", f"{synth_pid}.json")
        t_audit = os.path.join(self.tmp_dir, "agent_audit", f"{synth_pid}.jsonl")
        self.assertTrue(os.path.exists(t_state))
        self.assertTrue(os.path.exists(t_audit))

        cleanup_project_artifacts(synth_pid)
        self.assertFalse(os.path.exists(t_state))
        self.assertFalse(os.path.exists(t_audit))

        # 2. When BIOWRITER_DATA_DIR points to live data or is absent, cleanup strictly blocks
        os.environ.pop("BIOWRITER_DATA_DIR", None)
        # Verify that calling cleanup does not crash and does not delete anything from live data
        live_exemplar = "13989"
        live_audit = os.path.join(self.live_data_dir, "agent_audit", f"{live_exemplar}.jsonl")
        if os.path.exists(live_audit):
            cleanup_project_artifacts(live_exemplar)
            self.assertTrue(os.path.exists(live_audit), "Cleanup MUST NOT touch live data files!")

    # -------------------------------------------------------------------------
    # Test 10: Environment and path restoration works after tests
    # -------------------------------------------------------------------------
    def test_10_environment_and_path_restoration(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        self.assertEqual(os.path.abspath(get_agent_audit_dir()), os.path.abspath(os.path.join(self.tmp_dir, "agent_audit")))

        os.environ.pop("BIOWRITER_DATA_DIR", None)
        self.assertEqual(os.path.abspath(get_agent_audit_dir()), os.path.abspath(os.path.join(self.live_data_dir, "agent_audit")))

    # -------------------------------------------------------------------------
    # Test 11: Import-order variations do not produce stale or inconsistent paths
    # -------------------------------------------------------------------------
    def test_11_import_order_variations(self):
        tmp_target = os.path.abspath(self.tmp_dir)

        code_wf_first = f"""
import os, sys
sys.path.insert(0, r"{BASE_DIR}")
os.environ["BIOWRITER_DATA_DIR"] = r"{tmp_target}"
from agent.workflow import get_agent_state_dir
from agent.service import get_agent_context_dir
from agent.audit import get_agent_audit_dir
print(os.path.abspath(get_agent_state_dir()))
print(os.path.abspath(get_agent_context_dir()))
print(os.path.abspath(get_agent_audit_dir()))
"""

        code_audit_first = f"""
import os, sys
sys.path.insert(0, r"{BASE_DIR}")
os.environ["BIOWRITER_DATA_DIR"] = r"{tmp_target}"
from agent.audit import get_agent_audit_dir
from agent.workflow import get_agent_state_dir
from agent.service import get_agent_context_dir
print(os.path.abspath(get_agent_state_dir()))
print(os.path.abspath(get_agent_context_dir()))
print(os.path.abspath(get_agent_audit_dir()))
"""

        code_service_first = f"""
import os, sys
sys.path.insert(0, r"{BASE_DIR}")
os.environ["BIOWRITER_DATA_DIR"] = r"{tmp_target}"
from agent.service import get_agent_context_dir
from agent.audit import get_agent_audit_dir
from agent.workflow import get_agent_state_dir
print(os.path.abspath(get_agent_state_dir()))
print(os.path.abspath(get_agent_context_dir()))
print(os.path.abspath(get_agent_audit_dir()))
"""

        p1 = subprocess.run([sys.executable, "-c", code_wf_first], capture_output=True, text=True)
        p2 = subprocess.run([sys.executable, "-c", code_audit_first], capture_output=True, text=True)
        p3 = subprocess.run([sys.executable, "-c", code_service_first], capture_output=True, text=True)

        self.assertEqual(p1.returncode, 0, f"Process 1 failed: {p1.stderr}")
        self.assertEqual(p2.returncode, 0, f"Process 2 failed: {p2.stderr}")
        self.assertEqual(p3.returncode, 0, f"Process 3 failed: {p3.stderr}")

        out1 = p1.stdout.strip().splitlines()
        out2 = p2.stdout.strip().splitlines()
        out3 = p3.stdout.strip().splitlines()

        self.assertEqual(out1, out2)
        self.assertEqual(out2, out3)
        self.assertEqual(out1[0], os.path.abspath(os.path.join(tmp_target, "agent_state")))
        self.assertEqual(out1[1], os.path.abspath(os.path.join(tmp_target, "agent_context")))
        self.assertEqual(out1[2], os.path.abspath(os.path.join(tmp_target, "agent_audit")))

    # -------------------------------------------------------------------------
    # Test 12: Existing Agent workflow functionality remains intact
    # -------------------------------------------------------------------------
    def test_12_existing_agent_workflow_functionality_intact(self):
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-WORKFLOW-INTACT-01"

        orchestrator = AgentOrchestrator()
        proposal = {
            "student_id": synth_pid,
            "title": "Synthetic Dual Use Risk Assessment Proposal",
            "chassis": "Vibrio natriegens",
            "tool": "CRISPR-Cas12a",
            "target": "Antimicrobial resistance marker excision",
            "methodology": "Markerless deletion of beta-lactamase gene to ensure biocontainment.",
            "pathogen_work": False,
            "recombinant_dna": True
        }

        # Step 1: Initial analysis
        analysis = orchestrator.analyze_proposal(proposal, project_id=synth_pid)
        self.assertIn("workflow_state", analysis)
        self.assertIn("requirements", analysis)

        # Step 2: Valid legal state transitions
        curr_state = analysis.get("workflow_state", WorkflowState.DRAFT)
        if curr_state == WorkflowState.NEEDS_CLARIFICATION:
            transition_state(synth_pid, WorkflowState.REQUIREMENT_CHECK, actor="agent")
            curr_state = WorkflowState.REQUIREMENT_CHECK
        if curr_state == WorkflowState.REQUIREMENT_CHECK:
            state_data, ok = transition_state(synth_pid, WorkflowState.READY_FOR_ETHICS_HANDOFF, actor="agent")
            self.assertTrue(ok)
            self.assertEqual(state_data["current_state"], WorkflowState.READY_FOR_ETHICS_HANDOFF)

        # Step 3: Record audit events and verify tamper detection
        record_audit_event(synth_pid, "ETHICS_HANDOFF", "agent", "orchestrator", "Handoff to review", WorkflowState.READY_FOR_ETHICS_HANDOFF)
        integ = verify_audit_integrity(synth_pid)
        self.assertTrue(integ["valid"])
        self.assertGreaterEqual(integ["event_count"], 2)

    # -------------------------------------------------------------------------
    # Test 13: Repaired test_agent_workflow.py writes zero files to live storage
    # -------------------------------------------------------------------------
    def test_13_repaired_test_agent_workflow_zero_live_writes(self):
        snap_before = _snapshot_dir(self.live_data_dir)

        test_env = {
            **os.environ,
            "FLASK_TESTING": "1",
            "SECRET_KEY": "biowriter-test-secret-key-32chars-min-len!!",
            "TESTING": "1"
        }
        cmd = [sys.executable, "-m", "unittest", "tests.test_agent_workflow"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, env=test_env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"test_agent_workflow failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        snap_after = _snapshot_dir(self.live_data_dir)

        added = set(snap_after.keys()) - set(snap_before.keys())
        removed = set(snap_before.keys()) - set(snap_after.keys())
        changed = [k for k in snap_before if k in snap_after and snap_before[k] != snap_after[k]]

        self.assertEqual(len(added), 0, f"Live storage had unexpected added files: {added}")
        self.assertEqual(len(removed), 0, f"Live storage had unexpected removed files: {removed}")
        self.assertEqual(len(changed), 0, f"Live storage had modified files: {changed}")

    # -------------------------------------------------------------------------
    # Test 14: Repaired test_phase3_governed_agent_loop.py writes zero files to live storage
    # -------------------------------------------------------------------------
    def test_14_repaired_governed_agent_loop_zero_live_writes(self):
        snap_before = _snapshot_dir(self.live_data_dir)

        test_env = {
            **os.environ,
            "FLASK_TESTING": "1",
            "SECRET_KEY": "biowriter-test-secret-key-32chars-min-len!!",
            "TESTING": "1"
        }
        cmd = [sys.executable, "-m", "unittest", "tests.test_phase3_governed_agent_loop"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, env=test_env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"test_phase3_governed_agent_loop failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        snap_after = _snapshot_dir(self.live_data_dir)

        added = set(snap_after.keys()) - set(snap_before.keys())
        removed = set(snap_before.keys()) - set(snap_after.keys())
        changed = [k for k in snap_before if k in snap_after and snap_before[k] != snap_after[k]]

        self.assertEqual(len(added), 0, f"Live storage had unexpected added files: {added}")
        self.assertEqual(len(removed), 0, f"Live storage had unexpected removed files: {removed}")
        self.assertEqual(len(changed), 0, f"Live storage had modified files: {changed}")


if __name__ == "__main__":
    unittest.main()
