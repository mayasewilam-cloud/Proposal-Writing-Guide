import os

path = os.path.abspath('upload/tests/test_agent_integration_and_auth.py')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

target = """class TestAgentIntegrationAndAuth(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-catalyst-2026"
        self.client = self.app.test_client()"""

replacement = """class TestAgentIntegrationAndAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        import shutil
        cls._orig_env = os.environ.get("BIOWRITER_DATA_DIR")
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_test_agent_auth_")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_dir

        src_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        if os.path.exists(src_data):
            for item in os.listdir(src_data):
                s = os.path.join(src_data, item)
                d = os.path.join(cls.test_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

    @classmethod
    def tearDownClass(cls):
        import shutil
        if cls._orig_env is None:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        else:
            os.environ["BIOWRITER_DATA_DIR"] = cls._orig_env
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-catalyst-2026"
        self.client = self.app.test_client()"""

assert target in c, "Target not found"
c = c.replace(target, replacement, 1)

target2 = """    def test_cors_headers_and_preflight_on_agent_api(self):
        \"\"\"Ensures CORS headers are present to allow file:// and cross-origin access.\"\"\"
        # 1. Test OPTIONS preflight
        resp_opt = self.client.options("/agent/api/analyze/13989")
        self.assertEqual(resp_opt.status_code, 200)
        self.assertEqual(resp_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", resp_opt.headers.get("Access-Control-Allow-Methods", ""))

        # 2. Test GET with CORS header
        resp_get = self.client.get("/agent/api/status/13989")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.headers.get("Access-Control-Allow-Origin"), "*")"""

replacement2 = """    def test_cors_headers_and_preflight_on_agent_api(self):
        \"\"\"Ensures CORS headers are present to allow file:// and cross-origin access.\"\"\"
        # 1. Test OPTIONS preflight
        resp_opt = self.client.options("/agent/api/analyze/13989")
        self.assertEqual(resp_opt.status_code, 200)
        self.assertEqual(resp_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", resp_opt.headers.get("Access-Control-Allow-Methods", ""))

        # 2. Test GET with CORS header
        resp_get = self.client.get("/agent/api/status/13989")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.headers.get("Access-Control-Allow-Origin"), "*")

    def test_production_guest_access_to_student_project_rejected(self):
        \"\"\"Unauthenticated guest querying registered student project in production must receive 403.\"\"\"
        orig_testing = self.app.testing
        try:
            self.app.testing = False
            resp_status = self.client.get("/agent/api/status/20230001")
            self.assertEqual(resp_status.status_code, 403)
            data = resp_status.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["error"], "Unauthorized access to project.")

            resp_dash = self.client.get("/agent/dashboard/20230001")
            self.assertEqual(resp_dash.status_code, 403)

            resp_dossier = self.client.get("/agent/dossier/20230001/view")
            self.assertEqual(resp_dossier.status_code, 403)
        finally:
            self.app.testing = orig_testing

    def test_production_student_teammate_and_nonteammate_access(self):
        \"\"\"Owner and teammates can access project, non-teammates receive 403.\"\"\"
        orig_testing = self.app.testing
        try:
            self.app.testing = False

            # Non-teammate 20230004
            with self.client.session_transaction() as sess:
                sess["student_id"] = "20230004"
                sess["role"] = "student"
                sess["faculty_authenticated"] = False
            resp = self.client.get("/agent/api/status/20230001")
            self.assertEqual(resp.status_code, 403)

            # Teammate 20230002 (member of L1-T1 with 20230001)
            with self.client.session_transaction() as sess:
                sess["student_id"] = "20230002"
                sess["role"] = "student"
                sess["faculty_authenticated"] = False
            resp = self.client.get("/agent/api/status/20230001")
            self.assertEqual(resp.status_code, 200)

            # Owner 20230001
            with self.client.session_transaction() as sess:
                sess["student_id"] = "20230001"
                sess["role"] = "student"
                sess["faculty_authenticated"] = False
            resp = self.client.get("/agent/api/status/20230001")
            self.assertEqual(resp.status_code, 200)

            # Faculty
            with self.client.session_transaction() as sess:
                sess["faculty_authenticated"] = True
                sess["role"] = "faculty"
            resp = self.client.get("/agent/api/status/20230001")
            self.assertEqual(resp.status_code, 200)
        finally:
            self.app.testing = orig_testing"""

assert target2 in c, "Target2 not found"
c = c.replace(target2, replacement2, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(c)

print("Updated test_agent_integration_and_auth.py successfully")
