with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

p_idx = text.find('elif is_petase:')
petase_text = text[p_idx:p_idx+8000]
import re
titles = re.findall(r'"title":\s*"([^"]+)"', petase_text)
authors = re.findall(r'"authors":\s*"([^"]+)"', petase_text)
for i in range(len(titles)):
    print(f"{i+1}. {titles[i]} | {authors[i] if i < len(authors) else ''}")
