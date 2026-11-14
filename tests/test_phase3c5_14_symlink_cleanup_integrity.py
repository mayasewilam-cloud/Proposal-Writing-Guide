"""
Phase 3C.5.14: Symlink-Safe Agent Cleanup Integrity Test Suite.

Verifies that cleanup_project_artifacts() in tests/test_phase3_governed_agent_loop.py
safely unlinks symbolic links without resolving to or deleting the destination target file,
handles dangling symlinks, safely rejects directory junctions, and preserves
all existing containment, validation, and failure reporting protections.
"""

import os
import sys
import unittest
import tempfile
import shutil
import hashlib
import warnings
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Strict Startup Guard: Configure isolated temporary storage BEFORE imports
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PORTAL_DIR = os.path.join(_BASE_DIR, "portal") if os.path.exists(os.path.join(_BASE_DIR, "portal")) else _BASE_DIR
_LIVE_DATA_DIR_CANONICAL = os.path.normcase(os.path.realpath(os.path.join(_PORTAL_DIR, "data")))

_configured_raw = os.environ.get("BIOWRITER_DATA_DIR")
if not _configured_raw or not _configured_raw.strip():
    _BOOSTRAP_TMP = tempfile.mkdtemp(prefix="bw_p3c514_bootstrap_")
    os.environ["BIOWRITER_DATA_DIR"] = _BOOSTRAP_TMP
else:
    _configured_canonical = os.path.normcase(os.path.realpath(_configured_raw))
    try:
        _common = os.path.commonpath([_configured_canonical, _LIVE_DATA_DIR_CANONICAL])
        if _common == _LIVE_DATA_DIR_CANONICAL or _common == _configured_canonical:
            raise RuntimeError(
                f"FATAL: BIOWRITER_DATA_DIR resolves to or within live storage: {_configured_canonical}"
            )
    except (ValueError, OSError):
        pass

if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from tests.test_phase3_governed_agent_loop import (
    cleanup_project_artifacts,
    _is_strictly_within,
    _resolves_to_or_within,
    _is_junction,
)
from agent.audit import get_agent_data_dir, get_agent_audit_dir
from agent.service import get_agent_context_dir
from agent.workflow import get_agent_state_dir


def _hash_file(filepath: str) -> str:
    """Returns SHA-256 hex digest of file, or empty string if file does not exist."""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestSymlinkCleanupIntegrity(unittest.TestCase):
    """
    Comprehensive regression suite for symlink-safe artifact cleanup.
    Exercises real filesystem operations within isolated temporary directories.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="bw_p3c514_test_")
        self.orig_env = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.tmp_dir

        # Initialize subdirectories inside isolated temp dir
        self.state_dir = os.path.join(self.tmp_dir, "agent_state")
        self.context_dir = os.path.join(self.tmp_dir, "agent_context")
        self.audit_dir = os.path.join(self.tmp_dir, "agent_audit")
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.context_dir, exist_ok=True)
        os.makedirs(self.audit_dir, exist_ok=True)

    def tearDown(self):
        if self.orig_env is not None:
            os.environ["BIOWRITER_DATA_DIR"] = self.orig_env
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_symlink_or_skip(self, target: str, link_path: str, target_is_directory: bool = False) -> None:
        """Helper to create a real filesystem symlink or skip if OS privilege is absent."""
        try:
            os.symlink(target, link_path, target_is_directory=target_is_directory)
        except OSError as e:
            self.skipTest(
                f"Filesystem symlink creation unavailable on this system (requires Developer Mode or SeCreateSymbolicLinkPrivilege): {e}"
            )

    # -----------------------------------------------------------------------
    # Requirement 1: A regular project file is cleaned up successfully
    # -----------------------------------------------------------------------
    def test_01_regular_project_file_cleaned_up_successfully(self):
        pid = "TEST-REG-01"
        state_file = os.path.join(self.state_dir, f"{pid}.json")
        context_file = os.path.join(self.context_dir, f"{pid}.json")
        audit_file = os.path.join(self.audit_dir, f"{pid}.jsonl")

        with open(state_file, "w") as f:
            f.write('{"state": "active"}')
        with open(context_file, "w") as f:
            f.write('{"context": "sample"}')
        with open(audit_file, "w") as f:
            f.write('{"event": "start"}\n')

        self.assertTrue(os.path.exists(state_file))
        self.assertTrue(os.path.exists(context_file))
        self.assertTrue(os.path.exists(audit_file))

        cleanup_project_artifacts(pid)

        self.assertFalse(os.path.exists(state_file), "State file should be cleaned up")
        self.assertFalse(os.path.exists(context_file), "Context file should be cleaned up")
        self.assertFalse(os.path.exists(audit_file), "Audit file should be cleaned up")

    # -----------------------------------------------------------------------
    # Requirement 2: Symlink pointing to another file inside Agent directory
    # -----------------------------------------------------------------------
    def test_02_symlink_pointing_inside_agent_dir_removed_without_deleting_target(self):
        pid = "TEST-LINK-INT"
        target_pid = "TEST-TARGET-INT"
        target_file = os.path.join(self.state_dir, f"{target_pid}.json")
        with open(target_file, "w") as f:
            f.write('{"protected_data": "must_not_be_deleted"}')
        target_hash_before = _hash_file(target_file)

        link_file = os.path.join(self.state_dir, f"{pid}.json")
        self._create_symlink_or_skip(target_file, link_file)

        self.assertTrue(os.path.islink(link_file), "Precondition: link must be a symbolic link")
        self.assertTrue(os.path.exists(target_file), "Precondition: destination file must exist")

        cleanup_project_artifacts(pid)

        # Explicit assertions required by Section 4:
        self.assertFalse(os.path.lexists(link_file), "Link must NOT exist after cleanup")
        self.assertTrue(os.path.exists(target_file), "Destination file MUST exist after cleanup")
        self.assertEqual(_hash_file(target_file), target_hash_before, "Destination content and SHA-256 hash must be unchanged")

    def test_02_symlink_inside_agent_dir_simulated(self):
        """Simulated symlink test exercising islink -> os.unlink branch unconditionally."""
        pid = "TEST-SIM-02"
        target_file = os.path.join(self.state_dir, "TARGET-02.json")
        with open(target_file, "w") as f:
            f.write('{"data": "valuable_internal_payload"}')
        target_hash_before = _hash_file(target_file)

        link_file = os.path.join(self.state_dir, f"{pid}.json")
        with open(link_file, "w") as f:
            f.write('placeholder_link_entry')

        unlinked_paths = []
        orig_unlink = os.unlink

        def mock_unlink(path):
            unlinked_paths.append(os.path.normcase(os.path.abspath(path)))
            orig_unlink(path)

        with patch("os.path.islink", side_effect=lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(link_file))):
            with patch("os.unlink", side_effect=mock_unlink):
                with patch("os.remove") as mock_remove:
                    cleanup_project_artifacts(pid)
                    mock_remove.assert_not_called()

        self.assertIn(os.path.normcase(os.path.abspath(link_file)), unlinked_paths)
        self.assertFalse(os.path.lexists(link_file), "Link must be removed")
        self.assertTrue(os.path.exists(target_file), "Destination must exist")
        self.assertEqual(_hash_file(target_file), target_hash_before, "Destination hash must be identical")

    # -----------------------------------------------------------------------
    # Requirement 3: Symlink pointing outside Agent directory
    # -----------------------------------------------------------------------
    def test_03_symlink_pointing_outside_agent_dir_removed_without_modifying_target(self):
        outside_dir = tempfile.mkdtemp(prefix="bw_outside_")
        try:
            target_file = os.path.join(outside_dir, "external_valuable.json")
            with open(target_file, "w") as f:
                f.write('{"external_data": "external_payload"}')
            target_hash_before = _hash_file(target_file)

            pid = "TEST-LINK-EXT"
            link_file = os.path.join(self.state_dir, f"{pid}.json")
            self._create_symlink_or_skip(target_file, link_file)

            self.assertTrue(os.path.islink(link_file))
            self.assertTrue(os.path.exists(target_file))

            cleanup_project_artifacts(pid)

            # Explicit assertions:
            self.assertFalse(os.path.lexists(link_file), "Link must NOT exist after cleanup")
            self.assertTrue(os.path.exists(target_file), "Destination file MUST exist after cleanup")
            self.assertEqual(_hash_file(target_file), target_hash_before, "Destination content and SHA-256 must be unchanged")
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_03_symlink_outside_agent_dir_simulated(self):
        """Simulated external symlink test exercising islink -> os.unlink branch unconditionally."""
        outside_dir = tempfile.mkdtemp(prefix="bw_outside_sim_")
        try:
            target_file = os.path.join(outside_dir, "external_sim.json")
            with open(target_file, "w") as f:
                f.write('{"external": "important_unprotected"}')
            target_hash_before = _hash_file(target_file)

            pid = "TEST-SIM-03"
            link_file = os.path.join(self.state_dir, f"{pid}.json")
            with open(link_file, "w") as f:
                f.write("link_stub")

            with patch("os.path.islink", side_effect=lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(link_file))):
                with patch("os.remove") as mock_remove:
                    cleanup_project_artifacts(pid)
                    mock_remove.assert_not_called()

            self.assertFalse(os.path.lexists(link_file))
            self.assertTrue(os.path.exists(target_file))
            self.assertEqual(_hash_file(target_file), target_hash_before)
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # Requirement 4: Symlink pointing into simulated live storage is never followed
    # -----------------------------------------------------------------------
    def test_04_symlink_pointing_to_simulated_live_storage_destination_unchanged(self):
        sim_live_dir = tempfile.mkdtemp(prefix="bw_sim_live_")
        try:
            sim_protected_file = os.path.join(sim_live_dir, "users.json")
            with open(sim_protected_file, "w") as f:
                f.write('{"admin": "password_hash_unmodified"}')
            target_hash_before = _hash_file(sim_protected_file)

            pid = "TEST-LINK-LIVE"
            link_file = os.path.join(self.state_dir, f"{pid}.json")
            self._create_symlink_or_skip(sim_protected_file, link_file)

            self.assertTrue(os.path.islink(link_file))
            self.assertTrue(os.path.exists(sim_protected_file))

            cleanup_project_artifacts(pid)

            # Explicit assertions:
            self.assertFalse(os.path.lexists(link_file), "Link must NOT exist after cleanup")
            self.assertTrue(os.path.exists(sim_protected_file), "Simulated live storage file MUST exist after cleanup")
            self.assertEqual(_hash_file(sim_protected_file), target_hash_before, "Destination content and SHA-256 must be unchanged")
        finally:
            shutil.rmtree(sim_live_dir, ignore_errors=True)

    def test_04_symlink_to_simulated_live_storage_simulated(self):
        """Simulated test pointing to simulated live storage without touching real live storage."""
        sim_live_dir = tempfile.mkdtemp(prefix="bw_sim_live_sim_")
        try:
            sim_protected_file = os.path.join(sim_live_dir, "cohort_db.json")
            with open(sim_protected_file, "w") as f:
                f.write('{"cohort": "2026_spring"}')
            target_hash_before = _hash_file(sim_protected_file)

            pid = "TEST-SIM-04"
            link_file = os.path.join(self.state_dir, f"{pid}.json")
            with open(link_file, "w") as f:
                f.write("simulated_symlink_pointing_to_live_storage")

            with patch("os.path.islink", side_effect=lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(link_file))):
                with patch("os.remove") as mock_remove:
                    cleanup_project_artifacts(pid)
                    mock_remove.assert_not_called()

            self.assertFalse(os.path.lexists(link_file))
            self.assertTrue(os.path.exists(sim_protected_file))
            self.assertEqual(_hash_file(sim_protected_file), target_hash_before)
        finally:
            shutil.rmtree(sim_live_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # Requirement 5: Dangling symlink is detected and safely removed
    # -----------------------------------------------------------------------
    def test_05_dangling_symlink_detected_and_safely_removed(self):
        pid = "TEST-DANGLING-01"
        nonexistent_target = os.path.join(self.tmp_dir, "does_not_exist_xyz.json")
        link_file = os.path.join(self.state_dir, f"{pid}.json")
        self._create_symlink_or_skip(nonexistent_target, link_file)

        self.assertTrue(os.path.islink(link_file))
        self.assertFalse(os.path.exists(link_file), "Precondition: dangling link exists() returns False")
        self.assertTrue(os.path.lexists(link_file), "Precondition: lexists() returns True")

        cleanup_project_artifacts(pid)

        # Explicit assertions:
        self.assertFalse(os.path.lexists(link_file), "Dangling link must be removed from disk")
        self.assertFalse(os.path.exists(nonexistent_target), "Destination must remain non-existent")

    def test_05_dangling_symlink_simulated(self):
        """Simulated dangling symlink test ensuring lexists and unlink handle missing destination."""
        pid = "TEST-SIM-05"
        link_file = os.path.join(self.state_dir, f"{pid}.json")
        with open(link_file, "w") as f:
            f.write("broken_symlink_entry")

        unlinked = []
        orig_unlink = os.unlink

        def mock_unlink(path):
            unlinked.append(path)
            orig_unlink(path)

        # Simulate islink=True, exists=False, lexists=True
        with patch("os.path.islink", side_effect=lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(link_file))):
            with patch("os.unlink", side_effect=mock_unlink):
                cleanup_project_artifacts(pid)

        self.assertFalse(os.path.lexists(link_file), "Dangling link must be unlinked")
        self.assertEqual(len(unlinked), 1)

    # -----------------------------------------------------------------------
    # Requirement 6: Symlink pointing to second project's file does not delete second project
    # -----------------------------------------------------------------------
    def test_06_symlink_pointing_to_second_project_file_preserves_second_project(self):
        pid1 = "PROJECT-ALPHA"
        pid2 = "PROJECT-BETA"

        beta_file = os.path.join(self.state_dir, f"{pid2}.json")
        with open(beta_file, "w") as f:
            f.write('{"project": "beta", "secret": "keep_intact"}')
        beta_hash_before = _hash_file(beta_file)

        # ALPHA points to BETA
        alpha_link = os.path.join(self.state_dir, f"{pid1}.json")
        self._create_symlink_or_skip(beta_file, alpha_link)

        self.assertTrue(os.path.islink(alpha_link))
        self.assertTrue(os.path.exists(beta_file))

        cleanup_project_artifacts(pid1)

        # Explicit assertions:
        self.assertFalse(os.path.lexists(alpha_link), "Alpha link must be removed")
        self.assertTrue(os.path.exists(beta_file), "Beta project file MUST exist")
        self.assertEqual(_hash_file(beta_file), beta_hash_before, "Beta project file SHA-256 hash must be identical")

    def test_06_symlink_to_second_project_simulated(self):
        """Simulated second project protection test."""
        pid1 = "PROJECT-SIM-A"
        pid2 = "PROJECT-SIM-B"

        beta_file = os.path.join(self.state_dir, f"{pid2}.json")
        with open(beta_file, "w") as f:
            f.write('{"project": "beta_simulated_payload"}')
        beta_hash_before = _hash_file(beta_file)

        alpha_link = os.path.join(self.state_dir, f"{pid1}.json")
        with open(alpha_link, "w") as f:
            f.write("link_to_beta")

        with patch("os.path.islink", side_effect=lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(alpha_link))):
            with patch("os.remove") as mock_remove:
                cleanup_project_artifacts(pid1)
                mock_remove.assert_not_called()

        self.assertFalse(os.path.lexists(alpha_link))
        self.assertTrue(os.path.exists(beta_file))
        self.assertEqual(_hash_file(beta_file), beta_hash_before)

    # -----------------------------------------------------------------------
    # Requirement 7: Ordinary file with same naming pattern cleaned up correctly
    # -----------------------------------------------------------------------
    def test_07_ordinary_file_same_naming_pattern_cleaned_up(self):
        pid = "TEST-PATTERN-07"
        f1 = os.path.join(self.state_dir, f"{pid}.json")
        f2 = os.path.join(self.context_dir, f"{pid}.json")
        f3 = os.path.join(self.audit_dir, f"{pid}.jsonl")

        for f in (f1, f2, f3):
            with open(f, "w") as fp:
                fp.write('{"sample": "data"}')

        cleanup_project_artifacts(pid)

        self.assertFalse(os.path.exists(f1))
        self.assertFalse(os.path.exists(f2))
        self.assertFalse(os.path.exists(f3))

    # -----------------------------------------------------------------------
    # Requirement 8: Directory junction is not traversed or used to delete target
    # -----------------------------------------------------------------------
    def test_08_directory_junction_rejected_and_destination_preserved(self):
        """Tests that Windows directory junctions are safely rejected and contents preserved."""
        if not hasattr(os.path, "isjunction") or sys.platform != "win32":
            self.skipTest("Windows directory junctions not applicable on this platform.")

        import _winapi
        pid = "TEST-JUNCTION-08"
        dest_dir = os.path.join(self.tmp_dir, "real_junction_dest")
        os.makedirs(dest_dir, exist_ok=True)
        canary_file = os.path.join(dest_dir, "canary.txt")
        with open(canary_file, "w") as f:
            f.write("precious_junction_target_data")
        canary_hash_before = _hash_file(canary_file)

        junction_path = os.path.join(self.state_dir, f"{pid}.json")
        try:
            _winapi.CreateJunction(dest_dir, junction_path)
        except OSError as e:
            self.skipTest(f"Failed to create directory junction: {e}")

        self.assertTrue(os.path.isjunction(junction_path), "Precondition: junction must be recognized")
        self.assertTrue(os.path.exists(canary_file), "Precondition: canary file exists")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cleanup_project_artifacts(pid)
            self.assertTrue(len(w) > 0, "A warning should be emitted for directory junction")
            self.assertIn("directory junction", str(w[-1].message).lower())

        # Assert destination contents and directory are untouched
        self.assertTrue(os.path.exists(canary_file), "Canary file MUST exist after cleanup")
        self.assertTrue(os.path.isdir(dest_dir), "Destination directory MUST exist after cleanup")
        self.assertEqual(_hash_file(canary_file), canary_hash_before, "Canary hash must be identical")

        # Cleanup junction cleanly
        import subprocess
        subprocess.run(["cmd", "/c", "rmdir", junction_path], capture_output=True)

    # -----------------------------------------------------------------------
    # Requirement 9: Invalid project ID remains rejected
    # -----------------------------------------------------------------------
    def test_09_invalid_project_id_remains_rejected(self):
        invalid_ids = [
            "",
            "   ",
            None,
            123,
            [],
            "../traversal",
            "..\\traversal",
            "dir/subfile",
            "dir\\subfile",
            "/absolute/unix",
            "C:\\absolute\\win",
        ]
        for bad_id in invalid_ids:
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ValueError):
                    cleanup_project_artifacts(bad_id)

    # -----------------------------------------------------------------------
    # Requirement 10: Cleanup failure is visible and cannot be reported as success
    # -----------------------------------------------------------------------
    def test_10_cleanup_failure_is_visible(self):
        pid = "TEST-FAIL-10"
        target_file = os.path.join(self.state_dir, f"{pid}.json")
        with open(target_file, "w") as f:
            f.write('{"fail": "me"}')

        with patch("os.remove", side_effect=OSError("Forced filesystem lock error")):
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always")
                cleanup_project_artifacts(pid)
                self.assertTrue(len(recorded) > 0, "Warning must be recorded on failure")
                self.assertIn("Failed to remove test artifact", str(recorded[-1].message))
                self.assertIn("Forced filesystem lock error", str(recorded[-1].message))

        # Test failure on unlink
        with patch("os.path.islink", return_value=True):
            with patch("os.unlink", side_effect=OSError("Forced unlink permission denied")):
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter("always")
                    cleanup_project_artifacts(pid)
                    self.assertTrue(len(recorded) > 0)
                    self.assertIn("Failed to unlink symbolic link", str(recorded[-1].message))
                    self.assertIn("Forced unlink permission denied", str(recorded[-1].message))

    # -----------------------------------------------------------------------
    # Requirement 11: Existing containment protections still reject unsafe directories
    # -----------------------------------------------------------------------
    def test_11_containment_protections_reject_unsafe_directories(self):
        live_data_dir = os.path.normcase(os.path.realpath(os.path.join(_PORTAL_DIR, "data")))

        # Subtest A: Pointing BIOWRITER_DATA_DIR directly to live storage
        with patch.dict(os.environ, {"BIOWRITER_DATA_DIR": live_data_dir}):
            with self.assertRaises(RuntimeError) as cm:
                cleanup_project_artifacts("SAFE-ID")
            self.assertIn("resolves to or within live storage", str(cm.exception))

        # Subtest B: Pointing BIOWRITER_DATA_DIR to subdirectory within live storage
        sub_live = os.path.join(live_data_dir, "drafts")
        with patch.dict(os.environ, {"BIOWRITER_DATA_DIR": sub_live}):
            with self.assertRaises(RuntimeError) as cm:
                cleanup_project_artifacts("SAFE-ID")
            self.assertIn("resolves to or within live storage", str(cm.exception))

        # Subtest C: Pointing BIOWRITER_DATA_DIR to parent containing live storage
        parent_live = os.path.dirname(live_data_dir)
        with patch.dict(os.environ, {"BIOWRITER_DATA_DIR": parent_live}):
            with self.assertRaises(RuntimeError) as cm:
                cleanup_project_artifacts("SAFE-ID")
            self.assertIn("contains live storage", str(cm.exception))

    # -----------------------------------------------------------------------
    # Requirement 12: No test modifies files outside its isolated temporary directory
    # -----------------------------------------------------------------------
    def test_12_no_files_modified_outside_temporary_directory(self):
        # Record state of live data directory before operation
        live_data_dir = os.path.join(_PORTAL_DIR, "data")
        live_files_before = {}
        for root, dirs, files in os.walk(live_data_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                live_files_before[fpath] = _hash_file(fpath)

        # Run multiple cleanups
        cleanup_project_artifacts("NONEXISTENT-PROJECT")
        cleanup_project_artifacts("TEST-REG-01")

        # Verify live files are 100% untouched
        for fpath, original_hash in live_files_before.items():
            self.assertTrue(os.path.exists(fpath), f"File {fpath} must still exist")
            self.assertEqual(_hash_file(fpath), original_hash, f"File {fpath} must not be modified")


if __name__ == "__main__":
    unittest.main()
