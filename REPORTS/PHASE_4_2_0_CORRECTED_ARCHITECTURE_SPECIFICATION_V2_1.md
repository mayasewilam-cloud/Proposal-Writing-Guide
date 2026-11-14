# BioWriter Studio — Phase 4.2.0: Corrected Scientific Architecture Specification (V2.1)
## Authoritative Engineering Specification for the Scientific Methodology Intelligence Architecture (Version 2.1)

**Target Project:** `c:\Users\Lenovo\Downloads\Joint Platform\upload`  
**Target Document:** `upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_V2_1.md`  
**Authoritative Input:** `upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_V2.md`  
**Independent Verification Input:** `upload/REPORTS/PHASE_4_2_0_3_V2_INDEPENDENT_SPECIFICATION_VERIFICATION.md`  
**Phase:** Phase 4.2.0.4 — Targeted V2.1 Specification Correction  
**Execution Mode:** DOCUMENTATION-ONLY SPECIFICATION REVISION (Zero Code, Zero Test, Zero Live Data Mutations)  
**Role:** Senior Scientific Software Architect, Biomedical Research Methodologist, Biostatistician, Database Architect, and Data Integrity Auditor  
**Date:** November 14, 2026  
**Status:** AMENDED & ALIGNED SPECIFICATION (Authoritative Baseline for Independent Review)

---

## 1. System Vision, Architectural Principles, and Scientific Scope

### 1.1 Mission
BioWriter Studio's Scientific Methodology Intelligence Architecture transitions the platform from a heuristic keyword-matching tool into an epistemically humble, biostatistically grounded scientific reasoning copilot. The engine extracts, models, audits, and visualizes the causal and methodological architecture of experimental research across biotechnology, molecular pharmacology, synthetic biology, and translational biomedicine.

The system understands:
1. **What researchers investigated:** Research questions, primary hypotheses ($H_1$), null hypotheses ($H_0$), and study archetypes.
2. **What was actually performed:** Experimental systems, interventions (multi-agent formulations, vehicles, routes, durations), and assay protocols.
3. **How comparisons were controlled:** Vehicle controls, sham controls, positive benchmark controls, internal normalizations, and assay interference blanks.
4. **How replication was structured:** Distinguishing biological units from technical replicates and serial measurements to prevent pseudoreplication.
5. **How data were analyzed:** Statistical tests, post-hoc multiplicity corrections, and whether the analytical strategy appropriately reflects the experimental design.
6. **What claims are supported:** Mapping findings and causal claim strengths directly to statistical analyses and grounding evidence in verifiable source text.

### 1.2 Foundational Architectural Principles
1. **Epistemic Humility Over Speculative Completeness:** The platform never manufactures certainty. When an experimental detail, solvent concentration, or statistical model is incompletely reported in source literature or student drafts, the system explicitly reports insufficient data rather than guessing.
2. **Strict Evidence Grounding and Provenance:** Every extracted entity and relationship must be anchored to verifiable source passages. The system enforces zero tolerance for hallucinated quotations (Metric 4a Precision = 1.00).
3. **Assay-Specific and Design-Aware Biostatistical Auditing:** Statistical appropriateness is evaluated against the concrete experimental design (independent units, factorial crossings, serial timepoints) rather than naive sample size rules or universal solvent thresholds.
4. **Decoupled Evaluability and Appropriateness:** Incomplete reporting (epistemic abstention) is mathematically separated from ordinal methodology assessment (appropriate, questionable, inappropriate), preventing selective reporting bias.
5. **Absolute Software and Data Integrity:** All 54 baseline data files in `upload/data/` remain untouched. SQLite serves as the sole authoritative persistence layer with Write-Ahead Logging (WAL) and immutable audit history.

### 1.3 Target Boundaries & Epistemic Humility Disclaimers
- **Educational Guidance, Not Autonomous Grading:** The system generates pedagogical advisories, methodological critiques, and evidence tables. Final assessment and grading remain the sole prerogative of human faculty.
- **Methodological Appropriateness vs. Scientific Truth:** The system evaluates whether reported methods satisfy scientific design standards. It explicitly disclaims determining whether an underlying biological hypothesis is factually true in nature.

---

## 2. Corrected Minimal Viable Ontology (MVO) & Relational Graph Schema

### 2.1 Canonical Relational Architecture Diagram
The Minimal Viable Ontology (MVO) models experimental methodology as a directed, typed, acyclic relational graph grounded in source evidence:

```
+---------------------------------------------------------------------------------------------------------+
|                    CANONICAL METHODOLOGY INTELLIGENCE GRAPH ARCHITECTURE (MVO V2.1)                     |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|                                     +-------------------------------+                                   |
|                                     |       ResearchObjective       |                                   |
|                                     |-------------------------------|                                   |
|                                     | research_question             |                                   |
|                                     | primary_hypothesis_H1         |                                   |
|                                     | null_hypothesis_H0            |                                   |
|                                     | study_archetypes (Multi-label)|                                   |
|                                     +---------------+---------------+                                   |
|                                                     | guides                                            |
|                                                     v                                                   |
|       +-----------------------------+       +-------+-----------------------+                           |
|       |     ExperimentalSystem      |<------|       ExperimentalGroup       |                           |
|       |-----------------------------|       |-------------------------------|                           |
|       | system_id [SYS_xxx]         |       | group_id [GRP_xxx]            |                           |
|       | system_type (In Vitro/Vivo) |       | system_id                     |                           |
|       | model_name, organism        |       | group_label                   |                           |
|       | cell_line, biological_source|       | interventions [Agent/Dose]    |                           |
|       +-----------------------------+       | replication [N, n, unit]      |                           |
|                                             | associated_control_ids        |                           |
|                                             +-------+---------------+-------+                           |
|                                                     | ^             |                                   |
|                          associated_control_ids     | | targets     |                                   |
|                          (Strict Bidirectional)     v |             | compared_group_ids                |
|                                             +-------+-------+       |                                   |
|                                             |  ControlGroup |       |                                   |
|                                             |---------------|       |                                   |
|                                             | control_id    |       |                                   |
|                                             |   [CTRL_xxx]  |       |                                   |
|                                             | control_type  |       |                                   |
|                                             | target_groups |       |                                   |
|                                             | rationale     |       |                                   |
|                                             +---------------+       |                                   |
|                                                                     v                                   |
|  +---------------------------+       +----------------------+       |                                   |
|  |       AssayProtocol       |<------| MeasurementEndpoint  |       |                                   |
|  |---------------------------|       |----------------------|       |                                   |
|  | protocol_id [PROT_xxx]    |       | endpoint_id          |       |                                   |
|  | technique_name            |       |   [END_xxx]          |       |                                   |
|  | detection_platform        |       | protocol_id          |<------+                                   |
|  | critical_parameters       |       | raw_readout          |       |                                   |
|  | interference_control      |       | normalized_metric    |       |                                   |
|  +---------------------------+       | is_repeated_measure  |       |                                   |
|                                      +----------+-----------+       |                                   |
|                                                 | measured_in       |                                   |
|                                                 v                   v                                   |
|                                      +----------+-------------------+-------+                           |
|                                      |          StatisticalAnalysis         |                           |
|                                      |--------------------------------------|                           |
|                                      | analysis_id [STAT_xxx]               |                           |
|                                      | endpoint_id, compared_group_ids      |                           |
|                                      | test_name, post_hoc_correction       |                           |
|                                      | p_value, effect_size, 95% CI         |                           |
|                                      | evaluability (EVALUABLE / INSUFF)    |                           |
|                                      | appropriateness_verdict (Opt[Enum])  |                           |
|                                      +------------------+-------------------+                           |
|                                                         | supports                                      |
|                                                         v                                               |
|                                      +------------------+-------------------+                           |
|                                      |           EvidenceConclusion         |                           |
|                                      |--------------------------------------|                           |
|                                      | conclusion_id [CONCL_xxx]            |                           |
|                                      | finding_statement                    |                           |
|                                      | causal_claim_strength                |                           |
|                                      | supporting_analysis_ids              |                           |
|                                      | stated_limitations                   |                           |
|                                      +--------------------------------------+                           |
+---------------------------------------------------------------------------------------------------------+
```

### 2.2 Formal Pydantic v2 Schema Specification

```python
"""
BioWriter Studio: Corrected Scientific Methodology Schema (Pydantic v2.1)
Authoritative module defining the formal Minimal Viable Ontology (MVO).
Resolves all Phase 4.2.0.3 defects:
- A1: Complete identifier uniqueness across all 7 entity types including conclusions.
- A2: Non-mutating, idempotent, strictly validated bidirectional control-group links.
- A3: Complete referential integrity across all relationships with explicit group typing.
- A4: Safe statistical evaluability; INSUFFICIENT_DATA moved out of ordinal scale.
- A5: Rigorous evidence status constraints and validation rules.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field, model_validator


class FieldEvidenceStatus(str, Enum):
    """Epistemic provenance classification for an extracted field."""
    DIRECTLY_STATED = "DIRECTLY_STATED"
    MULTI_PASSAGE_SYNTHESIS = "MULTI_PASSAGE_SYNTHESIS"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_REPORTED = "NOT_REPORTED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ControlTypeEnum(str, Enum):
    """Standardized functional typology of experimental controls."""
    NEGATIVE_UNTREATED = "NEGATIVE_UNTREATED"
    NEGATIVE_VEHICLE = "NEGATIVE_VEHICLE"
    NEGATIVE_SHAM = "NEGATIVE_SHAM"
    NEGATIVE_GENETIC_SCRAMBLED = "NEGATIVE_GENETIC_SCRAMBLED"
    NEGATIVE_GENETIC_NULL = "NEGATIVE_GENETIC_NULL"
    POSITIVE_BENCHMARK = "POSITIVE_BENCHMARK"
    POSITIVE_MAX_RESPONSE = "POSITIVE_MAX_RESPONSE"
    INTERNAL_NORMALIZATION = "INTERNAL_NORMALIZATION"
    SPECIFICITY_BLANK = "SPECIFICITY_BLANK"
    OTHER = "OTHER"


class SystemTypeEnum(str, Enum):
    """Biological test system classification."""
    IN_VITRO_BIOCHEMICAL = "IN_VITRO_BIOCHEMICAL"
    CELL_CULTURE_IMMORTALIZED = "CELL_CULTURE_IMMORTALIZED"
    CELL_CULTURE_PRIMARY = "CELL_CULTURE_PRIMARY"
    ORGANOID_3D = "ORGANOID_3D"
    IN_VIVO_ANIMAL = "IN_VIVO_ANIMAL"
    EX_VIVO_TISSUE = "EX_VIVO_TISSUE"
    IN_SILICO_COMPUTATIONAL = "IN_SILICO_COMPUTATIONAL"
    CHEMICAL_EXTRACTION = "CHEMICAL_EXTRACTION"
    HUMAN_CLINICAL = "HUMAN_CLINICAL"


class ExperimentalUnitEnum(str, Enum):
    """Physical unit of biological randomization and intervention assignment."""
    WELL = "WELL"
    CULTURE_DISH = "CULTURE_DISH"
    ANIMAL = "ANIMAL"
    CAGE = "CAGE"
    LITTER = "LITTER"
    HUMAN_SUBJECT = "HUMAN_SUBJECT"
    ASSAY_TUBE = "ASSAY_TUBE"
    UNKNOWN = "UNKNOWN"


class EpistemicEvaluabilityEnum(str, Enum):
    """Binary epistemic evaluability status for statistical reporting."""
    EVALUABLE = "EVALUABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AppropriatenessVerdictEnum(str, Enum):
    """Three-point ordinal appropriateness scale conditional on evaluability."""
    APPROPRIATE = "APPROPRIATE"
    QUESTIONABLE = "QUESTIONABLE"
    INAPPROPRIATE = "INAPPROPRIATE"


class FieldEvidence(BaseModel):
    """Grounding provenance record for an extracted field or assertion."""
    field_name: str
    extracted_value: Any
    evidence_status: FieldEvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    verbatim_quote: Optional[str] = None
    section_name: Optional[str] = None
    char_start_offset: Optional[int] = None
    char_end_offset: Optional[int] = None
    source_sentence_indices: List[int] = Field(default_factory=list)
    reasoning_rationale: Optional[str] = None

    @model_validator(mode='after')
    def validate_evidence_status_constraints(self) -> 'FieldEvidence':
        """Enforces mandatory grounding constraints per evidence status category."""
        if self.evidence_status == FieldEvidenceStatus.DIRECTLY_STATED:
            if not self.verbatim_quote or len(self.verbatim_quote.strip()) == 0:
                raise ValueError("DIRECTLY_STATED evidence requires a non-empty verbatim_quote.")
            if self.char_start_offset is None or self.char_end_offset is None:
                raise ValueError("DIRECTLY_STATED evidence requires char_start_offset and char_end_offset.")
            if self.char_start_offset < 0 or self.char_end_offset <= self.char_start_offset:
                raise ValueError("Offsets must satisfy 0 <= char_start_offset < char_end_offset.")

        elif self.evidence_status == FieldEvidenceStatus.MULTI_PASSAGE_SYNTHESIS:
            if len(self.source_sentence_indices) < 2 and not self.reasoning_rationale:
                raise ValueError("MULTI_PASSAGE_SYNTHESIS requires multiple sentence indices and synthesis rationale.")

        elif self.evidence_status in (FieldEvidenceStatus.INFERRED, 
                                      FieldEvidenceStatus.AMBIGUOUS, 
                                      FieldEvidenceStatus.CONFLICTING_EVIDENCE):
            if not self.reasoning_rationale or len(self.reasoning_rationale.strip()) == 0:
                raise ValueError(f"{self.evidence_status} requires an explanatory reasoning_rationale.")

        elif self.evidence_status == FieldEvidenceStatus.NOT_REPORTED:
            if self.verbatim_quote is not None:
                raise ValueError("NOT_REPORTED evidence must not contain a verbatim_quote.")
            if not self.reasoning_rationale:
                raise ValueError("NOT_REPORTED evidence requires search_scope documentation in reasoning_rationale.")

        elif self.evidence_status == FieldEvidenceStatus.NOT_APPLICABLE:
            if not self.reasoning_rationale:
                raise ValueError("NOT_APPLICABLE requires an applicability_rationale in reasoning_rationale.")

        return self


class ReplicationStructure(BaseModel):
    """Replication architecture specifying independent units and pseudoreplication risk."""
    biological_replicates_N: Optional[int] = None
    technical_replicates_n: Optional[int] = None
    experimental_unit: ExperimentalUnitEnum = ExperimentalUnitEnum.UNKNOWN
    is_pseudoreplication_risk: bool = False
    rationale: Optional[str] = None


class AssayInterferenceControl(BaseModel):
    """Optical and chemical interference safeguards for spectrophotometric assays."""
    requires_color_blank: bool = False
    color_blank_performed: bool = False
    turbidity_or_autofluorescence_noted: bool = False
    blank_description: Optional[str] = None


class InterventionComponent(BaseModel):
    """Specification of an administered chemical, biological, or physical agent."""
    agent_name: str
    concentration_or_dose: Optional[str] = None
    vehicle_or_solvent: Optional[str] = None
    administration_route: Optional[str] = None
    exposure_duration: Optional[str] = None


class ResearchObjective(BaseModel):
    """Guiding scientific research question and formal hypotheses."""
    research_question: str
    primary_hypothesis_H1: Optional[str] = None
    null_hypothesis_H0: Optional[str] = None
    study_archetypes: List[str] = Field(default_factory=list)
    evidence: FieldEvidence


class ExperimentalSystem(BaseModel):
    """Biological or physical test system entity."""
    system_id: str  # Format: SYS_xxx
    system_type: SystemTypeEnum
    model_name: str
    organism_or_species: Optional[str] = None
    cell_line_or_strain: Optional[str] = None
    biological_source_details: Optional[str] = None
    evidence: FieldEvidence


class ControlGroup(BaseModel):
    """Explicitly modeled control group entity."""
    control_id: str  # Format: CTRL_xxx
    control_type: ControlTypeEnum
    reagent_or_vehicle: str
    concentration: Optional[str] = None
    target_group_ids: List[str] = Field(default_factory=list)
    control_rationale: str
    evidence: FieldEvidence


class ExperimentalGroup(BaseModel):
    """Treated or observed experimental group."""
    group_id: str  # Format: GRP_xxx
    system_id: str
    group_label: str
    interventions: List[InterventionComponent] = Field(default_factory=list)
    replication: ReplicationStructure
    associated_control_ids: List[str] = Field(default_factory=list)
    evidence: FieldEvidence


class AssayProtocol(BaseModel):
    """Experimental measurement procedure or assay."""
    protocol_id: str  # Format: PROT_xxx
    technique_name: str
    assay_category: str
    target_analyte_or_phenotype: str
    detection_platform: Optional[str] = None
    critical_parameters: Dict[str, str] = Field(default_factory=dict)
    interference_control: AssayInterferenceControl = Field(default_factory=AssayInterferenceControl)
    evidence: FieldEvidence


class MeasurementEndpoint(BaseModel):
    """Quantitative or qualitative readout measured from an assay."""
    endpoint_id: str  # Format: END_xxx
    protocol_id: str
    raw_readout: str
    normalized_metric: str
    units: str
    is_repeated_measure: bool = False
    timepoints: List[str] = Field(default_factory=list)
    evidence: FieldEvidence


class StatisticalAnalysis(BaseModel):
    """Statistical hypothesis test and methodological audit record."""
    analysis_id: str  # Format: STAT_xxx
    endpoint_id: str
    compared_group_ids: List[str]
    test_name: str
    post_hoc_correction: Optional[str] = None
    is_multiplicity_corrected: bool = False
    p_value: Optional[float] = None
    p_value_display: str
    effect_size: Optional[str] = None
    confidence_interval_95: Optional[str] = None
    is_statistically_significant: bool
    evaluability: EpistemicEvaluabilityEnum
    appropriateness_verdict: Optional[AppropriatenessVerdictEnum] = None
    biostatistical_critique: Optional[str] = None
    evidence: FieldEvidence

    @model_validator(mode='after')
    def validate_evaluability_and_appropriateness(self) -> 'StatisticalAnalysis':
        """Enforces decoupled epistemic evaluability and ordinal appropriateness logic."""
        if self.evaluability == EpistemicEvaluabilityEnum.INSUFFICIENT_DATA:
            if self.appropriateness_verdict is not None:
                raise ValueError(
                    "appropriateness_verdict must be None when evaluability is INSUFFICIENT_DATA. "
                    "System must not manufacture ordinal appropriateness on un-evaluable data."
                )
        elif self.evaluability == EpistemicEvaluabilityEnum.EVALUABLE:
            if self.appropriateness_verdict is None:
                raise ValueError(
                    "appropriateness_verdict (APPROPRIATE, QUESTIONABLE, or INAPPROPRIATE) "
                    "must be provided when evaluability is EVALUABLE."
                )
        return self


class EvidenceConclusion(BaseModel):
    """High-level causal claim or scientific conclusion supported by analyses."""
    conclusion_id: str  # Format: CONCL_xxx
    finding_statement: str
    causal_claim_strength: str  # DIRECT_CAUSAL, CORRELATIVE, SPECULATIVE, REFUTED
    supporting_analysis_ids: List[str]
    stated_limitations: List[str] = Field(default_factory=list)
    inferred_methodological_flaws: List[str] = Field(default_factory=list)
    evidence: FieldEvidence


class ScientificMethodologyGraph(BaseModel):
    """Complete authoritative relational graph representing scientific methodology."""
    document_id: str
    title: str
    doi: Optional[str] = None
    objective: ResearchObjective
    systems: List[ExperimentalSystem] = Field(default_factory=list)
    groups: List[ExperimentalGroup] = Field(default_factory=list)
    controls: List[ControlGroup] = Field(default_factory=list)
    protocols: List[AssayProtocol] = Field(default_factory=list)
    endpoints: List[MeasurementEndpoint] = Field(default_factory=list)
    analyses: List[StatisticalAnalysis] = Field(default_factory=list)
    conclusions: List[EvidenceConclusion] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_graph_referential_integrity(self) -> 'ScientificMethodologyGraph':
        """
        Validates canonical graph directionality, global uniqueness of identifiers
        across all 7 entity types, and referential integrity without in-place mutation.
        """
        # Collect sets across ALL 7 entity types (Resolves Defect A1)
        system_ids: Set[str] = {s.system_id for s in self.systems}
        group_ids: Set[str] = {g.group_id for g in self.groups}
        control_ids: Set[str] = {c.control_id for c in self.controls}
        protocol_ids: Set[str] = {p.protocol_id for p in self.protocols}
        endpoint_ids: Set[str] = {e.endpoint_id for e in self.endpoints}
        analysis_ids: Set[str] = {a.analysis_id for a in self.analyses}
        conclusion_ids: Set[str] = {c.conclusion_id for c in self.conclusions}

        # 1. Global uniqueness check across ALL entity types
        all_ids = (
            list(system_ids) + list(group_ids) + list(control_ids) +
            list(protocol_ids) + list(endpoint_ids) + list(analysis_ids) +
            list(conclusion_ids)
        )
        if len(all_ids) != len(set(all_ids)):
            seen = set()
            duplicates = {x for x in all_ids if x in seen or seen.add(x)}
            raise ValueError(f"Duplicate entity identifiers detected in methodology graph: {duplicates}")

        # 2. Strict bidirectional validation between Groups and Controls (Resolves Defect A2)
        # Both sides must agree prior to validation; NO IN-PLACE MUTATION.
        group_map = {g.group_id: g for g in self.groups}
        control_map = {c.control_id: c for c in self.controls}

        for c in self.controls:
            for g_id in c.target_group_ids:
                if g_id not in group_map:
                    raise ValueError(f"Control '{c.control_id}' targets non-existent group_id '{g_id}'.")
                matching_group = group_map[g_id]
                if c.control_id not in matching_group.associated_control_ids:
                    raise ValueError(
                        f"Bidirectional mismatch: Control '{c.control_id}' targets Group '{g_id}', "
                        f"but Group '{g_id}' does not list '{c.control_id}' in associated_control_ids."
                    )

        for g in self.groups:
            if g.system_id not in system_ids:
                raise ValueError(f"Group '{g.group_id}' references unknown system_id '{g.system_id}'.")
            for c_id in g.associated_control_ids:
                if c_id not in control_map:
                    raise ValueError(f"Group '{g.group_id}' references non-existent control_id '{c_id}'.")
                matching_control = control_map[c_id]
                if g.group_id not in matching_control.target_group_ids:
                    raise ValueError(
                        f"Bidirectional mismatch: Group '{g.group_id}' lists Control '{c_id}', "
                        f"but Control '{c_id}' does not list '{g.group_id}' in target_group_ids."
                    )

        # 3. MeasurementEndpoint foreign keys
        for ep in self.endpoints:
            if ep.protocol_id not in protocol_ids:
                raise ValueError(f"Endpoint '{ep.endpoint_id}' references unknown protocol_id '{ep.protocol_id}'.")

        # 4. StatisticalAnalysis foreign keys and compared group validation (Resolves Defect A3)
        valid_sample_sources = group_ids.union(control_ids)
        for an in self.analyses:
            if an.endpoint_id not in endpoint_ids:
                raise ValueError(f"Analysis '{an.analysis_id}' references unknown endpoint_id '{an.endpoint_id}'.")
            if len(an.compared_group_ids) < 2:
                raise ValueError(
                    f"Analysis '{an.analysis_id}' must specify at least 2 compared groups or controls. "
                    f"Received: {an.compared_group_ids}"
                )
            for g_id in an.compared_group_ids:
                if g_id not in valid_sample_sources:
                    raise ValueError(f"Analysis '{an.analysis_id}' compares unknown group/control ID '{g_id}'.")

        # 5. EvidenceConclusion foreign keys
        for conc in self.conclusions:
            if not conc.supporting_analysis_ids:
                raise ValueError(f"Conclusion '{conc.conclusion_id}' must reference at least one supporting_analysis_id.")
            for a_id in conc.supporting_analysis_ids:
                if a_id not in analysis_ids:
                    raise ValueError(f"Conclusion '{conc.conclusion_id}' references unknown analysis_id '{a_id}'.")

        return self
```

### 2.3 Identifier Namespaces and Upstream Relationship Construction
To ensure unambiguous serialization, debugging, and human readability, the following standardized prefix namespaces are required across all methodology graph entities:

```
+---------------------------------------------------------------------------------------------------------+
|                                  IDENTIFIER NAMESPACE SPECIFICATION                                     |
+--------------------------+--------------------+---------------------+-----------------------------------+
| Entity Type              | Prefix Pattern     | Example             | Scope & Uniqueness Rule           |
+--------------------------+--------------------+---------------------+-----------------------------------+
| ExperimentalSystem       | SYS_[0-9]{3,}      | SYS_001             | Globally unique across document   |
| ExperimentalGroup        | GRP_[0-9]{3,}      | GRP_001             | Globally unique across document   |
| ControlGroup             | CTRL_[0-9]{3,}     | CTRL_001            | Globally unique across document   |
| AssayProtocol            | PROT_[0-9]{3,}     | PROT_001            | Globally unique across document   |
| MeasurementEndpoint      | END_[0-9]{3,}      | END_001             | Globally unique across document   |
| StatisticalAnalysis      | STAT_[0-9]{3,}     | STAT_001            | Globally unique across document   |
| EvidenceConclusion       | CONCL_[0-9]{3,}    | CONCL_001           | Globally unique across document   |
+--------------------------+--------------------+---------------------+-----------------------------------+
```

**Upstream Relationship Construction Protocol:**  
In Pass 3 (Entity and Relation Extraction), candidate relationships between experimental groups and controls are extracted as directed pairing tuples: `(group_id, control_id, rationale)`. Before instantiating `ScientificMethodologyGraph`, the pipeline builder:
1. Populates `ControlGroup.target_group_ids` with all target group IDs for that control.
2. Synchronously populates `ExperimentalGroup.associated_control_ids` with all associated control IDs for that group.
3. If an extraction pass detects an un-reciprocated link, it flags the relation for heuristic reconciliation or human review *prior* to graph instantiation. The Pydantic model validator acts as an immutable integrity barrier, strictly rejecting any mismatched state.

---
## 3. Evidence Grounding, Text Normalization, and Semantic Verification

### 3.1 Four-Pass Text Normalization Pipeline & Offset Alignment Vector
Textual evidence in scientific manuscripts undergoes complex typographic transformations, typesetting artifacts, and entity encodings. To ensure mathematically rigorous grounding, the platform establishes a strict coordinate taxonomy and an invertible normalization alignment pipeline:

```
+---------------------------------------------------------------------------------------------------------+
|                                    COORDINATE SYSTEM DEFINITION                                         |
+--------------------------+------------------------------------------------------------------------------+
| Coordinate Concept       | Mathematical Definition & Operational Semantics                              |
+--------------------------+------------------------------------------------------------------------------+
| Raw Document Coordinates | 0-based, half-open [start, end) Unicode code points in the un-normalized     |
|                          | full-text manuscript string (S_raw). Exactly corresponds to source text.     |
+--------------------------+------------------------------------------------------------------------------+
| Normalized Coordinates   | 0-based, half-open [start, end) index positions in the clean, processed text |
|                          | string (S_norm) utilized for LLM prompt context and lexical matching.        |
+--------------------------+------------------------------------------------------------------------------+
| UTF-8 Byte Offsets       | Storage-level byte indices. Explicitly rejected for entity coordinates       |
|                          | because multi-byte UTF-8 sequences (e.g., Greek characters, ligatures)      |
|                          | desynchronize character slicing in Python (which indexes by code point).     |
+--------------------------+------------------------------------------------------------------------------+
```

#### Four-Pass Normalization and Alignment Vector Construction:
For an input raw document string $S_{	ext{raw}}$ of length $L_{	ext{raw}}$, the pipeline constructs a normalized string $S_{	ext{norm}}$ of length $L_{	ext{norm}}$ alongside a monotonic **Offset Alignment Vector** $A \in \mathbb{N}^{L_{	ext{norm}}}$ such that the character at $S_{	ext{norm}}[i]$ originates at $S_{	ext{raw}}[A[i]]$:

1. **Pass 1: Unicode NFKC Decomposition:**  
   Decomposes typographic ligatures (`ﬁ` $	o$ `fi`, `ﬂ` $	o$ `fl`, `ﬀ` $	o$ `ff`, `ﬃ` $	o$ `ffi`) and standardizes superscripts/subscripts. NFKC compatibility normalization expands single code points into multi-character sequences, updating $A$ by mapping each expanded character back to the original ligature's code point.
2. **Pass 2: XML/HTML Entity Unescaping:**  
   Decodes standardized markup entities (`&amp;` $	o$ `&`, `&lt;` $	o$ `<`, `&gt;` $	o$ `>`, `&#945;` $	o$ `α`). Contractions map the replacement character to the initial `&` offset in $S_{	ext{raw}}$.
3. **Pass 3: Hyphenation and Line-Break Reassembly:**  
   Detects word breaks across line breaks (e.g. `anti-
inflammatory` $	o$ `anti-inflammatory`). The hyphen and newline characters are excised, and indices for subsequent characters in the token maintain their corresponding raw coordinates.
4. **Pass 4: Whitespace Canonicalization and Coordinate Inversion:**  
   Collapses consecutive whitespace characters (tabs, non-breaking spaces, repeated spaces) into a single standard space ` `.

```python
def compute_normalized_alignment(raw_text: str) -> Tuple[str, List[int]]:
    """
    Constructs normalized text and an exact code-point alignment vector.
    A[i] yields the exact code-point index in raw_text corresponding to normalized_text[i].
    """
    import unicodedata, html, re

    # Step 1: NFKC with tracking
    # Each character in raw_text is mapped
    norm_chars = []
    alignment = []
    
    for raw_idx, char in enumerate(raw_text):
        decomp = unicodedata.normalize('NFKC', char)
        for d in decomp:
            norm_chars.append(d)
            alignment.append(raw_idx)
            
    # Step 2: Entity unescaping and whitespace canonicalization
    # Updates alignment vector monotonically...
    return "".join(norm_chars), alignment
```

*Strict Coordinate Abstention Policy:*  
Surfaced verbatim quotes stored in `FieldEvidence` MUST record `char_start_offset` and `char_end_offset` in **raw document coordinates** (0-based, half-open interval). If an extracted assertion spans non-contiguous sentences, broken tables, or discontinuous passages where alignment inversion is ambiguous, the engine **must abstain** from asserting exact character offsets, setting offsets to `None` and recording `evidence_status = MULTI_PASSAGE_SYNTHESIS` with `source_sentence_indices`.

---

### 3.2 Four-Tier Evidence Verification & Grounding Hierarchy
To reconcile approximate retrieval with zero-hallucination production gates (Metric 4a), the platform establishes a four-tier evidence verification hierarchy:

```
+---------------------------------------------------------------------------------------------------------+
|                               FOUR-TIER EVIDENCE GROUNDING HIERARCHY                                    |
+-------+--------------------------+-------------------------------------+--------------------------------+
| Tier  | Verification Level       | Operational Check                   | Gate Threshold & Action        |
+-------+--------------------------+-------------------------------------+--------------------------------+
| Tier 1| Approximate Candidate    | Heuristic fuzzy retrieval (token    | Levenshtein >= 0.85 window;    |
|       | Retrieval                | overlap, BM25, Levenshtein ratio).  | Identifies candidate passage.  |
+-------+--------------------------+-------------------------------------+--------------------------------+
| Tier 2| Normalized Text          | Exact substring presence in         | Exact Equality (1.00);         |
|       | Equivalence              | normalized text string S_norm.      | Rejects hallucinated text.     |
+-------+--------------------------+-------------------------------------+--------------------------------+
| Tier 3| Exact Source Quotation   | Exact code-point slice in raw text  | Precision = 1.00 (Metric 4a);  |
|       | Grounding Gate           | via alignment vector A.             | Mandatory UI display barrier.  |
+-------+--------------------------+-------------------------------------+--------------------------------+
| Tier 4| Semantic Entailment &    | Explicit semantic verification of   | Polarity match required;       |
|       | Polarity Verification    | negation, tense, and modality.      | Flag for human review if weak. |
+-------+--------------------------+-------------------------------------+--------------------------------+
```

#### Detailed Tier 4 Semantic Verification Checks:
1. **Grammatical Negation Detection:** Identifies explicit negation markers (`"did not"`, `"neither"`, `"without"`, `"failed to"`, `"no significant difference"`, `"was omitted"`). A quote stating *"we did not observe inhibition with vehicle alone"* cannot be cited as evidence that vehicle caused inhibition.
2. **Tense and Modality Verification:** Distinguishes completed empirical execution (`"we treated"`, `"cells were incubated"`, `"was measured"`) from speculative, aspirational, or future work (`"will be tested"`, `"is proposed to"`, `"remains to be elucidated"`, `"we hypothesize"`). Future-work statements are strictly prohibited from populating empirical intervention nodes.
3. **Intervention Exclusion Checking:** Verifies that a compound was actively administered in the described experiment, rather than mentioned as prior literature, an excluded candidate, or an untested analog.
4. **Numerical and Unit Consistency:** Validates that extracted quantitative dosages ($10\ \mu	ext{M}$ vs $10\ 	ext{mg/kg}$) and durations ($24\ 	ext{h}$ vs $24\ 	ext{min}$) strictly match the grounded passage.
5. **Biological Entity Matching:** Ensures that the quoted text refers to the specific experimental system under evaluation (e.g. distinguishing findings in murine BV-2 microglia from primary human macrophages).

*Conservative Abstention Barrier:*  
Passing Tiers 1–3 confirms lexical presence but does NOT prove semantic entailment. If Tier 4 semantic analysis yields ambiguity, conflicting polarity, or uncertain modality, the automated advisory is **suppressed**, and the entity is marked `evidence_status = AMBIGUOUS` with a mandatory human faculty review badge.

---

## 4. Biostatistical and Experimental Design Safety Rules

The biostatistical reasoning engine evaluates experimental validity across six core cases, incorporating contextuality, assay specificity, and explicit abstention:

```
+---------------------------------------------------------------------------------------------------------+
|                             REASSESSED BIOSTATISTICAL SAFETY RULES (CASES A - F)                        |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case   | Biological Topic       | Trigger Condition     | Suppression Condition | Automated Advisory    |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case A | Biological vs.         | Treating replicate    | Physical biological   | HIGH WARNING:         |
|        | Technical Replication  | wells/dishes from a   | independence verified | "Treating wells from a|
|        | (Pseudoreplication)    | single culture thaw or| (independent donor,   | single thaw/culture as|
|        |                        | serial passages as N. | separate animal, or   | N is pseudoreplication.|
|        |                        |                       | distinct thawed vial).| N must reflect unit." |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case B | Solvent / Vehicle      | Case B.1 (>= 0.05%):  | Contextual sensitivity| Case B.1: WARNING     |
|        | Control Concentration  | Solvent >= 0.05% v/v  | screening passed;     | Case B.2: HEURISTIC   |
|        | Matching (Contextual   | without matched vehicle| vehicle matched;      | SCREENING ADVISORY    |
|        | Screening Triggers)    | Case B.2 (< 0.05%):   | solvent identity and  | Case B.3: INSUFFICIENT|
|        |                        | Sensitivity check.    | cell line documented. | DATA ADVISORY         |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case C | Spectrophotometric     | C.1: MTT (570nm)      | Explicit cell-free    | ADVISORY:             |
|        | Interference (Assay-   | extract color blank   | extract background OD | "Plant extracts absorb|
|        | Specific Interference  | omitted.              | subtraction reported  | at 540/570nm; missing |
|        | Risk Assessment)       | C.2: Griess (540nm)   | for specific assay    | blank is an omission  |
|        |                        | extract blank omitted.| wavelength.           | risk, not proof."     |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case D | Multiplicity, Factorial| D.1: Unpaired t-tests | D.1: Dunnett/Tukey    | ADVISORY:             |
|        | Crossing, and Dose-    | on >2 treatment doses.| post-hoc specified.   | "Repeated t-tests     |
|        | Response Structure     | D.2: Factorial crossing| D.2: Two-Way ANOVA   | inflate Type I error; |
|        | (Beyond Naive Dunnett) | analyzed via 1-Way.   | interaction evaluated.| select test based on  |
|        |                        | D.3: Ordered trend.   | D.3: Trend/IC50 curve.| design and contrasts."|
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case E | Serial Measurements    | Repeated observations | Mixed-effects model or| WARNING:              |
|        | (Temporal Non-         | over time analyzed by | repeated-measures     | "Serial timepoints    |
|        | Independence)          | standard factorial    | ANOVA specified with  | violate independence; |
|        |                        | ANOVA.                | autoregressive cov.   | model serial corr."   |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case F | Sample Size Rigor      | N=3 claimed in high-  | Formal a priori power | ADVISORY:             |
|        | ("N=3" Fallacy)        | variability in vivo   | calculation reported  | "N=3 does not prove   |
|        |                        | animal or clinical set| (alpha, beta, delta); | adequate power; eval  |
|        |                        | without power calc.   | unit of random. clear.| unit and effect size."|
+--------+------------------------+-----------------------+-----------------------+-----------------------+
```

### 4.1 Detailed Biostatistical Rationale and Corrections

#### Case A: Cell Culture Replication and Pseudoreplication (Resolves Defect G1)
In vitro cell culture experiments frequently commit **simple pseudoreplication** (Hurlbert, 1984) by treating multiple wells on a microplate or serial passages of a continuous cell line as independent biological replicates ($N$).
- **The Passaging Fallacy Corrected:** Merely culturing cells across $\ge 3$ passage days does **NOT** establish biological independence. Passages $P_{12}, P_{13}, P_{14}$ derived from the same cryopreserved vial share identical genetic drift, epigenetic adaptations, and culture history.
- **Mandatory Independence Criteria:** To claim an independent biological replicate ($N \ge 1$), the experimental unit must originate from:
  1. An independent primary tissue isolation or separate donor animal.
  2. Distinct, independently cryopreserved master vials thawed on separate dates and prepared in distinct media lots.
  3. Independent bacterial or yeast transformation/colony isolates.
- **Automated Advisory Rule:** If an author or student proposal states $N=3$ but reports only replicate wells from a single thawed culture, the engine raises a High Pseudoreplication Warning, clarifying that well-to-well variations represent technical replication ($n$), not biological sample size ($N$).

#### Case B: Contextual Solvent Concentration Screening (Resolves Defect G2)
Concentrations of $0.01\%$ and $0.05\%$ (v/v) must **never** be cited as universal biological constants. The biological impact of a vehicle depends entirely on chemical structure and biological test system:
- **Solvent Chemistry:** DMSO ($0.05\%$) may disrupt neuronal membrane fluidity and alter differentiation in stem cells, whereas water-miscible polyethylene glycol (PEG-400) or low-concentration ethanol ($0.01\%$) exhibit different toxicity profiles.
- **Cell System Sensitivity:** Primary cortical neurons, embryonic stem cells, and electrophysiological preparations are vulnerable to solvent concentrations ($< 0.01\%$) that are well-tolerated by immortalized cancer cell lines (HeLa, HEK293).
- **Heuristic Screening Implementation:**
  - Values of $0.05\%$ and $0.01\%$ serve strictly as **configurable heuristic screening triggers**, not universal safety guarantees.
  - If solvent is $\ge 0.05\%$, emit warning: *"Vehicle concentration is $\ge 0.05\%$; an explicit vehicle-matched control is mandatory to rule out solvent-induced artifacts."*
  - If solvent is between $0.01\%$ and $0.05\%$, emit contextual advisory: *"Solvent concentration ($0.01\%	ext{--}0.05\%$) requires vehicle matching depending on cell type sensitivity."*
  - If solvent details are omitted, emit: *"Insufficient solvent reporting to evaluate vehicle control adequacy."* The engine never assumes safety in the absence of evidence.

#### Case C: Spectrophotometric Assay Interferences (MTT vs. Griess)
- **MTT Assay (570 nm):** Plant extracts rich in polyphenols (flavonoids, anthocyanins, tannins) or reducing agents directly reduce tetrazolium salts to formazan in a **cell-free environment**, producing false-positive viability signals. An extract color blank (extract + medium without cells) is an essential control. A missing blank is flagged as an *interference risk*, not definitive proof of assay failure.
- **Griess Assay (540 nm):** Measures nitrite ($	ext{NO}_2^-$) from nitric oxide production. Phenol red in culture media and pigmented botanical extracts absorb strongly at $540\ 	ext{nm}$. A specific cell-free media blank is required to prevent inflated nitric oxide claims.

#### Case D: Multiplicity, Factorial Crossing, and Dose-Response Structure
Statistical test selection must reflect the structural experimental design:
- **Multiplicity:** Running multiple unpaired Student's $t$-tests across 4 treatment groups compounds family-wise error rate ($lpha_{	ext{FWER}} = 1 - (1 - 0.05)^6 pprox 0.26$). Dunnett's test is required for comparing multiple treatments against a single control; Tukey's HSD is required for all pairwise comparisons.
- **Factorial Crossing:** A $2 	imes 2$ factorial experiment (e.g. Compound A $\pm$ Compound B) must be analyzed using **Two-Way ANOVA with an interaction term** ($A 	imes B$). Splitting the design into two separate One-Way ANOVAs masks synergistic or antagonistic interactions.
- **Dose-Response Trends:** Ordered concentration gradients should be evaluated using monotonic trend tests (Williams' test, Jonckheere-Terpstra) or non-linear sigmoidal curve fitting ($E_{\max}$ / $	ext{IC}_{50}$) rather than unconstrained pairwise comparisons.

#### Case E: Serial Measurements and Temporal Autocorrelation
Measuring the same biological subject (e.g. tumor volume in a mouse, optical density in a well) across multiple timepoints violates the assumption of observation independence. Standard Factorial ANOVA produces severely deflated $p$-values. The engine requires:
- Repeated-measures ANOVA with sphericity testing (Mauchly's test with Greenhouse-Geisser correction) or linear mixed-effects modeling with an autoregressive ($AR(1)$) within-subject covariance structure.

#### Case F: Sample Size Rigor and Power Realism
$N=3$ must neither be declared automatically invalid nor accepted as universally sufficient:
- In biochemical enzymatic assays with high signal-to-noise ratios, $N=3$ technical preparations may provide adequate precision.
- In animal behavioral studies or heterogeneous primary human samples, $N=3$ yields catastrophic statistical power ($\le 20\%$) for detecting moderate effect sizes ($d = 0.5$), resulting in high false-discovery rates (Ioannidis, 2005).
- The engine flags $N=3$ in animal/clinical contexts with an advisory: *"Sample size $N=3$ has limited power to detect realistic effect sizes; evaluate statistical power and define true independent units."*

### 4.2 Epistemic Humility Fallback Rule
When an extracted paper or student proposal omits essential experimental details, the engine **must not guess or manufacture certainty**. It outputs:
> `"Insufficient methodological information reported to assess statistical appropriateness or control completeness."`

---
## 5. Leakage-Resistant Benchmark Partitions & Protocol

### 5.1 Benchmark Partition Allocation & Pilot Separation (Resolves Defect D4)
To prevent data contamination, circular optimization, and uncalibrated performance claims, the platform establishes an un-contaminated **105-paper corpus architecture** partitioned into four disjoint cohorts:

```
+---------------------------------------------------------------------------------------------------------+
|                               BENCHMARK PARTITION & ACCESS GOVERNANCE                                   |
+--------------------------+----------+---------------------------------+---------------------------------+
| Partition Name           | Size     | Permitted Usage Scope           | Access Control & Safeguards     |
+--------------------------+----------+---------------------------------+---------------------------------+
| 0. Pilot Cohort          | 5 Papers | Annotation guideline validation,| Disjoint from all 100 benchmark |
|                          |          | inter-annotator training.       | papers. Fully isolated.         |
+--------------------------+----------+---------------------------------+---------------------------------+
| 1. Development Partition | 30 Papers| Few-shot prompt engineering,    | Open access to engineering team.|
|                          |          | regex refinement, error triage, | All model and rule refinement   |
|                          |          | 5-fold cross-validation.        | confined strictly here.         |
+--------------------------+----------+---------------------------------+---------------------------------+
| 2. Calibration Partition | 20 Papers| Fitting empirical probability   | Disjoint from dev and holdout.  |
|                          |          | calibration models (Platt).     | Accessible only at calibration. |
+--------------------------+----------+---------------------------------+---------------------------------+
| 3. Blind Holdout         | 50 Papers| Final release gate verification | STRICTLY LOCKED under SHA-256   |
|    Partition             |          | across all quantitative metrics.| hash manifest and OS escrow.    |
|                          |          | Single-pass evaluation only.    | Opened ONLY at Stage 6 release. |
+--------------------------+----------+---------------------------------+---------------------------------+
```

### 5.2 Mandatory Anti-Leakage Safeguards
1. **Cluster-Aware Grouping:** Preprints, journal articles, companion papers, and studies originating from the same research laboratory, author group, or institutional consortium are clustered into the **same partition** to prevent cross-partition lexical or methodological leakage.
2. **Access Governance and Cryptographic Escrow:** The Blind Holdout partition is managed by the Independent Software Quality Officer. The holdout is locked in a filesystem-restricted directory with a SHA-256 integrity manifest. It is unlocked only after Stage 5 integration passes, running in a single-pass unattended batch.
3. **Domain Quota Enforcement:** Across all three partitions, the 4 biological subdomains must maintain equal proportional representation:
   - Development (30): ~7–8 papers per domain.
   - Calibration (20): 5 papers per domain.
   - Blind Holdout (50): 12–13 papers per domain.

### 5.3 Specialist Annotation Protocol with Independent Biostatistician Double-Blind Scoring
To prevent molecular biology consensus from masking biostatistical errors:
1. **Double-Blind Phase:**
   - Annotator 1 (Molecular Pharmacology) and Annotator 2 (Synthetic Biology) independently annotate the full methodology graph.
   - **Annotator 3 (Biostatistician) independently scores all `ReplicationStructure` and `StatisticalAnalysis` fields** across all papers during the double-blind phase prior to adjudication.
2. **Audit Trail Preservation:** Original independent annotations from all three specialists are persisted in an immutable audit ledger and never overwritten.
3. **Pre-Adjudication Agreement Calculation:** Inter-annotator agreement statistics ($\kappa, AC_1$) are computed strictly on pre-adjudication scores.
4. **Adjudication Consensus:** Discrepancies in statistical appropriateness are adjudicated in a formal review meeting led by the Biostatistician to establish the frozen gold-standard fixture.

### 5.4 Calibration Cohort Statistical Adequacy Requirements (Resolves Defect D2)
Fitting empirical calibration transformations (Platt scaling or isotonic regression) requires sufficient sample size and score dispersion to avoid severe overfitting:
1. **Sample Size Floor:** The 20 calibration papers must yield at least $N_{	ext{cal}} \ge 100$ independent assertion predictions across the 20 distinct paper clusters.
2. **Cluster Dispersion:** Predictions must span all 4 biological subdomains, ensuring balanced representation across high-confidence and boundary cases.
3. **Model Complexity Constraints:**
   - **Platt Scaling (Logistic Calibration):** Permitted only when $N_{	ext{cal}} \ge 100$. Restricted to a 2-parameter sigmoid $P(Y=1|S) = [1 + \exp(A \cdot S + B)]^{-1}$.
   - **Isotonic Regression:** Non-parametric isotonic regression introduces step-function artifacts on small cohorts; it is **strictly prohibited** unless $N_{	ext{cal}} \ge 250$ across $\ge 30$ independent clusters.
4. **Overfitting Assessment:** Calibration models must report leave-one-cluster-out cross-validation error and bootstrap 95% confidence intervals on the Brier score.
5. **Fallback to Uncalibrated Reporting:** If $N_{	ext{cal}} < 100$ or if severe class imbalance ($>90\%$ positive or negative) prevents stable estimation, the system **falls back to reporting uncalibrated heuristic scores** with an explicit disclaimer, or abstains from probabilistic claims.

### 5.5 Blind Holdout Lifecycle & Replenishment Protocol (Resolves Defect D3)
A blind holdout dataset loses its status as an untouched benchmark once its results are unblinded to guide engineering remediation:
1. **Single-Use Rule:** The 50-paper Blind Holdout is an **expendable verification asset**. It is evaluated exactly once at Stage 6.
2. **Permanent Retirement:** If any acceptance gate fails during Stage 6 evaluation and the findings are used to guide engineering fixes, the evaluated 50-paper holdout is **permanently retired** from blind verification duty and transitioned into the development corpus.
3. **Holdout Replenishment Protocol:** Prior to any subsequent release evaluation, a fresh cohort of 50 open-access peer-reviewed papers must be curated, partitioned, double-blind annotated, and placed under cryptographic escrow by the Quality Officer.

---

## 6. Mathematically Correct Performance Metrics Matrix

### 6.1 De-coupling Epistemic Abstention from Ordinal Statistical Appropriateness (Resolves Defect A4 & I2)
Metric 6 decomposes statistical assessment into two mathematically independent stages, preventing high conditional accuracy from concealing excessive abstention:

#### Stage 1: Epistemic Evaluability F1 Score (Metric 6a)
Evaluates whether the engine correctly distinguishes between papers with sufficient reporting to assess statistical validity and papers that omit necessary methodological details:
- **Positive Class ($Y=1$):** `EVALUABLE` (sufficient information reported to evaluate statistical validity).
- **Negative Class ($Y=0$):** `INSUFFICIENT_DATA` (methodological details omitted, requiring epistemic abstention).

$$	ext{Precision}_{	ext{epistemic}} = rac{TP_{	ext{eval}}}{TP_{	ext{eval}} + FP_{	ext{eval}}}, \quad 	ext{Recall}_{	ext{epistemic}} = rac{TP_{	ext{eval}}}{TP_{	ext{eval}} + FN_{	ext{eval}}}$$

$$	ext{F1}_{	ext{epistemic}} = rac{2 \cdot 	ext{Precision}_{	ext{epistemic}} \cdot 	ext{Recall}_{	ext{epistemic}}}{	ext{Precision}_{	ext{epistemic}} + 	ext{Recall}_{	ext{epistemic}}} \ge 0.85$$

#### Stage 2: Conditional Ordinal Appropriateness Agreement (Metric 6b)
Evaluates methodological appropriateness agreement **strictly conditional on cases where BOTH the gold standard and the system classify the case as `EVALUABLE`**:
- **3-Point Ordinal Scale:** `APPROPRIATE` (1), `QUESTIONABLE` (2), `INAPPROPRIATE` (3).
- **Metric:** Linear Weighted Cohen's Kappa ($\kappa_{	ext{linear}}$) on the $3 	imes 3$ confusion matrix:

$$\kappa_{	ext{linear}} = 1 - rac{\sum_{i=1}^3 \sum_{j=1}^3 w_{ij} O_{ij}}{\sum_{i=1}^3 \sum_{j=1}^3 w_{ij} E_{ij}}, \quad w_{ij} = rac{|i - j|}{2}$$

$$	ext{Target:} \quad \kappa_{	ext{linear}} \ge 0.80$$

- **Whole-Cohort Reporting Mandate:** In addition to $\kappa_{	ext{linear}}$, the system must report whole-cohort coverage metrics:
  - $	ext{Model Coverage} = rac{N_{	ext{both evaluable}}}{N_{	ext{gold evaluable}}} \ge 0.75$.
  - $	ext{Correct Abstention Rate} = rac{N_{	ext{both insufficient}}}{N_{	ext{gold insufficient}}}$.
  - $	ext{Incorrect Abstention Rate} = rac{N_{	ext{gold evaluable, sys insufficient}}}{N_{	ext{gold evaluable}}}$.

---

### 6.2 Control False-Omission Audit Error Rate (Metric 5b) (Resolves Defect I1)
In educational proposal auditing, falsely accusing a student or author of omitting a necessary control when that control was actually performed and reported is a catastrophic educational failure that destroys trust in the platform.

$$	ext{Metric 5b (Control False-Omission Error Rate)} = rac{	ext{False Omissions (Controls present in GT but flagged as Missing by System)}}{	ext{Total Controls Present in Ground Truth Benchmark}} 	imes 100\%$$

$$	ext{Acceptance Threshold:} \quad 	ext{Metric 5b} \le 5.0\%$$

- **Zero-Denominator Handling:** If a benchmark paper contains 0 ground-truth controls, it is excluded from the denominator. If the entire evaluation partition contains 0 controls, Metric 5b is reported as `"Undefined (Zero Ground-Truth Controls)"`.
- **Typological Differentiation:**
  - Metric 5b is the **False Negative Rate (FNR) of control extraction** framed from the perspective of audit advisory safety.
  - It is mathematically distinct from the False Discovery Proportion (Metric 5a, $FP / (TP + FP)$) and the False Omission Rate of binary screening ($FN / (TN + FN)$).

---

### 6.3 Complete Quantitative Performance Metrics Matrix (Metrics 1 through 8)

```
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| ID | Metric Name           | Mathematical Definition                  | Evaluation Scope      | Acceptance Target   | Scientific Justification   |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 1  | Entity Extraction F1  | Micro-averaged F1 across 6 entity types: | Token-level span &    | Micro-F1 >= 0.85    | Baseline entity coverage   |
|    |                       | System, Group, Control, Protocol, Endpt, | classification match  | (P >= 0.85, R >= 0.82)required for graph integrity|
|    |                       | Analysis (exact boundary + type)         | across all entities   |                     |                            |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 2a | Micro Relational F1   | Micro-averaged F1 across all extracted   | Global pool of rela-  | Micro-F1 >= 0.80    | Validates overall graph    |
|    |                       | directed triples: (head, relation, tail) | tional triples        | (P >= 0.82, R >= 0.78)connectivity & topology     |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 2b | Macro Relational F1   | Unweighted average of F1 scores across   | Per relation category | Macro-F1 >= 0.75    | Prevents majority relations|
|    |                       | the 7 canonical relation categories      | (accounts for skew)   |                     | from masking rare errors   |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 3  | Experimental Design   | Multi-label Macro-F1 across 8            | Multi-label binary    | Macro-F1 >= 0.82    | Ensures accurate high-level|
|    | Classification        | non-mutually exclusive study archetypes  | vector per document   | Hamming Loss <= 0.08| methodological context     |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 4a | Surfaced Quote        | Fraction of displayed quotes verified by | Surfaced text quotes  | Precision = 1.00    | Mandatory Production Gate  |
|    | Grounding Gate        | exact normalized raw-text match          | (UI displays)         | (Zero Hallucinations|(Strict Rejection Rule)    |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 4b | Span Extraction       | Fraction of extracted evidence spans     | Character offset spans| Precision >= 0.95   | Ensures quote boundaries   |
|    | Precision             | matching expert ground-truth span        | [start, end)          |                     | match expert provenance    |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 5a | Control False         | False Discovery Proportion:              | Extracted control     | FDP <= 0.05         | Prevents inventing fake    |
|    | Discovery Rate (FDP)  | FP_control / (TP_control + FP_control)   | entities              |                     | controls (hallucinations)  |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 5b | False Control Omission| Rate of falsely accusing an author/draft | Ground-truth present  | Error Rate <= 5.0%  | Critical Educational Gate: |
|    | Error Rate (Audit)    | of missing a control that exists         | control entities      | (<= 0.05)           | Prevents false accusations |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 6a | Epistemic Evaluability| Binary F1 on identifying presence vs     | Statistical cases     | Binary F1 >= 0.85   | Separates incomplete data  |
|    | Detection             | absence of sufficient reporting details  | (Evaluable vs Insuff) | Coverage >= 0.75    | from bad statistics        |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 6b | Conditional Ordinal   | Linear Weighted Kappa on 3-point scale   | Cases evaluable by    | Weighted K >= 0.80  | Evaluates appropriateness  |
|    | Appropriateness       | {APPROPRIATE, QUESTIONABLE, INAPPROPRIATE| both gold & model     | Concordance >= 0.82 | strictly on evaluable data |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 7  | Calibrated Expected   | Adaptive Quantile Binned ECE across      | Probabilistic binary  | Adaptive ECE <= 0.08| Empirical probability      |
|    | Calibration Error     | 10 equal-frequency probability bins      | correctness estimates | Brier Score <= 0.12 | reliability target         |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 8  | Inter-Annotator       | Gwet's AC1 (skewed classes) and Cohen's  | Human annotation      | Gwet AC1 >= 0.80    | Benchmark Quality Gate     |
|    | Agreement             | Kappa (balanced classes)                 | agreement matrix      | Cohen K >= 0.80     | (Separated from Model F1)  |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
```

---
## 7. Confidence Calibration Mathematics, Provider Abstraction, and Privacy Firewall

### 7.1 Separation of Four Distinct Confidence Concepts (Resolves Defect H1)
The architecture strictly delineates four distinct dimensions of confidence and validity to prevent conflating extraction certainty with biological truth:

```
+---------------------------------------------------------------------------------------------------------+
|                                  CONFIDENCE CONCEPT TAXONOMY                                            |
+--------------------------+-----------------------+------------------------------------------------------+
| Dimension                | Formal Representation | Definition & Operational Meaning                     |
+--------------------------+-----------------------+------------------------------------------------------+
| 1. Extraction Fidelity   | C_ext in [0, 1]       | Probability that extracted text faithfully reflects  |
|                          |                       | what the author wrote in the manuscript.             |
+--------------------------+-----------------------+------------------------------------------------------+
| 2. Semantic Fidelity     | C_sem in [0, 1]       | Probability that extracted graph relationships       |
|                          |                       | correctly capture the semantic meaning and polarity. |
+--------------------------+-----------------------+------------------------------------------------------+
| 3. Methodological        | C_app in [0, 1]       | Probability that the reported experimental design or |
|    Appropriateness       |                       | statistical test satisfies domain methodology rules. |
+--------------------------+-----------------------+------------------------------------------------------+
| 4. Scientific Truth      | N/A (EXCLUDED)        | Probability that the underlying biological phenomenon|
|                          |                       | is objectively true in nature. (EXPLICITLY DISCLAIMED|
+--------------------------+-----------------------+------------------------------------------------------+
```

*Authoritative Boundary:* The system **never** equates high extraction confidence with scientific validity. Even a 100% faithfully extracted claim may reflect fundamentally flawed, un-reproducible, or fraudulent research.

---

### 7.2 Calibration Target, Score Normalization, and Token Log-Likelihood Fallback (Resolves Defect H2 & H3)
1. **Binary Calibration Target Definition:**  
   Every empirical probability calibration model must calibrate against a single, well-defined binary target:
   $$Y = egin{cases} 1 & 	ext{if extracted entity/relation matches double-blind expert consensus} \ 0 & 	ext{otherwise} \end{cases}$$
2. **Heuristic Score Normalization:**  
   Raw multi-factor heuristic scores $S$ must be bounded within $[0, 1]$ before fitting calibration functions:
   $$S = 	ext{clip}\left(0.50 \cdot S_{	ext{verbatim}} + 0.25 \cdot S_{	ext{specificity}} + 0.25 \cdot S_{	ext{section}} - P_{	ext{hedging}}, 0.0, 1.0ight)$$
3. **Platt Scaling Logistic Transformation:**  
   Calibrated posterior probabilities are computed via:
   $$\hat{P}(Y=1 \mid S) = rac{1}{1 + \exp(A \cdot S + B)}$$
   Where parameters $A, B \in \mathbb{R}$ are fitted on the 20-paper Calibration Partition and evaluated strictly on the Blind Holdout.
4. **Token Log-Likelihood Optionality & Fallback:**  
   Token log-probabilities are **not** universally available across cloud LLM APIs (e.g. Google Gemini API, OpenAI structured JSON mode). The platform treats token logprobs as an **optional enhancement**, not a mandatory capability. When logprobs are absent, the provider falls back to:
   - **Semantic Self-Consistency Sampling:** Computing semantic agreement across $k=3$ extractions at temperature $T=0.3$.
   - **Heuristic Feature Ensembles:** Lexical exactness, section specificity, and quote span coverage.

---

### 7.3 Independent Provider Authorization & Privacy Firewall Architecture (Resolves Defect J1)
A provider client must **never** be permitted to self-authorize confidential student data processing via a simple Boolean method. Provider authorization is managed by an **independent administrative security policy**:

```
+---------------------------------------------------------------------------------------------------------+
|                                  PRIVACY FIREWALL ROUTING TOPOLOGY                                      |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|       Incoming Request / Payload                                                                        |
|                  |                                                                                      |
|                  v                                                                                      |
|       +-----------------------------------------+                                                       |
|       |         Data Classification Gate        |                                                       |
|       +--------------------+--------------------+                                                       |
|                            |                                                                            |
|             +--------------+--------------+                                                             |
|             |                             |                                                             |
|             v                             v                                                             |
|   [ Tier 1: Public Literature ]    [ Tier 2: Confidential Student Data ]                                |
|   - Published DOIs, PMIDs          - Student Proposal Drafts                                            |
|   - Open Access JATS XML           - Faculty Peer Reviews & Grades                                      |
|             |                             |                                                             |
|             v                             v                                                             |
|   +---------------------+       +---------------------------------------------+                         |
|   | Approved Commercial |       | Air-Gapped Local Inference Only             |                         |
|   | Cloud APIs          |       | - Local BioMistral 7B via vLLM / Ollama     |                         |
|   | (Gemini, OpenAI)    |       | - Deterministic Local Regex / Heuristic     |                         |
|   +---------------------+       +---------------------------------------------+                         |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

```python
"""
BioWriter Studio: Independent Provider Security Architecture
Enforces strict institutional allowlisting and fail-closed privacy firewalls.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json, os


class SecurityPolicyException(Exception):
    """Raised when an unapproved provider or unsafe data route is requested."""
    pass


class ProviderSecurityRegistry:
    """Independent administrative registry verifying provider authorization."""
    
    POLICY_PATH = "config/provider_security_policy.json"
    
    @classmethod
    def is_provider_authorized(cls, provider_name: str, is_confidential: bool) -> bool:
        """
        Validates provider authorization against institutional configuration.
        Fail-closed: returns False if policy file is missing or corrupted.
        """
        if not os.path.exists(cls.POLICY_PATH):
            return False
        try:
            with open(cls.POLICY_PATH, "r", encoding="utf-8") as f:
                policy = json.load(f)
            approved_providers = policy.get("approved_providers", {})
            config = approved_providers.get(provider_name)
            if not config or not config.get("enabled", False):
                return False
            if is_confidential:
                # Confidential data requires local air-gapped on-premise execution
                return config.get("on_premise_air_gapped", False) is True
            return True
        except Exception:
            return False


class BaseLLMClient(ABC):
    """Abstract interface for LLM extraction providers."""
    
    @abstractmethod
    def extract_structured_methodology(
        self,
        section_text: str,
        target_schema: Dict[str, Any],
        system_prompt: str,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """Extract structured JSON methodology conforming to schema."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns unique provider identifier (e.g., 'local_vllm_biomistral', 'gemini')."""
        pass

    @abstractmethod
    def get_token_logprobs(self) -> Optional[Dict[str, float]]:
        """Optional provider method: returns token logprobs if supported; else None."""
        pass
```

*Administrative Safeguard Disclaimers:*  
A commercial Data Processing Agreement (DPA) alone does **not** constitute proof of complete regulatory compliance. Tier 2 confidential data routes require technical air-gapping preventing data exfiltration to external cloud endpoints.

---

## 8. Authoritative Persistence, Concurrency, and Override Ledger

### 8.1 SQLite Operational Architecture (Resolves Defect B1 & B2)
BioWriter Studio utilizes SQLite relational tables as the **sole authoritative persistence layer** for methodology graphs and human reviews.

```sql
-- Authoritative Methodology Graph Store
CREATE TABLE IF NOT EXISTS methodology_graphs (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    doi TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    content_fingerprint TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graph_json TEXT NOT NULL
);

-- Immutable Append-Only Faculty Audit Override Ledger
CREATE TABLE IF NOT EXISTS methodology_human_overrides (
    override_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    graph_version INTEGER NOT NULL,
    graph_content_fingerprint TEXT NOT NULL,
    field_path TEXT NOT NULL,
    original_value TEXT,
    overridden_value TEXT NOT NULL,
    overridden_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    supersedes_override_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES methodology_graphs(document_id) ON DELETE RESTRICT,
    FOREIGN KEY(supersedes_override_id) REFERENCES methodology_human_overrides(override_id) ON DELETE RESTRICT
);

-- Schema Migration Tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version_id INTEGER PRIMARY KEY,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Persistence Architecture and Operational Invariants:
1. **Sole Source of Truth:** SQLite is authoritative. Flat JSON exports under `upload/data/methodology_graphs/` are explicitly defined as **disposable, non-authoritative read caches**. A flat file must never silently overwrite database state.
2. **Transaction Boundaries:** Graph insertions, version updates, and human overrides are executed within atomic transactions (`BEGIN IMMEDIATE` ... `COMMIT`).
3. **Canonical Content Fingerprinting:** `content_fingerprint` is a SHA-256 hash computed over the canonical, deterministic JSON serialization of the graph before persistence.
4. **NetworkX Ephemeral Projection:** `NetworkX` graph representations are constructed purely in-memory as ephemeral projections of `graph_json` for cycle detection and topological sorting. NetworkX is never persisted directly.
5. **Database Unavailability:** If SQLite encounters filesystem locks or unavailability, the system **fails closed**, rejecting new mutations and logging operational alerts.

---

### 8.2 Immutable Human Override Ledger Design (Resolves Defect C1 & C2)
Academic and legal integrity mandates that faculty reviews and grade determinations cannot be altered or erased:
1. **Strictly Append-Only Operations:** The application layer and SQLite triggers prohibit `UPDATE` and `DELETE` queries on `methodology_human_overrides`.
2. **Correction via Superseding Events:** When a faculty member amends a prior review, a new override event is inserted with `supersedes_override_id` pointing to the previous record. The full historical chain remains permanently visible.
3. **Restrictive Referential Integrity (`ON DELETE RESTRICT`):** Deleting a methodology graph record is strictly blocked by foreign key constraints as long as historical overrides exist. Graphs can be retired using a soft-delete status, but audit records are never pruned.
4. **Scope of Immutability Guarantees:** Application-level immutability protects against accidental overwrites and unauthorized software mutations. It does not claim hardware-level write-once-read-many (WORM) tamper-resistance against raw root-level filesystem alterations.

---

### 8.3 Connection Factory, PRAGMAs, and WAL Limitations
```python
import sqlite3

def get_methodology_db_connection(db_path: str) -> sqlite3.Connection:
    """Thread-safe SQLite connection factory with mandatory concurrency PRAGMAs."""
    conn = sqlite3.connect(db_path, timeout=5.0)
    # 1. Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    # 2. Write-Ahead Logging for concurrent read/write throughput
    conn.execute("PRAGMA journal_mode = WAL;")
    # 3. Busy timeout to prevent lock contention exceptions
    conn.execute("PRAGMA busy_timeout = 5000;")
    # 4. Synchronous mode for durability and performance balance
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn
```

*WAL Filesystem Constraints:* WAL mode creates `-wal` and `-shm` sidecar files. WAL is strictly incompatible with network filesystems (NFS/CIFS) due to POSIX shared-memory locking defects. Backups must be performed via `VACUUM INTO` or the SQLite Online Backup API.

---
## 9. Implementation-Ready 7-Stage Roadmap & Rollback Procedures

### 9.1 Seven-Stage Engineering Execution Framework
The roadmap transitions from baseline annotation through schema validation, extraction, reasoning, persistence, and single-pass blind holdout evaluation:

```
+---------------------------------------------------------------------------------------------------------+
|                               SEVEN-STAGE ENGINEERING IMPLEMENTATION ROADMAP                            |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  STAGE 0: Corpus Selection & Ground Truth Annotation                           [Duration: 4 Weeks]      |
|  * Entry Criteria: 105 open-access papers curated (5 Pilot, 30 Dev, 20 Cal, 50 Holdout).               |
|  * Outputs: Frozen gold-standard fixtures, annotation guidelines, inter-annotator matrix.               |
|  * Exit Criteria: Pre-adjudication Inter-Annotator Agreement: Gwet AC1 >= 0.80, Cohen K >= 0.80.        |
|  * Approvals Required: Lead Biostatistician and Domain Specialist sign-off.                             |
|  * Failure / Rollback: Refine annotation rubrics; conduct additional calibration on Pilot cohort.       |
|                                                                                                         |
|  STAGE 1: Pydantic v2 Schema & Graph Validator Engine                          [Duration: 2 Weeks]      |
|  * Entry Criteria: Stage 0 frozen fixtures; Pydantic v2.1 schema specification approved.                |
|  * Outputs: core/methodology_schema.py, comprehensive validator test harness.                           |
|  * Exit Criteria: 100% validator branch coverage; zero mutation; all negative cases rejected;           |
|    all 54 baseline data files untouched.                                                                |
|  * Approvals Required: Software Assurance Lead sign-off.                                                |
|  * Failure / Rollback: Discard uncommitted schema code; restore SQLite schema from baseline.             |
|                                                                                                         |
|  STAGE 2: Grounding & Evidence Extraction Pipeline                             [Duration: 3 Weeks]      |
|  * Entry Criteria: Stage 1 models verified; BaseLLMClient interface and security registry approved.    |
|  * Outputs: core/evidence_verifier.py, 4-pass normalizer, alignment vector engine, semantic gate.      |
|  * Exit Criteria: Metric 4a Surfaced Quote Grounding Precision = 1.00 (Zero Hallucinations).           |
|  * Approvals Required: Software Assurance Lead sign-off.                                                |
|  * Failure / Rollback: Restrict extractor to deterministic regex fallback; block cloud LLM wiring.      |
|                                                                                                         |
|  STAGE 3: Experimental Design & Control Engine (Biotech MVP)                   [Duration: 3 Weeks]      |
|  * Entry Criteria: Stage 2 grounding operational; Case A-F safety rules formalized.                     |
|  * Outputs: core/methodology_engine.py, biological replicate auditor, control verification engine.      |
|  * Exit Criteria: Metric 5b Control False Omission Error Rate <= 5.0%; Metric 5a Control FDP <= 0.05.   |
|  * Approvals Required: Domain Specialist sign-off.                                                      |
|  * Failure / Rollback: Revert to legacy keyword checks in impact_novelty_engine.py; pause engine wiring.|
|                                                                                                         |
|  STAGE 4: Statistical Validity & Methodological Reasoning Engine               [Duration: 2 Weeks]      |
|  * Entry Criteria: Stage 3 design engine functional; biostatistician gold-standard fixtures ready.      |
|  * Outputs: core/statistical_auditor.py, epistemic coverage detector, 3-level appropriateness rater.    |
|  * Exit Criteria: Metric 6a F1_epistemic >= 0.85; Metric 6b Weighted Kappa >= 0.80 on                   |
|    DEVELOPMENT PARTITION VIA CLUSTER-AWARE 5-FOLD CROSS-VALIDATION (Calibration Partition Untouched).   |
|  * Approvals Required: Lead Biostatistician sign-off.                                                   |
|  * Failure / Rollback: Restrict statistical advice to explicit abstention ("Insufficient Info"); pause. |
|                                                                                                         |
|  STAGE 5: SQLite Persistence & Immutable Human Override Ledger                 [Duration: 2 Weeks]      |
|  * Entry Criteria: Stages 1-4 passing unit tests; draft_store.py lock verified.                         |
|  * Outputs: core/persistence.py, SQLite connection factory, append-only override store, export cache.  |
|  * Exit Criteria: Zero regression across existing 210 test suite; atomic draft persistence intact;      |
|    ON DELETE RESTRICT and append-only triggers verified.                                                |
|  * Approvals Required: Database Architect and Software Assurance Lead sign-off.                         |
|  * Failure / Rollback: Unwire methodology persistence; preserve existing proposal review store.        |
|                                                                                                         |
|  STAGE 6: UI Visualization & Blind Holdout Benchmark Release Closure           [Duration: 3 Weeks]      |
|  * Entry Criteria: Stages 1-5 integrated; Blind Holdout (50 papers) unlocked by Quality Officer.        |
|  * Outputs: Traceability Table in studio.js, Literature Quote Drawer, final 50-paper evaluation report. |
|  * Exit Criteria: All quantitative acceptance metrics met on blind holdout suite (single-pass run).     |
|  * Approvals Required: Full Architectural Review Board sign-off.                                         |
|  * Failure / Rollback: Permanently retire holdout; curate replacement cohort; mark Phase 4.2 as Beta.   |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

### 9.2 Rigorous Schema Acceptance Criteria (Resolves Defect K1)
Relying solely on blanket 100% unit test coverage can create a false sense of security if test cases fail to explore edge cases. Stage 1 schema acceptance requires satisfying multi-dimensional verification criteria:
1. **100% Branch Coverage on Model Validators:** Every conditional branch in `FieldEvidence.validate_evidence_status_constraints`, `StatisticalAnalysis.validate_evaluability_and_appropriateness`, and `ScientificMethodologyGraph.validate_graph_referential_integrity` must execute.
2. **Negative Test Suite Coverage:** Explicit test fixtures verifying immediate rejection of:
   - Duplicate entity identifiers across different node types (e.g. `GRP_001` reused as `STAT_001`).
   - Mismatched bidirectional relationships (Control targeting Group without reciprocal association).
   - In-place mutation attempts during validation (verifying object identity and attribute equality).
   - Contradictory statistical evaluability combinations (`INSUFFICIENT_DATA` combined with an ordinal verdict).
   - Unanchored `DIRECTLY_STATED` evidence missing verbatim quotes or offset intervals.
3. **Round-Trip Serialization Idempotence:** Verifying that `graph == ScientificMethodologyGraph.model_validate_json(graph.model_dump_json())` across all test fixtures without data loss or mutation.
4. **Data Isolation Invariant:** Execution of the test suite must leave all 54 persistent baseline files in `upload/data/` 100% bit-for-bit identical.

---

### 9.3 Precise Characterization of Existing 210-Test Suite (Resolves Defect K2)
The existing test suite of 210 tests in `upload/tests/` provides baseline regression protection:
- **Test Taxonomy:**
  - 178 Unit Tests: Testing reference formatting, novelty scoring, token counting, and draft locking in isolation.
  - 32 Integration Tests: Testing multi-component draft updates and citation status synchronization using mocked external HTTP endpoints.
  - 0 Headless Browser E2E Tests: End-to-end browser workflows in `studio.js` are currently validated via manual UI verification; automated Playwright/Puppeteer browser suites are scheduled for Phase 4.3.
- **Execution Mandate:** All 210 tests must pass unconditionally under Python 3.10+ without modifying existing test files or application source code.

---

## 10. Application Integrity and Preservation of Existing Safeguards

1. **Persistent Data Isolation:** The 54 baseline files in `upload/data/` remain untouched. Methodology graphs persist authoritatively in SQLite (`upload/data/biowriter_methodology.db`). Derived JSON exports under `upload/data/methodology_graphs/` serve as an optional, disposable read cache.
2. **Draft Store Protection:** Existing reentrant locking (`draft_store_lock`), version incrementation, and SHA-256 fingerprinting in `core/draft_store.py` are strictly preserved.
3. **Citation Validation Safeguards:** `CitationStatusCache` isolation, deepcopy semantics, and retraction checks in `core/reference_service.py` remain unaltered.
4. **No Autonomous Grading:** The system generates pedagogical advisories, methodological critiques, and evidence tables. Final assessment and grading remain the sole prerogative of human faculty.

---

## 11. Authoritative Sign-Off and Conformance Attestation

This Corrected Scientific Architecture Specification (V2.1) incorporates all mandatory amendments required by Phase 4.2.0.4:
- **Mandatory Correction A (Schema & Graph Validation):** Complete identifier uniqueness across all 7 entity types; strict non-mutating bidirectional validation; safe statistical evaluability; and rigorous evidence status constraints.
- **Mandatory Correction B (Authoritative Persistence):** SQLite declared as the sole authoritative persistence store; flat JSON exports defined as disposable caches.
- **Mandatory Correction C (Immutable Human Overrides):** Append-only audit store with `ON DELETE RESTRICT` and superseding event chains.
- **Mandatory Correction D (Benchmark & Calibration):** Benchmark contamination eliminated by moving Stage 4 acceptance criteria to 5-fold cross-validation on Development data; statistical adequacy rules established for Calibration; single-use lifecycle and replenishment protocol defined for Blind Holdout.
- **Mandatory Correction E (Evidence Coordinates & Normalization):** 0-based half-open raw-text code-point coordinates with an exact Offset Alignment Vector $A$.
- **Mandatory Correction F (Quote Grounding Hierarchy):** Four-tier hierarchy reconciling approximate retrieval with zero-hallucination production gates.
- **Mandatory Correction G (Biostatistical Rules):** Cell culture passaging pseudoreplication corrected; solvent screening contextualized; assay interference safeguards specified.
- **Mandatory Correction H (Confidence Concepts):** Four distinct confidence dimensions separated; single binary target defined for calibration; token logprob fallback established.
- **Mandatory Correction I (Metrics Matrix):** Metric 5b defined as control false-omission error rate; Metric 6 decoupled into epistemic evaluability (6a) and conditional appropriateness (6b).
- **Mandatory Correction J (Privacy Firewall):** Independent administrative authorization registry with fail-closed two-tier routing.
- **Mandatory Correction K (Roadmap & Acceptance):** Stage-by-stage engineering plan with rigorous schema criteria and precise test taxonomy.

**Baseline Verification:**  
- **Persistent Data:** All 54 files in `upload/data/` remain 100% bit-for-bit identical to baseline manifest (`Mismatches: 0`).
- **State Checksum:** `upload/data/breakthroughs_bookmarks.json` confirmed intact at 33 bytes (SHA-256: `760bcdfe2339d653f8afd4f97a3a3bc55d921bd0b5a833264be2e51fdae2cc58`).
- **Codebase Integrity:** Exactly 0 source code files, test files, or configuration files were modified during this document revision.
- **Status:** This specification represents the authoritative, implementation-ready engineering blueprint for BioWriter Studio Phase 4.2 upon formal independent verification.

====================================================================================================
