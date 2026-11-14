import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "test_phase3b_repair.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\r\n", "\n")

old_section = """    # =========================================================================
    # Task 7: CONN-SYNC-01 (Frontend Synchronization Audit)
    # =========================================================================
    def test_frontend_copies_are_identical(self):
        \"\"\"Verify upload/studio.js and upload/static/js/studio.js have identical SHA256 hashes.\"\"\"
        paths = ["upload/studio.js", "upload/static/js/studio.js"]
        hashes = []
        for p in paths:
            self.assertTrue(os.path.exists(p), f"Missing {p}")
            with open(p, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())

        self.assertEqual(hashes[0], hashes[1], "Root studio.js and static/js/studio.js must be identical")"""

new_section = """    # =========================================================================
    # Task 7: CONN-SYNC-01 / Repair E (Frontend Routing & Canonical Integrity Audit)
    # =========================================================================
    def test_canonical_frontend_served_at_routes(self):
        \"\"\"Verify Flask serves the canonical static/js/studio.js at /studio.js and /static/studio.js.\"\"\"
        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "r", encoding="utf-8") as f:
            canonical_content = f.read()

        # 1. /studio.js route returns canonical file
        resp1 = self.client.get("/studio.js")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.data.decode("utf-8"), canonical_content)

        # 2. /static/studio.js route returns canonical file
        resp2 = self.client.get("/static/studio.js")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data.decode("utf-8"), canonical_content)

    def test_canonical_frontend_scientific_integrity_features(self):
        \"\"\"Verify canonical static/js/studio.js contains required scientific integrity features.\"\"\"
        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "r", encoding="utf-8") as f:
            js = f.read()

        # Scientific integrity and citation status features
        self.assertIn("is_retracted", js)
        self.assertIn("RETRACTED", js)
        self.assertIn("Relevant Prior Art & Supporting Literature", js)
        self.assertIn("relationship_type", js)
        self.assertIn("relevance_explanation", js)

    def test_templates_do_not_reference_obsolete_copies(self):
        \"\"\"Verify templates and routes serve canonical frontend assets without unrouted paths.\"\"\"
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        for fname in os.listdir(template_dir):
            if fname.endswith(".html"):
                fpath = os.path.join(template_dir, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for line in content.splitlines():
                    if "script" in line and "studio.js" in line:
                        self.assertTrue(
                            'src="studio.js"' in line or 'src="static/js/studio.js"' in line or 'src="/static/studio.js"' in line,
                            f"Unexpected studio.js script tag in {fname}: {line}"
                        )"""

assert old_section in content, "old_section not found"
content = content.replace(old_section, new_section, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated upload/tests/test_phase3b_repair.py")
