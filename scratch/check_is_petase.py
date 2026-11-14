with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('is_cas_diagnostic =')
print(text[idx:idx+800])
