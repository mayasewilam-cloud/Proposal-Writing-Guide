with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('if metadata and metadata.get("success"):')
if idx == -1:
    idx = text.find('metadata.get("success")')
print(text[idx-50:idx+1500])
