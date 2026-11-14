import re

path = 'upload/core/paper_analyst_llm.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_func_pattern = r'def analyze_animal_model_context\(text: str\) -> Dict\[str, Any\]:.*?(?=\ndef generate_inferred_limitations)'

new_func = '''def analyze_animal_model_context(text: str) -> Dict[str, Any]:
    """
    Analyzes scientific text for animal-model mentions and determines context:
    - 'performed': animal experiments executed in this study
    - 'excluded': explicitly excluded or not conducted (including non-animal models and pronominal negation)
    - 'future_work': planned or proposed for future studies
    - 'background_only': discussed only as prior literature / external study limitation
    - 'mixed': both positive execution and negative exclusion/future/background mentioned
    - 'none': no animal models mentioned
    - 'ambiguous': animal model terms mentioned but context is unclear
    """
    if not isinstance(text, str) or not text.strip():
        return {"status": "none", "matches": []}

    animal_terms_pattern = r"(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents|rabbit|rabbits|new\\s+zealand\\s+white\\s+rabbits?|zebrafish|danio\\s+rerio)"
    animal_regex = re.compile(rf"\\b{animal_terms_pattern}\\b", re.IGNORECASE)

    matches = animal_regex.findall(text)
    if not matches:
        return {"status": "none", "matches": []}

    # Sentence-level check: Pronominal negation linking antecedent animal mention across contrastive clauses
    pronominal_exclusion = bool(re.search(
        rf"\\b{animal_terms_pattern}\\b[^.;\\n]+?\\b(?:but|however|although|whereas|while)\\b[^.;\\n]+?\\b(?:do|does|did|have|has|had|we|authors?|study|investigation|paper|work)\\s+(?:not\\s+|did\\s+not\\s+|does\\s+not\\s+|do\\s+not\\s+)?(?:use|employ|perform|conduct|utilize|include|involve|using)\\s+(?:them|these|it)\\b",
        text,
        re.IGNORECASE
    ))

    # Protect abbreviations with periods like "et al.", "i.e.", "e.g." before clause splitting
    protected_text = re.sub(r"\\bet\\s+al\\.", "et_al", text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\\be\\.g\\.", "eg", protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\\bi\\.e\\.", "ie", protected_text, flags=re.IGNORECASE)

    # Split into clauses by punctuation and contrastive conjunctions
    clauses = re.split(r"[.;\\n]+|\\b(?:whereas|while|although|however|but)\\b", protected_text, flags=re.IGNORECASE)

    exclusion_patterns = [
        rf"\\b(?:no|not|neither|nor|without|excluded|omitted|avoided|never|free\\s+of)\\b(?:\\s+\\w+){{0,12}}\\s+{animal_terms_pattern}\\b",
        rf"\\b{animal_terms_pattern}\\b(?:\\s+\\w+){{0,12}}\\s+\\b(?:were|was|are|is)?\\s*(?:excluded|omitted|avoided|not\\s+used|not\\s+performed|not\\s+conducted|not\\s+employed|unperformed)\\b",
        r"\\b(?:non-animal|nonanimal|non\\s+animal)\\s+(?:models?|systems?|assays?|methods?|approaches?|platforms?|testing)\\b",
        r"\\bno\\s+animal\\s+experiments\\b",
        r"\\banimal\\s+models\\s+were\\s+excluded\\b",
        r"\\bwithout\\s+animal\\s+models\\b",
        r"\\bexcluded\\s+other\\s+animal\\s+experiments\\b"
    ]

    future_patterns = [
        rf"\\b(?:future|planned|will\\s+be|will\\s+include|will\\s+evaluate|will\\s+use|prospective|pending|warranted)\\b(?:\\s+\\w+){{0,12}}\\s+{animal_terms_pattern}\\b",
        rf"\\b{animal_terms_pattern}\\b(?:\\s+\\w+){{0,12}}\\s+\\b(?:are\\s+planned|is\\s+planned|will\\s+be\\s+conducted|will\\s+be\\s+evaluated|will\\s+be\\s+used|will\\s+be\\s+tested|will\\s+be\\s+performed|will\\s+be\\s+investigated|for\\s+future\\s+work|in\\s+future\\s+studies|in\\s+future\\s+experiments|in\\s+future\\s+work)\\b",
        r"\\b(?:in\\s+future\\s+(?:work|studies|experiments|trials|assays)|for\\s+future\\s+(?:work|studies|experiments)|future\\s+(?:work|studies|experiments|directions)|future\\s+investigation)\\b",
        rf"\\b(?:plan\\s+to|plans\\s+to|aim\\s+to|aims\\s+to|intend\\s+to|intends\\s+to|planned\\s+to)\\s+(?:use|evaluate|test|conduct|perform|investigate|administer)\\b(?:\\s+\\w+){{0,12}}\\s+{animal_terms_pattern}\\b"
    ]

    background_patterns = [
        rf"\\b(?:prior|previous|earlier|other\\s+studies|another\\s+study|past|literature|reported\\s+in|background|introduction|cited\\s+studies|cited\\s+literature)\\b(?:\\s+\\w+){{0,12}}\\s+{animal_terms_pattern}\\b",
        rf"\\b{animal_terms_pattern}\\b(?:\\s+\\w+){{0,12}}\\s+\\b(?:in\\s+prior\\s+work|in\\s+earlier\\s+studies|in\\s+the\\s+literature|as\\s+reported\\s+previously|discussed\\s+only|in\\s+the\\s+introduction|of\\s+another\\s+study|discussed\\s+in\\s+previous\\s+literature\\s+only)\\b",
        r"\\b(?:discussed\\s+only\\s+in\\s+the\\s+introduction|limitation\\s+of\\s+another\\s+study|discussed\\s+in\\s+previous\\s+literature\\s+only)\\b",
        rf"\\b(?:paper|article|review|author|authors)\\s+discusses?\\s+{animal_terms_pattern}\\b"
    ]

    performed_patterns = [
        r"\\b(?:c57bl/6|sprague-dawley|balb/c|nude\\s+mice|xenograft|new\\s+zealand\\s+white\\s+rabbits?)\\b",
        rf"(?<!non-)(?<!non\\s)\\b(?:rat|rats|mouse|mice|murine|rodent|rodents|animal|animals|rabbit|rabbits|zebrafish|danio\\s+rerio)\\s+(?:models?|assays?|experiments?|studies)\\b",
        r"\\bin\\s+vivo\\s+(?:evaluation|assessment|testing|study|studies|experiment|experiments|model|models|efficacy|toxicity|assays?)\\b",
        rf"\\b(?:challenged|housed|injected|administered|sacrificed|implanted|treated|dosed|gavaged)\\b(?:\\s+\\w+){{0,12}}\\s+(?:to\\s+)?{animal_terms_pattern}\\b",
        rf"\\b{animal_terms_pattern}\\b(?:\\s+\\w+){{0,12}}\\s+\\b(?:were\\s+challenged|were\\s+housed|were\\s+injected|were\\s+administered|were\\s+sacrificed|were\\s+utilized|were\\s+used|were\\s+evaluated|were\\s+treated|were\\s+dosed|model\\s+was\\s+utilized|assays?\\s+were\\s+conducted|assays?\\s+were\\s+performed|experiments?\\s+were\\s+conducted|experiments?\\s+were\\s+performed)\\b",
        rf"\\b(?:study|we|authors?|investigation|our\\s+laboratory|our\\s+group|this\\s+work)\\s+(?:used|employed|utilized|tested\\s+in|administered)\\b(?:\\s+\\w+){{0,8}}\\s+(?:to\\s+)?{animal_terms_pattern}\\b",
        r"\\bin\\s+vivo\\s+validation\\s+confirmed\\b",
        rf"(?<!non-)(?<!non\\s)\\b{animal_terms_pattern}\\s+experiments?\\s+(?:were\\s+)?performed\\b",
        r"\\b(?:assays?|experiments?)\\s+were\\s+conducted\\b",
        r"\\bcannot\\s+be\\s+denied\\b"
    ]

    has_exclusion = pronominal_exclusion
    has_future = False
    has_background = False
    has_performed = False

    for c in clauses:
        c_clean = c.strip()
        if not c_clean:
            continue
        if animal_regex.search(c_clean):
            # Check exclusion first
            if any(re.search(p, c_clean, re.IGNORECASE) for p in exclusion_patterns):
                has_exclusion = True
            # Future-work priority: if clause indicates future work/planning, it must NOT be marked performed
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in future_patterns):
                has_future = True
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in background_patterns):
                has_background = True
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in performed_patterns):
                has_performed = True

    # Pronominal exclusion specifically refutes animal execution
    if pronominal_exclusion and not (has_background and has_performed):
        has_performed = False

    if has_exclusion and has_performed:
        return {"status": "mixed", "has_exclusion": True, "has_performed": True}
    if has_future and has_performed:
        return {"status": "mixed", "has_future": True, "has_performed": True}
    if has_background and has_performed:
        return {"status": "mixed", "has_background": True, "has_performed": True}
    if has_exclusion:
        return {"status": "excluded"}
    if has_future:
        return {"status": "future_work"}
    if has_background:
        return {"status": "background_only"}
    if has_performed:
        return {"status": "performed"}

    return {"status": "ambiguous"}
'''

m = re.search(old_func_pattern, content, flags=re.DOTALL)
assert m, "Could not find old analyze_animal_model_context function"
new_content = content[:m.start()] + new_func + content[m.end():]

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(new_content)

print("Successfully patched paper_analyst_llm.py!")
