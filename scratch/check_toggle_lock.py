with open('upload/core/draft_store.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def toggle_draft_lock')
print(text[idx:idx+600])
