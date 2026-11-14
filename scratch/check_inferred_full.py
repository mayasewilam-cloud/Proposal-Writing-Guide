with open('upload/core/paper_analyst_llm.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx2 = text.find('def generate_inferred_limitations')
next_def = text.find('\ndef ', idx2 + 10)
print(text[idx2:next_def])
