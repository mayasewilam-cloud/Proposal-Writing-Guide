"""
Researcher Clarification Loop for the Trusted Research Workflow Agent.
Generates targeted Socratic clarification prompts when ambiguities or missing
regulatory details are identified. Evaluates researcher answers without ghostwriting.
"""

from typing import List, Dict, Any, Optional
import datetime
import uuid
from .models import ResearchContext, ClarificationQuestion, FieldStatus


def generate_clarification_questions(context: ResearchContext) -> List[ClarificationQuestion]:
    """
    Analyzes uncertainties and missing attributes to generate targeted Socratic questions.
    Ensures questions are respectful, precise, and non-ghostwriting.
    """
    questions: List[ClarificationQuestion] = []

    # 1. Check for clinical material / human subject ambiguity
    if context.human_subjects.value and context.human_subjects.status in [FieldStatus.UNCERTAIN, FieldStatus.REQUIRES_HUMAN_REVIEW]:
        questions.append(ClarificationQuestion(
            question_id="CLAR-HUMAN-01",
            field="human_subjects",
            prompt=(
                "Your methodology specifies testing with clinical isolates/specimens. "
                "To determine your institutional ethics pathway: Are these samples obtained from a verified, "
                "de-identified public strain bank (e.g. ATCC, NCTC) or will they be sourced directly from patient diagnostic swabs/clinical cohorts?"
            ),
            rationale="Clarification needed to establish whether formal patient informed consent (Annex A) is mandatory.",
            context_snippet=context.human_subjects.evidence,
            status="pending"
        ))

    # 2. Check for missing host organism / chassis
    if context.organism_or_chassis.status in [FieldStatus.MISSING, FieldStatus.UNCERTAIN, FieldStatus.REQUIRES_HUMAN_REVIEW]:
        questions.append(ClarificationQuestion(
            question_id="CLAR-CHASSIS-01",
            field="organism_or_chassis",
            prompt=(
                "The proposal does not explicitly declare the biological host organism, expression system, or reaction matrix. "
                "What specific cellular host or acellular diagnostic matrix will you use to execute the experimental plan?"
            ),
            rationale="Essential for determining taxonomic biosafety risk and genetic containment requirements.",
            context_snippet="",
            status="pending"
        ))

    # 3. Check for biosafety containment ambiguity
    if context.pathogen_work.value and ("Potentially Required" in str(context.biosafety_containment.value) or context.biosafety_containment.status in [FieldStatus.INFERRED, FieldStatus.REQUIRES_HUMAN_REVIEW, FieldStatus.UNCERTAIN]):
        questions.append(ClarificationQuestion(
            question_id="CLAR-BIO-01",
            field="biosafety_containment",
            prompt=(
                "Your project involves pathogenic or antimicrobial-resistant bacterial targets (e.g., mcr-1 colistin resistance). "
                "What specific biosafety level (BSL-1 or BSL-2) and primary barrier equipment (e.g., certified Class II biosafety cabinet) will be utilized?"
            ),
            rationale="Verification needed to certify institutional biosafety protocols and prevent accidental laboratory exposure.",
            context_snippet=context.pathogen_work.evidence,
            status="pending"
        ))

    # 4. Check for animal model ambiguity
    if context.animal_subjects.value and not any(term in context.animal_subjects.evidence.lower() for term in ["iacuc", "ethics approved", "guidelines"]):
        questions.append(ClarificationQuestion(
            question_id="CLAR-ANIMAL-01",
            field="animal_subjects",
            prompt=(
                "Your experimental design mentions in vivo testing. "
                "Please specify the animal species, strain, sample size calculation, and whether an institutional animal care protocol has been pre-approved."
            ),
            rationale="Required for institutional animal care committee (Annex B) compliance.",
            context_snippet=context.animal_subjects.evidence,
            status="pending"
        ))

    # 5. Check for incomplete or unverified proposal specification
    if any(u.get("field") == "proposal.specification" for u in context.uncertainties):
        questions.append(ClarificationQuestion(
            question_id="CLAR-GOV-01",
            field="proposal.specification",
            prompt=(
                "The proposal title, abstract, or methodology appears incomplete or contains unverified placeholder content. "
                "Please provide a substantive technical summary of your planned experimental design and methodology."
            ),
            rationale="A complete project specification is mandatory before institutional ethics review can proceed.",
            context_snippet="",
            status="pending"
        ))

    return questions


def apply_researcher_clarification(
    context: ResearchContext,
    question_id: str,
    researcher_answer: str
) -> Tuple[ResearchContext, Dict[str, Any]]:
    """
    Applies a researcher's clarification directly to the context model.
    Does not ghostwrite text into the manuscript. Updates status to CONFIRMED
    and provenance source to researcher.answer[<question_id>].
    """
    answer_clean = researcher_answer.strip()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    answer_src = f"researcher.answer[{question_id}]"
    
    result = {
        "question_id": question_id,
        "accepted": True,
        "updated_field": None,
        "message": "Clarification recorded successfully."
    }

    if question_id == "CLAR-HUMAN-01":
        context.human_subjects.status = FieldStatus.CONFIRMED
        context.human_subjects.source = answer_src
        context.human_subjects.rationale = f"Researcher clarified sample origin: '{answer_clean}'."
        context.human_subjects.evidence = f"Researcher Clarification: {answer_clean}"
        # If researcher explicitly states ATCC / de-identified repo, reduce uncertainty
        if any(repo in answer_clean.lower() for repo in ["atcc", "nctc", "dsmz", "repository", "commercial", "de-identified", "anonymized"]):
            context.human_subjects.value = False
            context.human_subjects.rationale += " Confirmed de-identified repository strain (exempt from patient consent, requires biosafety only)."
        else:
            context.human_subjects.value = True
        
        # Clear uncertainty
        context.uncertainties = [u for u in context.uncertainties if u.get("field") != "human_subjects"]
        result["updated_field"] = "human_subjects"

    elif question_id == "CLAR-CHASSIS-01":
        context.organism_or_chassis.value = answer_clean
        context.organism_or_chassis.status = FieldStatus.CONFIRMED
        context.organism_or_chassis.source = answer_src
        context.organism_or_chassis.confidence = 1.0
        context.organism_or_chassis.evidence = answer_clean
        context.organism_or_chassis.rationale = "Declared by researcher via Socratic clarification response."
        context.uncertainties = [u for u in context.uncertainties if u.get("field") != "organism_or_chassis"]
        result["updated_field"] = "organism_or_chassis"

    elif question_id == "CLAR-BIO-01":
        bsl_val = "BSL-2" if "bsl-2" in answer_clean.lower() or "bsl 2" in answer_clean.lower() else "BSL-1"
        context.biosafety_containment.value = bsl_val
        context.biosafety_containment.status = FieldStatus.CONFIRMED
        context.biosafety_containment.source = answer_src
        context.biosafety_containment.confidence = 1.0
        context.biosafety_containment.evidence = answer_clean
        context.biosafety_containment.rationale = f"Researcher specified containment parameters: '{answer_clean}'."
        context.uncertainties = [u for u in context.uncertainties if u.get("field") != "biosafety_containment"]
        result["updated_field"] = "biosafety_containment"

    elif question_id == "CLAR-ANIMAL-01":
        context.animal_subjects.status = FieldStatus.CONFIRMED
        context.animal_subjects.source = answer_src
        context.animal_subjects.evidence += f" | Clarification: {answer_clean}"
        context.uncertainties = [u for u in context.uncertainties if u.get("field") != "animal_subjects"]
        result["updated_field"] = "animal_subjects"

    else:
        # Generic clarification recording
        context.evidence_log.append({
            "type": "researcher_clarification",
            "question_id": question_id,
            "answer": answer_clean,
            "timestamp": now_iso
        })
        result["updated_field"] = "general_evidence"

    context.last_updated = now_iso
    return context, result
