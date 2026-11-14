with open('upload/core/draft_store.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'DRAFTS_DIR', text)
print(f"Occurrences of DRAFTS_DIR in draft_store.py: {len(matches)}")

for idx, line in enumerate(text.splitlines()[:50]):
    if 'DRAFTS_DIR' in line or 'get_drafts_dir' in line:
        print(f"Line {idx+1}: {line}")
