"""
BioWriter Studio — Phase 3C.2 Security Regression Test Suite
Verifies:
  1. FIX-01: Data directory (/data/*) unauthenticated access completely removed.
  2. FIX-02: Image route (/images/*) strictly confined to static/images with extension whitelisting.
  3. FIX-03: Authentic student ST-2026-01 removed from public exemplars and draft listing,
             while preserving owner, faculty, and legitimate exemplar (13989) access.
  4. FIX-04: Production Flask session secret enforcement (fails startup on missing/insecure key;
             permits explicit dev/test modes).
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Set testing mode before importing app to satisfy configure_session_secret
os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"

from app import app, configure_session_secret, KNOWN_INSECURE_SECRETS, ALLOWED_IMAGE_EXTENSIONS
from flask import Flask


class TestPhase3C2SecurityRepairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mandatory test isolation: create temporary directory for all data operations
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_p3c2_test_")
        cls.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_dir

        # Ensure app is in testing mode
        app.config["TESTING"] = True
        app.testing = True

        # Copy baseline fixtures to isolated directory
        live_data = os.path.join(BASE_DIR, "data")
        for fname in ["users.json", "cohort_db.json", "faculty_security.json"]:
            src = os.path.join(live_data, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(cls.test_dir, fname))

        # Copy sample drafts (ST-2026-01 and 13989) to isolated drafts dir
        test_drafts_dir = os.path.join(cls.test_dir, "drafts")
        os.makedirs(test_drafts_dir, exist_ok=True)
        live_drafts = os.path.join(live_data, "drafts")
        for fname in ["13989.json", "ST-2026-01.json"]:
            src = os.path.join(live_drafts, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(test_drafts_dir, fname))

        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        # Restore environment variable
        if cls.old_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = cls.old_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)

        # Cleanup isolated temp directory
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # FIX-01: Data Directory Exposure Tests
    # =========================================================================

    def test_fix01_unauthenticated_request_to_users_json_returns_404(self):
        """Unauthenticated GET /data/users.json must return 404 (route removed)."""
        resp = self.client.get("/data/users.json")
        self.assertEqual(resp.status_code, 404)

    def test_fix01_unauthenticated_request_to_cohort_db_returns_404(self):
        """Unauthenticated GET /data/cohort_db.json must return 404."""
        resp = self.client.get("/data/cohort_db.json")
        self.assertEqual(resp.status_code, 404)

    def test_fix01_unauthenticated_request_to_faculty_security_returns_404(self):
        """Unauthenticated GET /data/faculty_security.json must return 404."""
        resp = self.client.get("/data/faculty_security.json")
        self.assertEqual(resp.status_code, 404)

    def test_fix01_unauthenticated_request_to_drafts_returns_404(self):
        """Unauthenticated GET /data/drafts/13989.json or ST-2026-01.json must return 404."""
        resp1 = self.client.get("/data/drafts/13989.json")
        resp2 = self.client.get("/data/drafts/ST-2026-01.json")
        self.assertEqual(resp1.status_code, 404)
        self.assertEqual(resp2.status_code, 404)

    def test_fix01_directory_traversal_against_data_returns_404(self):
        """Directory traversal against /data/ must return 404."""
        resp = self.client.get("/data/../app.py")
        self.assertEqual(resp.status_code, 404)

    # =========================================================================
    # FIX-02: Image Directory Restriction Tests
    # =========================================================================

    def test_fix02_valid_static_image_returns_200_and_image_content_type(self):
        """Valid image request to /images/detectr_aqua_figure2.png returns 200 and image/png."""
        resp = self.client.get("/images/detectr_aqua_figure2.png")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/png", resp.headers.get("Content-Type", ""))

    def test_fix02_direct_detectr_route_returns_200(self):
        """Direct GET /detectr_aqua_figure2.png returns 200 and image/png."""
        resp = self.client.get("/detectr_aqua_figure2.png")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/png", resp.headers.get("Content-Type", ""))

    def test_fix02_traversal_attempt_against_images_returns_404(self):
        """Path traversal attempt /images/../app.py returns 404."""
        resp = self.client.get("/images/../app.py")
        self.assertEqual(resp.status_code, 404)

    def test_fix02_source_file_request_via_images_returns_404(self):
        """Direct attempt to request source files (/images/app.py) returns 404."""
        resp = self.client.get("/images/app.py")
        self.assertEqual(resp.status_code, 404)

    def test_fix02_data_file_request_via_images_returns_404(self):
        """Direct attempt to request data files (/images/data/users.json) returns 404."""
        resp = self.client.get("/images/data/users.json")
        self.assertEqual(resp.status_code, 404)

    def test_fix02_config_file_request_via_images_returns_404(self):
        """Direct attempt to request config files (/images/.env) returns 404."""
        resp = self.client.get("/images/.env")
        self.assertEqual(resp.status_code, 404)

    def test_fix02_non_whitelisted_extension_returns_404(self):
        """Requests with non-whitelisted extensions (.js, .txt, .html) return 404."""
        for disallowed in ["test.txt", "script.js", "page.html", "backup.bak"]:
            resp = self.client.get(f"/images/{disallowed}")
            self.assertEqual(resp.status_code, 404)

    # =========================================================================
    # FIX-03: Authentic Student Record Privacy Tests (ST-2026-01)
    # =========================================================================

    def test_fix03_unauthenticated_guest_draft_access_denied(self):
        """Unauthenticated guest request to /api/student/draft/ST-2026-01 returns 403."""
        with self.client.session_transaction() as sess:
            sess.clear()
        resp = self.client.get("/api/student/draft/ST-2026-01")
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data.get("success", False))

    def test_fix03_unauthenticated_guest_drafts_list_excludes_st202601(self):
        """Unauthenticated guest request to /api/student/drafts must NOT contain ST-2026-01."""
        with self.client.session_transaction() as sess:
            sess.clear()
        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        drafts_list = data if isinstance(data, list) else data.get("drafts", [])
        student_ids = [str(d.get("student_id", "")).upper() for d in drafts_list]
        self.assertNotIn("ST-2026-01", student_ids)

    def test_fix03_unrelated_authenticated_student_draft_access_denied(self):
        """Authenticated student other than ST-2026-01 requesting ST-2026-01 returns 403."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["student_id"] = "ST-9999-99"
            sess["authenticated"] = True
            sess["role"] = "student"
        resp = self.client.get("/api/student/draft/ST-2026-01")
        self.assertEqual(resp.status_code, 403)

    def test_fix03_owner_student_draft_access_allowed(self):
        """Authenticated student ST-2026-01 requesting their own draft returns 200."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["student_id"] = "ST-2026-01"
            sess["authenticated"] = True
            sess["role"] = "student"
        resp = self.client.get("/api/student/draft/ST-2026-01")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success", False))
        self.assertEqual(str(data.get("draft", {}).get("student_id", "")).upper(), "ST-2026-01")

    def test_fix03_faculty_administrator_draft_access_allowed(self):
        """Authenticated faculty administrator requesting ST-2026-01 returns 200."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"
        resp = self.client.get("/api/student/draft/ST-2026-01")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success", False))

    def test_fix03_public_exemplar_13989_remains_accessible_to_guests(self):
        """Unauthenticated guest request to /api/student/draft/13989 returns 200."""
        with self.client.session_transaction() as sess:
            sess.clear()
        resp = self.client.get("/api/student/draft/13989")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success", False))

    def test_fix03_public_exemplar_13989_included_in_guest_drafts_list(self):
        """Unauthenticated guest request to /api/student/drafts includes 13989."""
        with self.client.session_transaction() as sess:
            sess.clear()
        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        drafts_list = data if isinstance(data, list) else data.get("drafts", [])
        student_ids = [str(d.get("student_id", "")).upper() for d in drafts_list]
        self.assertIn("13989", student_ids)

    # =========================================================================
    # FIX-04: Session Secret Configuration Tests
    # =========================================================================

    def test_fix04_production_missing_secret_raises_runtime_error(self):
        """In production mode with unset SECRET_KEY, configure_session_secret raises RuntimeError."""
        test_app = Flask("test_secret_prod_missing")
        env_backup = dict(os.environ)
        try:
            # Strip testing and development indicators
            os.environ.pop("SECRET_KEY", None)
            os.environ.pop("FLASK_TESTING", None)
            os.environ.pop("TESTING", None)
            os.environ.pop("BIOWRITER_ENV", None)
            os.environ.pop("FLASK_ENV", None)
            os.environ.pop("PYTEST_CURRENT_TEST", None)

            # Temporarily simulate non-unittest execution
            saved_unittest = sys.modules.pop("unittest", None)
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    configure_session_secret(test_app)
                self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", str(ctx.exception))
                self.assertIn("SECRET_KEY is unset or empty", str(ctx.exception))
            finally:
                if saved_unittest is not None:
                    sys.modules["unittest"] = saved_unittest
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_fix04_production_placeholder_secret_raises_runtime_error(self):
        """In production mode with known placeholder secret, configure_session_secret raises RuntimeError."""
        for bad_secret in ["biowriter-studio-session-secret-2026", "replace-with-your-production-secret-key"]:
            test_app = Flask("test_secret_prod_bad")
            env_backup = dict(os.environ)
            try:
                os.environ["SECRET_KEY"] = bad_secret
                os.environ.pop("FLASK_TESTING", None)
                os.environ.pop("TESTING", None)
                os.environ.pop("BIOWRITER_ENV", None)
                os.environ.pop("FLASK_ENV", None)
                os.environ.pop("PYTEST_CURRENT_TEST", None)

                saved_unittest = sys.modules.pop("unittest", None)
                try:
                    with self.assertRaises(RuntimeError) as ctx:
                        configure_session_secret(test_app)
                    self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", str(ctx.exception))
                    self.assertIn("insecure placeholder", str(ctx.exception))
                finally:
                    if saved_unittest is not None:
                        sys.modules["unittest"] = saved_unittest
            finally:
                os.environ.clear()
                os.environ.update(env_backup)

    def test_fix04_production_short_secret_raises_runtime_error(self):
        """In production mode with SECRET_KEY shorter than 16 chars, configure_session_secret raises RuntimeError."""
        test_app = Flask("test_secret_prod_short")
        env_backup = dict(os.environ)
        try:
            os.environ["SECRET_KEY"] = "short-key-123"
            os.environ.pop("FLASK_TESTING", None)
            os.environ.pop("TESTING", None)
            os.environ.pop("BIOWRITER_ENV", None)
            os.environ.pop("FLASK_ENV", None)
            os.environ.pop("PYTEST_CURRENT_TEST", None)

            saved_unittest = sys.modules.pop("unittest", None)
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    configure_session_secret(test_app)
                self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", str(ctx.exception))
                self.assertIn("too short", str(ctx.exception))
            finally:
                if saved_unittest is not None:
                    sys.modules["unittest"] = saved_unittest
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_fix04_production_strong_secret_succeeds(self):
        """In production mode with strong SECRET_KEY (>= 16 chars), configure_session_secret succeeds."""
        test_app = Flask("test_secret_prod_strong")
        strong_key = "a4f8b92c10d3e5f7a4f8b92c10d3e5f7a4f8b92c10d3e5f7"
        env_backup = dict(os.environ)
        try:
            os.environ["SECRET_KEY"] = strong_key
            os.environ.pop("FLASK_TESTING", None)
            os.environ.pop("TESTING", None)
            os.environ.pop("BIOWRITER_ENV", None)
            os.environ.pop("FLASK_ENV", None)
            os.environ.pop("PYTEST_CURRENT_TEST", None)

            saved_unittest = sys.modules.pop("unittest", None)
            try:
                result = configure_session_secret(test_app)
                self.assertEqual(result, strong_key)
                self.assertEqual(test_app.secret_key, strong_key)
            finally:
                if saved_unittest is not None:
                    sys.modules["unittest"] = saved_unittest
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_fix04_development_mode_allows_fallback(self):
        """In explicit development mode (BIOWRITER_ENV=development), fallback is permitted."""
        test_app = Flask("test_secret_dev")
        env_backup = dict(os.environ)
        try:
            os.environ.pop("SECRET_KEY", None)
            os.environ["BIOWRITER_ENV"] = "development"
            os.environ.pop("FLASK_TESTING", None)
            os.environ.pop("TESTING", None)

            result = configure_session_secret(test_app)
            self.assertTrue(len(result) >= 16)
            self.assertEqual(test_app.secret_key, result)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_fix04_testing_mode_allows_clean_execution(self):
        """In testing mode (app.testing=True or FLASK_TESTING=1), fallback/test secret is permitted."""
        test_app = Flask("test_secret_test_mode")
        test_app.testing = True
        env_backup = dict(os.environ)
        try:
            os.environ.pop("SECRET_KEY", None)
            os.environ["FLASK_TESTING"] = "1"
            result = configure_session_secret(test_app)
            self.assertTrue(len(result) >= 16)
            self.assertEqual(test_app.secret_key, result)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)


    def test_fix04_subprocess_production_missing_secret_fails_startup(self):
        """Subprocess test: Standalone startup in production without SECRET_KEY fails with RuntimeError."""
        env_clean = os.environ.copy()
        for k in ["SECRET_KEY", "FLASK_TESTING", "TESTING", "BIOWRITER_ENV", "FLASK_ENV", "PYTEST_CURRENT_TEST"]:
            env_clean.pop(k, None)
        code = "import sys, os; sys.path.insert(0, os.path.abspath('upload')); import app"
        proc = subprocess.run([sys.executable, "-c", code], env=env_clean, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("SECRET_KEY is unset or empty", proc.stderr)

    def test_fix04_subprocess_production_placeholder_secret_fails_startup(self):
        """Subprocess test: Standalone startup with placeholder secret fails with RuntimeError."""
        env_bad = os.environ.copy()
        for k in ["FLASK_TESTING", "TESTING", "BIOWRITER_ENV", "FLASK_ENV", "PYTEST_CURRENT_TEST"]:
            env_bad.pop(k, None)
        env_bad["SECRET_KEY"] = "biowriter-studio-session-secret-2026"
        code = "import sys, os; sys.path.insert(0, os.path.abspath('upload')); import app"
        proc = subprocess.run([sys.executable, "-c", code], env=env_bad, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("insecure placeholder", proc.stderr)

    def test_fix04_subprocess_production_strong_secret_succeeds(self):
        """Subprocess test: Standalone startup with strong SECRET_KEY succeeds."""
        env_good = os.environ.copy()
        for k in ["FLASK_TESTING", "TESTING", "BIOWRITER_ENV", "FLASK_ENV", "PYTEST_CURRENT_TEST"]:
            env_good.pop(k, None)
        env_good["SECRET_KEY"] = "0123456789abcdef0123456789abcdef"
        code = "import sys, os; sys.path.insert(0, os.path.abspath('upload')); import app; print('STARTUP_OK')"
        proc = subprocess.run([sys.executable, "-c", code], env=env_good, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("STARTUP_OK", proc.stdout)

    def test_fix04_subprocess_development_mode_succeeds(self):
        """Subprocess test: Standalone startup with BIOWRITER_ENV=development logs warning and succeeds."""
        env_dev = os.environ.copy()
        for k in ["SECRET_KEY", "FLASK_TESTING", "TESTING", "FLASK_ENV", "PYTEST_CURRENT_TEST"]:
            env_dev.pop(k, None)
        env_dev["BIOWRITER_ENV"] = "development"
        code = "import sys, os; sys.path.insert(0, os.path.abspath('upload')); import app; print('DEV_STARTUP_OK')"
        proc = subprocess.run([sys.executable, "-c", code], env=env_dev, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("DEV_STARTUP_OK", proc.stdout)
        self.assertIn("[SECURITY WARNING]", proc.stderr)


if __name__ == "__main__":
    unittest.main()
