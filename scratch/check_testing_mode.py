with open('upload/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def _is_testing_mode')
print(text[idx:idx+400])
