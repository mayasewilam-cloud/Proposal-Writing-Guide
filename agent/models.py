"""
Data Models for the Trusted Research Workflow Agent.
Defines typed representations for Research Context, Requirements,
Clarifications, State Machine States, and Dossiers.
"""

from typing import Dict, List, Any, Optional
import datetime
import uuid


class WorkflowState:
    DRAFT = "DRAFT"
    CONTEXT_ANALYSIS = "CONTEXT_ANALYSIS"
    REQUIREMENT_CHECK = "REQUIREMENT_CHECK"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    READY_FOR_ETHICS_HANDOFF = "READY_FOR_ETHICS_HANDOFF"
    ETHICS_REVIEW_PENDING = "ETHICS_REVIEW_PENDING"
    MOCK_HANDOFF_COMPLETED = "MOCK_HANDOFF_COMPLETED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CLEARED_FOR_NEXT_STAGE = "CLEARED_FOR_NEXT_STAGE"
    RETURNED_FOR_REVISION = "RETURNED_FOR_REVISION"
    ESCALATED = "ESCALATED"

    ALL_STATES = [
        DRAFT,
        CONTEXT_ANALYSIS,
        REQUIREMENT_CHECK,
        NEEDS_CLARIFICATION,
        READY_FOR_ETHICS_HANDOFF,
        ETHICS_REVIEW_PENDING,
        MOCK_HANDOFF_COMPLETED,
        HUMAN_REVIEW,
        CLEARED_FOR_NEXT_STAGE,
        RETURNED_FOR_REVISION,
        ESCALATED
    ]


class FieldStatus:
    CONFIRMED = "CONFIRMED"
    INFERRED = "INFERRED"
    MISSING = "MISSING"
    UNCERTAIN = "UNCERTAIN"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"

    # Compatibility aliases
    IDENTIFIED = "CONFIRMED"
    CONFIRMED_BY_RESEARCHER = "CONFIRMED"


def normalize_field_status(status: str) -> str:
    s = (status or "").strip().upper()
    mapping = {
        "IDENTIFIED": FieldStatus.CONFIRMED,
        "CONFIRMED_BY_RESEARCHER": FieldStatus.CONFIRMED,
        "CONFIRMED": FieldStatus.CONFIRMED,
        "INFERRED": FieldStatus.INFERRED,
        "MISSING": FieldStatus.MISSING,
        "UNCERTAIN": FieldStatus.UNCERTAIN,
        "REQUIRES_HUMAN_REVIEW": FieldStatus.REQUIRES_HUMAN_REVIEW
    }
    return mapping.get(s, FieldStatus.UNCERTAIN)


class FieldEvidence:
    """Represents a specific extracted research attribute with provenance evidence."""
    def __init__(
        self,
        field: str,
        value: Any,
        source: str = "unspecified",
        status: str = FieldStatus.MISSING,
        confidence: float = 0.0,
        evidence: str = "",
        rationale: str = ""
    ):
        self.field = field
        self.value = value
        self.source = source
        self.status = normalize_field_status(status)
        self.confidence = float(confidence)
        self.evidence = evidence
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "status": self.status,
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FieldEvidence":
        return cls(
            field=d.get("field", ""),
            value=d.get("value"),
            source=d.get("source", "unspecified"),
            status=d.get("status", FieldStatus.MISSING),
            confidence=float(d.get("confidence", 0.0)),
            evidence=d.get("evidence", ""),
            rationale=d.get("rationale", "")
        )


class ResearchContext:
    """Structured context extracted from a research proposal without inventing facts."""
    def __init__(
        self,
        project_id: str,
        title: str = "",
        researcher_name: str = "",
        research_area: str = "Biotechnology"
    ):
        self.project_id = project_id
        self.title = title
        self.researcher_name = researcher_name
        self.research_area = research_area
        self.last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Primary research entities
        self.organism_or_chassis: FieldEvidence = FieldEvidence("organism_or_chassis", None)
        self.molecular_tools: List[FieldEvidence] = []
        self.sample_origin: FieldEvidence = FieldEvidence("sample_origin", None)
        self.sample_type: FieldEvidence = FieldEvidence("sample_type", None)
        
        # Regulatory/safety indicators
        self.genetic_modification: FieldEvidence = FieldEvidence("genetic_modification", False)
        self.recombinant_dna: FieldEvidence = FieldEvidence("recombinant_dna", False)
        self.human_subjects: FieldEvidence = FieldEvidence("human_subjects", False)
        self.animal_subjects: FieldEvidence = FieldEvidence("animal_subjects", False)
        self.pathogen_work: FieldEvidence = FieldEvidence("pathogen_work", False)
        self.antimicrobial_resistance: FieldEvidence = FieldEvidence("antimicrobial_resistance", False)
        self.biosafety_containment: FieldEvidence = FieldEvidence("biosafety_containment", "BSL-1")
        
        # Evidence aggregates
        self.evidence_log: List[Dict[str, Any]] = []
        self.uncertainties: List[Dict[str, Any]] = []
        self.proposal_sections: Dict[str, Any] = {}
        self.extraction_mode: str = "deterministic_rules"
        self.llm_available: bool = False
        self.checks_performed: List[str] = []
        self.input_summary: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "researcher_name": self.researcher_name,
            "research_area": self.research_area,
            "last_updated": self.last_updated,
            "extraction_mode": self.extraction_mode,
            "llm_available": self.llm_available,
            "checks_performed": self.checks_performed,
            "input_summary": self.input_summary,
            "organism_or_chassis": self.organism_or_chassis.to_dict(),
            "molecular_tools": [t.to_dict() for t in self.molecular_tools],
            "sample_origin": self.sample_origin.to_dict(),
            "sample_type": self.sample_type.to_dict(),
            "genetic_modification": self.genetic_modification.to_dict(),
            "recombinant_dna": self.recombinant_dna.to_dict(),
            "human_subjects": self.human_subjects.to_dict(),
            "animal_subjects": self.animal_subjects.to_dict(),
            "pathogen_work": self.pathogen_work.to_dict(),
            "antimicrobial_resistance": self.antimicrobial_resistance.to_dict(),
            "biosafety_containment": self.biosafety_containment.to_dict(),
            "evidence_log": self.evidence_log,
            "uncertainties": self.uncertainties,
            "proposal_sections": self.proposal_sections
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchContext":
        ctx = cls(
            project_id=d.get("project_id", "unknown"),
            title=d.get("title", ""),
            researcher_name=d.get("researcher_name", ""),
            research_area=d.get("research_area", "Biotechnology")
        )
        ctx.last_updated = d.get("last_updated", "")
        ctx.extraction_mode = d.get("extraction_mode", "deterministic_rules")
        ctx.llm_available = bool(d.get("llm_available", False))
        ctx.checks_performed = d.get("checks_performed", [])
        ctx.input_summary = d.get("input_summary", {})
        ctx.proposal_sections = d.get("proposal_sections", {})
        if "organism_or_chassis" in d:
            ctx.organism_or_chassis = FieldEvidence.from_dict(d["organism_or_chassis"])
        if "molecular_tools" in d:
            ctx.molecular_tools = [FieldEvidence.from_dict(t) for t in d["molecular_tools"]]
        if "sample_origin" in d:
            ctx.sample_origin = FieldEvidence.from_dict(d["sample_origin"])
        if "sample_type" in d:
            ctx.sample_type = FieldEvidence.from_dict(d["sample_type"])
        if "genetic_modification" in d:
            ctx.genetic_modification = FieldEvidence.from_dict(d["genetic_modification"])
        if "recombinant_dna" in d:
            ctx.recombinant_dna = FieldEvidence.from_dict(d["recombinant_dna"])
        if "human_subjects" in d:
            ctx.human_subjects = FieldEvidence.from_dict(d["human_subjects"])
        if "animal_subjects" in d:
            ctx.animal_subjects = FieldEvidence.from_dict(d["animal_subjects"])
        if "pathogen_work" in d:
            ctx.pathogen_work = FieldEvidence.from_dict(d["pathogen_work"])
        if "antimicrobial_resistance" in d:
            ctx.antimicrobial_resistance = FieldEvidence.from_dict(d["antimicrobial_resistance"])
        if "biosafety_containment" in d:
            ctx.biosafety_containment = FieldEvidence.from_dict(d["biosafety_containment"])
        ctx.evidence_log = d.get("evidence_log", [])
        ctx.uncertainties = d.get("uncertainties", [])
        return ctx


class RequirementAssessment:
    """An institutional requirement or compliance trigger evaluated by the agent."""
    def __init__(
        self,
        rule_id: str,
        category: str,
        title: str,
        description: str,
        status: str = "not_triggered",  # potentially_relevant | advisory | not_triggered
        applicable_annex: Optional[str] = None,
        evidence: str = "",
        human_action_required: str = ""
    ):
        self.rule_id = rule_id
        self.category = category  # ethics | biosafety | institutional_review
        self.title = title
        self.description = description
        self.status = status
        self.applicable_annex = applicable_annex
        self.evidence = evidence
        self.human_action_required = human_action_required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "applicable_annex": self.applicable_annex,
            "evidence": self.evidence,
            "human_action_required": self.human_action_required
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RequirementAssessment":
        return cls(
            rule_id=d.get("rule_id", ""),
            category=d.get("category", "ethics"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            status=d.get("status", "not_triggered"),
            applicable_annex=d.get("applicable_annex"),
            evidence=d.get("evidence", ""),
            human_action_required=d.get("human_action_required", "")
        )


class ClarificationQuestion:
    """A targeted Socratic question posed to the researcher to resolve an ambiguity."""
    def __init__(
        self,
        question_id: str,
        field: str,
        prompt: str,
        rationale: str,
        context_snippet: str = "",
        status: str = "pending",
        researcher_response: Optional[str] = None,
        response_timestamp: Optional[str] = None
    ):
        self.question_id = question_id or str(uuid.uuid4())[:8]
        self.field = field
        self.prompt = prompt
        self.rationale = rationale
        self.context_snippet = context_snippet
        self.status = status  # pending | answered | dismissed
        self.researcher_response = researcher_response
        self.response_timestamp = response_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "field": self.field,
            "prompt": self.prompt,
            "rationale": self.rationale,
            "context_snippet": self.context_snippet,
            "status": self.status,
            "researcher_response": self.researcher_response,
            "response_timestamp": self.response_timestamp
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClarificationQuestion":
        return cls(
            question_id=d.get("question_id", ""),
            field=d.get("field", ""),
            prompt=d.get("prompt", ""),
            rationale=d.get("rationale", ""),
            context_snippet=d.get("context_snippet", ""),
            status=d.get("status", "pending"),
            researcher_response=d.get("researcher_response"),
            response_timestamp=d.get("response_timestamp")
        )
