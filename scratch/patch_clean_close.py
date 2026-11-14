with open('upload/tests/test_phase4_1_4_scientific_integrity.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """        r1 = self.client.get("/studio.js")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data, expected_bytes)

        r2 = self.client.get("/static/studio.js")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data, expected_bytes)"""

replacement = """        r1 = self.client.get("/studio.js")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data, expected_bytes)
        r1.close()

        r2 = self.client.get("/static/studio.js")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data, expected_bytes)
        r2.close()"""

assert target in text
text = text.replace(target, replacement, 1)

with open('upload/tests/test_phase4_1_4_scientific_integrity.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Added r1.close() and r2.close()")
