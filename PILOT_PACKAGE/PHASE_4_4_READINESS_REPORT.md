# BioWriter Studio — Phase 4.4: Supervised Student Pilot Readiness Report

**Target Project:** `c:\Users\Lenovo\Downloads\Joint Platform\upload`  
**Phase:** 4.4 — Supervised Student Pilot Preparation & Readiness Gate  
**Version:** 1.1.0-pilot (Post-Phase 4.4.1 Targeted Corrections)  
**Scope:** 2 Faculty Supervisors, 10 Graduate Students  
**Execution Mode:** STRICT READ-ONLY INSPECTION & OPERATIONAL PREPARATION  
**Priority:** HIGH — Transition to Student Use  
**Date:** 2026-11-14  
**Author:** BioWriter Studio Software Assurance & Independent Security Auditor  

---

## 1. Executive Summary

Phase 4.4 establishes the operational deployment baseline for BioWriter Studio's first supervised academic pilot. This evaluation determines whether the physical deployment environment, configuration parameters, data isolation mechanisms, and user documentation are operationally ready for 2 faculty members and 10 graduate students.

Following the Phase 4.4.1 targeted corrections, this report incorporates strict seed sanitation rules (excluding historical exemplar 13989), network security clarifications regarding `0.0.0.0` vs. HTTPS, production WSGI hosting mandates, individually attributable faculty authentication, and a mandatory 8-point pre-deployment smoke-test checklist.

### Overall Readiness Determination:

# **READY WITH ACTION REQUIRED**

The core application code, student data isolation boundaries, account-claiming mechanisms, and pilot documentation packages are fully verified and **READY**. Prior to onboarding the 10 graduate students, the system administrator must execute the following operational setup actions:
1. Initialize an isolated pilot data directory via `BIOWRITER_DATA_DIR` using audited, sanitized seed files (strictly excluding `drafts/13989.json` and historical student records).
2. Generate and export a 256-bit cryptographically secure `SECRET_KEY`.
3. Deploy the application behind a production WSGI server (Gunicorn) with TLS 1.3 / HTTPS termination and perimeter network restrictions (campus subnet/VPN).
4. Configure separate, individually attributable faculty accounts for both instructors.
5. Successfully complete and sign off on the 8-point Final Deployment Smoke-Test Checklist.

---

## 2. Deployment Readiness Audit Matrix

```
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| #  | Readiness Evaluation Item          | Status                     | Findings & Required Operational Actions               |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 01 | Core Application & Architecture    | READY                      | Flask application, blueprint routes, and client-side  |
|    |                                    |                            | assets verified across 565 preflight tests.           |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 02 | Student Access & Data Isolation    | READY                      | Author-only write coercion (student_id = session_sid) |
|    |                                    |                            | and account claiming protocol fully functional.       |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 03 | Pilot Documentation Package        | READY                      | Complete set of Runbook, Faculty Guide, Student Guide,|
|    |                                    |                            | Privacy Notice, and Acceptance Criteria completed.    |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 04 | Staging / Pilot Data Directory     | READY WITH ACTION REQUIRED | Default directory is upload/data. Administrator must  |
|    |                                    |                            | configure BIOWRITER_DATA_DIR; exclude 13989.json.     |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 05 | Seed File Sanitation Audit         | READY WITH ACTION REQUIRED | Administrator must verify copied seeds contain no     |
|    |                                    |                            | prior student records or unnecessary credentials.     |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 06 | Production Secret Configuration    | READY WITH ACTION REQUIRED | App strictly fails closed if SECRET_KEY is missing.   |
|    |                                    |                            | Administrator must generate a 256-bit key prior to run|
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 07 | Production WSGI & HTTPS Hosting    | READY WITH ACTION REQUIRED | Flask dev server is not approved for production. Must |
|    |                                    |                            | deploy Gunicorn behind HTTPS reverse proxy.           |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 08 | Individual Faculty Attribution     | READY WITH ACTION REQUIRED | Both instructors must have distinct, individual       |
|    |                                    |                            | accounts; sharing a common credential is prohibited.  |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 09 | Backup & Recovery Feasibility      | READY                      | Atomic file writes, SHA-256 manifests, and snapshot   |
|    |                                    |                            | procedures verified across historical backups.        |
+----+------------------------------------+----------------------------+-------------------------------------------------------+
| 10 | Pre-Deployment Smoke Test          | READY WITH ACTION REQUIRED | Mandatory 8-point smoke test must be executed on      |
|    |                                    |                            | live HTTPS staging environment prior to student entry.|
+----+------------------------------------+----------------------------+-------------------------------------------------------+
```

---

## 3. Targeted Technical Corrections & Policies

### 3.1 Pilot Seed Data Isolation (Exemplar 13989 Exclusion)
- **Policy:** The historical benchmark proposal `upload/data/drafts/13989.json` **MUST NOT** be copied into the active pilot data directory.
- **Rationale:** The supervised pilot must evaluate genuine student onboarding and draft lifecycle from a clean baseline. If an exemplar is required for instructional demonstration, the administrator must supply an approved, synthetic proposal (e.g. `DEMO-EXEMPLAR.json`).
- **Seed Sanitation Audit:** The administrator must audit `users.json`, `cohort_db.json`, and `faculty_security.json` to confirm that all historical student records from prior academic cohorts are purged, leaving only the 2 authorized faculty members and 10 enrolled pilot students.

### 3.2 Network Architecture: `0.0.0.0` vs. Security Controls
- **Clarification:** Binding a network socket to `0.0.0.0` simply instructs the operating system to listen on all local network adapters. **`0.0.0.0` is NOT a security control.**
- **Production WSGI Mandate:** Running the built-in Flask development server (`python app.py`) in production is **strictly prohibited**. The production deployment must use Gunicorn (`gunicorn -w 2 -b 127.0.0.1:5000 wsgi:app`) bound locally behind an institutional reverse proxy (Nginx/Caddy/Cloud Load Balancer).
- **HTTPS & Perimeter Security:** All external student and faculty access must occur over **TLS 1.3 / HTTPS**. Network access must be restricted to the university campus network or VPN allowlist before student onboarding.

### 3.3 Accurate Privacy & Bibliographic Scope
- **Zero Commercial Cloud AI Egress:** In the verified standard configuration, student proposals, draft narratives, hypotheses, and specific aims are **never sent to external commercial AI platforms** (OpenAI ChatGPT, Google Gemini, Anthropic Claude). All compliance analysis is executed locally on-premises via deterministic algorithmic rule engines.
- **Active Bibliographic Lookups:** When students check citations, the platform issues outbound HTTPS requests to public open-access scholarly databases (CrossRef, PubMed, Europe PMC, OpenAlex) using **only published DOIs or generic search strings**. Student text and identifiers are never included.
- **Air-Gap Policy:** The platform is not air-gapped in standard mode due to public DOI lookup. Strict air-gap operation requires network firewall blocking, which the application handles gracefully via local offline fallback.

### 3.4 Individually Attributable Faculty Credentials
- **Policy:** Sharing a single, generic faculty passcode or administrative credential across multiple instructors is **strictly prohibited**.
- **Implementation:** Both faculty members must have individual accounts in `users.json` with distinct credentials (e.g., `FAC-01` and `FAC-02`). Every evaluation memo, score entry, draft unlock, and token generation event must be permanently attributed to the individual instructor in the audit log.

---

## 4. Final Pre-Deployment Smoke-Test Checklist

Prior to student onboarding, the administrator and faculty supervisors must execute and sign off on this 8-point smoke test against the live HTTPS staging environment:

```
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| #  | Verification Item                  | Test Procedure & Acceptance Criteria                                    | Status |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 01 | Faculty Authentication             | Both faculty members log in independently with unique credentials.      | [ ] OK |
|    |                                    | Confirm individual attribution in session state.                        |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 02 | Student Activation & Login         | Faculty generates a test token; student account is claimed; password    | [ ] OK |
|    |                                    | is set; subsequent login succeeds. Token cannot be reused.              |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 03 | Proposal Creation, Save & Reopen   | Student creates draft with Title, Aims, and Methodology; auto-save      | [ ] OK |
|    |                                    | displays green; browser is closed and reopened; all text restored 100%.|        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 04 | Student Data Isolation Boundary    | Student A attempts to read/write Student B's draft. Server rejects with | [ ] OK |
|    |                                    | HTTP 403. Write payload tampering is coerced to session_sid.            |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 05 | Flowchart Upload & Recovery        | Student uploads a PNG workflow diagram (<5MB); preview renders properly;| [ ] OK |
|    |                                    | clear browser cache; caption remains intact and image recovers cleanly. |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 06 | Faculty Review & Feedback Dispatch | Student locks proposal; faculty reviews draft in /faculty, scores       | [ ] OK |
|    |                                    | rubric, enters memo, and dispatches; student sees Feedback Banner.      |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 07 | HTTPS & Network Accessibility      | Access verified over HTTPS with valid TLS cert; secure cookie flags set | [ ] OK |
|    |                                    | (HttpOnly, Secure); cleartext HTTP automatically redirects to HTTPS.    |        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
| 08 | Backup & Recovery Readiness        | Execute automated snapshot backup; verify SHA-256 manifest; test restore| [ ] OK |
|    |                                    | to temporary directory; confirm all 10 student draft files match hashes.|        |
+----+------------------------------------+-------------------------------------------------------------------------+--------+
```

---

## 5. Pre-Pilot Operational Launch Checklist

The administrator must complete the following steps in sequence:

```
[ ] Step 1: Create isolated pilot data directory (/var/biowriter/pilot_data).
[ ] Step 2: Perform seed sanitation audit on users.json, cohort_db.json, faculty_security.json.
[ ] Step 3: Copy sanitized seed files to pilot directory (STRICTLY EXCLUDE drafts/13989.json).
[ ] Step 4: Generate a 256-bit cryptographically secure SECRET_KEY.
[ ] Step 5: Configure individual faculty credentials for both instructors.
[ ] Step 6: Deploy Gunicorn WSGI behind Nginx/Caddy terminating HTTPS with campus IP allowlisting.
[ ] Step 7: Execute and pass the 8-point Pre-Deployment Smoke-Test Checklist.
[ ] Step 8: Distribute Student Quick-Start Guides, Privacy Notices, and individual activation tokens.
```

---

## 6. Final Recommendation

BioWriter Studio is **READY WITH ACTION REQUIRED**. All documentation, security boundaries, and technical runbooks have been updated to reflect the Phase 4.4.1 corrections. Upon completion of the administrator-led pre-pilot launch checklist, the supervised student pilot can proceed safely.
