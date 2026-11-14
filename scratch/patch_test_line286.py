with open('upload/tests/test_phase4_1_4_scientific_integrity.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'self.assertTrue(lock_resp.get_json()["is_locked"])'
replacement = 'self.assertTrue(lock_resp.get_json()["is_locked_for_grading"])'

assert target in text
text = text.replace(target, replacement, 1)

with open('upload/tests/test_phase4_1_4_scientific_integrity.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated line 286 in test_phase4_1_4_scientific_integrity.py")
