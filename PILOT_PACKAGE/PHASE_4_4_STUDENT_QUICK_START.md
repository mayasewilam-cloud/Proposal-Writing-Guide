# BioWriter Studio — Student Quick-Start Guide

**Document ID:** `PHASE_4_4_STUDENT_QUICK_START.md`  
**Audience:** Graduate Students in the BT 301 Research Proposal Studio Pilot  
**Target Project:** BioWriter Studio  
**Status:** Student-Facing User Guide  

---

## Welcome to BioWriter Studio!

BioWriter Studio is an interactive academic platform designed to guide you through drafting, structuring, illustrating, and validating high-impact bioengineering research proposals.

---

## 1. Accessing the Platform

1. Launch a modern web browser (Google Chrome, Mozilla Firefox, Microsoft Edge, or Apple Safari).
2. Navigate to your university course portal link:
   ```
   http://<server-address>:5000/
   ```
3. You will see the **BioWriter Studio** proposal editor interface.

---

## 2. Claiming Your Account & Signing In

To protect your research data, all student accounts must be claimed using an official one-time activation token issued by your course instructor.

### First-Time Account Activation:
1. Click the **"Claim Account / Activate"** button located at the top-right corner of the navigation bar.
2. Enter your **Student ID** (e.g., `20230001`).
3. Enter the **Activation Token** provided to you by your professor (e.g., `K9X2P4`).
4. Choose a strong personal password (at least 8 characters).
5. Click **"Activate Account"**.
6. You will see a green confirmation toast: *"Account activated successfully!"*

### Returning Sign-In:
- On future visits, simply click **"Sign In"** at the top right, enter your Student ID and chosen password, and click **"Log In"**.

---

## 3. Creating & Structuring Your Proposal

BioWriter Studio organizes your scientific proposal into five core architectural sections:

1. **Title & Specific Aims:** Clearly articulate your overarching scientific goal, primary research question, and two to three measurable specific aims.
2. **Abstract & Problem Narrative:** Synthesize the clinical, industrial, or scientific rationale driving your study.
3. **5-Phase Experimental Methodology:** Detail your assay design, laboratory protocol, negative/positive controls, and analytical verification steps.
4. **Experimental Flowchart Diagram:** Upload or generate a visual schematic illustrating your end-to-end experimental workflow.
5. **Literature References & Citations:** Link peer-reviewed evidence supporting your molecular targets and methods.

---

## 4. Editing and Saving Your Work

### Automated Background Saving:
- As you type in any field, BioWriter Studio automatically buffers your edits locally and synchronizes them to the university server.
- Look at the top navigation bar for the **Save Status Indicator**:
  - `● All progress saved` (Green): Your latest edits are securely saved on the university server.
  - `● Saved (Photos offloaded to IndexedDB)`: Your text and large figures are safely persisted across browser storage.
  - `⚠️ Save Failed (Click to retry)` (Red): If a temporary connection drop occurs, click this badge to retry immediately.

### Manual Save Shortcut:
- Press **Ctrl + S** (or **Cmd + S** on Mac) at any time to trigger an instant server save.

---

## 5. Uploading and Managing Flowcharts

A clear experimental flowchart is an essential component of Section 4.2 of your proposal.

1. In the **Methodology & Flowchart** section, locate the **Flowchart & Workflow Diagram** container.
2. **Uploading an Image:**
   - Click **"Upload Flowchart Image"** to select a PNG or JPG file from your computer (e.g., exported from BioRender, PowerPoint, or Illustrator).
   - The image preview will appear immediately in your studio editor.
3. **Figure Caption:**
   - Add a descriptive scientific caption in the caption box below the image (e.g., *"Figure 1: Five-phase experimental pipeline integrating RPA-Cas12a detection of mcr-1 in wastewater extracts."*).
4. **Storage Tip:** If you ever clear your browser cache or open your draft in a new browser, your text and caption will remain completely safe. You can easily re-attach your image file if prompted.

---

## 6. Understanding Deterministic Compliance Analysis

At the bottom of your editor, you will find the **Autonomous Compliance & Biosafety Agent** panel.

1. Click **"🚀 Run Compliance Check"** to analyze your proposal draft.
2. **What this check does:**
   - Identifies biosafety containment requirements (e.g., BSL-1 vs. BSL-2).
   - Scans for recombinant DNA / GMO triggers.
   - Verifies pathogen and antimicrobial resistance (AMR) declarations.
   - Detects potential regulatory contradictions (e.g., declared zero human subjects, but clinical samples mentioned in methodology).
3. **Understanding the "Deterministic fallback" Badge:**
   - You will see a badge reading: `Deterministic fallback (deterministic_rules_v3)`.
   - **What this means:** BioWriter Studio uses transparent, local scientific rule engines—not an external commercial AI—to evaluate your proposal. Your draft is evaluated on-premise without your ideas leaving the server.

---

## 7. Checking References & Citation Grounding

1. Enter your references in Section 6 or the References container. You can paste standard citation strings or raw DOIs (e.g., `10.1126/science.aar6245`).
2. The system checks citations against public scholarly registries (such as CrossRef):
   - Confirms publication year and journal metadata.
   - Alerts you if any cited publication has an official **Retraction Notice** or **Expression of Concern**.

---

## 8. Submitting Your Proposal for Grading

When your proposal is complete and ready for instructor review:

1. Perform a final review of all fields and your flowchart caption.
2. Scroll to the submission panel and click **"Lock & Submit Proposal for Grading"**.
3. A confirmation dialog will appear: *"Are you sure you want to submit? Your proposal will be locked for editing."*
4. Click **"Confirm Submission"**.
5. Your save indicator will update to **`🔒 Submitted & Locked for Grading`**.
6. The exact submission timestamp is permanently recorded on the server.

---

## 9. Viewing Faculty Feedback & Revision Guidance

Once your instructor evaluates your submission:

1. The next time you open BioWriter Studio, a green **Faculty Evaluation Banner** will be visible at the top of your draft.
2. Review your:
   - Evaluator comments and qualitative memo.
   - Recommended action items for methodology refinement.
   - Rubric assessment.
3. If your professor requests revisions and unlocks your draft, your editing capabilities will be restored automatically.

---

## 10. Reporting Issues Safely

If you experience technical issues:
- **Do:** Take a screenshot of the error message or note what action caused it.
- **Do:** Email your course instructor or lab administrator with your Student ID and a brief description of the issue.
- **DO NOT:** Ever send your password or sensitive personal data in an email or chat message. Instructors can reset your account or generate a new activation token without ever needing to know your password.
