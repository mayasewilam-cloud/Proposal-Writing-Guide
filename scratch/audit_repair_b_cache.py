"""
Independent Audit Script: Repair B - CitationStatusCache Copy & Mutation Isolation
Tests all 11 criteria and potential escape routes.
"""

import sys
import copy
import time
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.reference_service import CitationStatusCache, normalize_doi

def run_cache_audit():
    results = {}

    # 1. Type and attributes
    c = CitationStatusCache(max_size=20, ttl=1800.0)
    c["10.1038/nature1"] = {"success": True, "title": "Paper 1", "meta": {"citations": [1, 2, 3]}}
    c_copy = c.copy()
    assert isinstance(c_copy, CitationStatusCache), f"Expected CitationStatusCache, got {type(c_copy)}"
    assert c_copy.max_size == 20, f"max_size mismatch: {c_copy.max_size}"
    assert c_copy.ttl == 1800.0, f"ttl mismatch: {c_copy.ttl}"
    results["1_type_and_config"] = "PASSED"

    # 2. Defensive copy on __getitem__ and get()
    entry_copy = c_copy.get("10.1038/nature1")
    entry_copy["title"] = "MUTATED_GET"
    assert c["10.1038/nature1"]["title"] == "Paper 1", "Original mutated via get() reference!"
    assert c_copy["10.1038/nature1"]["title"] == "Paper 1", "Copy internal mutated via get() reference!"

    # 3. Direct internal mutation of copy does NOT mutate original
    # Access the underlying dict storage of c_copy to mutate internal structure directly
    dict.__getitem__(c_copy, "10.1038/nature1")["title"] = "DIRECT_INTERNAL_MUTATION"
    dict.__getitem__(c_copy, "10.1038/nature1")["meta"]["citations"].append(999)

    assert c["10.1038/nature1"]["title"] == "Paper 1", "Original mutated by internal copy mutation!"
    assert c["10.1038/nature1"]["meta"]["citations"] == [1, 2, 3], "Original nested list mutated by copy!"
    assert c_copy["10.1038/nature1"]["title"] == "DIRECT_INTERNAL_MUTATION"
    assert c_copy["10.1038/nature1"]["meta"]["citations"] == [1, 2, 3, 999]
    results["2_and_3_internal_and_nested_mutation_isolated"] = "PASSED"

    # 4. Mutating original does not affect existing copy
    c["10.1038/nature1"] = {"success": True, "title": "Brand New Title In Original", "meta": {"citations": []}}
    assert c_copy["10.1038/nature1"]["title"] == "DIRECT_INTERNAL_MUTATION", "Copy was modified when original was updated!"
    results["4_reverse_mutation_isolated"] = "PASSED"

    # 5. copy.copy() invokes __copy__()
    c2 = CitationStatusCache(max_size=15, ttl=500.0)
    c2["10.1000/test"] = {"success": True, "nested": {"val": 10}}
    c2_shallow = copy.copy(c2)
    assert isinstance(c2_shallow, CitationStatusCache)
    dict.__getitem__(c2_shallow, "10.1000/test")["nested"]["val"] = 999
    assert c2.get("10.1000/test")["nested"]["val"] == 10, "copy.copy() leaked mutable reference!"
    results["5_standard_copy_isolated"] = "PASSED"

    # 6. copy.deepcopy() invokes __deepcopy__()
    c2_deep = copy.deepcopy(c2)
    assert isinstance(c2_deep, CitationStatusCache)
    dict.__getitem__(c2_deep, "10.1000/test")["nested"]["val"] = 888
    assert c2.get("10.1000/test")["nested"]["val"] == 10, "copy.deepcopy() leaked mutable reference!"
    results["6_deepcopy_isolated"] = "PASSED"

    # 7. Timestamps and internal state isolation
    assert c_copy._timestamps is not c._timestamps, "Timestamps dictionary reference was shared!"
    c_copy._timestamps["10.1038/nature1"] = 0.0
    assert c._timestamps["10.1038/nature1"] != 0.0, "Original timestamp was mutated by copy!"
    results["7_timestamp_state_isolated"] = "PASSED"

    # 8. Expired entries handling upon copy
    c_exp = CitationStatusCache(max_size=10, ttl=0.1)
    c_exp["10.1000/active"] = {"success": True, "title": "Active"}
    c_exp["10.1000/stale"] = {"success": True, "title": "Stale"}
    # Artificially age stale item
    c_exp._timestamps["10.1000/stale"] = time.time() - 1000.0

    c_exp_copy = c_exp.copy()
    assert "10.1000/active" in c_exp_copy, "Active entry missing in copy!"
    assert "10.1000/stale" not in c_exp_copy, "Expired entry was not evicted upon copy()!"
    results["8_expired_eviction_upon_copy"] = "PASSED"

    # 9. Capacity and FIFO eviction preserved in copied cache
    c_small = CitationStatusCache(max_size=3, ttl=3600.0)
    c_small["10.1000/1"] = {"success": True, "id": 1}
    c_small["10.1000/2"] = {"success": True, "id": 2}
    c_small["10.1000/3"] = {"success": True, "id": 3}
    c_small_copy = c_small.copy()

    # Add 4th item to copy, should evict 10.1000/1
    c_small_copy["10.1000/4"] = {"success": True, "id": 4}
    assert len(c_small_copy) == 3, f"Capacity exceeded: {len(c_small_copy)}"
    assert "10.1000/1" not in c_small_copy, "Oldest entry 10.1000/1 was not evicted in copy!"
    assert "10.1000/4" in c_small_copy, "New entry 10.1000/4 missing in copy!"
    # Original must still have 10.1000/1
    assert "10.1000/1" in c_small, "Original was affected by copy eviction!"
    results["9_fifo_capacity_preserved"] = "PASSED"

    # 10. DOI normalization preserved
    c_norm = CitationStatusCache()
    c_norm["https://doi.org/10.1038/S41586-020-0001"] = {"success": True, "title": "Norm"}
    c_norm_copy = c_norm.copy()
    assert "10.1038/s41586-020-0001" in c_norm_copy
    assert "doi:10.1038/s41586-020-0001" in c_norm_copy
    assert c_norm_copy.get("HTTPS://DOI.ORG/10.1038/S41586-020-0001")["title"] == "Norm"
    results["10_doi_normalization_preserved"] = "PASSED"

    # 11. Failed / unknown responses not cached
    c_fail = CitationStatusCache()
    c_fail["10.1000/bad"] = {"success": False, "error": "Not found"}
    assert "10.1000/bad" not in c_fail
    c_fail_copy = c_fail.copy()
    assert "10.1000/bad" not in c_fail_copy
    results["11_failed_response_handling_intact"] = "PASSED"

    # 12. Public dictionary methods verification (values(), items(), __iter__())
    c_dict = CitationStatusCache()
    c_dict["10.1000/a"] = {"success": True, "k": "a"}
    vals = c_dict.values()
    vals[0]["k"] = "HACKED"
    assert c_dict["10.1000/a"]["k"] == "a", "values() leaked mutable reference!"
    
    it = c_dict.items()
    it[0][1]["k"] = "HACKED_AGAIN"
    assert c_dict["10.1000/a"]["k"] == "a", "items() leaked mutable reference!"
    results["12_public_dict_views_isolated"] = "PASSED"

    print("\n=== REPAIR B CITATION CACHE ISOLATION AUDIT RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("ALL 12 CACHE ISOLATION TESTS VERIFIED SUCCESSFULLY!\n")

if __name__ == "__main__":
    run_cache_audit()
