import sys
import os
import time
import copy

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('upload'))

from core.reference_service import CitationStatusCache

def test_cache_immutability():
    results = []
    def record(name, passed, details):
        results.append({"name": name, "passed": passed, "details": details})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} - {details}")

    cache = CitationStatusCache(max_size=5, ttl=3600.0)
    data = {
        "success": True,
        "doi": "10.1000/182",
        "title": "Original Title",
        "authors": ["Author 1", "Author 2"],
        "nested": {"key1": "val1", "citations": [10, 20]}
    }
    cache.set("10.1000/182", data)

    # 1. get() immutability
    g = cache.get("10.1000/182")
    g["title"] = "MUTATED"
    g["authors"].append("HACKER")
    g["nested"]["key1"] = "MUTATED"
    fresh1 = cache.get("10.1000/182")
    record("1. get() immutability", fresh1["title"] == "Original Title" and len(fresh1["authors"]) == 2 and fresh1["nested"]["key1"] == "val1", "No in-place mutation")

    # 2. __getitem__() immutability
    gi = cache["10.1000/182"]
    gi["title"] = "MUTATED INDEX"
    gi["authors"].clear()
    fresh2 = cache["10.1000/182"]
    record("2. __getitem__() immutability", fresh2["title"] == "Original Title" and len(fresh2["authors"]) == 2, "No in-place mutation via indexing")

    # 3. items() immutability
    for k, v in cache.items():
        v["title"] = "MUTATED ITEMS"
        v["nested"]["citations"].append(999)
    fresh3 = cache.get("10.1000/182")
    record("3. items() immutability", fresh3["title"] == "Original Title" and len(fresh3["nested"]["citations"]) == 2, "No in-place mutation via items()")

    # 4. values() immutability
    for v in cache.values():
        v["title"] = "MUTATED VALUES"
    fresh4 = cache.get("10.1000/182")
    record("4. values() immutability", fresh4["title"] == "Original Title", "No in-place mutation via values()")

    # 5. pop() behavior
    cache.set("10.1000/to_pop", {"success": True, "doi": "10.1000/to_pop", "title": "Pop Me", "sub": [1, 2]})
    popped = cache.pop("10.1000/to_pop")
    popped["sub"].append(3)
    record("5. pop() eviction", "10.1000/to_pop" not in cache and cache.get("10.1000/to_pop") is None, "Popped item evicted correctly")

    # 6. DOI normalization check
    cache.set("https://doi.org/10.1000/normalized", {"success": True, "doi": "10.1000/normalized"})
    ret_raw = cache.get("10.1000/normalized")
    ret_url = cache.get("https://dx.doi.org/10.1000/normalized")
    record("6. DOI normalization", ret_raw is not None and ret_url is not None and ret_raw["doi"] == "10.1000/normalized", "All URL prefixes resolve to normalized key")

    # 7. TTL expiration
    short_cache = CitationStatusCache(max_size=5, ttl=0.08)
    short_cache.set("10.1000/expire_me", {"success": True, "doi": "10.1000/expire_me"})
    before = short_cache.get("10.1000/expire_me")
    time.sleep(0.12)
    after = short_cache.get("10.1000/expire_me")
    record("7. TTL expiration", before is not None and after is None, f"before={bool(before)}, after={bool(after)}")

    # 8. Capacity limit and FIFO eviction
    cap_cache = CitationStatusCache(max_size=3, ttl=3600.0)
    for i in range(1, 5):
        cap_cache.set(f"10.1000/{i}", {"success": True, "val": i})
    record("8. Capacity & FIFO eviction", len(cap_cache) == 3 and "10.1000/1" not in cap_cache and "10.1000/4" in cap_cache, f"len={len(cap_cache)}, oldest evicted")

    # 9. Failed/unverified responses rejected
    failed_cache = CitationStatusCache(max_size=5, ttl=3600.0)
    failed_cache.set("10.1000/fail", {"success": False, "error": "Not Found"})
    failed_cache.set("10.1000/none", None)
    record("9. Rejection of failed lookups", len(failed_cache) == 0 and failed_cache.get("10.1000/fail") is None, "Unverified/failed responses never cached")

    # 10. Direct dict() / copy() investigation
    # If caller converts cache to dict: dict(cache) or cache.copy()
    # Note: CitationStatusCache inherits from dict. In Python, dict(cache) iterates over keys: dict([(k, cache[k])])
    d_conv = dict(cache.items())
    d_conv["10.1000/182"]["title"] = "MUTATED CONV"
    record("10. dict(cache.items()) safety", cache.get("10.1000/182")["title"] == "Original Title", "Safe via items() deepcopy")

    all_passed = all(r["passed"] for r in results)
    print(f"\nAUDIT B CACHE TOTAL: {sum(1 for r in results if r['passed'])}/{len(results)} PASSED (all_passed={all_passed})")

if __name__ == "__main__":
    test_cache_immutability()
