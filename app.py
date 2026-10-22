"""
BioWriter Studio: Comprehensive Scientific Proposal & Writing Portal.
Server application serving the interactive student workspace and REST API.
Includes: Search Builder, RHEV Paraphrase Lab, DOI Reference Service,
PowerPoint Slides Service, Socratic Engine, Rubric Audits, and Instructor Studio.
"""

import os
import json
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, session
from core.search_builder import build_boolean_query, get_curated_examples
from core.socratic_engine import analyze_student_draft, generate_viva_defense_questions
from core.audit_rules import (
    calculate_full_rubric_audit,
    audit_title,
    audit_abstract,
    audit_methodology_tense,
    audit_all_writing_sections
)
from core.funnel_scaffolder import get_sentence_starters, assemble_background_narrative
from core.export_service import generate_docx_portfolio, generate_markdown_portfolio
from core.paraphrase_engine import audit_paraphrase_rhev
from core.reference_service import fetch_doi_metadata, audit_bibliography_recency
from core.slides_service import create_defense_presentation
from core.instructor_engine import get_rapid_comment_bank, compile_instructor_feedback_report
from core.impact_novelty_engine import (
    GAP_TAXONOMY,
    audit_gap_statement,
    audit_novelty_and_soundness,
    build_significance_search_queries,
    evaluate_proposal_logic_chain,
    audit_competitor_matrix_and_usp
)
from core.paper_summarizer import (
    fetch_paper_abstract_and_meta,
    deconstruct_paper,
    SAMPLE_PAPERS,
    JARGON_LEXICON
)
from core.breakthroughs_manager import (
    get_breakthroughs_catalog,
    sync_europepmc_breakthroughs,
    toggle_breakthrough_bookmark,
    CREATORS,
    COPYRIGHT_NOTICE
)
from core.bt301_guide import (
    get_all_chapters,
    get_chapter,
    search_guide,
    get_quick_finder,
    get_sentence_formulation_guide
)
from core.auth_store import (
    register_student,
    authenticate_student,
    get_student_user,
    seed_default_users,
    verify_faculty_passcode,
    check_faculty_rate_limit,
    record_faculty_attempt,
    reset_faculty_rate_limit
)
from core.draft_store import (
    save_student_draft,
    get_student_draft,
    list_student_drafts,
    seed_default_drafts,
    toggle_draft_lock,
    dispatch_faculty_feedback,
    delete_student_draft
)
from core.copilot_brain import generate_socratic_thinking_response
from core.web_search import execute_multi_search
from core.cohort_store import (
    DEFAULT_SEMESTER,
    DEFAULT_COURSE_ID,
    parse_attendance_file,
    preview_attendance_upload,
    confirm_attendance_import,
    list_students,
    upsert_student_by_faculty,
    move_student_lab_group,
    create_lab_group,
    list_lab_groups,
    create_project_team,
    update_project_team,
    delete_project_team,
    add_student_to_team,
    remove_student_from_team,
    move_student_between_teams,
    assign_pi_to_team,
    assign_topic_to_team,
    list_teams,
    list_pis,
    create_or_update_pi,
    authenticate_pi,
    can_user_access_team_workspace,
    get_team_workspace,
    update_team_workspace,
    get_student_project_context,
    sync_student_draft_with_team_workspace,
    get_audit_history,
    get_cohort_overview_stats,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATES_DIR,
    static_url_path="/static"
)
app.secret_key = os.environ.get("SECRET_KEY", "biowriter-studio-session-secret-2026")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Enable WhiteNoise for zero-config production static assets (Render, Railway, Heroku)
try:
    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix="static/", autorefresh=True, max_age=0)
except Exception:
    pass

seed_default_users()
seed_default_drafts()

# Register Trusted Research Workflow Agent Blueprint (Catalyst 2026)
from agent import agent_bp
app.register_blueprint(agent_bp, url_prefix="/agent")

# Enable Universal CORS (Allows file:// desktop and cross-origin access)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.route("/agent/api/<path:subpath>", methods=["OPTIONS"])
def agent_api_cors_preflight(subpath):
    resp = jsonify({"status": "ok"})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp

CONFIG_DIR = os.path.join(BASE_DIR, "config")
active_course_id = "BT_301"


def get_course_config(course_id: str = "BT_301"):
    filename_map = {
        "BT_301": "course_bt301.json",
        "GRAD_501": "course_grad501.json",
        "GRANT_STDF": "course_grant_stdf.json"
    }
    fname = filename_map.get(course_id, "course_bt301.json")
    fpath = os.path.join(CONFIG_DIR, fname)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"course_id": "BT_301", "course_name": "BT_301: Introduction to Biotechnology"}


@app.route("/")
@app.route("/index.html")
def index():
    config = get_course_config("BT_301")
    return render_template("index.html", config=config, active_course="BT_301")


@app.route("/faculty")
@app.route("/faculty.html")
def faculty_view():
    if session.get("role") in ("student", "pi") or ((session.get("student_id") or session.get("pi_id")) and not session.get("faculty_authenticated")):
        sid = session.get("student_id") or session.get("pi_name") or session.get("pi_id") or "Unauthorized Account"
        with open(os.path.join(TEMPLATES_DIR, "faculty.html"), "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('data-access-denied="false"', 'data-access-denied="true"')
        content = content.replace('data-student-id=""', f'data-student-id="{sid}"')
        content = content.replace('<strong id="denied-student-id-display">Student</strong>', f'<strong id="denied-student-id-display">{sid}</strong>')
        return content, 403

    config = get_course_config("BT_301")
    return render_template("faculty.html", config=config, active_course="BT_301", access_denied=False, is_authenticated=False)


@app.route("/test_maya_runner")
@app.route("/test_maya_runner.html")
def test_maya_runner_view():
    return render_template("test_maya_runner.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(STATIC_DIR, "favicon.ico")


@app.route("/favicon.svg")
def favicon_svg():
    for f in [
        os.path.join(STATIC_DIR, "favicon.svg"),
        os.path.join(BASE_DIR, "favicon.svg"),
        os.path.join(STATIC_DIR, "favicon.ico"),
        os.path.join(BASE_DIR, "favicon.ico")
    ]:
        if os.path.exists(f):
            mimetype = "image/svg+xml" if f.endswith(".svg") else "image/x-icon"
            return send_from_directory(os.path.dirname(f), os.path.basename(f), mimetype=mimetype)
    return "", 404


@app.route("/static/<path:filename>")
def custom_static_handler(filename):
    """Explicit fallback static handler ensuring 200 OK regardless of web server quirks."""
    return send_from_directory(STATIC_DIR, filename)


@app.route("/studio.css")
def serve_root_css():
    """Fail-safe direct CSS route bypassing any proxy or web-server /static/ interceptors."""
    if os.path.exists(os.path.join(BASE_DIR, "studio.css")):
        return send_from_directory(BASE_DIR, "studio.css", mimetype="text/css")
    if os.path.exists(os.path.join(STATIC_DIR, "studio.css")):
        return send_from_directory(STATIC_DIR, "studio.css", mimetype="text/css")
    return send_from_directory(os.path.join(STATIC_DIR, "css"), "studio.css", mimetype="text/css")



@app.route("/bt301_guide_data.js")
def serve_root_guide_data():
    """Serves bt301_guide_data.js directly from root or data directories."""
    for p in [os.path.join(BASE_DIR, "bt301_guide_data.js"),
              os.path.join(BASE_DIR, "data", "bt301_guide_data.js"),
              os.path.join(STATIC_DIR, "data", "bt301_guide_data.js")]:
        if os.path.exists(p):
            return send_from_directory(os.path.dirname(p), os.path.basename(p), mimetype="application/javascript")
    return jsonify({"error": "bt301_guide_data.js not found"}), 404


@app.route("/data/<path:filename>")
def serve_data_directory(filename):
    """Serves files from upload/data directory."""
    data_dir = os.path.join(BASE_DIR, "data")
    if os.path.exists(os.path.join(data_dir, filename)):
        mimetype = "application/javascript" if filename.endswith(".js") else "application/json" if filename.endswith(".json") else None
        return send_from_directory(data_dir, filename, mimetype=mimetype)
    return jsonify({"error": f"File {filename} not found in data"}), 404


@app.route("/detectr_aqua_figure2.png")
@app.route("/images/<path:filename>")
def serve_root_images(filename="detectr_aqua_figure2.png"):
    """Serves diagram images with multiple directory fallbacks."""
    for p in [os.path.join(BASE_DIR, filename),
              os.path.join(STATIC_DIR, filename),
              os.path.join(STATIC_DIR, "images", filename)]:
        if os.path.exists(p):
            return send_from_directory(os.path.dirname(p), os.path.basename(p), mimetype="image/png")
    return jsonify({"error": "Image not found"}), 404

@app.route("/studio.js")
def serve_root_js():
    """Fail-safe direct JS route bypassing any proxy or web-server /static/ interceptors."""
    if os.path.exists(os.path.join(BASE_DIR, "studio.js")):
        return send_from_directory(BASE_DIR, "studio.js", mimetype="application/javascript")
    if os.path.exists(os.path.join(STATIC_DIR, "studio.js")):
        return send_from_directory(STATIC_DIR, "studio.js", mimetype="application/javascript")
    return send_from_directory(os.path.join(STATIC_DIR, "js"), "studio.js", mimetype="application/javascript")


@app.route("/agent_bridge.js")
def serve_root_agent_bridge_js():
    """Fail-safe direct JS route for agent_bridge.js."""
    if os.path.exists(os.path.join(STATIC_DIR, "agent_bridge.js")):
        return send_from_directory(STATIC_DIR, "agent_bridge.js", mimetype="application/javascript")
    if os.path.exists(os.path.join(BASE_DIR, "agent_bridge.js")):
        return send_from_directory(BASE_DIR, "agent_bridge.js", mimetype="application/javascript")
    return "", 404


@app.route("/faculty_cohort.js")
def serve_root_faculty_cohort_js():
    """Fail-safe direct JS route for faculty_cohort.js."""
    if os.path.exists(os.path.join(STATIC_DIR, "faculty_cohort.js")):
        return send_from_directory(STATIC_DIR, "faculty_cohort.js", mimetype="application/javascript")
    if os.path.exists(os.path.join(BASE_DIR, "faculty_cohort.js")):
        return send_from_directory(BASE_DIR, "faculty_cohort.js", mimetype="application/javascript")
    return "", 404


@app.route("/student_team_workspace.js")
def serve_root_student_team_workspace_js():
    """Fail-safe direct JS route for student_team_workspace.js."""
    if os.path.exists(os.path.join(STATIC_DIR, "student_team_workspace.js")):
        return send_from_directory(STATIC_DIR, "student_team_workspace.js", mimetype="application/javascript")
    if os.path.exists(os.path.join(BASE_DIR, "student_team_workspace.js")):
        return send_from_directory(BASE_DIR, "student_team_workspace.js", mimetype="application/javascript")
    return "", 404



@app.route("/api/writing/audit_all", methods=["POST"])
def api_audit_all_writing():
    data = request.get_json() or {}
    return jsonify(audit_all_writing_sections(data))



@app.route("/api/config", methods=["GET"])
def api_get_config():
    cid = session.get("active_course_id", active_course_id)
    return jsonify(get_course_config(cid))


@app.route("/api/courses", methods=["GET"])
def api_list_courses():
    cid = session.get("active_course_id", active_course_id)
    courses = [
        {"id": "BT_301", "name": "BT_301: Introduction to Biotechnology (Research Proposals)"},
        {"id": "GRAD_501", "name": "GRAD_501: Senior Graduation Project & Capstone Thesis"},
        {"id": "GRANT_STDF", "name": "GRANT_STDF: National & International Grant Standard (STDF/ICGEB)"}
    ]
    return jsonify({"courses": courses, "active": cid})


@app.route("/api/courses/switch", methods=["POST"])
def api_switch_course():
    data = request.get_json() or {}
    cid = data.get("course_id", "BT_301")
    if cid in ["BT_301", "GRAD_501", "GRANT_STDF"]:
        session["active_course_id"] = cid
        return jsonify({"success": True, "course": get_course_config(cid)})
    return jsonify({"success": False, "error": "Unknown course ID"}), 400


@app.route("/api/search/build", methods=["POST"])
def api_build_search():
    data = request.get_json() or {}
    system = data.get("chassis") or data.get("system", "")
    tool = data.get("tool", "")
    target = data.get("target", "")
    synonyms = data.get("synonyms", {})
    result = build_boolean_query(system, tool, target, synonyms)
    return jsonify(result)


@app.route("/api/search/examples", methods=["GET"])
def api_search_examples():
    return jsonify(get_curated_examples())


@app.route("/api/paraphrase/check", methods=["POST"])
def api_check_paraphrase():
    data = request.get_json() or {}
    original = data.get("original", "")
    draft = data.get("draft", "")
    result = audit_paraphrase_rhev(original, draft)
    return jsonify(result)


@app.route("/api/reference/lookup", methods=["POST"])
def api_lookup_reference():
    data = request.get_json() or {}
    doi = data.get("doi", "")
    result = fetch_doi_metadata(doi)
    return jsonify(result)


@app.route("/api/reference/audit_recency", methods=["POST"])
def api_audit_recency():
    data = request.get_json() or {}
    refs = data.get("references", "")
    result = audit_bibliography_recency(refs)
    return jsonify(result)


@app.route("/api/starters", methods=["GET"])
def api_get_starters():
    return jsonify(get_sentence_starters())


@app.route("/api/socratic/critique", methods=["POST"])
def api_socratic_critique():
    data = request.get_json() or {}
    section = data.get("section", "Draft")
    text = data.get("text", "")
    context = data.get("context", {})
    result = analyze_student_draft(section, text, context)
    return jsonify(result)


@app.route("/api/audit/full", methods=["POST"])
def api_audit_full():
    data = request.get_json() or {}
    result = calculate_full_rubric_audit(data)
    return jsonify(result)


@app.route("/api/viva/generate", methods=["POST"])
def api_generate_viva():
    data = request.get_json() or {}
    questions = generate_viva_defense_questions(data)
    return jsonify({"questions": questions})


@app.route("/api/instructor/comments", methods=["GET"])
def api_get_instructor_comments():
    return jsonify(get_rapid_comment_bank())


@app.route("/api/instructor/report", methods=["POST"])
@app.route("/api/instructor/compile_memo", methods=["POST"])
def api_create_instructor_report():
    data = request.get_json() or {}
    student_data = data.get("student_data", {})
    codes = data.get("codes") or data.get("selected_codes") or []
    manual = data.get("manual_comments", "")
    report = compile_instructor_feedback_report(student_data, codes, manual)
    return jsonify(report)


# ==========================================================================
# Student Authentication & Session Routes
# ==========================================================================

# ==========================================================================
# Faculty Authentication Routes
# ==========================================================================
def _get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


@app.route("/api/faculty/login", methods=["POST"])
def api_faculty_login():
    client_ip = _get_client_ip()

    # 1. Check anti-brute-force rate limiter & lockout
    allowed, lock_msg, remaining_sec = check_faculty_rate_limit(client_ip)
    if not allowed:
        return jsonify({
            "success": False,
            "error": lock_msg,
            "locked": True,
            "remaining_seconds": remaining_sec
        }), 429

    data = request.get_json() or {}
    passcode = data.get("passcode") or data.get("password", "")

    # 2. Cryptographically verify passcode against PBKDF2 salted hashes
    if verify_faculty_passcode(passcode):
        record_faculty_attempt(client_ip, success=True)
        # Clear student session if one was active
        session.pop("student_id", None)
        session.pop("student_name", None)
        session["faculty_authenticated"] = True
        session["role"] = "faculty"
        session["faculty_name"] = "Course Instructor & Review Chair"
        return jsonify({"success": True, "message": "Faculty access verified.", "redirect": "/faculty"})

    # Failed attempt: record and apply 1.0s artificial throttle
    import time
    time.sleep(1.0)
    att_res = record_faculty_attempt(client_ip, success=False)
    status_code = 429 if att_res.get("locked") else 401
    return jsonify({
        "success": False,
        "error": att_res.get("message", "Invalid instructor access passcode."),
        "locked": att_res.get("locked", False),
        "attempts": att_res.get("attempts", 1),
        "remaining_tries": att_res.get("remaining_tries", 0)
    }), status_code


@app.route("/api/faculty/logout", methods=["POST"])
def api_faculty_logout():
    session.pop("faculty_authenticated", None)
    if session.get("role") == "faculty":
        session.pop("role", None)
    return jsonify({"success": True, "message": "Faculty session signed out."})


@app.route("/api/faculty/me", methods=["GET"])
def api_faculty_me():
    is_auth = bool(session.get("faculty_authenticated"))
    is_student = session.get("role") == "student"
    return jsonify({
        "authenticated": is_auth,
        "is_student": is_student,
        "student_id": session.get("student_id") if is_student else None
    })

@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.get_json() or {}
    sid = data.get("student_id", "").strip()
    name = data.get("student_name", "").strip()
    pwd = data.get("password", "")
    result = register_student(sid, name, pwd)
    if result.get("success"):
        session["student_id"] = result["user"]["student_id"]
        session["student_name"] = result["user"]["student_name"]
        session["role"] = "student"
        ctx = get_student_project_context(result["user"]["student_id"])
        draft = get_student_draft(result["user"]["student_id"])
        if not draft and ctx.get("workspace") and ctx["workspace"].get("proposal_draft"):
            draft = ctx["workspace"]["proposal_draft"]
        result["draft"] = sanitize_draft_for_student(draft) if draft else None
        result["my_project"] = ctx.get("my_project")
        result["team_workspace"] = ctx.get("workspace")
    return jsonify(result), (200 if result.get("success") else 400)


def sanitize_draft_for_student(draft_dict):
    """Enforces strict pedagogical No-Grades policy for students:
    strips numeric GPA and raw score fields, keeping qualitative review status,
    action items, and feedback memo intact."""
    if not draft_dict or not isinstance(draft_dict, dict):
        return draft_dict
    sanitized = json.loads(json.dumps(draft_dict))
    if "faculty_review" in sanitized and isinstance(sanitized["faculty_review"], dict):
        rev = sanitized["faculty_review"]
        rev.pop("gpa", None)
        rev.pop("raw_total", None)
        if "criterion_overrides" in rev and isinstance(rev["criterion_overrides"], dict):
            clean_overrides = {}
            for k, v in rev["criterion_overrides"].items():
                if isinstance(v, dict):
                    clean_overrides[k] = {"notes": v.get("notes", "")}
                else:
                    clean_overrides[k] = {"notes": str(v)}
            rev["criterion_overrides"] = clean_overrides
        sanitized["faculty_review"] = rev
    return sanitized


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json() or {}
    sid = (data.get("student_id") or data.get("identifier") or "").strip()
    pwd = data.get("password", "")
    result = authenticate_student(sid, pwd)
    if result.get("success"):
        session.pop("faculty_authenticated", None)
        session.pop("pi_id", None)
        session.pop("pi_name", None)
        session["student_id"] = result["user"]["student_id"]
        session["student_name"] = result["user"]["student_name"]
        session["role"] = "student"
        ctx = get_student_project_context(result["user"]["student_id"])
        draft = get_student_draft(result["user"]["student_id"])
        if ctx.get("workspace") and ctx["workspace"].get("proposal_draft"):
            # If the student's team has a shared proposal draft, prefer or merge it
            ws_draft = ctx["workspace"]["proposal_draft"]
            if not draft or ws_draft.get("title") or ws_draft.get("methodology"):
                draft = ws_draft
        result["draft"] = sanitize_draft_for_student(draft)
        result["my_project"] = ctx.get("my_project")
        result["team_workspace"] = ctx.get("workspace")
    return jsonify(result), (200 if result.get("success") else 401)


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.clear()
    return jsonify({"success": True, "message": "Signed out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    sid = session.get("student_id")
    if not sid:
        return jsonify({"authenticated": False})
    user = get_student_user(sid)
    if not user:
        session.clear()
        return jsonify({"authenticated": False})
    ctx = get_student_project_context(sid)
    draft = get_student_draft(sid)
    if ctx.get("workspace") and ctx["workspace"].get("proposal_draft"):
        ws_draft = ctx["workspace"]["proposal_draft"]
        if not draft or ws_draft.get("title") or ws_draft.get("methodology"):
            draft = ws_draft
    return jsonify({
        "authenticated": True,
        "user": user,
        "draft": sanitize_draft_for_student(draft),
        "my_project": ctx.get("my_project"),
        "team_workspace": ctx.get("workspace"),
    })


def _is_authorized_for_student_draft(target_id: str, write_access: bool = False) -> bool:
    """Verifies whether the current session is authorized to read or write a student draft."""
    clean_target = (target_id or "").strip().upper()
    if not clean_target:
        return False
    # Faculty has full read/write access
    if session.get("faculty_authenticated") and session.get("role") == "faculty":
        return True
    # Public demo exemplars (13989, ST-2026-01, guest/custom starter IDs)
    if clean_target in ("13989", "ST-2026-01", "CUSTOM-TOPIC-01", "BT301-NANOMED", "BT301-BIOCAT"):
        return True
    session_sid = (session.get("student_id") or "").strip().upper()
    if session_sid and session_sid == clean_target:
        return True
    # Also allow if session_sid and clean_target belong to the same active project team
    if session_sid:
        ctx = get_student_project_context(session_sid)
        my_proj = ctx.get("my_project") or {}
        member_ids = [str(m.get("student_id", "")).upper() for m in my_proj.get("members", [])]
        if clean_target in member_ids or clean_target == str(my_proj.get("team_id", "")).upper():
            return True
    # If the target ID belongs to a registered student account, block unauthenticated or cross-student access
    registered_owner = get_student_user(clean_target)
    if registered_owner is not None:
        return False
    # Allow unauthenticated local/guest custom IDs that are not registered accounts
    return not bool(session_sid)


@app.route("/api/student/save_draft", methods=["POST"])
def api_save_student_draft():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip() or session.get("student_id", "")
    if not _is_authorized_for_student_draft(student_id, write_access=True):
        return jsonify({"success": False, "error": "Unauthorized: You cannot overwrite another registered student's proposal draft."}), 403
    student_data = data.get("student_data", data)
    result = save_student_draft(student_id, student_data)
    # Synchronize with shared Team Workspace if student belongs to an active team
    sync_student_draft_with_team_workspace(student_id, student_data)
    if not session.get("student_id") and result.get("student_id"):
        session["guest_draft_id"] = str(result["student_id"]).strip().upper()
    return jsonify(result)


@app.route("/api/student/toggle_lock", methods=["POST"])
def api_student_toggle_lock():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip() or session.get("student_id", "")
    is_locked = bool(data.get("is_locked", True))
    if not student_id:
        return jsonify({"success": False, "error": "Student ID required."}), 400
    if not _is_authorized_for_student_draft(student_id, write_access=True):
        return jsonify({"success": False, "error": "Unauthorized: Cannot modify lock state for another student's draft."}), 403
    res = toggle_draft_lock(student_id, is_locked)
    return jsonify(res)


@app.route("/api/student/drafts", methods=["GET"])
def api_list_student_drafts():
    all_drafts = list_student_drafts()
    if session.get("faculty_authenticated") and session.get("role") == "faculty":
        return jsonify(all_drafts)
    # For students or unauthenticated requests, only expose their own draft + public demo exemplar 13989
    session_sid = (session.get("student_id") or "").strip().upper()
    guest_sid = (session.get("guest_draft_id") or "").strip().upper() if not session_sid else ""
    allowed_ids = {s for s in (session_sid, guest_sid, "13989", "ST-2026-01") if s}
    filtered = [
        d for d in (all_drafts if isinstance(all_drafts, list) else all_drafts.get("drafts", []))
        if str(d.get("student_id", "")).upper() in allowed_ids
    ]
    if isinstance(all_drafts, dict):
        return jsonify({**all_drafts, "drafts": filtered})
    return jsonify(filtered)


@app.route("/api/student/draft/<student_id>", methods=["GET"])
def api_get_student_draft(student_id):
    if not _is_authorized_for_student_draft(student_id, write_access=False):
        return jsonify({"success": False, "error": "Unauthorized access to another student's proposal draft."}), 403
    draft = get_student_draft(student_id)
    if draft:
        # If faculty is requesting, return full draft; if student is requesting, redact numeric grades
        is_faculty = bool(session.get("faculty_authenticated"))
        payload = draft if is_faculty else sanitize_draft_for_student(draft)
        return jsonify({"success": True, "draft": payload})
    return jsonify({"success": False, "error": f"Student draft '{student_id}' not found."}), 404


@app.route("/api/instructor/dispatch_feedback", methods=["POST"])
def api_instructor_dispatch_feedback():
    if not session.get("faculty_authenticated"):
        return jsonify({"success": False, "error": "Faculty authorization required to dispatch evaluation."}), 401
    
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    if not student_id:
        return jsonify({"success": False, "error": "Student ID required."}), 400

    payload = data.get("feedback") if isinstance(data.get("feedback"), dict) else data
    feedback = {
        "instructor_name": payload.get("instructor_name", "BT_301 Faculty Evaluation Board"),
        "gpa": payload.get("gpa", 0.0),
        "raw_total": payload.get("raw_total", 0.0),
        "standing": payload.get("standing", "Evaluated"),
        "criterion_overrides": payload.get("criterion_overrides", {}),
        "manual_notes": payload.get("manual_notes", ""),
        "action_items": payload.get("action_items", []),
        "memo_text": payload.get("memo_text", "")
    }

    result = dispatch_faculty_feedback(student_id, feedback)
    return jsonify(result)


@app.route("/api/faculty/submission/<student_id>", methods=["DELETE", "POST"])
def api_faculty_delete_submission(student_id):
    """Deletes a student proposal submission. Requires faculty authorization."""
    if not session.get("faculty_authenticated") or session.get("role") != "faculty":
        return jsonify({"success": False, "error": "Faculty authorization required to remove submissions."}), 403

    clean_id = (student_id or "").strip()
    if not clean_id:
        return jsonify({"success": False, "error": "Student ID is required."}), 400

    result = delete_student_draft(clean_id)
    status_code = 200 if result.get("success") else 404
    return jsonify(result), status_code


@app.route("/api/export/docx", methods=["POST"])
def api_export_docx():
    data = request.get_json() or {}
    audit_results = calculate_full_rubric_audit(data)
    doc_io = generate_docx_portfolio(data, audit_results)
    
    filename = f"Proposal_Portfolio_{data.get('student_name', 'Student').replace(' ', '_')}.docx"
    return send_file(
        doc_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.route("/api/export/pptx", methods=["POST"])
def api_export_pptx():
    data = request.get_json() or {}
    audit_results = calculate_full_rubric_audit(data)
    pptx_io = create_defense_presentation(data, audit_results)
    
    filename = f"Oral_Defense_Slides_{data.get('student_name', 'Student').replace(' ', '_')}.pptx"
    return send_file(
        pptx_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@app.route("/api/export/md", methods=["POST"])
def api_export_md():
    data = request.get_json() or {}
    audit_results = calculate_full_rubric_audit(data)
    md_content = generate_markdown_portfolio(data, audit_results)
    
    filename = f"Proposal_Portfolio_{data.get('student_name', 'Student').replace(' ', '_')}.md"
    from io import BytesIO
    buf = BytesIO(md_content.encode("utf-8"))
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="text/markdown"
    )


# -------------------------------------------------------------
# Impact, Novelty, Gap & Competitor API Endpoints
# -------------------------------------------------------------

@app.route("/api/impact/gap_taxonomy", methods=["GET"])
def api_get_gap_taxonomy():
    return jsonify(GAP_TAXONOMY)


@app.route("/api/impact/gap_audit", methods=["POST"])
def api_audit_gap():
    data = request.get_json() or {}
    gap_text = data.get("gap_text", "")
    gap_type = data.get("gap_type", "")
    return jsonify(audit_gap_statement(gap_text, selected_gap_type=gap_type))


@app.route("/api/impact/novelty_audit", methods=["POST"])
def api_audit_novelty():
    data = request.get_json() or {}
    return jsonify(audit_novelty_and_soundness(
        title=data.get("title", ""),
        chassis=data.get("chassis", "") or data.get("system", ""),
        tool=data.get("tool", ""),
        target=data.get("target", ""),
        hypothesis=data.get("hypothesis", ""),
        methodology=data.get("methodology", "")
    ))


@app.route("/api/impact/significance_search", methods=["POST"])
def api_significance_search():
    data = request.get_json() or {}
    return jsonify(build_significance_search_queries(
        chassis=data.get("chassis", "") or data.get("system", ""),
        tool=data.get("tool", ""),
        target=data.get("target", ""),
        project_modality=data.get("modality", "cellular")
    ))


@app.route("/api/impact/competitor_audit", methods=["POST"])
def api_audit_competitor():
    data = request.get_json() or {}
    return jsonify(audit_competitor_matrix_and_usp(
        competitor_data=data.get("competitor_data", {}),
        usp_text=data.get("usp_text", "")
    ))


@app.route("/api/impact/chain_check", methods=["POST"])
def api_check_logic_chain():
    data = request.get_json() or {}
    return jsonify(evaluate_proposal_logic_chain(data))


@app.route("/api/paper/samples", methods=["GET"])
def api_get_paper_samples():
    return jsonify(SAMPLE_PAPERS)


@app.route("/api/paper/fetch", methods=["POST"])
def api_fetch_paper():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    return jsonify(fetch_paper_abstract_and_meta(identifier))


@app.route("/api/paper/summarize", methods=["POST"])
def api_summarize_paper():
    data = request.get_json() or {}
    text = data.get("text", "")
    title = data.get("title", "")
    identifier = data.get("identifier", "")
    authors = data.get("authors", "")
    year = data.get("year")
    journal = data.get("journal", "")
    return jsonify(deconstruct_paper(
        text=text,
        title=title,
        identifier=identifier,
        authors=authors,
        year=year,
        journal=journal
    ))


@app.route("/api/breakthroughs", methods=["GET"])
def api_get_breakthroughs():
    category = request.args.get("category", "All")
    storage_filter = request.args.get("storage_filter", "all")
    search_query = request.args.get("q", "")
    data = get_breakthroughs_catalog(
        category=category,
        storage_filter=storage_filter,
        search_query=search_query
    )
    return jsonify({
        "status": "success",
        "creators": CREATORS,
        "copyright": COPYRIGHT_NOTICE,
        **data
    })


@app.route("/api/breakthroughs/sync", methods=["POST"])
def api_sync_breakthroughs():
    data = request.get_json() or {}
    topic = data.get("topic", "").strip()
    result = sync_europepmc_breakthroughs(custom_topic=topic)
    return jsonify({
        "status": "success",
        "creators": CREATORS,
        "copyright": COPYRIGHT_NOTICE,
        **result
    })


@app.route("/api/breakthroughs/bookmark", methods=["POST"])
def api_bookmark_breakthrough():
    data = request.get_json() or {}
    item_id = data.get("id", "").strip()
    if not item_id:
        return jsonify({"status": "error", "message": "Item ID is required"}), 400
    res = toggle_breakthrough_bookmark(item_id)
    return jsonify({
        "status": "success",
        **res
    })


@app.route("/api/copilot/message", methods=["POST"])
def api_copilot_message():
    data = request.get_json() or {}
    message = data.get("message", "")
    context = data.get("context", {})
    history = data.get("history", [])
    result = generate_socratic_thinking_response(message, context, history)
    return jsonify({
        "status": "success",
        **result
    })


@app.route("/api/guide/chapters", methods=["GET"])
def api_get_guide_chapters():
    chapters = get_all_chapters()
    return jsonify({
        "status": "success",
        "total": len(chapters),
        "chapters": chapters
    })


@app.route("/api/guide/chapter/<int:chapter_num>", methods=["GET"])
def api_get_guide_chapter(chapter_num):
    ch = get_chapter(chapter_num)
    if not ch:
        return jsonify({"status": "error", "message": f"Chapter {chapter_num} not found"}), 404
    return jsonify({
        "status": "success",
        "chapter": ch
    })


@app.route("/api/guide/search", methods=["GET", "POST"])
def api_search_guide():
    if request.method == "POST":
        data = request.get_json() or {}
        q = data.get("query", data.get("q", ""))
        limit = int(data.get("limit", 10))
    else:
        q = request.args.get("q", request.args.get("query", ""))
        limit = int(request.args.get("limit", 10))
    results = search_guide(q, limit=limit)
    return jsonify({
        "status": "success",
        "query": q,
        "results": results
    })


@app.route("/api/guide/quick_finder", methods=["GET"])
def api_get_guide_quick_finder():
    items = get_quick_finder()
    return jsonify({
        "status": "success",
        "items": items
    })


@app.route("/api/guide/sentence_coach", methods=["GET"])
def api_get_sentence_coach():
    coach = get_sentence_formulation_guide()
    return jsonify({
        "status": "success",
        **coach
    })


@app.route("/api/search/web", methods=["GET", "POST"])
def api_search_web():
    if request.method == "POST":
        data = request.get_json() or {}
        query = data.get("query", "").strip()
    else:
        query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"status": "error", "message": "Search query is required"}), 400

    result = execute_multi_search(query)
    return jsonify({
        "status": "success",
        **result
    })


# ==========================================================================
# Cohort, Attendance, Lab Groups, Project Teams, PIs, Topics & Shared Workspaces
# ==========================================================================

def _is_faculty_session() -> bool:
    return bool(session.get("faculty_authenticated") and session.get("role") == "faculty")


def _is_pi_session() -> bool:
    return bool(session.get("role") == "pi" and session.get("pi_id"))


def _get_session_actor():
    if _is_faculty_session():
        return ("faculty", "FACULTY", session.get("faculty_name", "Faculty Coordinator"))
    if _is_pi_session():
        return ("pi", session.get("pi_id", "PI"), session.get("pi_name", "Project Supervisor"))
    if session.get("student_id"):
        return ("student", session.get("student_id"), session.get("student_name", session.get("student_id")))
    return ("guest", "", "Unauthenticated Visitor")


@app.route("/api/faculty/cohort/overview", methods=["GET"])
def api_faculty_cohort_overview():
    if not _is_faculty_session() and not _is_pi_session():
        return jsonify({"success": False, "error": "Faculty or PI authorization required."}), 403
    sem = request.args.get("semester") or session.get("active_semester", DEFAULT_SEMESTER)
    cid = request.args.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID)
    stats = get_cohort_overview_stats(semester=sem, course_id=cid)
    pis_res = list_pis()
    lg_res = list_lab_groups(semester=sem, course_id=cid)
    teams_res = list_teams(semester=sem, course_id=cid)
    history = get_audit_history(semester=sem, course_id=cid, limit=50)
    return jsonify({
        "success": True,
        "overview": stats,
        "pis": pis_res.get("pis", []),
        "lab_groups": lg_res.get("lab_groups", []),
        "unassigned_lab_group_students": lg_res.get("unassigned_lab_group_students", []),
        "teams": teams_res.get("teams", []),
        "audit_history": history,
    })


@app.route("/api/faculty/cohort/context", methods=["POST"])
def api_faculty_switch_cohort_context():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Faculty authorization required."}), 403
    data = request.get_json() or {}
    sem = (data.get("semester") or DEFAULT_SEMESTER).strip()
    cid = (data.get("course_id") or DEFAULT_COURSE_ID).strip()
    session["active_semester"] = sem
    session["active_course_id"] = cid
    stats = get_cohort_overview_stats(semester=sem, course_id=cid)
    return jsonify({"success": True, "semester": stats["semester"], "course_id": stats["course_id"], "overview": stats})


# 1. ATTENDANCE UPLOAD, PREVIEW & CONFIRMATION
@app.route("/api/faculty/attendance/preview", methods=["POST"])
def api_faculty_attendance_preview():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can upload attendance sheets."}), 403

    _, _, actor_name = _get_session_actor()
    sem = request.form.get("semester") or request.args.get("semester")
    cid = request.form.get("course_id") or request.args.get("course_id")
    filename = "attendance.csv"
    raw_rows = []

    if "file" in request.files and request.files["file"].filename:
        f = request.files["file"]
        filename = f.filename
        file_bytes = f.read()
        raw_rows = parse_attendance_file(filename, file_bytes)
    else:
        data = request.get_json(silent=True) or {}
        sem = sem or data.get("semester")
        cid = cid or data.get("course_id")
        filename = data.get("filename", filename)
        if isinstance(data.get("rows"), list):
            raw_rows = data["rows"]
        elif data.get("csv_text"):
            raw_rows = parse_attendance_file("attendance.csv", str(data["csv_text"]).encode("utf-8"))

    sem = sem or session.get("active_semester", DEFAULT_SEMESTER)
    cid = cid or session.get("active_course_id", DEFAULT_COURSE_ID)

    if not raw_rows:
        return jsonify({"success": False, "error": "No attendance rows detected in the uploaded file."}), 400

    res = preview_attendance_upload(
        raw_rows=raw_rows,
        semester=sem,
        course_id=cid,
        filename=filename,
        actor=actor_name,
    )
    return jsonify(res)


@app.route("/api/faculty/attendance/confirm", methods=["POST"])
def api_faculty_attendance_confirm():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can confirm attendance imports."}), 403

    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    preview_id = (data.get("preview_id") or "").strip()
    if not preview_id:
        return jsonify({"success": False, "error": "preview_id is required to confirm attendance import."}), 400

    res = confirm_attendance_import(preview_id=preview_id, actor=actor_name)
    return jsonify(res), (200 if res.get("success") else 400)


# 2. STUDENT DIRECTORY & FILTERING
@app.route("/api/faculty/students", methods=["GET", "POST"])
def api_faculty_students():
    if request.method == "POST":
        if not _is_faculty_session():
            return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can add or modify student records."}), 403
        _, _, actor_name = _get_session_actor()
        data = request.get_json() or {}
        res = upsert_student_by_faculty(
            student_id=data.get("student_id", ""),
            student_name=data.get("student_name", ""),
            lab_group=data.get("lab_group", ""),
            email=data.get("email", ""),
            semester=data.get("semester") or session.get("active_semester", DEFAULT_SEMESTER),
            course_id=data.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID),
            actor=actor_name,
        )
        return jsonify(res), (200 if res.get("success") else 400)

    if not _is_faculty_session() and not _is_pi_session():
        return jsonify({"success": False, "error": "Forbidden: Faculty or PI authorization required."}), 403

    sem = request.args.get("semester") or session.get("active_semester", DEFAULT_SEMESTER)
    cid = request.args.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID)
    lab_group = request.args.get("lab_group")
    team_id = request.args.get("team_id")
    pi_id = request.args.get("pi_id") or (session.get("pi_id") if _is_pi_session() else None)
    assignment_status = request.args.get("assignment_status")
    q = request.args.get("q")

    res = list_students(
        semester=sem,
        course_id=cid,
        lab_group=lab_group,
        team_id=team_id,
        pi_id=pi_id,
        assignment_status=assignment_status,
        search_query=q,
    )
    return jsonify(res)


# 3. LAB GROUP MANAGEMENT & STUDENT LAB GROUP MOVE
@app.route("/api/faculty/lab_groups", methods=["GET", "POST"])
def api_faculty_lab_groups():
    if request.method == "POST":
        if not _is_faculty_session():
            return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can create lab groups."}), 403
        _, _, actor_name = _get_session_actor()
        data = request.get_json() or {}
        res = create_lab_group(
            lab_group_id=data.get("lab_group_id") or data.get("lab_group", ""),
            name=data.get("name", ""),
            semester=data.get("semester") or session.get("active_semester", DEFAULT_SEMESTER),
            course_id=data.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID),
            actor=actor_name,
        )
        return jsonify(res), (200 if res.get("success") else 400)

    if not _is_faculty_session() and not _is_pi_session():
        return jsonify({"success": False, "error": "Forbidden: Faculty authorization required."}), 403

    sem = request.args.get("semester") or session.get("active_semester", DEFAULT_SEMESTER)
    cid = request.args.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID)
    return jsonify(list_lab_groups(semester=sem, course_id=cid))


@app.route("/api/faculty/students/move_lab_group", methods=["POST"])
def api_faculty_move_student_lab_group():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Students cannot change their own or others' lab group."}), 403
    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    res = move_student_lab_group(
        student_id=data.get("student_id", ""),
        new_lab_group=data.get("new_lab_group") or data.get("lab_group", ""),
        actor=data.get("actor") or actor_name,
        semester=data.get("semester"),
        course_id=data.get("course_id"),
    )
    return jsonify(res), (200 if res.get("success") else 400)


# 4. PROJECT TEAMS SETUP WITHIN LAB GROUPS
@app.route("/api/faculty/teams", methods=["GET", "POST"])
def api_faculty_teams():
    if request.method == "POST":
        if not _is_faculty_session():
            return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can create project teams."}), 403
        _, _, actor_name = _get_session_actor()
        data = request.get_json() or {}
        res = create_project_team(
            lab_group=data.get("lab_group", ""),
            team_name=data.get("team_name", ""),
            team_id=data.get("team_id", ""),
            student_ids=data.get("student_ids", []),
            pi_id=data.get("pi_id", ""),
            topic_title=data.get("topic_title", ""),
            topic_description=data.get("topic_description", ""),
            topic_category=data.get("topic_category", ""),
            semester=data.get("semester") or session.get("active_semester", DEFAULT_SEMESTER),
            course_id=data.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID),
            actor=actor_name,
        )
        return jsonify(res), (200 if res.get("success") else 400)

    if not _is_faculty_session() and not _is_pi_session():
        return jsonify({"success": False, "error": "Forbidden: Faculty or PI authorization required."}), 403

    sem = request.args.get("semester") or session.get("active_semester", DEFAULT_SEMESTER)
    cid = request.args.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID)
    lab_group = request.args.get("lab_group")
    pi_id = request.args.get("pi_id") or (session.get("pi_id") if _is_pi_session() else None)
    return jsonify(list_teams(semester=sem, course_id=cid, lab_group=lab_group, pi_id=pi_id))


@app.route("/api/faculty/teams/<team_id>", methods=["PUT", "DELETE", "POST"])
def api_faculty_team_modify(team_id):
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can modify project teams."}), 403
    _, _, actor_name = _get_session_actor()
    if request.method == "DELETE":
        res = delete_project_team(team_id=team_id, actor=actor_name)
        return jsonify(res), (200 if res.get("success") else 404)

    data = request.get_json() or {}
    if data.get("action") == "delete":
        res = delete_project_team(team_id=team_id, actor=actor_name)
        return jsonify(res), (200 if res.get("success") else 404)

    res = update_project_team(
        team_id=team_id,
        team_name=data.get("team_name"),
        status=data.get("status"),
        actor=actor_name,
    )
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/faculty/teams/<team_id>/members", methods=["POST"])
def api_faculty_team_add_member(team_id):
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Students cannot change team membership."}), 403
    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    res = add_student_to_team(
        team_id=team_id,
        student_id=data.get("student_id", ""),
        allow_move=bool(data.get("allow_move", False)),
        actor=actor_name,
    )
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/faculty/teams/<team_id>/members/<student_id>", methods=["DELETE", "POST"])
def api_faculty_team_remove_member(team_id, student_id):
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Students cannot remove team members."}), 403
    _, _, actor_name = _get_session_actor()
    res = remove_student_from_team(team_id=team_id, student_id=student_id, actor=actor_name)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/faculty/teams/move_student", methods=["POST"])
def api_faculty_move_student_team():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can move students between teams."}), 403
    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    res = move_student_between_teams(
        student_id=data.get("student_id", ""),
        target_team_id=data.get("target_team_id") or data.get("team_id", ""),
        actor=actor_name,
    )
    return jsonify(res), (200 if res.get("success") else 400)


# 5 & 6. PI ASSIGNMENT & TOPIC ASSIGNMENT
@app.route("/api/faculty/pis", methods=["GET", "POST"])
def api_faculty_pis():
    if request.method == "POST":
        if not _is_faculty_session():
            return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can register PIs."}), 403
        _, _, actor_name = _get_session_actor()
        data = request.get_json() or {}
        res = create_or_update_pi(
            name=data.get("name", ""),
            email=data.get("email", ""),
            title=data.get("title", "Project Supervisor / PI"),
            department=data.get("department", "Biotechnology & Genetic Engineering"),
            pi_id=data.get("pi_id", ""),
            passcode=data.get("passcode", "pi2026"),
            actor=actor_name,
        )
        return jsonify(res), (200 if res.get("success") else 400)

    return jsonify(list_pis())


@app.route("/api/faculty/teams/<team_id>/assign_pi", methods=["POST"])
def api_faculty_assign_pi(team_id):
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can assign or change a team's PI."}), 403
    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    res = assign_pi_to_team(
        team_id=team_id,
        pi_id=data.get("pi_id", ""),
        pi_name=data.get("pi_name", ""),
        pi_email=data.get("pi_email", ""),
        actor=actor_name,
    )
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/faculty/teams/<team_id>/assign_topic", methods=["POST"])
def api_faculty_assign_topic(team_id):
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Only Faculty/Coordinators can assign or change a team's official topic."}), 403
    _, _, actor_name = _get_session_actor()
    data = request.get_json() or {}
    res = assign_topic_to_team(
        team_id=team_id,
        topic_title=data.get("topic_title", ""),
        topic_description=data.get("topic_description", ""),
        topic_category=data.get("topic_category", ""),
        actor=actor_name,
    )
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/faculty/audit_history", methods=["GET"])
def api_faculty_audit_history():
    if not _is_faculty_session():
        return jsonify({"success": False, "error": "Forbidden: Faculty authorization required."}), 403
    sem = request.args.get("semester")
    cid = request.args.get("course_id")
    student_id = request.args.get("student_id")
    team_id = request.args.get("team_id")
    lab_group = request.args.get("lab_group")
    history = get_audit_history(
        semester=sem,
        course_id=cid,
        student_id=student_id,
        team_id=team_id,
        lab_group=lab_group,
        limit=100,
    )
    return jsonify({"success": True, "history": history})


# 7. PI LOGIN & SUPERVISED TEAMS VIEW
@app.route("/api/pi/login", methods=["POST"])
def api_pi_login():
    data = request.get_json() or {}
    pi_ident = data.get("pi_id") or data.get("email") or data.get("identifier", "")
    passcode = data.get("passcode") or data.get("password", "")
    res = authenticate_pi(pi_ident, passcode)
    if res.get("success"):
        session.pop("student_id", None)
        session.pop("student_name", None)
        session["role"] = "pi"
        session["pi_id"] = res["pi"]["pi_id"]
        session["pi_name"] = res["pi"]["name"]
        session["pi_email"] = res["pi"].get("email", "")
        return jsonify(res)
    return jsonify(res), 401


@app.route("/api/pi/my_teams", methods=["GET"])
def api_pi_my_teams():
    if _is_pi_session():
        target_pi_id = session.get("pi_id")
    elif _is_faculty_session():
        target_pi_id = request.args.get("pi_id")
    else:
        return jsonify({"success": False, "error": "PI or Faculty authentication required."}), 403

    sem = request.args.get("semester") or session.get("active_semester", DEFAULT_SEMESTER)
    cid = request.args.get("course_id") or session.get("active_course_id", DEFAULT_COURSE_ID)
    res = list_teams(semester=sem, course_id=cid, pi_id=target_pi_id)
    return jsonify({
        "success": True,
        "pi_id": target_pi_id,
        "pi_name": session.get("pi_name", ""),
        "teams": res.get("teams", []),
    })


# 8. STUDENT 'MY PROJECT' & SHARED TEAM WORKSPACE (PERSISTED BY TEAM ID)
@app.route("/api/student/my_project", methods=["GET"])
def api_student_my_project():
    sid = request.args.get("student_id") if (_is_faculty_session() or _is_pi_session()) else None
    sid = sid or session.get("student_id")
    if not sid:
        return jsonify({"success": False, "error": "Student authentication required."}), 401

    ctx = get_student_project_context(sid)
    if ctx.get("workspace") and session.get("role") == "student":
        ws = json.loads(json.dumps(ctx["workspace"]))
        if "proposal_draft" in ws:
            ws["proposal_draft"] = sanitize_draft_for_student(ws["proposal_draft"])
        ctx["workspace"] = ws
    return jsonify(ctx)


@app.route("/api/teams/<team_id>/workspace", methods=["GET", "POST", "PUT"])
def api_team_shared_workspace(team_id):
    role, actor_id, actor_name = _get_session_actor()
    is_write = request.method in ("POST", "PUT")

    allowed, reason = can_user_access_team_workspace(
        team_id=team_id,
        role=role,
        student_id=session.get("student_id"),
        pi_id=session.get("pi_id"),
        write_access=is_write,
    )
    if not allowed:
        return jsonify({"success": False, "error": reason}), 403

    if request.method == "GET":
        ws = get_team_workspace(team_id)
        if not ws:
            return jsonify({"success": False, "error": f"Workspace for team '{team_id}' not found."}), 404
        if role == "student" and "proposal_draft" in ws:
            ws = json.loads(json.dumps(ws))
            ws["proposal_draft"] = sanitize_draft_for_student(ws["proposal_draft"])
        return jsonify({"success": True, "workspace": ws})

    data = request.get_json() or {}
    # Strictly forbid students from injecting administrative changes through workspace endpoint
    if role == "student":
        for forbidden_field in ("lab_group", "pi_id", "pi_name", "topic_title", "student_ids"):
            if forbidden_field in data:
                return jsonify({
                    "success": False,
                    "error": f"Forbidden: Students cannot modify official assignment field '{forbidden_field}'."
                }), 403

    res = update_team_workspace(
        team_id=team_id,
        payload=data,
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role=role,
    )
    if not res.get("success"):
        return jsonify(res), 400
    if role == "student" and res.get("workspace") and "proposal_draft" in res["workspace"]:
        ws_copy = json.loads(json.dumps(res["workspace"]))
        ws_copy["proposal_draft"] = sanitize_draft_for_student(ws_copy["proposal_draft"])
        res["workspace"] = ws_copy
    return jsonify(res)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    print(f"===============================================================")
    print(f"[*] BioWriter Studio (Full Suite) running on:")
    print(f"    http://{host}:{port}")
    print(f"===============================================================")
    app.run(host=host, port=port, debug=False if os.environ.get("PORT") else True)
