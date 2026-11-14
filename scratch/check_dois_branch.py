with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('if not dois:')
print(text[idx+200:idx+1500])
