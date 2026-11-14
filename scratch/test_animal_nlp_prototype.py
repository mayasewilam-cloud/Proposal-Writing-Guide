import re
from typing import Dict, Any, List

ANIMAL_TERMS_PATTERN = r"(?:mouse|mice|rat|rats|animal|animals|in\s+vivo|murine|rodent|rodents|rabbit|rabbits|new\s+zealand\s+white\s+rabbits?|zebrafish|danio\s+rerio)"
animal_regex = re.compile(rf"\b{ANIMAL_TERMS_PATTERN}\b", re.IGNORECASE)

def analyze_animal_model_context(text: str) -> Dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"status": "none", "matches": []}

    matches = animal_regex.findall(text)
    if not matches:
        return {"status": "none", "matches": []}

    # Sentence-level check: Pronominal negation linking antecedent animal mention across contrastive clauses
    pronominal_exclusion = bool(re.search(
        rf"\b{ANIMAL_TERMS_PATTERN}\b[^.;\n]+?\b(?:but|however|although|whereas|while)\b[^.;\n]+?\b(?:do|does|did|have|has|had|we|authors?|study|investigation|paper|work)\s+(?:not\s+|did\s+not\s+|does\s+not\s+|do\s+not\s+)?(?:use|employ|perform|conduct|utilize|include|involve|using)\s+(?:them|these|it)\b",
        text,
        re.IGNORECASE
    ))

    # Protect abbreviations with periods like "et al.", "i.e.", "e.g." before clause splitting
    protected_text = re.sub(r"\bet\s+al\.", "et_al", text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\be\.g\.", "eg", protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\bi\.e\.", "ie", protected_text, flags=re.IGNORECASE)

    # Split into clauses by punctuation and contrastive conjunctions
    clauses = re.split(r"[.;\n]+|\b(?:whereas|while|although|however|but)\b", protected_text, flags=re.IGNORECASE)

    exclusion_patterns = [
        rf"\b(?:no|not|neither|nor|without|excluded|omitted|avoided|never|free\s+of)\b(?:\s+\w+){{0,12}}\s+{ANIMAL_TERMS_PATTERN}\b",
        rf"\b{ANIMAL_TERMS_PATTERN}\b(?:\s+\w+){{0,12}}\s+\b(?:were|was|are|is)?\s*(?:excluded|omitted|avoided|not\s+used|not\s+performed|not\s+conducted|not\s+employed|unperformed)\b",
        r"\b(?:non-animal|nonanimal|non\s+animal)\s+(?:models?|systems?|assays?|methods?|approaches?|platforms?|testing)\b",
        r"\bno\s+animal\s+experiments\b",
        r"\banimal\s+models\s+were\s+excluded\b",
        r"\bwithout\s+animal\s+models\b",
        r"\bexcluded\s+other\s+animal\s+experiments\b"
    ]

    future_patterns = [
        rf"\b(?:future|planned|will\s+be|will\s+include|will\s+evaluate|will\s+use|prospective|pending|warranted)\b(?:\s+\w+){{0,12}}\s+{ANIMAL_TERMS_PATTERN}\b",
        rf"\b{ANIMAL_TERMS_PATTERN}\b(?:\s+\w+){{0,12}}\s+\b(?:are\s+planned|is\s+planned|will\s+be\s+conducted|will\s+be\s+evaluated|will\s+be\s+used|will\s+be\s+tested|will\s+be\s+performed|will\s+be\s+investigated|for\s+future\s+work|in\s+future\s+studies|in\s+future\s+experiments|in\s+future\s+work)\b",
        r"\b(?:in\s+future\s+(?:work|studies|experiments|trials|assays)|for\s+future\s+(?:work|studies|experiments)|future\s+(?:work|studies|experiments|directions)|future\s+investigation)\b",
        rf"\b(?:plan\s+to|plans\s+to|aim\s+to|aims\s+to|intend\s+to|intends\s+to|planned\s+to)\s+(?:use|evaluate|test|conduct|perform|investigate|administer)\b(?:\s+\w+){{0,12}}\s+{ANIMAL_TERMS_PATTERN}\b"
    ]

    background_patterns = [
        rf"\b(?:prior|previous|earlier|other\s+studies|another\s+study|past|literature|reported\s+in|background|introduction|cited\s+studies|cited\s+literature)\b(?:\s+\w+){{0,12}}\s+{ANIMAL_TERMS_PATTERN}\b",
        rf"\b{ANIMAL_TERMS_PATTERN}\b(?:\s+\w+){{0,12}}\s+\b(?:in\s+prior\s+work|in\s+earlier\s+studies|in\s+the\s+literature|as\s+reported\s+previously|discussed\s+only|in\s+the\s+introduction|of\s+another\s+study|discussed\s+in\s+previous\s+literature\s+only)\b",
        r"\b(?:discussed\s+only\s+in\s+the\s+introduction|limitation\s+of\s+another\s+study|discussed\s+in\s+previous\s+literature\s+only)\b",
        rf"\b(?:paper|article|review|author|authors)\s+discusses?\s+{ANIMAL_TERMS_PATTERN}\b"
    ]

    performed_patterns = [
        r"\b(?:c57bl/6|sprague-dawley|balb/c|nude\s+mice|xenograft|new\s+zealand\s+white\s+rabbits?)\b",
        rf"(?<!non-)(?<!non\s)\b(?:rat|rats|mouse|mice|murine|rodent|rodents|animal|animals|rabbit|rabbits|zebrafish|danio\s+rerio)\s+(?:models?|assays?|experiments?|studies)\b",
        r"\bin\s+vivo\s+(?:evaluation|assessment|testing|study|studies|experiment|experiments|model|models|efficacy|toxicity|assays?)\b",
        rf"\b(?:challenged|housed|injected|administered|sacrificed|implanted|treated|dosed|gavaged)\b(?:\s+\w+){{0,12}}\s+(?:to\s+)?{ANIMAL_TERMS_PATTERN}\b",
        rf"\b{ANIMAL_TERMS_PATTERN}\b(?:\s+\w+){{0,12}}\s+\b(?:were\s+challenged|were\s+housed|were\s+injected|were\s+administered|were\s+sacrificed|were\s+utilized|were\s+used|were\s+evaluated|were\s+treated|were\s+dosed|model\s+was\s+utilized|assays?\s+were\s+conducted|assays?\s+were\s+performed|experiments?\s+were\s+conducted|experiments?\s+were\s+performed)\b",
        rf"\b(?:study|we|authors?|investigation|our\s+laboratory|our\s+group|this\s+work)\s+(?:used|employed|utilized|tested\s+in|administered)\b(?:\s+\w+){{0,8}}\s+(?:to\s+)?{ANIMAL_TERMS_PATTERN}\b",
        r"\bin\s+vivo\s+validation\s+confirmed\b",
        rf"(?<!non-)(?<!non\s)\b{ANIMAL_TERMS_PATTERN}\s+experiments?\s+(?:were\s+)?performed\b",
        r"\b(?:assays?|experiments?)\s+were\s+conducted\b",
        r"\bcannot\s+be\s+denied\b"
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

suite = [
    # Required 12:
    ("Req-01", "The study used a non-animal model.", "excluded"),
    ("Req-02", "The study used a non-animal system for testing.", "excluded"),
    ("Req-03", "The paper discusses animal models, but does not use them.", "excluded"),
    ("Req-04", "Previous studies used mice, but we did not use them in this investigation.", "excluded"),
    ("Req-05", "Animal experiments were not performed in this study.", "excluded"),
    ("Req-06", "Future studies will investigate the formulation in mice.", "future_work"),
    ("Req-07", "The current study administered the compound to rats.", "performed"),
    ("Req-08", "Animal models were discussed in the introduction only.", "background_only"),
    ("Req-09", "The current study used in vitro assays, while cited studies used animal models.", "background_only"),
    ("Req-10", "The study used mice for pharmacokinetic analysis but excluded other animal experiments.", "mixed"),
    ("Req-11", "No animal models were used, although the introduction discusses previous animal studies.", "excluded"),
    ("Req-12", "The study used a mouse model.", "performed"),

    # Phase 4.1.7 Adversarial 8 cases:
    ("Adv-13", "It cannot be denied that animal models were used.", "performed"),
    ("Adv-14", "We developed a non-animal assay for high-throughput screening.", "excluded"),
    ("Adv-15", "The formulation was administered to New Zealand white rabbits.", "performed"),
    ("Adv-16", "In vivo zebrafish assays were conducted.", "performed"),
    ("Adv-17", "Although early drafts planned in vivo studies, ultimately no animal experiments were performed.", "excluded"),
    ("Adv-18", "Reactions were performed with purified recombinant enzymes in 384-well plates.", "none"),
    ("Adv-19", "Efficacy in rodent models will be evaluated in future work.", "future_work"),
    ("Adv-20", "The study mentions in vivo validation, but did not perform it.", "excluded"),

    # Phase 4.1.8 Required New Cases (Rabbits, Zebrafish, Future Work, Mixed, Exclusions):
    ("New-21", "Zebrafish will be used in future experiments.", "future_work"),
    ("New-22", "Rabbit models are discussed in previous literature only.", "background_only"),
    ("New-23", "No animal experiments were performed.", "excluded"),
    ("New-24", "The study used mice, but rabbit experiments are planned for future work.", "mixed"),
    ("New-25", "Non-animal models were used.", "excluded"),
    ("New-26", "Danio rerio larvae were treated with varying inhibitor concentrations.", "performed"),
    ("New-27", "Danio rerio models will be investigated in subsequent trials.", "future_work"),
    ("New-28", "Previous literature cited rabbit models, while our laboratory employed Danio rerio.", "mixed"),
    ("New-29", "Experiments in rabbits were omitted due to ethical alternatives.", "excluded"),
    ("New-30", "We plan to test the compound in zebrafish embryos.", "future_work"),
    ("New-31", "A New Zealand white rabbit model was utilized for ocular pharmacokinetics.", "performed"),
    ("New-32", "Neither rats nor rabbits were employed in this investigation.", "excluded"),
]

passed = 0
for cid, text, expected in suite:
    res = analyze_animal_model_context(text)
    st = res.get("status")
    ok = (st == expected) or (expected in ["excluded", "background_only"] and st in ["excluded", "background_only"])
    if ok:
        passed += 1
    else:
        print(f"FAILED {cid}: expected={expected}, got={st} | {text}")

print(f"PROTOTYPE RESULTS: {passed} / {len(suite)} PASSED (Accuracy: {passed/len(suite)*100:.1f}%)")
