with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def get_benchmark_prior_art')
print(text[idx:])
