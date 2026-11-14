import re

bak_path = r"C:\Users\Lenovo\.gemini\antigravity\brain\d4f217ee-1064-43a4-b719-3a8627874e18\scratch\phase4_1_4_backups\tests_test_phase3b_repair.py.20261114_181505.bak"
curr_path = "upload/tests/test_phase3b_repair.py"

with open(bak_path, "r", encoding="utf-8") as f:
    bak_text = f.read()

with open(curr_path, "r", encoding="utf-8") as f:
    curr_text = f.read()

bak_methods = re.findall(r'def (test_[a-zA-Z0-9_]+)', bak_text)
curr_methods = re.findall(r'def (test_[a-zA-Z0-9_]+)', curr_text)

print(f"Backup test methods ({len(bak_methods)}):")
for m in bak_methods:
    print(f"  - {m}")

print(f"\nCurrent test methods ({len(curr_methods)}):")
for m in curr_methods:
    print(f"  - {m}")

print("\nMethods in backup but NOT in current:")
for m in bak_methods:
    if m not in curr_methods:
        print(f"  MISSING: {m}")

print("\nMethods in current but NOT in backup:")
for m in curr_methods:
    if m not in bak_methods:
        print(f"  ADDED: {m}")
