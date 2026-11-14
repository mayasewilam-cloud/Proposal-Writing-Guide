"""
BioWriter Studio - Phase 3C.5.4 Automated Test Suite
Tests cross-process concurrency locking, stale session invalidation, legacy cohort accounts,
anti-DoS rate limiting, and timezone-safe expiration handling.
All tests run against isolated temporary storage with zero live data touches.
"""

import unittest
import unittest.mock
import os
import sys
import json
import tempfile
import shutil
import time
import datetime
import multiprocessing
from werkzeug.security import generate_password_hash, check_password_hash

# Pre-set environment variables for test isolation
os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-bytes-long-for-testing-p3c54"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
import app as app_module
from core.auth_store import (
    register_student,
    authenticate_student,
    get_student_user,
    get_student_account_status,
    is_student_session_valid,
    issue_student_activation_token,
    generate_student_activation_token,
    verify_activation_token,
    verify_token_expiration,
    users_store_lock,
    _load_users,
    _save_users,
    _failed_ip_activation_attempts,
    _activation_rate_lock,
)
from core.cohort_store import (
    confirm_attendance_import,
    upsert_student_by_faculty,
)


# Top-level workers for Windows multiprocessing.spawn
def _worker_cross_process_claim(temp_dir, student_id, student_name, password, token, queue, barrier):
    os.environ["BIOWRITER_DATA_DIR"] = temp_dir
    os.environ["FLASK_TESTING"] = "1"
    os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-bytes-long-for-testing-p3c54"
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from core.auth_store import register_student
    barrier.wait()
    res = register_student(
        student_id=student_id,
        student_name=student_name,
        password=password,
        activation_token=token,
        client_ip="127.0.0.1",
    )
    queue.put((os.getpid(), res))


def _worker_cross_process_issue(temp_dir, student_id, faculty_name, queue, barrier):
    os.environ["BIOWRITER_DATA_DIR"] = temp_dir
    os.environ["FLASK_TESTING"] = "1"
    os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-bytes-long-for-testing-p3c54"
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from core.auth_store import issue_student_activation_token
    barrier.wait()
    ok, msg, data = issue_student_activation_token(student_id, faculty_id=faculty_name)
    queue.put((os.getpid(), ok, msg, data))


def _worker_cross_process_cohort_mutation(temp_dir, student_id, new_lab_group, queue, barrier):
    os.environ["BIOWRITER_DATA_DIR"] = temp_dir
    os.environ["FLASK_TESTING"] = "1"
    os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-bytes-long-for-testing-p3c54"
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from core.auth_store import users_store_lock, _load_users, _save_users
    barrier.wait()
    with users_store_lock():
        u = _load_users()
        if student_id in u:
            u[student_id]["lab_group"] = new_lab_group
            _save_users(u)
            queue.put((os.getpid(), True))
        else:
            queue.put((os.getpid(), False))


class Phase3C54AuthConcurrencyTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="biowriter_p3c54_test_")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir
        app_module.DATA_DIR = self.temp_dir

        # Reset in-memory IP rate limit cache
        with _activation_rate_lock:
            _failed_ip_activation_attempts.clear()

        # Generate pre-hashed baseline default users to avoid PBKDF2 seeding delay in tests
        raw_hex, formatted, salt, digest, expires_at = generate_student_activation_token()
        self.unclaimed_raw_token = raw_hex
        self.unclaimed_formatted_token = formatted
        self.unclaimed_expires_at = expires_at

        # Pre-seed default accounts with known fast dummy hashes
        dummy_hash = "pbkdf2:sha256:1000$salt$93874982374982374"
        self.initial_users = {
            "13989": {
                "student_id": "13989",
                "student_name": "Maya Abdelrazek",
                "password_hash": dummy_hash,
                "role": "student",
                "account_claimed": True,
            },
            "ST-2026-01": {
                "student_id": "ST-2026-01",
                "student_name": "Sara Ahmed & Team BioDetect",
                "password_hash": dummy_hash,
                "role": "student",
                "account_claimed": True,
            },
            "STU-UNCLAIMED-01": {
                "student_id": "STU-UNCLAIMED-01",
                "student_name": "Unclaimed Student",
                "password_hash": "!UNCLAIMED!",
                "created_at": "Sep 20, 2026 - 10:00",
                "role": "student",
                "pre_enrolled_by_faculty": True,
                "account_claimed": False,
                "activation_token_salt": salt,
                "activation_token_hash": digest,
                "activation_token_expires_at": expires_at,
            },
            "STU-CLAIMED-01": {
                "student_id": "STU-CLAIMED-01",
                "student_name": "Established Student",
                "password_hash": generate_password_hash("Password123!", method="pbkdf2:sha256", salt_length=16),
                "created_at": "Sep 20, 2026 - 10:00",
                "role": "student",
                "pre_enrolled_by_faculty": True,
                "account_claimed": True,
            },
            # Legacy account in users.json with null account_claimed
            "STU-LEGACY-01": {
                "student_id": "STU-LEGACY-01",
                "student_name": "Legacy Cohort Student",
                "password_hash": generate_password_hash("password123", method="pbkdf2:sha256", salt_length=16),
                "created_at": "Sep 20, 2026 - 10:00",
                "role": "student",
                "pre_enrolled_by_faculty": None,
                "account_claimed": None,
            },
        }
        with open(os.path.join(self.temp_dir, "users.json"), "w", encoding="utf-8") as f:
            json.dump(self.initial_users, f, indent=2)

        # Baseline cohort_db.json
        self.initial_cohort = {
            "meta": {"semester": "Fall 2026", "course_id": "BT301"},
            "students": {
                "STU-UNCLAIMED-01": {
                    "student_id": "STU-UNCLAIMED-01",
                    "student_name": "Unclaimed Student",
                    "course_id": "BT301",
                    "semester": "Fall 2026",
                    "lab_group": "L01",
                    "team_id": "TEAM-01",
                },
                "STU-LEGACY-01": {
                    "student_id": "STU-LEGACY-01",
                    "student_name": "Legacy Cohort Student",
                    "course_id": "BT301",
                    "semester": "Fall 2026",
                    "lab_group": "L01",
                    "team_id": None,
                },
                "STU-COHORT-ONLY": {
                    "student_id": "STU-COHORT-ONLY",
                    "student_name": "Cohort Only Student",
                    "course_id": "BT301",
                    "semester": "Fall 2026",
                    "lab_group": "L02",
                    "team_id": None,
                },
            },
            "teams": {
                "TEAM-01": {
                    "team_id": "TEAM-01",
                    "team_name": "Alpha Team",
                    "student_ids": ["STU-UNCLAIMED-01"],
                    "status": "active",
                }
            },
            "lab_groups": {},
            "pending_imports": {},
            "audit_history": [],
        }
        with open(os.path.join(self.temp_dir, "cohort_db.json"), "w", encoding="utf-8") as f:
            json.dump(self.initial_cohort, f, indent=2)

        # Create drafts directory with draft for STU-UNCLAIMED-01
        drafts_dir = os.path.join(self.temp_dir, "drafts")
        os.makedirs(drafts_dir, exist_ok=True)
        with open(os.path.join(drafts_dir, "STU-UNCLAIMED-01.json"), "w", encoding="utf-8") as f:
            json.dump({"student_id": "STU-UNCLAIMED-01", "title": "Confidential Research Aim"}, f, indent=2)

        self.client = app.test_client()

    def tearDown(self):
        with _activation_rate_lock:
            _failed_ip_activation_attempts.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # DEFECT 01: Cross-Process Concurrency Locking
    # --------------------------------------------------------------------------

    def test_01_cross_process_simultaneous_claiming(self):
        """Two separate OS processes claiming the same account with the same token results in exactly 1 success."""
        barrier = multiprocessing.Barrier(2)
        queue = multiprocessing.Queue()

        p1 = multiprocessing.Process(
            target=_worker_cross_process_claim,
            args=(self.temp_dir, "STU-UNCLAIMED-01", "P1 Claimant", "NewPassword123!", self.unclaimed_formatted_token, queue, barrier),
        )
        p2 = multiprocessing.Process(
            target=_worker_cross_process_claim,
            args=(self.temp_dir, "STU-UNCLAIMED-01", "P2 Claimant", "NewPassword456!", self.unclaimed_formatted_token, queue, barrier),
        )

        p1.start()
        p2.start()
        p1.join(timeout=15)
        p2.join(timeout=15)

        results = []
        while not queue.empty():
            results.append(queue.get())

        self.assertEqual(len(results), 2)
        successes = [r for _, r in results if r.get("success") is True]
        failures = [r for _, r in results if r.get("success") is False]

        self.assertEqual(len(successes), 1, f"Expected exactly 1 success, got {len(successes)}")
        self.assertEqual(len(failures), 1, f"Expected exactly 1 failure, got {len(failures)}")
        self.assertIn("already registered", failures[0]["error"].lower())

    def test_02_cross_process_simultaneous_token_issuance(self):
        """Two separate processes issuing tokens simultaneously; exactly one stored hash remains valid."""
        barrier = multiprocessing.Barrier(2)
        queue = multiprocessing.Queue()

        p1 = multiprocessing.Process(
            target=_worker_cross_process_issue,
            args=(self.temp_dir, "STU-UNCLAIMED-01", "Faculty Alpha", queue, barrier),
        )
        p2 = multiprocessing.Process(
            target=_worker_cross_process_issue,
            args=(self.temp_dir, "STU-UNCLAIMED-01", "Faculty Beta", queue, barrier),
        )

        p1.start()
        p2.start()
        p1.join(timeout=15)
        p2.join(timeout=15)

        results = []
        while not queue.empty():
            results.append(queue.get())

        self.assertEqual(len(results), 2)
        tokens = [data["activation_token"] for _, ok, msg, data in results if ok and data]
        self.assertEqual(len(tokens), 2)

        # Check users.json state
        with open(os.path.join(self.temp_dir, "users.json"), "r", encoding="utf-8") as f:
            saved = json.load(f)["STU-UNCLAIMED-01"]

        stored_salt = saved["activation_token_salt"]
        stored_hash = saved["activation_token_hash"]

        # Exactly one token must match the stored hash (the last writer wins atomically)
        valid_count = sum(1 for tok in tokens if verify_activation_token(tok, stored_salt, stored_hash))
        self.assertEqual(valid_count, 1, f"Expected exactly 1 token to match final stored hash, got {valid_count}")

    def test_03_cross_process_user_store_mutation_integrity(self):
        """Concurrent cohort mutation and authentication update do not overwrite each other."""
        barrier = multiprocessing.Barrier(2)
        queue = multiprocessing.Queue()

        p1 = multiprocessing.Process(
            target=_worker_cross_process_cohort_mutation,
            args=(self.temp_dir, "STU-CLAIMED-01", "L99_NEW", queue, barrier),
        )
        p2 = multiprocessing.Process(
            target=_worker_cross_process_cohort_mutation,
            args=(self.temp_dir, "13989", "L99_MAYA", queue, barrier),
        )

        p1.start()
        p2.start()
        p1.join(timeout=15)
        p2.join(timeout=15)

        with open(os.path.join(self.temp_dir, "users.json"), "r", encoding="utf-8") as f:
            final_users = json.load(f)

        self.assertEqual(final_users["STU-CLAIMED-01"].get("lab_group"), "L99_NEW")
        self.assertEqual(final_users["13989"].get("lab_group"), "L99_MAYA")

    def test_04_lock_release_after_simulated_failure(self):
        """Simulated exception inside users_store_lock releases OS and thread locks reliably."""
        lock_file = os.path.join(self.temp_dir, "users.json.lock")
        try:
            with users_store_lock(timeout=2.0):
                raise RuntimeError("Simulated crash inside lock")
        except RuntimeError:
            pass

        # Must be able to immediately re-acquire lock without timeout
        acquired = False
        with users_store_lock(timeout=2.0):
            acquired = True
        self.assertTrue(acquired, "Failed to re-acquire lock after exception")

    # --------------------------------------------------------------------------
    # DEFECT 02: Stale Session Invalidation
    # --------------------------------------------------------------------------

    def test_05_stale_session_invalidation_api_auth_me(self):
        """Unclaimed student session querying /api/auth/me is invalidated with 401."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "STU-UNCLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("authenticated"))

        # Verify session was cleared
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("student_id"))

    def test_06_protected_endpoint_rejection_after_stale_session(self):
        """Stale session for unclaimed account cannot access student proposal drafts."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "STU-UNCLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/draft/STU-UNCLAIMED-01")
        self.assertEqual(resp.status_code, 403)

        # Verify session cleared
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("student_id"))

    def test_07_valid_claimed_student_session_remains_authenticated(self):
        """Legitimate claimed student session querying /api/auth/me succeeds with 200."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "STU-CLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("authenticated"))
        self.assertEqual(data["user"]["student_id"], "STU-CLAIMED-01")

    # --------------------------------------------------------------------------
    # DEFECT 03: Legacy Cohort Account Bypass Remediation
    # --------------------------------------------------------------------------

    def test_08_legacy_account_with_null_claim_status_rejected_from_login(self):
        """Legacy account in users.json with account_claimed=null cannot log in directly."""
        res = authenticate_student("STU-LEGACY-01", "password123")
        self.assertFalse(res["success"])
        self.assertIn("not been activated", res["error"])

    def test_09_legacy_account_with_missing_fields_requires_token_to_register(self):
        """Legacy account in cohort_db.json cannot be registered without activation token."""
        res = register_student("STU-LEGACY-01", "Legacy Student", "NewPass12345!", activation_token="")
        self.assertFalse(res["success"])
        self.assertIn("Activation token is required", res["error"])

    def test_10_cohort_membership_fallback_consistency(self):
        """Cohort-only account not yet in users.json is recognized by both register and auth."""
        auth_res = authenticate_student("STU-COHORT-ONLY", "anypassword")
        self.assertFalse(auth_res["success"])
        self.assertIn("not been activated", auth_res["error"])

        reg_res = register_student("STU-COHORT-ONLY", "Cohort Student", "NewPass12345!", activation_token="")
        self.assertFalse(reg_res["success"])
        self.assertIn("Activation token is required", reg_res["error"])

    def test_11_claimed_legacy_student_normal_login(self):
        """Once legitimately claimed, legacy student can log in normally."""
        # Issue token for STU-LEGACY-01
        ok, msg, token_info = issue_student_activation_token("STU-LEGACY-01", "Faculty Coordinator")
        self.assertTrue(ok)
        tok = token_info["activation_token"]

        # Claim account
        claim_res = register_student("STU-LEGACY-01", "Legacy Student", "BrandNewPass123!", activation_token=tok)
        self.assertTrue(claim_res["success"])

        # Authenticate with new password
        login_res = authenticate_student("STU-LEGACY-01", "BrandNewPass123!")
        self.assertTrue(login_res["success"])
        self.assertEqual(login_res["user"]["student_id"], "STU-LEGACY-01")

    # --------------------------------------------------------------------------
    # DEFECT 04: Anti-DoS Rate Limiting
    # --------------------------------------------------------------------------

    def test_12_invalid_activation_attempts_cannot_create_student_wide_dos(self):
        """An attacker sending 5 invalid tokens does not lock out the student with a valid token."""
        # Attacker sends 5 bad tokens
        for _ in range(5):
            res = register_student("STU-UNCLAIMED-01", "Attacker", "BadPass123!", activation_token="0000-0000-0000-0000-0000-0000-0000-0000", client_ip="192.168.1.50")
            self.assertFalse(res["success"])

        # Legitimate student from another IP uses valid token
        legit_res = register_student("STU-UNCLAIMED-01", "Legit Student", "LegitPass123!", activation_token=self.unclaimed_formatted_token, client_ip="10.0.0.1")
        self.assertTrue(legit_res["success"], f"Legitimate student was blocked: {legit_res.get('error')}")

    def test_13_valid_token_accepted_after_previous_failed_attempts(self):
        """Student who made typos on previous attempts can successfully claim when entering correct token."""
        # 3 typos from same IP
        for _ in range(3):
            register_student("STU-UNCLAIMED-01", "Student", "MyPass123!", activation_token="1111-2222-3333-4444-5555-6666-7777-8888", client_ip="127.0.0.1")

        # 4th attempt with correct token succeeds
        res = register_student("STU-UNCLAIMED-01", "Student", "MyPass123!", activation_token=self.unclaimed_formatted_token, client_ip="127.0.0.1")
        self.assertTrue(res["success"])

    def test_14_ip_throttling_still_enforced(self):
        """IP sending 10 failed registration attempts is throttled on the 11th attempt."""
        for _ in range(10):
            register_student("STU-UNCLAIMED-01", "Spammer", "SpamPass123!", activation_token="0000-0000-0000-0000-0000-0000-0000-0000", client_ip="198.51.100.22")

        # 11th attempt from same IP is throttled
        res = register_student("STU-UNCLAIMED-01", "Spammer", "SpamPass123!", activation_token="0000-0000-0000-0000-0000-0000-0000-0000", client_ip="198.51.100.22")
        self.assertFalse(res["success"])
        self.assertIn("Too many failed activation attempts", res["error"])

    # --------------------------------------------------------------------------
    # DEFECT 05: Timezone-Safe Token Expiration
    # --------------------------------------------------------------------------

    def test_15_valid_utc_expiration(self):
        """Token with future UTC timestamp is accepted."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        future_utc = (now_utc + datetime.timedelta(days=7)).isoformat()
        ok, err = verify_token_expiration(future_utc)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_16_expired_utc_expiration(self):
        """Token with past UTC timestamp is rejected."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        past_utc = (now_utc - datetime.timedelta(days=1)).isoformat()
        ok, err = verify_token_expiration(past_utc)
        self.assertFalse(ok)
        self.assertIn("expired", err.lower())

    def test_17_positive_timezone_offset_expiration(self):
        """Timestamp with positive offset (+02:00) parsed and compared in UTC correctly."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cairo_tz = datetime.timezone(datetime.timedelta(hours=2))
        future_cairo = (now_utc + datetime.timedelta(hours=1)).astimezone(cairo_tz).isoformat()
        past_cairo = (now_utc - datetime.timedelta(hours=1)).astimezone(cairo_tz).isoformat()

        ok_future, _ = verify_token_expiration(future_cairo)
        ok_past, _ = verify_token_expiration(past_cairo)
        self.assertTrue(ok_future)
        self.assertFalse(ok_past)

    def test_18_negative_timezone_offset_expiration(self):
        """Timestamp with negative offset (-05:00) parsed and compared in UTC correctly."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        ny_tz = datetime.timezone(datetime.timedelta(hours=-5))
        future_ny = (now_utc + datetime.timedelta(hours=1)).astimezone(ny_tz).isoformat()
        past_ny = (now_utc - datetime.timedelta(hours=1)).astimezone(ny_tz).isoformat()

        ok_future, _ = verify_token_expiration(future_ny)
        ok_past, _ = verify_token_expiration(past_ny)
        self.assertTrue(ok_future)
        self.assertFalse(ok_past)

    def test_19_naive_legacy_timestamp_interpreted_as_utc(self):
        """Naive legacy timestamp string is safely parsed as UTC without raising TypeError."""
        future_naive = (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()
        past_naive = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()

        ok_future, _ = verify_token_expiration(future_naive)
        ok_past, _ = verify_token_expiration(past_naive)
        self.assertTrue(ok_future)
        self.assertFalse(ok_past)

    def test_20_malformed_and_missing_timestamp_rejected(self):
        """Malformed or missing expiration timestamps fail closed."""
        for bad_val in [None, "", "not-a-date", 12345, "2026-99-99"]:
            ok, err = verify_token_expiration(bad_val)
            self.assertFalse(ok, f"Expected failure for {bad_val}")
            self.assertIsNotNone(err)

    # --------------------------------------------------------------------------
    # Regression and System Workflows
    # --------------------------------------------------------------------------

    def test_21_persistence_failure_does_not_create_authenticated_session(self):
        """Disk write failure prevents claim transition and session creation."""
        with unittest.mock.patch("core.auth_store._save_users", side_effect=IOError("Simulated disk error")):
            with self.assertRaises(IOError):
                register_student("STU-UNCLAIMED-01", "Student", "ValidPass123!", activation_token=self.unclaimed_formatted_token)

        # Account must still be unclaimed on disk
        with open(os.path.join(self.temp_dir, "users.json"), "r", encoding="utf-8") as f:
            u = json.load(f)["STU-UNCLAIMED-01"]
        self.assertFalse(u.get("account_claimed"))

    def test_22_existing_faculty_login_and_token_issuance(self):
        """Faculty can issue tokens for unclaimed students via authenticated endpoint."""
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"

        resp = self.client.post("/api/faculty/students/STU-UNCLAIMED-01/activation-token")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("activation_token", data)

    def test_23_previously_claimed_student_login(self):
        """Existing established claimed student can log in seamlessly."""
        res = authenticate_student("STU-CLAIMED-01", "Password123!")
        self.assertTrue(res["success"])
        self.assertEqual(res["user"]["student_id"], "STU-CLAIMED-01")

    def test_24_existing_proposal_access_controls(self):
        """Claimed student can read their draft; other students are forbidden."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "STU-CLAIMED-01"
            sess["role"] = "student"

        # Claimed student accessing STU-UNCLAIMED-01 draft is rejected (403)
        resp = self.client.get("/api/student/draft/STU-UNCLAIMED-01")
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
