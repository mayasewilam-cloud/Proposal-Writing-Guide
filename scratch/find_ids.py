import re
with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

ids = re.findall(r'"id":\s*"([^"]+)"', text)
print("Record IDs:", ids)
