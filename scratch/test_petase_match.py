import sys
sys.path.insert(0, 'upload')
from core.impact_novelty_engine import audit_novelty_and_soundness

res = audit_novelty_and_soundness(
    title="Engineered PETase for Ambient Plastic Depolymerization",
    chassis="Escherichia coli BL21(DE3)",
    tool="Engineered IsPETase",
    target="Post-consumer PET plastic bottles",
    hypothesis="Active-site charge optimization increases turnover 3-fold at ambient temperatures",
    methodology="Recombinant expression and turbidimetric substrate clearance assay"
)

print("Benchmark status:", res.get("benchmark_status"))
print("Prior approaches count:", len(res.get("prior_approaches", [])))
print("Breakdown:", res.get("relationship_breakdown"))
