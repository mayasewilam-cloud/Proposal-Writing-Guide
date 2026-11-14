import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('upload/core/paper_analyst_llm.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def analyze_animal_model_context')
next_def = text.find('\ndef ', idx + 10)
print(text[idx:next_def])
