import re
with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Find PETase section
p_idx = text.find('elif is_petase:')
petase_text = text[p_idx:]
petase_titles = re.findall(r'"title":\s*"([^"]+)"', petase_text[:3000])
print("PETase titles:", petase_titles)
