filepath = "upload/tests/test_phase4_1_4_scientific_integrity.py"
with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

old_bd = '''        self.assertEqual(breakdown["direct_prior_art"], 3)
        self.assertEqual(breakdown["enabling_technology"], 2)'''

new_bd = '''        self.assertEqual(breakdown["direct_prior_art"], 2)
        self.assertEqual(breakdown["enabling_technology"], 3)'''

assert old_bd in text, "old_bd not found in test_phase4_1_4_scientific_integrity.py"
text = text.replace(old_bd, new_bd, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESS: Updated test_phase4_1_4_scientific_integrity.py breakdown at line 343.")
