with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def validate_citation_text')
print(text[idx+300:idx+1500])
