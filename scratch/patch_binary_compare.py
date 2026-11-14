import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "test_phase3b_repair.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

target = """        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "r", encoding="utf-8") as f:
            canonical_content = f.read()

        # 1. /studio.js route returns canonical file
        resp1 = self.client.get("/studio.js")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.data.decode("utf-8"), canonical_content)

        # 2. /static/studio.js route returns canonical file
        resp2 = self.client.get("/static/studio.js")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data.decode("utf-8"), canonical_content)"""

replacement = """        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "rb") as f:
            canonical_bytes = f.read()

        # 1. /studio.js route returns canonical file bytes
        resp1 = self.client.get("/studio.js")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.data, canonical_bytes)

        # 2. /static/studio.js route returns canonical file bytes
        resp2 = self.client.get("/static/studio.js")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data, canonical_bytes)"""

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated test_phase3b_repair.py successfully")
