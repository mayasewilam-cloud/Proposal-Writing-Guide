import os
import re

for root, dirs, files in os.walk('.'):
    for f in files:
        if 'test_phase3b_repair' in f:
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                methods = re.findall(r'def (test_[a-zA-Z0-9_]+)', fp.read())
                print(f"{p}: {len(methods)} test methods")
                for m in methods:
                    print(f"  - {m}")
                print("-" * 40)
