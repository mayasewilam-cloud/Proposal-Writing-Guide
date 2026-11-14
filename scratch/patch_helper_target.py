with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_s = 'target="PET"'
new_s = 'target="Post-consumer PET plastic bottles"'
assert old_s in text
text = text.replace(old_s, new_s, 1)

with open('upload/core/impact_novelty_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated get_benchmark_prior_art in impact_novelty_engine.py")
