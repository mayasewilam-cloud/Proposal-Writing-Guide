import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "impact_novelty_engine.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

# Find the cas12a prior approaches
cas_start = text.find('        prior_approaches = [\n            {\n                "id": "PA-01"')
cas_end = text.find('        diff_summary = "Point-of-Care Acellular Specificity:')
cas_approaches_str = text[cas_start + len('        prior_approaches = '):cas_end].strip()

# Find petase prior approaches
petase_start = text.find('        prior_approaches = [\n            {\n                "id": "PET-01"')
petase_end = text.find('        diff_summary = "Engineered Ambient Biocatalysis:')
petase_approaches_str = text[petase_start + len('        prior_approaches = '):petase_end].strip()

print(f"Found cas_approaches_str ({len(cas_approaches_str)} chars)")
print(f"Found petase_approaches_str ({len(petase_approaches_str)} chars)")

# Module-level definition
benchmark_prior_art_def = f"""BENCHMARK_PRIOR_ART = {{
    "cas12a_detection": {cas_approaches_str},
    "petase_engineering": {petase_approaches_str}
}}
"""

# Insert BENCHMARK_PRIOR_ART right after VALID_RELATIONSHIP_TYPES definition
vtypes_end = text.find('VALID_RELATIONSHIP_TYPES = {\n    "direct_prior_art",\n    "enabling_technology",\n    "target_biology",\n    "adjacent_background"\n}\n')
assert vtypes_end != -1, "VALID_RELATIONSHIP_TYPES not found"
insert_pos = vtypes_end + len('VALID_RELATIONSHIP_TYPES = {\n    "direct_prior_art",\n    "enabling_technology",\n    "target_biology",\n    "adjacent_background"\n}\n')

new_text = text[:insert_pos] + "\n" + benchmark_prior_art_def + "\n" + text[insert_pos:]

# Now replace the inline assignments in audit_novelty_and_soundness
old_cas_block = text[cas_start:cas_end]
new_cas_block = '        prior_approaches = [dict(x) for x in BENCHMARK_PRIOR_ART["cas12a_detection"]]\n'
new_text = new_text.replace(old_cas_block, new_cas_block, 1)

old_petase_block = text[petase_start:petase_end]
new_petase_block = '        prior_approaches = [dict(x) for x in BENCHMARK_PRIOR_ART["petase_engineering"]]\n'
new_text = new_text.replace(old_petase_block, new_petase_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_text)

print("Successfully updated impact_novelty_engine.py with module-level BENCHMARK_PRIOR_ART!")
