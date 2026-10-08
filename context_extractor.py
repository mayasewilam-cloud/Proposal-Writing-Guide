"""
Context Extractor for the Trusted Research Workflow Agent.
Performs deterministic, explainable extraction of research context,
experimental entities, and regulatory triggers from proposal data.
Every extracted fact is anchored by verbatim evidence from the text
with dot-notation source provenance and automatic conflict detection.
"""

import re
from typing import Dict, Any, List, Tuple
from .models import ResearchContext, FieldEvidence, FieldStatus
from .llm_extractor import get_llm_extractor


# Known entity dictionaries for biological and biotechnological context
ORGANISM_TAXONOMY = {
    "escherichia coli": ("Escherichia coli", "Microbial Host / Gram-Negative Model"),
    "e. coli": ("Escherichia coli", "Microbial Host / Gram-Negative Model"),
    "pichia pastoris": ("Pichia pastoris (Komagataella phaffii)", "Yeast Secretory Host"),
    "komagataella": ("Komagataella phaffii", "Yeast Host"),
    "pseudomonas putida": ("Pseudomonas putida", "Bacterial Biodegradation Host"),
    "triticum aestivum": ("Triticum aestivum (Wheat)", "Agricultural Plant Model"),
    "arabidopsis thaliana": ("Arabidopsis thaliana", "Plant Model"),
    "saccharomyces cerevisiae": ("Saccharomyces cerevisiae", "Yeast Host"),
    "clinical isolate": ("Clinical Bacterial Isolate", "Human-Derived Pathogen Source"),
    "cell-free": ("Cell-Free Reaction Matrix", "Acellular Reaction System"),
    "aquaculture": ("Aquaculture Aquatic Microbiome", "Environmental Sample Matrix"),
}

MOLECULAR_TOOL_LEXICON = {
    "crispr-cas12a": ("CRISPR-Cas12a", "Targeted Endonuclease with Collateral ssDNA Cleavage"),
    "cas12a": ("CRISPR-Cas12a", "Targeted Endonuclease"),
    "crispr-cas9": ("CRISPR-Cas9", "Targeted Double-Strand DNA Endonuclease"),
    "cas9": ("CRISPR-Cas9", "Endonuclease"),
    "petase": ("PETase (Polyethylene Terephthalate Hydrolase)", "Enzymatic Plastic Depolymerase"),
    "mhatase": ("MHETase", "Enzymatic Depolymerase"),
    "rpa": ("Recombinase Polymerase Amplification (RPA)", "Isothermal DNA Amplification"),
    "lamp": ("Loop-Mediated Isothermal Amplification (LAMP)", "Isothermal Nucleic Acid Amplification"),
    "car-t": ("Chimeric Antigen Receptor (CAR-T)", "Engineered Cell Immunotherapy"),
    "aptamer": ("Nucleic Acid Aptamer", "Synthetic Affinity Probe"),
    "laccase": ("Laccase", "Oxidoreductase Enzyme"),
    "clea": ("Cross-Linked Enzyme Aggregates (CLEA)", "Enzyme Immobilization Carrier"),
}

HUMAN_TRIGGERS = [
    r"\bhuman\b", r"\bpatient[s]?\b", r"\bclinical\b", r"\bblood\b",
    r"\bserum\b", r"\bplasma\b", r"\bbiops(y|ies)\b", r"\bswab[s]?\b",
    r"\bdonor[s]?\b", r"\bvolunteer[s]?\b", r"\bparticipant[s]?\b",
    r"\bhospital\b", r"\bpatient cohort\b"
]

ANIMAL_TRIGGERS = [
    r"\bmice\b", r"\bmouse\b", r"\bmurine\b", r"\brat[s]?\b",
    r"\brabbit[s]?\b", r"\bzebrafish\b", r"\bin vivo\b", r"\banimal model\b",
    r"\bsacrifice\b", r"\bxenograft\b", r"\bguinea pig\b"
]

GENETIC_MOD_TRIGGERS = [
    r"\brecombinant\b", r"\bplasmid[s]?\b", r"\btransformation\b",
    r"\btransfection\b", r"\bvector\b", r"\bknock[-]?out\b",
    r"\bknock[-]?in\b", r"\bgrna\b", r"\bcrrna\b", r"\bexpression construct\b",
    r"\bengineered strain\b", r"\bsynthetic gene\b", r"\btransgenic\b"
]

PATHOGEN_AMR_TRIGGERS = [
    r"\bmcr-1\b", r"\bcolistin[- ]resistant\b", r"\bpathogen[s]?\b",
    r"\bpathogenic\b", r"\bvirulence\b", r"\bmultidrug[- ]resistant\b",
    r"\bmrsa\b", r"\besbl\b", r"\bcarbapenem\b", r"\bantimicrobial resistance\b",
    r"\bamr\b", r"\banthracis\b", r"\banthrax\b", r"\btuberculosis\b",
    r"\bsalmonella\b", r"\bshigella\b", r"\bclostridium\b", r"\bricin\b",
    r"\btoxin\b", r"\baerosol\b", r"\baerosoliz(e|ed|ation)\b", r"\bspore[s]?\b",
    r"\bdual[- ]use\b", r"\bebola\b", r"\bcholera\b"
]

BIOSAFETY_TRIGGERS = [
    r"\bbsl[- ]?1\b", r"\bbsl[- ]?2\b", r"\bbsl[- ]?3\b",
    r"\blaminar flow\b", r"\bbiosafety cabinet\b", r"\bcontainment\b",
    r"\bautoclave\b", r"\bbiohazard\b", r"\bdecontamination\b"
]


def _find_matches_with_provenance(corpus_parts: List[Tuple[str, str]], patterns: List[str], max_snippets: int = 2) -> List[Tuple[str, str, str]]:
    """
    Scans corpus parts preserving exact dot-notation field provenance.
    Returns list of (matched_term, snippet, source_path) tuples.
    """
    results = []
    for source_path, text in corpus_parts:
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                term = m.group(0)
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = ("..." if start > 0 else "") + text[start:end].strip().replace("\n", " ") + ("..." if end < len(text) else "")
                results.append((term, snippet, source_path))
                if len(results) >= max_snippets:
                    return results
    return results


def _find_matches_with_snippets(text: str, patterns: List[str], max_snippets: int = 2) -> List[Tuple[str, str]]:
    """Legacy helper: Returns list of (matched_term, snippet) tuples from text."""
    matches = _find_matches_with_provenance([("proposal.methodology", text)], patterns, max_snippets)
    return [(m[0], m[1]) for m in matches]


def extract_research_context(proposal_data: Dict[str, Any], project_id: str = "") -> ResearchContext:
    """
    Parses proposal data into a structured ResearchContext.
    If an external LLM API key (GEMINI_API_KEY or OPENAI_API_KEY) is configured,
    attempts neurosymbolic LLM extraction with strict verbatim evidence grounding.
    If no key is configured, or if the API call fails or times out, gracefully and
    deterministically falls back to the deterministic rule engine with zero disruption.
    """
    clean_id = project_id or proposal_data.get("student_id") or "PROJECT-001"

    # Hybrid Neurosymbolic check: optional perception plug-in (evaluated and reconciled AFTER deterministic safety rules)
    extractor = get_llm_extractor()
    llm_avail = bool(extractor.is_available())
    llm_result = None
    if llm_avail:
        try:
            llm_result = extractor.extract(proposal_data, project_id=clean_id)
        except Exception:
            llm_result = None  # Seamless fallback to deterministic engine on any failure

    title = (proposal_data.get("title") or "").strip()
    student_name = (proposal_data.get("student_name") or "Student Researcher").strip()

    context = ResearchContext(
        project_id=clean_id,
        title=title,
        researcher_name=student_name,
        research_area="Biotechnology"
    )
    context.extraction_mode = "deterministic_rules"
    context.llm_available = llm_avail
    context.checks_performed = [
        "organism_taxonomy_scan",
        "molecular_tool_lexicon_scan",
        "specimen_origin_scan",
        "human_clinical_trigger_and_contradiction_check",
        "vertebrate_animal_trigger_check",
        "recombinant_dna_gmo_trigger_check",
        "pathogen_amr_trigger_check",
        "biosafety_containment_conflict_check",
        "acellular_vs_living_specimen_conflict_check",
        "proposal_specification_completeness_check"
    ]

    # Compile unified text corpus with dot-notation field provenance tags
    corpus_parts: List[Tuple[str, str]] = []
    if title:
        corpus_parts.append(("proposal.title", title))
    abstract_field = proposal_data.get("abstract", "")
    if abstract_field:
        corpus_parts.append(("proposal.abstract", str(abstract_field)))
    chassis_field = proposal_data.get("chassis") or proposal_data.get("system", "")
    if chassis_field:
        corpus_parts.append(("proposal.chassis", str(chassis_field)))
    tool_field = proposal_data.get("tool", "")
    if tool_field:
        corpus_parts.append(("proposal.tool", str(tool_field)))
    target_field = proposal_data.get("target", "")
    if target_field:
        corpus_parts.append(("proposal.target", str(target_field)))
    methodology = proposal_data.get("methodology", "")
    if methodology:
        corpus_parts.append(("proposal.methodology", str(methodology)))
    pitfalls = proposal_data.get("pitfalls") or proposal_data.get("interpretations", "")
    if pitfalls:
        corpus_parts.append(("proposal.pitfalls", str(pitfalls)))
    expected_outcomes = proposal_data.get("expected_outcomes", "")
    if expected_outcomes:
        corpus_parts.append(("proposal.expected_outcomes", str(expected_outcomes)))
    
    # Optional sections with hierarchical dot-notation provenance
    aims_dict = proposal_data.get("aims", {})
    if isinstance(aims_dict, dict):
        for k in ["aim1", "aim2", "aim3"]:
            if aims_dict.get(k):
                corpus_parts.append((f"proposal.aims.{k}", str(aims_dict[k])))
    
    funnel_dict = proposal_data.get("funnel", {})
    if isinstance(funnel_dict, dict):
        for k in ["tier1", "tier2", "tier3", "tier4"]:
            if funnel_dict.get(k):
                corpus_parts.append((f"proposal.funnel.{k}", str(funnel_dict[k])))

    all_text = " ".join([txt for _, txt in corpus_parts])

    # Store structured proposal sections & input summary for transparency and section inspection
    context.proposal_sections = {
        "title": title,
        "abstract": str(abstract_field),
        "chassis": str(chassis_field),
        "tool": str(tool_field),
        "target": str(target_field),
        "methodology": str(methodology),
        "pitfalls": str(pitfalls),
        "expected_outcomes": str(expected_outcomes),
        "aims": aims_dict if isinstance(aims_dict, dict) else {},
        "funnel": funnel_dict if isinstance(funnel_dict, dict) else {}
    }
    context.input_summary = {
        "title": title,
        "chassis": str(chassis_field),
        "tool": str(tool_field),
        "target": str(target_field),
        "abstract_word_count": len(str(abstract_field).split()) if abstract_field else 0,
        "methodology_word_count": len(str(methodology).split()) if methodology else 0,
        "human_subjects_declared": proposal_data.get("human_subjects"),
        "recombinant_dna_declared": proposal_data.get("recombinant_dna"),
        "pathogen_work_declared": proposal_data.get("pathogen_work")
    }

    # 1. ORGANISM / CHASSIS EXTRACTION
    KNOWN_CHASSIS_KEYWORDS = [
        "escherichia", "e. coli", "coli", "pseudomonas", "bacillus", "yeast", 
        "saccharomyces", "komagataella", "pichia", "triticum", "wheat", "arabidopsis", 
        "plant", "mammalian", "cho", "hek", "human", "bacteri", "clinical isolate", 
        "cell-free", "in-vitro", "in vitro", "acellular", "aquaculture", "water", 
        "microbiome", "phage", "algae", "cyanobacteri", "fung", "strain"
    ]
    if chassis_field:
        is_rec = any(kw in str(chassis_field).lower() for kw in KNOWN_CHASSIS_KEYWORDS)
        if is_rec:
            context.organism_or_chassis = FieldEvidence(
                field="organism_or_chassis",
                value=chassis_field,
                source="proposal.chassis",
                status=FieldStatus.CONFIRMED,
                confidence=1.0,
                evidence=str(chassis_field),
                rationale="Explicitly declared by researcher in Chassis/System field."
            )
        else:
            context.organism_or_chassis = FieldEvidence(
                field="organism_or_chassis",
                value=chassis_field,
                source="proposal.chassis",
                status=FieldStatus.REQUIRES_HUMAN_REVIEW,
                confidence=0.4,
                evidence=str(chassis_field),
                rationale=f"Declared chassis '{chassis_field}' does not match standard biological taxonomies or acellular models. Verification required."
            )
            context.uncertainties.append({
                "field": "organism_or_chassis",
                "issue": f"Unrecognized biological chassis: '{chassis_field}'. Verification required."
            })
    else:
        # Scan for taxonomy terms
        found_org = False
        for k, (canonical, desc) in ORGANISM_TAXONOMY.items():
            matches = _find_matches_with_provenance(corpus_parts, [re.escape(k)])
            if matches:
                term, snip, src = matches[0]
                context.organism_or_chassis = FieldEvidence(
                    field="organism_or_chassis",
                    value=canonical,
                    source=src,
                    status=FieldStatus.INFERRED,
                    confidence=0.85,
                    evidence=snip,
                    rationale=f"Inferred from proposal text matching '{k}' ({desc})."
                )
                found_org = True
                break
        if not found_org:
            context.organism_or_chassis = FieldEvidence(
                field="organism_or_chassis",
                value=None,
                source="unspecified",
                status=FieldStatus.MISSING,
                confidence=0.0,
                evidence="",
                rationale="No standard biological host or reaction matrix detected."
            )
            context.uncertainties.append({
                "field": "organism_or_chassis",
                "issue": "Missing biological host organism or chassis declaration."
            })

    # 2. MOLECULAR TOOLS EXTRACTION
    tools_list = []
    if tool_field:
        tools_list.append(FieldEvidence(
            field="molecular_tool",
            value=tool_field,
            source="proposal.tool",
            status=FieldStatus.CONFIRMED,
            confidence=1.0,
            evidence=str(tool_field),
            rationale="Explicitly declared by researcher in Tool field."
        ))

    # Scan for other tools in text
    for k, (canonical, desc) in MOLECULAR_TOOL_LEXICON.items():
        if k in all_text.lower() and not any(k.lower() in t.value.lower() for t in tools_list):
            matches = _find_matches_with_provenance(corpus_parts, [re.escape(k)])
            if matches:
                term, snip, src = matches[0]
                tools_list.append(FieldEvidence(
                    field="molecular_tool",
                    value=canonical,
                    source=src,
                    status=FieldStatus.INFERRED,
                    confidence=0.85,
                    evidence=snip,
                    rationale=f"Detected from text matching '{k}'."
                ))
    context.molecular_tools = tools_list

    # 3. SAMPLE TYPE / ORIGIN EXTRACTION
    sample_matches = _find_matches_with_provenance(
        corpus_parts,
        [r"clinical isolate[s]?", r"patient swab[s]?", r"effluent", r"water sample[s]?", r"wastewater", r"blood sample[s]?", r"soil sample[s]?"]
    )
    if sample_matches:
        match_term, snip, src = sample_matches[0]
        context.sample_type = FieldEvidence(
            field="sample_type",
            value=match_term,
            source=src,
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence=snip,
            rationale=f"Identified specimen/matrix descriptor '{match_term}' in {src}."
        )
    else:
        context.sample_type = FieldEvidence(
            field="sample_type",
            value="Laboratory Reagent / Unspecified Sample",
            source="unspecified",
            status=FieldStatus.UNCERTAIN,
            confidence=0.40,
            evidence="",
            rationale="No explicit biological sample origin identified."
        )

    # 4. HUMAN SUBJECTS / CLINICAL MATERIALS REGULATORY TRIGGER
    human_matches = _find_matches_with_provenance(corpus_parts, HUMAN_TRIGGERS)
    declared_human = proposal_data.get("human_subjects")
    if human_matches:
        term, snip, src = human_matches[0]
        is_isolate = "clinical isolate" in all_text.lower() or "patient" in all_text.lower()
        has_provenance_info = "consent" in all_text.lower() or "atcc" in all_text.lower()
        
        # Check for explicit conflict: form denies human subjects but methodology includes them
        if declared_human is False or str(declared_human).lower() in ["false", "no", "none"]:
            status_val = FieldStatus.REQUIRES_HUMAN_REVIEW
            rationale_val = (
                f"Contradiction detected: Form specifies NO human subjects [proposal.human_subjects], "
                f"but text specifies clinical/human materials '{term}' [{src}]."
            )
            evidence_val = f"Form: False [proposal.human_subjects] | Contradicting text: '{snip}' [{src}]"
            context.uncertainties.append({
                "field": "human_subjects",
                "issue": rationale_val,
                "requires_human_review": True
            })
        else:
            status_val = FieldStatus.UNCERTAIN if (is_isolate and not has_provenance_info) else FieldStatus.CONFIRMED
            rationale_val = f"Triggered by human/clinical keyword '{term}' in {src}. Sample provenance requires verification."
            evidence_val = snip
            if status_val == FieldStatus.UNCERTAIN:
                context.uncertainties.append({
                    "field": "human_subjects",
                    "issue": f"Clinical material detected ('{term}') but donor consent or strain repository provenance is not specified."
                })

        context.human_subjects = FieldEvidence(
            field="human_subjects",
            value=True,
            source=src,
            status=status_val,
            confidence=0.88,
            evidence=evidence_val,
            rationale=rationale_val
        )
    elif declared_human is True or str(declared_human).lower() in ["true", "yes"]:
        context.human_subjects = FieldEvidence(
            field="human_subjects",
            value=True,
            source="proposal.human_subjects",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="human_subjects=True (intake declaration)",
            rationale="Explicitly declared via proposal intake flag."
        )
    else:
        context.human_subjects = FieldEvidence(
            field="human_subjects",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="",
            rationale="No human participant or clinical tissue keywords found."
        )

    # 5. ANIMAL SUBJECTS REGULATORY TRIGGER
    animal_matches = _find_matches_with_provenance(corpus_parts, ANIMAL_TRIGGERS)
    if animal_matches:
        term, snip, src = animal_matches[0]
        context.animal_subjects = FieldEvidence(
            field="animal_subjects",
            value=True,
            source=src,
            status=FieldStatus.CONFIRMED,
            confidence=0.92,
            evidence=snip,
            rationale=f"Triggered by animal model / in vivo keyword '{term}' in {src}."
        )
    else:
        context.animal_subjects = FieldEvidence(
            field="animal_subjects",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="",
            rationale="No vertebrate or invertebrate animal research terms identified."
        )

    # 6. GENETIC MODIFICATION & RECOMBINANT DNA TRIGGER
    gmo_matches = _find_matches_with_provenance(corpus_parts, GENETIC_MOD_TRIGGERS)
    declared_rdna = proposal_data.get("recombinant_dna")
    if gmo_matches:
        term, snip, src = gmo_matches[0]
        context.genetic_modification = FieldEvidence(
            field="genetic_modification",
            value=True,
            source=src,
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence=snip,
            rationale=f"Triggered by recombinant/cloning keyword '{term}' in {src}."
        )
        context.recombinant_dna = FieldEvidence(
            field="recombinant_dna",
            value=True,
            source=src,
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence=snip,
            rationale=f"Molecular genetic manipulation indicator '{term}' present in {src}."
        )
    elif declared_rdna is True or str(declared_rdna).lower() in ["true", "yes"]:
        context.genetic_modification = FieldEvidence(
            field="genetic_modification",
            value=True,
            source="proposal.recombinant_dna",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="recombinant_dna=True (intake declaration)",
            rationale="Explicitly declared via proposal intake flag."
        )
        context.recombinant_dna = FieldEvidence(
            field="recombinant_dna",
            value=True,
            source="proposal.recombinant_dna",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="recombinant_dna=True (intake declaration)",
            rationale="Explicitly declared via proposal intake flag."
        )
    else:
        context.genetic_modification = FieldEvidence(
            field="genetic_modification",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.85,
            evidence="",
            rationale="No recombinant vectors or genetic editing methods identified."
        )
        context.recombinant_dna = FieldEvidence(
            field="recombinant_dna",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.85,
            evidence="",
            rationale="No recombinant DNA manipulation indicated."
        )

    # 7. PATHOGEN & ANTIMICROBIAL RESISTANCE TRIGGER
    pathogen_matches = _find_matches_with_provenance(corpus_parts, PATHOGEN_AMR_TRIGGERS)
    declared_pathogen = proposal_data.get("pathogen_work")
    if pathogen_matches:
        term, snip, src = pathogen_matches[0]
        context.pathogen_work = FieldEvidence(
            field="pathogen_work",
            value=True,
            source=src,
            status=FieldStatus.CONFIRMED,
            confidence=0.92,
            evidence=snip,
            rationale=f"Triggered by pathogen/AMR indicator '{term}' in {src}."
        )
        if any(amr in term.lower() for amr in ["mcr-1", "resistant", "resistance", "mrsa", "esbl"]):
            context.antimicrobial_resistance = FieldEvidence(
                field="antimicrobial_resistance",
                value=True,
                source=src,
                status=FieldStatus.CONFIRMED,
                confidence=0.95,
                evidence=snip,
                rationale=f"Explicit drug-resistant determinant '{term}' recognized in {src}."
            )
    elif declared_pathogen is True or str(declared_pathogen).lower() in ["true", "yes"]:
        context.pathogen_work = FieldEvidence(
            field="pathogen_work",
            value=True,
            source="proposal.pathogen_work",
            status=FieldStatus.CONFIRMED,
            confidence=0.95,
            evidence="pathogen_work=True (intake declaration)",
            rationale="Explicitly declared via proposal intake flag."
        )
        context.antimicrobial_resistance = FieldEvidence(
            field="antimicrobial_resistance",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence="",
            rationale="No antimicrobial resistance determinants detected."
        )
    else:
        context.pathogen_work = FieldEvidence(
            field="pathogen_work",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence="",
            rationale="No high-consequence pathogen keywords detected."
        )
        context.antimicrobial_resistance = FieldEvidence(
            field="antimicrobial_resistance",
            value=False,
            source="proposal.methodology" if methodology else "system.default",
            status=FieldStatus.CONFIRMED,
            confidence=0.90,
            evidence="",
            rationale="No antimicrobial resistance determinants detected."
        )

    # 8. BIOSAFETY CONTAINMENT LEVEL ESTIMATE & CONFLICT CHECK
    bsl_matches = _find_matches_with_provenance(corpus_parts, BIOSAFETY_TRIGGERS)
    if bsl_matches:
        term, snip, src = bsl_matches[0]
        bsl_val = "BSL-2" if ("bsl-2" in term.lower() or "bsl 2" in term.lower()) else ("BSL-3" if ("bsl-3" in term.lower() or "bsl 3" in term.lower()) else "BSL-1")
        
        # Conflict Check: BSL-1 explicitly stated but AMR or high-risk pathogen present
        if bsl_val == "BSL-1" and (context.antimicrobial_resistance.value or context.pathogen_work.value):
            conflict_issue = (
                f"Contradiction detected: Stated containment is BSL-1 [{src}], "
                f"but high-consequence pathogen/AMR determinants are present ({context.antimicrobial_resistance.evidence or context.pathogen_work.evidence}). "
                "Institutional rules mandate minimum BSL-2 review."
            )
            context.biosafety_containment = FieldEvidence(
                field="biosafety_containment",
                value="BSL-1 (Conflict: BSL-2 Required)",
                source=src,
                status=FieldStatus.REQUIRES_HUMAN_REVIEW,
                confidence=0.95,
                evidence=f"Stated: '{snip}' [{src}] | Conflicting determinant: '{context.antimicrobial_resistance.evidence}'",
                rationale=conflict_issue
            )
            context.uncertainties.append({
                "field": "biosafety_containment",
                "issue": conflict_issue,
                "requires_human_review": True
            })
        else:
            context.biosafety_containment = FieldEvidence(
                field="biosafety_containment",
                value=bsl_val,
                source=src,
                status=FieldStatus.CONFIRMED,
                confidence=0.90,
                evidence=snip,
                rationale=f"Biosafety level/containment explicitly referenced: '{term}' in {src}."
            )
    else:
        # Infer BSL requirement based on pathogen or clinical isolate presence
        if context.pathogen_work.value or context.human_subjects.value:
            context.biosafety_containment = FieldEvidence(
                field="biosafety_containment",
                value="BSL-2 (Potentially Required)",
                source="regulatory.bsl_inference",
                status=FieldStatus.INFERRED,
                confidence=0.80,
                evidence="Clinical isolates or antimicrobial resistant determinants detected without explicit BSL specification.",
                rationale="Institutional guidelines mandate BSL-2 containment for clinical isolates and pathogenic bacteria."
            )
            context.uncertainties.append({
                "field": "biosafety_containment",
                "issue": "Pathogen or clinical isolate detected, but physical containment protocol (BSL-2) is not explicitly detailed."
            })
        else:
            context.biosafety_containment = FieldEvidence(
                field="biosafety_containment",
                value="BSL-1",
                source="system.default",
                status=FieldStatus.CONFIRMED,
                confidence=0.75,
                evidence="Standard non-pathogenic laboratory model.",
                rationale="Standard baseline for educational/non-pathogenic host organisms."
            )

    # 9. CROSS-FIELD CONFLICT CHECK: Chassis declared acellular vs methodology living/clinical materials
    if chassis_field:
        cf_lower = str(chassis_field).lower()
        is_declared_acellular = any(term in cf_lower for term in ["cell-free", "buffer", "in vitro buffer", "paper lateral", "paper matrix", "acellular"])
        has_living_conflict = bool(
            context.human_subjects.value or 
            context.animal_subjects.value or 
            (context.pathogen_work.value and "cell-free" not in context.pathogen_work.evidence.lower())
        )
        if is_declared_acellular and has_living_conflict:
            conflicting_ev = context.sample_type.evidence or context.human_subjects.evidence or context.animal_subjects.evidence
            conflicting_src = context.sample_type.source if context.sample_type.source != "unspecified" else (context.human_subjects.source if context.human_subjects.source != "unspecified" else "proposal.methodology")
            conflict_msg = (
                f"Contradiction detected: Form declares acellular chassis '{chassis_field}' [proposal.chassis], "
                f"but methodology specifies live clinical or in vivo specimens: '{conflicting_ev}' [{conflicting_src}]."
            )
            context.organism_or_chassis.status = FieldStatus.REQUIRES_HUMAN_REVIEW
            context.organism_or_chassis.evidence = f"Form: '{chassis_field}' [proposal.chassis] | Contradicting text: '{conflicting_ev}' [{conflicting_src}]"
            context.organism_or_chassis.rationale = conflict_msg
            context.uncertainties.append({
                "field": "organism_or_chassis",
                "issue": conflict_msg,
                "requires_human_review": True
            })

    # 10. SPECIFICATION SANITY CHECK: Flag placeholder, lorem ipsum, or nonsensical submissions
    title_clean = re.sub(r"[^a-zA-Z\s]", "", title).strip()
    is_lorem = "lorem ipsum" in str(methodology).lower() or "lorem ipsum" in str(abstract_field).lower()
    has_minimal_text = len(title_clean.split()) < 2 or (len(str(methodology).split()) < 3 and not aims_dict)
    if is_lorem or has_minimal_text:
        context.uncertainties.append({
            "field": "proposal.specification",
            "issue": "Proposal contains minimal, placeholder (e.g. Lorem Ipsum), or unverified text requiring researcher elaboration.",
            "requires_human_review": True
        })

    # 11. AUTHORITY HIERARCHY RECONCILIATION (Hard Safety Rule > Deterministic Validation > LLM Interpretation > Human Review)
    if llm_result is not None:
        context.extraction_mode = "llm_hybrid"
        context.llm_available = True
        context.checks_performed.extend([
            "llm_neurosymbolic_entity_extraction",
            "verbatim_evidence_span_validation",
            "authority_hierarchy_conflict_reconciliation"
        ])
        context.evidence_log.extend(llm_result.evidence_log)

        # Enrich non-conflicting descriptive fields if LLM provided grounded values
        if (
            llm_result.organism_or_chassis.value
            and context.organism_or_chassis.status != FieldStatus.REQUIRES_HUMAN_REVIEW
        ):
            context.organism_or_chassis = llm_result.organism_or_chassis

        if llm_result.sample_type.value and context.sample_type.status == FieldStatus.UNCERTAIN:
            context.sample_type = llm_result.sample_type

        if llm_result.molecular_tools:
            existing_vals = {str(t.value).lower() for t in context.molecular_tools if t.value}
            for llm_tool in llm_result.molecular_tools:
                if str(llm_tool.value).lower() not in existing_vals:
                    context.molecular_tools.append(llm_tool)

        # Mandatory safety & governance boolean triggers:
        # - Deterministic True CANNOT be downgraded to False by LLM; instead flag REQUIRES_HUMAN_REVIEW + uncertainty.
        # - LLM True (when deterministic was False) upgrades the trigger to True so no LLM-detected risk is ignored.
        safety_fields = [
            "human_subjects",
            "animal_subjects",
            "genetic_modification",
            "recombinant_dna",
            "pathogen_work",
            "antimicrobial_resistance"
        ]
        for s_field in safety_fields:
            det_ev = getattr(context, s_field)
            llm_ev = getattr(llm_result, s_field)
            if bool(det_ev.value) and not bool(llm_ev.value):
                conflict_note = (
                    f"Authority Hierarchy Override on '{s_field}': Deterministic safety rule triggered "
                    f"({det_ev.evidence or det_ev.rationale}), overriding permissive LLM output (value=False). "
                    "Escalated for mandatory human review."
                )
                det_ev.status = FieldStatus.REQUIRES_HUMAN_REVIEW
                det_ev.rationale = conflict_note
                context.uncertainties.append({
                    "field": s_field,
                    "issue": conflict_note,
                    "requires_human_review": True,
                    "authority_resolution": "deterministic_safety_rule_prevailed"
                })
            elif not bool(det_ev.value) and bool(llm_ev.value):
                # LLM detected an additional risk not matched by regex; preserve LLM risk flag
                setattr(context, s_field, llm_ev)
            elif bool(det_ev.value) and bool(llm_ev.value):
                # Both agree on risk; if deterministic flagged REQUIRES_HUMAN_REVIEW, keep that status
                if det_ev.status == FieldStatus.REQUIRES_HUMAN_REVIEW:
                    llm_ev.status = FieldStatus.REQUIRES_HUMAN_REVIEW
                setattr(context, s_field, det_ev if det_ev.status == FieldStatus.REQUIRES_HUMAN_REVIEW else llm_ev)

        # Biosafety containment level conflict check:
        # If deterministic rules require BSL-2 or flagged a BSL conflict, LLM cannot downgrade to BSL-1 CONFIRMED.
        det_bsl = str(context.biosafety_containment.value or "")
        llm_bsl = str(llm_result.biosafety_containment.value or "")
        if ("BSL-2" in det_bsl or context.biosafety_containment.status == FieldStatus.REQUIRES_HUMAN_REVIEW) and llm_bsl == "BSL-1":
            bsl_conflict = (
                f"Authority Hierarchy Override on 'biosafety_containment': Deterministic rule requires '{det_bsl}', "
                "overriding permissive LLM 'BSL-1' classification."
            )
            context.biosafety_containment.status = FieldStatus.REQUIRES_HUMAN_REVIEW
            context.biosafety_containment.rationale = bsl_conflict
            context.uncertainties.append({
                "field": "biosafety_containment",
                "issue": bsl_conflict,
                "requires_human_review": True,
                "authority_resolution": "deterministic_safety_rule_prevailed"
            })

        # Merge any additional LLM-reported uncertainties
        for u in llm_result.uncertainties:
            if not any(existing.get("issue") == u.get("issue") for existing in context.uncertainties):
                context.uncertainties.append(u)

    return context
