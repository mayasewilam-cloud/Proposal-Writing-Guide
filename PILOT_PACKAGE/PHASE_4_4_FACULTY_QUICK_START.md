# BioWriter Studio — Faculty Quick-Start Guide

**Document ID:** `PHASE_4_4_FACULTY_QUICK_START.md`  
**Audience:** Supervised Pilot Faculty Instructors & Evaluation Board  
**Target Course:** BT 301 / Bioengineering Research Proposal Studio  
**Pilot Cohort:** 2 Faculty Members, 10 Graduate Students  
**Version:** 1.1.0-pilot (Post-Phase 4.4.1 Corrections)  
**Status:** Operational User Guide  

---

## 1. Accessing the Faculty Portal & Individually Attributable Sign-In

> [!IMPORTANT]
> **Individually Attributable Faculty Accounts:**  
> Sharing a common faculty passcode or password across instructors is **strictly prohibited**. Both faculty members must authenticate using their own individual faculty accounts (e.g., `FAC-01 Dr. Smith` and `FAC-02 Dr. Jones`). All rubric scores, qualitative memos, draft unlocking actions, and token generation events are logged with the specific faculty member's ID in the audit trail to ensure non-repudiation.

### Signing In:
1. Open your web browser and navigate to the faculty management URL over secure HTTPS:
   ```
   https://<server-address>/faculty
   ```
2. When the Faculty Security Gateway appears:
   - Enter your individual Faculty ID and private faculty account credentials.
   - Enter the secondary administrative security passcode (`FACULTY_PASSCODE`) configured by your system administrator.
3. Click **"Verify & Enter Faculty Portal"**.
4. Once authenticated, your browser establishes an encrypted, HMAC-signed session. You will access the **Faculty Dashboard**:
   - **Cohort & Teams:** Student roster, lab groups, and activation tokens.
   - **Submissions & Grading:** Live proposal inspection, rubric scoring, and feedback dispatch.
   - **System Audit Log:** Real-time visibility into student transitions and lock states.

---

## 2. Preparing and Activating Fresh Student Accounts

> [!NOTE]
> **Clean Pilot Cohort Baseline:**  
> The pilot cohort begins with fresh student accounts and an empty proposals directory. Historical student records and prior terms' drafts (including exemplar 13989) have been excluded from the pilot dataset. If you wish to demonstrate an exemplar proposal to students, use the approved synthetic demonstration draft (`DEMO-EXEMPLAR.json`).

### Step-by-Step Activation Flow:
1. In the Faculty Portal, navigate to the **"Cohort & Teams"** tab.
2. Review the verified roster of 10 enrolled pilot graduate students.
3. Locate the student who needs access (e.g., Student ID `STU-01`).
4. Click the **"Generate Activation Token"** button adjacent to the student's name.
5. The portal will generate a high-entropy, 6-character alphanumeric token (e.g., `K9X2P4` or 32-hex token).
6. **Token Properties:**
   - Single-use: Automatically consumed upon successful student account setup.
   - Time-bounded: Valid for 48 hours.
   - Bound to Student ID: Cannot be used by any other student.

---

## 3. Securely Distributing Activation Instructions to Students

To preserve student account confidentiality:
- **Do:** Send the activation token individually to the student's official university email address or deliver it in person during lab briefing.
- **Do:** Instruct the student to claim their account immediately and create a strong personal password.
- **DO NOT:** Post activation tokens in public Slack/Discord channels, class-wide broadcast emails, or on public message boards.
- **DO NOT:** Collect or store student passwords. Faculty passcodes grant administrative access; faculty should never know student passwords.

### Template Activation Email for Faculty to Send to Students:

> **Subject:** BT 301 BioWriter Studio — Account Activation Instructions  
> **Dear [Student Name],**  
>  
> Welcome to the BT 301 Research Proposal Studio pilot. Your pre-enrolled profile is ready for activation.  
>  
> **Activation Steps:**  
> 1. Open the BioWriter Studio portal over HTTPS: `https://<server-address>/`  
> 2. Click the **"Claim Account / Activate"** button at the top right.  
> 3. Enter your Student ID: `[Student ID]`  
> 4. Enter your single-use Activation Token: `[Token]`  
> 5. Create your secure personal password (minimum 8 characters).  
> 6. Click **"Activate Account"**.  
>  
> Please complete this within 48 hours. If you encounter any issues, notify your instructor immediately.

---

## 4. Monitoring Student Proposal Progress

Faculty members have continuous visibility into student drafts without interfering with their editing sessions:

1. Click on the **"Submissions & Grading"** tab in the Faculty Portal.
2. The roster displays real-time status indicators for all 10 students:
   - `DRAFTING` (Active in progress, unlocked)
   - `SUBMITTED / LOCKED` (Submitted for formal grading; editing disabled for student)
   - `EVALUATED` (Instructor evaluation dispatched)
3. Click **"Inspect Live Draft"** next to any student to view their current sections:
   - Specific Aims & Hypothesis
   - 5-Phase Experimental Methodology & Flowchart
   - Materials & Experimental Controls
   - Literature Citations and Retraction Checks

---

## 5. Reviewing and Evaluating Submissions

When a student submits their proposal for grading, the system locks their draft server-side to prevent post-deadline modifications.

### Evaluation Workflow:
1. In the **"Submissions & Grading"** tab, locate a student with status `SUBMITTED / LOCKED`.
2. Click **"Grade Submission / Enter Rubric"**.
3. Review the rubric criteria:
   - **Aim Clarity & Rationale** (0–25 points)
   - **Methodological Feasibility & Controls** (0–25 points)
   - **Flowchart & Assay Pipeline** (0–25 points)
   - **Literature Grounding & Citation Integrity** (0–25 points)
4. Enter individual criterion scores and an overall letter standing (`Distinction`, `Pass`, `Needs Revision`).
5. Compose your qualitative feedback in the **Instructor Guidance & Memo** editor:
   - Strengths identified.
   - Specific methodological risks or missing controls.
   - Recommended action items for revision.

---

## 6. Dispatching Feedback to Students

1. Once your rubric scores and qualitative comments are complete, click **"Dispatch Evaluation to Student"**.
2. The system securely persists the evaluation record to `upload/data/drafts/<student_id>.json`.
3. The student's interface updates immediately upon next reload or save:
   - A prominent **Instructor Feedback Banner** appears at the top of their studio editor.
   - Action items and methodological recommendations are displayed clearly.
   - Grades are presented in student-sanitized format.

---

## 7. Handling Common Student Access Issues

```
+------------------------------------+-------------------------------------------------------+
| Student Issue                      | Recommended Faculty Resolution Action                 |
+------------------------------------+-------------------------------------------------------+
| "My activation token expired or is | Click "Regenerate Activation Token" next to the       |
| invalid."                          | student's name in the Cohort & Teams tab. Send the    |
|                                    | newly generated token to the student.                 |
+------------------------------------+-------------------------------------------------------+
| "I forgot my password."            | In Cohort & Teams, click "Reset Student Account".     |
|                                    | This resets account_claimed to false and generates    |
|                                    | a new activation token for re-claiming.               |
+------------------------------------+-------------------------------------------------------+
| "I submitted my proposal by        | If an accidental submission occurred prior to the     |
| accident and it is locked."        | deadline, click "Unlock Draft for Re-Drafting" in     |
|                                    | Submissions tab. Re-drafting permission is restored.  |
+------------------------------------+-------------------------------------------------------+
| "Rate limit exceeded (5 attempts   | Advise student to wait 15 minutes for the rolling     |
| lockout)."                         | rate-limit window to clear before re-attempting.      |
+------------------------------------+-------------------------------------------------------+
```

---

## 8. Incident Reporting & Pre-Pilot Smoke Test

1. Prior to admitting students, both faculty members must participate with the system administrator in executing the **8-Point Pre-Deployment Smoke Test** documented in Section 9 of the [Pilot Deployment Runbook](file:///c:/Users/Lenovo/Downloads/Joint%20Platform/upload/PILOT_PACKAGE/PHASE_4_4_PILOT_DEPLOYMENT_RUNBOOK.md#9-final-deployment-smoke-test-checklist).
2. During the pilot, record all student access, save, or rendering issues in the [Pilot Monitoring Register](file:///c:/Users/Lenovo/Downloads/Joint%20Platform/upload/PILOT_PACKAGE/PHASE_4_4_PILOT_MONITORING_REGISTER.md).
3. **Confidentiality:** Never record or transmit student passwords in incident reports.
