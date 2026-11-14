"""
Requirement & Routing Engine for the Trusted Research Workflow Agent.
Evaluates extracted research context against declarative institutional
compliance rules. Generates workflow recommendations rather than final decisions.
"""

from typing import List, Dict, Any
from .models import ResearchContext, RequirementAssessment, FieldStatus


INSTITUTIONAL_COMPLIANCE_RULES = [
    {
        "rule_id": "REQ-ETH-01",
        "category": "ethics",
        "title": "Human Participants & Clinical Materials Review",
        "annex": "Annex A: Human Subjects & Clinical Specimens",
        "trigger_condition": lambda ctx: bool(ctx.human_subjects.value),
        "description": (
            "Research involving human participants, patient records, or clinical specimens "
            "requires formal institutional bioethics committee review to ensure informed consent "
            "and patient confidentiality."
        ),
        "human_action": "Institutional BioEthics Committee (IBC) Reviewer must inspect informed consent or strain repository provenance."
    },
    {
        "rule_id": "REQ-ETH-02",
        "category": "ethics",
        "title": "Vertebrate Animal Care & In Vivo Welfare",
        "annex": "Annex B: Animal Welfare & In Vivo Husbandry",
        "trigger_condition": lambda ctx: bool(ctx.animal_subjects.value),
        "description": (
            "Projects utilizing live vertebrate or invertebrate animal models must comply with "
            "institutional 3R principles (Replacement, Reduction, Refinement) and require animal care committee sign-off."
        ),
        "human_action": "Animal Care & Use Committee (IACUC) must verify humane endpoints, housing, and anesthesia protocols."
    },
    {
        "rule_id": "REQ-BIO-01",
        "category": "biosafety",
        "title": "Recombinant DNA & Genetic Manipulation Oversight",
        "annex": "Annex C: Genetic Modification & Recombinant Vectors",
        "trigger_condition": lambda ctx: bool(ctx.genetic_modification.value or ctx.recombinant_dna.value),
        "description": (
            "Use of engineered plasmids, viral or bacterial vectors, or CRISPR genetic alterations "
            "necessitates institutional biosafety committee (IBC) registration and containment assessment."
        ),
        "human_action": "Institutional Biosafety Officer must confirm vector safety profile and host containment verification."
    },
    {
        "rule_id": "REQ-BIO-02",
        "category": "biosafety",
        "title": "Antimicrobial Resistance Determinants & Pathogen Containment",
        "annex": "Annex C: Biosafety Level 2 Protocol Verification",
        "trigger_condition": lambda ctx: bool(ctx.pathogen_work.value or ctx.antimicrobial_resistance.value),
        "description": (
            "Work with multidrug-resistant isolates (e.g. mcr-1 colistin resistance) or opportunistic "
            "pathogens presents dual-use and laboratory-acquired infection risks requiring minimum BSL-2 precautions."
        ),
        "human_action": "Biosafety Officer must inspect standard operating procedures (SOPs) for biohazard autoclaving and barrier protection."
    },
    {
        "rule_id": "REQ-GOV-01",
        "category": "institutional_governance",
        "title": "Ambiguity & Incomplete Specification Escalation",
        "annex": "Institutional Review Triage Queue",
        "trigger_condition": lambda ctx: len(ctx.uncertainties) > 0 or any(
            getattr(ctx, f).status in [FieldStatus.UNCERTAIN, FieldStatus.REQUIRES_HUMAN_REVIEW, FieldStatus.MISSING] 
            for f in ["human_subjects", "organism_or_chassis", "biosafety_containment"]
            if hasattr(ctx, f)
        ),
        "description": (
            "Proposal context contains ambiguous or unverified regulatory parameters. "
            "Autonomous progression is suspended to route context to human supervisor or request researcher clarification."
        ),
        "human_action": "Academic Advisor or Ethics Coordinator must review flagged ambiguities before proposal advances."
    }
]


def evaluate_institutional_requirements(context: ResearchContext) -> List[RequirementAssessment]:
    """
    Evaluates context against all institutional rules.
    Returns list of RequirementAssessment objects.
    All outputs strictly use non-consequential advisory phrasing ('potentially_relevant').
    """
    assessments = []

    for rule in INSTITUTIONAL_COMPLIANCE_RULES:
        is_triggered = False
        try:
            is_triggered = rule["trigger_condition"](context)
        except Exception:
            is_triggered = False

        if is_triggered:
            # Collate matching evidence
            evidences = []
            if rule["category"] == "ethics" and context.human_subjects.value:
                evidences.append(f"Human subject indicator: '{context.human_subjects.evidence}'")
            if rule["category"] == "ethics" and context.animal_subjects.value:
                evidences.append(f"Animal research indicator: '{context.animal_subjects.evidence}'")
            if rule["category"] == "biosafety" and (context.genetic_modification.value or context.recombinant_dna.value):
                evidences.append(f"Recombinant indicator: '{context.genetic_modification.evidence}'")
            if rule["category"] == "biosafety" and context.antimicrobial_resistance.value:
                evidences.append(f"AMR determinant: '{context.antimicrobial_resistance.evidence}'")
            if rule["rule_id"] == "REQ-GOV-01" and context.uncertainties:
                evidences.append(f"Uncertainties detected: {len(context.uncertainties)} item(s) unverified.")

            evidence_str = "; ".join(evidences) if evidences else "Triggered by proposal keyword classification."

            assessments.append(RequirementAssessment(
                rule_id=rule["rule_id"],
                category=rule["category"],
                title=rule["title"],
                description=rule["description"],
                status="potentially_relevant",
                applicable_annex=rule.get("annex"),
                evidence=evidence_str,
                human_action_required=rule["human_action"]
            ))

    return assessments
