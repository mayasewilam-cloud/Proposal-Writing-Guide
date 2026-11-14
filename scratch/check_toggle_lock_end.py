with open('upload/core/draft_store.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('json.dump(draft, f')
print(text[idx:idx+300])
