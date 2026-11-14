import os

path = os.path.abspath('upload/tests/test_enhancements.py')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

target = """class TestProposalEnhancements(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.test_sid = 'TEST-ENHANCE-01'
        self.sample_data = {
            'student_id': self.test_sid,
            'student_name': 'Test Researcher',
            'title': 'Synthetic Biosensor for Water Analysis',
            'modality': 'Cell-Free Diagnostics',
            'chassis': 'Cell-free Tx-Tl lysate',
            'tool': 'Cas12a fluorescent assay',
            'target': 'Antimicrobial resistance marker'
        }
        save_student_draft(self.test_sid, self.sample_data)

    def tearDown(self):
        drafts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'drafts'))
        fpath = os.path.join(drafts_dir, f'{self.test_sid}.json')
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass"""

replacement = """class TestProposalEnhancements(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        import shutil
        cls._orig_env = os.environ.get("BIOWRITER_DATA_DIR")
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_test_enhance_")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_dir

        cls._orig_app_testing = app.testing
        app.testing = True

        src_data = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
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
        app.testing = cls._orig_app_testing
        if cls._orig_env is None:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        else:
            os.environ["BIOWRITER_DATA_DIR"] = cls._orig_env
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        self.client = app.test_client()
        self.test_sid = 'TEST-ENHANCE-01'
        self.sample_data = {
            'student_id': self.test_sid,
            'student_name': 'Test Researcher',
            'title': 'Synthetic Biosensor for Water Analysis',
            'modality': 'Cell-Free Diagnostics',
            'chassis': 'Cell-free Tx-Tl lysate',
            'tool': 'Cas12a fluorescent assay',
            'target': 'Antimicrobial resistance marker'
        }
        save_student_draft(self.test_sid, self.sample_data)

    def tearDown(self):
        from core.draft_store import get_drafts_dir
        fpath = os.path.join(get_drafts_dir(), f'{self.test_sid}.json')
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass"""

assert target in c, "Target not found in test_enhancements.py"
c = c.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(c)

print("Updated test_enhancements.py successfully")
