import re

tests = [
    ("Rat model for evaluating inflammatory responses", "performed"),
    ("Mouse model of disease progression", "performed"),
    ("In vivo evaluation of therapeutic efficacy", "performed"),
    ("Genomic integration of a recombinant biosynthetic pathway", "none"),
    ("Mice were treated with 5 mg/kg compound once daily for 14 days to assess in vivo toxicity.", "performed"),
    ("Because this study focuses on cell-free enzymatic characterization, animal experiments were explicitly omitted and excluded from the experimental design.", "excluded"),
    ("Future work will include validating pharmacokinetic parameters in rodent animal models.", "future_work"),
    ("Previous studies by Jones et al. demonstrated in vivo neurotoxicity in rat models.", "background_only"),
    ("Purified Cas12a enzyme was mixed with guide RNA and fluorophore quencher ssDNA probe at 37 C.", "none"),
    ("Animal-free protocols require careful consideration when evaluating physiological boundaries.", "ambiguous")
]

def analyze_animal_model_context(text: str):
    if not isinstance(text, str) or not text.strip():
        return {"status": "none", "matches": []}

    animal_regex = re.compile(r"\b(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b", re.IGNORECASE)
    matches = animal_regex.findall(text)
    if not matches:
        return {"status": "none", "matches": []}

    # Protect abbreviations with periods like "et al.", "i.e.", "e.g." before clause splitting
    protected_text = re.sub(r"\bet\s+al\.", "et_al", text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\be\.g\.", "eg", protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\bi\.e\.", "ie", protected_text, flags=re.IGNORECASE)

    # Split into clauses by punctuation and contrastive conjunctions
    clauses = re.split(r"[.;\n]+|\b(?:whereas|while|although|however|but)\b", protected_text, flags=re.IGNORECASE)

    exclusion_patterns = [
        r"\b(?:no|not|neither|nor|without|excluded|omitted|avoided|never|non-animal|free\s+of)\b(?:\s+\w+){0,12}\s+(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b",
        r"\b(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b(?:\s+\w+){0,12}\s+\b(?:were|was|are|is)?\s*(?:excluded|omitted|avoided|not\s+used|not\s+performed|not\s+conducted|not\s+employed|unperformed)\b",
        r"\bno\s+animal\s+experiments\b",
        r"\banimal\s+models\s+were\s+excluded\b"
    ]

    future_patterns = [
        r"\b(?:future|planned|will\s+be|will\s+include|prospective|pending|warranted)\b(?:\s+\w+){0,12}\s+(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b",
        r"\b(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b(?:\s+\w+){0,12}\s+\b(?:are\s+planned|will\s+be\s+conducted|for\s+future\s+work|in\s+future\s+studies)\b"
    ]

    background_patterns = [
        r"\b(?:prior|previous|earlier|other\s+studies|another\s+study|past|literature|reported\s+in|background|introduction)\b(?:\s+\w+){0,12}\s+(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b",
        r"\b(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b(?:\s+\w+){0,12}\s+\b(?:in\s+prior\s+work|in\s+earlier\s+studies|in\s+the\s+literature|as\s+reported\s+previously|discussed\s+only|in\s+the\s+introduction|of\s+another\s+study)\b",
        r"\b(?:discussed\s+only\s+in\s+the\s+introduction|limitation\s+of\s+another\s+study)\b"
    ]

    performed_patterns = [
        r"\b(?:c57bl/6|sprague-dawley|balb/c|nude\s+mice|xenograft)\b",
        r"\b(?:rat|mouse|murine|rodent|animal)\s+models?\b",
        r"\bin\s+vivo\s+(?:evaluation|assessment|testing|study|studies|experiment|experiments|model|models|efficacy|toxicity)\b",
        r"\b(?:challenged|housed|injected|administered|sacrificed|implanted|treated|dosed|gavaged)\b(?:\s+\w+){0,12}\s+(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b",
        r"\b(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents)\b(?:\s+\w+){0,12}\s+\b(?:were\s+challenged|were\s+housed|were\s+injected|were\s+administered|were\s+sacrificed|were\s+utilized|were\s+used|were\s+evaluated|were\s+treated|were\s+dosed|model\s+was\s+utilized)\b",
        r"\bin\s+vivo\s+validation\s+confirmed\b",
        r"\bexperiments\s+performed\b",
        r"\b(?:mouse|mice|rat|rats|animal|in\s+vivo)\s+experiments?\s+(?:were\s+)?performed\b"
    ]

    has_exclusion = False
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

all_passed = True
for inp, exp in tests:
    res = analyze_animal_model_context(inp)["status"]
    passed = res == exp
    print(f"[{'PASS' if passed else 'FAIL'}] '{inp[:50]}...' -> {res} (expected: {exp})")
    if not passed:
        all_passed = False

print("\nAll passed:", all_passed)
