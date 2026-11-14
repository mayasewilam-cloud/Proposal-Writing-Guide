with open('upload/core/draft_store.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def toggle_draft_lock')
ret_idx = text.find('return {', idx)
print(text[ret_idx:ret_idx+400])
