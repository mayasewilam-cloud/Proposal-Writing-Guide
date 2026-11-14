import os

filepath = "upload/core/impact_novelty_engine.py"
with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update Gootenberg record:
old_goot = '''            {
                "id": "PA-01",
                "relationship_type": "direct_prior_art",
                "relevance_explanation": "Seminal foundational demonstration of CRISPR collateral cleavage diagnostics (SHERLOCK), establishing the assay mechanism adapted here for Cas12a.",
                "title": "Nucleic acid detection with CRISPR-Cas13a/C2c2 (SHERLOCK)",
                "authors": "Gootenberg et al. (Science 2017)",
                "doi": "10.1126/science.aam9321",
                "benchmark_type": "curated_benchmark",
                "source_verification": "Verified peer-reviewed publication",
                "similarity_tier": "High",
                "similarity_score": 92,
                "reported_benchmark": "LOD: 10–50 pM with fluorescent reporter cleavage",
                "mechanism": "Collateral RNase cleavage of quenched reporter RNA probes",
                "differentiation": "Prior art uses purified recombinant buffer and RNA targets; your proposal targets specific diagnostic nucleic acid sequences directly."
            },'''

new_goot = '''            {
                "id": "PA-01",
                "relationship_type": "enabling_technology",
                "relevance_explanation": "Foundational demonstration of CRISPR collateral cleavage diagnostics (SHERLOCK) using Cas13a RNA targeting, establishing the conceptual collateral-cleavage diagnostic paradigm rather than demonstrating Cas12a-specific ssDNA trans-cleavage.",
                "title": "Nucleic acid detection with CRISPR-Cas13a/C2c2 (SHERLOCK)",
                "authors": "Gootenberg et al. (Science 2017)",
                "doi": "10.1126/science.aam9321",
                "benchmark_type": "curated_benchmark",
                "source_verification": "Verified peer-reviewed publication",
                "similarity_tier": "Moderate",
                "similarity_score": 75,
                "reported_benchmark": "LOD: 10–50 pM with fluorescent reporter cleavage",
                "mechanism": "Collateral RNase cleavage of quenched reporter RNA probes",
                "differentiation": "Prior art uses Cas13a targeting RNA with collateral RNase activity; your proposal adapts collateral cleavage using Cas12a for target-specific DNA detection with ssDNA trans-cleavage."
            },'''

assert old_goot in text, "old_goot not found in impact_novelty_engine.py"
text = text.replace(old_goot, new_goot, 1)

# 2. Update _BenchmarkPriorArtDict:
old_dict = '''class _BenchmarkPriorArtDict(dict):
    def __getitem__(self, key):
        return get_benchmark_prior_art().get(key, [])
    def items(self):
        return get_benchmark_prior_art().items()
    def keys(self):
        return get_benchmark_prior_art().keys()
    def values(self):
        return get_benchmark_prior_art().values()
    def __iter__(self):
        return iter(get_benchmark_prior_art())
    def __len__(self):
        return len(get_benchmark_prior_art())'''

new_dict = '''class _BenchmarkPriorArtDict(dict):
    def __getitem__(self, key):
        benchmarks = get_benchmark_prior_art()
        if key in benchmarks:
            return benchmarks[key]
        return benchmarks.get(key, [])

    def get(self, key, default=None):
        benchmarks = get_benchmark_prior_art()
        if key in benchmarks:
            return benchmarks[key]
        return default

    def __contains__(self, key):
        return key in get_benchmark_prior_art()

    def items(self):
        return get_benchmark_prior_art().items()

    def keys(self):
        return get_benchmark_prior_art().keys()

    def values(self):
        return get_benchmark_prior_art().values()

    def __iter__(self):
        return iter(get_benchmark_prior_art())

    def __len__(self):
        return len(get_benchmark_prior_art())'''

assert old_dict in text, "old_dict not found in impact_novelty_engine.py"
text = text.replace(old_dict, new_dict, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESS: Updated impact_novelty_engine.py with Repairs C and D.")
