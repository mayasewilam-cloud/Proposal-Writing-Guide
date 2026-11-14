with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def audit_novelty_and_soundness')
next_def = text.find('\ndef ', idx + 10)
print(text[next_def-500:next_def])
