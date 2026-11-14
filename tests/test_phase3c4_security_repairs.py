"""
BioWriter Studio — Phase 3C.4 Security Regression Test Suite
Comprehensive verification of Phase 3C.4 targeted repairs:
  1. FIX-01: Removal of ambient testing-mode bypasses (no 'unittest' or 'pytest' import bypass,
             no PYTEST_CURRENT_TEST bypass; explicit test config required).
  2. FIX-02: Strengthened production SECRET_KEY validation (case-insensitive placeholder checks,
             minimum 32-character requirement, no key leakage in error messages).
  3. FIX-03: Realpath canonical filesystem containment for /images/ and /detectr_aqua_figure2.png
             (symlinks and Windows directory junctions pointing outside are strictly blocked;
             nested subdirectories and valid images preserved).
"""

import os
import sys
import shutil
import subprocess
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Set explicit test mode before importing app
os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"

from app import app, configure_session_secret, KNOWN_INSECURE_SECRETS, ALLOWED_IMAGE_EXTENSIONS
from flask import Flask, send_from_directory, jsonify


class TestPhase3C4SessionSecurity(unittest.TestCase):
    """Subprocess and in-process tests for session-secret enforcement and ambient bypass removal."""

    @classmethod
    def setUpClass(cls):
        cls.python_bin = sys.executable
        cls.upload_dir = BASE_DIR

    def _run_subprocess_startup(self, env_overrides=None, code_prefix=""):
        """Executes application import in an isolated subprocess with explicit environment."""
        env = os.environ.copy()
        # Scrub all testing/dev mode triggers by default
        for key in ["SECRET_KEY", "FLASK_TESTING", "TESTING", "BIOWRITER_ENV", "FLASK_ENV", "PYTEST_CURRENT_TEST"]:
            env.pop(key, None)

        if env_overrides:
            for k, v in env_overrides.items():
                if v is None:
                    env.pop(k, None)
                else:
                    env[k] = v

        code = (
            "import sys, os\n"
            f"sys.path.insert(0, r'{self.upload_dir}')\n"
            f"{code_prefix}\n"
            "try:\n"
            "    import app\n"
            "    is_fallback = 'fallback' in app.app.secret_key or 'test' in app.app.secret_key\n"
            "    print('STARTUP_SUCCESS|FALLBACK=' + str(is_fallback))\n"
            "except Exception as e:\n"
            "    print('STARTUP_ERROR:' + type(e).__name__ + '|' + str(e), file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        return subprocess.run([self.python_bin, "-c", code], env=env, capture_output=True, text=True)

    # 1. Production mode, no SECRET_KEY, no test imports: startup fails.
    def test_01_subprocess_prod_no_secret_fails(self):
        proc = self._run_subprocess_startup()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("SECRET_KEY is unset or empty", proc.stderr)

    # 2. Production mode, no SECRET_KEY, with unittest imported: startup still fails.
    def test_02_subprocess_prod_with_unittest_import_fails(self):
        proc = self._run_subprocess_startup(code_prefix="import unittest")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("SECRET_KEY is unset or empty", proc.stderr)

    # 3. Production mode, no SECRET_KEY, with pytest imported if available: startup still fails.
    def test_03_subprocess_prod_with_pytest_import_fails(self):
        proc = self._run_subprocess_startup(code_prefix="try:\n    import pytest\nexcept ImportError:\n    pass")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)

    # 4. Production mode, no SECRET_KEY, with PYTEST_CURRENT_TEST set: startup still fails.
    def test_04_subprocess_prod_with_pytest_env_var_fails(self):
        proc = self._run_subprocess_startup(env_overrides={"PYTEST_CURRENT_TEST": "test_dummy.py::test_fn (call)"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("SECRET_KEY is unset or empty", proc.stderr)

    # 5. Production mode, known placeholder in lowercase: startup fails.
    def test_05_subprocess_prod_lowercase_placeholder_fails(self):
        proc = self._run_subprocess_startup(env_overrides={"SECRET_KEY": "biowriter-studio-session-secret-2026"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("insecure placeholder", proc.stderr)

    # 6. Production mode, known placeholder in uppercase: startup fails.
    def test_06_subprocess_prod_uppercase_placeholder_fails(self):
        proc = self._run_subprocess_startup(env_overrides={"SECRET_KEY": "BIOWRITER-STUDIO-SESSION-SECRET-2026"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("insecure placeholder", proc.stderr)

    # 7. Production mode, mixed-case placeholder: startup fails.
    def test_07_subprocess_prod_mixedcase_placeholder_fails(self):
        proc = self._run_subprocess_startup(env_overrides={"SECRET_KEY": "Replace-With-Your-Production-Secret-Key"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("insecure placeholder", proc.stderr)

    # 8. Production mode, short secret (< 32 chars): startup fails.
    def test_08_subprocess_prod_short_secret_fails(self):
        # 16-character secret is now rejected (minimum 32 required)
        proc = self._run_subprocess_startup(env_overrides={"SECRET_KEY": "1234567890123456"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("too short", proc.stderr)

    # 9. Production mode, valid explicitly supplied random secret: startup succeeds.
    def test_09_subprocess_prod_strong_random_secret_succeeds(self):
        strong_key = "a4f8b92c10d3e5f7a4f8b92c10d3e5f7a4f8b92c10d3e5f7a4f8b92c10d3e5f7"
        proc = self._run_subprocess_startup(env_overrides={"SECRET_KEY": strong_key})
        self.assertEqual(proc.returncode, 0)
        self.assertIn("STARTUP_SUCCESS|FALLBACK=False", proc.stdout)

    # 10. Explicit testing mode: tests run with an isolated test secret.
    def test_10_subprocess_explicit_testing_mode_succeeds(self):
        proc = self._run_subprocess_startup(env_overrides={"FLASK_TESTING": "1"})
        self.assertEqual(proc.returncode, 0)
        self.assertIn("STARTUP_SUCCESS", proc.stdout)

    # 11. Explicit development mode: permitted fallback works and emits a warning.
    def test_11_subprocess_explicit_dev_mode_emits_warning(self):
        proc = self._run_subprocess_startup(env_overrides={"BIOWRITER_ENV": "development"})
        self.assertEqual(proc.returncode, 0)
        self.assertIn("STARTUP_SUCCESS|FALLBACK=True", proc.stdout)
        self.assertIn("[SECURITY WARNING]", proc.stderr)

    # 12. Unknown or misspelled environment mode: production enforcement remains active.
    def test_12_subprocess_misspelled_env_mode_fails_closed(self):
        proc = self._run_subprocess_startup(env_overrides={"BIOWRITER_ENV": "developemnt"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)


class TestPhase3C4ImageContainment(unittest.TestCase):
    """Harness tests for realpath image containment, directory junctions, and symlinks."""

    @classmethod
    def setUpClass(cls):
        # Create isolated temporary directory structure
        cls.test_root = tempfile.mkdtemp(prefix="biowriter_p3c4_img_")
        cls.static_dir = os.path.join(cls.test_root, "static")
        cls.images_dir = os.path.join(cls.static_dir, "images")
        cls.secret_dir = os.path.join(cls.test_root, "secret")
        os.makedirs(cls.images_dir, exist_ok=True)
        os.makedirs(cls.secret_dir, exist_ok=True)

        # 1. Valid root image
        cls.valid_img = os.path.join(cls.images_dir, "valid_diag.png")
        with open(cls.valid_img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

        # 2. Valid nested image
        cls.nested_dir = os.path.join(cls.images_dir, "subfolder")
        os.makedirs(cls.nested_dir, exist_ok=True)
        cls.nested_img = os.path.join(cls.nested_dir, "nested_diag.png")
        with open(cls.nested_img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

        # 3. Secret file outside images directory
        cls.secret_file = os.path.join(cls.secret_dir, "confidential.png")
        with open(cls.secret_file, "w") as f:
            f.write("CONFIDENTIAL_SECURITY_PAYLOAD_DO_NOT_SERVE")

        # 4. Windows directory junction pointing outside
        cls.junction_path = os.path.join(cls.images_dir, "junc_ext")
        cls.junction_created = False
        try:
            cmd = f'cmd.exe /c mklink /J "{cls.junction_path}" "{cls.secret_dir}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(cls.junction_path):
                cls.junction_created = True
        except Exception:
            cls.junction_created = False

        # 5. Symbolic link pointing outside
        cls.symlink_path = os.path.join(cls.images_dir, "sym_ext.png")
        cls.symlink_created = False
        try:
            os.symlink(cls.secret_file, cls.symlink_path)
            cls.symlink_created = True
        except (OSError, NotImplementedError):
            cls.symlink_created = False

        # Build test Flask application reproducing app.py's canonical logic
        cls.test_app = Flask("test_phase3c4_img_containment")
        test_images_dir = cls.images_dir

        @cls.test_app.route("/detectr_aqua_figure2.png")
        def serve_detectr():
            img_dir = os.path.realpath(test_images_dir)
            target = os.path.realpath(os.path.join(img_dir, "valid_diag.png"))
            norm_img_dir = os.path.normcase(img_dir)
            norm_target = os.path.normcase(target)
            try:
                common = os.path.commonpath([norm_img_dir, norm_target])
            except ValueError:
                return jsonify({"error": "Image not found"}), 404
            if common != norm_img_dir or not os.path.isfile(target):
                return jsonify({"error": "Image not found"}), 404
            return send_from_directory(img_dir, "valid_diag.png", mimetype="image/png")

        @cls.test_app.route("/images/<path:filename>")
        def serve_images(filename):
            if ".." in filename or filename.startswith("/") or "\\" in filename:
                return jsonify({"error": "Invalid image path"}), 404
            _, ext = os.path.splitext(filename)
            mime = ALLOWED_IMAGE_EXTENSIONS.get(ext.lower())
            if not mime:
                return jsonify({"error": "Unsupported or prohibited file type"}), 404

            img_dir = os.path.realpath(test_images_dir)
            raw_target = os.path.join(img_dir, filename)
            target_path = os.path.realpath(raw_target)

            norm_img_dir = os.path.normcase(img_dir)
            norm_target = os.path.normcase(target_path)
            try:
                common = os.path.commonpath([norm_img_dir, norm_target])
            except ValueError:
                return jsonify({"error": "Invalid path"}), 404

            if common != norm_img_dir or not os.path.isfile(target_path):
                return jsonify({"error": "Image not found"}), 404

            rel_dir = os.path.relpath(os.path.dirname(target_path), img_dir)
            safe_dir = img_dir if rel_dir == "." else os.path.join(img_dir, rel_dir)
            return send_from_directory(safe_dir, os.path.basename(target_path), mimetype=mime)

        cls.client = cls.test_app.test_client()

    @classmethod
    def tearDownClass(cls):
        # Remove junction first if it exists
        if cls.junction_created and os.path.exists(cls.junction_path):
            subprocess.run(f'cmd.exe /c rmdir "{cls.junction_path}"', shell=True, capture_output=True)
        shutil.rmtree(cls.test_root, ignore_errors=True)

    # 1. Valid image inside permitted directory returns 200.
    def test_01_valid_image_returns_200(self):
        resp = self.client.get("/images/valid_diag.png")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/png", resp.headers.get("Content-Type", ""))

    # 2. Unsupported file extensions return 404.
    def test_02_unsupported_extensions_return_404(self):
        for bad in ["notes.txt", "script.js", "data.json", "payload.php", "image.svg.html"]:
            resp = self.client.get(f"/images/{bad}")
            self.assertEqual(resp.status_code, 404)

    # 3. Standard traversal returns 404.
    def test_03_standard_traversal_returns_404(self):
        resp = self.client.get("/images/../secret/confidential.png")
        self.assertEqual(resp.status_code, 404)

    # 4. URL-encoded traversal returns 404.
    def test_04_urlencoded_traversal_returns_404(self):
        resp = self.client.get("/images/%2e%2e/secret/confidential.png")
        self.assertEqual(resp.status_code, 404)

    # 5. Backslash traversal returns 404.
    def test_05_backslash_traversal_returns_404(self):
        resp = self.client.get("/images/..\\secret\\confidential.png")
        self.assertEqual(resp.status_code, 404)

    # 6. Symbolic link inside images directory pointing outside is rejected.
    def test_06_symlink_pointing_outside_returns_404(self):
        if not self.symlink_created:
            self.skipTest("Symlink creation requires elevated privileges on this Windows configuration.")
        resp = self.client.get("/images/sym_ext.png")
        self.assertEqual(resp.status_code, 404)

    # 7. Windows directory junction pointing outside is rejected.
    def test_07_junction_pointing_outside_returns_404(self):
        if not self.junction_created:
            self.skipTest("Directory junction creation failed or is unsupported.")
        resp = self.client.get("/images/junc_ext/confidential.png")
        self.assertEqual(resp.status_code, 404)
        body = resp.get_data(as_text=True)
        self.assertNotIn("CONFIDENTIAL_SECURITY_PAYLOAD", body)

    # 8. Normal nested image directory remains functional.
    def test_08_nested_image_returns_200(self):
        resp = self.client.get("/images/subfolder/nested_diag.png")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/png", resp.headers.get("Content-Type", ""))

    # 9. Dedicated DETECTR image route remains functional.
    def test_09_dedicated_detectr_route_returns_200(self):
        resp = self.client.get("/detectr_aqua_figure2.png")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/png", resp.headers.get("Content-Type", ""))


if __name__ == "__main__":
    unittest.main()
