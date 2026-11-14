with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def validate_citation_text')
ret_idx = text.find('return {', idx)
print(text[ret_idx:ret_idx+600])
