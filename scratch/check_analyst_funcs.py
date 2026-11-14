with open('upload/core/paper_analyst_llm.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def analyze_animal_model_context')
print(text[idx:idx+800])

idx2 = text.find('def generate_inferred_limitations')
print(text[idx2:idx2+600])
