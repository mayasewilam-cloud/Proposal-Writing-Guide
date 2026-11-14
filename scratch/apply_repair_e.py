import os, re

filepath = "upload/core/paper_analyst_llm.py"
with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

old_func_start = 'def analyze_animal_model_context(text: str) -> Dict[str, Any]:'
old_func_end = 'def generate_inferred_limitations(model_type: str, paper_type: str = "research", is_review: bool = False) -> List[str]:'

start_idx = text.find(old_func_start)
end_idx = text.find(old_func_end)

assert start_idx != -1 and end_idx != -1, "Could not locate analyze_animal_model_context in paper_analyst_llm.py"

new_func = '''def analyze_animal_model_context(text: str) -> Dict[str, Any]:
    """
    Analyzes scientific text for animal-model mentions and determines context:
    - 'performed': animal experiments executed in this study
    - 'excluded': explicitly excluded or not conducted (including non-animal models and pronominal negation)
    - 'future_work': planned or proposed for future studies
    - 'background_only': discussed only as prior literature / external study limitation
    - 'mixed': both positive execution and negative exclusion mentioned
    - 'none': no animal models mentioned
    - 'ambiguous': animal model terms mentioned but context is unclear
    """
    if not isinstance(text, str) or not text.strip():
        return {"status": "none", "matches": []}

    animal_regex = re.compile(r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b", re.IGNORECASE)
    matches = animal_regex.findall(text)
    if not matches:
        return {"status": "none", "matches": []}

    # Sentence-level check: Pronominal negation linking antecedent animal mention across contrastive clauses
    # e.g., 'discusses animal models, but does not use them' or 'used mice, but we did not use them'
    pronominal_exclusion = bool(re.search(
        r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b[^.;\\n]+?\\b(?:but|however|although|whereas|while)\\b[^.;\\n]+?\\b(?:do|does|did|have|has|had|we|authors?|study|investigation|paper|work)\\s+(?:not\\s+|did\\s+not\\s+|does\\s+not\\s+|do\\s+not\\s+)?(?:use|employ|perform|conduct|utilize|include|involve|using)\\s+(?:them|these|it)\\b",
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
        r"\\b(?:no|not|neither|nor|without|excluded|omitted|avoided|never|free\\s+of)\\b(?:\\s+\\w+){0,12}\\s+(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b",
        r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b(?:\\s+\\w+){0,12}\\s+\\b(?:were|was|are|is)?\\s*(?:excluded|omitted|avoided|not\\s+used|not\\s+performed|not\\s+conducted|not\\s+employed|unperformed)\\b",
        r"\\b(?:non-animal|nonanimal|non\\s+animal)\\s+(?:models?|systems?|assays?|methods?|approaches?|platforms?|testing)\\b",
        r"\\bno\\s+animal\\s+experiments\\b",
        r"\\banimal\\s+models\\s+were\\s+excluded\\b",
        r"\\bwithout\\s+animal\\s+models\\b",
        r"\\bexcluded\\s+other\\s+animal\\s+experiments\\b"
    ]

    future_patterns = [
        r"\\b(?:future|planned|will\\s+be|will\\s+include|prospective|pending|warranted)\\b(?:\\s+\\w+){0,12}\\s+(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b",
        r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b(?:\\s+\\w+){0,12}\\s+\\b(?:are\\s+planned|will\\s+be\\s+conducted|for\\s+future\\s+work|in\\s+future\\s+studies)\\b"
    ]

    background_patterns = [
        r"\\b(?:prior|previous|earlier|other\\s+studies|another\\s+study|past|literature|reported\\s+in|background|introduction|cited\\s+studies|cited\\s+literature)\\b(?:\\s+\\w+){0,12}\\s+(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b",
        r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b(?:\\s+\\w+){0,12}\\s+\\b(?:in\\s+prior\\s+work|in\\s+earlier\\s+studies|in\\s+the\\s+literature|as\\s+reported\\s+previously|discussed\\s+only|in\\s+the\\s+introduction|of\\s+another\\s+study)\\b",
        r"\\b(?:discussed\\s+only\\s+in\\s+the\\s+introduction|limitation\\s+of\\s+another\\s+study)\\b",
        r"\\b(?:paper|article|review|author|authors)\\s+discusses?\\s+animal\\s+models?\\b"
    ]

    performed_patterns = [
        r"\\b(?:c57bl/6|sprague-dawley|balb/c|nude\\s+mice|xenograft)\\b",
        r"(?<!non-)(?<!non\\s)\\b(?:rat|mouse|murine|rodent|animal)\\s+models?\\b",
        r"\\bin\\s+vivo\\s+(?:evaluation|assessment|testing|study|studies|experiment|experiments|model|models|efficacy|toxicity)\\b",
        r"\\b(?:challenged|housed|injected|administered|sacrificed|implanted|treated|dosed|gavaged)\\b(?:\\s+\\w+){0,12}\\s+(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b",
        r"\\b(?:mouse|mice|rat|rats|animal|animals|in\\s+vivo|murine|rodent|rodents)\\b(?:\\s+\\w+){0,12}\\s+\\b(?:were\\s+challenged|were\\s+housed|were\\s+injected|were\\s+administered|were\\s+sacrificed|were\\s+utilized|were\\s+used|were\\s+evaluated|were\\s+treated|were\\s+dosed|model\\s+was\\s+utilized)\\b",
        r"\\b(?:study|we|authors?|investigation)?\\s*(?:used|employed|utilized|tested\\s+in)\\s+(?:mouse|mice|rat|rats|animals?|rodents?)\\b",
        r"\\b(?:study|investigation|we)\\s+administered\\b(?:\\s+\\w+){0,8}\\s+(?:to\\s+)?(?:mice|rats|animals|rodents)\\b",
        r"\\bin\\s+vivo\\s+validation\\s+confirmed\\b",
        r"(?<!non-)(?<!non\\s)\\b(?:mouse|mice|rat|rats|animal|in\\s+vivo)\\s+experiments?\\s+(?:were\\s+)?performed\\b"
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
            if any(re.search(p, c_clean, re.IGNORECASE) for p in exclusion_patterns):
                has_exclusion = True
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in future_patterns):
                has_future = True
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in background_patterns):
                has_background = True
            elif any(re.search(p, c_clean, re.IGNORECASE) for p in performed_patterns):
                has_performed = True

    if has_exclusion and has_performed:
        return {"status": "mixed", "has_exclusion": True, "has_performed": True}
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

updated_text = text[:start_idx] + new_func + text[end_idx:]
with open(filepath, "w", encoding="utf-8") as f:
    f.write(updated_text)

print("SUCCESS: Updated analyze_animal_model_context in core/paper_analyst_llm.py.")
