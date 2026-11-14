with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('if metadata.get("is_retracted"):')
if idx == -1:
    idx = text.find('is_retracted')
print(text[idx-50:idx+600])
