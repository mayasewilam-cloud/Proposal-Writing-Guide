"""
Socratic Coaching & Academic Mentor Engine for BT_301.
Enforces the "Scaffold, Don't Solve" pedagogical policy:
- Functions strictly as an academic mentor and reviewer — NEVER a ghostwriter or proposal generator.
- Refuses to write or rewrite student proposal sections, paragraphs, abstracts, aims, or methods.
- Diagnoses weaknesses, vague assertions, and missing biochemical mechanisms in student-authored text.
- Delivers structured 6-part academic mentoring feedback:
  1. What is working (strengths in student draft)
  2. What needs attention (issues, ambiguous claims, missing elements)
  3. Why it matters scientifically (consequences for validity, reviewers, and viva)
  4. Guiding Socratic questions (focused questions to prompt student thinking)
  5. Revision criteria (standards the revised version must demonstrate)
  6. Self-check checklist (student self-verification before submission)
- Adapts Viva Voce defense cross-examinations dynamically to the student's research type.
"""

import re
from typing import Dict, List, Any


GHOSTWRITING_PATTERNS = [
    r"\b(write|draft)\s+(me\s+)?(a\s+|an\s+|my\s+)?(complete\s+)?(proposal|introduction|background|abstract|methodology|methods|aims?|objectives?|hypothesis|hypotheses|literature\s+review|results?|discussion|conclusion|paper)\b",
    r"\bgenerate\s+(a\s+|an\s+|my\s+)?(complete\s+)?(proposal|introduction|background|abstract|methodology|methods|aims?|objectives?|hypothesis|hypotheses|paper|section)\b",
    r"\bgive\s+me\s+(a\s+|an\s+|my\s+)?(title|aims?|objectives?|hypothesis|introduction|methodology|proposal|paragraph|section|ready(-|\s+)to(-|\s+)submit)\b",
    r"\bfix\s+my\s+(methodology|introduction|aims?|objectives?|hypothesis|proposal|draft|methods)\s*(for\s+me)?\b",
    r"\brewrite\s+(this|my)\s+(section|draft|introduction|methodology|proposal|abstract|text|paragraph|methods)\b",
    r"\b(do\s+this|write\s+this|finish\s+this)\s+for\s+me\b",
    r"\bauto(-|\s+)assemble\s+(my\s+|the\s+)?(proposal|blueprint|complete\s+proposal)\b",
    r"\bmake\s+(me\s+)?a\s+(proposal|draft|title|aim)\b"
]


def detect_ghostwriting_intent(text: str) -> bool:
    """Checks whether the user is prompting the system to write proposal content on their behalf."""
    clean = text.strip().lower()
    for pattern in GHOSTWRITING_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return True
    return False


def get_mentoring_refusal_response(section_name: str, text: str) -> Dict[str, Any]:
    """Generates an educational, supportive refusal explaining why the AI mentors rather than ghostwrites."""
    sec_lower = section_name.lower()
    
    if "title" in sec_lower or "cover" in sec_lower or "pillar" in sec_lower or "sec0" in sec_lower or "section 0" in sec_lower or "section-0" in sec_lower:
        specific_task = "formulate your Project Title & 3 Strategic Pillars (Criterion 1)"
        criteria = [
            "Use the 4-part Publication Title Formula: [Active Tool / Extract] in [Delivery Matrix / Formulation] tested in [Experimental Biological Chassis] to [Target Benchmark] for [Real-World Problem].",
            "Distinguish delivery matrix (e.g. 'Cream' / 'Gel') from true biological testing chassis (e.g. RAW 264.7 macrophages, HaCaT keratinocytes, or BALB/c mice).",
            "Lead with an active engineering or formulation mechanism rather than descriptive school-lab phrases ('Study of').",
            "Include a measurable quantitative benchmark or comparator (e.g. 'benchmarked against Hydrocortisone 1% cream' or '>80% wound closure')."
        ]
        questions = [
            "What is your active substance and what formulation matrix (cream, gel, hydrogel) carries it?",
            "What exact experimental biological chassis will you test it in (in vitro cell line e.g. RAW 264.7, ex vivo tissue e.g. porcine skin, or in vivo animal model e.g. BALB/c mice)?",
            "What clinical reference drug or target quantitative milestone will you benchmark against?"
        ]
        checklist = [
            "Does my title clearly state my experimental biological chassis (cell line, animal species, or tissue model)?",
            "Does it name the formulation vehicle and target condition?",
            "Does it avoid passive phrasing like 'A study of'?"
        ]
    elif "intro" in sec_lower or "background" in sec_lower or "problem" in sec_lower or "sec2" in sec_lower or "section 2" in sec_lower or "section-2" in sec_lower:
        specific_task = "draft your Introduction & 4-Tier Funnel Narrative (Section 2.1)"
        criteria = [
            "Use the 4-tier inverted funnel architecture (Tier 1: Global Epidemiological Burden -> Tier 2: Current Clinical/Standard Methods -> Tier 3: Critical Knowledge Gap -> Tier 4: Proposed Intervention & Biological Chassis Rationale).",
            "State quantified real-world burden figures (e.g. >230M patients worldwide, economic loss in EGP/USD).",
            "Benchmark against an established clinical standard of care (e.g. Hydrocortisone 1% cream) and detail its clinical adverse effects (epidermal barrier thinning, skin atrophy, tachyphylaxis).",
            "Justify why your biological chassis was selected (e.g. why RAW 264.7 macrophages, HaCaT keratinocytes, or porcine ear skin).",
            "Avoid conversational phrasing (e.g. 'bad for the skin') and 'not enough studies' strawman fallacies."
        ]
        questions = [
            "What specific physiological or epidemiological burden (>230M patients, annual cost) does your target problem represent?",
            "What conventional gold standard is currently used (e.g. Hydrocortisone 1%), and what is its primary technical or clinical limitation (e.g. epidermal atrophy)?",
            "Why is your chosen biological testing model (RAW 264.7 macrophages, porcine skin) the most physiologically relevant chassis?"
        ]
        checklist = [
            "Did I start with the broad quantified real-world burden before narrowing to my specific tool?",
            "Did I name a clinical or reference standard comparator and its adverse effects?",
            "Did I identify a concrete biophysical or chemical bottleneck rather than just 'more studies are needed'?",
            "Did I scientifically justify my choice of experimental biological chassis?"
        ]
    elif "aim" in sec_lower or "objective" in sec_lower or "sec3" in sec_lower or "section 3" in sec_lower or "section-3" in sec_lower:
        specific_task = "formulate your Specific Aims & Objectives (Section 3)"
        criteria = [
            "Lead every aim with a measurable active scientific verb (e.g. Formulate, Quantify, Standardize, Validate, Optimize).",
            "Avoid passive or school-lab verbs like 'Study', 'Investigate', or 'Look into'.",
            "Structure into 3 decoupled milestones: Aim 1 (Extraction & HPLC marker standardization), Aim 2 (Formulation & ex vivo Franz cell permeation kinetics), Aim 3 (In vitro cytokine suppression & cytocompatibility vs Hydrocortisone 1%).",
            "Decouple downstream testing so Aim 2 and Aim 3 can proceed using parallel standards if Aim 1 encounters yield delays (pass the Domino Collapse check)."
        ]
        questions = [
            "What is the first physical material or construct you need to standardize (e.g. HPLC-DAD quantification of active marker compounds)?",
            "What biophysical formulation milestone (e.g. Franz cell permeation flux J_ss across porcine skin) will Aim 2 establish?",
            "What quantitative bioactivity endpoint (e.g. % suppression of TNF-alpha/IL-6 in RAW 264.7 macrophages, Selectivity Index >= 3.0) will Aim 3 benchmark against positive controls?"
        ]
        checklist = [
            "Does each objective begin with an active scientific verb?",
            "Is Aim 2 protected from total failure if Aim 1 encounters extraction or yield delays?",
            "Is every aim linked to a specific quantitative assay and benchmark comparator?"
        ]
    elif "method" in sec_lower or "sec4" in sec_lower or "section 4" in sec_lower or "section-4" in sec_lower:
        specific_task = "design your Experimental Methodology & Protocol Design (Section 4)"
        criteria = [
            "Structure into sequential laboratory phases (Phase 1: Standardization -> Phase 2: Formulation & Stability -> Phase 3: Ex Vivo Release -> Phase 4: Inflammatory Bioassay & Cytotoxicity -> Phase 5: Statistics).",
            "Declare paired controls: Untreated cells (baseline), positive disease stimulus (LPS), unloaded vehicle control (blank cream base), and active clinical comparator (Hydrocortisone 1% cream).",
            "Specify cell culture conditions (e.g. DMEM + 10% heat-inactivated FBS, 37°C, 5% CO2, passage range P5–P15) and analytical parameters (HPLC column, UV wavelengths, Franz cell receptor buffer PBS pH 7.4).",
            "Specify biological triplicates (n = 3 independent batches/cultures) distinct from triplicate technical repeat wells.",
            "Define a formal statistical hypothesis test (One-way ANOVA followed by Dunnett's or Tukey's post-hoc test, p < 0.05)."
        ]
        questions = [
            "What unloaded vehicle control will confirm that excipients/solvents do not cause false-positive effects?",
            "What positive clinical reference standard (e.g. Hydrocortisone 1% cream) will you test in parallel to benchmark performance?",
            "How do you distinguish true anti-inflammatory efficacy from cytotoxicity (e.g. MTT viability assay, Selectivity Index >= 3.0)?",
            "What specific ANOVA statistical test and post-hoc comparison will determine statistical significance?"
        ]
        checklist = [
            "Are methods written in formal prospective future tense ('will be incubated', 'will be measured')?",
            "Are exact concentrations, temperatures, and equipment parameters specified?",
            "Are biological replicates (n >= 3) and statistical tests declared?",
            "Does the protocol include an unloaded vehicle blank and clinical reference drug?"
        ]
    elif "risk" in sec_lower or "outcome" in sec_lower or "plan b" in sec_lower or "contingency" in sec_lower or "sec5" in sec_lower or "section 5" in sec_lower or "section-5" in sec_lower:
        specific_task = "develop your Expected Outcomes & Contingency Plan (Plan B) (Section 5)"
        criteria = [
            "Define quantifiable milestone deliverables (e.g. extraction yield > 5%, permeation flux J_ss > 10 µg/cm²/h, >50% cytokine inhibition).",
            "Establish quantitative go/no-go decision gates for each experimental phase.",
            "Provide proactive technical rescue protocols (e.g. if emulsion phase-separates, adjust HLB surfactant ratio or add 0.5% Carbomer 940; if cytotoxicity occurs, perform Sephadex column fractionation)."
        ]
        questions = [
            "What specific quantitative number defines successful execution of each aim?",
            "What is your immediate technical Plan B if the botanical extract exhibits poor skin permeation across stratum corneum?",
            "What go/no-go gate will trigger switching from the primary vehicle to an alternative nanocarrier?"
        ]
        checklist = [
            "Did I specify quantifiable performance thresholds for each deliverable?",
            "Did I establish concrete technical contingency alternatives for potential failure modes?"
        ]
    elif ("abstract" in sec_lower or bool(re.search(r"\b(sec0?1|section[\s-]0?1)\b", sec_lower))) and "10" not in sec_lower:
        specific_task = "draft your Executive Abstract (Section 1)"
        criteria = [
            "Adhere strictly to the 150–250 word limit.",
            "Summarize the problem burden (>230M patients), current clinical standard (Hydrocortisone 1%) and its limits, proposed active intervention & formulation, explicit biological testing chassis (RAW 264.7 macrophages / porcine skin), and target quantitative milestone (>50% suppression, SI >= 3.0).",
            "Ensure structured academic flow without colloquial expressions."
        ]
        questions = [
            "What is the core quantitative problem metric you are addressing?",
            "What specific bioengineering tool or formulation is your intervention?",
            "What explicit biological testing chassis and positive comparator standard are named?"
        ]
        checklist = [
            "Is the word count strictly between 150 and 250 words?",
            "Does it state the biological mechanism, experimental testing chassis, and benchmark target?"
        ]
    elif "budget" in sec_lower or "timeline" in sec_lower or "sec9" in sec_lower or "section 9" in sec_lower or "section-9" in sec_lower:
        specific_task = "develop your Timeline & Itemized Budget in EGP (Section 9)"
        criteria = [
            "Itemize research costs in Egyptian Pounds (EGP) across Categories A through F with supplier quotes.",
            "Provide scientific justifications linking every line item to a specific experimental aim.",
            "Include a 10% contingency buffer for reagent price inflation.",
            "Map experimental phases into a quarterly Gantt chart schedule across 12 months."
        ]
        questions = [
            "Which major consumables (ELISA kits, HPLC columns, cell lines, Franz cells) drive your direct costs in EGP?",
            "How does your 12-month timeline sequence extraction, formulation, ex vivo permeation, and in vitro cell testing?"
        ]
        checklist = [
            "Are all costs itemized in Egyptian Pounds (EGP)?",
            "Is every expense justified by an experimental milestone?",
            "Does the Gantt chart show realistic sequencing of work packages?"
        ]
    else:
        specific_task = f"develop your {section_name} draft"
        criteria = [
            "Ground your proposal in verifiable empirical literature.",
            "State clear, falsifiable hypotheses and testable milestones.",
            "Maintain an objective academic register."
        ]
        questions = [
            "What is the central scientific hypothesis or engineering goal of this section?",
            "What evidence or data will convince a faculty reviewer that this approach is sound?"
        ]
        checklist = [
            "Is the writing clear, concise, and academically rigorous?",
            "Are assertions supported by literature or empirical rationale?"
        ]

    msg = (
        f"⚠️ Pedagogical Firewall Triggered — Academic Integrity & Mentoring Policy: As your academic research mentor, "
        f"I do not write proposal text, aims, or methodology for you. Submitting AI-generated prose "
        f"violates academic integrity standards, deprives you of intellectual ownership, and leaves you "
        f"vulnerable during your faculty viva defense.\n\n"
        f"Instead, I am here to coach you through how to {specific_task} yourself!"
    )

    return {
        "status": "refusal",
        "is_ghostwriting_request": True,
        "role": "academic_mentor",
        "word_count": len(text.split()),
        "message": msg,
        "what_is_working": [
            f"You have identified the need to work on {section_name}."
        ],
        "needs_attention": [
            "The request asks the AI to produce proposal text. All proposal content must be authored by the student investigator."
        ],
        "why_it_matters": [
            "Grant committees and university faculty evaluate your personal scientific reasoning, experimental design skills, and ability to defend your methodology in oral viva voce examinations."
        ],
        "guiding_questions": questions,
        "revision_criteria": criteria,
        "self_check": checklist,
        "praise": [f"Focusing on {section_name} is an important next step in your proposal workflow."],
        "critiques": ["AI ghostwriting is strictly prevented to safeguard your academic integrity."],
        "socratic_questions": questions,
        "action_item": (
            f"Draft your own initial ideas in {section_name} using the revision criteria and guiding questions above. "
            "Then submit your draft, and I will provide detailed Socratic feedback on your reasoning!"
        )
    }


def analyze_student_draft(section_name: str, draft_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Evaluates a student-authored draft section with Socratic critique without rewriting or replacing the text.
    Provides a structured 6-part academic mentoring review:
    1. What is working
    2. What needs attention
    3. Why it matters scientifically
    4. Guiding Socratic questions
    5. Revision criteria
    6. Self-check checklist
    """
    text = draft_text.strip()
    if not text:
        return {
            "status": "empty",
            "is_ghostwriting_request": False,
            "role": "academic_mentor",
            "word_count": 0,
            "message": f"Enter your draft for {section_name}. I will review your logic, scientific rigor, and methodology without writing it for you.",
            "what_is_working": [],
            "needs_attention": [f"Section {section_name} is currently empty."],
            "why_it_matters": ["Complete sections are required for faculty evaluation and rubric scoring."],
            "guiding_questions": [f"What is the primary scientific message or deliverable of {section_name}?"],
            "revision_criteria": [f"Draft an initial narrative for {section_name} grounded in your research pillars."],
            "self_check": ["Draft initial content before requesting peer or mentor review."],
            "praise": [],
            "critiques": ["Section currently empty."],
            "socratic_questions": [f"What is your starting concept for {section_name}?"],
            "action_item": "Enter an initial draft to receive Socratic mentoring feedback."
        }

    # Anti-cheating & anti-ghostwriting guard
    if detect_ghostwriting_intent(text):
        return get_mentoring_refusal_response(section_name, text)

    words = text.split()
    word_count = len(words)
    what_is_working = []
    needs_attention = []
    why_it_matters = []
    guiding_questions = []
    revision_criteria = []
    self_check = []

    # 1. Check for vague or informal vocabulary
    vague_terms = {
        "very good": ("Quantitative precision", "State the exact kinetic rate, percent yield, or statistical significance rather than 'very good'."),
        "many studies": ("Literature specificity", "Name specific landmark authors and publication years rather than saying 'many studies'."),
        "huge problem": ("Epidemiological framing", "Quantify the real-world burden (e.g. annual patient population, economic loss in EGP/USD)."),
        "miraculous": ("Objective scientific register", "Maintain a restrained academic tone; express efficacy through empirical measurements."),
        "cheaper and faster": ("Comparative benchmarking", "State the baseline cost/time vs. your projected cost/time in quantified units."),
        "various enzymes": ("Molecular specificity", "Specify exact enzyme classes, EC numbers, or bacterial strains."),
        "improve health": ("Physiological readout", "Identify the exact biomarker or clinical endpoint being measured."),
        "make a cream": ("Biomedical terminology", "Use formal formulation terms (e.g. 'formulate an oil-in-water topical emulsion')."),
        "bad for the skin": ("Pathological terminology", "Use clinical terms (e.g. 'cutaneous barrier disruption', 'epidermal inflammation')."),
        "more studies are needed": ("Literature gap fallacy", "Reviewers know thousands of papers exist; identify the specific unaddressed bottleneck (e.g. lack of marker standardization or transdermal permeation kinetics)."),
        "not enough studies": ("Literature gap fallacy", "Avoid the 'not enough studies' trap; state the exact biochemical or formulation challenge."),
        "see if it works": ("Scientific objective", "Frame as a hypothesis test: 'determine whether [intervention] significantly suppresses [biomarker]'.")
    }

    found_vague = False
    for term, (aspect, explanation) in vague_terms.items():
        if term in text.lower():
            needs_attention.append(f"Informal or vague phrasing: '{term}'. {explanation}")
            why_it_matters.append("Academic grant committees reject conversational wording because it diminishes scientific credibility and suggests an informal school-lab mindset.")
            guiding_questions.append(f"How can you rephrase '{term}' using formal biomedical terminology and quantified metrics?")
            found_vague = True
            break # Flag top one to avoid overwhelming beginner

    # 2. Check for passive vs. active or conversational generalizations
    if "everyone knows that" in text.lower() or "it is obvious that" in text.lower():
        needs_attention.append("Conversational assumption detected ('everyone knows' / 'it is obvious').")
        why_it_matters.append("In academic proposals, every assertion must be supported by empirical literature citations rather than personal intuition.")
        guiding_questions.append("What peer-reviewed paper provides empirical evidence for this claim?")

    # 3. Citation density check (for prose narrative sections)
    citations = re.findall(r"\[[0-9,\s-]+\]|\([A-Za-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", text)
    sec_lower = section_name.lower()
    is_prose_section = any(k in sec_lower for k in ["intro", "background", "problem", "review", "abstract", "literature"])

    if is_prose_section:
        if word_count > 60 and len(citations) == 0:
            needs_attention.append("No in-text literature citations detected in this narrative.")
            why_it_matters.append("Unreferenced factual claims are treated as unsupported assertions by peer review panels.")
            guiding_questions.append("Which published studies substantiate your baseline data or epidemiological figures?")
            revision_criteria.append("Anchor core claims with peer-reviewed literature citations [Author, Year] or numerical brackets [1].")
            self_check.append("Did I cite at least 1–2 peer-reviewed sources for my background claims?")
        elif len(citations) >= 1:
            what_is_working.append(f"Literature grounding: {len(citations)} citation(s) recognized in text.")
            
        # APA 7th in-text syntax diagnostics (Chapter 5 §5.2.2)
        if re.search(r'\([A-Za-z]+(?:\s+and\s+[A-Za-z]+)+\s*,\s*\d{4}\)', text):
            needs_attention.append("APA 7th In-Text Syntax: Use an ampersand (&) inside parenthetical citations: (Rahman & Lopez, 2023), not the word 'and'. Reserve 'and' for narrative prose outside parentheses (Rahman and Lopez, 2023).")
            why_it_matters.append("Under APA 7th Edition (§5.2.2), ampersands (&) are strictly required inside parentheses, while written 'and' is reserved for running narrative.")
        
        if re.search(r'\bet\.\s+al\b', text, re.I):
            needs_attention.append("Latin abbreviation syntax: Write 'et al.' (no period after 'et'). 'Et' is a full Latin word meaning 'and'; 'al.' is an abbreviation for alia/alii and requires a trailing period.")
            why_it_matters.append("Scientific reviewers expect exact bibliographic conventions; 'et. al.' is flagged as a proofreading error.")
        
        if re.search(r'\([A-Za-z]+,\s*[A-Za-z]+,\s*(?:and\s*)?[A-Za-z]+,\s*\d{4}\)', text):
            needs_attention.append("3+ Authors In-Text Rule: In APA 7th Edition (§5.2.2), any source with 3 or more authors is shortened to 'FirstAuthor et al., Year' from the very first citation (e.g., Chen et al., 2021). Do not list all three names in text.")

    # 4. SECTION-SPECIFIC RIGOR DIAGNOSTICS

    # --- Section 0 / 1: Title & Strategic Pillars ---
    if "title" in sec_lower or "cover" in sec_lower or "pillar" in sec_lower or "sec0" in sec_lower:
        if word_count < 6:
            needs_attention.append(f"Title is too brief ({word_count} words). Academic grant titles require 8–24 words to specify active intervention, delivery matrix, biological chassis, and target benchmark.")
            why_it_matters.append("Under BT_301 Rubric Criterion 1, grant reviewers evaluate whether your title defines the complete scientific scope of the investigation.")
            guiding_questions.append("How can you expand your title using the 4-part formula: [Active Substance] in [Delivery Matrix] tested in [Experimental Biological Chassis] to [Target Benchmark] for [Application]?")
        elif word_count > 30:
            needs_attention.append(f"Title is overly lengthy ({word_count} words). Aim for 12–25 words to maintain academic punchiness.")

        # Check for descriptive phrasing ("Study of", "The effect of")
        descriptive_m = re.search(r"^(the\s+)?(effect|role|impact|study|investigation|evaluation|analysis|overview)\s+(of|on|into)\b", text, re.IGNORECASE)
        if descriptive_m:
            needs_attention.append(f"Descriptive lead detected: '{descriptive_m.group(0)}'. While it identifies your topic, peer-reviewed research papers lead directly with active formulation and experimental scope (e.g. 'Formulation and In Vitro Anti-Inflammatory Evaluation of...').")
            why_it_matters.append("Grant panels favor titles framed as active bioengineering interventions over passive school-lab observations.")
            guiding_questions.append(f"How would you reframe the title starting directly with the active formulation or evaluation (e.g. 'Formulation and In Vitro Evaluation of...')?")

        # Check for Research Subject / Active Intervention
        has_subject = any(t in text.lower() for t in [
            "extract", "cream", "gel", "formulation", "calendula", "aloe", "chamomile", "phytochem",
            "crispr", "cas12", "cas9", "base edit", "petase", "cutinase", "enzyme", "aptamer", "antibody",
            "nanoparticle", "peptide", "vector", "vaccine", "docking", "inhibitor", "compound",
            "probiotic", "metabolite", "surfactant", "emulsion", "hydrogel", "cleanser", "bioreactor", "bioactive"
        ])
        if has_subject:
            what_is_working.append("Active research subject / intervention recognized in draft.")
        else:
            needs_attention.append("Missing explicit active substance, botanical extract, or molecular tool.")
            guiding_questions.append("What specific active substance or bioengineered tool is the subject of this proposal?")

        # Check for Formulation / Delivery Matrix
        has_formulation_matrix = any(t in text.lower() for t in [
            "cream", "gel", "emulsion", "formulation", "ointment", "hydrogel", "topical",
            "nanoparticle", "nanoparticles", "liposome", "liposomal", "microneedle", "lotion", "cleanser", "snedds"
        ])
        if has_formulation_matrix:
            what_is_working.append("Formulation delivery vehicle recognized in title.")

        # Check for True Experimental Biological Model / Testing Chassis
        has_in_vitro = any(t in text.lower() for t in [
            "raw 264", "raw264", "hacat", "hdf", "fibroblast", "fibroblasts", "keratinocyte", "keratinocytes",
            "macrophage", "macrophages", "hepg2", "hek293", "mcf-7", "thp-1", "caco-2", "in vitro", "cell line",
            "cell culture", "primary cells"
        ])
        has_in_vivo = any(t in text.lower() for t in [
            "balb/c", "c57bl", "wistar", "sprague-dawley", "murine", "mice", "mouse", "rat", "rats",
            "rabbit", "rabbits", "in vivo", "animal model", "edema model", "ear edema"
        ])
        has_ex_vivo = any(t in text.lower() for t in [
            "porcine skin", "porcine ear", "franz cell", "franz diffusion", "skin explant", "ex vivo", "excised skin"
        ])
        has_in_silico = any(t in text.lower() for t in [
            "molecular docking", "molecular dynamics", "in silico", "virtual screening"
        ])
        has_microbial = any(t in text.lower() for t in [
            "coli", "pastoris", "yeast", "bacillus", "pseudomonas", "staphylococcus", "aureus", "mrsa"
        ])

        has_explicit_bio_model = has_in_vitro or has_in_vivo or has_ex_vivo or has_in_silico or has_microbial

        if has_explicit_bio_model:
            what_is_working.append("Publication-grade biological chassis declared (cell line, animal species, or tissue model).")
        elif has_formulation_matrix:
            # THIS IS THE CRUCIAL CASE: Title has "cream" but lacks explicit cell line or animal species!
            needs_attention.append(
                "🔬 Publication-Grade Scientific Recommendation: Your title specifies the delivery matrix ('Cream' / formulation), but does not state the experimental biological chassis. "
                "Peer-reviewed research papers must declare whether testing is in vitro (naming the exact cell type, e.g. 'in RAW 264.7 Macrophages' or 'in HaCaT Keratinocytes'), "
                "in vivo (naming the animal species/strain, e.g. 'in a BALB/c Murine Edema Model'), ex vivo (e.g. 'in Porcine Skin Franz Diffusion Cells'), "
                "or in silico (e.g. 'Molecular Docking against COX-2'). Specifying your testing model elevates your proposal to publication caliber."
            )
            why_it_matters.append(
                "In biotechnology research papers, a topical formulation ('Cream') is the vehicle, not the biological testing model. Reviewers and ethics committees require an explicit biological chassis to evaluate physiological relevance and required regulatory approvals."
            )
            guiding_questions.append(
                "Will you evaluate this cream: (1) In Vitro in macrophage cell culture (e.g. RAW 264.7)? (2) Ex Vivo across excised porcine skin in Franz cells? Or (3) In Vivo in an animal edema model (e.g. BALB/c mice)?"
            )
            revision_criteria.append(
                "Integrate your explicit biological chassis into the title: e.g. 'Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized Calendula Cream in RAW 264.7 Macrophages'."
            )
            self_check.append("Did I state whether my biological testing is in vitro (exact cell line), ex vivo (skin tissue), or in vivo (animal species)?")
        else:
            needs_attention.append("Missing both delivery matrix and experimental biological testing model.")
            why_it_matters.append("Proposals cannot be evaluated without knowing the biological chassis or delivery vehicle.")
            guiding_questions.append("In what biological chassis, cell culture, or animal model will your intervention be evaluated?")

        # Check for Target Benchmark / Clinical Comparator
        has_benchmark = bool(re.search(r'\b(\d+%|>\s*\d+|<\s*\d+|ic50|mic\b|mbc\b|kd\b|closure|hydrocortisone|corticosteroid|comparator|benchmarked)\b', text, re.I))
        if has_benchmark:
            what_is_working.append("Quantitative milestone or reference comparator declared in title.")
        else:
            guiding_questions.append("Can you add a target quantitative benchmark or reference comparator (e.g. 'to Inhibit Pro-Inflammatory Mediators Benchmarked Against Hydrocortisone 1%')?")
            revision_criteria.append("State a target quantitative milestone or positive comparator in your title.")

    # --- Section 1: Executive Abstract ---
    elif ("abstract" in sec_lower or bool(re.search(r"\b(sec0?1|section[\s-]0?1)\b", sec_lower))) and "10" not in sec_lower:
        if word_count < 150:
            needs_attention.append(f"Abstract is under-developed ({word_count}/150 words). Official BT_301 rubric requires 150–250 words summarizing problem, baseline, methods, and expected impact.")
            why_it_matters.append("Reviewers read the abstract first; brief abstracts suggest an incomplete scientific proposal.")
            guiding_questions.append("Which essential components (problem burden, gold-standard comparator, explicit testing chassis, or target milestone) can you expand?")
        elif word_count > 250:
            needs_attention.append(f"Abstract exceeds the 250-word ceiling ({word_count}/250 words). Grant committees strictly enforce word limits.")
            why_it_matters.append("Review panels reject or truncate abstracts exceeding the word ceiling.")
            guiding_questions.append("Where can you remove filler words to bring the abstract under 250 words?")
        else:
            what_is_working.append(f"Word count ({word_count} words) satisfies the strict 150–250 word rubric standard.")

        has_quant_burden = bool(re.search(r'\b(\d+(\.\d+)?%|\d+\s*(million|billion|m|b)|>\s*\d+|<\s*\d+)\b', text, re.I))
        if has_quant_burden:
            what_is_working.append("Quantified real-world problem or burden identified.")
        else:
            needs_attention.append("Missing quantified epidemiological figure (e.g. >230M patients worldwide, economic loss in EGP).")
            guiding_questions.append("What verified empirical statistic defines the global scale of this problem?")

        has_comparator = bool(re.search(r'\b(hydrocortisone|corticosteroid|standard|gold\s+standard|conventional|comparator|current)\b', text, re.I))
        if has_comparator:
            what_is_working.append("Current clinical benchmark / standard of care referenced.")
        else:
            needs_attention.append("Missing reference to the current clinical standard of care (e.g. Hydrocortisone 1% cream) and its limitations.")
            guiding_questions.append("What current standard treatment will your intervention improve upon or benchmark against?")

    # --- Section 2: Introduction & 4-Tier Inverted Funnel ---
    elif "intro" in sec_lower or "background" in sec_lower or "problem" in sec_lower or "sec2" in sec_lower:
        has_pivot = any(w in text.lower() for w in ["however", "nevertheless", "limitation", "bottleneck", "challenge", "constrained", "barrier"])
        if has_pivot:
            what_is_working.append("Clear conceptual transition: includes a pivot word identifying a challenge or limitation.")
        else:
            needs_attention.append("Missing explicit pivot from current standards to the unresolved research gap.")
            why_it_matters.append("Reviewers look for an explicit transition (e.g. 'However, widespread clinical deployment is constrained by...') to understand why your project is necessary.")
            guiding_questions.append("Where does current technology fail, and how can you introduce that bottleneck with an explicit pivot word ('However', 'Nevertheless')?")
            revision_criteria.append("Include an explicit transition sentence highlighting the specific knowledge or formulation gap.")
            self_check.append("Does my draft contain a clear 'However...' pivot introducing the bottleneck?")

        has_hypo = any(w in text.lower() for w in ["hypothes", "propose", "here we", "this study will", "we aim to"])
        if has_hypo:
            what_is_working.append("Proposed intervention and hypothesis articulated.")
        else:
            guiding_questions.append("Does your background conclude with your proposed hypothesis and scientific justification for your biological chassis?")
            revision_criteria.append("Conclude the inverted funnel narrative with a clear statement of your proposed project and chassis rationale.")

        # Check for standard of care side-effect profile (e.g. steroid thinning)
        has_standard_side_effects = bool(re.search(r'\b(atrophy|thinning|rebound|tachyphylaxis|telangiectasia|side\s+effects?|adverse|corticosteroid|steroid)\b', text, re.I))
        if has_standard_side_effects:
            what_is_working.append("Clinical adverse effects of standard therapy detailed (strong motivation).")
        else:
            needs_attention.append("Deepen Tier 2: Detail the published clinical limitations or adverse effects of standard therapy (e.g. epidermal barrier atrophy and tachyphylaxis from Hydrocortisone 1%).")
            guiding_questions.append("What clinical adverse effects make conventional standard therapies problematic for patients?")

        # Check for strawman gap fallacy
        if any(term in text.lower() for term in ["no studies have been done", "no research exists", "never been done before", "no one has ever"]):
            needs_attention.append("Strawman Gap Alert: Avoid claiming 'no research exists'. Faculty reviewers know thousands of papers exist; state the precise biochemical, formulation, or analytical bottleneck.")
            why_it_matters.append("Grant reviewers penalize absolute negative claims ('no studies exist') as evidence of an inadequate literature search.")
            guiding_questions.append("What specific parameter (e.g. lack of HPLC marker standardization, poor transdermal skin flux) is the genuine unaddressed bottleneck?")

    # --- Section 3: Specific Aims & Objectives ---
    elif "aim" in sec_lower or "objective" in sec_lower or "sec3" in sec_lower:
        active_verbs = ["quantify", "engineer", "validate", "characterize", "optimize", "formulate", "design", "evaluate", "synthesize", "standardize", "isolate"]
        has_active_verb = any(v in text.lower() for v in active_verbs)
        if has_active_verb:
            what_is_working.append("Action-oriented formulation: starts with measurable scientific action verbs.")
        else:
            needs_attention.append("Objectives should lead with active, measurable bioengineering verbs rather than descriptive terms like 'study' or 'investigate'.")
            guiding_questions.append("Which measurable action verb (e.g. Quantify, Formulate, Standardize, Optimize, Validate) best describes your milestone?")

        # Domino Collapse Check
        domino_phrases = ["if aim 1 works", "following successful completion of aim 1", "pending positive results in aim 1", "if objective 1 succeeds", "if successful"]
        if any(dp in text.lower() for dp in domino_phrases):
            needs_attention.append("DOMINO COLLAPSE RISK: Objective appears conditionally dependent on 100% success of a preceding aim. Provide a parallel baseline or standard so downstream work can proceed.")
            why_it_matters.append("Grant panels reject proposals where Aim 2 or Aim 3 collapses if Aim 1 encounters yield or technical delays.")
            guiding_questions.append("How can you decouple this objective using commercial standards so it can proceed independently if Aim 1 is delayed?")

    # --- Section 4: Experimental Methodology & Controls ---
    elif "method" in sec_lower or "sec4" in sec_lower:
        # Check for vehicle controls and comparators
        has_neg = any(w in text.lower() for w in ["vehicle control", "blank cream", "blank emulsion", "unloaded vehicle", "untreated control", "blank base"])
        has_pos = any(w in text.lower() for w in ["positive control", "hydrocortisone", "corticosteroid", "indomethacin", "dexamethasone", "ascorbic acid", "reference standard", "commercial cream", "positive comparator"])
        
        if has_neg and has_pos:
            what_is_working.append("Experimental rigor: Both an unloaded vehicle control and a positive reference standard are declared.")
        elif not has_neg:
            needs_attention.append("Missing Unloaded Vehicle Control: Specify a blank cream/vehicle base lacking extract to prove excipients do not cause false-positive suppression.")
            why_it_matters.append("Excipients, preservatives, and surfactants can cause background inhibition; reviewers demand vehicle blanks to confirm biological specificity.")
            guiding_questions.append("What exact blank matrix will serve as your negative vehicle control?")
        elif not has_pos:
            needs_attention.append("Missing Positive Reference Standard: Benchmark side-by-side against an established clinical drug comparator (e.g. Commercial Hydrocortisone 1% cream or Indomethacin).")
            why_it_matters.append("Without a positive clinical comparator, reviewers cannot calibrate whether observed bioactivity is clinically meaningful.")
            guiding_questions.append("What established pharmaceutical drug will serve as your positive reference standard?")

        # Check for replicate structure
        has_trips = bool(re.search(r'\b(triplicate|n\s*=\s*3|biological\s+replicate|independent\s+batches|three\s+independent)\b', text, re.I))
        if has_trips:
            what_is_working.append("Statistical replication: Biological triplicates (n=3) declared.")
        else:
            needs_attention.append("Statistical Rigor: Specify biological triplicates (n=3 independent batches or cell cultures) distinct from technical pipetting repeats.")
            guiding_questions.append("How many independent biological batches will you prepare to calculate standard errors (mean ± SEM)?")

        # Check for statistical test
        has_stats = bool(re.search(r'\b(anova|dunnett|tukey|t-test|post-hoc|p\s*<\s*0\.05|confidence\s+interval)\b', text, re.I))
        if has_stats:
            what_is_working.append("Statistical hypothesis test declared.")
        else:
            needs_attention.append("Missing Statistical Analysis Plan: Name your statistical test (e.g. One-way ANOVA followed by Dunnett's post-hoc test against vehicle control, p < 0.05).")
            guiding_questions.append("What specific ANOVA test and post-hoc comparison will you use to determine statistical significance?")

        # Check for tense
        has_future_tense = any(w in text.lower() for w in ["will be", "shall be", "are to be", "is to be"])
        if has_future_tense:
            what_is_working.append("Appropriate proposal tense: uses prospective future tense.")
        else:
            needs_attention.append("Grant proposals must describe proposed experimental procedures in prospective future tense ('will be incubated', 'will be quantified').")
            revision_criteria.append("Standardize procedural descriptions into formal future tense.")

    # --- Section 5: Risk Assessment & Contingency Plan (Plan B) ---
    elif "risk" in sec_lower or "outcome" in sec_lower or "plan b" in sec_lower or "sec5" in sec_lower:
        has_gates = bool(re.search(r'\b(go/no-go|contingency|plan b|if.*fail|alternative|threshold|gate|switch to)\b', text, re.I))
        if has_gates:
            what_is_working.append("Proactive contingency thinking: includes go/no-go decision gates or alternative protocols.")
        else:
            needs_attention.append("Missing Quantitative Go/No-Go Decision Gates: Detail specific numerical failure thresholds (e.g. if extraction yield < 5% or skin flux < 5 µg/cm²/h) and technical rescue protocols.")
            guiding_questions.append("What technical Plan B will you trigger if the topical formulation exhibits phase separation during freeze-thaw cycles?")

    # --- Section 7 / 8: Strategic Position (SWOT & PESTEL) ---
    elif "swot" in sec_lower or "pestel" in sec_lower or "sec7" in sec_lower or "sec8" in sec_lower:
        has_cliche = any(term in text.lower() for term in ["we are students", "lack of experience", "not enough time", "we are beginners", "limited knowledge"])
        if has_cliche:
            needs_attention.append("Avoid student clichés ('we are beginners', 'lack of experience'). Reviewers expect technical/biochemical risks (e.g. active marker oxidation, emulsion coalescence, skin irritancy).")
            why_it_matters.append("Grant evaluation committees evaluate proposals based on technical and commercial feasibility, not personal investigator modesty.")
            guiding_questions.append("What genuine biochemical, formulation, or regulatory bottleneck threatens project translation?")

    # --- Section 9: Timeline & Budget ---
    elif "budget" in sec_lower or "timeline" in sec_lower or "sec9" in sec_lower:
        has_egp = bool(re.search(r'\b(egp|egyptian\s+pounds?|ج\.م)\b', text, re.I))
        if has_egp:
            what_is_working.append("Budget accurately specified in local currency (Egyptian Pounds - EGP).")
        else:
            needs_attention.append("Ensure all budget line items and consumables are costed in Egyptian Pounds (EGP) with supplier quotes.")
            guiding_questions.append("What are your estimated costs in EGP for key reagents, ELISA kits, and analytical chromatography?")

        # --- Section 10: References / Bibliography (APA 7th Edition) ---
    elif any(k in sec_lower for k in ["reference", "bibliography", "citation", "sec10"]):
        ref_lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 15]
        ref_count = len(ref_lines)
        
        if ref_count < 3:
            needs_attention.append(f"Insufficient literature base ({ref_count} reference(s) detected). Academic proposals require at least 5–10 peer-reviewed primary citations.")
            why_it_matters.append("A sparse reference list signals to reviewers that the project is not grounded in current prior art or methodology standards.")
            guiding_questions.append("What recent peer-reviewed studies (2021–2026) report active benchmarks or protocols for your model chassis?")
            revision_criteria.append("Expand reference list to include primary research articles, benchmark studies, and standard protocol references.")
        else:
            what_is_working.append(f"Substantial literature foundation: {ref_count} reference entries detected.")
        
        # Check alphabetical sorting
        first_authors = []
        for l in ref_lines:
            m = re.match(r'^([A-Z][a-zA-Z\'\-]+)', l)
            if m:
                first_authors.append(m.group(1).lower())
        if len(first_authors) >= 2:
            is_sorted = first_authors == sorted(first_authors)
            if is_sorted:
                what_is_working.append("Alphabetical layout: References are properly alphabetized by first author surname (§5.2.3).")
            else:
                needs_attention.append("Alphabetical Order: APA 7th references must be sorted alphabetically by the first author's surname (not in order of appearance).")
                why_it_matters.append("Reviewers expect standard APA 7th alphabetical listing to rapidly verify cited claims.")
                revision_criteria.append("Sort your reference list alphabetically from A to Z by first author's last name.")

        # Check DOI formatting (https://doi.org/... with no trailing period)
        has_doi = "doi.org" in text.lower() or "10." in text
        if has_doi:
            what_is_working.append("Digital Object Identifiers (DOIs) included for traceable literature retrieval.")
            if re.search(r'doi:\s*10\.', text, re.I):
                needs_attention.append("Modern DOI Format: APA 7th requires DOIs as active hyperlinks (https://doi.org/10.xxxx/...), not the older 'doi:10.xxxx' prefix (§5.2.3).")
            if re.search(r'https?://doi\.org/[^\s]+\.\s*$', text, re.M):
                needs_attention.append("No Trailing Period on DOIs: Do not place a period after a DOI hyperlink (e.g. 'https://doi.org/...'). A trailing period breaks the web link when clicked by reviewers.")
        else:
            needs_attention.append("Missing DOIs: Provide active DOI hyperlinks (https://doi.org/10.xxxx/...) for journal articles to allow direct reviewer verification.")
            why_it_matters.append("DOIs are persistent identifiers required under APA 7th to enable instant electronic cross-referencing.")

        # Check for deprecated "Retrieved from"
        if re.search(r'\bretrieved\s+from\b', text, re.I):
            needs_attention.append("Deprecated Phrasing: Do not include 'Retrieved from' before a DOI or standard database URL in APA 7th (§5.2.3, §5.2.6). Present the DOI URL directly.")

        # Check article title capitalization (Sentence case vs Title case)
        title_case_suspects = re.findall(r'(?:[A-Z][a-z]+\s+){3,}(?:in|of|and|for|with|by)\s+(?:[A-Z][a-z]+\s+){2,}', text)
        if title_case_suspects:
            needs_attention.append("Title Capitalization Rule (#1 APA Mistake): APA 7th requires sentence case for article and book titles. Capitalize ONLY the first word, the first word after a colon, and proper nouns/genus names (e.g. 'Formulation and in vitro evaluation of Calendula officinalis cream: A comparative study'). Journal titles, however, remain in Title Case and italics.")
            why_it_matters.append("Under APA 7th (§5.2.3(d)), article titles use sentence case. Capitalizing every word is the single most frequent error flagged by academic reviewers.")

        # Check ampersand vs and in author lists
        if re.search(r'[A-Z][a-z]+,\s*[A-Z]\.?\s*(?:[A-Z]\.?\s*)?and\s+[A-Z][a-z]+,\s*[A-Z]\.?', text):
            needs_attention.append("Author List Syntax: In APA 7th reference list entries, separate the final author with an ampersand (&), not the word 'and' (e.g. 'Khan, M. A., & Rahman, S. L.').")

        # Literature recency check
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', text)]
        recent_years = [y for y in years if y >= 2020]
        if years:
            recency_ratio = len(recent_years) / len(years)
            if recency_ratio >= 0.5:
                what_is_working.append(f"Literature currency: {len(recent_years)}/{len(years)} citations ({int(recency_ratio*100)}%) published within the last 5 years (2020–2026).")
            else:
                needs_attention.append("Literature Recency: Less than 50% of your citations are from the last 5 years. Strengthen your proposal with recent peer-reviewed articles (2021–2026).")
                why_it_matters.append("Grant panels expect modern methodology and current benchmarks rather than exclusively historical literature.")

        # Matching Rule reminder
        self_check.append("The Matching Rule (§5.2.1): Does every reference entry appear in my proposal text as an in-text citation, and vice versa?")
        self_check.append("Are article titles formatted in sentence case and journal names in Title Case & italics?")
        self_check.append("Are all DOIs formatted as https://doi.org/... without trailing periods?")

# Default praise if draft is solid
    if not needs_attention and word_count >= 30:
        what_is_working.append("Strong academic register and structured scientific prose.")
        guiding_questions.append("How would you defend this section if a reviewer asked: 'What is the primary biological failure risk of this approach?'")
        self_check.append("Is my text completely in my own words and ready for oral defense?")

    # Guarantee at least 1 guiding question
    if not guiding_questions:
        guiding_questions.append(f"How does this draft specifically advance your stated hypothesis and quantitative benchmark?")

    # Populate revision criteria & self-check defaults if empty
    if not revision_criteria:
        revision_criteria.append("Ensure every factual claim has an empirical literature basis.")
        revision_criteria.append("Maintain formal biomedical terminology throughout.")
    if not self_check:
        self_check.append("Did I address the specific reviewer concerns highlighted above?")
        self_check.append("Is the text authored entirely in my own academic voice?")

    return {
        "status": "analyzed",
        "is_ghostwriting_request": False,
        "role": "academic_mentor",
        "word_count": word_count,
        "what_is_working": what_is_working,
        "needs_attention": needs_attention,
        "why_it_matters": why_it_matters,
        "guiding_questions": guiding_questions,
        "revision_criteria": revision_criteria,
        "self_check": self_check,
        # Backward compatibility aliases
        "praise": what_is_working,
        "critiques": needs_attention,
        "socratic_questions": guiding_questions,
        "action_item": (
            "Review the mentor feedback above. Revise your draft independently to address the guiding questions "
            "and revision criteria before submitting for faculty evaluation."
        )
    }



def generate_viva_defense_questions(proposal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates 3-5 authentic oral defense cross-examination questions dynamically adapted
    to the student's research type to prepare them for the Week 10 Mock Review Panel / Viva Voce.
    Preserves research identity: topical formulations get topical questions, recombinant projects
    get recombinant questions, computational projects get docking/benchmarking questions.
    """
    title = proposal_data.get("title", "")
    chassis = proposal_data.get("chassis") or proposal_data.get("system", "the experimental model")
    tool = proposal_data.get("tool", "the active substance/tool")
    target = proposal_data.get("target", "the target problem")
    combined = f"{title} {chassis} {tool} {target}".lower()

    # Domain classification
    is_topical_or_phyto = bool(re.search(r"\b(plant|calendula|herb|herbal|extract|topical|cream|ointment|gel|emulsion|dermal|skin|erythema|wound|curcumin|flavonoid|faradiol|formulat)\b", combined))
    is_computational = bool(re.search(r"\b(docking|molecular\s+dynamics|md\s+sim|in\s+silico|qsar|virtual\s+screen|binding\s+affinity|rmsd|alphafold|autodock)\b", combined))
    is_microbial_amr = bool(re.search(r"\b(amr|antimicrobial|antibacterial|mic\b|mbc|disk\s+diffusion|colistin|mcr-?1|pathogen|biofilm|zone\s+of\s+inhibition)\b", combined))
    is_diagnostics = bool(re.search(r"\b(diagnostic|crispr|cas12|cas13|detectr|sherlock|isothermal|rpa|lamp|biosensor|lateral\s+flow)\b", combined))

    if is_topical_or_phyto:
        return [
            {
                "id": 1,
                "category": "Chemical Standardization & Marker Quantification",
                "question": f"Botanical extracts display wide batch-to-batch variation depending on season, geography, and drying conditions. How will you chemically standardize your {tool} to guarantee reproducible pharmacological activity?",
                "eval_criteria": "Student must declare an analytical marker (e.g. HPLC-UV quantification of faradiol esters or total flavonoids against a reference standard curve) rather than treating crude extract as uniform.",
                "hint": "Specify HPLC reverse-phase C18 chromatography with a defined reference standard (e.g. faradiol-3-myristate) and batch release specifications in mg/g dry weight."
            },
            {
                "id": 2,
                "category": "Cytotoxicity vs. Anti-Inflammatory Efficacy Discrimination",
                "question": "Dying cells do not secrete cytokines. If your formulation reduces nitric oxide or TNF-α in LPS-stimulated macrophages, how do you prove this is true anti-inflammatory efficacy rather than extract-induced cytotoxicity?",
                "eval_criteria": "Student must articulate the requirement for an MTT or LDH cell viability assay and calculate the Selectivity Index (SI = CC50 / IC50 ≥ 3.0) confirming testing strictly at sub-cytotoxic concentrations (>85% viability).",
                "hint": "Explain that cell viability must remain >85% across all tested dilutions, and calculate the Selectivity Index."
            },
            {
                "id": 3,
                "category": "Vehicle Excipient Controls",
                "question": f"When formulating {tool} into {chassis}, what negative vehicle control will you run to prove that excipients (emulsifiers, preservatives, oils) do not produce false-positive anti-inflammatory effects?",
                "eval_criteria": "Student must identify an unloaded blank cream/vehicle (containing all excipients except active extract) tested alongside untreated and positive comparator controls.",
                "hint": "State that blank cream base without extract must be tested head-to-head with active cream and commercial hydrocortisone 1% cream."
            },
            {
                "id": 4,
                "category": "Transdermal Permeation vs. Dialysis Release",
                "question": "Why is simple dialysis membrane release insufficient to establish transdermal delivery, and what authentic biological barrier model will you use to demonstrate stratum corneum permeation?",
                "eval_criteria": "Student distinguishes synthetic membrane diffusion from biological skin permeation across stratum corneum (e.g. Franz diffusion cells with porcine ear skin).",
                "hint": "Highlight that synthetic membranes lack the lipophilic stratum corneum intercellular lipids that dictate true transdermal absorption."
            },
            {
                "id": 5,
                "category": "Aim Decoupling & Emulsion Stability Contingency",
                "question": "If your cream formulation undergoes phase separation or creaming during thermal stress testing, does that halt your in vitro cellular bioassays?",
                "eval_criteria": "Student demonstrates decoupled aims: standardized extract is tested in parallel bioassays while formulation rheology and stability optimization proceed with carbomer or surfactant adjustments.",
                "hint": "Explain that cellular assays utilize standardized extract directly, preventing formulation instability from creating a domino project halt."
            }
        ]

    elif is_computational:
        return [
            {
                "id": 1,
                "category": "Scoring Function Calibration & Redocking",
                "question": f"Molecular docking programs produce docking scores, but scores often correlate poorly with experimental free energy. How will you validate that your scoring function accurately predicts true binding affinity for {target}?",
                "eval_criteria": "Student cites redocking of co-crystallized native ligands (RMSD < 2.0 Å) and benchmarking against known experimentally verified active inhibitors vs. decoy compounds (ROC-AUC / Enrichment Factor).",
                "hint": "Mention redocking crystallographic ligands to achieve RMSD < 2.0 Å and testing on DUD-E decoy sets."
            },
            {
                "id": 2,
                "category": "Receptor Flexibility & Solvation",
                "question": "Rigid-receptor docking ignores induced-fit conformational changes and water-mediated hydrogen bonds. What methodology will you use to address receptor flexibility and solvent effects?",
                "eval_criteria": "Student proposes molecular dynamics (MD) simulations (e.g. 100 ns in explicit solvent using GROMACS/AMBER) or ensemble docking with MM-PBSA/GBSA free energy calculations.",
                "hint": "Reference all-atom MD simulations with TIP3P explicit water and MM-GBSA binding energy estimation."
            },
            {
                "id": 3,
                "category": "Experimental Wet-Lab Validation Gate",
                "question": "A computational proposal without experimental validation is considered preliminary by grant panels. What wet-lab assay will validate your top in silico candidate hits?",
                "eval_criteria": "Student outlines purchasing or expressing the target protein and running an in vitro binding assay (SPR, ITC, or enzyme inhibition IC50 assay).",
                "hint": "Cite Surface Plasmon Resonance (SPR), Isothermal Titration Calorimetry (ITC), or fluorometric enzymatic inhibition assays."
            }
        ]

    elif is_microbial_amr:
        return [
            {
                "id": 1,
                "category": "Antimicrobial Standardization (CLSI/EUCAST)",
                "question": f"Why is disk diffusion (Kirby-Bauer) alone considered an unquantified screening assay rather than a rigorous quantitative endpoint for your testing of {tool}?",
                "eval_criteria": "Student explains that disk diffusion depends on agar thickness and molecule diffusion rates, and declares broth microdilution following CLSI/EUCAST guidelines to determine exact MIC and MBC in µg/mL.",
                "hint": "Reference CLSI M07/M100 broth microdilution standards using 96-well microtiter plates and cation-adjusted Mueller-Hinton broth."
            },
            {
                "id": 2,
                "category": "Inoculum Density & Growth Phase Controls",
                "question": "How will you standardize your bacterial inoculum, and what positive antibiotic comparator control will validate that your assay is calibrated correctly?",
                "eval_criteria": "Student specifies 0.5 McFarland standard (~1.5 × 10⁸ CFU/mL) diluted to 5 × 10⁵ CFU/mL in wells, verified by colony counts, alongside an ATCC reference strain and standard antibiotic control (e.g. ciprofloxacin).",
                "hint": "Mention ATCC reference strains (e.g. E. coli ATCC 25922 or S. aureus ATCC 29213) and 0.5 McFarland turbidity calibration."
            },
            {
                "id": 3,
                "category": "Bactericidal vs. Bacteriostatic Discrimination",
                "question": f"How will you demonstrate whether {tool} is truly bactericidal or merely bacteriostatic against {target}?",
                "eval_criteria": "Student explains subculturing from clear MIC wells onto antibiotic-free agar to determine the Minimum Bactericidal Concentration (MBC) and establishes the MBC/MIC ratio (≤4 = bactericidal).",
                "hint": "Explain plating from clear MIC wells to quantify CFU reduction: ≥99.9% kill (3-log reduction) defines bactericidal action."
            }
        ]

    elif is_diagnostics:
        return [
            {
                "id": 1,
                "category": "Diagnostic Sensitivity & Limit of Detection (LoD)",
                "question": f"What is your experimental protocol to determine the Limit of Detection (LoD) for {tool}, and how do you ensure statistical rigor under CLSI EP17 standards?",
                "eval_criteria": "Student declares serial dilution of quantified target DNA/RNA (e.g. 10⁶ down to 1 copy/µL), testing across biological replicates (n ≥ 20 near threshold), and applying probit regression to define 95% detection probability.",
                "hint": "Cite probit regression analysis across ≥20 replicates per low-concentration dilution under CLSI EP17-A2."
            },
            {
                "id": 2,
                "category": "Cross-Reactivity & Matrix Interference",
                "question": f"Clinical and environmental matrices contain humic acids, nucleases, and high-abundance background nucleic acids. What challenge panels and matrix-matched blanks will you test to rule out false positives?",
                "eval_criteria": "Student outlines spike-and-recovery tests in authentic unspiked matrix, alongside a panel of close phylogenetically related non-target organisms to prove analytical specificity.",
                "hint": "Describe testing unspiked authentic matrix blanks and non-target microbial genomic DNA panels."
            }
        ]

    # Default: Molecular biology / Recombinant chassis
    return [
        {
            "id": 1,
            "category": "Chassis Justification & Physiology",
            "question": f"Why did your team select {chassis} as your production or deployment chassis instead of standard lab models (like E. coli or Pichia pastoris)? What specific post-translational modifications, codon biases, or growth advantages does it provide?",
            "eval_criteria": "Student must articulate biological rationale (e.g. secretory pathway, endotoxin-free, tolerance to high osmolarity) rather than just saying 'it was in the paper'.",
            "hint": "Reference doubling time, secretion signals, disulfide bond isomerization, or native metabolic pathways."
        },
        {
            "id": 2,
            "category": "Experimental Controls & Rigor",
            "question": f"In your testing of {tool}, what is your exact negative control, and what quantitative threshold separates a true biological effect from background noise or abiotic variation?",
            "eval_criteria": "Student must identify vehicle/mock-treated controls, dead enzyme (catalytic mutant), or untransformed host strain.",
            "hint": "For enzyme degradation: heat-inactivated enzyme control. For CRISPR: non-targeting guide RNA control."
        },
        {
            "id": 3,
            "category": "Biological Failure Modes (ACP Defense)",
            "question": f"Suppose your recombinant construct yields insoluble inclusion bodies when expressed in {chassis}. What is your immediate technical contingency plan to rescue soluble, active protein?",
            "eval_criteria": "Student applies the Acknowledge-Clarify-Pivot (ACP) technique and offers a realistic bioprocess pivot.",
            "hint": "Lower induction temperature to 16°C, fuse solubility tags (MBP/GST/SUMO), or switch to an Origami/chaperone-coexpressing strain."
        },
        {
            "id": 4,
            "category": "Aim Independence & Milestone Risk",
            "question": f"If Aim 1 yields 40% lower expression than your target milestone, how does that compromise Aim 2 and Aim 3? Did you engineer a parallel baseline or alternative candidate?",
            "eval_criteria": "Proves project does not suffer from Domino Collapse.",
            "hint": "Explain that Aim 2 utilizes commercially purchased wild-type enzyme as an active parallel baseline while Aim 1 mutants are being optimized."
        },
        {
            "id": 5,
            "category": "Translation & Regulatory Reality (PESTEL)",
            "question": f"Addressing {target} in a laboratory is vastly different from real-world environmental or clinical deployment. What specific biosafety level (BSL) or national regulatory framework governs your project?",
            "eval_criteria": "Student demonstrates awareness of containment, Cartagena Protocol, or local regulatory approval processes.",
            "hint": "Mention BSL-1/BSL-2 containment, kill-switch biocontainment for GMO release, or ethics committee approvals."
        }
    ]


# Backward-compatible alias
is_ghostwriting_intent = detect_ghostwriting_intent
