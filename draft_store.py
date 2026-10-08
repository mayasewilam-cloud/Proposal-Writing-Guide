"""
BioWriter Studio - Server-side Student Draft Storage and Roster Management.
Persists student proposal drafts as structured JSON in portal/data/drafts/.
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.environ.get("VERCEL"):
    DATA_DIR = os.path.join("/tmp", "data")
    DRAFTS_DIR = os.path.join(DATA_DIR, "drafts")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")
    DRAFTS_DIR = os.path.join(DATA_DIR, "drafts")


def _ensure_drafts_dir():
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    if os.environ.get("VERCEL") and os.path.exists(os.path.join(BASE_DIR, "data", "drafts")):
        bundled = os.path.join(BASE_DIR, "data", "drafts")
        for f in os.listdir(bundled):
            src = os.path.join(bundled, f)
            dst = os.path.join(DRAFTS_DIR, f)
            if not os.path.exists(dst) and os.path.isfile(src):
                try:
                    with open(src, "r", encoding="utf-8") as rf, open(dst, "w", encoding="utf-8") as wf:
                        wf.write(rf.read())
                except Exception:
                    pass


def sanitize_student_id(student_id: str) -> str:
    if not student_id:
        return "student_draft"
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", student_id.strip()).strip("_")
    return clean[:40] if clean else "student_draft"


def calculate_draft_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    nodes = 0
    if (data.get("chassis") or data.get("system")) and data.get("tool"):
        nodes += 1
    if data.get("query") or data.get("search_query") or data.get("target"):
        nodes += 1
    if data.get("matrix") and (data.get("matrix", {}).get("blue") or data.get("matrix", {}).get("green") or data.get("matrix", {}).get("yellow") or data.get("matrix", {}).get("citation")):
        nodes += 1
    if data.get("funnel") and (data.get("funnel", {}).get("tier1") or data.get("funnel", {}).get("tier2")):
        nodes += 1
    if data.get("aims") and (data.get("aims", {}).get("aim1") or data.get("overarching_aim")):
        nodes += 1
    if data.get("methodology") and len(data.get("methodology", "").strip()) > 30:
        nodes += 1
    if (data.get("impact_data") and (data.get("impact_data", {}).get("academic") or data.get("impact_data", {}).get("economic"))) or (data.get("impact") and len(data.get("impact", "").strip()) > 10) or data.get("impact_text"):
        nodes += 1
    if (data.get("competitor_data") and (data.get("competitor_data", {}).get("usp") or data.get("competitor_data", {}).get("proposed_name"))) or data.get("usps"):
        nodes += 1
    if data.get("swot") and (data.get("swot", {}).get("s") or data.get("swot", {}).get("strengths")) and (data.get("swot", {}).get("w") or data.get("swot", {}).get("weaknesses")):
        nodes += 1
    if data.get("references") and len(data.get("references", "").strip()) > 20:
        nodes += 1

    # Approximate total words
    all_text = " ".join([
        str(data.get("title", "")),
        str(data.get("abstract", "")),
        str(data.get("methodology", "")),
        str(data.get("funnel", {}).get("tier1", "")),
        str(data.get("funnel", {}).get("tier2", "")),
        str(data.get("funnel", {}).get("tier3", "")),
        str(data.get("funnel", {}).get("tier4", "")),
        str(data.get("aims", {}).get("aim1", "")),
        str(data.get("aims", {}).get("aim2", "")),
        str(data.get("aims", {}).get("aim3", ""))
    ])
    words = len(all_text.split())

    return {
        "completed_nodes": nodes,
        "completion_percentage": int((nodes / 10.0) * 100),
        "word_count": words
    }


def save_student_draft(student_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id or data.get("student_id", ""))
    now_iso = datetime.datetime.now().isoformat()
    now_readable = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")

    data["student_id"] = clean_id
    data["student_name"] = data.get("student_name", "BT_301 Student")
    data["updated_at"] = now_iso
    data["updated_at_readable"] = now_readable

    # SECURITY & ISOLATION: A student client MUST NEVER be able to inject or forge faculty_review.
    # Preserve existing official faculty evaluation if one was already dispatched for this student.
    existing = get_student_draft(clean_id)
    if existing and existing.get("faculty_review"):
        data["faculty_review"] = existing["faculty_review"]
    else:
        data["faculty_review"] = None

    summary = calculate_draft_summary(data)
    data["summary"] = summary

    filepath = os.path.join(DRAFTS_DIR, f"{clean_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "student_id": clean_id,
        "student_name": data["student_name"],
        "title": data.get("title", "Untitled Proposal"),
        "updated_at": now_readable,
        "summary": summary
    }


def get_student_draft(student_id: str) -> Optional[Dict[str, Any]]:
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    filepath = os.path.join(DRAFTS_DIR, f"{clean_id}.json")
    if not os.path.exists(filepath):
        # Case insensitive / partial lookup fallback
        for fname in os.listdir(DRAFTS_DIR):
            if fname.lower().endswith(".json"):
                stem = fname[:-5]
                if stem.lower() == clean_id.lower() or stem.lower() == student_id.lower():
                    filepath = os.path.join(DRAFTS_DIR, fname)
                    break
        else:
            return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["summary"] = calculate_draft_summary(data)
            return data
    except Exception:
        return None


def toggle_draft_lock(student_id: str, is_locked: bool) -> Dict[str, Any]:
    """Toggles or sets the proposal lock for official grading."""
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    draft = get_student_draft(clean_id)
    if not draft:
        return {"success": False, "error": f"Student draft '{clean_id}' not found."}

    draft["is_locked_for_grading"] = bool(is_locked)
    draft["locked_at"] = datetime.datetime.now().strftime("%b %d, %Y - %H:%M") if is_locked else None

    filepath = os.path.join(DRAFTS_DIR, f"{clean_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(draft, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "student_id": clean_id,
        "is_locked_for_grading": bool(is_locked),
        "message": "Proposal successfully locked for faculty grading." if is_locked else "Proposal unlocked for revisions."
    }


def dispatch_faculty_feedback(student_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
    """Stores official instructor evaluation, point overrides, and action items onto the student's cloud record."""
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    draft = get_student_draft(clean_id)
    if not draft:
        return {"success": False, "error": f"Student draft '{clean_id}' not found."}

    now_readable = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")
    feedback["dispatched_at"] = now_readable

    draft["faculty_review"] = feedback
    # Also save to disk
    filepath = os.path.join(DRAFTS_DIR, f"{clean_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(draft, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "student_id": clean_id,
        "dispatched_at": now_readable,
        "faculty_review": feedback,
        "message": f"Official evaluation successfully dispatched to student draft {clean_id}."
    }


def delete_student_draft(student_id: str) -> Dict[str, Any]:
    """Permanently deletes a student's proposal draft file from the server database."""
    _ensure_drafts_dir()
    clean_id = sanitize_student_id(student_id)
    if not clean_id or clean_id == "student_draft":
        return {"success": False, "error": "Invalid student ID."}

    filepath = os.path.join(DRAFTS_DIR, f"{clean_id}.json")
    if not os.path.exists(filepath):
        # Case-insensitive fallback
        for fname in os.listdir(DRAFTS_DIR):
            if fname.lower().endswith(".json") and fname[:-5].lower() == clean_id.lower():
                filepath = os.path.join(DRAFTS_DIR, fname)
                break
        else:
            return {"success": False, "error": f"Submission for student '{clean_id}' not found."}

    try:
        os.remove(filepath)
        return {
            "success": True,
            "student_id": clean_id,
            "message": f"Proposal submission for {clean_id} permanently removed."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to delete submission: {str(e)}"}


def list_student_drafts() -> List[Dict[str, Any]]:
    _ensure_drafts_dir()
    seed_default_drafts()

    roster = []
    for fname in os.listdir(DRAFTS_DIR):
        if fname.endswith(".json"):
            filepath = os.path.join(DRAFTS_DIR, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    summary = calculate_draft_summary(d)
                    fac_rev = d.get("faculty_review")
                    action_items = fac_rev.get("action_items", []) if (fac_rev and isinstance(fac_rev, dict)) else []
                    completed_feedback = d.get("completed_feedback_items", [])
                    roster.append({
                        "student_id": d.get("student_id", fname[:-5]),
                        "student_name": d.get("student_name", "Anonymous Student"),
                        "title": d.get("title", "Untitled Proposal"),
                        "modality": d.get("modality", "Cellular Expression"),
                        "updated_at": d.get("updated_at_readable", d.get("updated_at", "Recently")),
                        "completed_nodes": summary["completed_nodes"],
                        "completion_percentage": summary["completion_percentage"],
                        "word_count": summary["word_count"],
                        "is_locked_for_grading": bool(d.get("is_locked_for_grading", False)),
                        "faculty_reviewed": bool(fac_rev),
                        "faculty_review": fac_rev,
                        "total_action_items": len(action_items),
                        "completed_feedback_items": completed_feedback,
                        "completed_action_count": len(completed_feedback)
                    })
            except Exception:
                continue

    roster.sort(key=lambda x: x.get("student_id", ""))
    return roster


def seed_default_drafts():
    """Seeds Maya Abdelrazek's exemplar proposal draft (13989.json) if not already present."""
    _ensure_drafts_dir()
    fpath = os.path.join(DRAFTS_DIR, "13989.json")
    if not os.path.exists(fpath):
        exemplar = {
    "student_id": "13989",
    "student_name": "Maya Abdelrazek",
    "model_id": "cellular",
    "custom_modality": "",
    "submission_date": "28 September 2026",
    "title": "DETECTR-Aqua: A CRISPR-Cas12a-Assisted Isothermal Assay for Detecting the Colistin-Resistance Gene mcr-1 in Hospital Wastewater",
    "keywords": "CRISPR-Cas12a; mcr-1; colistin resistance; recombinase polymerase amplification; hospital wastewater; antimicrobial resistance surveillance.",
    "system": "Microbial pathogen detection & environmental AMR surveillance",
    "chassis": "Hospital wastewater effluent matrix containing plasmid-borne mcr-1 Gram-negative bacteria",
    "tool": "Recombinase Polymerase Amplification (RPA) coupled with LbCas12a-crRNA trans-cleavage and FAM-quencher ssDNA reporter",
    "target": "Plasmid-borne colistin-resistance gene mcr-1 (phosphoethanolamine transferase)",
    "search_query": "(\"CRISPR-Cas12a\" OR \"DETECTR\") AND (\"mcr-1\" OR \"colistin resistance\") AND \"wastewater\" AND \"RPA\"",
    "team_roster": [
        {
            "name": "Maya Abdelrazek (Principal Investigator)",
            "id": "13989",
            "email": "m.abdelrazek@nu.edu.eg",
            "role": "Principal Investigator"
        },
        {
            "name": "Team Member 2",
            "id": "13990",
            "email": "member2@nu.edu.eg",
            "role": "Co-Investigator"
        },
        {
            "name": "Team Member 3",
            "id": "13991",
            "email": "member3@nu.edu.eg",
            "role": "Co-Investigator"
        }
    ],
    "abstract": "Antimicrobial resistance (AMR) is spreading through healthcare effluents, and colistin, a last-line antibiotic for multidrug-resistant Gram-negative infections, is increasingly threatened by the plasmid-borne gene mcr-1. Hospital wastewater is an ideal early-warning sample, yet routine monitoring relies on culture or quantitative PCR (qPCR), which need thermal cyclers, trained staff, and several hours. Assays that pair recombinase polymerase amplification (RPA) with CRISPR-Cas12a have detected mcr-1 in pure isolates, spiked clinical material, and retail meat, but they have not been evaluated in inhibitor-rich hospital effluent against a reference method. This project proposes DETECTR-Aqua, an RPA–Cas12a fluorescence assay built for wastewater: a crRNA in a conserved mcr-1 region, an internal amplification control that separates true negatives from inhibition, and a concentration-plus-extraction workflow. We will define the detection limit with synthetic DNA, test specificity against mcr-2 to mcr-5 and mcr-1-negative genomes, quantify matrix effects, and compare 36 paired wastewater samples with a TaqMan qPCR comparator. We expect a detection limit near 10 copies per reaction in buffer, no more than 50 copies in wastewater extract, at least 90% agreement with qPCR (Cohen’s κ ≥ 0.80), and a sample-to-result time of about 95 minutes, roughly 40% shorter than qPCR. The results will show whether low-instrument CRISPR detection can support hospital wastewater surveillance.",
    "matrix": {
        "yellow": "LoD of ~6–10 copies per reaction; assay turnaround ~55–60 min at 37–42 °C without thermal cyclers; fluorescence plate reader or blue-LED transilluminator readout.",
        "blue": "Chen, J. S. et al. (Science 2018): CRISPR-Cas12a target binding unleashes indiscriminate single-stranded DNase activity (collateral trans-cleavage), enabling rapid nucleic acid detection down to attomolar sensitivity without PCR cycling. Subsequent mcr-1 assays by Gong et al. (2022) achieved 420 fg sensitivity and Wang et al. (2024) achieved 6.25 copies via one-tube RPA-Cas12b.",
        "green": "Published mcr-1 CRISPR assays were validated solely on pure isolates, spiked clinical samples, and retail meat (Gong et al., 2022; Wang et al., 2024). No peer-reviewed study has evaluated an mcr-1 RPA–Cas12a assay in raw hospital effluent, quantified matrix signal suppression from detergents/disinfectants/humic matter, or conducted a head-to-head comparison with qPCR on paired effluent samples.",
        "purple": "DETECTR-Aqua: a matrix-aware RPA–Cas12a fluorescence assay for hospital effluent with an internal amplification control (IAC). Target analytical LoD95 ≤ 10 copies/reaction in buffer, ≤ 50 copies in wastewater extract, ≥ 90% agreement with TaqMan qPCR (Cohen's κ ≥ 0.80), and ~95 min sample-to-result turnaround.",
        "red": "Chen, J. S., Ma, E., Harrington, L. B., Da Costa, M., Tian, X., Palefsky, J. M., & Doudna, J. A. (2018). CRISPR-Cas12a target binding unleashes indiscriminate single-stranded DNase activity. Science, 360(6387), 436–439. https://doi.org/10.1126/science.aar6245",
        "citation": "Chen, J. S. et al. (2018) Science 360(6387):436–439."
    },
    "funnel": {
        "tier1": "Antimicrobial resistance threatens the treatment of common infections, and Gram-negative bacteria that resist many drugs are a particular concern. Colistin (polymyxin E) is one of the few remaining options against these organisms (Osei Sekyere et al., 2016). Resistance to colistin was long attributed to chromosomal mutations, which spread only vertically. That changed in 2015, when Liu et al. (2016) identified mcr-1 on a conjugative plasmid in Escherichia coli from pigs and humans in China, showing that colistin resistance could move between bacteria. A systematic review of clinical E. coli isolates found mcr-1 to be the most widespread mcr variant worldwide (Dadashi et al., 2022).",
        "tier2": "Hospitals concentrate antibiotic use, resistant bacteria, and resistance genes, and their wastewater carries all three toward the wider environment. Where treatment is incomplete, these contaminants can enter surface water and reach other bacterial communities (Serwecińska, 2020), and resistance genes have been shown to pollute aquatic systems on a continental scale (Zhu et al., 2017). Wastewater therefore serves two roles: a route by which resistance spreads and a pooled, non-invasive sample that reflects many patients at once. Monitoring mcr-1 in hospital effluent could give infection-control teams an early signal without testing individual patients.",
        "tier3": "Current detection methods do not fit routine effluent monitoring well. Culture-based screening takes more than 24 hours, and PCR-based methods, although specific, take about two hours or more and require thermal cyclers and trained operators (Wang et al., 2024). A TaqMan qPCR assay for mcr-1 (Chabou et al., 2016) is a widely used reference, but it is confined to laboratories with this equipment.",
        "tier4": "CRISPR-based diagnostics offer an alternative. When Cas12a binds its DNA target through a guide RNA, it begins cutting any nearby single-stranded DNA, so a quenched fluorescent reporter can be used to signal the presence of the target (Chen et al., 2018; Kaminski et al., 2021). Coupled to RPA, which amplifies DNA at 37–42 °C without a thermal cycler, this approach has been applied to mcr-1 (Gong et al., 2022; Wang et al., 2024; Lin et al., 2022). We propose DETECTR-Aqua: an RPA–Cas12a fluorescence assay tailored for hospital effluent with an internal amplification control, concentration-plus-extraction workflow, and paired qPCR benchmarking."
    },
    "problem_narrative": "Antimicrobial resistance threatens the treatment of common infections, and Gram-negative bacteria that resist many drugs are a particular concern. Colistin (polymyxin E) is one of the few remaining options against these organisms. Resistance to colistin was long attributed to chromosomal mutations, but the 2015 discovery of plasmid-borne mcr-1 showed horizontal transmissibility. Hospitals concentrate antibiotic use, resistant bacteria, and resistance genes, and their wastewater carries all three toward the wider environment. Current detection methods do not fit routine effluent monitoring well: culture takes >24 hours, while qPCR requires thermal cyclers and trained operators. Published mcr-1 CRISPR assays were validated on pure isolates and food matrices, leaving unresolved how the assay performs in raw, inhibitor-rich hospital effluent.",
    "impact": "Scientific: First quantified account of how hospital effluent affects an RPA–Cas12a assay, together with a matrix-aware validity rule that other CRISPR-diagnostic studies can reuse. Clinical & Infection Control: Fast, low-equipment signal for colistin-resistance genes in hospital sewage could prompt earlier review of antibiotic use and isolation practice. Environmental: Routine screening of effluent before discharge would help identify sites that release resistance genes into surface water. Industrial & Economic: A validated, kit-ready workflow that needs only a heat block and a light source could reach public-health laboratories that lack qPCR.",
    "impact_text": "Scientific: First quantified account of how hospital effluent affects an RPA–Cas12a assay, together with a matrix-aware validity rule that other CRISPR-diagnostic studies can reuse. Clinical & Infection Control: Fast, low-equipment signal for colistin-resistance genes in hospital sewage could prompt earlier review of antibiotic use and isolation practice. Environmental: Routine screening of effluent before discharge would help identify sites that release resistance genes into surface water. Industrial & Economic: A validated, kit-ready workflow that needs only a heat block and a light source could reach public-health laboratories that lack qPCR.",
    "target_audience": "Hospital infection-control teams, municipal wastewater treatment operators, public-health surveillance laboratories, and environmental protection agencies.",
    "customer": "Hospital infection-control and municipal environmental surveillance laboratories",
    "market": "Global environmental antimicrobial resistance surveillance and decentralized diagnostic testing",
    "overarching_aim": "To develop an RPA–Cas12a assay for the colistin-resistance gene mcr-1 and to evaluate its analytical performance and practicality in hospital wastewater against a reference qPCR method.",
    "objectives": [
        {
            "verb": "Design and optimise",
            "text": "an RPA–Cas12a assay targeting a conserved mcr-1 region by selecting the best of three primer pairs and crRNAs and tuning magnesium, temperature, and time (Months 2–4)."
        },
        {
            "verb": "Determine",
            "text": "the 95% limit of detection (LoD) in buffer using synthetic mcr-1 DNA, with a target of 10 copies per reaction or fewer (Months 5–6)."
        },
        {
            "verb": "Evaluate",
            "text": "analytical specificity against mcr-2 to mcr-5 and mcr-1-negative genomic DNA, and repeatability across three days, with a coefficient of variation (CV) of 15% or less (Months 5–6)."
        },
        {
            "verb": "Quantify",
            "text": "the effect of hospital-wastewater extracts on signal and LoD, and identify a dilution that keeps at least 80% of extracts valid by the internal control (Months 5–8)."
        },
        {
            "verb": "Compare",
            "text": "the assay with TaqMan qPCR on 36 paired samples, reporting percent agreement and Cohen’s κ with 95% confidence intervals (Months 8–10)."
        },
        {
            "verb": "Measure",
            "text": "hands-on time, time to result (≤ 100 min), and itemised cost per sample for both methods (Months 10–12)."
        }
    ],
    "aims": {
        "overarching": "To develop an RPA–Cas12a assay for the colistin-resistance gene mcr-1 and to evaluate its analytical performance and practicality in hospital wastewater against a reference qPCR method.",
        "aim1": "Aim 1: Design and optimise an RPA–Cas12a assay targeting a conserved mcr-1 region by selecting the best of three primer pairs and crRNAs and tuning magnesium, temperature, and time (Months 2–4).",
        "aim1_title": "Assay Design & Isothermal Reaction Optimization",
        "aim2": "Aim 2: Determine 95% LoD in buffer (≤ 10 copies/reaction), evaluate analytical specificity against mcr-2 to mcr-5, and quantify wastewater extract matrix effects and IAC validity (Months 5–8).",
        "aim2_title": "Analytical Validation & Matrix Effect Quantification",
        "aim3": "Aim 3: Compare DETECTR-Aqua with TaqMan qPCR on 36 paired hospital wastewater samples (agreement ≥ 90%, Cohen's κ ≥ 0.80), and measure hands-on time, time to result, and itemised cost (Months 8–12).",
        "aim3_title": "Paired qPCR Benchmarking & Practical Evaluation"
    },
    "aims_contingencies": {
        "aim1_fallback": "If kinetic trans-cleavage efficiency of Cas12a is suboptimal (<10-fold signal-to-noise within 20 min), substitute with high-turnover LbCas12a (Lachnospiraceae bacterium) which exhibits 2.5-fold faster trans-cleavage rates at 37°C.",
        "aim2_fallback": "If hospital wastewater extracts exhibit severe matrix suppression or IAC failure, evaluate 1:10 dilution and add PVPP (polyvinylpolypyrrolidone) or 1.5% BSA to scavenge polyphenols and humic acids.",
        "aim3_fallback": "If agreement with qPCR is discordant on specific effluent samples, re-test extracts once with both methods and perform sequencing confirmation to resolve potential false negatives or false positives."
    },
    "control_triad": {
        "negative": "No-template control (NTC, ≥ 6 per plate) containing nuclease-free water, extraction blank per batch, and field blank of sterile water per site visit to confirm absence of contamination.",
        "positive": "1,000 copies synthetic mcr-1 DNA fragment (gBlock) run in every analytical batch to verify complete Cas12a activation and reporter trans-cleavage.",
        "specificity": "Internal amplification control (IAC) synthetic non-mcr DNA run on every extract; specificity panel of mcr-2 to mcr-5 fragments, and mcr-negative E. coli and K. pneumoniae genomic DNA."
    },
    "controls_checklist": {
        "positive": true,
        "negative": true,
        "triplicates": true
    },
    "risks": [
        {
            "risk": "Off-target cleavage of background microbial metagenomic DNA in effluent matrix",
            "level": "Low",
            "fallback": "Bioinformatic BLAST filtering against 1,000+ wastewater metagenomes; select crRNA with ≥3 mismatches."
        },
        {
            "risk": "Extreme humic acid or chemical inhibitor quenching of fluorescence signal",
            "level": "Moderate",
            "fallback": "Implement 1:10 extract dilution and add PVPP/BSA scavengers; evaluate IAC validity rule."
        },
        {
            "risk": "Suboptimal Cas12a trans-cleavage kinetics at 37°C",
            "level": "Moderate",
            "fallback": "Substitute with high-turnover LbCas12a (Lachnospiraceae bacterium ND2006) which yields 2.5-fold faster trans-cleavage."
        },
        {
            "risk": "Biosafety hazard handling hospital effluent samples",
            "level": "Low",
            "fallback": "Standard BSL-2 precautions with PPE, 1% sodium hypochlorite chemical inactivation of all waste; synthetic DNA handled in assays."
        }
    ],
    "methodology": "The project is a method-development and analytical-evaluation study that will run for 12 months in five phases. In Phase 1, we will design primers and crRNAs in silico targeting a conserved mcr-1 region with a TTTV PAM, and optimise RPA (TwistAmp Basic at 37 °C, 20 min) and LbCas12a cleavage (50 nM LbCas12a, 62.5 nM crRNA, 500 nM FAM–quencher reporter). In Phase 2, we will validate detection limit (1, 3, 10, 30, 100, 1,000 copies, 20 replicates each), specificity against mcr-2 to mcr-5, and repeatability across 3 days with synthetic DNA. In Phase 3, we will collect 200 mL grab effluent samples weekly from 3 hospitals (30 samples) and 6 community sewer controls, filter through 0.22 µm membranes, extract DNA via silica-column kits, and quantify matrix effects neat and at 1:10 dilution alongside the internal amplification control (IAC). In Phase 4, 36 paired extracts will be tested in triplicate with DETECTR-Aqua and reference TaqMan qPCR (Chabou et al., 2016) by blinded analysts. In Phase 5, we will analyse data in R using probit regression for LoD, Wilson 95% intervals and Cohen's κ for qPCR concordance, and compute hands-on time and itemised reagent costs.",
    "flowchart_caption": "Figure 1: Workflow of the DETECTR-Aqua study, from in silico assay design (Phase 1) to final data analysis and reporting (Phase 5).",
    "materials_methods": "TwistAmp Basic RPA kits (TwistDx), recombinant LbCas12a enzyme (NEB), synthetic oligonucleotides, crRNAs, and gBlock standards (IDT), 0.22 µm membrane filters, silica-column DNA extraction kits, TaqMan qPCR master mix and probe (Chabou et al., 2016), microplate fluorometer (485/520 nm) and blue-LED transilluminator.",
    "expected_outcomes": "The study is expected to deliver (i) an optimised, documented RPA–Cas12a protocol for mcr-1; (ii) a dataset of analytical performance in buffer and wastewater extracts; (iii) a paired comparison with qPCR on 36 samples; and (iv) measured time and cost per sample. Table 2 links each objective to its measurable result and acceptance criterion. The values are hypotheses grounded in published performance (Gong et al., 2022; Wang et al., 2024), not results.",
    "expected_results_table": [
        {
            "obj": "1",
            "metric": "Working assay",
            "method": "Screen 3 primer pairs and crRNAs",
            "criterion": "Best set chosen by highest signal-to-NTC ratio; no signal in NTC"
        },
        {
            "obj": "2",
            "metric": "95% LoD in buffer",
            "method": "Probit; 6 levels × 20 replicates",
            "criterion": "≤ 10 copies per reaction (published range: 6.25 copies)"
        },
        {
            "obj": "3",
            "metric": "Specificity; repeatability",
            "method": "≥ 8 non-targets; 3 days × 3 levels × 5",
            "criterion": "0 false positives; CV ≤ 15% at ≥ 100 copies"
        },
        {
            "obj": "4",
            "metric": "Matrix effect",
            "method": "Extract vs buffer; IAC",
            "criterion": "LoD95 ≤ 50 copies in extract; ≥ 80% of extracts valid at neat or 1:10"
        },
        {
            "obj": "5",
            "metric": "Agreement with qPCR",
            "method": "36 paired samples; κ, McNemar",
            "criterion": "Overall agreement ≥ 90%; κ ≥ 0.80; discordant samples explained"
        }
    ],
    "expected_outcomes_contingency": "Figure 2. Hypothesised results (illustrative, not experimental data). (A) Fluorescence rises earlier and higher with more target; the no-template control stays below the positivity threshold. (B) Wastewater extract is expected to shift the detection curve to the right relative to buffer. (C) Time to result is expected to be shorter than qPCR mainly because the assay step is shorter; concentration and extraction take the same time in both.\\n\\nIf results differ from these expectations, they remain informative: a large matrix shift would define the extra clean-up needed, and poor agreement with qPCR would show where the assay fails.",
    "ansoff": {
        "penetration": "Hospital infection-control and public-health laboratories already run qPCR on mcr-1. DETECTR-Aqua offers a faster screen for routine effluent checks, with qPCR reserved for confirmation of positives.",
        "mkt_dev": "The same assay could serve wastewater-treatment operators, livestock-farm effluent monitoring, and district laboratories in regions without qPCR.",
        "prod_dev": "Using the same RPA–Cas12a chassis: a multiplex panel adding other priority resistance genes (for example carbapenemase genes) and a lateral-flow readout kit.",
        "diversification": "The platform could be adapted for pathogen detection in drinking water, irrigation water, and food-safety testing under a One Health approach."
    },
    "usps": "1) Matrix-aware validity: the internal amplification control separates true negatives from inhibited samples, reducing false reassurance; 2) Low-instrument workflow: a heat block, a plate reader or blue-LED light source, and pipettes are sufficient with no thermal cycler needed; 3) Speed: target of about 95 minutes from sample to result, roughly 40% shorter than qPCR; 4) Bioinformatically vetted specificity: the crRNA is placed in a conserved mcr-1 region and checked by BLAST against all known variants.",
    "competitor_data": {
        "incumbent_name": "TaqMan Quantitative PCR (qPCR) - Chabou et al. 2016",
        "incumbent_speed": "165 minutes (~2.75 hours including thermocycling)",
        "incumbent_cost": "High per reaction (requires dedicated thermal cycler)",
        "incumbent_metric": "LoD: ~10-50 copies/rxn; Cq ≤ 35 positivity threshold",
        "incumbent_portability": "Laboratory benchtop thermal cycler required",
        "incumbent_safety": "BSL-2 molecular biology containment",
        "emerging_name": "Loop-Mediated Isothermal Amplification (LAMP)",
        "emerging_speed": "60 to 75 minutes at 65 °C",
        "emerging_cost": "Moderate cost",
        "emerging_metric": "Prone to false-positive primer-dimer amplification",
        "emerging_portability": "Requires 65 °C heating block",
        "emerging_safety": "Open-tube carryover contamination risk",
        "proposed_name": "DETECTR-Aqua (RPA–Cas12a Fluorescence Assay)",
        "proposed_speed": "95 minutes sample-to-result (~40% faster than qPCR)",
        "proposed_cost": "Low-instrument cost (heat block + blue-LED reader)",
        "proposed_metric": "LoD95 ≤ 10 copies in buffer, ≤ 50 copies in extract; κ ≥ 0.80",
        "proposed_portability": "Portable 37 °C heat block and blue-LED transilluminator",
        "proposed_safety": "Closed-tube fluorescence read; non-infectious synthetic DNA standards",
        "usp": "First matrix-aware CRISPR assay built for hospital effluent with an internal amplification control (IAC) to prevent false-negative inhibition calls, achieving 95-minute turnaround at 37 °C without thermal cyclers."
    },
    "swot": {
        "s": "Fast, low-equipment workflow (heat block and light source); Internal control distinguishes inhibition from true negatives; crRNA vetted against all known mcr-1 variants; Direct benchmark against qPCR on paired samples; Feasible scope: synthetic DNA, no culture of resistant bacteria.",
        "w": "Small sample set (36) from one region and season; RPA reagents are costly and need cold storage; Detects DNA, not viability or gene expression; Covers mcr-1 only, not other mcr variants; Risk of non-specific RPA background.",
        "o": "Growing interest in wastewater-based AMR surveillance; Extension to multiplex and lateral-flow formats; Use in laboratories without qPCR; Partnerships with hospitals and treatment plants.",
        "t": "qPCR and sequencing keep getting cheaper and more available; Effluent variability may exceed what clean-up can handle; Licensing limits on CRISPR and RPA reagents for commercial use; Currency shifts and import delays for reagents; Hospitals may restrict sampling access.",
        "strengths": "Fast, low-equipment workflow (heat block and light source); Internal control distinguishes inhibition from true negatives; crRNA vetted against all known mcr-1 variants; Direct benchmark against qPCR on paired samples; Feasible scope: synthetic DNA, no culture of resistant bacteria.",
        "weaknesses": "Small sample set (36) from one region and season; RPA reagents are costly and need cold storage; Detects DNA, not viability or gene expression; Covers mcr-1 only, not other mcr variants; Risk of non-specific RPA background.",
        "opportunities": "Growing interest in wastewater-based AMR surveillance; Extension to multiplex and lateral-flow formats; Use in laboratories without qPCR; Partnerships with hospitals and treatment plants.",
        "threats": "qPCR and sequencing keep getting cheaper and more available; Effluent variability may exceed what clean-up can handle; Licensing limits on CRISPR and RPA reagents for commercial use; Currency shifts and import delays for reagents; Hospitals may restrict sampling access."
    },
    "pestel": {
        "political": "National and global AMR action plans favour surveillance, which supports funding and hospital cooperation. Sampling still depends on administrative approval from each hospital and on import rules for reagents.",
        "economic": "Reagents are imported and priced in foreign currency, so exchange-rate changes affect costs. Cheap equipment lowers the barrier to adoption; per-sample cost versus qPCR will be measured, not assumed.",
        "social": "Resistant infections concern clinicians and the public. Wastewater sampling is non-invasive and collects no individual data, but results must be communicated carefully to avoid blaming individual hospitals.",
        "technological": "CRISPR diagnostics are maturing (Kaminski et al., 2021), and portable fluorescence readers are becoming cheaper. Competing qPCR, digital PCR, and sequencing methods are also improving.",
        "environmental": "Untreated or poorly treated effluent can spread resistance genes to surface water (Serwecińska, 2020; Zhu et al., 2017). Rapid screening could guide treatment. The project’s own waste will be chemically inactivated.",
        "legal": "Institutional biosafety approval, hospital permission, and waste-disposal regulations apply. Commercial use of Cas12a and RPA reagents may need licences, and data-sharing terms must be agreed with hospitals."
    },
    "biotech_risk_matrix": {
        "off_target": "Risk: Off-target cleavage of background microbial metagenomic DNA in effluent matrix. Mitigation: Bioinformatic BLAST filtering against 1,000+ wastewater metagenomes; select crRNA with ≥3 mismatches.",
        "toxicity": "Risk: Chemical toxicity of lysis and extraction reagents in waste stream. Mitigation: Neutralize all waste with 1% sodium hypochlorite prior to licensed environmental disposal.",
        "solubility": "Risk: Humic acid and polyphenol fluorescence quenching in raw effluent extracts. Mitigation: Include internal amplification control (IAC); test 1:10 dilution; add PVPP polyphenol scavengers.",
        "biosafety": "Risk: Exposure to hospital wastewater pathogens. Mitigation: Handle under BSL-2 precautions with PPE; filter and chemically inactivate samples; handle only synthetic or extracted DNA during assay runs."
    },
    "fmea": {
        "off_target": "Bioinformatic BLAST filtering against 1,000+ wastewater metagenomes ensures ≥3 mismatches to any known non-target sequence.",
        "toxicity": "Chemical decontamination with 1% sodium hypochlorite inactivates all biological and chemical waste before disposal.",
        "solubility": "Internal amplification control (IAC) and 1:10 extract dilution with PVPP scavengers prevent false-negative fluorescence attenuation.",
        "biosafety": "Strict BSL-2 laboratory procedures, sterile collection PPE, and synthetic DNA standards eliminate exposure to live resistant cultures."
    },
    "time_plan": "1. Literature review, protocol, approvals (Jan–Feb 2027, 8 wks, PI/supervisor) | 2. Procurement and biosafety training (Feb–Mar 2027, 6 wks, Member 2) | 3. In silico design and optimisation (Feb–Apr 2027, 13 wks, PI) | 4. Analytical validation (LoD, specificity, repeatability) (May–Jun 2027, 8 wks, PI/Member 3) | 5. Wastewater sampling and matrix tests (May–Aug 2027, 16 wks, Members 2/3) | 6. Paired qPCR comparison (Aug–Oct 2027, 13 wks, PI/Member 3) | 7. Data analysis, time and cost (Oct–Nov 2027, 8 wks, PI) | 8. Reporting and dissemination (Nov–Dec 2027, 8 wks, All members).",
    "budget": "Total Budget: 208,450 EGP. Equipment (A): 21,000 EGP (Blue-LED transilluminator 12,000, plate-reader access 9,000). Consumables & Reagents (B): 128,500 EGP (LbCas12a 12,000, RPA kits 52,000, Synthetic DNA gBlocks 15,000, Primers/crRNAs/reporter 9,000, Extraction kits 10,000, 0.22 µm filters 6,000, qPCR reagents 11,500, Lab plasticware 8,000, PPE/bleach 5,000). Travel (C): 6,000 EGP (Transport 4,500, Cooler boxes 1,500). Personnel (D): 16,000 EGP (Technician support 16,000). Training & Software (E): 9,000 EGP (Biosafety course 3,000, Statistical software licence 6,000). Other Costs (F): 9,000 EGP (Utilities 4,000, Waste disposal 3,000, Printing 2,000). Contingency (10%): 18,950 EGP.",
    "budget_egp_items": [
        {
            "item": "Blue-LED transilluminator (1 unit)",
            "category": "equipment",
            "qty": 1,
            "unit_cost": 12000,
            "total": 12000
        },
        {
            "item": "Plate-reader access (60 hours)",
            "category": "equipment",
            "qty": 60,
            "unit_cost": 150,
            "total": 9000
        },
        {
            "item": "LbCas12a recombinant enzyme",
            "category": "consumables",
            "qty": 1,
            "unit_cost": 12000,
            "total": 12000
        },
        {
            "item": "TwistAmp Basic RPA kits (96 rxns)",
            "category": "consumables",
            "qty": 8,
            "unit_cost": 6500,
            "total": 52000
        },
        {
            "item": "Synthetic DNA standards (gBlocks)",
            "category": "consumables",
            "qty": 6,
            "unit_cost": 2500,
            "total": 15000
        },
        {
            "item": "Primers, crRNAs, FAM-quencher reporter",
            "category": "consumables",
            "qty": 1,
            "unit_cost": 9000,
            "total": 9000
        },
        {
            "item": "Silica-column DNA extraction kits (100 preps)",
            "category": "consumables",
            "qty": 2,
            "unit_cost": 5000,
            "total": 10000
        },
        {
            "item": "0.22 µm PES membrane filters (100 pk)",
            "category": "consumables",
            "qty": 100,
            "unit_cost": 60,
            "total": 6000
        },
        {
            "item": "TaqMan qPCR comparator reagents",
            "category": "consumables",
            "qty": 1,
            "unit_cost": 11500,
            "total": 11500
        },
        {
            "item": "Sterile bottles, tubes, tips, 96-well plates",
            "category": "consumables",
            "qty": 1,
            "unit_cost": 8000,
            "total": 8000
        },
        {
            "item": "PPE, hypochlorite disinfectant, biohazard bags",
            "category": "consumables",
            "qty": 1,
            "unit_cost": 5000,
            "total": 5000
        },
        {
            "item": "Sample transport to 3 hospitals (10 trips)",
            "category": "travel",
            "qty": 10,
            "unit_cost": 450,
            "total": 4500
        },
        {
            "item": "Cooler boxes and cold-chain ice packs",
            "category": "travel",
            "qty": 1,
            "unit_cost": 1500,
            "total": 1500
        },
        {
            "item": "Laboratory technician support (4 months)",
            "category": "personnel",
            "qty": 4,
            "unit_cost": 4000,
            "total": 16000
        },
        {
            "item": "Biosafety BSL-2 certification course",
            "category": "training",
            "qty": 1,
            "unit_cost": 3000,
            "total": 3000
        },
        {
            "item": "Statistical analysis software licence (1 year)",
            "category": "training",
            "qty": 1,
            "unit_cost": 6000,
            "total": 6000
        },
        {
            "item": "Utilities share (electricity, -20 °C storage)",
            "category": "other",
            "qty": 1,
            "unit_cost": 4000,
            "total": 4000
        },
        {
            "item": "Chemical waste treatment & disposal",
            "category": "other",
            "qty": 1,
            "unit_cost": 3000,
            "total": 3000
        },
        {
            "item": "Dissemination, reports, poster printing",
            "category": "other",
            "qty": 1,
            "unit_cost": 2000,
            "total": 2000
        },
        {
            "item": "Contingency reserve (10%)",
            "category": "other",
            "qty": 1,
            "unit_cost": 18950,
            "total": 18950
        }
    ],
    "references": "1. Chabou, S., Leangapichart, T., Okdah, L., Le Page, S., Hadjadj, L., & Rolain, J.-M. (2016). Real-time quantitative PCR assay with Taqman® probe for rapid detection of MCR-1 plasmid-mediated colistin resistance. New Microbes and New Infections, 13, 71–74. https://doi.org/10.1016/j.nmni.2016.06.017\n2. Chen, J. S., Ma, E., Harrington, L. B., Da Costa, M., Tian, X., Palefsky, J. M., & Doudna, J. A. (2018). CRISPR-Cas12a target binding unleashes indiscriminate single-stranded DNase activity. Science, 360(6387), 436–439. https://doi.org/10.1126/science.aar6245\n3. Dadashi, M., Sameni, F., Bostanshirin, N., Yaslianifard, S., Khosravi-Dehaghi, N., Nasiri, M. J., Goudarzi, M., Hashemi, A., & Hajikhani, B. (2022). Global prevalence and molecular epidemiology of mcr-mediated colistin resistance in Escherichia coli clinical isolates: A systematic review. Journal of Global Antimicrobial Resistance, 29, 444–461. https://doi.org/10.1016/j.jgar.2021.10.022\n4. Gong, L., Jin, Z., Liu, E., Tang, F., Yuan, F., Liang, J., Wang, Y., Liu, X., & Wang, Y. (2022). Highly sensitive and specific detection of mobilized colistin resistance gene mcr-1 by CRISPR-based platform. Microbiology Spectrum, 10(5), e01884-22. https://doi.org/10.1128/spectrum.01884-22\n5. Kaminski, M. M., Abudayyeh, O. O., Gootenberg, J. S., Zhang, F., & Collins, J. J. (2021). CRISPR-based diagnostics. Nature Biomedical Engineering, 5(7), 643–656. https://doi.org/10.1038/s41551-021-00760-6\n6. Lin, M., Yue, H., Tian, T., Xiong, E., Zhu, D., Jiang, Y., & Zhou, X. (2022). Glycerol additive boosts 100-fold sensitivity enhancement for one-pot RPA-CRISPR/Cas12a assay. Analytical Chemistry, 94(23), 8277–8284. https://doi.org/10.1021/acs.analchem.2c00616\n7. Liu, Y.-Y., Wang, Y., Walsh, T. R., Yi, L.-X., Zhang, R., Spencer, J., Doi, Y., Tian, G., Dong, B., Huang, X., Yu, L.-F., Gu, D., Ren, H., Chen, X., Lv, L., He, D., Zhou, H., Liang, Z., Liu, J.-H., & Shen, J. (2016). Emergence of plasmid-mediated colistin resistance mechanism MCR-1 in animals and human beings in China: A microbiological and molecular biological study. The Lancet Infectious Diseases, 16(2), 161–168. https://doi.org/10.1016/S1473-3099(15)00424-7\n8. Osei Sekyere, J., Govinden, U., Bester, L. A., & Essack, S. Y. (2016). Colistin and tigecycline resistance in carbapenemase-producing Gram-negative bacteria: Emerging resistance mechanisms and detection methods. Journal of Applied Microbiology, 121(3), 601–617. https://doi.org/10.1111/jam.13169\n9. Wang, Y., Chen, H., Pan, Q., Wang, J., Jiao, X., & Zhang, Y. (2024). Development and evaluation of rapid and accurate one-tube RPA-CRISPR-Cas12b-based detection of mcr-1 and tet(X4). Applied Microbiology and Biotechnology, 108, Article 345. https://doi.org/10.1007/s00253-024-13191-6\n10. Zhu, Y.-G., Zhao, Y., Li, B., Huang, C.-L., Zhang, S.-Y., Yu, S., Chen, Y.-S., Zhang, T., Gillings, M. R., & Su, J.-Q. (2017). Continental-scale pollution of estuaries with antibiotic resistance genes. Nature Microbiology, 2, 16270. https://doi.org/10.1038/nmicrobiol.2016.270",
    "completed_feedback_items": [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11"
    ],
    "is_locked_for_grading": false,
    "faculty_review": {
        "instructor_name": "BT_301 Faculty Evaluation Board",
        "gpa": 0.5882352941176471,
        "raw_total": 5,
        "standing": "⚠️ Substantial Revisions Needed",
        "criterion_overrides": {},
        "manual_notes": "require revision",
        "action_items": [
            "[AB-01] Address rubric diagnostic code: AB-01",
            "Proposal Title: Review and strengthen scientific rigor against rubric standards.",
            "Structured Abstract: Review and strengthen scientific rigor against rubric standards.",
            "Inverted Funnel & Knowledge Gap: Review and strengthen scientific rigor against rubric standards.",
            "3 Decoupled Aims Non-Contingency: Review and strengthen scientific rigor against rubric standards.",
            "Experimental Controls & Methodology: Review and strengthen scientific rigor against rubric standards.",
            "3-Tier Impact & Deliverables: Review and strengthen scientific rigor against rubric standards.",
            "Competitor Analysis & USP: Review and strengthen scientific rigor against rubric standards.",
            "Biotech FMEA & Risk Mitigation: Review and strengthen scientific rigor against rubric standards.",
            "Peer-Reviewed References Recency: Review and strengthen scientific rigor against rubric standards.",
            "Scientific Nomenclature & Format: Review and strengthen scientific rigor against rubric standards.",
            "require revision"
        ],
        "memo_text": "FACULTY REVIEW & FACILITATION AUDIT MEMO\nProject: \nStudent / Team: Maya\nCourse: BT_301 Introduction to Biotechnology\n=================================================================\n\nRAPID AUDIT NOTES:\n• [AB-01 - Exceeds 250 Words]: Abstract exceeds the strict 250-word ceiling. Edit down concisely to prevent editorial desk rejection.\n\nFACULTY INSTRUCTOR NOTES:\nrequire revision\n",
        "dispatched_at": "Sep 20, 2026 - 11:53"
    }
}
        exemplar["updated_at"] = datetime.datetime.now().isoformat()
        exemplar["updated_at_readable"] = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")
        exemplar["summary"] = calculate_draft_summary(exemplar)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(exemplar, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Also seed demo student drafts ST-2026-01, ST-2026-02, ST-2026-03 if missing
    demo_drafts = [
        {
            "student_id": "ST-2026-01",
            "student_name": "Sara Ahmed",
            "title": "Targeted CAR-T Cell Immunotherapy for Solid Tumor Microenvironments",
            "modality": "Cellular Expression",
            "chassis": "Human Primary T Cells",
            "tool": "Second-Generation CAR-T (scFv-4-1BB-CD3zeta)",
            "target": "Solid Tumor Stroma Antigens",
            "abstract": "Solid tumors exhibit profound immunosuppression that limits conventional CAR-T persistence. This proposal designs logic-gated synthetic circuits to enhance T-cell cytotoxicity against solid malignancies.",
            "aims": {
                "aim1": "Construct logic-gated CAR expression vectors with inducible costimulation.",
                "aim2": "Evaluate tumor penetration and cytotoxicity in 3D spheroid models.",
                "aim3": "Benchmark against wild-type non-transduced T cells in triplicates."
            },
            "methodology": "Primary human T cells will be transduced via lentiviral vectors and expanded with IL-2. Cytotoxicity will be quantified using flow cytometry and real-time impedance assays.",
            "references": "1. June, C. H. et al. (Science 2018). CAR T cell immunotherapy."
        },
        {
            "student_id": "ST-2026-02",
            "student_name": "Zaid Ibrahim",
            "title": "Thermostable Engineered PETase for Municipal Plastic Waste Depolymerization",
            "modality": "Cellular Expression",
            "chassis": "Pseudomonas putida KT2440",
            "tool": "Engineered IsPETase (S121C-D186C Disulfide Variant)",
            "target": "Post-Consumer Polyethylene Terephthalate (PET)",
            "abstract": "Bacterial PETase undergoes thermal unfolding above 45°C, restricting deployment in industrial recycling. This project engineers thermostable disulfide variants expressed in P. putida for continuous biorecycling.",
            "aims": {
                "aim1": "Introduce rational disulfide bridges into IsPETase catalytic cleft.",
                "aim2": "Express recombinant variants in P. putida and purify via Ni-NTA.",
                "aim3": "Quantify depolymerization rate at 65°C using reverse-phase HPLC."
            },
            "methodology": "Mutant constructs will be cloned into pBBR1MCS-2 and expressed in P. putida KT2440. PET film degradation will be monitored by HPLC against wild-type control.",
            "references": "1. Austin, H. P. et al. (PNAS 2018). Characterization and engineering of PETase."
        },
        {
            "student_id": "ST-2026-03",
            "student_name": "Nourhan Mostafa",
            "title": "Microalgal Biofuel Optimization via CRISPR-Mediated Metabolic Flux Redirection",
            "modality": "Cellular Expression",
            "chassis": "Chlamydomonas reinhardtii",
            "tool": "CRISPR-Cas9 Ribonucleoprotein (RNP)",
            "target": "Starch Branching Enzyme Knockout for Lipid Accumulation",
            "abstract": "Diverting photosynthetic carbon from starch to neutral lipid synthesis enhances microalgal biodiesel yields. This study employs DNA-free CRISPR RNPs to target starch synthases without foreign transgene integration.",
            "aims": {
                "aim1": "Deliver Cas9-crRNA RNPs targeting STA6 via electroporation.",
                "aim2": "Screen knockout mutants using iodine staining and PCR.",
                "aim3": "Quantify triacylglycerol (TAG) accumulation via Nile Red fluorescence."
            },
            "methodology": "C. reinhardtii cells will be electroporated with pre-assembled Cas9-gRNA complexes. Neutral lipid production will be measured in nitrogen-depleted culture against parental CC-125.",
            "references": "1. Jinkerson, R. E. et al. (Nat Plants 2018). Microalgal biofuels and genome editing."
        }
    ]

    for d in demo_drafts:
        sid = d["student_id"]
        dp = os.path.join(DRAFTS_DIR, f"{sid}.json")
        if not os.path.exists(dp):
            d["updated_at"] = datetime.datetime.now().isoformat()
            d["updated_at_readable"] = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")
            d["summary"] = calculate_draft_summary(d)
            try:
                with open(dp, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
