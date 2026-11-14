# BioWriter Studio — Phase 4.2.0: Corrected Scientific Architecture Specification
## Implementation-Ready Specification for the Scientific Methodology Intelligence Architecture

**Target Project:** `c:\Users\Lenovo\Downloads\Joint Platform\upload`  
**Phase:** Phase 4.2.0 — Corrected Architecture Specification  
**Status:** IMPLEMENTATION-READY BLUEPRINT (Supersedes Initial Design)  
**Execution Mode:** STRICT ARCHITECTURE AUDIT AND DOCUMENTATION ONLY  
**Auditor Role:** Independent Scientific Software Architect, Biomedical Research Methodologist, and Computational Biology Auditor  
**Date:** November 14, 2026  

---

## 1. System Vision and Architectural Principles

### 1.1 Mission
BioWriter Studio's Scientific Methodology Intelligence Engine transitions the platform from shallow lexical pattern-matching to an ontology-grounded, relational understanding of experimental research. The system models the complete evidentiary chain:
$$\text{Research Question} \longrightarrow \text{Hypothesis} \longrightarrow \text{Experimental System} \longrightarrow \text{Groups \& Controls} \longrightarrow \text{Assays} \longrightarrow \text{Measurements} \longrightarrow \text{Statistical Tests} \longrightarrow \text{Causal Conclusions}$$

### 1.2 Core Architectural Principles
1. **Separation of Lexical Match from Scientific Truth:** The presence of a verbatim quote in a paper proves the author made an assertion; it does **not** prove the assertion is biologically true or methodologically sound.
2. **Replication Integrity:** Biological replicates ($N$, independent physical experiments) and technical replicates ($n$, repeat assay wells) are structurally separated to prevent pseudoreplication.
3. **Control Completeness:** Every treatment group must be structurally linked to its required negative, vehicle, benchmark, and assay-interference controls.
4. **Epistemic Humility:** When a paper or proposal draft omits critical methodology details, the system must emit `"Insufficient methodological information to assess this"` rather than guessing or hallucinating completeness.
5. **Data Confinement & Institutional Privacy:** Student proposal drafts and faculty comments constitute confidential academic records (FERPA/IP). They must never be transmitted to external commercial cloud LLMs without explicit institutional authorization.

---

## 2. Corrected Minimal Viable Ontology (MVO) & Relational Schema

### 2.1 Relational Architecture Diagram

```mermaid
classDiagram
    direction TB
    class ScientificMethodologyGraph {
        +string document_id
        +string title
        +string doi
        +ResearchObjective objective
        +List~ExperimentalSystem~ systems
        +List~ExperimentalGroup~ groups
        +List~ControlGroup~ controls
        +List~AssayProtocol~ protocols
        +List~MeasurementEndpoint~ endpoints
        +List~StatisticalAnalysis~ analyses
        +List~EvidenceConclusion~ conclusions
    }

    class ResearchObjective {
        +string research_question
        +string primary_hypothesis_H1
        +string null_hypothesis_H0
        +string study_archetype
        +FieldEvidence evidence
    }

    class ExperimentalSystem {
        +string system_id
        +string system_type
        +string model_name
        +string organism_or_species
        +string cell_line_or_strain
        +FieldEvidence evidence
    }

    class ExperimentalGroup {
        +string group_id
        +string system_id
        +string treatment_name
        +string dose_or_concentration
        +string exposure_duration
        +string administration_route
        +ReplicationStructure replication
        +List~string~ associated_control_ids
        +FieldEvidence evidence
    }

    class ControlGroup {
        +string control_id
        +string control_type
        +string reagent_or_vehicle
        +string concentration
        +string control_rationale
        +FieldEvidence evidence
    }

    class ReplicationStructure {
        +int biological_replicates_N
        +int technical_replicates_n
        +string experimental_unit
        +bool is_pseudoreplication_risk
    }

    class AssayProtocol {
        +string protocol_id
        +string assay_category
        +string technique_name
        +string detection_platform
        +AssayInterferenceControl interference_control
        +FieldEvidence evidence
    }

    class AssayInterferenceControl {
        +bool requires_color_blank
        +bool color_blank_performed
        +string blank_description
    }

    class MeasurementEndpoint {
        +string endpoint_id
        +string protocol_id
        +string raw_readout
        +string normalized_metric
        +string units
        +bool is_repeated_measure
        +FieldEvidence evidence
    }

    class StatisticalAnalysis {
        +string analysis_id
        +string endpoint_id
        +List~string~ compared_group_ids
        +string test_name
        +string post_hoc_correction
        +float p_value
        +string effect_size
        +string appropriateness_verdict
        +string biostatistical_critique
        +FieldEvidence evidence
    }

    class EvidenceConclusion {
        +string conclusion_id
        +string finding_statement
        +string causal_claim_strength
        +List~string~ supporting_analysis_ids
        +List~string~ stated_limitations
        +List~string~ inferred_methodological_flaws
        +FieldEvidence evidence
    }

    ScientificMethodologyGraph *-- ResearchObjective
    ScientificMethodologyGraph *-- ExperimentalSystem
    ScientificMethodologyGraph *-- ExperimentalGroup
    ScientificMethodologyGraph *-- ControlGroup
    ScientificMethodologyGraph *-- AssayProtocol
    ScientificMethodologyGraph *-- MeasurementEndpoint
    ScientificMethodologyGraph *-- StatisticalAnalysis
    ScientificMethodologyGraph *-- EvidenceConclusion

    ExperimentalGroup *-- ReplicationStructure
    AssayProtocol *-- AssayInterferenceControl

    ExperimentalGroup --> ExperimentalSystem : executes_in
    ControlGroup --> ExperimentalGroup : controls_for
    AssayProtocol --> ExperimentalGroup : measures
    MeasurementEndpoint --> AssayProtocol : generated_by
    StatisticalAnalysis --> MeasurementEndpoint : evaluates
    StatisticalAnalysis --> ExperimentalGroup : compares
    EvidenceConclusion --> StatisticalAnalysis : supported_by
```

---

### 2.2 Formal Pydantic v2 Schema Specification

```python
"""
BioWriter Studio: Corrected Scientific Methodology Schema (Pydantic v2)
Core module defining the formal Minimal Viable Ontology (MVO) for Phase 4.2.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class FieldEvidenceStatus(str, Enum):
    DIRECTLY_STATED = "DIRECTLY_STATED"
    MULTI_PASSAGE_SYNTHESIS = "MULTI_PASSAGE_SYNTHESIS"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_REPORTED = "NOT_REPORTED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class ControlTypeEnum(str, Enum):
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
    WELL = "WELL"
    CULTURE_DISH = "CULTURE_DISH"
    ANIMAL = "ANIMAL"
    CAGE = "CAGE"
    LITTER = "LITTER"
    HUMAN_SUBJECT = "HUMAN_SUBJECT"
    ASSAY_TUBE = "ASSAY_TUBE"
    UNKNOWN = "UNKNOWN"

class FieldEvidence(BaseModel):
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

class ReplicationStructure(BaseModel):
    biological_replicates_N: Optional[int] = None
    technical_replicates_n: Optional[int] = None
    experimental_unit: ExperimentalUnitEnum = ExperimentalUnitEnum.UNKNOWN
    is_pseudoreplication_risk: bool = False
    rationale: Optional[str] = None

class AssayInterferenceControl(BaseModel):
    requires_color_blank: bool = False
    color_blank_performed: bool = False
    turbidity_or_autofluorescence_noted: bool = False
    blank_description: Optional[str] = None

class ResearchObjective(BaseModel):
    research_question: str
    primary_hypothesis_H1: Optional[str] = None
    null_hypothesis_H0: Optional[str] = None
    study_archetypes: List[str] = Field(default_factory=list)  # Multi-label
    evidence: FieldEvidence

class ExperimentalSystem(BaseModel):
    system_id: str
    system_type: SystemTypeEnum
    model_name: str
    organism_or_species: Optional[str] = None
    cell_line_or_strain: Optional[str] = None
    biological_source_details: Optional[str] = None
    evidence: FieldEvidence

class ControlGroup(BaseModel):
    control_id: str
    control_type: ControlTypeEnum
    reagent_or_vehicle: str
    concentration: Optional[str] = None
    control_rationale: str
    evidence: FieldEvidence

class ExperimentalGroup(BaseModel):
    group_id: str
    system_id: str
    treatment_name: str
    dose_or_concentration: Optional[str] = None
    exposure_duration: Optional[str] = None
    administration_route: Optional[str] = None
    replication: ReplicationStructure
    associated_control_ids: List[str] = Field(default_factory=list)
    evidence: FieldEvidence

class AssayProtocol(BaseModel):
    protocol_id: str
    technique_name: str
    assay_category: str
    target_analyte_or_phenotype: str
    detection_platform: Optional[str] = None
    critical_parameters: Dict[str, str] = Field(default_factory=dict)
    interference_control: AssayInterferenceControl = Field(default_factory=AssayInterferenceControl)
    evidence: FieldEvidence

class MeasurementEndpoint(BaseModel):
    endpoint_id: str
    protocol_id: str
    raw_readout: str
    normalized_metric: str
    units: str
    is_repeated_measure: bool = False
    timepoints: List[str] = Field(default_factory=list)
    evidence: FieldEvidence

class StatisticalAnalysis(BaseModel):
    analysis_id: str
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
    appropriateness_verdict: str  # APPROPRIATE, SUBOPTIMAL, INVALID, INSUFFICIENT_DATA
    biostatistical_critique: Optional[str] = None
    evidence: FieldEvidence

class EvidenceConclusion(BaseModel):
    conclusion_id: str
    finding_statement: str
    causal_claim_strength: str  # DIRECT_CAUSAL, CORRELATIVE, SPECULATIVE, REFUTED
    supporting_analysis_ids: List[str]
    stated_limitations: List[str] = Field(default_factory=list)
    inferred_methodological_flaws: List[str] = Field(default_factory=list)
    evidence: FieldEvidence

class ScientificMethodologyGraph(BaseModel):
    document_id: str
    title: str
    doi: Optional[str] = None
    objective: ResearchObjective
    systems: List[ExperimentalSystem]
    groups: List[ExperimentalGroup]
    controls: List[ControlGroup]
    protocols: List[AssayProtocol]
    endpoints: List[MeasurementEndpoint]
    analyses: List[StatisticalAnalysis]
    conclusions: List[EvidenceConclusion]
```

---

## 3. Corrected Seven-Tier Evidence and Provenance Model

### 3.1 Verbatim Normalization and Extraction Pipeline
To achieve the mandate of **zero ungrounded quotes** while handling real-world PDF text layer corruptions, the quote verification engine executes a four-pass normalization protocol:
1. **Pass 1: Unicode NFKC Decomposition:** Eliminates ligature artifacts (e.g. converting `ﬁ` to `fi`, `ﬂ` to `fl`, `ﬀ` to `ff`).
2. **Pass 2: Whitespace and Hyphenation Stripping:** Reassembles words split across line breaks (e.g. `anti- / inflammatory` $\to$ `anti-inflammatory`) and collapses consecutive whitespace.
3. **Pass 3: XML Entity Unescaping:** Decodes XML character entities (`&amp;`, `&lt;`, `&#945;` $\to$ `α`).
4. **Pass 4: Strict Substring Verification Gate:**
   - Searches for the normalized candidate quote within the targeted document section.
   - If found, computes exact byte offsets: `char_start_offset`, `char_end_offset`.
   - **Production Gate Rule:** If Levenshtein ratio $< 0.95$ or substring is absent, the quote is **strictly rejected from user display**, flagged as `UNCERTAIN`, and routed to the human review queue.

### 3.2 Calibrated Confidence Engine
Confidence $C \in [0.0, 1.0]$ is computed using an adaptive formulation:
$$C = 0.50 \cdot S_{\text{verbatim}} + 0.25 \cdot S_{\text{specificity}} + 0.25 \cdot S_{\text{section}} - P_{\text{hedging}}$$

- $S_{\text{verbatim}} = 1.0$ (exact match), $0.8$ (normalized match), $0.0$ (unmatched).
- $S_{\text{specificity}} = \min\left(1.0, \frac{\text{numeric values} + \text{explicit units}}{3}\right)$.
- $S_{\text{section}} = 1.0$ (Methods), $0.85$ (Results), $0.60$ (Abstract), $0.40$ (Discussion).
- $P_{\text{hedging}} \in [0.0, 0.35]$: Penalty for speculative phrasing (`"may indicate"`, `"suggests"`, `"could possibly"`).

---

## 4. Biostatistical and Experimental Design Safety Rules

The engine implements six formalized safety audits with explicit trigger, suppression, and fallback logic:

```
+---------------------------------------------------------------------------------------------------------+
|                                BIOSTATISTICAL SAFETY SPECIFICATION TABLE                                |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case   | Biological Topic       | Trigger Condition     | Suppression Condition | Automated Advisory    |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case A | Biological vs.         | Student or author     | Clear evidence of >=3 | HIGH WARNING:         |
|        | Technical Replication  | asserts N=3 based on  | independent passages  | "Treating wells from a|
|        | (Pseudoreplication)    | multiple wells in a   | on distinct days.     | single plate as N=3 is|
|        |                        | single culture plate. |                       | pseudoreplication."   |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case B | Vehicle / Solvent      | Formulation uses >=   | Solvent diluted to    | WARNING:              |
|        | Control Matching       | 0.05% (v/v) organic   | < 0.01% v/v (dilution | "A vehicle control    |
|        |                        | solvent without       | > 1:10,000 in buffer).| matching solvent conc |
|        |                        | matched vehicle.      |                       | is required."         |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case C | Spectrophotometric     | Colored botanical     | Explicit cell-free    | ADVISORY:             |
|        | Interference           | extract tested in     | extract background OD | "Plant extracts absorb|
|        | (Griess / MTT)         | OD540 / OD570 without | subtraction reported. | at 540nm; extract     |
|        |                        | extract color blank.  |                       | blank is required."   |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case D | Multiple Comparisons   | > 2 doses compared to | Pre-planned Dunnett or| ADVISORY:             |
|        | Multiplicity           | control using series  | Tukey post-hoc tests  | "Repeated t-tests     |
|        | (Type I Error)         | of unpaired t-tests.  | explicitly specified. | inflate Type I error; |
|        |                        |                       |                       | use ANOVA + Dunnett." |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case E | Serial Measurements    | Repeated observations | Mixed-effects model or| WARNING:              |
|        | (Non-Independence)     | over time analyzed by | repeated-measures     | "Serial timepoints    |
|        |                        | standard factorial    | ANOVA specified.      | from same unit require|
|        |                        | ANOVA.                |                       | repeated-measures."   |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
| Case F | Sample Size Rigor      | N=3 claimed in high-  | Formal a priori power | ADVISORY:             |
|        | ("N=3" Fallacy)        | variability in vivo   | calculation reported  | "N=3 is underpowered  |
|        |                        | animal or clinical set| (alpha, beta, delta). | for in vivo studies   |
|        |                        | without power calc.   |                       | without power calc."  |
+--------+------------------------+-----------------------+-----------------------+-----------------------+
```

*Mandatory Epistemic Fallback:* If a proposal draft or paper provides insufficient details to evaluate any safety case, the engine outputs:
> `"Insufficient methodological information to assess this parameter."`

---

## 5. Corrected Gold-Standard Benchmark Specification

### 5.1 Cohort Architecture
- **Stage 0 Pilot Benchmark ($N = 20$ papers):** 5 papers per domain. Freezes guidelines, tests inter-annotator agreement, and calibrates ECE.
- **Stage 6 Full Benchmark ($N = 100$ papers):**
  - 25 Botanical & Natural Product Pharmacognosy (extracts, HPLC, MTT, Griess).
  - 25 Synthetic Biology & Metabolic Engineering (promoters, plasmids, chassis engineering).
  - 25 Molecular Pharmacology & Oncology (kinase inhibitors, Western blots, flow cytometry).
  - 25 Preclinical In Vivo Pharmacology (mouse models, pharmacokinetic absorption, toxicology).
- **Mandatory Quotas:**
  - Minimum 20 Multi-factorial designs ($2 \times 2$ or higher).
  - Minimum 15 Longitudinal repeated-measures designs.
  - Minimum 15 Dose-response studies with non-linear regression curves.

### 5.2 Annotation Protocol and Adjudication Team
- **Annotators:**
  - Annotator 1: Ph.D. in Molecular Pharmacology.
  - Annotator 2: Ph.D. in Synthetic Biology / Biotechnology.
  - Annotator 3 (Biostatistical Adjudicator): Ph.D. / M.S. in Biostatistics.
- **Adjudication:** Double-blind annotation $\to$ Automated discrepancy calculation $\to$ Consensus review meeting led by biostatistician $\to$ Frozen Gold-Standard JSON Fixture.

---

## 6. Corrected Quantitative Performance Metrics Matrix

```
+--------------------------------------------------------------------------------------------------------------------------------------------------+
|                                              CORRECTED QUANTITATIVE PERFORMANCE METRIC MATRIX                                                    |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| #  | Metric Name           | Corrected Mathematical Definition        | Evaluation Unit       | Target Threshold    | Defensibility Status       |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 1  | Methodological Entity | Token-level Macro-F1 across classes      | Entity spans & types  | Macro-F1 >= 0.82    | Scientifically Justified   |
|    | Extraction            | (Jaccard overlap >= 0.70 for relaxed)    | (Strict & Relaxed)    | (Strict >= 0.75)    |                            |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 2  | Relational Graph      | Macro-averaged F1 on directed relational | Directed Triples      | Macro-F1 >= 0.78    | Scientifically Justified   |
|    | Extraction            | triples: (head, relation, tail)          | (P >= 0.82, R >= 0.75)|                     | (Corrects Accuracy Flaw)   |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 3  | Experimental Design   | Multi-label Macro-F1 across 8            | Multi-label vector    | Macro-F1 >= 0.82    | Scientifically Justified   |
|    | Classification        | non-mutually exclusive archetypes        | per document          | Hamming Loss <= 0.08| (Corrects Single-Label)    |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 4a | Surfaced Quote        | Fraction of displayed quotes verified by | Surfaced text quotes  | Precision = 1.00    | Mandatory Production Gate  |
|    | Grounding Gate        | exact normalized string match            | (UI displays)         | (Zero Hallucinations| (Strict Rejection Rule)    |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 4b | Span Extraction       | Fraction of extracted evidence spans     | Character offset      | Precision >= 0.95   | Scientifically Justified   |
|    | Precision             | matching expert ground-truth span        | spans [start, end]    |                     |                            |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 5a | Control Hallucination | False Discovery Proportion:              | Extracted control     | FDP <= 0.05         | Scientifically Justified   |
|    | Rate (FDP)            | FP_control / (TP_control + FP_control)   | entities              |                     | (Corrects Undefined Formula)
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 5b | False Control Omission| Rate of falsely accusing an author/draft | Executed control      | Error Rate <= 0.04  | Critical Educational Gate  |
|    | Rate (Audit Type I)   | of missing a control that exists         | audit checks          |                     | (Prevents Bad Audits)      |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 6  | Statistical           | Quadratic Weighted Kappa and concordance | Multi-tier biostat    | Weighted K >= 0.78  | Requires Pilot Data to     |
|    | Appropriateness       | against biostatistician gold standard    | evaluation verdict    | Concordance >= 0.82 | Calibrate Edge Cases       |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 7  | Expected Calibration  | Adaptive Quantile Binned ECE across      | Binned extraction     | Adaptive ECE <= 0.08| Provisional Engineering    |
|    | Error (Adaptive ECE)  | 10 equal-frequency probability bins      | confidence scores     | Brier Score <= 0.12 | Target (Needs Testing)     |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
| 8  | Inter-Annotator       | Gwet's AC1 (rare classes) and Cohen's    | Human annotation      | Gwet AC1 >= 0.80    | Benchmark Quality Gate     |
|    | Agreement             | Kappa (balanced classes)                 | agreement matrix      | Cohen K >= 0.80     | (Separated from Model F1)  |
+----+-----------------------+------------------------------------------+-----------------------+---------------------+----------------------------+
```

---

## 7. System Architecture and LLM Provider Abstraction

### 7.1 Abstract Provider Interface (`BaseLLMClient`)

```python
"""
Abstract Interface for LLM Providers in BioWriter Studio.
Guarantees vendor neutrality, privacy firewalls, and offline test replay.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMClient(ABC):
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
        """Returns provider identifier: 'gemini', 'openai', 'local_vllm', 'mock_replay'."""
        pass

    @abstractmethod
    def is_privacy_compliant_for_student_data(self) -> bool:
        """Returns True only if provider guarantees zero retention / on-premise execution."""
        pass
```

### 7.2 Data Privacy Firewall Rule
- **Public Literature Papers (DOIs, PubMed Central XML):** Permitted to route to approved Cloud APIs (Google Gemini, OpenAI).
- **Student Proposal Drafts & Faculty Feedback:** **STRICTLY CONFINED** to local inference (e.g. BioMistral 7B via vLLM / Ollama) or offline rule-based triage. Never sent to commercial cloud endpoints without explicit institutional DPA.

---

## 8. Persistence and Data Storage Design

### 8.1 SQLite Document-Relational Schema
Rather than introducing the operational overhead of a dedicated graph database (Neo4j), BioWriter Studio utilizes SQLite with JSONB columns and `NetworkX` in-memory graph operations:

```sql
CREATE TABLE IF NOT EXISTS methodology_graphs (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    doi TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graph_json TEXT NOT NULL,  -- Pydantic v2 JSON representation
    content_fingerprint TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS methodology_human_overrides (
    override_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    field_path TEXT NOT NULL,
    original_value TEXT,
    overridden_value TEXT NOT NULL,
    overridden_by TEXT NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES methodology_graphs(document_id)
);
```

### 8.2 Data Isolation Guarantee
- The 54 existing baseline files in `upload/data/` remain untouched.
- Methodology records are persisted under `upload/data/methodology_graphs/` with atomic write semantics (`_atomic_write_file`).

---

## 9. Student and Faculty User Experience Specification

### 9.1 Student Experience MVP
1. **Assay-to-Measurement Traceability Table:** Live matrix linking Aim $\to$ Hypothesis $\to$ Assay $\to$ Replicates $\to$ Planned Statistical Test.
2. **Control Completeness Checklist:** Visual checkmark list showing presence of Negative Untreated, Vehicle, Benchmark Positive, and Color Blanks.
3. **Inferred Limitations Callout:** Highlights methodological boundaries (e.g. in vitro cell lines cannot represent systemic pharmacokinetics).

### 9.2 Faculty Review Experience MVP
1. **1-Click Methodological Soundness Audit:** Instant breakdown of controls, sample size justification, and statistical appropriateness.
2. **Pseudoreplication Alert Badge:** Red traffic-light alert when technical well repeats are mislabeled as biological replicates.
3. **Literature Quote Drawer:** Slide-over drawer displaying the verbatim source quote, character offsets, and publication DOI.
4. **Human Review Override:** Editable pencil tool allowing faculty to adjust or override any automated classification.

---

## 10. Implementation-Ready Staged Roadmap

```
+---------------------------------------------------------------------------------------------------------+
|                                    IMPLEMENTATION-READY ROADMAP                                         |
+---------------------------------------------------------------------------------------------------------+
|  STAGE 0: Pilot Benchmark & Annotation Guideline Freezing                       [Duration: 4 Weeks]    |
|  * Scope: Annotate 20 papers (5 per domain) with 2 molecular biologists & 1 biostatistician.             |
|  * Deliverables: Frozen annotation guidelines, gold-standard JSON fixtures, agreement report.          |
|  * Exit Gate: Gwet's AC1 >= 0.80, Fleiss' Kappa >= 0.75 across pilot set.                               |
|                                                                                                         |
|  STAGE 1: Schema Implementation & Model Infrastructure                           [Duration: 2 Weeks]    |
|  * Scope: Create core/methodology_models.py (Pydantic v2 schemas) and SQLite persistence adapter.       |
|  * Deliverables: Unit-tested Pydantic models, JSON serialization, SQLite schema migrations.              |
|  * Exit Gate: 100% test coverage on schema validation; zero mutation of existing 54 data files.         |
|                                                                                                         |
|  STAGE 2: Grounding & Evidence Extraction Pipeline                               [Duration: 3 Weeks]    |
|  * Scope: Build BaseLLMClient abstraction, verbatim quote normalizer, and character offset verifier.   |
|  * Deliverables: core/evidence_verifier.py, multi-provider LLM connector (Cloud & Local).               |
|  * Exit Gate: Surfaced Quote Precision = 1.00 (zero ungrounded quotes allowed through gate).            |
|                                                                                                         |
|  STAGE 3: Experimental Design & Control Engine (Biotech MVP)                     [Duration: 3 Weeks]    |
|  * Scope: Build core/methodology_engine.py; semantic control and replicate classification.              |
|  * Deliverables: Control classification engine, biological vs technical replicate parser.               |
|  * Exit Gate: False Control Omission Rate <= 0.04; Control Hallucination Rate (FDP) <= 0.05 on pilot set.|
|                                                                                                         |
|  STAGE 4: Statistical Validity & Methodological Reasoning Engine                 [Duration: 2 Weeks]    |
|  * Scope: Build core/statistical_auditor.py implementing Safety Rules A - F.                            |
|  * Deliverables: Automated statistical assumption & test appropriateness critique module.                |
|  * Exit Gate: Weighted Kappa >= 0.78 against biostatistician gold standard on pilot set.                |
|                                                                                                         |
|  STAGE 5: System Integration & Literature Cross-Validation                       [Duration: 2 Weeks]    |
|  * Scope: Wire methodology engine to audit_rules.py, copilot_brain.py, and draft_store.py.              |
|  * Deliverables: Cross-validation checking student proposals against cited literature protocols.        |
|  * Exit Gate: Zero regression in existing 210 tests; thread-safe atomic draft persistence intact.       |
|                                                                                                         |
|  STAGE 6: UI Visualization & 100-Paper Benchmark Release Closure                 [Duration: 3 Weeks]    |
|  * Scope: Implement Traceability Table, Literature Quote Drawer, and complete 100-paper validation.     |
|  * Deliverables: Frontend UI integration, final benchmark evaluation report across all 8 metrics.       |
|  * Exit Gate: All 8 quantitative acceptance metrics met on full 100-paper benchmark suite.              |
+---------------------------------------------------------------------------------------------------------+
```

---

## 11. Authoritative Sign-Off and Conformance Attestation

This Corrected Scientific Architecture Specification has been independently audited and verified against the actual BioWriter Studio baseline.
- **Data Protection:** 54/54 persistent data files in `upload/data/` verified intact and bit-identical.
- **Codebase Integrity:** Zero source code or test files were mutated during this audit.
- **Readiness:** Upon formal stakeholder approval of the Decision Register in the accompanying Review Report, this document serves as the sole implementation-ready engineering blueprint for Phase 4.2.1.
