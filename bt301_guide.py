"""
BT301 Complete Student Guide Engine & Knowledge Provider.
Loads, indexes, searches, and serves the 31-chapter BT301 Course Guide
("From Zero to a Fundable Research Proposal").

Integrates:
- Part A: Foundations (Chapters 1–5)
- Part B: Find & Shape Your Project (Chapters 6–11)
- Part C: Learn to Write (Chapters 12–18)
- Part D: Write the Proposal (Chapters 19–26)
- Part E: Review & Submit (Chapters 27–28)
- Part F: Reference & Templates (Chapters 29–31)
"""

import json
import os
import re
from typing import Dict, List, Any, Optional

_GUIDE_CACHE: Optional[List[Dict[str, Any]]] = None
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bt301_guide.json")


def load_guide_data() -> List[Dict[str, Any]]:
    """Loads and caches the 31-chapter BT301 guide."""
    global _GUIDE_CACHE
    if _GUIDE_CACHE is not None:
        return _GUIDE_CACHE

    path = os.path.abspath(_DATA_PATH)
    if not os.path.exists(path):
        # Fallback to current working directory relative
        alt_path = os.path.join(os.getcwd(), "upload", "data", "bt301_guide.json")
        if os.path.exists(alt_path):
            path = alt_path

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "chapters" in data:
                raw_data = data["chapters"]
            elif isinstance(data, list):
                raw_data = data
            else:
                raw_data = []

            # Enhance each chapter with metadata
            for ch in raw_data:
                content = ch.get("content", "")
                words = content.split()
                ch["word_count"] = len(words)
                ch["char_count"] = len(content)
                # Extract first meaningful goal or summary line
                goal_match = re.search(r'Goal:\s*([^\n\r]+)', content, re.I)
                if goal_match:
                    ch["goal"] = goal_match.group(1).strip()
                elif not ch.get("goal"):
                    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("Chapter")]
                    ch["goal"] = lines[0] if lines else ch.get("title", "")
            _GUIDE_CACHE = raw_data
            return _GUIDE_CACHE

    return []


def get_all_chapters() -> List[Dict[str, Any]]:
    """Returns metadata for all 31 chapters."""
    guide = load_guide_data()
    summary_list = []
    for ch in guide:
        summary_list.append({
            "number": ch.get("number"),
            "title": ch.get("title"),
            "part": ch.get("part"),
            "goal": ch.get("goal", ""),
            "word_count": ch.get("word_count", 0),
            "char_count": ch.get("char_count", 0)
        })
    return summary_list


def get_chapter(number: int) -> Optional[Dict[str, Any]]:
    """Retrieves full text and details for a specific chapter number (1-31)."""
    guide = load_guide_data()
    for ch in guide:
        if ch.get("number") == number:
            return ch
    return None


def get_quick_finder() -> List[Dict[str, Any]]:
    """Returns the 'I'm Stuck' quick reference table from Section 0.3."""
    return [
        {
            "problem": "I don't understand a word in a paper",
            "solution": "Check vocabulary definitions and the full alphabetical glossary.",
            "chapters": [2, 30],
            "action": "open_chapter",
            "icon": "📖"
        },
        {
            "problem": "I don't know how to read a paper",
            "solution": "Follow the 3-pass reading method and critical analysis guide.",
            "chapters": [3],
            "action": "open_chapter",
            "icon": "🔬"
        },
        {
            "problem": "I can't find enough papers",
            "solution": "Use Boolean search strings, MeSH terms, and citation snowballing.",
            "chapters": [7],
            "action": "open_chapter",
            "icon": "🔍"
        },
        {
            "problem": "I don't know how to cite in APA or format my references",
            "solution": "Use the complete APA 7th Edition citation handbook (in-text parenthetical/narrative, 11 source templates A–K, DOI rules, reference managers).",
            "chapters": [5],
            "action": "open_chapter",
            "icon": "📚"
        },
        {
            "problem": "I don't know what topic to choose",
            "solution": "Survey biotechnology sectors, funder priorities, and gap matrices.",
            "chapters": [6, 8, 10],
            "action": "open_chapter",
            "icon": "💡"
        },
        {
            "problem": "I confuse aim / objective / hypothesis",
            "solution": "Follow the Research Funnel: Gap -> Question -> Hypothesis -> Aims -> Objectives.",
            "chapters": [9],
            "action": "open_chapter",
            "icon": "🎯"
        },
        {
            "problem": "My sentences sound vague, weak, or overly certain",
            "solution": "Master scientific sentence structure, precise verbs, and proper hedging.",
            "chapters": [12, 13],
            "action": "open_chapter",
            "icon": "✍️"
        },
        {
            "problem": "My paragraph feels like a disjointed list",
            "solution": "Use topic sentences, logical transitions, and the MEAL structure.",
            "chapters": [15, 16],
            "action": "open_chapter",
            "icon": "🧱"
        },
        {
            "problem": "I don't know what goes in each proposal section",
            "solution": "Follow the 10-section architecture and step-by-step scientific proposal drafting rules.",
            "chapters": [19, 20, 21, 22, 23, 24, 25, 26],
            "action": "open_chapter",
            "icon": "📐"
        },
        {
            "problem": "I want to see a complete worked example",
            "solution": "Read the complete, condensed model proposal with annotated sections.",
            "chapters": [27],
            "action": "open_chapter",
            "icon": "🌟"
        },
        {
            "problem": "I want to audit and check before submitting",
            "solution": "Grade your draft against the official rubric and master 30-item checklist.",
            "chapters": [27, 28],
            "action": "open_chapter",
            "icon": "✅"
        },
        {
            "problem": "I need fill-in templates",
            "solution": "Copy standardized fill-in proposal templates and budget tables.",
            "chapters": [29, 31],
            "action": "open_chapter",
            "icon": "📝"
        }
    ]


def search_guide(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Performs relevance-ranked keyword search across all 29 chapters."""
    if not query or len(query.strip()) < 2:
        return []

    tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]+', query) if len(t) > 2]
    if not tokens:
        return []

    guide = load_guide_data()
    results = []

    for ch in guide:
        num = ch.get("number", 0)
        title = ch.get("title", "")
        part = ch.get("part", "")
        content = ch.get("content", "")
        lower_content = content.lower()
        lower_title = title.lower()

        score = 0
        snippets = []

        # Exact title match bonus
        if query.lower() in lower_title:
            score += 100

        # Token matches in title
        for t in tokens:
            if t in lower_title:
                score += 30

        # Token matches in content
        for t in tokens:
            count = lower_content.count(t)
            score += min(count * 2, 40)

        # Extract best snippet
        if score > 0:
            first_pos = -1
            for t in tokens:
                p = lower_content.find(t)
                if p != -1 and (first_pos == -1 or p < first_pos):
                    first_pos = p

            if first_pos != -1:
                start = max(0, first_pos - 80)
                end = min(len(content), first_pos + 180)
                snip = content[start:end].replace("\n", " ").strip()
                if start > 0:
                    snip = "..." + snip
                if end < len(content):
                    snip = snip + "..."
                snippets.append(snip)

            results.append({
                "number": num,
                "title": title,
                "part": part,
                "goal": ch.get("goal", ""),
                "score": score,
                "snippet": snippets[0] if snippets else (content[:150] + "...")
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def get_sentence_formulation_guide() -> Dict[str, Any]:
    """
    Returns authentic pedagogical coaching for sentence construction
    derived from Chapters 12 and 13 of the BT301 Complete Guide.
    """
    return {
        "title": "BT301 Guide — Chapter 13: Building a Scientific Sentence",
        "core_formula": "Subject (Agent/Tool) + Verb (Precise Action) + Object (Measured Property) + Condition (Matrix/Model)",
        "formula_example": "The Calendula extract (Subject) inhibited (Verb) inflammatory cytokine release (Object) in cultured human dermal fibroblasts (Condition).",
        "key_rules": [
            "1. Put the actor in the subject position (e.g. 'The plant extract...', NOT 'In this study, an evaluation was conducted on...').",
            "2. Choose precise scientific verbs over vague fillers (replace 'deals with' or 'is related to' with 'inhibits', 'catalyzes', 'amplifies', 'downregulates').",
            "3. State the exact biological condition or chassis to prevent overgeneralizing to humans or in vivo contexts.",
            "4. Match verb strength to evidence: use 'suggests' or 'indicates' for preliminary data; reserve 'demonstrates' for confirmed controls."
        ],
        "archetypes": [
            {
                "type": "Problem Sentence (Section 2)",
                "formula": "[Disease / Pathogen / Industrial Bottleneck] causes [quantified harm / cost], yet current [standard methods] suffer from [specific limitation].",
                "example": "Multidrug-resistant Acinetobacter baumannii infections cause over 40% mortality in intensive care units, yet conventional culture-based diagnostics require 48 to 72 hours to report antibiotic susceptibility profiles."
            },
            {
                "type": "Literature Gap Pivot Sentence (Section 2)",
                "formula": "Although [previous studies / authors] demonstrated that [established finding], whether [unresolved variable] can [target effect] under [relevant condition] remains unknown.",
                "example": "Although recent studies demonstrated that ethanolic chamomile extracts exhibit broad-spectrum bactericidal activity in vitro, whether bio-active terpenes retain transdermal stability in topical emulsion formulations remains uncharacterized."
            },
            {
                "type": "Mechanistic Hypothesis Sentence (Section 3)",
                "formula": "We hypothesize that [formulation / tool / extract] will [action verb] [target molecule / pathway] by [biochemical mechanism], thereby [quantified milestone / physiological benchmark].",
                "example": "We hypothesize that an ethosomal nano-emulsion of Calendula officinalis will accelerate dermal wound re-epithelialization by downregulating pro-inflammatory TNF-alpha and IL-6 expression in human epidermal keratinocytes, achieving >75% wound closure within 48 hours."
            },
            {
                "type": "Specific Aim / Objective Sentence (Section 3)",
                "formula": "To [action verb: quantify / optimize / evaluate / characterize] [target parameter] using [analytical method / assay] in order to [success criterion / benchmark].",
                "example": "To determine the minimum inhibitory concentration (MIC) and kill-curve kinetics of the formulated emulsion against S. aureus and P. aeruginosa using standard microdilution broth assays (CLSI M07-A10)."
            },
            {
                "type": "Methodology Protocol Sentence (Section 4 — Future Tense)",
                "formula": "[Sample / Formulation] will be [passive action verb] using [instrument / assay] at [operating parameter] with [positive & negative controls] to [quantified readout].",
                "example": "Triplicate 50 mg emulsion samples will be subjected to automated Franz diffusion cell permeation at 32°C across porcine stratum corneum for 24 hours, with drug flux quantified via reverse-phase HPLC at 254 nm."
            }
        ],
        "verb_matrix": {
            "Define / Explain": ["is defined as", "refers to", "comprises", "involves"],
            "Describe a Mechanism": ["regulates", "mediates", "catalyzes", "transcribes", "downregulates", "upregulates"],
            "Report Previous Work": ["reported", "demonstrated", "observed", "identified", "confirmed"],
            "Compare": ["exceeds", "differs significantly from", "outperforms", "resembles"],
            "Interpret Cautiously (Hedging)": ["suggests", "indicates", "supports the hypothesis that", "is consistent with"],
            "Quantify Effect": ["inhibited by 65%", "accelerated by 2.4-fold", "reduced below the detection limit of 10 pM"]
        },
        "informal_to_academic": [
            ("A lot of studies", "Numerous empirical investigations"),
            ("Scientists found out that", "Prior researchers demonstrated that"),
            ("This proves that", "These findings provide strong evidence that / suggest that"),
            ("Because of the fact that", "Because / Since / Given that"),
            ("We wanted to see if", "This study aims to determine whether"),
            ("The extract did not work", "The extract produced no statistically significant inhibition under the tested conditions (p > 0.05)")
        ]
    }


def get_glossary_terms() -> Dict[str, Dict[str, Any]]:
    """
    Parses and returns all structured glossary terms from Chapter 30 of the guide.
    Maps lowercase terms and aliases to their definition, standard formula, and guide reference.
    """
    ch30 = next((c for c in load_guide_data() if "glossary" in c.get("title", "").lower()), None) or get_chapter(30)
    if not ch30 or "content" not in ch30:
        return {}
    
    terms = {}
    lines = ch30["content"].split("\n")
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2:
            t = parts[0].strip()
            if not t or t == "Term" or t.startswith("Chapter") or t.startswith("30.") or t.startswith("31."):
                continue
            d = parts[1].strip()
            r = parts[2].strip() if len(parts) > 2 else "Chapter 30"
            ch_m = re.search(r'Chapter\s*(\d+)', r)
            ch_num = int(ch_m.group(1)) if ch_m else 30
            
            clean_t = t.lower()
            core_t = re.sub(r'\(.*?\)', '', clean_t).strip()
            slash_parts = [p.strip() for p in core_t.split('/') if p.strip()]
            
            aliases = list(set([clean_t, core_t] + slash_parts))
            if "lod" in clean_t:
                aliases.extend(["lod", "limit of detection"])
            if "anova" in clean_t:
                aliases.extend(["anova", "analysis of variance"])
            if "finer" in clean_t:
                aliases.extend(["finer", "finer framework"])
            
            entry = {
                "term": t,
                "aliases": aliases,
                "definition": d,
                "ref": r,
                "chapter": ch_num
            }
            terms[core_t] = entry
            terms[clean_t] = entry
            for a in aliases:
                terms[a] = entry
    return terms


def get_glossary_term(query: str) -> Optional[Dict[str, Any]]:
    """Matches a term query against all Chapter 30 glossary definitions."""
    if not query:
        return None
    lower = query.lower().strip()
    clean = re.sub(r'^(what\s+is|what\s+are|define|definition\s+of|explain|meaning\s+of|what\s+does|tell\s+me\s+about)\s+(a\s+|an\s+|the\s+)?', '', lower)
    clean = re.sub(r'\s+(mean|means|stand\s+for|definition)\??$', '', clean).strip()
    
    terms = get_glossary_terms()
    if clean in terms:
        return terms[clean]
    
    # Try word-boundary match
    for k, entry in terms.items():
        if len(k) > 2 and re.search(r'\b' + re.escape(k) + r'\b', lower):
            return entry
    return None
