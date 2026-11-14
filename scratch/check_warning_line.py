with open('upload/tests/test_phase4_1_4_scientific_integrity.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('test_canonical_studio_js_served_by_routes')
print(text[idx:idx+600])
