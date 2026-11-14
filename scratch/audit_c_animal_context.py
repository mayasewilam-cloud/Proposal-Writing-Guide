import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
from core.paper_analyst_llm import analyze_animal_model_context, generate_inferred_limitations

cases = [
    (1, "No animal experiments were performed in this study.", "excluded"),
    (2, "Animal models were excluded from the present investigation.", "excluded"),
    (3, "Previous studies used rat models, but the current study was conducted in vitro.", "background_only"),
    (4, "Future work will evaluate the formulation in mice.", "future_work"),
    (5, "The formulation was administered to mice, while the in vitro experiments were performed separately.", "performed"),
    (6, "Animal studies were not performed; however, previous animal findings support the hypothesis.", "mixed"),  # exclusion + background?
    (7, "The study used a non-animal model.", "excluded"),
    (8, "No in vivo experiments were conducted.", "excluded"),
    (9, "The paper discusses animal models but does not use them.", "excluded"),
    (10, "The current study used a rat model.", "performed"),
    (11, "In vitro assays were performed; animal models were excluded.", "excluded"),
    (12, "The authors did not use mice, but they administered the formulation to rats.", "mixed")  # negation on mice + administered to rats
]

print("=== AUDIT C: CONTEXT-AWARE ANIMAL-MODEL ANALYSIS ===")

for num, text, expected_semantic in cases:
    ctx = analyze_animal_model_context(text)
    lims = generate_inferred_limitations(model_type=text)
    status = ctx.get("status")
    print(f"\nCase {num}: '{text}'")
    print(f"  Analyzed Status: {status} (Expected semantic: {expected_semantic})")
    print(f"  Inferred Limitations ({len(lims)}):")
    for l in lims:
        print(f"    - {l}")
