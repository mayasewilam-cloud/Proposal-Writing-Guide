with open('upload/tests/test_phase4_1_2_scientific_integrity.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(295, 345):
    print(f"{i+1}: {repr(lines[i])}")
