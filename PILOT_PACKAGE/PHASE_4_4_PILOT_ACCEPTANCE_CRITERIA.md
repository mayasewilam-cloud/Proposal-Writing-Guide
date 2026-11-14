# BioWriter Studio — Pilot Acceptance Criteria

**Document ID:** `PHASE_4_4_PILOT_ACCEPTANCE_CRITERIA.md`  
**Target Milestone:** Supervised Student Pilot Completion Gate (Phase 4.4 -> General Rollout)  
**Cohort Scope:** 2 Faculty Supervisors, 10 Graduate Students  
**Version:** 1.1.0-pilot (Post-Phase 4.4.1 Corrections)  
**Status:** Formal Acceptance Specification  

---

## 1. Overview and Purpose

This document establishes the measurable, empirical criteria required to determine whether the Supervised Student Pilot (Phase 4.4) is successful. Satisfying these criteria is the mandatory gate before BioWriter Studio can be approved for general, unsupervised student cohort deployment.

---

## 2. Pre-Condition: Pre-Deployment Smoke-Test Sign-Off

Prior to admitting the 10 graduate students into the pilot environment, the system administrator and lead faculty member must complete and sign off on the **8-Point Deployment Smoke-Test Checklist** defined in Section 9 of the [Pilot Deployment Runbook](file:///c:/Users/Lenovo/Downloads/Joint%20Platform/upload/PILOT_PACKAGE/PHASE_4_4_PILOT_DEPLOYMENT_RUNBOOK.md#9-final-deployment-smoke-test-checklist):
1. Individually attributable faculty authentication verified.
2. Student activation and login verified.
3. Student proposal creation, saving, and reopening verified.
4. Student cross-account data isolation verified.
5. Flowchart upload and cache fallback verified.
6. Faculty review, scoring, and feedback dispatch verified.
7. HTTPS termination, secure cookie flags, and network perimeter verified.
8. Backup snapshot and hash restoration verified.

---

## 3. Measurable Pilot Acceptance Criteria

```
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| #  | Criterion Category                     | Specific Measurable Target         | Verification Method      | Mandatory Threshold |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 01 | Student Onboarding & Claiming          | 10 out of 10 students claim their  | Faculty dashboard audit; | 100% (10/10)        |
|    |                                        | accounts using activation tokens.  | users.json status check. |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 02 | Session Authentication & Persistence   | 10 out of 10 students can log out  | Student self-report;     | 100% (10/10)        |
|    |                                        | and log back in without errors.    | server session logs.     |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 03 | Proposal Creation & Auto-Save          | All 10 students create proposals;  | Draft file inspection in | 100% (10/10)        |
|    |                                        | auto-save succeeds with no loss.   | pilot_data/drafts/.      |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 04 | Proposal Reopening & Integrity         | Students reopen drafts across      | Student verification;    | 100% (Zero text     |
|    |                                        | multiple sessions with zero loss.  | SHA-256 diff comparison. | loss allowed)       |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 05 | Student Data Isolation Boundary        | Zero instances of cross-student    | Server routing audit;    | 100% Isolation      |
|    |                                        | draft reads or writes.             | audit log verification.  | (0 breaches)        |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 06 | Flowchart Upload & Recovery            | Students successfully attach and   | Visual inspection in     | >= 90% (9/10)       |
|    |                                        | render workflow diagrams.          | studio preview & export. |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 07 | Deterministic Compliance Analysis      | Students execute compliance check; | UI status review;        | 100% (10/10)        |
|    |                                        | "Deterministic fallback" is visible| server agent logs.       |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 08 | Proposal Locking & Submission          | Students submit proposals; system  | Draft inspection;        | 100% (10/10)        |
|    |                                        | locks drafts against further edits.| lock flags verified.     |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 09 | Faculty Feedback Delivery              | Faculty reviews, scores, and       | Student UI inspection;   | 100% (10/10)        |
|    |                                        | dispatches evaluation feedback.    | draft JSON inspection.   |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 10 | Individual Faculty Attribution         | Both faculty members authenticate  | Audit trail inspection;  | 100% (Separate      |
|    |                                        | individually; actions attributed.  | actor_id non-repudiation.| accounts verified)  |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 11 | Privacy Disclosure Comprehension       | Privacy notice accessible and      | Student confirmation     | 100% (10/10)        |
|    |                                        | understood prior to drafting.      | acknowledgment.          |                     |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
| 12 | Zero Unresolved P0/P1 Incidents        | No open data loss, corruption, or  | Pilot Monitoring and     | 0 Open P0/P1        |
|    |                                        | access vulnerability incidents.    | Incident Register audit. | Incidents           |
+----+----------------------------------------+------------------------------------+--------------------------+---------------------+
```

---

## 4. Evaluation Protocol by Criterion

### Criterion 1 & 2: Account Claiming and Authentication
- **Test:** Each student receives an activation token from faculty, visits the HTTPS portal, clicks "Claim Account", enters their token, and sets a personal password.
- **Pass Rule:** The account's `"account_claimed"` status in `users.json` transitions from `false` to `true`. The student successfully logs in.

### Criterion 3 & 4: Proposal Drafting, Saving, and Reopening
- **Test:** Each student drafts at least: Title, Abstract, Specific Aims (3 aims), 5-Phase Methodology, and Flowchart caption. Edits auto-save across writing sessions. Browser is closed and reopened.
- **Pass Rule:** All drafted text, sections, and formatting are restored completely. No sections revert to empty or default templates.

### Criterion 5: Cross-Student Access Boundaries
- **Test:** Server logs and audit records are audited for unauthorized endpoint attempts. Students confirm they can only see their own work and assigned team workspace.
- **Pass Rule:** Exact server-side author binding (`student_id = session_sid`) prevents any unauthorized student from viewing or modifying another student's draft file. Zero unauthorized reads or writes occur.

### Criterion 6: Flowchart Diagram Upload
- **Test:** Students upload a PNG or JPG workflow diagram (under 5MB).
- **Pass Rule:** Image displays correctly in Section 4.2 preview and renders in generated manuscript views. If IndexedDB cache misses occur, the caption and fallback asset remain stable.

### Criterion 7: Deterministic Compliance Check
- **Test:** Each student clicks "Run Compliance Check".
- **Pass Rule:** The agent returns regulatory determinations (BSL level, recombinant DNA, human subjects, pathogen flags) without network timeout or error. The UI explicitly displays `Deterministic fallback` and `Extraction Mode: deterministic_rules`.

### Criterion 8 & 9: Submission, Locking, and Instructor Feedback
- **Test:** Students lock their proposals for grading. Faculty reviews the locked submission in `/faculty`, enters rubric scores, adds a memo, and clicks "Dispatch Evaluation".
- **Pass Rule:** The student's draft is locked against editing. When the student refreshes, the green Faculty Feedback Banner appears with the instructor's memo and scores.

### Criterion 10: Individual Faculty Attribution
- **Test:** Inspect server audit events (`pilot_data/agent_audit/*.jsonl`) for all evaluations, score entries, and token generation events.
- **Pass Rule:** Each event contains the specific instructor's identifier (`FAC-01`, `FAC-02`) rather than a shared generic credential.

### Criterion 11 & 12: Privacy Transparency & Zero Critical Incidents
- **Test:** Students review the Student Privacy Notice. Faculty audits the Pilot Monitoring Register upon completion of the pilot period.
- **Pass Rule:** Zero unresolved P0 (Critical) or P1 (High) incidents exist. All logged minor issues (P2/P3) have documented workarounds or resolutions.

---

## 5. Final Sign-Off Gate

At the conclusion of the pilot:
- If **all 12 criteria are SATISFIED**, the pilot is declared **SUCCESSFUL**, and Phase 5 (General Student Cohort Rollout) is authorized.
- If any P0 or P1 criterion fails, general rollout is **HELD**, and an engineering remediation cycle is initiated.
