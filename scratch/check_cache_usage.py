with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('_CITATION_STATUS_CACHE')
idx2 = text.find('_CITATION_STATUS_CACHE', idx + 25)
print(text[idx2-50:idx2+600])
