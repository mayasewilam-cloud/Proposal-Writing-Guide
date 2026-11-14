import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

from core.impact_novelty_engine import BENCHMARK_PRIOR_ART
from core.paper_analyst_llm import analyze_animal_model_context
import core.reference_service as rs

print("=== REPRODUCING PHASE 4.1.5 FINDINGS ===")

# Defect 4: BENCHMARK_PRIOR_ART.get()
val_get = BENCHMARK_PRIOR_ART.get("cas12a_detection")
val_idx = BENCHMARK_PRIOR_ART["cas12a_detection"]
print(f"[Defect 4] BENCHMARK_PRIOR_ART.get('cas12a_detection'): {val_get}")
print(f"[Defect 4] BENCHMARK_PRIOR_ART['cas12a_detection']: {len(val_idx)} records")
assert val_get is None, "Expected Defect 4 to return None"

# Defect 5: Gootenberg classification
cas_records = BENCHMARK_PRIOR_ART["cas12a_detection"]
goot = next(r for r in cas_records if "Gootenberg" in r.get("authors", ""))
print(f"[Defect 5] Gootenberg relationship_type: {goot.get('relationship_type')}")
assert goot.get("relationship_type") == "direct_prior_art", "Expected Defect 5 to be direct_prior_art"

# Defect 6: Animal-model false positives
ctx1 = analyze_animal_model_context("The study used a non-animal model.")
print(f"[Defect 6] 'The study used a non-animal model.' -> status: {ctx1.get('status')}")
assert ctx1.get("status") == "performed", "Expected Defect 6 false positive (performed)"

ctx2 = analyze_animal_model_context("The paper discusses animal models, but does not use them.")
print(f"[Defect 6] 'The paper discusses animal models, but does not use them.' -> status: {ctx2.get('status')}")
assert ctx2.get("status") == "performed", "Expected Defect 6 false positive (performed)"

# Defect 3: Cache structure
print(f"[Defect 3] _CITATION_STATUS_CACHE type: {type(rs._CITATION_STATUS_CACHE).__name__}")
print("ALL 4 SCRATCH DEFECTS CONFIRMED REPRODUCIBLE.")
