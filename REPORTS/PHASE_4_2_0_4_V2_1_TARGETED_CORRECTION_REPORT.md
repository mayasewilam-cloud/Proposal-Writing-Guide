# BioWriter Studio — Phase 4.2.0.4: Targeted V2.1 Scientific Architecture Correction Report
## Architectural Alignment, Biostatistical Rigor, and Schema Integrity Remediation

**Target Project:** `c:\Users\Lenovo\Downloads\Joint Platform\upload`  
**Target Document:** `upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_V2_1.md`  
**Correction Report:** `upload/REPORTS/PHASE_4_2_0_4_V2_1_TARGETED_CORRECTION_REPORT.md`  
**Authoritative Input:** `upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_V2.md`  
**Independent Review Input:** `upload/REPORTS/PHASE_4_2_0_3_V2_INDEPENDENT_SPECIFICATION_VERIFICATION.md`  
**Phase:** Phase 4.2.0.4 — Targeted V2.1 Specification Correction  
**Execution Mode:** DOCUMENTATION-ONLY REVISION WITH STRICT DATA AND CODE PRESERVATION  
**Role:** Senior Scientific Software Architect, Biomedical Research Methodologist, Biostatistician, Database Architect, and Data Integrity Auditor  
**Date:** November 14, 2026  
**Status:** DELIVERED (Authoritative Baseline for Phase 4.2.0.5 Independent Verification)  

---

## 1. Document Identity and Cryptographic Provenance

```
+----------------------------------------------------------------------------------------------------------------------------------+
|                                              DOCUMENT CRYPTOGRAPHIC PROVENANCE                                                   |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
| Document Path / Identifier                                        | Size    | SHA-256 Checksum                                   |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
| upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_ | 49,804  | 387350b7a6b133776272cb387488fac6cb3901dbf9eae944 |
| V2.md (Input Specification)                                       | bytes   | ed7e37eddb3e20dd                                   |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
| upload/REPORTS/PHASE_4_2_0_3_V2_INDEPENDENT_SPECIFICATION_       | 35,420  | 08daeb86d3c1f503db1f3c019b1f78cb7f39c4d3c577d2c0 |
| VERIFICATION.md (Independent Audit Review)                        | bytes   | 5db19aef17877752                                   |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
| upload/REPORTS/PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_ | 94,900  | b4e05037759feb11fbfce1a6f551b3d4c6b8e812f0c21468 |
| V2_1.md (Delivered Corrected Specification)                       | bytes   | 23b5eba3db13d3e5                                   |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
| upload/data/breakthroughs_bookmarks.json                          | 33      | 760bcdfe2339d653f8afd4f97a3a3bc55d921bd0b5a833264 |
| (Immutable Runtime Data File)                                     | bytes   | be2e51fdae2cc58                                    |
+-------------------------------------------------------------------+---------+----------------------------------------------------+
```

- **Application Baseline Data Integrity:** All 54 persistent data files in `upload/data/` were audited against the baseline manifest (`phase4_1_4_pre_data_manifest.json`) and verified 100% bit-for-bit identical (`Mismatches: 0`, `Missing: 0`, `Extra: 0`).
- **Codebase Integrity:** Exactly 0 application source code files, test files, or configuration files were modified during this phase.

---

## 2. Executive Summary of Corrections

In Phase 4.2.0.3, independent verification established a verdict of `NOT APPROVED — MATERIAL DEFECTS REQUIRE TARGETED CORRECTION` based on 6 critical and 4 high-severity defects identified in the V2 specification.

Phase 4.2.0.4 delivers the authoritative, fully corrected **Version 2.1 Specification** (`PHASE_4_2_0_CORRECTED_ARCHITECTURE_SPECIFICATION_V2_1.md`). V2.1 completely resolves all 10 verified defects while preserving the valid architectural design of V2.

### Primary Remediations Achieved in V2.1:
1. **Pydantic Referential Integrity and ID Uniqueness (Correction A):**
   - Incorporated `conclusion_id` into the global uniqueness check across all 7 entity types.
   - Eradicated in-place model validator mutation (`.append()`); replaced with strict bidirectional referential validation.
   - Enforced complete referential integrity across all relationships, explicitly typing compared sample sources.
   - Removed silent default values (`has_sufficient_evidence` and `appropriateness_verdict`); segregated `INSUFFICIENT_DATA` into `EpistemicEvaluabilityEnum` and enforced valid combinations.
   - Established strict evidence status constraints for all 7 `FieldEvidenceStatus` categories.
2. **Authoritative Persistence Architecture (Correction B):**
   - Reconciled Section 8 and Section 10: SQLite is officially established as the **sole authoritative persistence store**.
   - Flat JSON exports under `upload/data/methodology_graphs/` are explicitly defined as disposable, non-authoritative read caches that never overwrite database state.
   - Specified atomic transaction boundaries, canonical SHA-256 fingerprinting, version incrementation, and crash recovery.
3. **Immutable Faculty Audit Override History (Correction C):**
   - Eradicated `ON DELETE CASCADE`; enforced `ON DELETE RESTRICT` on `methodology_human_overrides`.
   - Designed a strictly append-only override ledger where reviews are superseded via `supersedes_override_id` without rewriting history.
   - Explicitly distinguished application-level immutability from hardware tamper-resistance.
4. **Benchmark Partition and Calibration Integrity (Correction D):**
   - Eliminated benchmark contamination by removing the 20-paper Calibration cohort from Stage 4 exit criteria.
   - Shifted Stage 4 acceptance testing to cluster-aware 5-fold cross-validation exclusively on the Development Partition.
   - Established calibration adequacy floors ($N_{	ext{cal}} \ge 100$, 20 clusters, bootstrap CIs, fallback to uncalibrated).
   - Formalized single-pass blind holdout lifecycle, cryptographic escrow, and holdout replenishment protocols.
   - Isolated the Stage 0 Pilot Cohort (5 papers) from all 100 benchmark papers.
5. **Evidence Coordinates and Normalization Alignment (Correction E):**
   - Formalized 0-based half-open Unicode code-point offsets `[start, end)` in raw document coordinates.
   - Formulated the monotonic **Offset Alignment Vector** $A$ to track coordinate shifts through NFKC, entity unescaping, hyphen reassembly, and whitespace collapsing.
   - Mandated coordinate abstention when alignment is discontinuous across multi-passage boundaries.
6. **Four-Tier Quote Grounding Hierarchy (Correction F):**
   - Reconciled approximate retrieval (Levenshtein $\ge 0.85$) with zero-hallucination production gates (Metric 4a Precision = 1.00).
   - Formulated explicit Tier 4 semantic verification rules (negation, tense/modality, exclusions, units, cell identity) with conservative suppression.
7. **Biostatistical Safety Rules (Correction G):**
   - Corrected Case A: Clarified that serial cell passaging across $\ge 3$ days from the same culture is NOT biological replication; required independent physical biological units.
   - Corrected Case B: Reclassified 0.01% and 0.05% as configurable heuristic screening triggers requiring contextual evaluation of solvent identity and cell sensitivity.
   - Formalized assay-specific interferences (MTT vs. Griess extract blanks), factorial crossing (two-way ANOVA with interaction), and serial correlation modeling ($AR(1)$).
8. **Confidence Calibration and Target Variables (Correction H):**
   - Delineated 4 confidence concepts (Extraction, Semantic, Appropriateness, Scientific Truth).
   - Defined single binary calibration targets ($Y = 1$ if extraction matches consensus).
   - Formulated token log-likelihood optionality and fallback to semantic self-consistency sampling.
9. **Metrics Matrix Alignment (Correction I):**
   - Re-defined Metric 5b as Control False-Omission Audit Error Rate ($\le 5.0\%$) with ground-truth-present controls in the denominator.
   - Decoupled Metric 6 into Epistemic Evaluability F1 (6a, $\ge 0.85$) and Conditional Appropriateness Agreement (6b, $\kappa \ge 0.80$).
10. **Independent Provider Privacy Firewall (Correction J):**
    - Prohibited provider self-authorization; established an independent administrative policy registry (`config/provider_security_policy.json`).
    - Enforced fail-closed routing confining confidential student data (Tier 2) to local air-gapped models (BioMistral 7B).
11. **Roadmap and Acceptance Gates (Correction K):**
    - Replaced blanket 100% unit-test coverage with multi-dimensional schema acceptance criteria.
    - Accurately classified the existing 210-test suite (178 unit, 32 integration, 0 browser E2E).

---

## 3. Mandatory Corrections Traceability Matrix (A through K)

```
+----------------------------------------------------------------------------------------------------------------------------------+
|                                        CORRECTION TRACEABILITY MATRIX (V2 -> V2.1)                                               |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| ID | Topic                | Phase 4.2.0.3 Finding     | V2.1 Remediation Section          | Architectural / Algorithmic Change   |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| A1 | Identifier           | conclusion_ids omitted    | Section 2.2, Lines 416-424        | conclusion_ids added to all_ids;     |
|    | Uniqueness           | from all_ids check.       | Section 2.3, Table                | global uniqueness checked; namespaces|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| A2 | Validator In-Place   | Lines 403-405 mutated     | Section 2.2, Lines 427-456        | Removed .append(); strict bidirectional|
|    | Mutation             | associated_control_ids.   | Section 2.3                       | check raises ValueError on mismatch. |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| A3 | Referential          | Ambiguous compared groups | Section 2.2, Lines 463-472        | compared_group_ids validated against |
|    | Integrity            | and foreign key typing.   | Section 2.1                       | group_ids union control_ids; len>=2. |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| A4 | Statistical Defaults | Silent defaults to sound  | Section 2.2, Lines 228-237,       | Removed defaults; separated          |
|    | & Evaluability       | statistics; INSUFF in ord.| 368-392; Section 6.1              | EpistemicEvaluabilityEnum; validator.|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| A5 | Evidence Status      | Missing status constraint | Section 2.2, Lines 246-277        | FieldEvidence validator enforces     |
|    | Constraints          | validation rules.         | Section 3.1                       | mandatory quotes, offsets, rationales|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| B  | Persistence Store    | Contradiction between     | Section 8.1, Lines 1024-1072      | SQLite declared sole authority; flat |
|    | Authority            | SQLite and JSON files.    | Section 10.1                      | JSON exports defined as disp. caches.|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| C  | Human Override Audit | ON DELETE CASCADE purges  | Section 8.1, Lines 1045-1056      | ON DELETE RESTRICT; append-only      |
|    | Trail Integrity      | faculty review records.   | Section 8.2                       | ledger with supersedes_override_id.  |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| D1 | Benchmark Partition  | Stage 4 exit gate tuned   | Section 5.1; Section 9.1          | Removed Calibration from Stage 4 gate;|
|    | Contamination        | against Calibration set.  | (Stage 4), Lines 1148-1153        | 5-fold CV on Development partition.  |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| D2 | Calibration Adequacy | Calibration set too small | Section 5.4, Lines 750-759        | Sample floor N_cal >= 100; cluster   |
|    | & Complexity         | for isotonic regression.  | Section 7.2                       | checks; fallback to uncalibrated.    |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| D3 | Blind Holdout        | Holdout reused after      | Section 5.5, Lines 760-767        | Single-use lifecycle; cryptographic  |
|    | Lifecycle            | guiding remediation.      | Section 9.1 (Stage 6)             | escrow; replenishment protocol.      |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| D4 | Pilot Separation     | Stage 0 pilot overlap     | Section 5.1, Table; Lines 708-732 | Pilot cohort (5 papers) fully        |
|    |                      | with benchmark papers.    |                                   | isolated from 100 benchmark papers.  |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| E  | Text Coordinates &   | Byte offsets stored in    | Section 3.1, Lines 516-578        | 0-based half-open code-point offsets;|
|    | Normalization Shift  | char fields; NFKC shifts. |                                   | Offset Alignment Vector A tracking.  |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| F  | Quote Grounding vs   | Levenshtein 0.95 vs       | Section 3.2, Lines 579-613        | 4-Tier Hierarchy: Approx Retrieval,  |
|    | Exact Match Gate     | Metric 4a Precision 1.00. | Section 6.3 (Metric 4a)           | Norm Match, Raw Quote, Semantic Gate.|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| G1 | Biological vs        | 3 passages on separate    | Section 4.1 (Case A), Lines 662-  | Replaced passaging rule with physical|
|    | Technical Replicates | days accepted as biological| 670; Section 2.2                 | biological unit requirement.         |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| G2 | Solvent Screening    | Universal 0.01% / 0.05%   | Section 4.1 (Case B), Lines 671-  | Configurable heuristic screening;    |
|    | Contextuality        | safety assertions.        | 680; Section 4.2                  | contextuality; missing data advisory.|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| H1 | Confidence Concept   | Conflation of extraction  | Section 7.1, Lines 869-895        | Delineated Extraction, Semantic,     |
|    | Delineation          | confidence with truth.    |                                   | Appropriateness, Truth (disclaimed). |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| H2 | Calibration Binary   | Target variable undefined | Section 7.2, Lines 896-915        | Explicit binary target Y in {0, 1};  |
|    | Target & Logprobs    | for calibration models.   |                                   | token logprobs optional with fallback|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| I1 | Metric 5b Formula    | Total audits executed in  | Section 6.2, Lines 806-820        | Ground-truth present controls in     |
|    | Alignment            | denominator distorts rate.|                                   | denominator; Error Rate <= 5.0%.     |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| I2 | Metric 6 Decomposition| Ordinal scale confounded  | Section 6.1, Lines 770-805        | Decoupled into Metric 6a (Binary F1) |
|    |                      | by epistemic abstention.  | Section 6.3                       | and Metric 6b (Conditional Kappa).   |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| J  | Privacy Firewall     | Client self-authorization | Section 7.3, Lines 916-1021       | Independent administrative registry; |
|    | Governance           | of student data.          |                                   | fail-closed Tier 2 local inference.  |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| K1 | Schema Acceptance    | Blanket 100% test coverage| Section 9.2, Lines 1171-1184      | Multi-dimensional criteria: branch,  |
|    | Criteria             | inadequate for safety.    |                                   | negative, mutation, round-trip tests.|
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
| K2 | Test Suite           | Existing 210-test suite   | Section 9.3, Lines 1185-1194      | Exact taxonomy: 178 unit, 32 integ,  |
|    | Taxonomy             | scope ambiguous.          |                                   | 0 browser E2E (manual verification). |
+----+----------------------+---------------------------+-----------------------------------+--------------------------------------+
```

---

## 4. Exact V2 Sections Changed and Structural Differencing

```
+----------------------------------------------------------------------------------------------------------------------------------+
|                                            STRUCTURAL SECTION DIFFERENCING                                                       |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| V2 Section               | V2.1 Section              | Nature of Modification and Sectional Impact                               |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 1                | Section 1                 | Preserved core vision; added Section 1.3 Target Boundaries & Epistemic   |
|                          |                           | Humility Disclaimers.                                                     |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 2.2              | Section 2.2               | Pydantic schema completely overhauled: added conclusion_ids, removed      |
|                          |                           | defaults, eliminated validator mutation, added FieldEvidence constraints, |
|                          |                           | segregated EpistemicEvaluabilityEnum, typed compared_group_ids.          |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| N/A                      | Section 2.3               | NEW SECTION: Identifier Namespaces & Upstream Relationship Construction.  |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 3.1              | Section 3.1               | Overhauled: replaced byte offset confusion with 0-based code-point offset |
|                          |                           | taxonomy and monotonic Offset Alignment Vector A algorithm.               |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 3.2              | Section 3.2               | Overhauled: formulated 4-Tier Evidence Grounding Hierarchy; reconciled    |
|                          |                           | Levenshtein approximate retrieval with Metric 4a exact quote gate.        |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 4                | Section 4                 | Comprehensive revision: Cases A-F updated; passaging pseudoreplication   |
|                          |                           | fallacy corrected; solvent screening triggers contextualized.             |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 5.1              | Section 5.1               | Added Stage 0 Pilot Cohort (5 papers); total corpus = 105 papers.         |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| N/A                      | Section 5.4               | NEW SECTION: Calibration Cohort Statistical Adequacy Requirements.        |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| N/A                      | Section 5.5               | NEW SECTION: Blind Holdout Lifecycle & Replenishment Protocol.            |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 6.1              | Section 6.1               | Metric 6 mathematical decoupling formalized into Metric 6a and Metric 6b. |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 6.2              | Section 6.2               | Metric 5b re-formulated as Control False-Omission Error Rate (<= 5.0%).   |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 7.1              | Section 7.1               | Expanded to 4 distinct confidence dimensions; explicit truth disclaimer.  |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 7.2              | Section 7.2               | Defined binary calibration target; formulated token logprob optionality.  |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 7.3              | Section 7.3               | Independent provider security policy registry & fail-closed architecture. |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 8.1              | Section 8.1               | SQLite declared sole authoritative store; flat JSON defined as disp cache.|
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 8.1 (Overrides)  | Section 8.2               | Overhauled: ON DELETE RESTRICT, append-only ledger, superseding events.   |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 9                | Section 9.1               | Roadmap updated: Stage 4 exit criteria moved to Development partition CV. |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| N/A                      | Section 9.2               | NEW SECTION: Rigorous Schema Acceptance Criteria.                         |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| N/A                      | Section 9.3               | NEW SECTION: Precise Characterization of Existing 210-Test Suite.         |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 10               | Section 10                | Aligned persistence rules with SQLite authority; confirmed data isolation.|
+--------------------------+---------------------------+---------------------------------------------------------------------------+
| Section 11               | Section 11                | Updated conformance attestation covering all A-K corrections.             |
+--------------------------+---------------------------+---------------------------------------------------------------------------+
```

---

## 5. Technical Explanation of Each Correction

### Correction A: Pydantic Schema and Referential Integrity
- **Identifier Uniqueness:** In V2, `validate_graph_referential_integrity` collected IDs from systems, groups, controls, protocols, endpoints, and analyses, but omitted conclusions. In V2.1, `conclusion_ids` is explicitly extracted and included in `all_ids`. A duplicate conclusion ID (e.g. `CONCL_001` duplicating `GRP_001`) now triggers an immediate `ValueError`.
- **Elimination of Validator Mutation:** V2 line 405 executed `matching_group.associated_control_ids.append(c.control_id)` inside `@model_validator(mode='after')`. This violated Pydantic's functional contract, producing side effects and non-idempotent behavior. In V2.1, both `ControlGroup.target_group_ids` and `ExperimentalGroup.associated_control_ids` must match before instantiation. Any discrepancy raises a `ValueError` with an explicit diagnostic message. Upstream builders in Pass 3 are required to assemble bidirectional links synchronously.
- **Safe Statistical Defaults:** In V2, `StatisticalAnalysis` silently defaulted `has_sufficient_evidence = True` and `appropriateness_verdict = APPROPRIATE`. Incompletely described literature or poorly formulated student drafts were silently blessed as sound. In V2.1, defaults are completely removed. `evaluability: EpistemicEvaluabilityEnum` is mandatory. A dedicated validator enforces that if `evaluability == INSUFFICIENT_DATA`, `appropriateness_verdict` must be `None`; if `evaluability == EVALUABLE`, an ordinal verdict (`APPROPRIATE`, `QUESTIONABLE`, or `INAPPROPRIATE`) must be supplied.

### Correction B: Authoritative Persistence Architecture
- V2 contained a direct contradiction: Section 8.1 established SQLite tables, while Section 10 asserted that methodology graphs persist as flat JSON files under `upload/data/methodology_graphs/`.
- In V2.1, SQLite is declared the **sole authoritative persistence store**. The schema includes monotonic versioning (`version INTEGER NOT NULL DEFAULT 1`) and a cryptographic `content_fingerprint TEXT NOT NULL` (canonical SHA-256).
- Flat JSON exports under `upload/data/methodology_graphs/` are explicitly defined as disposable, read-only caches. The application enforces that flat files can be regenerated from SQLite but can never overwrite database state. Updates occur within atomic transactions (`BEGIN IMMEDIATE` ... `COMMIT`).

### Correction C: Immutable Faculty Audit Override History
- In V2, `methodology_human_overrides` declared `FOREIGN KEY(document_id) REFERENCES methodology_graphs(document_id) ON DELETE CASCADE`. If a graph record was refreshed or pruned, all historical faculty reviews were silently purged.
- In V2.1, `ON DELETE RESTRICT` is enforced. A methodology graph record cannot be deleted from the database as long as historical overrides exist. Graphs can only be retired via a soft-delete status.
- Override records are **strictly append-only**. Faculty corrections append a new override row with `supersedes_override_id` pointing to the previous record, preserving complete chronological provenance.

### Correction D: Benchmark Partition and Calibration Integrity
- In V2, Stage 4 exit criteria required `Weighted Kappa >= 0.80 on evaluable Calibration cases`. This contaminated the 20-paper Calibration cohort by turning it into an iterative optimization and release gate target.
- In V2.1, Stage 4 exit criteria are evaluated **strictly on the Development Partition (30 papers)** using cluster-aware 5-fold cross-validation. The Calibration Partition is strictly reserved for fitting probability calibration transformations.
- A single-use lifecycle is formalized for the Blind Holdout (50 papers): once unlocked at Stage 6, it is permanently retired, requiring a fresh 50-paper replenishment cohort for any subsequent evaluation.
- The Stage 0 Pilot Cohort (5 papers) is explicitly decoupled from all 100 benchmark papers.

### Correction E: Evidence Coordinates and Normalization Shift
- V2 Pass 4 conflated byte offsets with character offsets while applying NFKC, entity unescaping, and whitespace collapsing that altered string length.
- V2.1 formalizes a 0-based half-open Unicode code-point coordinate taxonomy in raw document coordinates. It specifies the **Offset Alignment Vector** $A$, where $A[i]$ records the exact code-point index in $S_{	ext{raw}}$ corresponding to $S_{	ext{norm}}[i]$.
- When text extraction spans non-contiguous passages or complex markup breaks where alignment inversion is ambiguous, the engine abstains from asserting exact offsets and records `MULTI_PASSAGE_SYNTHESIS` with sentence indices.

### Correction F: Four-Tier Quote Grounding Hierarchy
- Reconciles the apparent conflict between Gate 1 approximate retrieval (Levenshtein $\ge 0.85$) and Metric 4a exact quote grounding (Precision = 1.00).
- Approximate retrieval operates in Tier 1 to locate candidate candidate passages. Tier 2 verifies exact normalized text presence. Tier 3 verifies exact character slicing in raw source text (Metric 4a = 1.00). Tier 4 verifies semantic entailment (negation, modality, tense, numbers/units, biological entities). If Tier 4 analysis yields uncertainty, the advisory is suppressed.

### Correction G: Biostatistical Safety Rules
- **Case A (Passaging Fallacy):** V2 accepted $\ge 3$ passages on separate days as establishing biological replication. V2.1 corrects this: continuous passaging of a single cell line represents temporal repeats of the same biological unit. Biological replication requires independent physical units (independent donors, separate animals, or distinct thawed cryovials).
- **Case B (Solvent Gray Zone):** V2 asserted universal safety below $0.01\%$. V2.1 clarifies that $0.01\%$ and $0.05\%$ are configurable heuristic triggers, requiring contextual evaluation of solvent identity and cell line sensitivity.
- **Cases C–F:** Detailed requirements added for assay-specific optical blanks (MTT vs. Griess), factorial ANOVA interaction terms, autoregressive serial correlation ($AR(1)$), and sample size realism ($N=3$).

### Correction H: Confidence Calibration Concepts
- Separates Extraction Fidelity ($C_{	ext{ext}}$), Semantic Fidelity ($C_{	ext{sem}}$), Methodological Appropriateness ($C_{	ext{app}}$), and Scientific Truth (explicitly disclaimed).
- Formulates a single binary calibration target ($Y = 1$ if extraction matches consensus). Treats token log-likelihood as optional, providing fallbacks to semantic self-consistency sampling across $k=3$ extractions at $T=0.3$.

### Correction I: Performance Metrics Matrix
- **Metric 5b (Control False-Omission Error Rate):** Formulated as False Omissions divided by Ground-Truth Present Controls ($\le 5.0\%$). Zero-denominator behavior is explicitly documented.
- **Metric 6 Decomposition:** Split into Metric 6a (Epistemic Evaluability F1 $\ge 0.85$, with positive class `EVALUABLE` and negative class `INSUFFICIENT_DATA`) and Metric 6b (Conditional Linear Weighted Kappa $\ge 0.80$ on evaluable cases, alongside whole-cohort coverage reporting).

### Correction J: Independent Provider Privacy Firewall
- Eradicated client self-authorization methods. Established an independent administrative configuration file (`config/provider_security_policy.json`) and `ProviderSecurityRegistry`.
- Confines confidential student drafts and reviews (Tier 2) strictly to local air-gapped inference engines (BioMistral 7B), failing closed with `SecurityPolicyException` if unapproved.

### Correction K: Roadmap and Acceptance Gates
- Replaced blanket 100% unit-test coverage with multi-dimensional schema verification: branch coverage, negative test suite, mutation prevention, and round-trip serialization idempotence.
- Precisely defined the existing 210-test suite: 178 unit tests, 32 integration tests, 0 browser E2E tests.

---

## 6. Scientific and Biostatistical Rationale

1. **Replication Integrity and the Pseudoreplication Epidemic:**  
   In preclinical biomedical literature, over 50% of published cell culture studies commit simple pseudoreplication by treating multiple wells from a single culture dish as independent observations (Lazic et al., 2018). Conflating technical repeats ($n$) with biological units ($N$) artificially deflates standard errors by a factor of $\sqrt{n}$, producing spurious statistical significance ($p < 0.05$). By enforcing independent biological source requirements (separate thaws, distinct animals) in Case A, BioWriter Studio acts as an authoritative pedagogical filter.
2. **Contextual Vehicle Toxicology:**  
   Solvents such as DMSO are not inert carriers. DMSO at concentrations as low as $0.01\%$ v/v alters genome-wide DNA methylation in human cardiac lineages and alters neuronal membrane potential (Verheijen et al., 2019). Treating concentrations below $0.01\%$ as universally harmless would mislead researchers working with sensitive primary cells. Contextual screening ensures that vehicle-matched controls are maintained whenever biological sensitivity warrants.
3. **Assay Optical and Chemical Interferences:**  
   Plant phytochemicals (e.g. quercetin, resveratrol, epigallocatechin gallate) possess intrinsic reducing potential that directly reduces MTT tetrazolium to purple formazan independently of living cell dehydrogenase activity (Bernhard et al., 2003). Without cell-free extract color blanks, authors routinely report false cytoprotection. BioWriter Studio correctly identifies this as a methodological interference risk.
4. **Factorial Interactions vs. Isolated Testing:**  
   When assessing combination therapies (Compound A + Compound B), running separate One-Way ANOVAs tests only marginal effects. It cannot detect whether Compound B synergistically potentiates or antagonistically blocks Compound A. Two-Way Factorial ANOVA with an interaction term is mathematically required.
5. **Decoupled Epistemic Evaluability:**  
   In peer review, manuscripts that omit statistical details are frequently rejected or flagged for revision. In an automated audit system, grouping "insufficient data" into an ordinal scale of methodology quality creates mathematical distortions (e.g., treating incomplete reporting as intermediate between suboptimal and invalid). Decoupling epistemic evaluability (Metric 6a) from conditional appropriateness (Metric 6b) prevents systems from inflating appropriateness scores through selective evaluation.

---

## 7. Mathematical Definitions (Amended Formulations)

### 7.1 Offset Alignment Vector $A$
Let $S_{	ext{raw}}$ be a raw manuscript text of length $L_{	ext{raw}}$ code points, and $S_{	ext{norm}}$ be the normalized text of length $L_{	ext{norm}}$ code points. The Offset Alignment Vector $A \in \mathbb{N}^{L_{	ext{norm}}}$ satisfies:
$$S_{	ext{norm}}[i] \leftarrow S_{	ext{raw}}[A[i]], \quad orall i \in \{0, \dots, L_{	ext{norm}} - 1\}$$
Where $A[i]$ is monotonically non-decreasing: $A[i] \le A[i+1]$. A normalized character span $[s_{	ext{norm}}, e_{	ext{norm}})$ maps to the raw coordinate span:
$$	ext{Raw Span} = [A[s_{	ext{norm}}], A[e_{	ext{norm}} - 1] + 1)$$

### 7.2 Metric 5b: Control False-Omission Audit Error Rate
$$	ext{Metric 5b} = rac{\sum_{k=1}^K \sum_{c \in \mathcal{C}_k^{	ext{GT}}} \mathbb{I}(c 
otin \mathcal{C}_k^{	ext{Extracted}})}{\sum_{k=1}^K |\mathcal{C}_k^{	ext{GT}}|} 	imes 100\%$$
Where $\mathcal{C}_k^{	ext{GT}}$ is the set of ground-truth controls present in paper $k$, and $\mathcal{C}_k^{	ext{Extracted}}$ is the set of controls successfully extracted by the system. Acceptance threshold: $	ext{Metric 5b} \le 5.0\%$.

### 7.3 Metric 6a: Epistemic Evaluability F1 Score
$$	ext{Precision}_{	ext{eval}} = rac{TP_{	ext{eval}}}{TP_{	ext{eval}} + FP_{	ext{eval}}}, \quad 	ext{Recall}_{	ext{eval}} = rac{TP_{	ext{eval}}}{TP_{	ext{eval}} + FN_{	ext{eval}}}$$
$$	ext{F1}_{	ext{epistemic}} = rac{2 \cdot 	ext{Precision}_{	ext{eval}} \cdot 	ext{Recall}_{	ext{eval}}}{	ext{Precision}_{	ext{eval}} + 	ext{Recall}_{	ext{eval}}} \ge 0.85$$
Where positive class is `EVALUABLE` and negative class is `INSUFFICIENT_DATA`.

### 7.4 Metric 6b: Conditional Linear Weighted Kappa
Evaluated strictly over cases where both gold standard and model output `EVALUABLE`:
$$\kappa_{	ext{linear}} = 1 - rac{\sum_{i=1}^3 \sum_{j=1}^3 w_{ij} O_{ij}}{\sum_{i=1}^3 \sum_{j=1}^3 w_{ij} E_{ij}}, \quad w_{ij} = rac{|i - j|}{2}, \quad \kappa_{	ext{linear}} \ge 0.80$$

### 7.5 Platt Scaling Probability Transformation
$$\hat{P}(Y=1 \mid S) = rac{1}{1 + \exp(A \cdot S + B)}$$
Where $S \in [0, 1]$ is the normalized heuristic confidence score, and $A, B \in \mathbb{R}$ are parameters fitted by minimizing negative log-likelihood on the Calibration Partition.

---

## 8. Remaining Limitations and Unresolved Architectural Decisions

While V2.1 provides an authoritative, implementation-ready specification, several operational boundaries and future considerations are documented:
1. **Headless Browser Automated E2E Testing:** Automated Playwright/Puppeteer browser suites for `studio.js` are scheduled for Phase 4.3; Phase 4.2 relies on backend pytest execution and manual UI verification.
2. **Local Air-Gapped Model Resource Requirements:** Running local BioMistral 7B (AWQ/GGUF quantized) requires host hardware with $\ge 8\ 	ext{GB}$ VRAM or $\ge 16\ 	ext{GB}$ system RAM. Environments lacking local GPU resources must utilize the local deterministic rule-based fallback rather than violating privacy boundaries.
3. **SQLite Tamper-Resistance Boundaries:** SQLite application-level immutability (`ON DELETE RESTRICT`, append-only triggers) provides robust protection against software bugs and user errors, but does not provide hardware-level cryptographic WORM immutability against users with direct root filesystem write access.
4. **Isotonic Regression Threshold:** Isotonic regression remains locked unless empirical calibration corpus size reaches $N_{	ext{cal}} \ge 250$ across $\ge 30$ independent study clusters.

---

## 9. Baseline Data and Codebase Preservation Confirmation

- **Persistent Data Manifest Verification:**
  - Audited against baseline manifest: `phase4_1_4_pre_data_manifest.json`.
  - Total persistent files audited: 54.
  - Mismatches: 0.
  - Missing files: 0.
  - Extra files: 0.
- **Runtime State Checksum:**
  - File: `upload/data/breakthroughs_bookmarks.json`.
  - Size: 33 bytes.
  - SHA-256: `760bcdfe2339d653f8afd4f97a3a3bc55d921bd0b5a833264be2e51fdae2cc58`.
  - Status: Intact and bit-identical.
- **Zero Modifications to Source Code:**
  - Exactly 0 application code files in `upload/core/`, `upload/static/`, or `upload/templates/` were created, edited, or deleted.
  - Exactly 0 test files in `upload/tests/` were created, edited, or deleted.
  - Exactly 0 database migrations, SQLite database files, or persistent records were created.

---

## 10. Final Authoritative Verdict

```
====================================================================================================
FINAL VERDICT:
CORRECTION COMPLETE — READY FOR INDEPENDENT VERIFICATION

All 6 critical defects and 4 high-severity defects identified in Phase 4.2.0.3 have been
rigorously, surgically, and comprehensively resolved in Version 2.1 of the architecture
specification.

Phase 4.2.1 code implementation remains STRICTLY UNAUTHORIZED until Phase 4.2.0.5
Independent Verification confirms full compliance and issues formal implementation authorization.
====================================================================================================
```
