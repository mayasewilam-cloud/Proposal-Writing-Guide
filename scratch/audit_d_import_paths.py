import os
import re

for root, dirs, files in os.walk('upload'):
    for f in files:
        if f.endswith('.py') and 'backups' not in root:
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                # Check for module level DATA_DIR = get_data_dir() or similar
                matches = re.findall(r'^[A-Z_]+_DIR\s*=\s*.*', content, flags=re.MULTILINE)
                if matches:
                    print(f"{p}:")
                    for m in matches:
                        print(f"  {m}")
