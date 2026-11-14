# BioWriter Studio — Student Privacy & Data Protection Notice

**Document ID:** `PHASE_4_4_STUDENT_PRIVACY_NOTICE.md`  
**Applicability:** Supervised Pilot Cohort (BT 301 / Research Proposal Studio)  
**Effective Date:** 2026-11-14  
**Classification:** Official Course Syllabus & Platform Privacy Disclosure  

---

## 1. Purpose of this Notice

This notice explains how BioWriter Studio handles your research proposal drafts, academic credentials, and personal data during the supervised student pilot. We believe in complete scientific and technological transparency.

---

## 2. Local Proposal Processing & Zero Cloud AI Egress

- **On-Premise Server Storage:** Your research proposal text, specific aims, hypotheses, experimental protocols, and project titles are stored directly on the university-hosted BioWriter Studio server.
- **No Commercial Cloud AI Transmission:** In the verified standard pilot configuration, **your proposal text is never transmitted to external commercial AI platforms** (such as OpenAI ChatGPT, Google Gemini, or Anthropic Claude).
- **Intellectual Property Protection:** Your unpublished scientific hypotheses and novel experimental strategies remain strictly confidential within the university platform.

---

## 3. Deterministic Local Compliance Analysis

- BioWriter Studio includes an automated preliminary compliance and biosafety assistant.
- **How it Works:** All compliance scans (including biosafety level categorization, recombinant DNA flags, animal subject triggers, and clinical sample contradiction checks) are performed on-premises using transparent, deterministic algorithmic rules and pattern extractors.
- **Visual Labeling:** The system clearly displays `Extraction Mode: deterministic_rules` and `Deterministic fallback (deterministic_rules_v3)` in the user interface to ensure you always know an algorithmic rule engine evaluated your proposal, rather than a generative cloud AI.

---

## 4. Bibliographic Queries & Public Scholarly Databases

To assist with academic rigor and literature grounding, BioWriter Studio checks citations and literature references:

- **What is Sent Externally:** When you validate citations or search literature, the application issues outbound HTTPS requests to public, open-access scholarly databases:
  - **CrossRef API** (`api.crossref.org`)
  - **NCBI PubMed E-utilities** (`eutils.ncbi.nlm.nih.gov`)
  - **Europe PMC API** (`ebi.ac.uk/europepmc`)
  - **OpenAlex API** (`api.openalex.org`)
- **Strict Query Scoping:** Outbound requests contain **ONLY** public digital object identifiers (DOIs) or generic bibliographic search terms (e.g., `"CRISPR-Cas12a AND colistin"`).
- **Confidentiality Guarantee:** Your student name, Student ID, proposal draft paragraphs, and specific aims are **never included** in bibliographic lookup queries.

---

## 5. Network Connectivity & Air-Gap Clarification

- **Not an Air-Gapped System:** Because BioWriter Studio queries public bibliographic databases over the Internet to verify DOIs and check for scientific paper retractions, the platform is **not strictly air-gapped** in its standard configuration.
- **Firewall Fallback:** If your university IT department blocks outbound Internet access, BioWriter Studio automatically catches connection timeouts and falls back cleanly to offline local citation parsing without disrupting your drafting experience.

---

## 6. Access Control & Student Data Isolation

- **Author-Only Write Boundaries:** BioWriter Studio cryptographically enforces that you are the sole author with permission to modify your individual draft. The server strictly binds your session to your Student ID; no other student can overwrite your work.
- **Teammate Visibility:** If you are assigned to a collaborative lab group or team, teammates in your designated team can view your shared team workspace and updates. Students in other teams receive an automatic `403 Access Denied`.
- **Faculty Supervision:** Authorized course instructors and evaluation board members have administrative access to inspect your progress, grade locked submissions, and deliver qualitative feedback memos.

---

## 7. Student Best Practices for Data Security

1. **Protect Your Account Password:** Never share your student account password with classmates, teammates, or teaching assistants.
2. **Do Not Include Private Personal Data:** Do not type passwords, personal phone numbers, national identification numbers, or real patient medical records into proposal draft fields.
3. **Use Only De-Identified Research Data:** If your research involves retrospective clinical literature, reference only anonymized, published case data and public accession numbers.
4. **Log Out on Shared Computers:** If working on a shared university library or laboratory workstation, always click **"Log Out"** when completing your session.

---

## 8. Questions and Incident Inquiries

If you have questions regarding how your proposal data is handled or suspect an unauthorized access attempt, contact your course faculty supervisor immediately.
