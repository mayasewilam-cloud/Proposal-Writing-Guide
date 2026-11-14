import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
from core.impact_novelty_engine import BENCHMARK_PRIOR_ART

cas_records = BENCHMARK_PRIOR_ART["cas12a_detection"]
pet_records = BENCHMARK_PRIOR_ART["petase_engineering"]

print("=== AUDIT B: SCIENTIFIC BENCHMARK RECORDS INSPECTION ===")
print(f"Cas12a records count: {len(cas_records)}")
print(f"PETase records count: {len(pet_records)}")

print("\n================== CAS12A BENCHMARK RECORDS ==================")
for idx, r in enumerate(cas_records):
    print(f"\n[Cas12a #{idx+1}] ID: {r.get('id')} | DOI: {r.get('doi')}")
    print(f"  Title: {r.get('title')}")
    print(f"  Authors: {r.get('authors')}")
    print(f"  Relationship Type: {r.get('relationship_type')}")
    print(f"  Relevance Explanation: {r.get('relevance_explanation')}")
    print(f"  Reported Benchmark: {r.get('reported_benchmark')}")
    print(f"  Mechanism: {r.get('mechanism')}")
    print(f"  Differentiation: {r.get('differentiation')}")

print("\n================== PETASE BENCHMARK RECORDS ==================")
for idx, r in enumerate(pet_records):
    print(f"\n[PETase #{idx+1}] ID: {r.get('id')} | DOI: {r.get('doi')}")
    print(f"  Title: {r.get('title')}")
    print(f"  Authors: {r.get('authors')}")
    print(f"  Relationship Type: {r.get('relationship_type')}")
    print(f"  Relevance Explanation: {r.get('relevance_explanation')}")
    print(f"  Reported Benchmark: {r.get('reported_benchmark')}")
    print(f"  Mechanism: {r.get('mechanism')}")
    print(f"  Differentiation: {r.get('differentiation')}")
