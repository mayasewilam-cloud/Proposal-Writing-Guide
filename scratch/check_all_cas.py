with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

cas_idx = text.find('elif is_cas_diagnostic:')
pet_idx = text.find('elif is_petase:')
cas_text = text[cas_idx:pet_idx]
import re
titles = re.findall(r'"title":\s*"([^"]+)"', cas_text)
authors = re.findall(r'"authors":\s*"([^"]+)"', cas_text)
for i in range(len(titles)):
    print(f"{i+1}. {titles[i]} | {authors[i] if i < len(authors) else ''}")
