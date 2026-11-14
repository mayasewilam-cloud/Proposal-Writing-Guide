# BioWriter Studio — Pilot Deployment Runbook

**Document ID:** `PHASE_4_4_PILOT_DEPLOYMENT_RUNBOOK.md`  
**Target Platform:** BioWriter Studio (Full Suite)  
**Target Environment:** Supervised Academic Pilot (2 Faculty, 10 Graduate Students)  
**Project Path:** `c:\Users\Lenovo\Downloads\Joint Platform\upload`  
**Version:** 1.1.0-pilot (Post-Phase 4.4.1 Corrections)  
**Status:** Operational Production Deployment Guide  

---

## 1. System Requirements & Architecture Baseline

### 1.1 Software Dependencies
- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 recommended), Windows Server 2022, or macOS 13+
- **Python Runtime:** Python 3.10, 3.11, 3.12, or 3.14 (Verified on Python 3.14.0)
- **Package Manager:** `pip` (bundled with Python)
- **Production WSGI Server:** `gunicorn>=21.2.0` (Linux/macOS) or `waitress>=2.1.2` (Windows Server)
- **TLS Reverse Proxy:** Nginx 1.22+, Caddy 2.7+, or cloud load balancer with valid TLS certificates
- **Supported Browsers:** Google Chrome 115+, Mozilla Firefox 115+, Microsoft Edge 115+, Apple Safari 16+

### 1.2 Python Package Installation
Navigate to the application root directory and install dependencies from `requirements.txt`:

```bash
cd "/path/to/BioWriter-Studio/upload"
pip install -r requirements.txt
```

Verified core dependencies:
- `Flask>=3.0.0` (Core WSGI application framework)
- `Werkzeug>=3.0.0` (HTTP and routing engine)
- `python-docx>=1.1.0` (Word document export generation)
- `python-pptx>=1.0.0` (PowerPoint presentation export generation)
- `requests>=2.31.0` (Bibliographic lookup and citation resolution)
- `gunicorn>=21.2.0` (Production WSGI server)
- `whitenoise>=6.6.0` (Static asset delivery engine)

---

## 2. Environment Configuration & Cryptographic Controls

BioWriter Studio requires explicit environment configuration in production. The application strictly fails closed at startup if security parameters are missing or weak.

```
+---------------------+----------------------+-------------------------------------------------------+
| Variable Name       | Required in Prod?    | Description & Constraints                             |
+---------------------+----------------------+-------------------------------------------------------+
| SECRET_KEY          | MANDATORY            | Cryptographic session key (min. 32 chars / 256 bits).  |
|                     |                      | Startup raises RuntimeError if unset or placeholder.  |
| FACULTY_PASSCODE    | MANDATORY (Custom)   | Passcode for faculty security gateway. MUST be set to  |
|                     |                      | a strong, unique administrative secret.               |
| PORT                | OPTIONAL (Default 5000)| Internal TCP listening port for WSGI worker processes.|
| BIOWRITER_DATA_DIR  | MANDATORY FOR PILOT  | Absolute path to isolated pilot data directory.       |
|                     |                      | (e.g., /var/biowriter/pilot_data).                    |
| BIOWRITER_ENV       | MANDATORY 'production'| Set explicitly to 'production'. NEVER 'development'. |
+---------------------+----------------------+-------------------------------------------------------+
```

### 2.1 Generating a Production Secret Key
Generate a cryptographically secure 256-bit hexadecimal key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Pilot Data Isolation & Seed Verification

### 3.1 Strict Seed Separation (Exemplar 13989 Excluded)
> [!IMPORTANT]
> **Zero Historical Student Seed Policy:**  
> The historical benchmark draft `drafts/13989.json` **MUST NOT** be copied into the active pilot data directory. The pilot cohort must begin with fresh student accounts and an empty drafts directory. If an exemplar proposal is needed for classroom instruction, the administrator must provide a synthetic demonstration proposal (e.g., `DEMO-EXEMPLAR.json`) explicitly reviewed and approved by faculty.

### 3.2 Pre-Copy Seed Sanitation Audit
Before copying seed files into the pilot directory, the administrator must inspect and verify:
1. `users.json`: Contains **ONLY** the 2 authorized faculty members and the 10 enrolled pilot graduate students. All historical student accounts from prior academic terms must be purged.
2. `cohort_db.json`: Roster, lab groups, and assigned teams must match the current pilot roster exactly.
3. `faculty_security.json`: Administrative credentials and lockout counters must be reset.
4. `breakthroughs_bookmarks.json`: Clean baseline (`{"bookmarked_ids": [], "tags": {}}`).

### 3.3 Initializing the Isolated Pilot Data Directory

```bash
# Linux / macOS (Production Server)
mkdir -p /var/biowriter/pilot_data/drafts
mkdir -p /var/biowriter/pilot_data/agent_audit
mkdir -p /var/biowriter/pilot_data/agent_context
mkdir -p /var/biowriter/pilot_data/agent_state
chmod 700 /var/biowriter/pilot_data

export BIOWRITER_DATA_DIR="/var/biowriter/pilot_data"

# Copy ONLY audited, sanitized seed files (Exemplar 13989 is strictly excluded)
cp sanitized_seeds/users.json /var/biowriter/pilot_data/
cp sanitized_seeds/cohort_db.json /var/biowriter/pilot_data/
cp sanitized_seeds/faculty_security.json /var/biowriter/pilot_data/
cp data/breakthroughs_bookmarks.json /var/biowriter/pilot_data/
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path "C:\BioWriter\pilot_data\drafts"
New-Item -ItemType Directory -Force -Path "C:\BioWriter\pilot_data\agent_audit"
New-Item -ItemType Directory -Force -Path "C:\BioWriter\pilot_data\agent_context"
New-Item -ItemType Directory -Force -Path "C:\BioWriter\pilot_data\agent_state"
$env:BIOWRITER_DATA_DIR = "C:\BioWriter\pilot_data"

# Copy ONLY audited, sanitized seed files (Exemplar 13989 is strictly excluded)
Copy-Item "sanitized_seeds\users.json" -Destination "C:\BioWriter\pilot_data\"
Copy-Item "sanitized_seeds\cohort_db.json" -Destination "C:\BioWriter\pilot_data\"
Copy-Item "sanitized_seeds\faculty_security.json" -Destination "C:\BioWriter\pilot_data\"
Copy-Item "data\breakthroughs_bookmarks.json" -Destination "C:\BioWriter\pilot_data\"
```

---

## 4. Production Hosting, Network Security, and HTTPS Enforcement

> [!WARNING]
> **Network Binding Clarification:**  
> Binding an application to `0.0.0.0` is purely a network socket configuration instructing the OS to listen on all interfaces. **`0.0.0.0` is NOT a security control.** Exposing the Flask development server or WSGI worker directly to the public Internet without HTTPS and network perimeter controls creates severe security risks.

### 4.1 Mandatory Production Architecture Rules
1. **Flask Development Server Prohibition:**  
   The built-in Flask development server (`python app.py`) is for local developer debugging only. It is **NOT an approved production deployment**. In production, use Gunicorn (Linux) or Waitress (Windows).
2. **Mandatory HTTPS (TLS 1.3):**  
   The application must sit behind a reverse proxy (e.g., Nginx, Caddy, Cloudflare, AWS ALB) terminating TLS with a valid institutional certificate. Cleartext HTTP access must be redirected to HTTPS.
3. **Secure Session Cookie Flags:**  
   Ensure that the reverse proxy forwards `X-Forwarded-Proto: https` so Flask sets `Secure`, `HttpOnly`, and `SameSite=Lax` on all session cookies.
4. **Perimeter Network Access Restriction:**  
   Access to the pilot deployment must be restricted to authorized campus IP subnets or an institutional VPN prior to student onboarding.

### 4.2 Starting the Production WSGI Service (Linux / Gunicorn)

```bash
# Set production environment
export SECRET_KEY="<generated-64-hex-secret>"
export FACULTY_PASSCODE="<strong-faculty-pilot-secret>"
export BIOWRITER_DATA_DIR="/var/biowriter/pilot_data"
export BIOWRITER_ENV="production"
export PORT=5000

# Start Gunicorn WSGI bound locally to 127.0.0.1 (Reverse proxy handles public TLS)
gunicorn -w 2 -b 127.0.0.1:5000 --access-logfile /var/log/biowriter/access.log --error-logfile /var/log/biowriter/error.log wsgi:app
```

### 4.3 Nginx Reverse Proxy Sample Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name biowriter.university.edu;

    ssl_certificate /etc/ssl/certs/biowriter_cert.pem;
    ssl_certificate_key /etc/ssl/private/biowriter_key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Restrict to campus VPN / authorized subnet
    allow 10.0.0.0/8;
    allow 192.168.1.0/24;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}
```

---

## 5. Individually Attributable Faculty Authentication

> [!CAUTION]
> **No Shared Faculty Credentials:**  
> Sharing a single, common faculty password or administrative passcode across multiple instructors is **strictly prohibited**. In an academic grading environment, all evaluation memos, score overrides, draft unlocking actions, and token generation events must be non-repudiable and individually attributable to a specific faculty member.

### Implementation Requirements:
1. In `users.json`, each of the two faculty members must have a distinct, named account (e.g., `FAC-01 Dr. Smith` and `FAC-02 Dr. Jones`) with unique, individual passwords.
2. The administrative gateway passcode (`FACULTY_PASSCODE`) serves solely as a secondary defense-in-depth perimeter gate, not as a substitute for individual user identification.
3. Every dispatched evaluation records the specific instructor's identity in the audit trail:
   ```json
   {
     "event_type": "HUMAN_DECISION_RECORDED",
     "actor_id": "FAC-01",
     "actor_name": "Dr. Sarah Smith",
     "action": "Evaluation dispatched to student STU-01"
   }
   ```

---

## 6. Privacy & Outbound Network Boundaries

To ensure compliance with university research standards and data protection guidelines:
- **Proposal Privacy:** In the verified standard configuration, **zero student proposal text, specific aims, or hypotheses are transmitted to external commercial AI platforms** (OpenAI, Google Gemini, Anthropic). All compliance triage runs on-premises via deterministic local algorithms.
- **Bibliographic Egress:** When students check citations, the server queries public scholarly registries (CrossRef, PubMed, Europe PMC, OpenAlex) over HTTPS using **only public DOIs or generic search strings**. No student draft narratives or personal data are included in these requests.
- **Air-Gap Policy:** Because bibliographic lookups communicate with scholarly APIs, the platform is not air-gapped in standard mode. If strict air-gap is required by institutional policy, outbound Internet access can be blocked at the firewall; the software catches connection timeouts and falls back to offline regex validation.

---

## 7. Stop, Restart, and Maintenance Procedures

BioWriter Studio uses atomic file writes (`tempfile` + `os.replace`) for all draft and state files. It can be safely terminated without data corruption:
- **Graceful Shutdown:** Send `SIGTERM` to Gunicorn master process:
  ```bash
  kill -TERM $(pgrep -f "gunicorn.*wsgi:app")
  ```
- **Service Restart:**
  ```bash
  sudo systemctl restart biowriter
  ```

---

## 8. Backup and Recovery Procedure

Prior to each student writing session, execute a snapshot of `BIOWRITER_DATA_DIR`:

```bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/biowriter/backups/pilot_backup_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

cp -r /var/biowriter/pilot_data/* "${BACKUP_DIR}/"

# Generate SHA-256 integrity manifest
cd "${BACKUP_DIR}"
find . -type f -exec sha256sum {} + > manifest.sha256
echo "[*] Backup complete at: ${BACKUP_DIR}"
```

---

## 9. Final Deployment Smoke-Test Checklist

Prior to admitting students into the pilot, the system administrator and lead faculty member must execute this comprehensive 8-point smoke test against the live HTTPS staging environment:

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

**Approval Gate:** All 8 items must be checked and signed off by the administrator before onboarding pilot students.
