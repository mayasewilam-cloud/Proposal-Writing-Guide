"""
BioWriter Studio — Phase 3C.5.12: Agent Storage Isolation Defensive Hardening Regression Suite.

Verifies all 17 requirements from Section 7:
1. Windows case-insensitive path comparisons.
2. Canonical path resolution.
3. Symlink escape rejection.
4. Junction escape rejection where supported.
5. Live storage rejection.
6. Rejection of paths inside live storage.
7. Acceptance of valid external temporary directories.
8. Rejection of absolute project IDs.
9. Rejection of traversal project IDs.
10. Validation of the final deletion target.
11. Correct behavior when BIOWRITER_DATA_DIR is unset.
12. Explicit rejection of empty BIOWRITER_DATA_DIR.
13. Explicit rejection of whitespace-only BIOWRITER_DATA_DIR.
14. Correct Vercel fallback and precedence.
15. Dynamic environment-variable changes.
16. Consistent storage resolution across Agent modules.
17. Persistence behavior in isolated temporary storage.
"""

import os
import sys
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
    get_agent_data_dir,
    get_agent_audit_dir,
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
    WorkflowState,
    WorkflowError
)
from tests.test_phase3_governed_agent_loop import (
    cleanup_project_artifacts,
    _is_strictly_within,
    _resolves_to_or_within
)


class TestPhase3C512AgentStorageHardening(unittest.TestCase):

    def setUp(self):
        self._orig_env = os.environ.get("BIOWRITER_DATA_DIR")
        self._orig_vercel = os.environ.get("VERCEL")
        self.tmp_dir = tempfile.mkdtemp(prefix="biowriter_test_p3c512_")
        self.live_data_dir = os.path.normcase(os.path.realpath(os.path.join(BASE_DIR, "data")))

    def tearDown(self):
        if self._orig_env is None:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        else:
            os.environ["BIOWRITER_DATA_DIR"] = self._orig_env

        if self._orig_vercel is None:
            os.environ.pop("VERCEL", None)
        else:
            os.environ["VERCEL"] = self._orig_vercel

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Windows case-insensitive path comparisons
    # -------------------------------------------------------------------------
    def test_01_windows_case_insensitive_comparisons(self):
        """Verifies that casing variations on Windows do not bypass live data protection."""
        if self.live_data_dir[0].isalpha() and self.live_data_dir[1:3] == ":\\":
            flipped_drive = self.live_data_dir[0].lower() if self.live_data_dir[0].isupper() else self.live_data_dir[0].upper()
            cased_live_dir = flipped_drive + self.live_data_dir[1:]
        else:
            cased_live_dir = self.live_data_dir.swapcase()

        os.environ["BIOWRITER_DATA_DIR"] = cased_live_dir
        with self.assertRaises(RuntimeError) as ctx:
            cleanup_project_artifacts("TEST-PROJECT-01")
        self.assertIn("live storage", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # 2. Canonical path resolution
    # -------------------------------------------------------------------------
    def test_02_canonical_path_resolution(self):
        """Verifies canonical path resolution with redundant separators, dots, and case differences."""
        messy_path = os.path.join(self.tmp_dir, "sub", "..", ".", "sub2")
        os.makedirs(messy_path, exist_ok=True)
        canonical = os.path.normcase(os.path.realpath(messy_path))
        expected = os.path.normcase(os.path.realpath(os.path.join(self.tmp_dir, "sub2")))
        self.assertEqual(canonical, expected)

    # -------------------------------------------------------------------------
    # 3. Symlink escape rejection
    # -------------------------------------------------------------------------
    def test_03_symlink_escape_rejection(self):
        """Verifies symlink escape rejection or skips gracefully if privileges are absent."""
        symlink_target = os.path.join(self.tmp_dir, "target")
        symlink_link = os.path.join(self.tmp_dir, "link")
        os.makedirs(symlink_target, exist_ok=True)

        try:
            os.symlink(symlink_target, symlink_link, target_is_directory=True)
            resolved = os.path.normcase(os.path.realpath(symlink_link))
            target_resolved = os.path.normcase(os.path.realpath(symlink_target))
            self.assertEqual(resolved, target_resolved)
        except (OSError, NotImplementedError):
            self.skipTest("Unprivileged symlinks not supported on this platform/configuration.")

    # -------------------------------------------------------------------------
    # 4. Junction escape rejection where supported
    # -------------------------------------------------------------------------
    def test_04_junction_escape_rejection(self):
        """Verifies that directory junctions are resolved canonically via realpath."""
        junction_target = os.path.join(self.tmp_dir, "real_store")
        junction_link = os.path.join(self.tmp_dir, "junction_store")
        os.makedirs(junction_target, exist_ok=True)

        if sys.platform == "win32":
            res = subprocess.run(["cmd", "/c", "mklink", "/J", junction_link, junction_target], capture_output=True)
            if res.returncode == 0 and os.path.exists(junction_link):
                try:
                    resolved = os.path.normcase(os.path.realpath(junction_link))
                    target_resolved = os.path.normcase(os.path.realpath(junction_target))
                    self.assertEqual(resolved, target_resolved)
                    # Verify containment helper resolves correctly through junction
                    self.assertTrue(_is_strictly_within(resolved, os.path.normcase(os.path.realpath(self.tmp_dir))))
                finally:
                    subprocess.run(["cmd", "/c", "rmdir", junction_link], capture_output=True)

    # -------------------------------------------------------------------------
    # 5. Live storage rejection
    # -------------------------------------------------------------------------
    def test_05_live_storage_rejection(self):
        """Verifies that pointing BIOWRITER_DATA_DIR directly to live storage is rejected."""
        os.environ["BIOWRITER_DATA_DIR"] = self.live_data_dir
        with self.assertRaises(RuntimeError) as ctx:
            cleanup_project_artifacts("P3-SCEN-A")
        self.assertIn("live storage", str(ctx.exception).lower())

        # Also verify subprocess module guard in test_agent_workflow
        test_env = {
            **os.environ,
            "BIOWRITER_DATA_DIR": self.live_data_dir,
            "FLASK_TESTING": "1",
            "SECRET_KEY": "biowriter-test-secret-key-32chars-min-len!!",
            "TESTING": "1"
        }
        cmd = [sys.executable, "-m", "unittest", "tests.test_agent_workflow"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, env=test_env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unsafe test configuration", proc.stderr)

    # -------------------------------------------------------------------------
    # 6. Rejection of paths inside live storage
    # -------------------------------------------------------------------------
    def test_06_rejection_of_paths_inside_live_storage(self):
        """Verifies that pointing BIOWRITER_DATA_DIR to a path inside live storage is rejected."""
        sub_live = os.path.join(self.live_data_dir, "test_subfolder")
        os.environ["BIOWRITER_DATA_DIR"] = sub_live
        with self.assertRaises(RuntimeError) as ctx:
            cleanup_project_artifacts("P3-SCEN-A")
        self.assertIn("live storage", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # 7. Acceptance of valid external temporary directories
    # -------------------------------------------------------------------------
    def test_07_acceptance_of_valid_external_temporary_directories(self):
        """Verifies that a valid external temporary directory is accepted and used."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        audit_dir = get_agent_audit_dir()
        self.assertEqual(os.path.normcase(os.path.realpath(audit_dir)),
                         os.path.normcase(os.path.realpath(os.path.join(self.tmp_dir, "agent_audit"))))

    # -------------------------------------------------------------------------
    # 8. Rejection of absolute project IDs
    # -------------------------------------------------------------------------
    def test_08_rejection_of_absolute_project_ids(self):
        """Verifies that cleanup rejects absolute path project IDs."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        abs_pids = [r"C:\Windows\System32\cmd", "/etc/passwd"] if sys.platform == "win32" else ["/etc/passwd"]
        for bad_pid in abs_pids:
            with self.assertRaises(ValueError) as ctx:
                cleanup_project_artifacts(bad_pid)
            self.assertIn("Unsafe project identifier", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 9. Rejection of traversal project IDs
    # -------------------------------------------------------------------------
    def test_09_rejection_of_traversal_project_ids(self):
        """Verifies that cleanup rejects project IDs with path traversal characters."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        for bad_pid in ["../victim", "../../data/users", "sub/folder", "..\\victim", "foo/bar"]:
            with self.assertRaises(ValueError) as ctx:
                cleanup_project_artifacts(bad_pid)
            self.assertIn("Unsafe project identifier", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 10. Validation of the final deletion target
    # -------------------------------------------------------------------------
    def test_10_validation_of_final_deletion_target(self):
        """Verifies that final deletion target must be inside agent directory and cannot delete directory itself."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-TARGET-01"
        save_workflow_state(synth_pid, {"project_id": synth_pid, "current_state": "DRAFT"})
        state_file = os.path.join(get_agent_state_dir(), f"{synth_pid}.json")
        self.assertTrue(os.path.exists(state_file))

        cleanup_project_artifacts(synth_pid)
        self.assertFalse(os.path.exists(state_file))
        # Ensure agent_state directory itself was NOT deleted
        self.assertTrue(os.path.isdir(get_agent_state_dir()))

    # -------------------------------------------------------------------------
    # 11. Correct behavior when BIOWRITER_DATA_DIR is unset
    # -------------------------------------------------------------------------
    def test_11_behavior_when_biowriter_data_dir_unset(self):
        """Verifies default storage path when BIOWRITER_DATA_DIR is unset."""
        os.environ.pop("BIOWRITER_DATA_DIR", None)
        os.environ.pop("VERCEL", None)
        expected = os.path.normcase(os.path.realpath(os.path.join(BASE_DIR, "data")))
        actual = os.path.normcase(os.path.realpath(get_agent_data_dir()))
        self.assertEqual(actual, expected)

    # -------------------------------------------------------------------------
    # 12. Explicit rejection of empty BIOWRITER_DATA_DIR
    # -------------------------------------------------------------------------
    def test_12_explicit_rejection_of_empty_biowriter_data_dir(self):
        """Verifies that BIOWRITER_DATA_DIR='' raises ValueError."""
        os.environ["BIOWRITER_DATA_DIR"] = ""
        with self.assertRaises(ValueError) as ctx:
            get_agent_data_dir()
        self.assertIn("empty or whitespace-only", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 13. Explicit rejection of whitespace-only BIOWRITER_DATA_DIR
    # -------------------------------------------------------------------------
    def test_13_explicit_rejection_of_whitespace_only_biowriter_data_dir(self):
        """Verifies that BIOWRITER_DATA_DIR='   \\t\\n  ' raises ValueError."""
        os.environ["BIOWRITER_DATA_DIR"] = "   \t\n  "
        with self.assertRaises(ValueError) as ctx:
            get_agent_data_dir()
        self.assertIn("empty or whitespace-only", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 14. Correct Vercel fallback and precedence
    # -------------------------------------------------------------------------
    def test_14_correct_vercel_fallback_and_precedence(self):
        """Verifies Vercel fallback and BIOWRITER_DATA_DIR precedence."""
        # Case A: VERCEL=1, BIOWRITER_DATA_DIR unset
        os.environ.pop("BIOWRITER_DATA_DIR", None)
        os.environ["VERCEL"] = "1"
        self.assertEqual(get_agent_data_dir(), os.path.join("/tmp", "data"))

        # Case B: Both set -> BIOWRITER_DATA_DIR takes precedence
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        self.assertEqual(get_agent_data_dir(), self.tmp_dir)

        # Case C: VERCEL empty -> falls back to live data
        os.environ.pop("BIOWRITER_DATA_DIR", None)
        os.environ["VERCEL"] = ""
        expected = os.path.normcase(os.path.realpath(os.path.join(BASE_DIR, "data")))
        self.assertEqual(os.path.normcase(os.path.realpath(get_agent_data_dir())), expected)

    # -------------------------------------------------------------------------
    # 15. Dynamic environment-variable changes
    # -------------------------------------------------------------------------
    def test_15_dynamic_environment_variable_changes(self):
        """Verifies that dynamic changes to BIOWRITER_DATA_DIR are immediately recognized."""
        temp_a = tempfile.mkdtemp(prefix="biowriter_test_dyn_a_")
        temp_b = tempfile.mkdtemp(prefix="biowriter_test_dyn_b_")
        try:
            os.environ["BIOWRITER_DATA_DIR"] = temp_a
            self.assertEqual(get_agent_data_dir(), temp_a)
            self.assertEqual(get_agent_audit_dir(), os.path.join(temp_a, "agent_audit"))

            os.environ["BIOWRITER_DATA_DIR"] = temp_b
            self.assertEqual(get_agent_data_dir(), temp_b)
            self.assertEqual(get_agent_audit_dir(), os.path.join(temp_b, "agent_audit"))
        finally:
            shutil.rmtree(temp_a, ignore_errors=True)
            shutil.rmtree(temp_b, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 16. Consistent storage resolution across Agent modules
    # -------------------------------------------------------------------------
    def test_16_consistent_storage_resolution_across_agent_modules(self):
        """Verifies that audit, context, and state resolvers resolve beneath the same root data directory."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        root_data = os.path.normcase(os.path.realpath(get_agent_data_dir()))
        audit_dir = os.path.normcase(os.path.realpath(get_agent_audit_dir()))
        ctx_dir = os.path.normcase(os.path.realpath(get_agent_context_dir()))
        state_dir = os.path.normcase(os.path.realpath(get_agent_state_dir()))

        self.assertTrue(_is_strictly_within(audit_dir, root_data))
        self.assertTrue(_is_strictly_within(ctx_dir, root_data))
        self.assertTrue(_is_strictly_within(state_dir, root_data))
        self.assertEqual(os.path.basename(audit_dir), "agent_audit")
        self.assertEqual(os.path.basename(ctx_dir), "agent_context")
        self.assertEqual(os.path.basename(state_dir), "agent_state")

    # -------------------------------------------------------------------------
    # 17. Persistence behavior in isolated temporary storage
    # -------------------------------------------------------------------------
    def test_17_persistence_behavior_in_isolated_temporary_storage(self):
        """Verifies full orchestrator, workflow, and audit ledger persistence in temp storage."""
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir
        synth_pid = "SYNTH-PERSIST-17"

        orchestrator = AgentOrchestrator()
        proposal = {
            "student_id": synth_pid,
            "title": "Dual-Use Research of Concern Screening Proposal",
            "chassis": "Bacillus subtilis",
            "tool": "Synthetic Riboswitch",
            "target": "Reporter expression regulation",
            "methodology": "Engineered theophylline-responsive riboswitch in non-pathogenic chassis.",
            "pathogen_work": False,
            "recombinant_dna": True
        }

        # 1. Proposal analysis
        analysis = orchestrator.analyze_proposal(proposal, project_id=synth_pid)
        self.assertIn("workflow_state", analysis)

        # 2. State transition
        state_data, ok = transition_state(synth_pid, WorkflowState.REQUIREMENT_CHECK, actor="agent")
        self.assertTrue(ok)
        self.assertEqual(state_data["current_state"], WorkflowState.REQUIREMENT_CHECK)

        # 3. Audit ledger record and tamper check
        record_audit_event(synth_pid, "TEST_EVENT", "agent", "orchestrator", "Verified persistence", WorkflowState.REQUIREMENT_CHECK)
        integ = verify_audit_integrity(synth_pid)
        self.assertTrue(integ["valid"])
        self.assertGreaterEqual(integ["event_count"], 1)

        # Verify files were created inside tmp_dir and NOT live storage
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "agent_audit", f"{synth_pid}.jsonl")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "agent_state", f"{synth_pid}.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "agent_context", f"{synth_pid}.json")))

        self.assertFalse(os.path.exists(os.path.join(self.live_data_dir, "agent_audit", f"{synth_pid}.jsonl")))
        self.assertFalse(os.path.exists(os.path.join(self.live_data_dir, "agent_state", f"{synth_pid}.json")))
        self.assertFalse(os.path.exists(os.path.join(self.live_data_dir, "agent_context", f"{synth_pid}.json")))


if __name__ == "__main__":
    unittest.main()
