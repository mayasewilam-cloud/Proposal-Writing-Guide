# BioWriter Studio — Pilot Monitoring and Incident Register

**Document ID:** `PHASE_4_4_PILOT_MONITORING_REGISTER.md`  
**Target Course:** BT 301 / Research Proposal Studio  
**Cohort Scope:** 2 Faculty Members, 10 Graduate Students (Anonymized: `STU-01` to `STU-10`)  
**Status:** Operational Monitoring Instrument  

---

## 1. Instructions for Faculty Supervisors

This register is designed for the two faculty supervisors to track student onboarding, drafting milestones, submission integrity, and technical incidents during the supervised pilot.

- Update this register after each classroom or laboratory milestone.
- **Privacy Rule:** Never record real student passwords or private personal credentials in this document. Use student IDs or anonymized pilot tracking codes (`STU-01` through `STU-10`).

---

## 2. Pilot Student Milestone Tracking Matrix

```
+---------+------------------+------------------+-------------------+--------------------+--------------------+-------------------+---------------------+--------------------+
| Student | Account Claimed  | First Login      | Proposal Auto-Save| Proposal Reopened  | Flowchart Uploaded | Teammate Sync     | Submitted & Locked  | Feedback Delivered |
| Code    | (Token Consumed) | Successful?      | & Verified?       | Without Data Loss? | & Rendered?        | (If Applicable)   | for Grading?        | to Student?        |
+---------+------------------+------------------+-------------------+--------------------+--------------------+-------------------+---------------------+--------------------+
| STU-01  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-02  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-03  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-04  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-05  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-06  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-07  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-08  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-09  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
| STU-10  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No  | [ ] Yes  [ ] No   | [ ] Yes  [ ] No    | [ ] Yes  [ ] No    | [ ] Yes  [ ] N/A  | [ ] Yes  [ ] No     | [ ] Yes  [ ] No    |
+---------+------------------+------------------+-------------------+--------------------+--------------------+-------------------+---------------------+--------------------+
```

---

## 3. Incident Severity Classification Framework

```
+---------------+----------------------------------------------------------+-----------------------+
| Severity Level| Description & Impact                                     | Response Target       |
+---------------+----------------------------------------------------------+-----------------------+
| CRITICAL (P0) | Unintended data loss, proposal overwrite, cross-account  | Immediate halt;       |
|               | data leakage, server crash affecting all users.          | resolve before resume.|
+---------------+----------------------------------------------------------+-----------------------+
| HIGH (P1)     | Individual student blocked from login/claiming, save     | Resolve within        |
|               | failure requiring retry, submission lock malfunction.    | 4 hours.              |
+---------------+----------------------------------------------------------+-----------------------+
| MEDIUM (P2)   | Flowchart image re-upload required, reference validation | Resolve within        |
|               | timeout, cosmetic layout anomaly on specific browser.    | 24 hours.             |
+---------------+----------------------------------------------------------+-----------------------+
| LOW (P3)      | Minor UI typo, clarification wording suggestion, styling | Log for future        |
|               | enhancement request.                                     | release cycle.        |
+---------------+----------------------------------------------------------+-----------------------+
```

---

## 4. Pilot Incident Log & Resolution Record

Record any observed technical, authentication, or persistence anomalies below:

```
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| Incident # | Date/Time  | Student | Severity | Description of Observed Anomaly     | Remediation Action Taken          | Status      |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| INC-001    | YYYY-MM-DD | STU-XX  | MEDIUM   | Example: Activation token expired   | Regenerated fresh token in        | RESOLVED    |
|            |            |         |          | after 48h before student claimed.   | Faculty Portal; claimed OK.       |             |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| INC-002    | YYYY-MM-DD | STU-XX  | LOW      | Example: Flowchart warning logged   | Confirmed text intact; student    | RESOLVED    |
|            |            |         |          | after browser cache cleared.        | re-attached PNG; preview restored.|             |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| INC-003    |            |         |          |                                     |                                   |             |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| INC-004    |            |         |          |                                     |                                   |             |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
| INC-005    |            |         |          |                                     |                                   |             |
+------------+------------+---------+----------+-------------------------------------+-----------------------------------+-------------+
```

---

## 5. End-of-Pilot Summary & Review Sign-Off

```
+-------------------------------------------------+------------------------------------------+
| Metric Evaluation Item                          | Final Pilot Outcome                      |
+-------------------------------------------------+------------------------------------------+
| Total Students Participating                    | 10 Graduate Students                     |
| Total Successful Account Activations            | ___ / 10                                 |
| Total Proposals Successfully Submitted & Graded | ___ / 10                                 |
| Total Data Loss Incidents Recorded              | ___ (Target: 0)                          |
| Total Cross-Account Access Breaches             | ___ (Target: 0)                          |
| Overall Pilot Outcome Assessment                | [ ] SUCCESSFUL  [ ] ACTION NEEDED        |
+-------------------------------------------------+------------------------------------------+

Faculty Supervisor 1 Signature: _______________________ Date: ____________
Faculty Supervisor 2 Signature: _______________________ Date: ____________
```
