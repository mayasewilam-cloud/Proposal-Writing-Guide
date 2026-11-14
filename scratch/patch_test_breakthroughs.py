import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "test_breakthroughs.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize CRLF
content = content.replace("\r\n", "\n")

old_imports = """import unittest
import json
import os
import sys"""

new_imports = """import unittest
import json
import os
import sys
import tempfile
import shutil"""

assert old_imports in content, "old_imports not found"
content = content.replace(old_imports, new_imports, 1)

old_setup = """class TestBreakthroughsRadar(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()"""

new_setup = """class TestBreakthroughsRadar(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir.name
        self.orig_env = os.environ.get("BIOWRITER_ENV")
        os.environ["BIOWRITER_ENV"] = "testing"
        self.client = app.test_client()

    def tearDown(self):
        if self.orig_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = self.orig_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        if self.orig_env is not None:
            os.environ["BIOWRITER_ENV"] = self.orig_env
        else:
            os.environ.pop("BIOWRITER_ENV", None)
        self.temp_dir.cleanup()"""

assert old_setup in content, "old_setup not found"
content = content.replace(old_setup, new_setup, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated upload/tests/test_breakthroughs.py")
