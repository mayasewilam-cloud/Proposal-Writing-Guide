"""
Rubric & Heuristic Auditing Engine for BT_301 Research Proposals.
Supports cellular hosts, cell-free diagnostics, nanotechnology, topical formulations, natural extracts, and computational systems.
Evaluates student proposals against the 11-point rubric (85 raw marks -> 10 GPA), with 3 decoupled review domains:
  Domain A: Scientific Validity (Experimental design, controls, statistics, objective-method traceability)
  Domain B: Academic Writing & Assignment Compliance (Title, abstract, funnel background, aims, future tense, references)
  Domain C: Translation & Commercialization (Market, SWOT, PESTEL, Budget, Timeline)
"""

import re
from typing import Dict, List, Any
from core.impact_novelty_engine import (
    audit_gap_statement,
    audit_novelty_and_soundness,
    audit_competitor_matrix_and_usp
)


# =========================================================================
# 10 Recognized Biotechnology Research Types
# =========================================================================
RESEARCH_TYPES = {
    "natural_extract": {
        "id": "natural_extract",
        "name": "Natural Product Extraction & Characterization",
        "icon": "🌿",
        "description": "Botanical, fungal, or marine extraction, phytochemical profiling, and yield/standardization.",
        "expected_controls": ["Extraction solvent blank", "Phytochemical reference standard (e.g. Quercetin, Gallic acid)"],
        "typical_assays": ["UV-Vis / HPLC profiling", "TLC / GC-MS", "Extraction yield optimization", "Spectrophotometric assay"]
    },
    "topical_formulation": {
        "id": "topical_formulation",
        "name": "Topical Formulation Development",
        "icon": "🧴",
        "description": "Creams, gels, nanoemulsions, hydrogels, and topical cosmetic/dermatological preparations.",
        "expected_controls": ["Unloaded vehicle blank (cream/gel base without active agent)", "Positive commercial comparator (standard marketed cream/ointment)"],
        "typical_assays": ["Organoleptic stability & phase separation", "pH & rheological viscosity", "Centrifugation / freeze-thaw cycles", "In vitro release / Franz cell diffusion"]
    },
    "anti_inflammatory": {
        "id": "anti_inflammatory",
        "name": "Antioxidant & Anti-Inflammatory Studies",
        "icon": "🛡️",
        "description": "Evaluation of radical scavenging, cytokine reduction, or modulation of inflammatory pathways.",
        "expected_controls": ["Untreated negative vehicle control", "LPS-only stimulated positive control", "Standard anti-inflammatory reference (e.g. Indomethacin, Dexamethasone, Hydrocortisone)"],
        "typical_assays": ["LPS-stimulated RAW 264.7 / THP-1 macrophages", "ELISA for TNF-alpha, IL-6, IL-1beta", "Griess assay for Nitric Oxide (NO)", "COX-2 / LOX inhibition", "DPPH / ABTS / FRAP for antioxidant profile"]
    },
    "antimicrobial": {
        "id": "antimicrobial",
        "name": "Antimicrobial & Susceptibility Studies",
        "icon": "🧫",
        "description": "Evaluation of antibacterial, antifungal, or antibiofilm efficacy against microbial pathogens.",
        "expected_controls": ["Sterility blank (uninoculated broth)", "Growth control (inoculated vehicle without drug)", "Standard antibiotic/antifungal reference drug (e.g. Ampicillin, Ciprofloxacin, Fluconazole)"],
        "typical_assays": ["Broth microdilution for MIC / MBC (CLSI/EUCAST)", "Disk diffusion / agar well diffusion", "Time-kill kinetics (CFU/mL)", "Crystal violet biofilm quantification"]
    },
    "molecular_biotech": {
        "id": "molecular_biotech",
        "name": "Molecular Biotechnology & Genetic Engineering",
        "icon": "🧬",
        "description": "Recombinant protein expression, construct cloning, CRISPR/Cas editing, or vector engineering.",
        "expected_controls": ["Wild-type / untransformed host baseline", "Empty vector mock-transfection control", "Non-targeting gRNA control (for CRISPR)"],
        "typical_assays": ["Restriction digest / sequencing verification", "SDS-PAGE / Western blot", "qPCR expression profiling", "Enzymatic specific activity / kcat / Km"]
    },
    "microbiology": {
        "id": "microbiology",
        "name": "Microbiology & Microbial Product Development",
        "icon": "🦠",
        "description": "Bacterial fermentation, microbial growth kinetics, bioreactor scale-up, or biomanufacturing.",
        "expected_controls": ["Uninoculated sterile media baseline", "Parental / wild-type strain comparator"],
        "typical_assays": ["OD600 growth curves", "Biomass / dry cell weight", "Substrate consumption & product titer (HPLC)", "Bioreactor yield (g/L/h)"]
    },
    "cell_culture": {
        "id": "cell_culture",
        "name": "Cell Culture & In Vitro Assays",
        "icon": "🔬",
        "description": "Mammalian/primary cell viability, cytotoxicity, proliferation, or apoptosis studies.",
        "expected_controls": ["Untreated cell control (100% viability baseline)", "Vehicle control (e.g. 0.1% DMSO)", "Positive cytotoxic reference (e.g. Doxorubicin, Cisplatin, Triton X-100)"],
        "typical_assays": ["MTT / CCK-8 / Resazurin viability", "Flow cytometry / Annexin V apoptosis", "Wound healing / scratch assay", "Lactate dehydrogenase (LDH) release"]
    },
    "computational": {
        "id": "computational",
        "name": "Computational Biology & Bioinformatics",
        "icon": "💻",
        "description": "Molecular docking, dynamic simulations, phylogenetic analysis, or genomics/transcriptomics pipelines.",
        "expected_controls": ["Redocking of co-crystallized ligand (RMSD validation)", "Known inactive / decoy benchmark set", "Negative scrambled sequence control"],
        "typical_assays": ["Binding energy / pose score (kcal/mol)", "RMSD / RMSF trajectories (MD simulation)", "Cross-validation / ROC-AUC / PR-AUC", "Differential gene expression (DESeq2/edgeR)"]
    },
    "clinical_observational": {
        "id": "clinical_observational",
        "name": "Clinical or Observational Research",
        "icon": "📋",
        "description": "Patient cohorts, epidemiological surveys, diagnostic specimen evaluation, or retrospective audits.",
        "expected_controls": ["Healthy control cohort / norm reference values", "Placebo or standard-of-care comparator group"],
        "typical_assays": ["Sensitivity, specificity, PPV, NPV", "ROC curve analysis", "Chi-square / Fisher's exact / multivariable logistic regression", "Pre- and post-intervention scores"]
    },
    "review_non_exp": {
        "id": "review_non_exp",
        "name": "Review-Based & Non-Experimental Projects",
        "icon": "📚",
        "description": "Systematic literature reviews, meta-analyses, bibliometric mapping, or policy frameworks.",
        "expected_controls": ["PRISMA screening protocol", "Risk of bias assessment (Cochrane RoB / ROBINS-I)"],
        "typical_assays": ["Standardized mean differences (SMD) / Odds Ratios", "Heterogeneity quantification (I2 statistic)", "Funnel plots for publication bias", "Thematic synthesis"]
    }
}


def detect_research_type(title: str, text: str = "", chassis: str = "", tool: str = "") -> str:
    """
    Infers the predominant biotechnology project type from supplied proposal text.
    """
    combined = f"{title} {text} {chassis} {tool}".lower()
    if re.search(r"\b(?:in silico|molecular docking|docking|molecular dynamics|bioinformatics|pipeline|alphafold|qsar|virtual screening)\b", combined):
        return "computational"
    if re.search(r"\b(?:systematic review|meta-analysis|scoping review|literature review|overview|bibliometric)\b", combined):
        return "review_non_exp"
    if re.search(r"\b(?:patient cohort|observational study|epidemiological|clinical survey|retrospective audit|patient registry)\b", combined):
        return "clinical_observational"
    if re.search(r"\b(?:cream|gel\b|ointment|lotion|emulsion|hydrogel|topical|transdermal|carbomer|cleansing gel|cosmeceutic)\b", combined):
        return "topical_formulation"
    if re.search(r"\b(?:anti-?inflamm[a-z]*|inflammation|cytokine[a-z]*|raw\s*264|thp-?1|macrophage[a-z]*|cox-?2|nitric oxide|tnf)\b", combined):
        return "anti_inflammatory"
    if re.search(r"\b(?:antibacteri[a-z]*|antimicrob[a-z]*|antifung[a-z]*|mic\b|mbc\b|susceptibility|disk diffusion|biofilm|zone of inhibition)\b", combined):
        return "antimicrobial"
    if re.search(r"\b(?:extract|plant extract|phytochem[a-z]*|botanical|maceration|soxhlet|herbal|calendula|aloe|chamomile|saponin|flavonoid)\b", combined):
        return "natural_extract"
    if re.search(r"\b(?:fermentation|bioreactor|growth curve|biomanufacturing|microbial factory|biomass|titer)\b", combined):
        return "microbiology"
    if re.search(r"\b(?:mtt assay|cell viability|cancer cells|mcf-7|hela|cytotoxicity|flow cytometry|annexin)\b", combined):
        return "cell_culture"
    return "molecular_biotech"


def audit_title(title: str, system: str = "", tool: str = "", chassis: str = "", target: str = "", research_type: str = None) -> Dict[str, Any]:
    """
    Rubric Item 1: Title (2% marks).
    Evaluates whether the title accurately communicates:
      1. Research Subject / Active Intervention
      2. Experimental Model / Host Chassis (In Vitro cell line, In Vivo animal species, Ex Vivo tissue, or In Silico method)
      3. Formulation / Delivery Matrix (if applicable, e.g. cream, hydrogel, emulsion)
      4. Intended Outcome, Target Condition, or Practical Application
    Distinguishes delivery matrix (e.g. 'Cream') from true biological chassis (e.g. RAW 264.7 macrophages, BALB/c mice).
    Constructive feedback guides students to publication-grade research paper caliber.
    """
    system = system or chassis
    title_clean = title.strip()
    words = title_clean.split()
    word_count = len(words)
    
    issues = []
    strengths = []
    recommendations = []
    awarded_marks = 0.0

    if not title_clean:
        return {
            "score": 0.0,
            "max": 2.0,
            "passed": False,
            "issues": ["Title is empty."],
            "strengths": [],
            "feedback": "Provide a complete scientific title identifying your subject, model/system, and application."
        }

    # Rubric check: brief titles under 6 words receive 0.0
    if word_count < 6:
        issues.append(f"Title is too brief ({word_count} words). Academic grant titles require 8–24 words.")
    elif word_count > 32:
        issues.append(f"Title is overly lengthy ({word_count} words). Aim for under 28 words to preserve punchiness.")
    else:
        strengths.append(f"Appropriate academic length ({word_count} words).")

    # Constructive note for descriptive phrasing
    descriptive_patterns = [
        r"^(the\s+)?effect of\b",
        r"^(the\s+)?role of\b",
        r"^(the\s+)?impact of\b",
        r"^study of\b",
        r"^a study on\b",
        r"^research on\b",
        r"^investigation into\b",
        r"^evaluation of\b",
        r"^analysis of\b"
    ]
    is_descriptive = False
    for pat in descriptive_patterns:
        m = re.search(pat, title_clean, re.IGNORECASE)
        if m:
            is_descriptive = True
            recommendations.append(
                f"Academic Publishing Standard: While '{m.group(0)}' accurately identifies your research subject, "
                f"peer-reviewed research papers lead directly with the active agent, formulation platform, and experimental scope "
                f"(e.g. 'Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized Calendula Cream in RAW 264.7 Macrophages') "
                f"to create a direct, publication-grade title. This is an optional stylistic refinement."
            )
            break

    lower_t = title_clean.lower()

    # 1. Subject / Intervention / Active Agent check
    tool_found = False
    tool_words = [w for w in re.split(r"[\s,\(\)\-_/]+", tool.lower()) if len(w) >= 4 and w not in ["engineered", "recombinant", "the", "and", "for", "with"]] if tool else []
    if tool and (tool.lower() in lower_t or any(w in lower_t for w in tool_words)):
        tool_found = True
        strengths.append(f"Active intervention or agent explicitly named ('{tool}').")
    elif any(term in lower_t for term in [
        "extract", "cream", "gel", "formulation", "calendula", "aloe", "chamomile", "phytochem",
        "crispr", "cas12", "cas9", "base edit", "petase", "cutinase", "enzyme", "aptamer", "antibody",
        "nanoparticle", "peptide", "vector", "vaccine", "docking", "inhibitor", "compound",
        "probiotic", "metabolite", "surfactant", "emulsion", "hydrogel", "cleanser", "bioreactor",
        "silver", "chitosan", "bioactive"
    ]):
        tool_found = True
        strengths.append("Research subject, active agent, or molecular intervention recognized.")
    else:
        issues.append("Specific active agent, intervention, or research subject is missing.")

    # 2. Distinguish Delivery Matrix vs. True Experimental Biological Model / Chassis
    # Formulation / Delivery Matrix
    has_formulation_matrix = any(term in lower_t for term in [
        "cream", "gel", "emulsion", "formulation", "ointment", "hydrogel", "topical",
        "nanoparticle", "nanoparticles", "liposome", "liposomal", "microneedle", "lotion", "cleanser", "snedds"
    ])

    # Biological Model / Testing Chassis (In Vitro cell line, In Vivo animal species, Ex Vivo tissue, In Silico computational method, or microbial host)
    has_in_vitro_cell = any(term in lower_t for term in [
        "raw 264", "raw264", "hacat", "hdf", "fibroblast", "fibroblasts", "keratinocyte", "keratinocytes",
        "macrophage", "macrophages", "hepg2", "hek293", "mcf-7", "thp-1", "caco-2", "in vitro", "cell line",
        "cell culture", "primary cells", "pbmcs"
    ])
    has_in_vivo_animal = any(term in lower_t for term in [
        "balb/c", "c57bl", "wistar", "sprague-dawley", "murine", "mice", "mouse", "rat", "rats",
        "rabbit", "rabbits", "in vivo", "animal model", "edema model", "ear edema"
    ])
    has_ex_vivo_tissue = any(term in lower_t for term in [
        "porcine skin", "porcine ear", "franz cell", "franz diffusion", "skin explant", "ex vivo", "excised skin"
    ])
    has_in_silico = any(term in lower_t for term in [
        "molecular docking", "molecular dynamics", "in silico", "virtual screening", "binding simulations"
    ])
    has_microbial_host = any(term in lower_t for term in [
        "coli", "pastoris", "yeast", "bacillus", "pseudomonas", "staphylococcus", "aureus", "mrsa",
        "arabidopsis", "triticum", "wheat", "rice"
    ])

    has_explicit_bio_model = has_in_vitro_cell or has_in_vivo_animal or has_ex_vivo_tissue or has_in_silico or has_microbial_host

    # Check against declared system argument as well
    system_words = [w for w in re.split(r"[\s,\(\)\-_/]+", system.lower()) if len(w) >= 4 and w not in ["the", "and", "for", "with"]] if system else []
    system_match = bool(system and (system.lower() in lower_t or any(w in lower_t for w in system_words)))

    system_found = system_match or has_explicit_bio_model or has_formulation_matrix

    if has_explicit_bio_model:
        strengths.append("Publication-Grade Experimental Model: Biological testing chassis explicitly declared (cell line, animal species, or tissue model).")
    elif has_formulation_matrix:
        strengths.append("Delivery matrix or pharmaceutical formulation recognized in title.")
        # Scientific guidance: Formulation matrix is not a biological testing chassis!
        recommendations.append(
            "🔬 Publication-Grade Scientific Recommendation: Your title specifies the delivery matrix ('Cream' / formulation), but does not state the experimental biological model. "
            "Peer-reviewed research papers must declare whether testing is in vitro (naming the exact cell type, e.g. 'in RAW 264.7 Macrophages' or 'in HaCaT Keratinocytes'), "
            "in vivo (naming the animal species/strain, e.g. 'in a BALB/c Murine Edema Model'), ex vivo (e.g. 'in Porcine Skin Franz Diffusion Cells'), "
            "or in silico (e.g. 'Molecular Docking against COX-2'). Specifying your testing model elevates your proposal to publication caliber."
        )
    elif system_found:
        strengths.append(f"Experimental system or model explicitly named ('{system}').")
    else:
        issues.append("Experimental system, host organism, or delivery matrix is missing.")

    # 3. Application / Outcome check
    app_found = False
    target_words = [w for w in re.split(r"[\s,\(\)\-_/]+", target.lower()) if len(w) >= 4 and w not in ["rate", "with", "than", "from", "exceeding", "target"]] if target else []
    if target and (target.lower() in lower_t or any(w in lower_t for w in target_words)):
        app_found = True
        strengths.append(f"Target application or benchmark recognized from goals ('{target}').")
    else:
        app_indicators = [
            "inflammation", "wound", "healing", "skin", "infection", "cancer", "tumor", "tolerance",
            "salinity", "drought", "degradation", "depolymeriz", "plastic", "recycl", "upcycl", "detection",
            "diagnostic", "therapy", "treatment", "prevention", "protection", "eradication", "removal",
            "clearing", "yield", "stability", "accelerat", "convers", "product", "synthes", "express",
            "activit", "cataly", "hydroly", "for ", "against ", "to enhance", "to reduce", "to inhibit", "to achieve", "to degrade"
        ]
        if any(ind in lower_t for ind in app_indicators):
            app_found = True
            strengths.append("Target application, condition, or functional outcome specified.")
        else:
            issues.append("Target application, condition, or intended outcome is missing.")

    # 4. Check for quantitative milestone or clinical benchmark comparator
    has_milestone = bool(re.search(r'\b(\d+%|>\s*\d+|<\s*\d+|ic50|mic\b|mbc\b|kd\b|ec50\b|flux\b|closure|hydrocortisone|corticosteroid|comparator|benchmarked)\b', lower_t))
    if has_milestone:
        strengths.append("Quantitative milestone or reference comparator explicitly declared.")
    else:
        recommendations.append(
            "Target Benchmark / Comparator Suggestion: Consider specifying the target biological milestone or reference standard "
            "(e.g. 'to Inhibit Pro-Inflammatory Mediators Benchmarked Against Hydrocortisone 1%' or 'to Attain >80% Wound Closure') "
            "to clearly communicate your study's quantitative benchmark."
        )

    # Scoring: Under rubric, titles under 6 words receive 0.0
    if word_count < 6:
        awarded_marks = 0.0
        passed = False
        feedback = f"0.0/2.0 Awarded. Title is too brief ({word_count} words). Academic grant titles require 8–24 words."
    elif tool_found and (system_found or app_found):
        awarded_marks = 2.0
        passed = True
        if is_descriptive:
            feedback = "Title communicates research subject, delivery system, and application (2.0/2.0 awarded). An optional stylistic refinement is suggested below."
        else:
            feedback = "Strong, mechanistically grounded title (2.0/2.0 awarded)."
    elif tool_found or system_found:
        awarded_marks = 1.0
        passed = False
        feedback = "Title is partially complete (1.0/2.0 awarded). Ensure both the active tool/agent and host/target application are specified."
    else:
        awarded_marks = 0.5
        passed = False
        feedback = "Title lacks critical scientific components (0.5/2.0 awarded). Explicitly name the research subject, model chassis, and application."

    # Constructive suggestions
    if is_descriptive:
        recommendations.append(
            f"Optional Stylistic Suggestion: While your title is scientifically valid, you may make it more impactful by leading with an active engineering verb or molecular tool (e.g., 'Formulation and Evaluation of {tool or 'Phytochemical'} {system or 'Cream'} for {research_type or 'Therapeutic Application'}')."
        )
    if not (system_found and app_found):
        recommendations.append("Ensure both your host experimental model (or delivery system) and target application are clear to grant reviewers.")

    return {
        "score": awarded_marks,
        "max": 2.0,
        "passed": passed,
        "word_count": word_count,
        "tool_found": tool_found,
        "system_found": system_found,
        "app_found": app_found,
        "is_descriptive": is_descriptive,
        "has_explicit_bio_model": has_explicit_bio_model,
        "has_formulation_matrix": has_formulation_matrix,
        "issues": issues,
        "strengths": strengths,
        "recommendations": recommendations,
        "feedback": feedback
    }

def audit_abstract(abstract: str) -> Dict[str, Any]:
    """
    Rubric Item 2: Abstract (5% Scaled).
    Strict 250-word ceiling.
    Balances Problem (2%), Methodology (2%), Expected Outcomes (1%).
    """
    abstract_clean = abstract.strip()
    words = abstract_clean.split()
    word_count = len(words)
    
    issues = []
    strengths = []

    if not abstract_clean:
        return {
            "score": 0.0,
            "max": 5.0,
            "word_count": 0,
            "issues": ["Abstract is empty."],
            "strengths": [],
            "feedback": "Abstract required (250-word maximum)."
        }

    penalty = 0.0
    if word_count > 250:
        penalty = min(2.0, (word_count - 250) * 0.05)
        issues.append(f"Abstract exceeds the 250-word ceiling ({word_count} words). Shorten by {word_count - 250} words to adhere to strict submission guidelines.")
    elif word_count < 40:
        penalty = 1.5
        issues.append(f"Abstract is too brief ({word_count} words). Standard grant abstracts require 150–250 words to properly outline problem, methods, and outcomes.")
    elif word_count < 75:
        penalty = 0.0
        strengths.append(f"Concise structured abstract draft ({word_count} words). Expanding towards 150–250 words is recommended for final submission.")
    else:
        strengths.append(f"Word count ({word_count} words) conforms to the 150–250 word guidance.")

    # 1. Problem / burden keywords (2%)
    problem_kw = ["crisis", "challenge", "burden", "mortality", "economic", "resistance", "loss", "patient", "threat", "pollution", "prevalence", "demand", "need", "limit", "cost", "inflamm", "disease", "adverse", "side effect"]
    problem_hits = sum(1 for kw in problem_kw if kw in abstract_clean.lower())
    problem_score = 2.0 if problem_hits >= 2 else (1.0 if problem_hits == 1 else 0.5)

    # 2. Methodology keywords (2%)
    method_kw = ["will be", "cloned", "expressed", "assay", "assayed", "construct", "screen", "transform", "measure", "quantif", "formulat", "extract", "synthes", "evaluat", "characteriz", "model", "docking", "pipeline", "variant", "bioreactor", "mutation", "disulfide"]
    method_hits = sum(1 for kw in method_kw if kw in abstract_clean.lower())
    method_score = 2.0 if method_hits >= 2 else (1.0 if method_hits == 1 else 0.5)

    # 3. Expected outcomes & significance (1%)
    outcome_kw = ["expect", "anticipate", "milestone", "achieve", "yield", "fold", "improve", "benchmark", "target", "result", "demonstrate", "efficacy", "stability", "cure", "reduc", "upcycl"]
    outcome_hits = sum(1 for kw in outcome_kw if kw in abstract_clean.lower())
    outcome_score = 1.0 if outcome_hits >= 1 else 0.0

    raw = problem_score + method_score + outcome_score - penalty
    score = round(max(0.0, min(5.0, raw)), 1)

    return {
        "score": score,
        "max": 5.0,
        "word_count": word_count,
        "issues": issues,
        "strengths": strengths,
        "feedback": f"Structured Abstract scored {score}/5.0 (Word count: {word_count})."
    }

def audit_funnel_background(tier1: str, tier2: str, tier3: str, tier4: str) -> Dict[str, Any]:
    """
    Rubric Item 3: Background & Funnel (20% Scaled).
    Tier 1: Problem Significance & Epidemiological Burden (5%)
    Tier 2: Current Scientific Benchmark & Methodological Baselines (5%)
    Tier 3: Critical Scientific Knowledge Gap & Mechanistic Flaw (5%)
    Tier 4: Primary Project Aim, Mechanistic Hypothesis & Objectives (5%)
    """
    tier_reports = []

    # Tier 1 Audit: Burden (5%)
    t1_score = 0.0
    t1_issues = []
    t1_strengths = []
    if not tier1.strip():
        t1_issues.append("Tier 1 is missing.")
    else:
        has_number = bool(re.search(r"\b\d+(\\.\d+)?\b", tier1))
        has_citation = bool(re.search(r"\[[0-9,\s-]+\]|\([A-Za-z]+(?:\s+et\s+al\\.)?,\s*\d{4}\)", tier1))
        if has_number:
            t1_score += 2.5
            t1_strengths.append("Contains quantified burden metric (statistics, percentages, or monetary impact).")
        else:
            t1_issues.append("Missing an empirical quantified statistic (e.g. annual patient incidence, economic loss, or global burden).")
        if has_citation:
            t1_score += 1.5
            t1_strengths.append("Includes literature citation.")
        else:
            t1_issues.append("Missing peer-reviewed citation for the problem burden statement.")
        if len(tier1.split()) >= 20:
            t1_score += 1.0
    t1_score = min(5.0, t1_score)
    tier_reports.append({"tier": 1, "name": "Epidemiological & Global Burden", "score": t1_score, "max": 5.0, "issues": t1_issues, "strengths": t1_strengths})

    # Tier 2 Audit: Current Literature & Baseline (5%)
    t2_score = 0.0
    t2_issues = []
    t2_strengths = []
    if not tier2.strip():
        t2_issues.append("Tier 2 is missing.")
    else:
        has_current_terms = any(term in tier2.lower() for term in ["conventional", "currently", "standard", "gold standard", "existing", "baseline", "prior", "commercial", "traditional", "published"])
        has_citation = bool(re.search(r"\[[0-9,\s-]+\]|\([A-Za-z]+(?:\s+et\s+al\\.)?,\s*\d{4}\)", tier2))
        if has_current_terms:
            t2_score += 2.5
            t2_strengths.append("Documents current scientific benchmark methodology.")
        else:
            t2_issues.append("Clearly state existing baseline solutions or what current standard protocols achieve.")
        if has_citation:
            t2_score += 1.5
            t2_strengths.append("Cites primary literature.")
        else:
            t2_issues.append("Missing citation for current scientific benchmark.")
        if len(tier2.split()) >= 20:
            t2_score += 1.0
    t2_score = min(5.0, t2_score)
    tier_reports.append({"tier": 2, "name": "Current Scientific Benchmark", "score": t2_score, "max": 5.0, "issues": t2_issues, "strengths": t2_strengths})

    # Tier 3 Audit: Knowledge Gap & Mechanistic Flaw (5%)
    t3_score = 0.0
    t3_issues = []
    t3_strengths = []
    if not tier3.strip():
        t3_issues.append("Tier 3 is missing.")
    else:
        has_gap_terms = any(term in tier3.lower() for term in ["however", "remains", "unclear", "unresolved", "bottleneck", "barrier", "limitation", "lacks", "challenge", "gap", "flaw", "instability", "degrade"])
        if has_gap_terms:
            t3_score += 2.5
            t3_strengths.append("Identifies clear bottleneck or knowledge gap.")
        else:
            t3_issues.append("Missing explicit contrastive gap phrasing (e.g. 'However, the biophysical barrier... remains unknown').")
        has_strawman = any(term in tier3.lower() for term in ["no one has ever", "never been done", "first time in history", "no research exists", "no studies have been done"])
        if has_strawman:
            t3_issues.append("Strawman Gap Alert: Avoid claiming 'no research exists'. State the specific technical or biological parameter that remains unaddressed.")
        else:
            t3_score += 1.5
        if len(tier3.split()) >= 20:
            t3_score += 1.0
    t3_score = min(5.0, t3_score)
    tier_reports.append({"tier": 3, "name": "Critical Scientific Knowledge Gap", "score": t3_score, "max": 5.0, "issues": t3_issues, "strengths": t3_strengths})

    # Tier 4 Audit: Mechanistic Hypothesis & Solution (5%)
    t4_score = 0.0
    t4_issues = []
    t4_strengths = []
    if not tier4.strip():
        t4_issues.append("Tier 4 is missing.")
    else:
        has_hypo_terms = any(term in tier4.lower() for term in ["hypothesize", "hypothesis", "we propose", "this project will", "we aim to", "here, we", "objective", "will develop", "will formulate", "will test"])
        if has_hypo_terms:
            t4_score += 3.0
            t4_strengths.append("States explicit research approach / hypothesis.")
        else:
            t4_issues.append("State an explicit testable hypothesis (e.g. 'We hypothesize that formulating... will achieve...').")
        if len(tier4.split()) >= 20:
            t4_score += 2.0
    t4_score = min(5.0, t4_score)
    tier_reports.append({"tier": 4, "name": "Primary Project Aim & Hypothesis", "score": t4_score, "max": 5.0, "issues": t4_issues, "strengths": t4_strengths})

    total_funnel_score = sum(tr["score"] for tr in tier_reports)
    return {
        "score": total_funnel_score,
        "max": 20.0,
        "tiers": tier_reports,
        "feedback": f"Background Inverted Funnel scored {total_funnel_score}/20.0 marks."
    }


def audit_aims_independence(aim1: str, aim2: str, aim3: str, research_type: str = None) -> Dict[str, Any]:
    """
    Audits the 3 Specific Objectives (Specific Aims) against the Domino Collapse Trap.
    Objective 2 must not depend completely on Objective 1 achieving 100% success.
    Recognizes exploratory profiling aims as legitimate without penalizing for lack of arbitrary numerical thresholds.
    """
    s1 = str(aim1 or "").strip()
    s2 = str(aim2 or "").strip()
    s3 = str(aim3 or "").strip()
    aims = [("Specific Objective 1", s1), ("Specific Objective 2", s2), ("Specific Objective 3", s3)]
    issues = []
    strengths = []

    populated = [a for a in aims if a[1]]
    if len(populated) < 3:
        issues.append(f"Only {len(populated)} of 3 Specific Objectives provided. Academic biotechnology proposals require 3 distinct objectives.")
        return {
            "score": len(populated) * 1.5,
            "max": 5.0,
            "issues": issues,
            "strengths": strengths,
            "feedback": "Provide all 3 Specific Objectives."
        }

    domino_phrases = ["if aim 1 works", "following successful completion of aim 1", "pending positive results in aim 1", "if objective 1 succeeds", "if successful"]
    has_domino = False
    for name, content in aims[1:]:
        for dp in domino_phrases:
            if dp in content.lower():
                has_domino = True
                issues.append(f"DOMINO COLLAPSE RISK in {name}: Found conditional dependency ('{dp}'). If Objective 1 experiences technical delays, {name} collapses. Provide an active parallel baseline.")

    if not has_domino:
        strengths.append("Objectives exhibit parallel, decoupled feasibility (passes Domino Collapse check).")

    # Exploratory vs Benchmark Milestone Check for Aim 2
    a2_text = aims[1][1].lower()
    has_num = bool(re.search(r"\b\d+(\\.\d+)?\s*(?:%|µg/ml|ug/ml|mg/ml|µm|um|nm|mm|hours?|hrs?|days?|fold|kcat|km|mic|mbc|ic50)\b|(?:>|<|≥|≤)\s*\d+", a2_text))
    is_exploratory = any(term in a2_text for term in ["characteriz", "profil", "identif", "screen", "phytochem", "metabolite", "elucidat", "preliminar", "assess", "evaluat", "releas", "formulat", "kinetic", "assay"])
    
    if has_num:
        strengths.append("Objective 2 defines a quantifiable milestone (verify basis in published benchmark or preliminary data).")
    elif is_exploratory:
        strengths.append("Objective 2 declares an exploratory/discovery characterization aim. To maximize grant rigor, define qualitative acceptance criteria.")
    else:
        issues.append("Objective 2 expresses general qualitative intent. Specify either a target milestone (e.g., % release, MIC, or yield) or explicit qualitative acceptance criteria.")

    score = 5.0 if (not has_domino and len(issues) == 0) else (3.5 if not has_domino else 2.0)
    return {
        "score": score,
        "max": 5.0,
        "has_domino_risk": has_domino,
        "domino_failure_risk": has_domino,
        "exploratory_recognized": is_exploratory,
        "issues": issues,
        "strengths": strengths,
        "feedback": f"Specific Objectives scored {score}/5.0."
    }


def audit_methodology_tense(methodology: str) -> Dict[str, Any]:
    text = methodology.strip()
    if not text:
        return {
            "score": 0.0,
            "max": 15.0,
            "tense_mark": 0.0,
            "past_violations": [],
            "issues": ["Methodology text is empty."],
            "strengths": [],
            "feedback": "Methodology required (15% total marks)."
        }

    issues = []
    strengths = []
    future_markers = len(re.findall(r"\b(will be|shall be|will undergo|will evaluate|will construct|will measure|will quantify|will synthesize|will isolate|will test|will assess|will determine|will compare|will serve)\b", text, re.IGNORECASE))
    past_markers = re.findall(r"\b(was [a-z]+ed|were [a-z]+ed|we [a-z]+ed|was incubated|were inoculated|was performed|were collected|was added|were analyzed|was measured|was observed|were observed|we incubated|we measured|we performed|we analyzed|we observed|we tested|we collected|we cultured)\b", text, re.IGNORECASE)
    past_count = len(past_markers)

    if future_markers >= 2 and past_count == 0:
        strengths.append(f"Adheres to prospective future tense ({future_markers} future tense auxiliary verbs identified).")
        tense_mark = 1.0
    elif future_markers >= 1 and past_count == 0:
        strengths.append("Adheres to future tense (add more 'will be' auxiliary markers to strengthen).")
        tense_mark = 0.8
    elif past_count > 0 and future_markers > past_count:
        tense_mark = 0.5
        issues.append(f"Mixed tense detected ({past_count} past tense verbs vs {future_markers} future). Proposals must describe proposed experiments in future tense.")
    elif past_count > 0:
        tense_mark = 0.0
        issues.append(f"Past tense phrasing detected ({past_count} past tense verbs). Grant proposals must use prospective future tense ('will be incubated', not 'was incubated').")
    else:
        tense_mark = 0.5
        issues.append("Add future tense auxiliary verbs ('will be evaluated', 'will be measured') to clearly frame prospective grant activities.")

    # Methodology comprehensiveness (15% scaled)
    word_count = len(text.split())
    if word_count >= 120:
        base_score = 12.0
        strengths.append(f"Methodology exhibits substantial protocol depth ({word_count} words).")
    elif word_count >= 40:
        base_score = 11.0
        strengths.append(f"Methodology provides prospective protocol structure ({word_count} words). Expand with instrument specifics and replicate parameters.")
    else:
        base_score = 5.0
        issues.append(f"Methodology is underdeveloped ({word_count} words). Provide complete phase-by-phase experimental procedures.")

    total_meth_score = round(min(15.0, base_score + (tense_mark * 3.0)), 1)
    return {
        "score": total_meth_score,
        "max": 15.0,
        "tense_mark": tense_mark,
        "past_violations": past_markers,
        "issues": issues,
        "strengths": strengths,
        "feedback": f"Methodology scored {total_meth_score}/15.0 marks."
    }

def audit_swot_pestel(swot_data: Dict[str, str], pestel_data: Dict[str, str]) -> Dict[str, Any]:
    issues = []
    strengths = []
    swot_score = 0.0

    student_cliches = ["we are students", "lack of experience", "not enough time", "budget might run out", "we are beginners", "limited knowledge"]
    weaknesses = (swot_data.get("weaknesses") or swot_data.get("w", "")).lower()
    threats = (swot_data.get("threats") or swot_data.get("t", "")).lower()
    strengths_text = (swot_data.get("strengths") or swot_data.get("s", "")).lower()
    opportunities = (swot_data.get("opportunities") or swot_data.get("o", "")).lower()

    found_cliche = False
    for cl in student_cliches:
        if cl in weaknesses or cl in threats:
            found_cliche = True
            issues.append(f"Avoid student cliché: '{cl}'. Reviewers expect biochemical/technical failure modes.")

    biotech_failure_modes = ["insolub", "inclusion bod", "off-target", "substrate inhibit", "toxicity", "immunogenicity", "degrade", "protease", "misfold", "shear", "scale-up", "separation", "oxidation", "precipitation", "aggregation", "conversion", "fermentation"]
    has_tech_failure = any(term in (weaknesses + " " + threats) for term in biotech_failure_modes)
    if has_tech_failure:
        strengths.append("Identifies authentic technical/biochemical failure modes.")
        swot_score += 2.5
    else:
        swot_score += 1.0

    swot_quads = sum(1 for q, k in [("strengths", "s"), ("weaknesses", "w"), ("opportunities", "o"), ("threats", "t")] if swot_data.get(q, "").strip() or swot_data.get(k, "").strip())
    swot_score += (swot_quads * 0.6)
    swot_score = min(5.0, swot_score)

    pestel_dims = sum(1 for d in ["political", "economic", "social", "technological", "tech", "environmental", "env", "legal"] if pestel_data.get(d, "").strip())
    pestel_score = min(5.0, pestel_dims * 0.85)

    return {
        "score": round(swot_score + pestel_score, 1),
        "swot_score": round(swot_score, 1),
        "pestel_score": round(pestel_score, 1),
        "max": 10.0,
        "issues": issues,
        "strengths": strengths,
        "feedback": f"SWOT & PESTEL scored {round(swot_score + pestel_score, 1)}/10.0."
    }

def audit_objective_method_traceability(
    aims: Dict[str, str],
    methodology: str,
    outcomes: str = "",
    research_type: str = "molecular_biotech"
) -> List[Dict[str, Any]]:
    """
    Evaluates end-to-end objective-to-methodology traceability and detects biological mismatches.
    Produces evidence-based findings conforming to the 12-field standard.
    """
    findings = []
    all_aims_text = " ".join([
        aims.get("overarching", ""),
        aims.get("aim1", ""),
        aims.get("aim2", ""),
        aims.get("aim3", "")
    ]).strip()
    
    meth_clean = methodology.strip()
    outcomes_clean = outcomes.strip()

    # Guard: Missing or empty objectives
    if not all_aims_text:
        findings.append({
            "id": "TRACE-MISSING-AIMS",
            "title": "Objectives Not Assessable: No Specific Objectives Detected",
            "severity": "Warning",
            "category": "Scientific Completeness",
            "section": "Section 3 (Specific Aims & Objectives)",
            "quote": "(No objectives detected in Section 3)",
            "evidence_source": "BT301 Rubric Criterion 3 (Specific Aims Architecture)",
            "explanation": "Specific objectives have not been drafted yet. Objective–methodology traceability cannot be verified until you formulate your specific aims.",
            "scientific_rationale": "Without explicit specific aims, the experimental methodology cannot be evaluated for alignment, controls, or decoupling.",
            "corrective_action": "Draft 2–3 specific milestones in Section 3 that state what will be tested or quantified.",
            "option_a": {
                "label": "Formulate 3 Decoupled Aims",
                "description": "Formulate Aim 1 (Preparation/Standardization), Aim 2 (Testing/Efficacy), and Aim 3 (Mechanism/Safety).",
                "action_code": "draft_aims"
            },
            "option_b": {
                "label": "Consult Socratic Aims Coach",
                "description": "Use the Socratic Aims Coach in Co-Pilot to develop decoupled milestones for your research type.",
                "action_code": "consult_aims_coach"
            },
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Missing Information",
            "example": "Aim 1: 'Standardize extraction parameters...'; Aim 2: 'Evaluate bioactivity...'",
            "status": "not_assessable"
        })
        return findings

    # 1. Anti-Inflammatory Claim vs Only Antioxidant or Antibacterial Assays
    claims_anti_inflamm = bool(re.search(r"\b(?:anti-?inflamm[a-z]*|inflammation|cytokine[a-z]*|macrophage[a-z]*|tnf|il-?6|cox-?2|erythema|dermatitis)\b", all_aims_text, re.I))
    if claims_anti_inflamm:
        has_inflamm_assay = bool(re.search(r"\b(?:elisa|tnf|il-?6|il-?1|griess|nitric\s+oxide|\bno\b|cox-?2|lox|macrophage[a-z]*|raw\s*264|thp-?1|nf-?kb|western\s+blot|rt-?qpcr|paw\s+edema|ear\s+edema)\b", meth_clean, re.I))
        has_only_antiox_or_antimicrob = bool(re.search(r"\b(?:dpph|abts|frap|orac|antibacteri[a-z]*|disk\s+diffusion|mic\b|zone\s+of\s+inhibition)\b", meth_clean, re.I))
        
        if not has_inflamm_assay:
            findings.append({
                "id": "TRACE-INFLAMM-01",
                "title": "Objective–Methodology Mismatch: Anti-Inflammatory Claim Without Inflammatory Assay",
                "severity": "Critical",
                "category": "Scientific Validity & Experimental Design",
                "section": "Section 3 (Aims) vs Section 4 (Methodology)",
                "quote": f"Aims: '{all_aims_text[:90]}...' vs Methodology: '{meth_clean[:90]}...'",
                "evidence_source": "Scientific Methodology Principles (Criterion: Assay-Objective Concordance)",
                "explanation": (
                    "Your proposal aims to evaluate anti-inflammatory activity, but Section 4 lacks an assay measuring inflammatory biomarkers. "
                    + ("Section 4 currently only describes antioxidant (e.g. DPPH/ABTS) or antibacterial assays. Free-radical scavenging and bacterial growth inhibition do NOT prove that an extract inhibits mammalian inflammatory mediators (such as TNF-α, IL-6, or PGE2)." if has_only_antiox_or_antimicrob else "No inflammatory mediator bioassay is described in the protocol.")
                ),
                "scientific_rationale": "Antioxidant capacity (free radical scavenging) and antibacterial activity operate through distinct biochemical pathways and cannot serve as surrogate proof of anti-inflammatory efficacy.",
                "corrective_action": (
                    "Select one of two scientifically sound pathways:\\n"
                    "• Option A (Strengthen Methods): Add an in vitro inflammatory bioassay to Section 4 (e.g., LPS-stimulated RAW 264.7 macrophages measuring TNF-α or IL-6 via ELISA, or Nitric Oxide via Griess assay).\\n"
                    "• Option B (Narrow Objective): Adjust the objective in Section 3 to focus on antioxidant radical-scavenging activity and phytochemical characterization, without claiming anti-inflammatory efficacy."
                ),
                "option_a": {
                    "label": "Option A (Strengthen Methods)",
                    "description": "Add an in vitro inflammatory bioassay to Section 4 (e.g., LPS-stimulated RAW 264.7 macrophages measuring TNF-α or IL-6 via ELISA, or Nitric Oxide via Griess assay).",
                    "action_code": "add_anti_inflammatory"
                },
                "option_b": {
                    "label": "Option B (Narrow Objective)",
                    "description": "Adjust the objective in Section 3 to focus on antioxidant radical-scavenging activity and phytochemical characterization, without claiming anti-inflammatory efficacy.",
                    "action_code": "narrow_to_antioxidant"
                },
                "requirement_class": "B. Scientific requirement",
                "confidence_status": "Verified Mismatch",
                "example": "Option A: 'Evaluate anti-inflammatory activity in LPS-stimulated RAW 264.7 macrophages by quantifying TNF-α and IL-6 suppression via ELISA.' | Option B: 'Evaluate in vitro antioxidant radical-scavenging capacity across DPPH and ABTS assays.'",
                "status": "pending"
            })

    # 2. Antibacterial Claim vs Missing Susceptibility Testing
    claims_antimicrobial = bool(re.search(r"\b(?:antibacteri[a-z]*|antimicrob[a-z]*|antifung[a-z]*|bactericid[a-z]*|bacteriostatic|pathogen\s+inhibition)\b", all_aims_text, re.I))
    if claims_antimicrobial:
        has_antimicrobial_assay = bool(re.search(r"\b(?:mic\b|mbc\b|microdilution|clsi|eucast|disk\s+diffusion|agar\s+well|zone\s+of\s+inhibition|cfu|time-?kill|crystal\s+violet)\b", meth_clean, re.I))
        if not has_antimicrobial_assay:
            findings.append({
                "id": "TRACE-ANTIMICROB-01",
                "title": "Objective–Methodology Mismatch: Antimicrobial Claim Without Susceptibility Assay",
                "severity": "Critical",
                "category": "Scientific Validity & Experimental Design",
                "section": "Section 3 (Aims) vs Section 4 (Methodology)",
                "quote": f"Aims: '{all_aims_text[:90]}...'",
                "evidence_source": "CLSI / EUCAST Standardized Guidelines",
                "explanation": "Specific Aims declare antimicrobial efficacy, but Section 4 does not describe standardized susceptibility testing (such as CLSI broth microdilution for MIC/MBC or disk diffusion with measured zones of inhibition).",
                "scientific_rationale": "Antimicrobial potency must be verified using standardized dilution or diffusion assays with quantitative endpoints (e.g., MIC in µg/mL).",
                "corrective_action": "Incorporate broth microdilution following CLSI M07 guidelines to quantify Minimum Inhibitory Concentration (MIC) against designated test strains alongside a reference antibiotic control.",
                "requirement_class": "B. Scientific requirement",
                "confidence_status": "Verified Mismatch",
                "example": "Determine Minimum Inhibitory Concentration (MIC) via broth microdilution in 96-well microplates following CLSI M07 standards.",
                "status": "pending"
            })

    # 3. Topical Release (Franz Cell) vs Unwarranted Transdermal Permeation / Clinical Efficacy Claims
    claims_transdermal_or_cure = bool(re.search(r"\b(?:transdermal\s+(?:permeation|delivery|absorption|transport)|stratum\s+corneum\s+penetration|deep\s+dermal\s+permeation|skin\s+penetration|systemic\s+absorption|clinical\s+skin\s+cure)\b", all_aims_text + " " + outcomes_clean, re.I))
    has_release_only = bool(re.search(r"\b(?:franz\s+(?:cell|diffusion)|synthetic\s+membrane|in\s+vitro\s+(?:drug\s+)?release|dialysis\s+(?:bag|membrane|tubing)|dissolution)\b", meth_clean, re.I))
    has_skin_permeation = bool(re.search(r"\b(?:stratum\s+corneum|skin\s+explant|human\s+skin|porcine\s+ear|franz.*skin|tape\s+stripping)\b", meth_clean, re.I))
    
    if claims_transdermal_or_cure and has_release_only and not has_skin_permeation:
        findings.append({
            "id": "TRACE-RELEASE-01",
            "title": "Methodology–Outcome Overreach: Synthetic Membrane Release vs Transdermal Permeation",
            "severity": "Major",
            "category": "Scientific Validity & Translation",
            "section": "Section 4 (Methodology) vs Section 5 (Outcomes)",
            "quote": "Methodology specifies Franz cell / synthetic membrane diffusion, but text claims transdermal stratum corneum penetration.",
            "evidence_source": "OECD 428 / Dermatological Evaluation Guidelines",
            "explanation": "In vitro drug release across a synthetic or cellulose membrane measures vehicle diffusion kinetics, but does NOT establish biological skin permeation across the lipophilic stratum corneum barrier.",
            "scientific_rationale": "Diffusion across an inert synthetic membrane reflects thermodynamic driving force and vehicle viscosity, whereas transdermal penetration depends on lipid partition coefficients and stratum corneum partitioning.",
            "corrective_action": "Either qualify the claim as 'in vitro release kinetics across synthetic membrane' or specify ex vivo skin tissue (e.g. excised porcine ear skin) mounted in Franz diffusion cells.",
            "option_a": {
                "label": "Option A (Strengthen Methods)",
                "description": "Mount dermatomed porcine skin in Franz diffusion cells with tape-stripping.",
                "action_code": "add_transdermal_permeation"
            },
            "option_b": {
                "label": "Option B (Narrow Objective)",
                "description": "Frame objective strictly as in vitro formulation release kinetics.",
                "action_code": "narrow_to_release"
            },
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Verified Overreach",
            "example": "Calibrate outcome: 'Establish in vitro active release rate (% release over 12 h) across synthetic membrane as preliminary formulation screening.'",
            "status": "pending"
        })

    # 4. Formulation Physical Stability vs Clinical Safety / Hypoallergenicity Claims
    claims_clinical_safety = bool(re.search(r"\b(?:clinical\s+safety|hypoallergenic|non-?irritating\s+to\s+patients|safe\s+for\s+human\s+skin|dermatologically\s+safe)\b", all_aims_text + " " + outcomes_clean, re.I))
    has_stability_only = bool(re.search(r"\b(?:centrifugation|freeze-?thaw|organoleptic|ph\s+stability|accelerated\s+stability|ich|viscosity)\b", meth_clean, re.I))
    has_safety_assay = bool(re.search(r"\b(?:mtt\s+assay|cytotox|keratinocyte|fibroblast|cell\s+viability|hen'?s\s+egg|het-?cam|rbc\s+hemolysis|patch\s+test)\b", meth_clean, re.I))
    
    if claims_clinical_safety and has_stability_only and not has_safety_assay:
        findings.append({
            "id": "TRACE-STABILITY-01",
            "title": "Methodology–Outcome Overreach: Physical Stability Does Not Establish Biological Safety",
            "severity": "Major",
            "category": "Scientific Validity & Translation",
            "section": "Section 4 (Methodology) vs Section 5 (Outcomes)",
            "quote": "Physical stability testing (centrifugation/pH) paired with claims of clinical cutaneous safety.",
            "evidence_source": "ISO 10993 / Cosmetic Safety Assessment Principles",
            "explanation": "Physical stability (absence of phase separation, stable pH, or centrifugation resistance) demonstrates formulation shelf-life, but does NOT prove biological non-irritancy or cellular cytocompatibility.",
            "scientific_rationale": "An emulsion or gel can remain physically homogenous while containing components that trigger cutaneous erythema or cellular toxicity.",
            "corrective_action": "Incorporate an in vitro cytocompatibility assay (e.g., MTT cell viability on HaCaT human keratinocytes or 3T3 fibroblasts) or clarify that clinical safety testing is a future translational milestone.",
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Verified Overreach",
            "example": "Couple physical stability with in vitro cytocompatibility: 'Assess formulation cytocompatibility on HaCaT keratinocytes via MTT viability assay alongside accelerated physical stability.'",
            "status": "pending"
        })

    # 5. In Vitro Bench Assay vs Direct Human Clinical Cure Overreach
    claims_clinical_cure = bool(re.search(r"\b(?:cure\s+(?:human|cancer|patients?|disease|dermatitis|clinical)|clinical\s+(?:cure|remission|efficacy|survival)|eliminate\s+(?:all\s+)?clinical\s+tumors|cure\s+in\s+humans|reduce\s+mortality\s+in\s+patients|human\s+patient\s+cure)\b", outcomes_clean, re.I))
    has_clinical_trial = bool(re.search(r"\b(?:clinical\s+trial|patient\s+cohort|randomized|placebo-?controlled|human\s+volunteers)\b", meth_clean, re.I))
    if claims_clinical_cure and not has_clinical_trial:
        findings.append({
            "id": "TRACE-CLINICAL-01",
            "title": "Methodology–Outcome Overreach: Direct Human Cure Claimed from In Vitro Assays",
            "severity": "Critical",
            "category": "Scientific Validity & Translation",
            "section": "Section 4 (Methodology) vs Section 5 (Outcomes)",
            "quote": f"Outcomes: '{outcomes_clean[:90]}...'",
            "evidence_source": "Good Academic & Grant Writing Practice",
            "explanation": "Section 5 claims clinical disease cures or patient remission, whereas Section 4 only describes in vitro laboratory bench assays.",
            "scientific_rationale": "Preclinical in vitro assays provide proof-of-concept mechanistic data but cannot establish clinical efficacy in humans due to pharmacokinetics, metabolism, and immune complexity.",
            "corrective_action": "Calibrate Section 5 expected outcomes to quantifiable in vitro benchmarks (e.g. % inhibition, IC50, or target release profile) as preclinical validation supporting future in vivo studies.",
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Verified Overreach",
            "example": "Calibrate outcome: 'Demonstrate >50% suppression of inflammatory biomarkers in vitro to establish preclinical proof-of-concept for future translational development.'",
            "status": "pending"
        })

    return findings


def audit_controls_and_statistics(
    methodology: str,
    research_type: str = "molecular_biotech"
) -> List[Dict[str, Any]]:
    """
    Evaluates experimental controls and statistical design adaptively based on research type.
    """
    findings = []
    meth_clean = methodology.strip()
    if len(meth_clean) < 30:
        return findings

    # Check for computational / review projects (do NOT penalize for wet-lab controls)
    if research_type in ["computational", "review_non_exp"]:
        if research_type == "computational":
            has_docking_control = bool(re.search(r"\b(?:redocking|rmsd|decoy|known\s+inhibitor|benchmark\s+dataset|reference\s+ligand)\b", meth_clean, re.I))
            if not has_docking_control:
                findings.append({
                    "id": "CTRL-COMP-01",
                    "title": "Computational Validation: Missing Benchmarking or Redocking Controls",
                    "severity": "Moderate",
                    "category": "Scientific Validity & Controls",
                    "section": "Section 4 (Methodology)",
                    "quote": meth_clean[:90],
                    "evidence_source": "Computational Chemistry & Docking Best Practices",
                    "explanation": "Computational modeling and docking studies require benchmark validation, such as redocking the co-crystallized ligand to verify RMSD < 2.0 Å, or screening against a decoy library to calculate ROC-AUC.",
                    "scientific_rationale": "Without redocking validation or decoy benchmarking, docking scoring functions may generate false-positive binding poses.",
                    "corrective_action": "Specify that the docking protocol will be validated by redocking native co-crystallized ligands (target RMSD < 2.0 Å) and benchmarking against known active/decoy datasets.",
                    "requirement_class": "B. Scientific requirement",
                    "confidence_status": "Verified Mismatch",
                    "example": "Validate docking workflow by redocking native co-crystallized ligands to verify pose RMSD < 2.0 Å.",
                    "status": "pending"
                })
        return findings

    # For Wet-Lab Experimental Projects:
    # 1. Unloaded Vehicle Blank (Condition D: only when formulation or solvent carrier is used)
    needs_vehicle_control = research_type in ["topical_formulation", "natural_extract", "anti_inflammatory", "cell_culture"] or bool(re.search(r"\b(?:cream|gel|dmso|ethanol|carrier|formulation|vehicle|solvent)\b", meth_clean, re.I))
    has_vehicle_control = bool(re.search(r"\b(?:vehicle\s+(?:control|blank)|negative\s+vehicle|unloaded\s+(?:cream|gel|base|emulsion)|blank\s+(?:cream|gel|emulsion|formulation|vehicle)|solvent\s+blank|0\.1%\s*dmso)\b", meth_clean, re.I))
    
    if needs_vehicle_control and not has_vehicle_control:
        findings.append({
            "id": "CTRL-VEHICLE-01",
            "title": "Experimental Controls: Missing Unloaded Vehicle Blank",
            "severity": "Major",
            "category": "Scientific Validity & Controls",
            "section": "Section 4 (Methodology)",
            "quote": meth_clean[:90],
            "evidence_source": "Standard Pharmacological & Formulation Design Principles",
            "explanation": "Your formulation or extraction protocol introduces excipients or solvent carriers (such as cream base, surfactants, or DMSO). An unloaded vehicle control (the exact matrix without the active agent) is required to rule out vehicle-induced background effects.",
            "scientific_rationale": "Emulsion excipients, preservatives, or solvents can themselves exert mild anti-inflammatory, occlusive, or cytotoxic effects; vehicle blanks ensure observed activity is exclusively attributable to the active extract.",
            "corrective_action": "Explicitly specify an unloaded vehicle control (e.g. blank cream base without extract, or solvent carrier alone) evaluated under identical experimental conditions.",
            "requirement_class": "D. Conditional recommendation",
            "confidence_status": "Conditionally Required",
            "example": "Include an unloaded vehicle control consisting of the cream base without botanical extract alongside active treatment groups.",
            "status": "pending"
        })

    # 2. Positive Reference Standard (Matched to Assay)
    has_pos_comparator = bool(re.search(r"\b(?:positive\s+control|reference\s+standard|clinical\s+comparator|indomethacin|dexamethasone|hydrocortisone|ascorbic\s+acid|trolox|ciprofloxacin|ampicillin|standard\s+drug)\b", meth_clean, re.I))
    if not has_pos_comparator:
        suggested_comparator = "an established active comparator appropriate to the assay"
        if research_type == "topical_formulation":
            suggested_comparator = "a commercial topical comparator (e.g. Hydrocortisone 1% cream or Diclofenac gel)"
        elif research_type == "anti_inflammatory":
            suggested_comparator = "an established anti-inflammatory drug (e.g. Indomethacin or Dexamethasone)"
        elif research_type == "antimicrobial":
            suggested_comparator = "a standard clinical antibiotic reference (e.g. Ciprofloxacin or Ampicillin)"
        elif research_type == "natural_extract":
            suggested_comparator = "a verified antioxidant reference (e.g. Ascorbic acid or Trolox)"

        findings.append({
            "id": "CTRL-POSITIVE-01",
            "title": "Experimental Controls: Missing Positive Reference Standard",
            "severity": "Major",
            "category": "Scientific Validity & Controls",
            "section": "Section 4 (Methodology)",
            "quote": meth_clean[:90],
            "evidence_source": "Academic Peer Review & Rubric Standards",
            "explanation": f"Section 4 lacks an active positive reference standard. Reviewers expect novel biological extracts or formulations to be benchmarked against {suggested_comparator} to calibrate comparative efficacy.",
            "scientific_rationale": "A positive control verifies assay sensitivity and provides a known efficacy benchmark against which the experimental treatment can be quantitatively evaluated.",
            "corrective_action": f"Incorporate {suggested_comparator} as a positive control arm running concurrently with test concentrations.",
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Verified Need",
            "example": f"Benchmarked against {suggested_comparator} as a positive reference standard.",
            "status": "pending"
        })

    # 3. Statistical Replication & Sample Size
    has_replication = bool(re.search(r"\b(?:independent\s+(?:batches|experiments|cultures|replicates)|biological\s+triplicates|n\s*=\s*[3-9]|three\s+independent)\b", meth_clean, re.I))
    if not has_replication:
        findings.append({
            "id": "STAT-REPLICATE-01",
            "title": "Statistical Rigor: Distinguish Biological Batches from Technical Repeats",
            "severity": "Moderate",
            "category": "Scientific Validity & Statistics",
            "section": "Section 4 (Methodology)",
            "quote": meth_clean[:90],
            "evidence_source": "Reproducibility in Science Principles",
            "explanation": "Section 4 does not clearly specify independent replication. Clarify that testing will be performed across at least n=3 independent formulation batches or biological preparations, distinct from triplicate pipetting wells.",
            "scientific_rationale": "Technical replicate wells only reflect pipetting precision within a single run, whereas independent biological/formulation batches reflect true experimental reproducibility and inter-batch variability.",
            "corrective_action": "Specify that all assays will be executed using at least n=3 independent formulation batches or cell cultures, with each batch evaluated in triplicate technical repeats.",
            "requirement_class": "C. Recommended improvement",
            "confidence_status": "Recommended",
            "example": "All measurements will be performed using n=3 independently prepared formulation batches, with each assay run in triplicate technical wells (mean ± standard deviation).",
            "status": "pending"
        })

    # 4. Statistical Analysis Plan
    has_stats_plan = bool(re.search(r"\b(?:anova|t-?test|mann-?whitney|tukey|dunnett|p\s*[<≤]\s*0\\.05|confidence\s+interval|regression|ic50\s+calculation)\b", meth_clean, re.I))
    if not has_stats_plan:
        findings.append({
            "id": "STAT-PLAN-01",
            "title": "Statistical Plan: Missing Hypothesis Testing Framework",
            "severity": "Moderate",
            "category": "Scientific Validity & Statistics",
            "section": "Section 4 (Methodology)",
            "quote": meth_clean[:90],
            "evidence_source": "Biostatistics & Experimental Design Principles",
            "explanation": "Section 4 lacks a formal statistical analysis plan specifying hypothesis testing, significance thresholds, and planned post-hoc comparisons.",
            "scientific_rationale": "Without a predefined statistical test, readers cannot evaluate whether observed differences between treatment and control arms reach statistical significance.",
            "corrective_action": "Specify the appropriate statistical test (e.g. One-way ANOVA followed by Dunnett's post-hoc test for multiple concentrations vs vehicle control, with statistical significance defined at p < 0.05).",
            "requirement_class": "B. Scientific requirement",
            "confidence_status": "Verified Need",
            "example": "Statistical significance will be determined by one-way ANOVA followed by Dunnett's multiple comparisons test against the vehicle control arm (p < 0.05 deemed significant).",
            "status": "pending"
        })

    return findings


def calculate_full_rubric_audit(proposal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates complete proposal against 11-point rubric (85 raw marks -> 10 GPA).
    Separates into 3 Decoupled Review Domains:
      Domain A: Scientific Validity (45% weight / 55% for basic science)
      Domain B: Academic Writing & Compliance (35% weight / 45% for basic science)
      Domain C: Translation & Commercialization (20% weight / 0% for basic science)
    Enforces Scientific Validity Gating: Critical biological mismatches cap Domain A at 50/100,
    preventing commercial sections from masking invalid science.
    """
    title_text = proposal_data.get("title", "")
    system_val = proposal_data.get("system") or proposal_data.get("chassis", "")
    tool_val = proposal_data.get("tool", "")
    methodology_text = proposal_data.get("methodology", "")
    
    # Research type detection or user override
    res_type = proposal_data.get("research_type") or detect_research_type(title_text, methodology_text, system_val, tool_val)
    is_basic_science = proposal_data.get("scientific_track") == "basic_science" or res_type == "review_non_exp"

    title_res = audit_title(title_text, system_val, tool_val, research_type=res_type)
    abstract_res = audit_abstract(proposal_data.get("abstract", ""))
    
    funnel_raw = proposal_data.get("funnel", {})
    if isinstance(funnel_raw, dict):
        funnel = funnel_raw
    elif isinstance(funnel_raw, str):
        funnel = {"tier1": funnel_raw, "tier2": "", "tier3": "", "tier4": ""}
    else:
        funnel = {}
    funnel_res = audit_funnel_background(
        funnel.get("tier1", ""),
        funnel.get("tier2", ""),
        funnel.get("tier3", ""),
        funnel.get("tier4", "")
    )
    method_res = audit_methodology_tense(methodology_text)
    aims_raw = proposal_data.get("aims", {})
    if isinstance(aims_raw, dict):
        aims = aims_raw
    elif isinstance(aims_raw, str):
        aims = {"aim1": aims_raw, "aim2": "", "aim3": ""}
    else:
        aims = {}
    aims_res = audit_aims_independence(
        aims.get("aim1", ""),
        aims.get("aim2", ""),
        aims.get("aim3", ""),
        research_type=res_type
    )
    swot_raw = proposal_data.get("swot", {})
    swot = swot_raw if isinstance(swot_raw, dict) else {}
    pestel_raw = proposal_data.get("pestel", {})
    pestel = pestel_raw if isinstance(pestel_raw, dict) else {}
    swot_res = audit_swot_pestel(swot, pestel)
    outcomes_text = str(proposal_data.get("expected_outcomes") or "").strip()
    impact_text = str(proposal_data.get("impact") or "").strip()
    deliverables_score = 5.0 if len(outcomes_text) > 50 else (2.5 if outcomes_text else 0.0)
    impact_score = 5.0 if len(impact_text) > 40 else (2.5 if impact_text or len(outcomes_text) > 100 else 0.0)
    outcomes_total = round(min(10.0, deliverables_score + impact_score), 1)
    competitor_raw = proposal_data.get("competitor_data", {})
    competitor_data = competitor_raw if isinstance(competitor_raw, dict) else {}
    usp_text = str(proposal_data.get("usps") or "")
    competitor_res = audit_competitor_matrix_and_usp(competitor_data, usp_text)
    usps_score = competitor_res["score"]

    gap_res = audit_gap_statement(funnel.get("tier3", ""))
    novelty_res = audit_novelty_and_soundness(
        title=title_text,
        chassis=system_val,
        tool=tool_val,
        target=proposal_data.get("target", ""),
        hypothesis=funnel.get("tier4", ""),
        methodology=methodology_text
    )

    timeline_text = proposal_data.get("time_plan", "").strip()
    timeline_score = 4.0 if len(timeline_text) > 30 else (2.0 if timeline_text else 0.0)

    budget_text = proposal_data.get("budget", "").strip()
    budget_score = 4.0 if len(budget_text) > 30 else (2.0 if budget_text else 0.0)

    refs = proposal_data.get("references", "")
    refs_count = len([r for r in re.split(r'[\r\n]+', refs.strip()) if len(r.strip()) > 15]) if refs else 0
    refs_score = min(5.0, round(refs_count * 1.0, 1))

    structure_score = 2.0 + method_res.get("tense_mark", 0.0)

    # Cross-Section Traceability & Controls Audits
    traceability_findings = audit_objective_method_traceability(aims, methodology_text, outcomes_text, res_type)
    controls_findings = audit_controls_and_statistics(methodology_text, res_type)
    
    has_critical_traceability_mismatch = any(f["severity"] == "Critical" for f in traceability_findings)

    # =========================================================================
    # DOMAIN BREAKDOWNS (3 INDEPENDENT DOMAINS)
    # =========================================================================
    # Domain A: Scientific Validity (Methods 15, Controls/Soundness 10, Gap 5) -> 30 raw -> 100%
    dom_a_raw = method_res["score"] + (outcomes_total * 0.5) + (aims_res["score"])
    dom_a_pct = round((dom_a_raw / 25.0) * 100.0)
    if has_critical_traceability_mismatch:
        dom_a_pct = min(50, dom_a_pct) # Gated at 50% max due to critical scientific contradiction

    # Domain B: Academic Writing & Compliance (Title 2, Abstract 5, Funnel 20, Tense 3, References 5) -> 35 raw -> 100%
    dom_b_raw = title_res["score"] + abstract_res["score"] + funnel_res["score"] + structure_score + refs_score
    dom_b_pct = round((dom_b_raw / 35.0) * 100.0)

    # Domain C: Translation & Commercialization (SWOT/PESTEL 10, USPs 5, Timeline 5, Budget 5) -> 25 raw -> 100%
    dom_c_raw = swot_res["score"] + usps_score + timeline_score + budget_score
    dom_c_pct = round((dom_c_raw / 25.0) * 100.0)

    # Overall GPA and Raw Total
    if is_basic_science:
        # In Basic Science Track, Domain C is not applicable
        raw_total = (
            title_res["score"] +
            abstract_res["score"] +
            funnel_res["score"] +
            method_res["score"] +
            outcomes_total +
            aims_res["score"] +
            refs_score +
            structure_score
        )
        max_possible = 60.0
        scaled_score_85 = round((raw_total / max_possible) * 85.0, 1)
        if has_critical_traceability_mismatch:
            scaled_score_85 = min(55.0, scaled_score_85)
        gpa_score = round((scaled_score_85 / 85.0) * 10.0, 1)
    else:
        raw_total = (
            title_res["score"] +
            abstract_res["score"] +
            funnel_res["score"] +
            method_res["score"] +
            outcomes_total +
            usps_score +
            swot_res["score"] +
            aims_res["score"] +
            timeline_score +
            budget_score +
            refs_score +
            structure_score
        )
        total_score_85 = min(85.0, raw_total)
        if has_critical_traceability_mismatch:
            total_score_85 = min(55.0, total_score_85)
        gpa_score = round((total_score_85 / 85.0) * 10.0, 1)

    return {
        "raw_total": raw_total,
        "max_raw": 85.0,
        "gpa_score": gpa_score,
        "max_gpa": 10.0,
        "research_type": res_type,
        "research_type_meta": RESEARCH_TYPES.get(res_type, {}),
        "scientific_validity_gated": has_critical_traceability_mismatch,
        "domains": {
            "domain_a": {
                "id": "domain_a",
                "name": "Scientific Validity & Experimental Traceability",
                "score": dom_a_pct,
                "weight_pct": 55 if is_basic_science else 45,
                "is_gated": has_critical_traceability_mismatch,
                "findings": traceability_findings + controls_findings
            },
            "domain_b": {
                "id": "domain_b",
                "name": "Academic Writing & Rubric Compliance",
                "score": dom_b_pct,
                "weight_pct": 45 if is_basic_science else 35,
                "findings": []
            },
            "domain_c": {
                "id": "domain_c",
                "name": "Translation & Feasibility",
                "score": dom_c_pct if not is_basic_science else None,
                "weight_pct": 0 if is_basic_science else 20,
                "status": "active" if not is_basic_science else "not_applicable",
                "findings": []
            }
        },
        "traceability_findings": traceability_findings,
        "controls_findings": controls_findings,
        "breakdown": {
            "title": {"score": title_res["score"], "max": 2.0, "report": title_res},
            "abstract": {"score": abstract_res["score"], "max": 5.0, "report": abstract_res},
            "background": {"score": funnel_res["score"], "max": 20.0, "report": funnel_res, "gap_audit": gap_res},
            "methodology": {"score": method_res["score"], "max": 15.0, "report": method_res},
            "aims_independence": {"score": aims_res["score"], "max": 5.0, "report": aims_res},
            "swot_pestel": {"score": swot_res["score"], "max": 10.0, "report": swot_res},
            "expected_outcomes": {"score": outcomes_total, "max": 10.0, "impact_included": bool(impact_text)},
            "competitive_advantage": {"score": usps_score, "max": 5.0, "report": competitor_res},
            "novelty_soundness": {"score": novelty_res["soundness_score"], "max": 100.0, "report": novelty_res},
            "time_plan": {"score": timeline_score, "max": 5.0},
            "budget": {"score": budget_score, "max": 5.0},
            "references": {"score": refs_score, "max": 5.0},
            "structure": {"score": structure_score, "max": 3.0}
        }
    }


def audit_all_writing_sections(proposal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive Writing Audit covering all drafted sections of the proposal.
    """
    sections = []

    title = proposal_data.get("title", "")
    chassis = proposal_data.get("chassis") or proposal_data.get("system", "")
    tool = proposal_data.get("tool", "")
    target = proposal_data.get("target", "")
    res_type = proposal_data.get("research_type") or detect_research_type(title, proposal_data.get("methodology", ""), chassis, tool)
    
    t_rep = audit_title(title, system=chassis, tool=tool, target=target, research_type=res_type)
    t_status = "pass" if t_rep["passed"] else ("warning" if title.strip() else "incomplete")
    sections.append({
        "id": "sec_title",
        "name": "1. Proposal Title & Research Anchors",
        "status": t_status,
        "badge": "✓ Robust" if t_status == "pass" else ("⚠️ Needs Refinement" if t_status == "warning" else "❌ Incomplete"),
        "excerpt": title if title.strip() else "No title provided yet.",
        "strengths": t_rep.get("strengths", []),
        "issues": t_rep.get("issues", []),
        "recommendations": t_rep.get("recommendations", []),
        "action_recommendation": "Name the active agent/intervention, model chassis, and application."
    })

    abstract = proposal_data.get("abstract", "")
    a_rep = audit_abstract(abstract)
    a_status = "pass" if a_rep["score"] >= 3.5 else ("warning" if abstract.strip() else "incomplete")
    sections.append({
        "id": "sec_abstract",
        "name": "2. Abstract / Executive Summary",
        "status": a_status,
        "badge": "✓ Robust" if a_status == "pass" else ("⚠️ Needs Refinement" if a_status == "warning" else "❌ Incomplete"),
        "excerpt": abstract[:140] + "..." if len(abstract) > 140 else (abstract if abstract.strip() else "Abstract not entered yet."),
        "strengths": a_rep.get("strengths", []),
        "issues": a_rep.get("issues", []),
        "action_recommendation": "Ensure proportional coverage of Problem (2%), Methodology (2%), and Quantitative Milestone (1%) within 250 words."
    })

    funnel = proposal_data.get("funnel", {})
    t1 = funnel.get("tier1", "")
    t2 = funnel.get("tier2", "")
    t3 = funnel.get("tier3", "")
    t4 = funnel.get("tier4", "")
    f_rep = audit_funnel_background(t1, t2, t3, t4)
    gap_rep = audit_gap_statement(t3)
    f_status = "pass" if f_rep["score"] >= 14.0 and not gap_rep.get("is_strawman") else ("warning" if any([t1, t2, t3, t4]) else "incomplete")
    all_f_strengths = []
    all_f_issues = []
    for tr in f_rep.get("tiers", []):
        all_f_strengths.extend(tr.get("strengths", []))
        all_f_issues.extend(tr.get("issues", []))
    if gap_rep.get("is_strawman"):
        all_f_issues.append("STRAWMAN GAP DETECTED: Avoid claiming 'no research exists'. Frame the gap as a documented biophysical, performance, or delivery bottleneck.")
    sections.append({
        "id": "sec_funnel",
        "name": "3. Background Inverted Funnel (Tiers 1–4)",
        "status": f_status,
        "badge": "✓ Robust" if f_status == "pass" else ("⚠️ Needs Refinement" if f_status == "warning" else "❌ Incomplete"),
        "excerpt": f"Tier 1: {t1[:70]}... | Tier 3 Gap: {t3[:70]}..." if (t1 or t3) else "Funnel tiers not drafted yet.",
        "strengths": all_f_strengths[:4],
        "issues": all_f_issues,
        "action_recommendation": "Ensure Tier 1 includes quantified burden statistics, Tier 2 documents baseline rates, Tier 3 identifies the biophysical mechanism of failure, and Tier 4 establishes your testable hypothesis."
    })

    aims_data = proposal_data.get("aims", {})
    aim_main = aims_data.get("overarching", "")
    aim1 = aims_data.get("aim1", "")
    aim2 = aims_data.get("aim2", "")
    aim3 = aims_data.get("aim3", "")
    aims_rep = audit_aims_independence(aim1, aim2, aim3, research_type=res_type)
    aims_status = "pass" if aims_rep["score"] >= 4.0 else ("warning" if (aim1 or aim2 or aim3) else "incomplete")
    sections.append({
        "id": "sec_aims",
        "name": "4. Central Aim & 3 Specific Objectives",
        "status": aims_status,
        "badge": "✓ Robust" if aims_status == "pass" else ("⚠️ Needs Refinement" if aims_status == "warning" else "❌ Incomplete"),
        "excerpt": f"Aim 1: {aim1[:60]}... | Aim 2: {aim2[:60]}..." if (aim1 or aim2) else "Specific Aims not entered yet.",
        "strengths": aims_rep.get("strengths", []),
        "issues": aims_rep.get("issues", []),
        "action_recommendation": "Ensure Aim 1 (Synthesis/Isolation), Aim 2 (Quantitative Milestone or Exploratory Profiling), and Aim 3 (Matrix/Safety Validation) can proceed independently."
    })

    meth_text = proposal_data.get("methodology", "")
    m_rep = audit_methodology_tense(meth_text)
    m_status = "pass" if m_rep["score"] >= 10.0 else ("warning" if meth_text.strip() else "incomplete")
    sections.append({
        "id": "sec_methodology",
        "name": "5. Experimental Methodology & Controls",
        "status": m_status,
        "badge": "✓ Robust" if m_status == "pass" else ("⚠️ Needs Refinement" if m_status == "warning" else "❌ Incomplete"),
        "excerpt": meth_text[:160] + "..." if len(meth_text) > 160 else (meth_text if meth_text.strip() else "Methodology not entered yet."),
        "strengths": m_rep.get("strengths", []),
        "issues": m_rep.get("issues", []),
        "action_recommendation": "Format into sequential experimental phases, explicitly state negative and positive controls, and use future tense auxiliary verbs ('will be evaluated')."
    })

    outcomes_text = proposal_data.get("expected_outcomes", "")
    if not outcomes_text and "impact_data" in proposal_data:
        impact = proposal_data["impact_data"]
        if isinstance(impact, dict):
            outcomes_text = " ".join([str(v) for v in impact.values() if v])
        elif isinstance(impact, str):
            outcomes_text = impact
    o_status = "pass" if len(outcomes_text.split()) >= 20 else ("warning" if outcomes_text.strip() else "incomplete")
    sections.append({
        "id": "sec_outcomes",
        "name": "6. Expected Outcomes & Long-Term Impact",
        "status": o_status,
        "badge": "✓ Robust" if o_status == "pass" else ("⚠️ Needs Refinement" if o_status == "warning" else "❌ Incomplete"),
        "excerpt": outcomes_text[:160] + "..." if len(outcomes_text) > 160 else (outcomes_text if outcomes_text.strip() else "Expected outcomes not entered yet."),
        "strengths": ["Clear deliverables and impact defined."] if o_status == "pass" else [],
        "issues": ["Expand on deliverables and long-term academic, economic, or clinical impact."] if o_status != "pass" else [],
        "action_recommendation": "Detail tangible analytical deliverables for each aim and delineate long-term translational impact."
    })

    # 7. Competitor Analysis & Unique Selling Proposition (USP)
    competitor_data = proposal_data.get("competitor_data", {})
    usp_text = proposal_data.get("usps", "") or (competitor_data.get("usp", "") if isinstance(competitor_data, dict) else "")
    comp_rep = audit_competitor_matrix_and_usp(competitor_data, usp_text)
    comp_status = "pass" if comp_rep["score"] >= 3.5 else ("warning" if (competitor_data or usp_text) else "incomplete")
    sections.append({
        "id": "sec_competitor",
        "name": "7. Competitor Analysis & Unique Selling Proposition (USP)",
        "status": comp_status,
        "badge": "✓ Robust" if comp_status == "pass" else ("⚠️ Needs Refinement" if comp_status == "warning" else "❌ Incomplete"),
        "excerpt": usp_text[:120] if usp_text else "Competitor and USP analysis not drafted yet.",
        "strengths": comp_rep.get("strengths", []),
        "issues": comp_rep.get("issues", []),
        "action_recommendation": "Name a real competing technology (avoid 'traditional methods' strawman) and formulate a clear USP sentence."
    })

    # 8. Strategic Analysis (SWOT & PESTEL)
    swot_data = proposal_data.get("swot", {})
    pestel_data = proposal_data.get("pestel", {})
    sp_rep = audit_swot_pestel(swot_data, pestel_data)
    is_basic_track = proposal_data.get("scientific_track") == "basic_science" or res_type == "review_non_exp"
    has_full_swot = ((swot_data.get("s") and swot_data.get("w") and swot_data.get("o") and swot_data.get("t")) or 
                     (swot_data.get("strengths") and swot_data.get("weaknesses") and swot_data.get("opportunities") and swot_data.get("threats")))
    sp_status = "pass" if (is_basic_track or sp_rep["score"] >= 7.0 or (has_full_swot and sp_rep["swot_score"] >= 4.0)) else ("warning" if any(swot_data.values()) else "incomplete")
    sections.append({
        "id": "sec_swot_pestel",
        "name": "8. Strategic Analysis (SWOT & PESTEL)",
        "status": "pass" if is_basic_track else sp_status,
        "badge": "✓ N/A - Basic Science Track" if is_basic_track else ("✓ Robust" if sp_status == "pass" else ("⚠️ Needs Refinement" if sp_status == "warning" else "❌ Incomplete")),
        "excerpt": "Optional for basic science track." if is_basic_track else f"SWOT: {sp_rep['swot_score']}/5.0 | PESTEL: {sp_rep['pestel_score']}/5.0",
        "strengths": sp_rep.get("strengths", []),
        "issues": [] if is_basic_track else sp_rep.get("issues", []),
        "action_recommendation": "Identify technical failure modes (e.g. enzyme insolubility, aggregation, or phase instability) rather than student clichés."
    })

    # 9. Peer-Reviewed References Cited (APA 7th)
    refs_text = proposal_data.get("references", "")
    refs_count = len([r for r in re.split(r'[\r\n]+', refs_text.strip()) if len(r.strip()) > 15])
    r_status = "pass" if refs_count >= 3 else ("warning" if refs_count > 0 else "incomplete")
    sections.append({
        "id": "sec_references",
        "name": "9. Peer-Reviewed References Cited (APA 7th)",
        "status": r_status,
        "badge": "✓ Robust" if r_status == "pass" else ("⚠️ Needs Refinement" if r_status == "warning" else "❌ Incomplete"),
        "excerpt": f"{refs_count} references cited." if refs_count > 0 else "No references cited yet.",
        "strengths": [f"Contains {refs_count} references formatted in APA 7th."] if r_status == "pass" else [],
        "issues": ["Provide at least 3 peer-reviewed citations with active DOIs."] if r_status != "pass" else [],
        "action_recommendation": "Cite current peer-reviewed literature (>=60% from 2021–2026) in APA 7th Edition format."
    })

    passed_count = sum(1 for s in sections if s["status"] == "pass")
    warning_count = sum(1 for s in sections if s["status"] == "warning")
    incomplete_count = sum(1 for s in sections if s["status"] == "incomplete")
    
    if passed_count >= 7 and incomplete_count == 0:
        overall_status = "Ready for Submission"
    elif passed_count >= 5:
        overall_status = "Needs Minor Revisions"
    else:
        overall_status = "Incomplete Draft"

    summary = {
        "total_sections": len(sections),
        "passed_sections": passed_count,
        "warning_sections": warning_count,
        "incomplete_sections": incomplete_count,
        "overall_status": overall_status
    }

    full_audit = calculate_full_rubric_audit(proposal_data)
    return {
        "summary": summary,
        "sections": sections,
        "research_type": res_type,
        "research_type_meta": RESEARCH_TYPES.get(res_type, {}),
        "domains": full_audit["domains"],
        "traceability_findings": full_audit["traceability_findings"],
        "controls_findings": full_audit["controls_findings"],
        "raw_total": full_audit["raw_total"],
        "gpa_score": full_audit["gpa_score"]
    }
