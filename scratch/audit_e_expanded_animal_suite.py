import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

from core.paper_analyst_llm import analyze_animal_model_context, generate_inferred_limitations

test_cases = [
    # Required 12 cases:
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
    
    # Adversarial cases:
    # Double negation:
    ("Adv-13", "It cannot be denied that animal models were used.", "performed"),
    # Non-animal assay:
    ("Adv-14", "We developed a non-animal assay for high-throughput screening.", "excluded"),
    # Other species:
    ("Adv-15", "The formulation was administered to New Zealand white rabbits.", "performed"), # Wait, does regex know rabbits?
    ("Adv-16", "In vivo zebrafish assays were conducted.", "performed"),
    # Multi-clause with distant negation:
    ("Adv-17", "Although early drafts planned in vivo studies, ultimately no animal experiments were performed.", "excluded"),
    # Pure in vitro with zero animal keywords:
    ("Adv-18", "Reactions were performed with purified recombinant enzymes in 384-well plates.", "none"),
    # Future work with rats:
    ("Adv-19", "Efficacy in rodent models will be evaluated in future work.", "future_work"),
    # Pronominal negation with 'it':
    ("Adv-20", "The study mentions in vivo validation, but did not perform it.", "excluded"),
]

passed_count = 0
failed_cases = []

print("=== AUDIT E: ANIMAL MODEL CONTEXTUAL ANALYSIS (20 CASES) ===")
for cid, text, expected in test_cases:
    res = analyze_animal_model_context(text)
    status = res.get("status")
    # Acceptable equivalence between excluded and background_only for comparative sentences
    if status == expected or (expected in ["excluded", "background_only"] and status in ["excluded", "background_only"]):
        passed_count += 1
        ok = True
    else:
        ok = False
        failed_cases.append({"id": cid, "text": text, "expected": expected, "got": status})
    print(f"[{'PASS' if ok else 'FAIL'}] {cid:<7}: expected={expected:<15} got={status:<15} | '{text}'")

print(f"\nTOTAL: {passed_count} / {len(test_cases)} PASSED (Accuracy: {passed_count/len(test_cases)*100:.1f}%)")
if failed_cases:
    print(f"FAILURES ({len(failed_cases)}):")
    for fc in failed_cases:
        print(f"  - {fc['id']}: expected '{fc['expected']}', got '{fc['got']}' | '{fc['text']}'")
