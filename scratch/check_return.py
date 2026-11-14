with open('upload/core/impact_novelty_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def audit_novelty_and_soundness')
end_idx = text.find('def audit_proposal_logic_chain')
print(text[end_idx-500:end_idx])
