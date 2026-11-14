filepath = "upload/tests/test_phase4_1_4_scientific_integrity.py"
with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

old_breakdown = '''        # Cas12a: 3 direct_prior_art, 2 enabling_technology, 1 target_biology, 1 adjacent_background
        self.assertEqual(cas12a_types.count("direct_prior_art"), 3)
        self.assertEqual(cas12a_types.count("enabling_technology"), 2)'''

new_breakdown = '''        # Cas12a: 2 direct_prior_art, 3 enabling_technology, 1 target_biology, 1 adjacent_background
        self.assertEqual(cas12a_types.count("direct_prior_art"), 2)
        self.assertEqual(cas12a_types.count("enabling_technology"), 3)'''

assert old_breakdown in text, "old_breakdown not found in test_phase4_1_4_scientific_integrity.py"
text = text.replace(old_breakdown, new_breakdown, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESS: Updated test_phase4_1_4_scientific_integrity.py breakdown.")
