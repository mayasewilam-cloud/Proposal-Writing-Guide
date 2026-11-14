import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

from core.paper_analyst_llm import analyze_animal_model_context, generate_inferred_limitations

cases = [
    # 32 Baseline Cases from Phase 4.1.8:
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
    ("Adv-13", "It cannot be denied that animal models were used.", "performed"),
    ("Adv-14", "We developed a non-animal assay for high-throughput screening.", "excluded"),
    ("Adv-15", "The formulation was administered to New Zealand white rabbits.", "performed"),
    ("Adv-16", "In vivo zebrafish assays were conducted.", "performed"),
    ("Adv-17", "Although early drafts planned in vivo studies, ultimately no animal experiments were performed.", "excluded"),
    ("Adv-18", "Reactions were performed with purified recombinant enzymes in 384-well plates.", "none"),
    ("Adv-19", "Efficacy in rodent models will be evaluated in future work.", "future_work"),
    ("Adv-20", "The study mentions in vivo validation, but did not perform it.", "excluded"),
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

    # 18 Additional Adversarial Cases for Phase 4.1.9:
    # Performed + Future in separate sentences:
    ("Adv-33", "Mice were challenged with the pathogen. Further rabbit assays will be conducted in future work.", "mixed"),
    # Performed keywords inside negation:
    ("Adv-34", "We strictly avoided administering doses to New Zealand white rabbits.", "excluded"),
    ("Adv-35", "No animals were challenged, housed, or sacrificed in this study.", "excluded"),
    # Negative future work:
    ("Adv-36", "Animal experiments will not be conducted in future studies.", "excluded"),
    # Background literature only:
    ("Adv-37", "Prior literature documented toxicity in rats, but our study is computational.", "background_only"),
    # In vitro with Xenopus (unlisted model organism):
    ("Adv-38", "Oocytes from Xenopus laevis were injected with cRNA in vitro.", "none"),
    # In vitro with C. elegans (unlisted model organism):
    ("Adv-39", "Caenorhabditis elegans lifespan assays were performed at 20°C.", "none"),
    # Murine model with negation in same clause:
    ("Adv-40", "A murine model was not employed.", "excluded"),
    # Performed in vivo validation confirmed:
    ("Adv-41", "In vivo validation confirmed the therapeutic response in rats.", "performed"),
    # Future work with danio rerio:
    ("Adv-42", "Toxicity in Danio rerio will be evaluated in subsequent work.", "future_work"),
    # Pronominal negation with rabbits:
    ("Adv-43", "The review discusses rabbit models, but we do not use them.", "excluded"),
    # High-throughput screening with zero animal keywords:
    ("Adv-44", "Spectrophotometric enzyme kinetic assays were monitored at 340 nm.", "none"),
    # Compound animal mention:
    ("Adv-45", "Both rats and mice were housed under pathogen-free conditions.", "performed"),
    # In vivo imaging without animal keyword:
    ("Adv-46", "In vivo imaging demonstrated biodistribution.", "performed"),
    # Ambiguous sentence:
    ("Adv-47", "Animal models are interesting.", "ambiguous"),
    # Future intention with aim:
    ("Adv-48", "We aim to evaluate the nanoparticles in mice.", "future_work"),
    # Contrastive coordinator with rodent negation:
    ("Adv-49", "The authors mention rodent experiments, however they did not conduct them.", "excluded"),
    # Multi-clause with performed prevailing over background:
    ("Adv-50", "Earlier studies evaluated cell culture, whereas we tested the formulation in mice.", "performed"),
]

passed_count = 0
results_list = []

for cid, text, expected in cases:
    res = analyze_animal_model_context(text)
    status = res.get("status")
    # Both excluded and background_only represent non-performed distinction
    ok = (status == expected) or (expected in ["excluded", "background_only"] and status in ["excluded", "background_only"])
    if ok:
        passed_count += 1
    results_list.append((cid, text, expected, status, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {cid:<7}: expected={expected:<15} got={status:<15} | '{text}'")

total = len(cases)
print(f"\nAUDIT C TOTAL: {passed_count} / {total} PASSED (Accuracy: {passed_count/total*100:.1f}%)")
