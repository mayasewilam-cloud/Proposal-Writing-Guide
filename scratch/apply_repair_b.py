import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "impact_novelty_engine.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

# 1. Add VALID_RELATIONSHIP_TYPES
if "VALID_RELATIONSHIP_TYPES" not in text:
    old_gap_tax = "GAP_TAXONOMY = {"
    new_gap_tax = """VALID_RELATIONSHIP_TYPES = {
    "direct_prior_art",
    "enabling_technology",
    "target_biology",
    "adjacent_background"
}

GAP_TAXONOMY = {"""
    assert old_gap_tax in text, "GAP_TAXONOMY not found"
    text = text.replace(old_gap_tax, new_gap_tax, 1)

# Annotate Cas12a records (under is_cas_diagnostic)
cas_records = [
    ("Gootenberg et al. (Science 2017)", "direct_prior_art", "Seminal foundational demonstration of CRISPR collateral cleavage diagnostics (SHERLOCK), establishing the assay mechanism adapted here for Cas12a."),
    ("Chen et al. (Science 2018)", "direct_prior_art", "Seminal discovery of Cas12a target-activated single-stranded DNA collateral cleavage (DETECTR), serving as the direct catalytic foundation."),
    ("Kellner et al. (Nature Protocols 2019)", "direct_prior_art", "Comprehensive standard protocol establishing reaction conditions, guide-RNA concentrations, and lateral-flow readouts for Cas enzymatic diagnostics."),
    ("Myhrvold et al. (Science 2018)", "enabling_technology", "Field-deployable instrument-free viral extraction and amplification protocols (HUDSON), enabling rapid diagnostic workflows."),
    ("Piepenburg et al. (PLOS Biology 2006)", "enabling_technology", "Foundational demonstration of Recombinase Polymerase Amplification (RPA), providing the isothermal pre-amplification required for attomolar sensitivity."),
    ("Liu et al. (Lancet Infect Dis 2016)", "target_biology", "Seminal epidemiology discovering plasmid-mediated colistin resistance (mcr-1), defining the clinical gene target."),
    ("Pardee et al. (Cell 2016)", "adjacent_background", "Paper-based freeze-dried cell-free gene circuits for point-of-care diagnostics, illustrating adjacent paper strip deployment.")
]

for author, rtype, rexp in cas_records:
    author_needle = f'"authors": "{author}",'
    assert author_needle in text, f"Author {author} not found"
    idx = text.find(author_needle)
    # Find preceding "id": "PA-0X",
    id_start = text.rfind('"id":', 0, idx)
    id_end = text.find('\n', id_start)
    old_id_line = text[id_start:id_end]
    new_id_block = f'{old_id_line}\n                "relationship_type": "{rtype}",\n                "relevance_explanation": "{rexp}",'
    text = text[:id_start] + new_id_block + text[id_end:]

# Annotate PETase records (under is_petase)
petase_records = [
    ("Austin et al. (PNAS 2018)", "direct_prior_art", "High-resolution crystal structure and initial active-site engineering narrowing the binding cleft for improved PET depolymerization."),
    ("Tournier et al. (Nature 2020)", "direct_prior_art", "Benchmark computational redesign (LCCICCG) demonstrating 90% depolymerization in 10 hours at 72 C in a 3-m3 reactor."),
    ("Yoshida et al. (Science 2016)", "direct_prior_art", "Seminal identification and initial characterization of Ideonella sakaiensis PETase and MHETase enzymatic degradation."),
    ("Sonnendecker et al. (ChemSusChem 2022)", "direct_prior_art", "Discovery of engineered polyester hydrolase PHL7 exhibiting two-fold faster degradation kinetics than LCC at elevated temperatures."),
    ("Herrero Acero, Ribitsch et al. (Biotechnol Bioeng 2013)", "enabling_technology", "Surface charge and electrostatic optimization of bacterial cutinases, establishing protein engineering strategies for polyester binding clefts."),
    ("Skariyachan et al. (Polym Degrad Stab 2018)", "adjacent_background", "Thermophilic microbial consortia for polyolefin degradation, representing adjacent non-enzymatic plastic bioremediation."),
    ("Sheldon et al. (Adv Synth Catal 2007)", "enabling_technology", "Foundational carrier-free enzyme immobilization methodology (CLEA) enabling macro-scale enzyme recycling and operational stability.")
]

for author, rtype, rexp in petase_records:
    author_needle = f'"authors": "{author}",'
    assert author_needle in text, f"Author {author} not found"
    idx = text.find(author_needle)
    # Find preceding "id": "PA-0X",
    id_start = text.rfind('"id":', 0, idx)
    id_end = text.find('\n', id_start)
    old_id_line = text[id_start:id_end]
    new_id_block = f'{old_id_line}\n                "relationship_type": "{rtype}",\n                "relevance_explanation": "{rexp}",'
    text = text[:id_start] + new_id_block + text[id_end:]

# Add validation and relationship_breakdown
validation_and_breakdown_code = """
    # Validate benchmark record schemas: every prior approach must have valid relationship_type and explanation
    for p in prior_approaches:
        rtype = p.get("relationship_type")
        if not rtype or rtype not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(f"Benchmark record '{p.get('id')}' has invalid or missing relationship_type '{rtype}'. Must be one of {VALID_RELATIONSHIP_TYPES}")
        if not p.get("relevance_explanation"):
            raise ValueError(f"Benchmark record '{p.get('id')}' is missing required relevance_explanation.")

    relationship_breakdown = {
        "direct_prior_art": sum(1 for p in prior_approaches if p.get("relationship_type") == "direct_prior_art"),
        "enabling_technology": sum(1 for p in prior_approaches if p.get("relationship_type") == "enabling_technology"),
        "target_biology": sum(1 for p in prior_approaches if p.get("relationship_type") == "target_biology"),
        "adjacent_background": sum(1 for p in prior_approaches if p.get("relationship_type") == "adjacent_background"),
        "total_records": len(prior_approaches)
    }
"""

old_return = 'return {\n        "soundness_score": soundness_score,'
assert old_return in text, "old_return not found"
text = text.replace(old_return, validation_and_breakdown_code + '\n    return {\n        "soundness_score": soundness_score,', 1)

old_return_entry = '"closest_approach": closest_app,'
assert old_return_entry in text, "old_return_entry not found"
text = text.replace(old_return_entry, '"closest_approach": closest_app,\n        "relationship_breakdown": relationship_breakdown,', 1)

# Now, add BENCHMARK_PRIOR_ART helper accessor function or dict at module level
helper_code = """

def get_benchmark_prior_art() -> Dict[str, List[Dict[str, Any]]]:
    \"\"\"Returns curated benchmark prior art collections for benchmarked diagnostic and enzyme engineering domains.\"\"\"
    res_cas = audit_novelty_and_soundness(title="CRISPR-Cas12a Diagnostic", chassis="Cell-free", tool="CRISPR-Cas12a", target="NDM-1", hypothesis="", methodology="")
    res_pet = audit_novelty_and_soundness(title="PETase Enzyme Engineering", chassis="E. coli", tool="PETase", target="PET", hypothesis="", methodology="")
    return {
        "cas12a_detection": res_cas.get("prior_approaches", []),
        "petase_engineering": res_pet.get("prior_approaches", [])
    }


class _BenchmarkPriorArtDict(dict):
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
        return len(get_benchmark_prior_art())


BENCHMARK_PRIOR_ART = _BenchmarkPriorArtDict()
"""

text += helper_code

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Applied Repair B successfully!")
