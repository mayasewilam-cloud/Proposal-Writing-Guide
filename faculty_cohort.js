/**
 * BioWriter Faculty Studio — Cohort, Attendance, Lab Groups, Project Teams, PIs, Topics & Shared Workspaces Controller.
 * Extends the existing Faculty Portal without duplicating authentication, database, or evaluation views.
 */

(function () {
  const state = {
    semester: "Fall 2026",
    course_id: "BT_301",
    semesters: ["Fall 2026", "Spring 2026", "Spring 2027"],
    courses: [
      { id: "BT_301", name: "BT_301: Introduction to Biotechnology" },
      { id: "GRAD_501", name: "GRAD_501: Senior Graduation Project" },
      { id: "GRANT_STDF", name: "GRANT_STDF: National Grant Standard" }
    ],
    activeSubTab: "attendance", // attendance | students | labgroups | teams | pitopics | workspaces | history
    overview: null,
    students: [],
    labGroups: [],
    teams: [],
    pis: [],
    auditHistory: [],
    selectedLabGroup: "",
    selectedWorkspaceTeamId: "",
    activeWorkspace: null,
    lastAttendancePreview: null,
    filters: {
      q: "",
      lab_group: "",
      team_id: "",
      pi_id: "",
      assignment_status: ""
    }
  };

  function esc(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function notify(msg, type = "info") {
    if (typeof window.showToast === "function") {
      window.showToast(msg, type);
    }
  }

  // ============================================================================
  // DUAL-MODE API + CLIENT-SIDE LOCALSTORAGE COHORT ENGINE (ZERO CORS ERRORS)
  // ============================================================================
  const COHORT_DB_KEY = "biowriter_cohort_db_v1";

  function isStaticEnv() {
    if (typeof window.isStaticEnvironment === "function") {
      return window.isStaticEnvironment();
    }
    return (
      window.location.protocol === "file:" ||
      window.location.hostname.endsWith("github.io") ||
      window.location.hostname.endsWith("pages.dev") ||
      window.location.hostname.includes("github") ||
      (window.location.hostname === "localhost" && !window.location.port)
    );
  }

  function nowStamp() {
    const d = new Date();
    const pad = n => String(n).padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`;
  }

  function normalizeLabGroupCode(raw) {
    const val = String(raw || "").trim();
    if (!val) return "";
    const m = val.match(/^(?:lab\s*group\s*|group\s*|lab\s*|lg\s*|l\s*)(\d+[a-zA-Z]?)$/i);
    if (m) return "L" + m[1].toUpperCase();
    return val.toUpperCase();
  }

  function labGroupDisplayName(code) {
    const c = normalizeLabGroupCode(code);
    if (!c) return "Unassigned";
    const m = c.match(/^L(\d+[A-Z]?)$/);
    if (m) return `Lab Group ${m[1]}`;
    return c;
  }

  function getDefaultLocalCohortDb() {
    const ts = nowStamp();
    return {
      active_semester: "Fall 2026",
      active_course_id: "BT_301",
      semesters: ["Fall 2026", "Spring 2026", "Spring 2027"],
      courses: [
        { id: "BT_301", name: "BT_301: Introduction to Biotechnology" },
        { id: "GRAD_501", name: "GRAD_501: Senior Graduation Project" },
        { id: "GRANT_STDF", name: "GRANT_STDF: National Grant Standard" }
      ],
      pis: {
        "PI-RANIA": { pi_id: "PI-RANIA", name: "Dr. Rania Hassan", email: "r.hassan@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-AHMED": { pi_id: "PI-AHMED", name: "Dr. Ahmed Hassan", email: "a.hassan@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-TARIK": { pi_id: "PI-TARIK", name: "Dr. Tarek El-Sayed", email: "t.elsayed@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-TAREK": { pi_id: "PI-TAREK", name: "Dr. Tarek Mansour", email: "t.mansour@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-MONA": { pi_id: "PI-MONA", name: "Dr. Mona Abdelrahman", email: "m.abdelrahman@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-NADIA": { pi_id: "PI-NADIA", name: "Dr. Nadia El-Sayed", email: "n.elsayed@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-KARIM": { pi_id: "PI-KARIM", name: "Dr. Karim Fawzy", email: "k.fawzy@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" }
      },
      lab_groups: {
        L1: { lab_group_id: "L1", name: "Lab Group 1", semester: "Fall 2026", course_id: "BT_301", created_at: ts },
        L2: { lab_group_id: "L2", name: "Lab Group 2", semester: "Fall 2026", course_id: "BT_301", created_at: ts },
        L3: { lab_group_id: "L3", name: "Lab Group 3", semester: "Fall 2026", course_id: "BT_301", created_at: ts }
      },
      students: {
        "13989": { student_id: "13989", student_name: "Maya Abdelrazek", email: "m.abdelrazek@nu.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230001": { student_id: "20230001", student_name: "Ahmed Ali", email: "ahmed.ali@student.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230002": { student_id: "20230002", student_name: "Sara Mohamed", email: "sara.mohamed@student.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230003": { student_id: "20230003", student_name: "Mariam Hassan", email: "mariam.hassan@student.edu.eg", lab_group: "L1", team_id: "L1-T2", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230004": { student_id: "20230004", student_name: "Karim Adel", email: "karim.adel@student.edu.eg", lab_group: "L1", team_id: "L1-T2", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230005": { student_id: "20230005", student_name: "Omar Khaled", email: "omar.khaled@student.edu.eg", lab_group: "L1", team_id: "", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230006": { student_id: "20230006", student_name: "Nour Hany", email: "nour.hany@student.edu.eg", lab_group: "L1", team_id: "", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts },
        "20230007": { student_id: "20230007", student_name: "Youssef Tarek", email: "youssef.tarek@student.edu.eg", lab_group: "L2", team_id: "L2-T1", semester: "Fall 2026", course_id: "BT_301", status: "Active", created_at: ts, updated_at: ts }
      },
      teams: {
        "L1-T1": {
          team_id: "L1-T1",
          team_name: "Team 1 — DETECTR-Aqua",
          lab_group: "L1",
          semester: "Fall 2026",
          course_id: "BT_301",
          pi_id: "PI-RANIA",
          topic_title: "DETECTR-Aqua: A CRISPR-Cas12a-Assisted Isothermal Assay for Detecting the Colistin-Resistance Gene mcr-1 in Hospital Wastewater",
          topic_description: "Matrix-aware RPA-Cas12a fluorescence diagnostic assay for rapid surveillance of plasmid-borne colistin resistance in hospital effluent.",
          member_ids: ["13989", "20230001", "20230002"],
          status: "active",
          created_at: ts,
          updated_at: ts
        },
        "L1-T2": {
          team_id: "L1-T2",
          team_name: "Team 2 — PhytoNano",
          lab_group: "L1",
          semester: "Fall 2026",
          course_id: "BT_301",
          pi_id: "PI-AHMED",
          topic_title: "Plant-Derived Compounds and Anti-Inflammatory Nanocarriers",
          topic_description: "Targeted liposomal delivery of standardized plant secondary metabolites for NF-kB modulation.",
          member_ids: ["20230003", "20230004"],
          status: "active",
          created_at: ts,
          updated_at: ts
        },
        "L2-T1": {
          team_id: "L2-T1",
          team_name: "Team 1 — BioCatalyst",
          lab_group: "L2",
          semester: "Fall 2026",
          course_id: "BT_301",
          pi_id: "PI-TARIK",
          topic_title: "Thermostable PETase Variants for Industrial Polyester Depolymerization",
          topic_description: "Directed evolution of Ideonella sakaiensis PETase for bioreactor-scale plastic recycling.",
          member_ids: ["20230007"],
          status: "active",
          created_at: ts,
          updated_at: ts
        }
      },
      team_workspaces: {
        "L1-T1": {
          team_id: "L1-T1",
          shared_notes: "Aim 1 crRNA sequences verified against 42 mcr-1 alleles. Next milestone: matrix spiking in autoclaved vs raw hospital effluent.",
          important_info: "Weekly lab bench slot: Mondays 10:00–13:00 (BSL-2 Cabinet B).",
          pi_feedback_notes: "Dr. Rania Hassan: Ensure internal amplification control (IAC) concentration is fixed at 50 copies/reaction across all dilutions.",
          proposal_draft: {
            team_id: "L1-T1",
            team_name: "Team 1 — DETECTR-Aqua",
            lab_group: "L1",
            title: "DETECTR-Aqua: A CRISPR-Cas12a-Assisted Isothermal Assay for Detecting the Colistin-Resistance Gene mcr-1 in Hospital Wastewater"
          },
          updates_feed: [{
            timestamp: ts,
            author_id: "PI-RANIA",
            author_name: "Dr. Rania Hassan",
            author_role: "pi",
            action: "pi_guidance",
            message: "Initialized DETECTR-Aqua shared team workspace and IAC validation guidelines."
          }],
          last_updated_at: ts,
          last_updated_by: "Dr. Rania Hassan"
        }
      },
      attendance_previews: {},
      audit_history: []
    };
  }

  function loadLocalCohortDb() {
    try {
      const raw = localStorage.getItem(COHORT_DB_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          const def = getDefaultLocalCohortDb();
          for (const k of Object.keys(def)) {
            if (parsed[k] === undefined) parsed[k] = def[k];
          }
          if (!parsed.students || Object.keys(parsed.students).length === 0) {
            parsed.students = def.students;
            parsed.teams = def.teams;
            parsed.pis = { ...def.pis, ...(parsed.pis || {}) };
            parsed.team_workspaces = { ...def.team_workspaces, ...(parsed.team_workspaces || {}) };
            saveLocalCohortDb(parsed);
          }
          return parsed;
        }
      }
    } catch (e) {}
    const fresh = getDefaultLocalCohortDb();
    saveLocalCohortDb(fresh);
    return fresh;
  }

  function saveLocalCohortDb(db) {
    try {
      localStorage.setItem(COHORT_DB_KEY, JSON.stringify(db));
    } catch (e) {}
  }

  function recordLocalAudit(db, eventType, summary, actor = "Faculty Coordinator", studentId = "", teamId = "", oldVal = "", newVal = "") {
    const entry = {
      event_id: "EVT-" + Math.random().toString(36).slice(2, 10).toUpperCase(),
      timestamp: nowStamp(),
      event_type: eventType,
      summary: summary,
      actor: actor,
      student_id: studentId,
      team_id: teamId,
      old_value: oldVal,
      new_value: newVal
    };
    db.audit_history = db.audit_history || [];
    db.audit_history.unshift(entry);
    if (db.audit_history.length > 500) db.audit_history.length = 500;
    return entry;
  }

  function preEnrollStudentAccountInLocalStorage(sid, sname, email, lg, semester, courseId) {
    const cleanId = String(sid || "").trim().toUpperCase();
    if (!cleanId) return;
    try {
      const accRaw = localStorage.getItem("bt301_student_accounts_db");
      const accDb = accRaw ? JSON.parse(accRaw) : {};
      if (!accDb[cleanId]) {
        accDb[cleanId] = {
          student_id: cleanId,
          student_name: sname,
          password: "",
          role: "student",
          pre_enrolled_by_faculty: true,
          account_claimed: false,
          lab_group: lg,
          semester: semester,
          course_id: courseId
        };
      } else {
        accDb[cleanId].student_name = sname || accDb[cleanId].student_name;
        accDb[cleanId].lab_group = lg || accDb[cleanId].lab_group;
      }
      localStorage.setItem("bt301_student_accounts_db", JSON.stringify(accDb));
    } catch (e) {}

    try {
      const dKey = "bt301_student_draft_" + cleanId;
      const dRaw = localStorage.getItem(dKey);
      const draft = dRaw ? JSON.parse(dRaw) : {
        student_id: cleanId,
        student_name: sname,
        email: email || "",
        course_id: courseId || "BT_301",
        semester: semester || "Fall 2026",
        title: ""
      };
      draft.student_name = sname || draft.student_name;
      draft.lab_group = lg;
      draft.semester = semester || draft.semester || "Fall 2026";
      draft.course_id = courseId || draft.course_id || "BT_301";
      localStorage.setItem(dKey, JSON.stringify(draft));
    } catch (e) {}
  }

  function syncTeamToMemberLocalDrafts(db, teamId) {
    const t = db.teams[teamId];
    if (!t) return;
    const piObj = db.pis[t.pi_id] || {};
    const membersList = (t.member_ids || []).map((sid, idx) => {
      const st = db.students[sid] || {};
      return {
        name: st.student_name || sid,
        id: sid,
        email: st.email || "",
        role: idx === 0 ? "Principal Investigator" : "Co-Investigator"
      };
    });
    const ws = db.team_workspaces[teamId] || {};

    for (const sid of (t.member_ids || [])) {
      try {
        const dKey = "bt301_student_draft_" + sid;
        const dRaw = localStorage.getItem(dKey);
        const draft = dRaw ? JSON.parse(dRaw) : { student_id: sid, student_name: (db.students[sid] || {}).student_name || sid };
        draft.team_id = teamId;
        draft.team_name = t.team_name || teamId;
        draft.lab_group = t.lab_group || draft.lab_group || "";
        draft.pi_id = t.pi_id || "";
        draft.pi_name = piObj.name || "Unassigned";
        draft.topic_title = t.topic_title || "";
        draft.topic_description = t.topic_description || "";
        draft.team_members = membersList;
        draft.team_roster = membersList;
        if (t.topic_title && !draft.title) {
          draft.title = t.topic_title;
        }
        if (ws.proposal_draft && typeof ws.proposal_draft === "object") {
          for (const [k, v] of Object.entries(ws.proposal_draft)) {
            if (!["student_id", "student_name"].includes(k) && v !== undefined && v !== "") {
              draft[k] = v;
            }
          }
        }
        localStorage.setItem(dKey, JSON.stringify(draft));
      } catch (e) {}
    }
  }

  function enrichStudentObj(db, st) {
    const teamId = st.team_id || "";
    const team = (teamId && db.teams[teamId] && db.teams[teamId].status !== "archived") ? db.teams[teamId] : null;
    const piId = team ? (team.pi_id || "") : "";
    const piObj = piId ? (db.pis[piId] || null) : null;
    return {
      student_id: st.student_id,
      student_name: st.student_name || "Unnamed Student",
      email: st.email || "",
      semester: st.semester || db.active_semester || "Fall 2026",
      course_id: st.course_id || db.active_course_id || "BT_301",
      lab_group: st.lab_group || "",
      lab_group_name: labGroupDisplayName(st.lab_group || ""),
      team_id: team ? teamId : "",
      team_name: team ? (team.team_name || teamId) : "Unassigned",
      pi_id: piId,
      pi_name: piObj ? piObj.name : "Unassigned",
      topic_title: team && team.topic_title ? team.topic_title : "Unassigned",
      topic_description: team && team.topic_description ? team.topic_description : "",
      status: st.status || "Active",
      updated_at: st.updated_at || ""
    };
  }

  function enrichTeamObj(db, t) {
    const piId = t.pi_id || "";
    const piObj = piId ? (db.pis[piId] || null) : null;
    const members = [];
    for (const sid of (t.member_ids || [])) {
      const s = db.students[sid];
      if (s && s.team_id === t.team_id) {
        members.push({
          student_id: sid,
          student_name: s.student_name || sid,
          email: s.email || "",
          lab_group: s.lab_group || ""
        });
      }
    }
    const ws = db.team_workspaces[t.team_id] || {};
    return {
      team_id: t.team_id,
      team_name: t.team_name || t.team_id,
      lab_group: t.lab_group || "",
      lab_group_name: labGroupDisplayName(t.lab_group || ""),
      semester: t.semester || "Fall 2026",
      course_id: t.course_id || "BT_301",
      pi_id: piId,
      pi_name: piObj ? piObj.name : "Unassigned",
      pi_email: piObj ? (piObj.email || "") : "",
      pi_department: piObj ? (piObj.department || "") : "",
      topic_title: t.topic_title || "",
      topic_description: t.topic_description || "",
      member_ids: members.map(m => m.student_id),
      members: members,
      member_count: members.length,
      workspace_updated_at: ws.last_updated_at || t.updated_at || "",
      workspace_updated_by: ws.last_updated_by || "System"
    };
  }

  function listLocalStudents(db, filters = {}) {
    const sem = filters.semester || db.active_semester || "Fall 2026";
    const cid = filters.course_id || db.active_course_id || "BT_301";
    const q = String(filters.q || "").trim().toLowerCase();
    const lgFilter = normalizeLabGroupCode(filters.lab_group || "");
    const tmFilter = String(filters.team_id || "").trim();
    const piFilter = String(filters.pi_id || "").trim();
    const stFilter = String(filters.assignment_status || "").trim().toLowerCase();

    const out = [];
    for (const st of Object.values(db.students || {})) {
      if (sem && st.semester && st.semester !== sem) continue;
      if (cid && st.course_id && st.course_id !== cid) continue;
      const item = enrichStudentObj(db, st);
      if (lgFilter) {
        if (lgFilter === "UNASSIGNED" && item.lab_group) continue;
        if (lgFilter !== "UNASSIGNED" && item.lab_group !== lgFilter) continue;
      }
      if (tmFilter) {
        if (tmFilter.toUpperCase() === "UNASSIGNED" && item.team_id) continue;
        if (tmFilter.toUpperCase() !== "UNASSIGNED" && item.team_id !== tmFilter) continue;
      }
      if (piFilter) {
        if (piFilter.toUpperCase() === "UNASSIGNED" && item.pi_id) continue;
        if (piFilter.toUpperCase() !== "UNASSIGNED" && item.pi_id !== piFilter) continue;
      }
      if (stFilter === "unassigned_team" && item.team_id) continue;
      if (stFilter === "assigned_team" && !item.team_id) continue;
      if (stFilter === "unassigned_lab" && item.lab_group) continue;
      if (q) {
        const hay = `${item.student_id} ${item.student_name} ${item.lab_group} ${item.team_name} ${item.pi_name} ${item.topic_title}`.toLowerCase();
        if (!hay.includes(q)) continue;
      }
      out.push(item);
    }
    out.sort((a, b) => (a.lab_group || "ZZZ").localeCompare(b.lab_group || "ZZZ") || a.student_id.localeCompare(b.student_id));
    return out;
  }

  function listLocalTeams(db, sem, cid) {
    const out = [];
    for (const t of Object.values(db.teams || {})) {
      if (t.status === "archived") continue;
      if (sem && t.semester && t.semester !== sem) continue;
      if (cid && t.course_id && t.course_id !== cid) continue;
      out.push(enrichTeamObj(db, t));
    }
    out.sort((a, b) => (a.lab_group || "").localeCompare(b.lab_group || "") || a.team_id.localeCompare(b.team_id));
    return out;
  }

  function listLocalLabGroups(db, sem, cid) {
    const allStudents = listLocalStudents(db, { semester: sem, course_id: cid });
    const allTeams = listLocalTeams(db, sem, cid);
    const codes = new Set(Object.keys(db.lab_groups || {}));
    allStudents.forEach(s => { if (s.lab_group) codes.add(s.lab_group); });
    allTeams.forEach(t => { if (t.lab_group) codes.add(t.lab_group); });

    const sortedCodes = Array.from(codes).sort((a, b) => {
      const na = parseInt(a.replace(/\D/g, ""), 10) || 999;
      const nb = parseInt(b.replace(/\D/g, ""), 10) || 999;
      return na - nb || a.localeCompare(b);
    });

    return sortedCodes.map(code => {
      const meta = (db.lab_groups || {})[code] || { lab_group_id: code, name: labGroupDisplayName(code) };
      const lgStudents = allStudents.filter(s => s.lab_group === code);
      const lgTeams = allTeams.filter(t => t.lab_group === code);
      const unassigned = lgStudents.filter(s => !s.team_id);
      return {
        lab_group_id: code,
        name: meta.name || labGroupDisplayName(code),
        semester: sem,
        course_id: cid,
        student_count: lgStudents.length,
        team_count: lgTeams.length,
        unassigned_count: unassigned.length,
        students: lgStudents,
        unassigned_students: unassigned,
        teams: lgTeams,
        summary_label: `${code}: ${lgStudents.length} students | ${lgTeams.length} teams | ${unassigned.length} unassigned`
      };
    });
  }

  function buildLocalCohortOverview(db, sem, cid) {
    const students = listLocalStudents(db, { semester: sem, course_id: cid });
    const labGroups = listLocalLabGroups(db, sem, cid);
    const teams = listLocalTeams(db, sem, cid);
    return {
      overview: {
        semester: sem,
        course_id: cid,
        total_students: students.length,
        total_lab_groups: labGroups.length,
        total_teams: teams.length,
        unassigned_lab_group_count: students.filter(s => !s.lab_group).length,
        unassigned_team_count: students.filter(s => !s.team_id).length,
        teams_without_pi_count: teams.filter(t => !t.pi_id).length,
        teams_without_topic_count: teams.filter(t => !t.topic_title).length
      },
      semesters: db.semesters || ["Fall 2026", "Spring 2026", "Spring 2027"],
      courses: db.courses || [],
      pis: Object.values(db.pis || {}),
      lab_groups: labGroups,
      teams: teams,
      audit_history: (db.audit_history || []).slice(0, 60)
    };
  }

  // Client-side CSV + XLSX parser for Attendance Upload in file:// mode
  function parseCsvRowsClient(text) {
    const lines = String(text || "").replace(/^\uFEFF/, "").split(/\r?\n/).filter(l => l.trim().length > 0);
    if (!lines.length) return [];
    const first = lines[0];
    const delim = first.includes("\t") ? "\t" : (first.includes(";") && !first.includes(",") ? ";" : ",");
    return lines.map(line => {
      const cells = [];
      let cur = "";
      let inQ = false;
      for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === '"') {
          if (inQ && line[i + 1] === '"') { cur += '"'; i++; }
          else inQ = !inQ;
        } else if (ch === delim && !inQ) {
          cells.push(cur.trim());
          cur = "";
        } else {
          cur += ch;
        }
      }
      cells.push(cur.trim());
      return cells;
    });
  }

  async function parseXlsxBufferClient(arrayBuffer) {
    const bytes = new Uint8Array(arrayBuffer);
    const view = new DataView(arrayBuffer);
    const files = {};
    let offset = 0;
    while (offset + 30 <= bytes.length) {
      const sig = view.getUint32(offset, true);
      if (sig !== 0x04034b50) break;
      const method = view.getUint16(offset + 8, true);
      const compSize = view.getUint32(offset + 18, true);
      const nameLen = view.getUint16(offset + 26, true);
      const extraLen = view.getUint16(offset + 28, true);
      const name = new TextDecoder().decode(bytes.subarray(offset + 30, offset + 30 + nameLen));
      const dataStart = offset + 30 + nameLen + extraLen;
      const compData = bytes.subarray(dataStart, dataStart + compSize);
      offset = dataStart + compSize;

      if (name === "xl/sharedStrings.xml" || (name.startsWith("xl/worksheets/sheet") && name.endsWith(".xml"))) {
        if (method === 0) {
          files[name] = new TextDecoder().decode(compData);
        } else if (method === 8 && typeof DecompressionStream !== "undefined") {
          const ds = new DecompressionStream("deflate-raw");
          const writer = ds.writable.getWriter();
          writer.write(compData);
          writer.close();
          const outBuf = await new Response(ds.readable).arrayBuffer();
          files[name] = new TextDecoder().decode(outBuf);
        }
      }
    }

    const sharedStrings = [];
    if (files["xl/sharedStrings.xml"]) {
      const doc = new DOMParser().parseFromString(files["xl/sharedStrings.xml"], "application/xml");
      doc.querySelectorAll("si").forEach(si => {
        const ts = Array.from(si.querySelectorAll("t")).map(t => t.textContent || "");
        sharedStrings.push(ts.join(""));
      });
    }

    const sheetKey = Object.keys(files).find(k => k.startsWith("xl/worksheets/sheet"));
    if (!sheetKey) return [];
    const sheetDoc = new DOMParser().parseFromString(files[sheetKey], "application/xml");
    const colIdxFromRef = ref => {
      const letters = (ref.match(/^[A-Z]+/i) || ["A"])[0].toUpperCase();
      let idx = 0;
      for (let i = 0; i < letters.length; i++) idx = idx * 26 + (letters.charCodeAt(i) - 64);
      return Math.max(0, idx - 1);
    };

    const rows = [];
    sheetDoc.querySelectorAll("row").forEach(rEl => {
      const rowCells = [];
      rEl.querySelectorAll("c").forEach(cEl => {
        const ref = cEl.getAttribute("r") || "A1";
        const idx = colIdxFromRef(ref);
        const cType = cEl.getAttribute("t") || "";
        const vEl = cEl.querySelector("v");
        const isEl = cEl.querySelector("is");
        let val = "";
        if (cType === "s" && vEl) {
          const sIdx = parseInt(vEl.textContent || "0", 10);
          val = sharedStrings[sIdx] !== undefined ? sharedStrings[sIdx] : "";
        } else if (cType === "inlineStr" && isEl) {
          val = Array.from(isEl.querySelectorAll("t")).map(t => t.textContent || "").join("");
        } else if (vEl && vEl.textContent) {
          val = vEl.textContent.trim();
        }
        while (rowCells.length <= idx) rowCells.push("");
        rowCells[idx] = String(val).trim();
      });
      if (rowCells.some(c => c !== "")) rows.push(rowCells);
    });
    return rows;
  }

  function generateLocalAttendancePreview(db, rawRows, semester, courseId, filename) {
    if (!rawRows || !rawRows.length) {
      return { success: false, error: "No rows detected in uploaded attendance sheet." };
    }
    const header = rawRows[0].map(c => String(c || "").trim().toLowerCase().replace(/[\-_\s]+/g, " "));
    let idIdx = null, nameIdx = null, lgIdx = null, emailIdx = null;
    header.forEach((h, i) => {
      if (idIdx === null && ["id", "student id", "studentid", "university id", "uni id", "code", "matric", "seat"].some(k => h.includes(k))) idIdx = i;
      if (nameIdx === null && ["name", "student name", "full name", "student"].some(k => h.includes(k)) && !h.includes("id")) nameIdx = i;
      if (lgIdx === null && ["lab", "group", "section", "bench", "cohort"].some(k => h.includes(k))) lgIdx = i;
      if (emailIdx === null && ["email", "mail"].some(k => h.includes(k))) emailIdx = i;
    });
    let startRow = 1;
    if (idIdx === null && nameIdx === null && lgIdx === null) {
      startRow = 0; idIdx = 0; nameIdx = 1; lgIdx = 2; emailIdx = 3;
    } else {
      if (idIdx === null) idIdx = 0;
      if (nameIdx === null) nameIdx = idIdx !== 1 ? 1 : 0;
      if (lgIdx === null) lgIdx = !([idIdx, nameIdx].includes(2)) ? 2 : 0;
    }

    const previewRows = [];
    const seenIds = {};
    const seenRowSigs = {};
    const detectedLabGroups = new Set();
    let newCount = 0, existingCount = 0, dupIdCount = 0, dupRowCount = 0, missIdCount = 0, missNameCount = 0, missLgCount = 0;

    for (let rIdx = startRow; rIdx < rawRows.length; rIdx++) {
      const row = rawRows[rIdx];
      if (!row || !row.some(c => String(c || "").trim() !== "")) continue;
      let rawSid = idIdx < row.length ? String(row[idIdx] || "").trim() : "";
      if (rawSid.endsWith(".0") && /^\d+$/.test(rawSid.slice(0, -2))) rawSid = rawSid.slice(0, -2);
      const sid = rawSid.toUpperCase();
      const sname = nameIdx < row.length ? String(row[nameIdx] || "").trim() : "";
      const rawLg = lgIdx < row.length ? String(row[lgIdx] || "").trim() : "";
      const lgCode = normalizeLabGroupCode(rawLg);
      const email = (emailIdx !== null && emailIdx < row.length) ? String(row[emailIdx] || "").trim() : "";

      const issues = [];
      let statusLabel = "New";
      const rowSig = `${sid}|${sname.toLowerCase()}|${lgCode}`;

      if (!sid) { issues.push("Missing Student ID"); missIdCount++; }
      if (!sname) { issues.push("Missing Student Name"); missNameCount++; }
      if (!lgCode) { issues.push("Missing Lab Group"); missLgCount++; }
      else detectedLabGroups.add(lgCode);

      if (seenRowSigs[rowSig]) {
        issues.push(`Duplicate Row (same as row ${seenRowSigs[rowSig]})`);
        dupRowCount++;
      } else {
        seenRowSigs[rowSig] = rIdx + 1;
      }

      if (sid) {
        if (seenIds[sid]) {
          issues.push(`Duplicate Student ID in sheet (first seen row ${seenIds[sid]})`);
          dupIdCount++;
        } else {
          seenIds[sid] = rIdx + 1;
        }
      }

      if (sid && db.students[sid]) {
        statusLabel = "Existing";
        existingCount++;
      } else if (sid && issues.length === 0) {
        statusLabel = "New";
        newCount++;
      }

      if (issues.length > 0) statusLabel = `Issue: ${issues.join(", ")}`;

      previewRows.push({
        row_number: rIdx + 1,
        student_id: sid,
        student_name: sname,
        lab_group: lgCode,
        lab_group_raw: rawLg,
        email: email,
        status: statusLabel,
        issues: issues,
        is_valid: Boolean(sid && sname && lgCode && !issues.some(x => x.includes("Duplicate")))
      });
    }

    const previewId = "PREV-" + Math.random().toString(36).slice(2, 10).toUpperCase();
    const previewObj = {
      success: true,
      preview_id: previewId,
      filename: filename || "attendance.csv",
      semester: semester,
      course_id: courseId,
      created_at: nowStamp(),
      students_detected: previewRows.filter(r => r.is_valid).length,
      total_rows_parsed: previewRows.length,
      lab_groups_detected: detectedLabGroups.size,
      lab_groups_list: Array.from(detectedLabGroups).sort(),
      summary: {
        new_count: newCount,
        existing_count: existingCount,
        duplicate_id_count: dupIdCount,
        duplicate_row_count: dupRowCount,
        missing_id_count: missIdCount,
        missing_name_count: missNameCount,
        missing_lab_group_count: missLgCount
      },
      rows: previewRows
    };
    db.attendance_previews[previewId] = previewObj;
    saveLocalCohortDb(db);
    return previewObj;
  }

  async function handleLocalCohortApi(url, options = {}) {
    const db = loadLocalCohortDb();
    const method = (options.method || "GET").toUpperCase();
    const u = new URL(url, "http://localhost");
    const path = u.pathname;
    const params = Object.fromEntries(u.searchParams.entries());

    let body = {};
    if (options.body && typeof options.body === "string") {
      try { body = JSON.parse(options.body); } catch (e) {}
    }

    // 1. Context switch
    if (path === "/api/faculty/cohort/context" && method === "POST") {
      db.active_semester = body.semester || db.active_semester || "Fall 2026";
      db.active_course_id = body.course_id || db.active_course_id || "BT_301";
      saveLocalCohortDb(db);
      return { success: true, active_semester: db.active_semester, active_course_id: db.active_course_id };
    }

    // 2. Cohort Overview
    if (path === "/api/faculty/cohort/overview" && method === "GET") {
      const sem = params.semester || db.active_semester || "Fall 2026";
      const cid = params.course_id || db.active_course_id || "BT_301";
      return { success: true, ...buildLocalCohortOverview(db, sem, cid) };
    }

    // 3. Attendance Preview
    if (path === "/api/faculty/attendance/preview" && method === "POST") {
      if (options.body instanceof FormData) {
        const file = options.body.get("file");
        const sem = options.body.get("semester") || state.semester || "Fall 2026";
        const cid = options.body.get("course_id") || state.course_id || "BT_301";
        if (!file) return { success: false, error: "No file selected." };
        const fname = file.name || "attendance.csv";
        let rows = [];
        if (fname.toLowerCase().endsWith(".xlsx")) {
          const buf = await file.arrayBuffer();
          rows = await parseXlsxBufferClient(buf);
        } else {
          const txt = await file.text();
          rows = parseCsvRowsClient(txt);
        }
        return generateLocalAttendancePreview(db, rows, sem, cid, fname);
      } else {
        const rows = parseCsvRowsClient(body.csv_text || "");
        return generateLocalAttendancePreview(db, rows, body.semester || state.semester, body.course_id || state.course_id, body.filename || "pasted_attendance.csv");
      }
    }

    // 4. Confirm Attendance Import
    if (path === "/api/faculty/attendance/confirm" && method === "POST") {
      const prev = db.attendance_previews[body.preview_id];
      if (!prev) return { success: false, error: "Attendance preview not found or already confirmed." };
      const sem = prev.semester || "Fall 2026";
      const cid = prev.course_id || "BT_301";
      const ts = nowStamp();
      let imported = 0, updated = 0;
      const lgSet = new Set();

      for (const r of (prev.rows || [])) {
        if (!r.is_valid) continue;
        const sid = r.student_id;
        const sname = r.student_name;
        const lg = r.lab_group;
        const email = r.email || "";
        lgSet.add(lg);
        if (!db.lab_groups[lg]) {
          db.lab_groups[lg] = { lab_group_id: lg, name: labGroupDisplayName(lg), semester: sem, course_id: cid, created_at: ts };
        }
        if (db.students[sid]) {
          const cur = db.students[sid];
          const oldLg = cur.lab_group || "Unassigned";
          cur.student_name = sname || cur.student_name;
          if (email) cur.email = email;
          cur.lab_group = lg;
          cur.semester = sem;
          cur.course_id = cid;
          cur.updated_at = ts;
          updated++;
          if (oldLg !== lg) {
            recordLocalAudit(db, "lab_group_change", `Attendance import updated ${sname} (${sid}) lab group: ${oldLg} ➔ ${lg}`, "Faculty Coordinator", sid, cur.team_id || "", oldLg, lg);
          }
        } else {
          db.students[sid] = {
            student_id: sid,
            student_name: sname,
            email: email,
            semester: sem,
            course_id: cid,
            lab_group: lg,
            team_id: "",
            status: "Active",
            created_at: ts,
            updated_at: ts
          };
          imported++;
        }
        preEnrollStudentAccountInLocalStorage(sid, sname, email, lg, sem, cid);
      }
      recordLocalAudit(db, "attendance_import", `Confirmed attendance import (${prev.filename}): ${imported} new, ${updated} existing across ${lgSet.size} lab groups.`, "Faculty Coordinator", "", "", "", `${imported + updated} students`);
      delete db.attendance_previews[body.preview_id];
      saveLocalCohortDb(db);
      return { success: true, imported_count: imported + updated, new_students_count: imported, updated_students_count: updated, lab_groups_count: lgSet.size };
    }

    // 5. Students GET & POST
    if (path === "/api/faculty/students" && method === "GET") {
      return { success: true, students: listLocalStudents(db, params) };
    }
    if (path === "/api/faculty/students" && method === "POST") {
      const sid = String(body.student_id || "").trim().toUpperCase();
      const sname = String(body.student_name || "").trim();
      const lg = normalizeLabGroupCode(body.lab_group || "L1");
      const sem = body.semester || state.semester || "Fall 2026";
      const cid = body.course_id || state.course_id || "BT_301";
      if (!sid || !sname) return { success: false, error: "Student ID and Student Name are required." };
      const ts = nowStamp();
      if (lg && !db.lab_groups[lg]) {
        db.lab_groups[lg] = { lab_group_id: lg, name: labGroupDisplayName(lg), semester: sem, course_id: cid, created_at: ts };
      }
      db.students[sid] = {
        ...(db.students[sid] || { team_id: "", status: "Active", created_at: ts }),
        student_id: sid,
        student_name: sname,
        email: body.email || "",
        lab_group: lg,
        semester: sem,
        course_id: cid,
        updated_at: ts
      };
      preEnrollStudentAccountInLocalStorage(sid, sname, body.email || "", lg, sem, cid);
      recordLocalAudit(db, "student_upserted", `Added/updated student ${sname} (${sid}) in ${lg}`, "Faculty Coordinator", sid, "", "", lg);
      saveLocalCohortDb(db);
      return { success: true, student: enrichStudentObj(db, db.students[sid]) };
    }

    // 6. Move Student Lab Group
    if (path === "/api/faculty/students/move_lab_group" && method === "POST") {
      const sid = String(body.student_id || "").trim().toUpperCase();
      const targetLg = normalizeLabGroupCode(body.new_lab_group || "");
      const st = db.students[sid];
      if (!st) return { success: false, error: `Student ${sid} not found.` };
      if (!targetLg) return { success: false, error: "Target lab group is required." };
      const oldLg = st.lab_group || "Unassigned";
      const ts = nowStamp();
      if (!db.lab_groups[targetLg]) {
        db.lab_groups[targetLg] = { lab_group_id: targetLg, name: labGroupDisplayName(targetLg), semester: st.semester || "Fall 2026", course_id: st.course_id || "BT_301", created_at: ts };
      }
      st.lab_group = targetLg;
      st.updated_at = ts;
      preEnrollStudentAccountInLocalStorage(sid, st.student_name, st.email, targetLg, st.semester, st.course_id);
      const entry = recordLocalAudit(db, "lab_group_change", `Moved ${st.student_name} (${sid}) from ${oldLg} to ${targetLg}`, "Faculty Coordinator", sid, st.team_id || "", oldLg, targetLg);
      saveLocalCohortDb(db);
      return { success: true, student: enrichStudentObj(db, st), audit_entry: entry };
    }

    // 7. Create Lab Group
    if (path === "/api/faculty/lab_groups" && method === "POST") {
      const code = normalizeLabGroupCode(body.lab_group_id || "");
      if (!code) return { success: false, error: "Lab Group code is required." };
      db.lab_groups[code] = {
        lab_group_id: code,
        name: body.name || labGroupDisplayName(code),
        semester: body.semester || state.semester || "Fall 2026",
        course_id: body.course_id || state.course_id || "BT_301",
        created_at: nowStamp()
      };
      saveLocalCohortDb(db);
      return { success: true, lab_group: db.lab_groups[code] };
    }

    // 8. Create Project Team (with selected students & topic)
    if (path === "/api/faculty/teams" && method === "POST") {
      const lgCode = normalizeLabGroupCode(body.lab_group || "L1");
      const sem = body.semester || state.semester || "Fall 2026";
      const cid = body.course_id || state.course_id || "BT_301";
      const ts = nowStamp();
      if (!db.lab_groups[lgCode]) {
        db.lab_groups[lgCode] = { lab_group_id: lgCode, name: labGroupDisplayName(lgCode), semester: sem, course_id: cid, created_at: ts };
      }
      const existingInLg = Object.values(db.teams || {}).filter(t => t.lab_group === lgCode && t.status !== "archived");
      let seq = existingInLg.length + 1;
      let teamId = `${lgCode}-T${seq}`;
      while (db.teams[teamId]) { seq++; teamId = `${lgCode}-T${seq}`; }
      const tName = (body.team_name || "").trim() || `Team ${seq}`;
      const memberIds = [];

      for (const rawSid of (body.student_ids || [])) {
        const sid = String(rawSid || "").trim().toUpperCase();
        const st = db.students[sid];
        if (!st) continue;
        const prevTeamId = st.team_id || "";
        if (prevTeamId && prevTeamId !== teamId && db.teams[prevTeamId]) {
          db.teams[prevTeamId].member_ids = (db.teams[prevTeamId].member_ids || []).filter(m => m !== sid);
          syncTeamToMemberLocalDrafts(db, prevTeamId);
        }
        st.lab_group = lgCode;
        st.team_id = teamId;
        st.updated_at = ts;
        if (!memberIds.includes(sid)) memberIds.push(sid);
      }

      db.teams[teamId] = {
        team_id: teamId,
        team_name: tName,
        lab_group: lgCode,
        semester: sem,
        course_id: cid,
        pi_id: body.pi_id || "",
        topic_title: (body.topic_title || "").trim(),
        topic_description: (body.topic_description || "").trim(),
        member_ids: memberIds,
        status: "active",
        created_at: ts,
        updated_at: ts
      };

      db.team_workspaces[teamId] = {
        team_id: teamId,
        shared_notes: `Welcome to ${tName} (${teamId}) Shared Team Workspace!\nUse this space to coordinate experiments, aims, and literature references with your teammates.`,
        important_info: (body.topic_description || "").trim(),
        pi_feedback_notes: "",
        proposal_draft: {
          team_id: teamId,
          team_name: tName,
          lab_group: lgCode,
          course_id: cid,
          semester: sem,
          title: (body.topic_title || "").trim()
        },
        updates_feed: [{
          timestamp: ts,
          author_id: "faculty",
          author_name: "Faculty Coordinator",
          author_role: "faculty",
          action: "workspace_created",
          message: `Created project team ${tName} (${teamId}) in ${lgCode}.`
        }],
        last_updated_at: ts,
        last_updated_by: "Faculty Coordinator"
      };

      syncTeamToMemberLocalDrafts(db, teamId);
      recordLocalAudit(db, "team_created", `Created ${tName} (${teamId}) in ${lgCode} with ${memberIds.length} member(s)`, "Faculty Coordinator", "", teamId, "", `${memberIds.length} members`);
      saveLocalCohortDb(db);
      return { success: true, team: enrichTeamObj(db, db.teams[teamId]) };
    }

    // 9. Move Student Between Teams
    if (path === "/api/faculty/teams/move_student" && method === "POST") {
      const sid = String(body.student_id || "").trim().toUpperCase();
      const targetTid = String(body.target_team_id || "").trim();
      const st = db.students[sid];
      const targetTeam = db.teams[targetTid];
      if (!st || !targetTeam) return { success: false, error: "Student or target team not found." };
      const oldTid = st.team_id || "";
      if (oldTid && db.teams[oldTid]) {
        db.teams[oldTid].member_ids = (db.teams[oldTid].member_ids || []).filter(m => m !== sid);
        syncTeamToMemberLocalDrafts(db, oldTid);
      }
      if (!targetTeam.member_ids.includes(sid)) targetTeam.member_ids.push(sid);
      st.team_id = targetTid;
      st.lab_group = targetTeam.lab_group || st.lab_group;
      st.updated_at = nowStamp();
      syncTeamToMemberLocalDrafts(db, targetTid);
      recordLocalAudit(db, "team_member_moved", `Moved ${st.student_name} (${sid}) from ${oldTid || 'Unassigned'} to ${targetTid}`, "Faculty Coordinator", sid, targetTid, oldTid, targetTid);
      saveLocalCohortDb(db);
      return { success: true, team: enrichTeamObj(db, targetTeam) };
    }

    // 10. Team actions (/api/faculty/teams/<tid>...)
    const teamMatch = path.match(/^\/api\/faculty\/teams\/([^/]+)(?:\/(.+))?$/);
    if (teamMatch) {
      const tid = decodeURIComponent(teamMatch[1]);
      const sub = teamMatch[2] || "";
      const team = db.teams[tid];
      if (!team) return { success: false, error: `Team ${tid} not found.` };
      const ts = nowStamp();

      if (!sub && method === "PUT") {
        const oldName = team.team_name;
        team.team_name = (body.team_name || "").trim() || oldName;
        team.updated_at = ts;
        syncTeamToMemberLocalDrafts(db, tid);
        recordLocalAudit(db, "team_renamed", `Renamed ${tid}: ${oldName} ➔ ${team.team_name}`, "Faculty Coordinator", "", tid, oldName, team.team_name);
        saveLocalCohortDb(db);
        return { success: true, team: enrichTeamObj(db, team) };
      }

      if (!sub && method === "DELETE") {
        for (const sid of (team.member_ids || [])) {
          if (db.students[sid] && db.students[sid].team_id === tid) {
            db.students[sid].team_id = "";
          }
        }
        team.member_ids = [];
        team.status = "archived";
        recordLocalAudit(db, "team_deleted", `Archived team ${tid}`, "Faculty Coordinator", "", tid, "active", "archived");
        saveLocalCohortDb(db);
        return { success: true };
      }

      if (sub === "members" && method === "POST") {
        const sid = String(body.student_id || "").trim().toUpperCase();
        const st = db.students[sid];
        if (!st) return { success: false, error: `Student ${sid} not found.` };
        if (st.team_id && st.team_id !== tid && !body.allow_move) {
          return { success: false, error: `Student ${sid} is already in team ${st.team_id}.` };
        }
        if (st.team_id && db.teams[st.team_id]) {
          db.teams[st.team_id].member_ids = (db.teams[st.team_id].member_ids || []).filter(m => m !== sid);
        }
        if (!team.member_ids.includes(sid)) team.member_ids.push(sid);
        st.team_id = tid;
        st.lab_group = team.lab_group || st.lab_group;
        syncTeamToMemberLocalDrafts(db, tid);
        recordLocalAudit(db, "team_member_added", `Added ${st.student_name} (${sid}) to ${tid}`, "Faculty Coordinator", sid, tid, "Unassigned", tid);
        saveLocalCohortDb(db);
        return { success: true, team: enrichTeamObj(db, team) };
      }

      const rmMatch = sub.match(/^members\/([^/]+)$/);
      if (rmMatch && method === "DELETE") {
        const sid = decodeURIComponent(rmMatch[1]).toUpperCase();
        team.member_ids = (team.member_ids || []).filter(m => m !== sid);
        if (db.students[sid] && db.students[sid].team_id === tid) {
          db.students[sid].team_id = "";
        }
        syncTeamToMemberLocalDrafts(db, tid);
        recordLocalAudit(db, "team_member_removed", `Removed ${sid} from ${tid}`, "Faculty Coordinator", sid, tid, tid, "Unassigned");
        saveLocalCohortDb(db);
        return { success: true, team: enrichTeamObj(db, team) };
      }

      if (sub === "assign_pi" && method === "POST") {
        const oldPi = team.pi_id || "Unassigned";
        team.pi_id = (body.pi_id || "").trim();
        team.updated_at = ts;
        syncTeamToMemberLocalDrafts(db, tid);
        const piName = (db.pis[team.pi_id] || {}).name || "Unassigned";
        recordLocalAudit(db, "pi_assigned", `Assigned PI ${piName} to ${tid}`, "Faculty Coordinator", "", tid, oldPi, piName);
        saveLocalCohortDb(db);
        return { success: true, team: enrichTeamObj(db, team) };
      }

      if (sub === "assign_topic" && method === "POST") {
        const oldTopic = team.topic_title || "Unassigned";
        team.topic_title = (body.topic_title || "").trim();
        if (body.topic_description !== undefined) {
          team.topic_description = (body.topic_description || "").trim();
        }
        team.updated_at = ts;
        if (db.team_workspaces[tid] && db.team_workspaces[tid].proposal_draft) {
          db.team_workspaces[tid].proposal_draft.title = team.topic_title;
        }
        syncTeamToMemberLocalDrafts(db, tid);
        recordLocalAudit(db, "topic_assigned", `Assigned topic '${team.topic_title || 'Unassigned'}' to ${tid}`, "Faculty Coordinator", "", tid, oldTopic, team.topic_title || "Unassigned");
        saveLocalCohortDb(db);
        return { success: true, team: enrichTeamObj(db, team) };
      }
    }

    // 11. Register PI
    if (path === "/api/faculty/pis" && method === "POST") {
      const name = String(body.name || "").trim();
      if (!name) return { success: false, error: "PI name is required." };
      const pid = "PI_" + String(Object.keys(db.pis || {}).length + 1).padStart(2, "0");
      db.pis[pid] = { pi_id: pid, name: name, email: body.email || "", department: body.department || "Biotechnology", role: "pi" };
      saveLocalCohortDb(db);
      return { success: true, pi: db.pis[pid] };
    }

    // 12. Shared Team Workspace GET & POST
    const wsMatch = path.match(/^\/api\/teams\/([^/]+)\/workspace$/);
    if (wsMatch) {
      const tid = decodeURIComponent(wsMatch[1]);
      const team = db.teams[tid];
      if (!team) return { success: false, error: `Team ${tid} not found.` };
      const tInfo = enrichTeamObj(db, team);
      if (!db.team_workspaces[tid]) {
        db.team_workspaces[tid] = {
          team_id: tid,
          shared_notes: "",
          important_info: tInfo.topic_description || "",
          pi_feedback_notes: "",
          proposal_draft: { title: tInfo.topic_title || "" },
          updates_feed: [],
          last_updated_at: nowStamp(),
          last_updated_by: "System"
        };
      }
      const ws = db.team_workspaces[tid];
      if (method === "POST") {
        const ts = nowStamp();
        if (body.shared_notes !== undefined) ws.shared_notes = body.shared_notes;
        if (body.important_info !== undefined) ws.important_info = body.important_info;
        if (body.pi_feedback_notes !== undefined) ws.pi_feedback_notes = body.pi_feedback_notes;
        if (body.proposal_draft && typeof body.proposal_draft === "object") {
          ws.proposal_draft = { ...(ws.proposal_draft || {}), ...body.proposal_draft };
        }
        ws.last_updated_at = ts;
        ws.last_updated_by = "Faculty Coordinator";
        ws.updates_feed = ws.updates_feed || [];
        ws.updates_feed.unshift({
          timestamp: ts,
          author_id: "faculty",
          author_name: "Faculty Coordinator",
          author_role: "faculty",
          action: "workspace_updated",
          message: body.update_message || "Updated shared workspace notes & guidance"
        });
        syncTeamToMemberLocalDrafts(db, tid);
        saveLocalCohortDb(db);
      }
      return {
        success: true,
        workspace: {
          ...tInfo,
          shared_notes: ws.shared_notes || "",
          important_info: ws.important_info || "",
          pi_feedback_notes: ws.pi_feedback_notes || "",
          proposal_draft: ws.proposal_draft || {},
          updates_feed: ws.updates_feed || [],
          last_updated_at: ws.last_updated_at || "",
          last_updated_by: ws.last_updated_by || "System",
          summary: { completion_percentage: 85, word_count: 420 }
        }
      };
    }

    // 13. Audit History
    if (path === "/api/faculty/audit_history" && method === "GET") {
      return { success: true, history: (db.audit_history || []).slice(0, 100) };
    }

    return { success: true };
  }

  async function cohortApiFetch(url, options = {}) {
    if (!isStaticEnv()) {
      try {
        const resp = await window.fetch(url, options);
        if (resp.ok) {
          return resp;
        }
      } catch (e) {
        // Fall through to client-side localStorage Cohort Engine
      }
    }
    const localData = await handleLocalCohortApi(url, options);
    return {
      ok: true,
      status: 200,
      json: async () => localData
    };
  }
  window.cohortApiFetch = cohortApiFetch;

  // ============================================================================
  // INITIALIZATION & NAVIGATION WIRING
  // ============================================================================
  function initFacultyCohortExtension() {
    wireCohortSubTabs();
    wireContextSelectors();
    wireAttendanceUpload();
    wireStudentDirectoryControls();
    wireLabGroupControls();
    wireTeamCreationControls();
    wirePiAndTopicControls();
    wireSharedWorkspaceControls();
  }

  function wireCohortSubTabs() {
    document.querySelectorAll(".cohort-subtab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-subtab");
        switchCohortSubTab(tab);
      });
    });
  }

  function switchCohortSubTab(tab) {
    state.activeSubTab = tab;
    document.querySelectorAll(".cohort-subtab-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-subtab") === tab);
    });
    document.querySelectorAll(".cohort-subpanel").forEach(p => {
      p.style.display = p.id === `cohort-subpanel-${tab}` ? "block" : "none";
    });

    if (tab === "students") {
      loadFilteredStudents();
    } else if (tab === "labgroups") {
      renderLabGroupsPanel();
    } else if (tab === "teams") {
      renderTeamsPanel();
    } else if (tab === "pitopics") {
      renderPiAndTopicsPanel();
    } else if (tab === "workspaces") {
      renderWorkspacesSelectorPanel();
    } else if (tab === "history") {
      loadAuditHistoryPanel();
    }
  }
  window.switchCohortSubTab = switchCohortSubTab;

  function wireContextSelectors() {
    const semSel = document.getElementById("cohort-semester-select");
    const cidSel = document.getElementById("cohort-course-select");
    const btnRefreshAll = document.getElementById("btn-cohort-refresh-all");

    const onContextChange = async () => {
      state.semester = semSel ? semSel.value : "Fall 2026";
      state.course_id = cidSel ? cidSel.value : "BT_301";
      try {
        await cohortApiFetch("/api/faculty/cohort/context", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ semester: state.semester, course_id: state.course_id })
        });
      } catch (e) {}
      await refreshCohortData();
      notify(`Switched context to ${state.semester} • ${state.course_id}`);
    };

    if (semSel) semSel.addEventListener("change", onContextChange);
    if (cidSel) cidSel.addEventListener("change", onContextChange);
    if (btnRefreshAll) btnRefreshAll.addEventListener("click", () => refreshCohortData(true));
  }

  async function refreshCohortData(showToastMsg = false) {
    try {
      const q = new URLSearchParams({ semester: state.semester, course_id: state.course_id });
      const resp = await cohortApiFetch(`/api/faculty/cohort/overview?${q.toString()}`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.success) {
          state.overview = data.overview;
          state.pis = data.pis || [];
          state.labGroups = data.lab_groups || [];
          state.teams = data.teams || [];
          state.auditHistory = data.audit_history || [];
          renderCohortKpiBanner();
          populateFilterDropdowns();
          await loadFilteredStudents();
          renderLabGroupsPanel();
          renderTeamsPanel();
          renderPiAndTopicsPanel();
          renderWorkspacesSelectorPanel();
          renderAuditHistoryTable(state.auditHistory);
          if (showToastMsg && typeof window.loadCohortRoster === "function") {
            window.loadCohortRoster();
          }
          if (showToastMsg) notify("Cohort, lab groups, teams, and workspaces synchronized!");
        }
      }
    } catch (e) {
      console.warn("Cohort overview fetch error:", e);
    }
  }
  window.refreshCohortData = refreshCohortData;

  function renderCohortKpiBanner() {
    const ov = state.overview || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val !== undefined && val !== null ? val : 0;
    };
    setTxt("cohort-kpi-students", ov.total_students || 0);
    setTxt("cohort-kpi-labgroups", ov.total_lab_groups || 0);
    setTxt("cohort-kpi-teams", ov.total_teams || 0);
    setTxt("cohort-kpi-unassigned", ov.unassigned_team_count || 0);
    setTxt("cohort-kpi-missing-pi", ov.teams_without_pi_count || 0);
    setTxt("cohort-kpi-missing-topic", ov.teams_without_topic_count || 0);
  }

  function populateFilterDropdowns() {
    const lgFilter = document.getElementById("filter-student-labgroup");
    if (lgFilter) {
      const cur = lgFilter.value;
      lgFilter.innerHTML = `<option value="">All Lab Groups</option>` +
        state.labGroups.map(lg => `<option value="${esc(lg.lab_group_id)}">${esc(lg.lab_group_id)} (${lg.student_count} students)</option>`).join("");
      lgFilter.value = cur;
    }

    const tmFilter = document.getElementById("filter-student-team");
    if (tmFilter) {
      const cur = tmFilter.value;
      tmFilter.innerHTML = `<option value="">All Teams</option>` +
        state.teams.map(t => `<option value="${esc(t.team_id)}">${esc(t.team_id)} — ${esc(t.team_name)}</option>`).join("");
      tmFilter.value = cur;
    }

    const piFilter = document.getElementById("filter-student-pi");
    if (piFilter) {
      const cur = piFilter.value;
      piFilter.innerHTML = `<option value="">All PIs / Supervisors</option>` +
        state.pis.map(p => `<option value="${esc(p.pi_id)}">${esc(p.name)}</option>`).join("");
      piFilter.value = cur;
    }

    // Also populate Lab Group selectors in Team creation and Move Student modals
    const teamLgSelect = document.getElementById("create-team-labgroup");
    if (teamLgSelect) {
      const cur = teamLgSelect.value || state.selectedLabGroup || (state.labGroups[0] ? state.labGroups[0].lab_group_id : "L1");
      teamLgSelect.innerHTML = state.labGroups.map(lg =>
        `<option value="${esc(lg.lab_group_id)}">${esc(lg.lab_group_id)} — ${esc(lg.name)} (${lg.unassigned_count} unassigned)</option>`
      ).join("") || `<option value="L1">L1 — Lab Group 1</option>`;
      teamLgSelect.value = cur;
    }

    const createTeamPi = document.getElementById("create-team-pi");
    if (createTeamPi) {
      const cur = createTeamPi.value;
      createTeamPi.innerHTML = `<option value="">-- Optional: Select PI / Supervisor --</option>` +
        state.pis.map(p => `<option value="${esc(p.pi_id)}">${esc(p.name)} (${esc(p.department)})</option>`).join("");
      createTeamPi.value = cur;
    }
  }

  // ============================================================================
  // 1. ATTENDANCE UPLOAD, PREVIEW & EXPLICIT CONFIRMATION
  // ============================================================================
  function wireAttendanceUpload() {
    const fileInput = document.getElementById("attendance-file-input");
    const btnPreviewFile = document.getElementById("btn-preview-attendance-file");
    const btnLoadSampleCsv = document.getElementById("btn-load-sample-attendance");
    const btnConfirmImport = document.getElementById("btn-confirm-attendance-import");
    const btnCancelPreview = document.getElementById("btn-cancel-attendance-preview");

    if (btnPreviewFile) {
      btnPreviewFile.addEventListener("click", async () => {
        const csvArea = document.getElementById("attendance-csv-paste");
        if (fileInput && fileInput.files && fileInput.files.length > 0) {
          const formData = new FormData();
          formData.append("file", fileInput.files[0]);
          formData.append("semester", state.semester);
          formData.append("course_id", state.course_id);
          btnPreviewFile.disabled = true;
          btnPreviewFile.innerText = "⏳ Analyzing Attendance Sheet...";
          try {
            const resp = await cohortApiFetch("/api/faculty/attendance/preview", {
              method: "POST",
              body: formData
            });
            const res = await resp.json();
            if (res.success) {
              state.lastAttendancePreview = res;
              renderAttendancePreview(res);
              notify(`Attendance Preview ready: ${res.students_detected} valid students across ${res.lab_groups_detected} lab groups.`);
            } else {
              notify(res.error || "Failed to parse attendance file.", "error");
            }
          } catch (err) {
            notify("Error uploading attendance sheet.", "error");
          } finally {
            btnPreviewFile.disabled = false;
            btnPreviewFile.innerText = "🔍 Upload & Generate Import Preview";
          }
        } else if (csvArea && csvArea.value.trim()) {
          btnPreviewFile.disabled = true;
          btnPreviewFile.innerText = "⏳ Analyzing CSV Data...";
          try {
            const resp = await cohortApiFetch("/api/faculty/attendance/preview", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                csv_text: csvArea.value.trim(),
                semester: state.semester,
                course_id: state.course_id,
                filename: "pasted_attendance.csv"
              })
            });
            const res = await resp.json();
            if (res.success) {
              state.lastAttendancePreview = res;
              renderAttendancePreview(res);
              notify(`Attendance Preview ready: ${res.students_detected} valid students across ${res.lab_groups_detected} lab groups.`);
            } else {
              notify(res.error || "Failed to parse CSV data.", "error");
            }
          } catch (err) {
            notify("Error previewing CSV attendance.", "error");
          } finally {
            btnPreviewFile.disabled = false;
            btnPreviewFile.innerText = "🔍 Upload & Generate Import Preview";
          }
        } else {
          notify("Please select a CSV/Excel (.xlsx) file or paste attendance rows first.", "warning");
        }
      });
    }

    if (btnLoadSampleCsv) {
      btnLoadSampleCsv.addEventListener("click", () => {
        const sampleCsv = [
          "Student ID,Student Name,Lab Group,Email",
          "20230001,Ahmed Ali,L1,ahmed.ali@student.edu.eg",
          "20230002,Sara Mohamed,L1,sara.mohamed@student.edu.eg",
          "20230003,Mariam Hassan,L1,mariam.hassan@student.edu.eg",
          "20230004,Karim Adel,L1,karim.adel@student.edu.eg",
          "20230005,Omar Khaled,L1,omar.khaled@student.edu.eg",
          "20230006,Nour Hany,L1,nour.hany@student.edu.eg",
          "20230007,Youssef Tarek,L2,youssef.tarek@student.edu.eg",
          "20230008,Salma Nabil,L2,salma.nabil@student.edu.eg",
          "20230009,Hana Mostafa,L2,hana.mostafa@student.edu.eg",
          "20230010,Ziad Mahmoud,L2,ziad.mahmoud@student.edu.eg",
          "20230011,Farida Ashraf,L3,farida.ashraf@student.edu.eg",
          "20230012,Marwan Sameh,L3,marwan.sameh@student.edu.eg",
          "13989,Maya Abdelrazek,L1,m.abdelrazek@nu.edu.eg",
          "20230001,Ahmed Ali,L1,ahmed.ali@student.edu.eg",
          ",Missing ID Student,L2,missing@student.edu.eg"
        ].join("\n");
        const csvArea = document.getElementById("attendance-csv-paste");
        if (csvArea) csvArea.value = sampleCsv;
        if (btnPreviewFile) btnPreviewFile.click();
      });
    }

    if (btnConfirmImport) {
      btnConfirmImport.addEventListener("click", async () => {
        if (!state.lastAttendancePreview || !state.lastAttendancePreview.preview_id) {
          notify("No active attendance preview to confirm.", "warning");
          return;
        }
        btnConfirmImport.disabled = true;
        btnConfirmImport.innerText = "⏳ Importing Confirmed Students...";
        try {
          const resp = await cohortApiFetch("/api/faculty/attendance/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ preview_id: state.lastAttendancePreview.preview_id })
          });
          const res = await resp.json();
          if (res.success) {
            notify(`✅ Imported ${res.imported_count} students across ${res.lab_groups_count} lab groups! Choose a Lab Group below to select students, form teams, and write their topics.`);
            state.lastAttendancePreview = null;
            const previewCard = document.getElementById("attendance-preview-card");
            if (previewCard) previewCard.style.display = "none";
            await refreshCohortData();
            switchCohortSubTab("labgroups");
          } else {
            notify(res.error || "Failed to confirm attendance import.", "error");
          }
        } catch (err) {
          notify("Network error confirming attendance import.", "error");
        } finally {
          btnConfirmImport.disabled = false;
          btnConfirmImport.innerText = "✅ Confirm & Commit Attendance Import";
        }
      });
    }

    if (btnCancelPreview) {
      btnCancelPreview.addEventListener("click", () => {
        state.lastAttendancePreview = null;
        const previewCard = document.getElementById("attendance-preview-card");
        if (previewCard) previewCard.style.display = "none";
        notify("Attendance import preview discarded. No database records were modified.");
      });
    }
  }

  function renderAttendancePreview(res) {
    const card = document.getElementById("attendance-preview-card");
    if (!card) return;
    card.style.display = "block";

    const sum = res.summary || {};
    document.getElementById("prev-students-detected").innerText = res.students_detected || 0;
    document.getElementById("prev-labgroups-detected").innerText = res.lab_groups_detected || 0;
    document.getElementById("prev-new-count").innerText = sum.new_count || 0;
    document.getElementById("prev-existing-count").innerText = sum.existing_count || 0;
    document.getElementById("prev-dup-count").innerText = (sum.duplicate_id_count || 0) + (sum.duplicate_row_count || 0);
    document.getElementById("prev-missing-count").innerText =
      (sum.missing_id_count || 0) + (sum.missing_name_count || 0) + (sum.missing_lab_group_count || 0);

    const tbody = document.getElementById("attendance-preview-tbody");
    if (!tbody) return;
    tbody.innerHTML = (res.rows || []).map(r => {
      let badgeBg = "#dcfce7";
      let badgeCol = "#166534";
      if (r.status === "Existing") {
        badgeBg = "#e0f2fe";
        badgeCol = "#0369a1";
      } else if (!r.is_valid) {
        badgeBg = "#fee2e2";
        badgeCol = "#991b1b";
      }
      return `
        <tr style="${!r.is_valid ? 'background:#fff1f2;' : ''}">
          <td>${r.row_number}</td>
          <td><strong style="font-family:monospace; color:#4338ca;">${esc(r.student_id || "—")}</strong></td>
          <td><strong>${esc(r.student_name || "—")}</strong></td>
          <td><span class="status-pill" style="background:#f1f5f9; color:#334155;">${esc(r.lab_group || "—")}</span></td>
          <td>
            <span class="status-pill" style="background:${badgeBg}; color:${badgeCol};">${esc(r.status)}</span>
            ${r.issues && r.issues.length ? `<div style="font-size:0.72rem; color:#dc2626; margin-top:2px;">${esc(r.issues.join("; "))}</div>` : ""}
          </td>
        </tr>
      `;
    }).join("");
  }

  // ============================================================================
  // 2. STUDENT MANAGEMENT VIEW, SEARCH, FILTERS & MOVE LAB GROUP
  // ============================================================================
  function wireStudentDirectoryControls() {
    const searchIn = document.getElementById("filter-student-search");
    const lgSel = document.getElementById("filter-student-labgroup");
    const tmSel = document.getElementById("filter-student-team");
    const piSel = document.getElementById("filter-student-pi");
    const stSel = document.getElementById("filter-student-status");
    const btnAddStudent = document.getElementById("btn-quick-add-student");

    const triggerFilter = () => {
      state.filters.q = searchIn ? searchIn.value.trim() : "";
      state.filters.lab_group = lgSel ? lgSel.value : "";
      state.filters.team_id = tmSel ? tmSel.value : "";
      state.filters.pi_id = piSel ? piSel.value : "";
      state.filters.assignment_status = stSel ? stSel.value : "";
      loadFilteredStudents();
    };

    if (searchIn) searchIn.addEventListener("input", triggerFilter);
    if (lgSel) lgSel.addEventListener("change", triggerFilter);
    if (tmSel) tmSel.addEventListener("change", triggerFilter);
    if (piSel) piSel.addEventListener("change", triggerFilter);
    if (stSel) stSel.addEventListener("change", triggerFilter);

    if (btnAddStudent) {
      btnAddStudent.addEventListener("click", async () => {
        const sid = (document.getElementById("quick-add-sid")?.value || "").trim();
        const sname = (document.getElementById("quick-add-sname")?.value || "").trim();
        const lgroup = (document.getElementById("quick-add-lgroup")?.value || "").trim();
        if (!sid || !sname) {
          notify("Please enter Student ID and Student Name.", "warning");
          return;
        }
        const resp = await cohortApiFetch("/api/faculty/students", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            student_id: sid,
            student_name: sname,
            lab_group: lgroup,
            semester: state.semester,
            course_id: state.course_id
          })
        });
        const res = await resp.json();
        if (res.success) {
          document.getElementById("quick-add-sid").value = "";
          document.getElementById("quick-add-sname").value = "";
          notify(`Saved student ${res.student.student_name} (${res.student.student_id}) in ${res.student.lab_group || 'Unassigned'}!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Could not add student.", "error");
        }
      });
    }

    // Move Lab Group Modal wiring
    const btnCancelMoveLg = document.getElementById("btn-cancel-move-lg");
    const btnConfirmMoveLg = document.getElementById("btn-confirm-move-lg");
    const modalMoveLg = document.getElementById("modal-move-lab-group");

    if (btnCancelMoveLg && modalMoveLg) {
      btnCancelMoveLg.addEventListener("click", () => {
        modalMoveLg.style.display = "none";
      });
    }
    if (btnConfirmMoveLg) {
      btnConfirmMoveLg.addEventListener("click", async () => {
        const sid = document.getElementById("move-lg-student-id").value;
        const targetLg = (document.getElementById("move-lg-target-input").value || "").trim();
        if (!sid || !targetLg) {
          notify("Please specify the new Lab Group (e.g. L3).", "warning");
          return;
        }
        const resp = await cohortApiFetch("/api/faculty/students/move_lab_group", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            student_id: sid,
            new_lab_group: targetLg,
            semester: state.semester,
            course_id: state.course_id
          })
        });
        const res = await resp.json();
        if (res.success) {
          if (modalMoveLg) modalMoveLg.style.display = "none";
          notify(`✅ ${res.audit_entry.summary}`);
          await refreshCohortData();
        } else {
          notify(res.error || "Failed to move student.", "error");
        }
      });
    }
  }

  async function loadFilteredStudents() {
    const params = new URLSearchParams({
      semester: state.semester,
      course_id: state.course_id
    });
    if (state.filters.q) params.set("q", state.filters.q);
    if (state.filters.lab_group) params.set("lab_group", state.filters.lab_group);
    if (state.filters.team_id) params.set("team_id", state.filters.team_id);
    if (state.filters.pi_id) params.set("pi_id", state.filters.pi_id);
    if (state.filters.assignment_status) params.set("assignment_status", state.filters.assignment_status);

    try {
      const resp = await cohortApiFetch(`/api/faculty/students?${params.toString()}`);
      if (resp.ok) {
        const res = await resp.json();
        if (res.success) {
          state.students = res.students || [];
          renderStudentsDirectoryTable(state.students);
        }
      }
    } catch (e) {}
  }

  function renderStudentsDirectoryTable(students) {
    const tbody = document.getElementById("cohort-students-tbody");
    const countBadge = document.getElementById("cohort-students-count-badge");
    if (countBadge) countBadge.innerText = `${students.length} student(s) shown`;
    if (!tbody) return;

    if (!students.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#94a3b8; padding:24px;">No students match the current filters. Upload an attendance sheet or adjust filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = students.map(st => {
      const lgBadge = st.lab_group
        ? `<span class="status-pill" style="background:#e0e7ff; color:#3730a3;">${esc(st.lab_group)}</span>`
        : `<span class="status-pill" style="background:#fee2e2; color:#991b1b;">Unassigned</span>`;

      const tmBadge = st.team_id
        ? `<span class="status-pill" style="background:#dcfce7; color:#166534;">${esc(st.team_id)} (${esc(st.team_name)})</span>`
        : `<span class="status-pill" style="background:#fef3c7; color:#92400e;">Unassigned</span>`;

      const piText = st.pi_name ? esc(st.pi_name) : `<span style="color:#94a3b8;">Unassigned</span>`;
      const topicText = st.topic_title
        ? `<span title="${esc(st.topic_title)}">${esc(st.topic_title.length > 48 ? st.topic_title.slice(0, 48) + "..." : st.topic_title)}</span>`
        : `<span style="color:#94a3b8;">Unassigned</span>`;

      return `
        <tr>
          <td><strong style="font-family:monospace; color:#4338ca;">${esc(st.student_id)}</strong></td>
          <td>
            <strong>${esc(st.student_name)}</strong>
            ${st.email ? `<div style="font-size:0.73rem; color:#64748b;">${esc(st.email)}</div>` : ""}
          </td>
          <td>${lgBadge}</td>
          <td>${tmBadge}</td>
          <td>${piText}</td>
          <td style="max-width:260px;">${topicText}</td>
          <td>
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              <button type="button" class="btn-student-nav btn-open-move-lg"
                      data-id="${esc(st.student_id)}"
                      data-name="${esc(st.student_name)}"
                      data-lg="${esc(st.lab_group || 'Unassigned')}"
                      style="font-size:0.74rem; padding:4px 8px;">
                🔄 Change Lab Group
              </button>
              ${st.team_id ? `
                <button type="button" class="btn-control-action btn-open-team-ws"
                        data-team="${esc(st.team_id)}"
                        style="font-size:0.74rem; padding:4px 8px; background:#059669;">
                  🌐 Team Workspace
                </button>
              ` : `
                <button type="button" class="btn-student-nav btn-jump-assign-team"
                        data-id="${esc(st.student_id)}"
                        data-lg="${esc(st.lab_group || 'L1')}"
                        style="font-size:0.74rem; padding:4px 8px; color:#4338ca; border-color:#c7d2fe;">
                  ➕ Assign Team
                </button>
              `}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".btn-open-move-lg").forEach(btn => {
      btn.addEventListener("click", () => {
        openMoveLabGroupModal(
          btn.getAttribute("data-id"),
          btn.getAttribute("data-name"),
          btn.getAttribute("data-lg")
        );
      });
    });

    tbody.querySelectorAll(".btn-open-team-ws").forEach(btn => {
      btn.addEventListener("click", () => {
        const tid = btn.getAttribute("data-team");
        openSharedTeamWorkspace(tid);
      });
    });

    tbody.querySelectorAll(".btn-jump-assign-team").forEach(btn => {
      btn.addEventListener("click", () => {
        state.selectedLabGroup = btn.getAttribute("data-lg") || "L1";
        switchCohortSubTab("teams");
      });
    });
  }

  function openMoveLabGroupModal(studentId, studentName, currentLg) {
    const modal = document.getElementById("modal-move-lab-group");
    if (!modal) return;
    document.getElementById("move-lg-student-id").value = studentId;
    document.getElementById("move-lg-student-display").innerText = `${studentName} (${studentId})`;
    document.getElementById("move-lg-current-display").innerText = currentLg || "Unassigned";
    const targetInput = document.getElementById("move-lg-target-input");
    if (targetInput) {
      targetInput.value = "";
      targetInput.placeholder = "e.g. L3";
    }
    modal.style.display = "flex";
  }
  window.openMoveLabGroupModal = openMoveLabGroupModal;

  // ============================================================================
  // 3. LAB GROUP MANAGEMENT & UNASSIGNED STUDENTS VIEW
  // ============================================================================
  function wireLabGroupControls() {
    const btnCreateLg = document.getElementById("btn-create-lab-group");
    if (btnCreateLg) {
      btnCreateLg.addEventListener("click", async () => {
        const codeIn = document.getElementById("new-labgroup-code");
        const nameIn = document.getElementById("new-labgroup-name");
        const code = (codeIn ? codeIn.value : "").trim();
        const name = (nameIn ? nameIn.value : "").trim();
        if (!code) {
          notify("Enter a Lab Group code (e.g. L1, L2, L3).", "warning");
          return;
        }
        const resp = await cohortApiFetch("/api/faculty/lab_groups", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lab_group_id: code,
            name: name,
            semester: state.semester,
            course_id: state.course_id
          })
        });
        const res = await resp.json();
        if (res.success) {
          if (codeIn) codeIn.value = "";
          if (nameIn) nameIn.value = "";
          state.selectedLabGroup = res.lab_group.lab_group_id;
          notify(`Created ${res.lab_group.name} (${res.lab_group.lab_group_id})!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Could not create lab group.", "error");
        }
      });
    }
  }

  function renderLabGroupsPanel() {
    const grid = document.getElementById("lab-groups-cards-grid");
    const detailContainer = document.getElementById("lab-group-detail-container");
    if (!grid) return;

    if (!state.labGroups.length) {
      grid.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding:24px; color:#64748b; background:#f8fafc; border-radius:12px; border:1px dashed #cbd5e1;">No Lab Groups created yet. Upload an attendance sheet or add a Lab Group above.</div>`;
      if (detailContainer) detailContainer.innerHTML = "";
      return;
    }

    if (!state.selectedLabGroup || !state.labGroups.some(g => g.lab_group_id === state.selectedLabGroup)) {
      state.selectedLabGroup = state.labGroups[0].lab_group_id;
    }

    grid.innerHTML = state.labGroups.map(lg => {
      const isSelected = lg.lab_group_id === state.selectedLabGroup;
      return `
        <div class="lab-group-summary-card" data-lg="${esc(lg.lab_group_id)}"
             style="background:${isSelected ? '#eef2ff' : '#ffffff'}; border:2px solid ${isSelected ? '#4f46e5' : '#e2e8f0'}; border-radius:12px; padding:16px; cursor:pointer; transition:all 0.15s ease;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="font-size:1.05rem; color:#0f172a;">🧪 ${esc(lg.lab_group_id)} — ${esc(lg.name)}</strong>
            <span class="status-pill" style="background:#e0e7ff; color:#3730a3;">${lg.team_count} teams</span>
          </div>
          <div style="font-size:0.83rem; color:#475569; font-weight:600;">
            ${esc(lg.summary_label)}
          </div>
          <div style="margin-top:8px; font-size:0.76rem; color:${lg.unassigned_count > 0 ? '#b45309' : '#15803d'}; font-weight:700;">
            ${lg.unassigned_count > 0 ? `⚠️ ${lg.unassigned_count} unassigned student(s)` : `✅ All students assigned to teams`}
          </div>
        </div>
      `;
    }).join("");

    grid.querySelectorAll(".lab-group-summary-card").forEach(card => {
      card.addEventListener("click", () => {
        state.selectedLabGroup = card.getAttribute("data-lg");
        renderLabGroupsPanel();
      });
    });

    const activeLg = state.labGroups.find(g => g.lab_group_id === state.selectedLabGroup);
    if (!activeLg || !detailContainer) return;

    const unassignedHtml = activeLg.unassigned_students.length
      ? activeLg.unassigned_students.map(u =>
          `<span class="status-pill" style="background:#ffffff; border:1px solid #fcd34d; color:#92400e; padding:4px 10px; margin:2px;">👤 ${esc(u.student_name)} (<code>${esc(u.student_id)}</code>)</span>`
        ).join("")
      : `<span style="color:#15803d; font-weight:700;">🎉 Every student in ${esc(activeLg.lab_group_id)} is assigned to a project team!</span>`;

    detailContainer.innerHTML = `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin-top:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px; border-bottom:1px solid #f1f5f9; padding-bottom:12px;">
          <div>
            <h3 style="margin:0; font-size:1.1rem; color:#0f172a;">
              ${esc(activeLg.lab_group_id)} Detail — ${activeLg.student_count} Students • ${activeLg.team_count} Project Teams
            </h3>
            <div style="font-size:0.8rem; color:#64748b;">Select students below to form a project team and write their topic, or move students between lab groups</div>
          </div>
          <button type="button" class="btn-control-action" id="btn-lg-jump-create-team" data-lg="${esc(activeLg.lab_group_id)}">
            🤝 Open Full Team &amp; Topic Setup for ${esc(activeLg.lab_group_id)}
          </button>
        </div>

        <!-- Inline Quick Team & Topic Builder for Selected Lab Group -->
        <div style="background:#f8fafc; border:2px solid #c7d2fe; border-radius:12px; padding:16px; margin-bottom:18px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
            <div style="font-size:0.88rem; font-weight:800; color:#1e1b4b;">
              🤝 Form a Team in ${esc(activeLg.lab_group_id)}: Check Students Below ➔ State Team Name &amp; Write Topic
            </div>
            <span id="lg-inline-selected-count" class="status-pill" style="background:#e0e7ff; color:#3730a3; font-weight:800;">
              0 student(s) checked
            </span>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 1.5fr 1fr auto; gap:10px; align-items:end;">
            <div>
              <label style="display:block; font-size:0.72rem; font-weight:800; color:#312e81; margin-bottom:4px;">Team Name</label>
              <input type="text" id="lg-inline-team-name" class="form-input" placeholder="e.g. Team ${activeLg.team_count + 1}" style="font-size:0.8rem;">
            </div>
            <div>
              <label style="display:block; font-size:0.72rem; font-weight:800; color:#312e81; margin-bottom:4px;">Project Topic Title</label>
              <input type="text" id="lg-inline-team-topic" class="form-input" placeholder="Write the team's project topic..." style="font-size:0.8rem;">
            </div>
            <div>
              <label style="display:block; font-size:0.72rem; font-weight:800; color:#312e81; margin-bottom:4px;">PI / Supervisor (Optional)</label>
              <select id="lg-inline-team-pi" class="form-input" style="font-size:0.8rem;">
                <option value="">-- Optional PI --</option>
                ${state.pis.map(p => `<option value="${esc(p.pi_id)}">${esc(p.name)}</option>`).join("")}
              </select>
            </div>
            <button type="button" class="btn-control-action" id="btn-lg-inline-create-team" style="background:#059669; border-color:#059669; padding:9px 16px; white-space:nowrap; font-weight:800;">
              ✅ Form Team &amp; Save Topic
            </button>
          </div>
          <div style="margin-top:8px;">
            <input type="text" id="lg-inline-team-topic-desc" class="form-input" placeholder="Optional: Topic description / scope notes for students..." style="font-size:0.78rem;">
          </div>
        </div>

        <!-- Unassigned Students Alert Box (Section 5) -->
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:12px 16px; margin-bottom:18px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
            <div style="font-size:0.82rem; font-weight:800; color:#92400e;">
              📌 Unassigned Students in ${esc(activeLg.lab_group_id)} (${activeLg.unassigned_students.length}):
            </div>
            ${activeLg.unassigned_students.length ? `
              <button type="button" id="btn-lg-check-all-unassigned" class="btn-student-nav" style="font-size:0.72rem; padding:3px 9px;">
                ☑️ Check All Unassigned in ${esc(activeLg.lab_group_id)}
              </button>
            ` : ""}
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:6px;">
            ${unassignedHtml}
          </div>
        </div>

        <!-- Students in this Lab Group -->
        <div style="overflow-x:auto;">
          <table class="roster-table">
            <thead>
              <tr>
                <th style="width:46px; text-align:center;">Select</th>
                <th>Student ID</th>
                <th>Student Name</th>
                <th>Current Lab Group</th>
                <th>Assigned Team</th>
                <th>Project Topic</th>
                <th>PI / Supervisor</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${activeLg.students.length ? activeLg.students.map(st => `
                <tr style="${!st.team_id ? 'background:#fffdf5;' : ''}">
                  <td style="text-align:center;">
                    <input type="checkbox" class="chk-lg-inline-student" value="${esc(st.student_id)}" ${st.team_id ? 'title="Already in a team (checking will move student to the new team)"' : ''}>
                  </td>
                  <td><strong style="font-family:monospace; color:#4338ca;">${esc(st.student_id)}</strong></td>
                  <td><strong>${esc(st.student_name)}</strong></td>
                  <td><span class="status-pill" style="background:#e0e7ff; color:#3730a3;">${esc(st.lab_group)}</span></td>
                  <td>${st.team_id ? `<span class="status-pill" style="background:#dcfce7; color:#166534;">${esc(st.team_id)} — ${esc(st.team_name)}</span>` : `<span class="status-pill" style="background:#fef3c7; color:#92400e;">Unassigned</span>`}</td>
                  <td style="font-size:0.78rem; color:#334155; max-width:220px;">${st.topic_title ? `<strong>${esc(st.topic_title)}</strong>` : `<span style="color:#94a3b8;">Unassigned</span>`}</td>
                  <td>${esc(st.pi_name || "Unassigned")}</td>
                  <td>
                    <button type="button" class="btn-student-nav btn-lg-move-student"
                            data-id="${esc(st.student_id)}"
                            data-name="${esc(st.student_name)}"
                            data-lg="${esc(st.lab_group)}"
                            style="font-size:0.75rem; padding:4px 10px;">
                      🔄 Move Lab Group (e.g. ${esc(st.lab_group)} ➔ L3)
                    </button>
                  </td>
                </tr>
              `).join("") : `<tr><td colspan="8" style="text-align:center; color:#94a3b8;">No students in ${esc(activeLg.lab_group_id)}.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;

    const updateInlineLgCount = () => {
      const checked = detailContainer.querySelectorAll(".chk-lg-inline-student:checked").length;
      const badge = document.getElementById("lg-inline-selected-count");
      if (badge) badge.innerText = `${checked} student(s) checked`;
    };
    detailContainer.querySelectorAll(".chk-lg-inline-student").forEach(cb => {
      cb.addEventListener("change", updateInlineLgCount);
    });

    const btnCheckAllLg = document.getElementById("btn-lg-check-all-unassigned");
    if (btnCheckAllLg) {
      btnCheckAllLg.addEventListener("click", () => {
        const unassignedIds = new Set((activeLg.unassigned_students || []).map(u => u.student_id));
        detailContainer.querySelectorAll(".chk-lg-inline-student").forEach(cb => {
          cb.checked = unassignedIds.has(cb.value);
        });
        updateInlineLgCount();
      });
    }

    const btnInlineCreateTeam = document.getElementById("btn-lg-inline-create-team");
    if (btnInlineCreateTeam) {
      btnInlineCreateTeam.addEventListener("click", async () => {
        const checkedSids = Array.from(detailContainer.querySelectorAll(".chk-lg-inline-student:checked")).map(cb => cb.value);
        if (!checkedSids.length) {
          notify("Please check at least one student in this Lab Group to form a team.", "warning");
          return;
        }
        const tName = (document.getElementById("lg-inline-team-name")?.value || "").trim();
        const topicTitle = (document.getElementById("lg-inline-team-topic")?.value || "").trim();
        const topicDesc = (document.getElementById("lg-inline-team-topic-desc")?.value || "").trim();
        const piId = (document.getElementById("lg-inline-team-pi")?.value || "").trim();

        btnInlineCreateTeam.disabled = true;
        btnInlineCreateTeam.innerText = "⏳ Forming Team...";
        try {
          const resp = await cohortApiFetch("/api/faculty/teams", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              lab_group: activeLg.lab_group_id,
              team_name: tName,
              student_ids: checkedSids,
              pi_id: piId,
              topic_title: topicTitle,
              topic_description: topicDesc,
              semester: state.semester,
              course_id: state.course_id
            })
          });
          const res = await resp.json();
          if (res.success) {
            notify(`✅ Formed ${res.team.team_name} (${res.team.team_id}) in ${res.team.lab_group} with ${res.team.member_count} student(s)${res.team.topic_title ? ' & topic: ' + res.team.topic_title : ''}!`);
            await refreshCohortData();
          } else {
            notify(res.error || "Could not create team.", "error");
          }
        } catch (e) {
          notify("Error creating team.", "error");
        } finally {
          btnInlineCreateTeam.disabled = false;
          btnInlineCreateTeam.innerText = "✅ Form Team & Save Topic";
        }
      });
    }

    const btnJumpTeams = document.getElementById("btn-lg-jump-create-team");
    if (btnJumpTeams) {
      btnJumpTeams.addEventListener("click", () => {
        state.selectedLabGroup = btnJumpTeams.getAttribute("data-lg");
        const lgSel = document.getElementById("create-team-labgroup");
        if (lgSel) lgSel.value = state.selectedLabGroup;
        switchCohortSubTab("teams");
      });
    }

    detailContainer.querySelectorAll(".btn-lg-move-student").forEach(btn => {
      btn.addEventListener("click", () => {
        openMoveLabGroupModal(
          btn.getAttribute("data-id"),
          btn.getAttribute("data-name"),
          btn.getAttribute("data-lg")
        );
      });
    });
  }

  // ============================================================================
  // 4. PROJECT TEAMS SETUP WITHIN LAB GROUPS (SINGLE-ACTIVE-TEAM ENFORCED)
  // ============================================================================
  function updateSelectedStudentsBadge() {
    const checkedCount = document.querySelectorAll(".chk-unassigned-for-team:checked").length;
    const badge = document.getElementById("team-builder-selected-badge");
    if (badge) {
      badge.innerText = `${checkedCount} student(s) selected for team`;
    }
  }

  function wireTeamCreationControls() {
    const lgSelect = document.getElementById("create-team-labgroup");
    if (lgSelect) {
      lgSelect.addEventListener("change", () => {
        state.selectedLabGroup = lgSelect.value;
        renderTeamsPanel();
      });
    }

    const btnSelectAll = document.getElementById("btn-select-all-unassigned-team");
    if (btnSelectAll) {
      btnSelectAll.addEventListener("click", () => {
        document.querySelectorAll(".chk-unassigned-for-team").forEach(cb => {
          cb.checked = true;
        });
        updateSelectedStudentsBadge();
      });
    }

    const btnClearAll = document.getElementById("btn-clear-unassigned-team");
    if (btnClearAll) {
      btnClearAll.addEventListener("click", () => {
        document.querySelectorAll(".chk-unassigned-for-team").forEach(cb => {
          cb.checked = false;
        });
        updateSelectedStudentsBadge();
      });
    }

    const btnCreateTeam = document.getElementById("btn-create-project-team");
    if (btnCreateTeam) {
      btnCreateTeam.addEventListener("click", async () => {
        const lg = (document.getElementById("create-team-labgroup")?.value || state.selectedLabGroup || "L1").trim();
        const tName = (document.getElementById("create-team-name")?.value || "").trim();
        const piId = (document.getElementById("create-team-pi")?.value || "").trim();
        const topicTitle = (document.getElementById("create-team-topic")?.value || "").trim();
        const topicDesc = (document.getElementById("create-team-topic-desc")?.value || "").trim();

        const checkedBoxes = document.querySelectorAll(".chk-unassigned-for-team:checked");
        const selectedSids = Array.from(checkedBoxes).map(cb => cb.value);

        const resp = await cohortApiFetch("/api/faculty/teams", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lab_group: lg,
            team_name: tName,
            student_ids: selectedSids,
            pi_id: piId,
            topic_title: topicTitle,
            topic_description: topicDesc,
            semester: state.semester,
            course_id: state.course_id
          })
        });
        const res = await resp.json();
        if (res.success) {
          if (document.getElementById("create-team-name")) document.getElementById("create-team-name").value = "";
          if (document.getElementById("create-team-topic")) document.getElementById("create-team-topic").value = "";
          if (document.getElementById("create-team-topic-desc")) document.getElementById("create-team-topic-desc").value = "";
          notify(`✅ Created ${res.team.team_name} (${res.team.team_id}) in ${res.team.lab_group} with ${res.team.member_count} student(s)${res.team.topic_title ? ' & topic: ' + res.team.topic_title : ''}!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Failed to create team.", "error");
        }
      });
    }
  }

  function renderTeamsPanel() {
    const lgSelect = document.getElementById("create-team-labgroup");
    if (lgSelect && state.selectedLabGroup) {
      lgSelect.value = state.selectedLabGroup;
    }
    const currentLgCode = (lgSelect && lgSelect.value) || state.selectedLabGroup || (state.labGroups[0]?.lab_group_id || "L1");
    state.selectedLabGroup = currentLgCode;

    const activeLg = state.labGroups.find(g => g.lab_group_id === currentLgCode);
    const unassignedBox = document.getElementById("team-builder-unassigned-list");
    if (unassignedBox) {
      const unassigned = activeLg ? activeLg.unassigned_students : [];
      if (!unassigned.length) {
        unassignedBox.innerHTML = `<div style="font-size:0.8rem; color:#15803d; font-weight:600;">✅ No unassigned students remaining in ${esc(currentLgCode)}. You can still create an empty team or move students between teams below.</div>`;
      } else {
        unassignedBox.innerHTML = unassigned.map(u => `
          <label style="display:inline-flex; align-items:center; gap:6px; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:6px 10px; font-size:0.8rem; cursor:pointer;">
            <input type="checkbox" class="chk-unassigned-for-team" value="${esc(u.student_id)}">
            <span><strong>${esc(u.student_name)}</strong> (<code>${esc(u.student_id)}</code>)</span>
          </label>
        `).join("");
        unassignedBox.querySelectorAll(".chk-unassigned-for-team").forEach(cb => {
          cb.addEventListener("change", updateSelectedStudentsBadge);
        });
      }
      updateSelectedStudentsBadge();
    }

    const teamsContainer = document.getElementById("labgroup-teams-cards-container");
    if (!teamsContainer) return;

    const visibleTeams = state.teams.filter(t => !currentLgCode || t.lab_group === currentLgCode);
    const unassignedInLg = activeLg ? activeLg.unassigned_students : [];

    if (!visibleTeams.length) {
      teamsContainer.innerHTML = `<div style="padding:24px; text-align:center; color:#64748b; background:#f8fafc; border-radius:12px; border:1px dashed #cbd5e1;">No project teams in ${esc(currentLgCode)} yet. Use the form above to select students, state Team 1, and write their topic.</div>`;
      return;
    }

    teamsContainer.innerHTML = visibleTeams.map(tm => `
      <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:14px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px; border-bottom:1px solid #f1f5f9; padding-bottom:10px; margin-bottom:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="status-pill" style="background:#e0e7ff; color:#3730a3; font-family:monospace;">${esc(tm.team_id)}</span>
              <strong style="font-size:1rem; color:#0f172a;">${esc(tm.team_name)}</strong>
              <span class="status-pill" style="background:#f1f5f9; color:#475569;">${tm.member_count} student(s)</span>
            </div>
            <div style="font-size:0.78rem; color:#64748b; margin-top:4px;">
              👨‍🔬 <strong>PI:</strong> ${esc(tm.pi_name || "Unassigned")} • 🎯 <strong>Topic:</strong> ${esc(tm.topic_title || "Unassigned")}
            </div>
          </div>
          <div style="display:flex; gap:6px;">
            <button type="button" class="btn-control-action btn-team-open-ws" data-team="${esc(tm.team_id)}" style="font-size:0.74rem; padding:5px 10px; background:#059669;">
              🌐 Open Shared Workspace
            </button>
            <button type="button" class="btn-student-nav btn-team-rename" data-team="${esc(tm.team_id)}" data-name="${esc(tm.team_name)}" style="font-size:0.74rem; padding:5px 8px;">
              ✏️ Rename
            </button>
            <button type="button" class="btn-student-nav btn-team-delete" data-team="${esc(tm.team_id)}" style="font-size:0.74rem; padding:5px 8px; color:#dc2626; border-color:#fecaca;">
              🗑️
            </button>
          </div>
        </div>

        <!-- Inline Quick Topic & PI Editor on Team Card -->
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px; margin-bottom:12px; display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
          <span style="font-size:0.72rem; font-weight:800; color:#475569;">🎯 Topic:</span>
          <input type="text" class="form-input inp-card-team-topic" data-team="${esc(tm.team_id)}" value="${esc(tm.topic_title)}" placeholder="Write or update team topic..." style="flex:1; min-width:160px; font-size:0.78rem; padding:4px 8px;">
          <button type="button" class="btn-student-nav btn-card-save-topic" data-team="${esc(tm.team_id)}" style="font-size:0.72rem; padding:4px 10px; background:#4f46e5; color:#ffffff; border-color:#4f46e5;">
            💾 Save Topic
          </button>
        </div>

        <!-- Team Members List -->
        <div style="margin-bottom:12px;">
          <div style="font-size:0.75rem; font-weight:800; color:#475569; text-transform:uppercase; margin-bottom:6px;">Team Members:</div>
          ${tm.members.length ? `
            <div style="display:flex; flex-direction:column; gap:6px;">
              ${tm.members.map(m => `
                <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; padding:6px 10px; border-radius:8px; font-size:0.82rem;">
                  <span>👤 <strong>${esc(m.student_name)}</strong> (<code style="color:#4338ca;">${esc(m.student_id)}</code>)</span>
                  <div style="display:flex; gap:6px; align-items:center;">
                    <select class="form-input sel-move-member-team" data-sid="${esc(m.student_id)}" data-from="${esc(tm.team_id)}" style="width:auto; font-size:0.73rem; padding:2px 6px;">
                      <option value="">Move to team...</option>
                      ${state.teams.filter(other => other.team_id !== tm.team_id).map(other =>
                        `<option value="${esc(other.team_id)}">${esc(other.team_id)} (${esc(other.team_name)})</option>`
                      ).join("")}
                    </select>
                    <button type="button" class="btn-student-nav btn-remove-team-member" data-team="${esc(tm.team_id)}" data-sid="${esc(m.student_id)}" style="font-size:0.72rem; padding:2px 8px; color:#dc2626;">
                      ✕ Remove
                    </button>
                  </div>
                </div>
              `).join("")}
            </div>
          ` : `<div style="font-size:0.8rem; color:#94a3b8; font-style:italic;">No students assigned yet.</div>`}
        </div>

        <!-- Add Unassigned Student to this Team -->
        <div style="display:flex; gap:8px; align-items:center; border-top:1px dashed #e2e8f0; padding-top:10px;">
          <select class="form-input sel-add-student-to-team" data-team="${esc(tm.team_id)}" style="font-size:0.78rem; padding:5px 8px;">
            <option value="">+ Add unassigned student from ${esc(tm.lab_group)}...</option>
            ${unassignedInLg.map(u => `<option value="${esc(u.student_id)}">${esc(u.student_id)} — ${esc(u.student_name)}</option>`).join("")}
          </select>
          <button type="button" class="btn-student-nav btn-add-student-to-team" data-team="${esc(tm.team_id)}" style="font-size:0.76rem; padding:5px 12px; white-space:nowrap;">
            ➕ Add to Team
          </button>
        </div>
      </div>
    `).join("");

    // Wire team card actions
    teamsContainer.querySelectorAll(".btn-team-open-ws").forEach(btn => {
      btn.addEventListener("click", () => openSharedTeamWorkspace(btn.getAttribute("data-team")));
    });

    teamsContainer.querySelectorAll(".btn-card-save-topic").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const inp = teamsContainer.querySelector(`.inp-card-team-topic[data-team="${tid}"]`);
        const topicTitle = inp ? inp.value.trim() : "";
        btn.disabled = true;
        btn.innerText = "Saving...";
        try {
          const resp = await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}/assign_topic`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic_title: topicTitle })
          });
          const res = await resp.json();
          if (res.success) {
            notify(`✅ Saved topic for ${tid}: ${res.team.topic_title || 'Cleared'}`);
            await refreshCohortData();
          } else {
            notify(res.error || "Failed to save topic.", "error");
          }
        } catch (e) {
          notify("Error saving topic.", "error");
        } finally {
          btn.disabled = false;
          btn.innerText = "💾 Save Topic";
        }
      });
    });

    teamsContainer.querySelectorAll(".btn-team-rename").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const curName = btn.getAttribute("data-name");
        const newName = window.prompt(`Rename team ${tid}:`, curName);
        if (newName && newName.trim()) {
          const resp = await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ team_name: newName.trim() })
          });
          const res = await resp.json();
          if (res.success) {
            notify(`Renamed ${tid} to ${res.team.team_name}!`);
            await refreshCohortData();
          }
        }
      });
    });

    teamsContainer.querySelectorAll(".btn-team-delete").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const resp = await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}`, { method: "DELETE" });
        const res = await resp.json();
        if (res.success) {
          notify(`Archived team ${tid} and returned its members to Unassigned.`);
          await refreshCohortData();
        }
      });
    });

    teamsContainer.querySelectorAll(".btn-remove-team-member").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const sid = btn.getAttribute("data-sid");
        const resp = await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}/members/${encodeURIComponent(sid)}`, {
          method: "DELETE"
        });
        const res = await resp.json();
        if (res.success) {
          notify(`Removed student ${sid} from ${tid}.`);
          await refreshCohortData();
        }
      });
    });

    teamsContainer.querySelectorAll(".sel-move-member-team").forEach(sel => {
      sel.addEventListener("change", async () => {
        const targetTid = sel.value;
        const sid = sel.getAttribute("data-sid");
        if (!targetTid || !sid) return;
        const resp = await cohortApiFetch("/api/faculty/teams/move_student", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: sid, target_team_id: targetTid })
        });
        const res = await resp.json();
        if (res.success) {
          notify(`Moved student ${sid} to team ${targetTid}!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Move failed.", "error");
        }
      });
    });

    teamsContainer.querySelectorAll(".btn-add-student-to-team").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const sel = teamsContainer.querySelector(`.sel-add-student-to-team[data-team="${tid}"]`);
        const sid = sel ? sel.value : "";
        if (!sid) {
          notify("Select an unassigned student first.", "warning");
          return;
        }
        const resp = await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}/members`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: sid, allow_move: false })
        });
        const res = await resp.json();
        if (res.success) {
          notify(`Added ${sid} to ${tid}!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Could not add student to team.", "error");
        }
      });
    });
  }

  // ============================================================================
  // 5 & 6. PI / SUPERVISOR ASSIGNMENT & PROJECT TOPIC ASSIGNMENT
  // ============================================================================
  function wirePiAndTopicControls() {
    const btnRegisterPi = document.getElementById("btn-register-new-pi");
    if (btnRegisterPi) {
      btnRegisterPi.addEventListener("click", async () => {
        const name = (document.getElementById("new-pi-name")?.value || "").trim();
        const email = (document.getElementById("new-pi-email")?.value || "").trim();
        const dept = (document.getElementById("new-pi-dept")?.value || "").trim();
        if (!name) {
          notify("Enter the PI / Supervisor's full name.", "warning");
          return;
        }
        const resp = await cohortApiFetch("/api/faculty/pis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, department: dept || "Biotechnology & Genetic Engineering" })
        });
        const res = await resp.json();
        if (res.success) {
          document.getElementById("new-pi-name").value = "";
          document.getElementById("new-pi-email").value = "";
          notify(`Registered PI ${res.pi.name} (${res.pi.pi_id})!`);
          await refreshCohortData();
        } else {
          notify(res.error || "Could not add PI.", "error");
        }
      });
    }
  }

  function renderPiAndTopicsPanel() {
    const tbody = document.getElementById("pi-topics-teams-tbody");
    if (!tbody) return;

    if (!state.teams.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:24px;">No project teams created yet. Create teams in Step 4 first.</td></tr>`;
      return;
    }

    tbody.innerHTML = state.teams.map(tm => `
      <tr>
        <td>
          <strong style="font-family:monospace; color:#4338ca;">${esc(tm.team_id)}</strong>
          <div style="font-size:0.8rem; font-weight:700; color:#0f172a;">${esc(tm.team_name)}</div>
          <span class="status-pill" style="background:#e0e7ff; color:#3730a3; font-size:0.68rem;">${esc(tm.lab_group)} • ${tm.member_count} student(s)</span>
        </td>
        <td style="font-size:0.78rem; color:#334155;">
          ${tm.members.length ? tm.members.map(m => `${esc(m.student_name)} (<code>${esc(m.student_id)}</code>)`).join("<br>") : "<em>No students</em>"}
        </td>
        <td>
          <select class="form-input sel-team-pi-assign" data-team="${esc(tm.team_id)}" style="font-size:0.8rem; padding:6px 8px;">
            <option value="">-- Unassigned --</option>
            ${state.pis.map(p => `<option value="${esc(p.pi_id)}" ${tm.pi_id === p.pi_id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}
          </select>
        </td>
        <td>
          <input type="text" class="form-input inp-team-topic-title" data-team="${esc(tm.team_id)}"
                 value="${esc(tm.topic_title)}"
                 placeholder="Enter official project topic title..."
                 style="font-size:0.82rem; font-weight:700; margin-bottom:4px;">
          <input type="text" class="form-input inp-team-topic-desc" data-team="${esc(tm.team_id)}"
                 value="${esc(tm.topic_description)}"
                 placeholder="Optional short topic scope/description or category..."
                 style="font-size:0.76rem; color:#475569;">
        </td>
        <td>
          <span class="status-pill ${tm.topic_title && tm.pi_id ? 'status-grant-ready' : 'status-major-rev'}">
            ${tm.topic_title && tm.pi_id ? "✅ Ready" : "⚠️ Incomplete"}
          </span>
        </td>
        <td>
          <div style="display:flex; gap:6px; flex-direction:column;">
            <button type="button" class="btn-control-action btn-save-pi-topic" data-team="${esc(tm.team_id)}" style="font-size:0.75rem; padding:6px 10px;">
              💾 Save PI & Topic
            </button>
            <button type="button" class="btn-student-nav btn-open-ws-from-pitopic" data-team="${esc(tm.team_id)}" style="font-size:0.74rem; padding:4px 8px;">
              🌐 Open Workspace
            </button>
          </div>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll(".btn-save-pi-topic").forEach(btn => {
      btn.addEventListener("click", async () => {
        const tid = btn.getAttribute("data-team");
        const piSel = tbody.querySelector(`.sel-team-pi-assign[data-team="${tid}"]`);
        const topTitleIn = tbody.querySelector(`.inp-team-topic-title[data-team="${tid}"]`);
        const topDescIn = tbody.querySelector(`.inp-team-topic-desc[data-team="${tid}"]`);

        const piId = piSel ? piSel.value : "";
        const topicTitle = topTitleIn ? topTitleIn.value.trim() : "";
        const topicDesc = topDescIn ? topDescIn.value.trim() : "";

        btn.disabled = true;
        btn.innerText = "Saving...";
        try {
          await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}/assign_pi`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pi_id: piId })
          });
          await cohortApiFetch(`/api/faculty/teams/${encodeURIComponent(tid)}/assign_topic`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic_title: topicTitle, topic_description: topicDesc })
          });
          notify(`✅ Saved PI & Topic assignment for team ${tid}!`);
          await refreshCohortData();
        } catch (e) {
          notify("Error saving PI/Topic.", "error");
        } finally {
          btn.disabled = false;
          btn.innerText = "💾 Save PI & Topic";
        }
      });
    });

    tbody.querySelectorAll(".btn-open-ws-from-pitopic").forEach(btn => {
      btn.addEventListener("click", () => openSharedTeamWorkspace(btn.getAttribute("data-team")));
    });
  }

  // ============================================================================
  // 7. SHARED TEAM WORKSPACES & PI SUPERVISED TEAMS VIEW
  // ============================================================================
  function wireSharedWorkspaceControls() {
    const selTeam = document.getElementById("workspace-team-selector");
    if (selTeam) {
      selTeam.addEventListener("change", () => {
        if (selTeam.value) loadTeamWorkspaceDetail(selTeam.value);
      });
    }

    const filterPi = document.getElementById("workspace-pi-filter");
    if (filterPi) {
      filterPi.addEventListener("change", () => {
        renderWorkspacesSelectorPanel();
      });
    }

    const btnSaveWs = document.getElementById("btn-fac-save-team-workspace");
    if (btnSaveWs) {
      btnSaveWs.addEventListener("click", async () => {
        const tid = state.selectedWorkspaceTeamId;
        if (!tid) return;
        const notes = document.getElementById("fac-ws-shared-notes")?.value || "";
        const info = document.getElementById("fac-ws-important-info")?.value || "";
        const piGuidance = document.getElementById("fac-ws-pi-guidance")?.value || "";
        const msg = document.getElementById("fac-ws-update-msg")?.value || "";

        btnSaveWs.disabled = true;
        btnSaveWs.innerText = "⏳ Saving to Shared Team Workspace...";
        try {
          const resp = await cohortApiFetch(`/api/teams/${encodeURIComponent(tid)}/workspace`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              shared_notes: notes,
              important_info: info,
              pi_feedback_notes: piGuidance,
              update_message: msg || "Faculty/PI updated shared workspace notes & guidance"
            })
          });
          const res = await resp.json();
          if (res.success && res.workspace) {
            state.activeWorkspace = res.workspace;
            if (document.getElementById("fac-ws-update-msg")) {
              document.getElementById("fac-ws-update-msg").value = "";
            }
            renderActiveTeamWorkspace(res.workspace);
            notify(`✅ Shared Team Workspace (${tid}) saved! All team members & PI now see this update.`);
          } else {
            notify(res.error || "Failed to save workspace.", "error");
          }
        } catch (e) {
          notify("Network error saving shared workspace.", "error");
        } finally {
          btnSaveWs.disabled = false;
          btnSaveWs.innerText = "💾 Save Shared Workspace & Post Update";
        }
      });
    }

    const btnEvalTeamProposal = document.getElementById("btn-fac-eval-team-proposal");
    if (btnEvalTeamProposal) {
      btnEvalTeamProposal.addEventListener("click", () => {
        if (!state.activeWorkspace) return;
        const members = state.activeWorkspace.members || [];
        if (members.length > 0 && typeof window.loadStudentDraft === "function") {
          window.loadStudentDraft(members[0].student_id);
          if (typeof window.switchFacultyView === "function") {
            window.switchFacultyView("grading");
          }
        } else if (state.activeWorkspace.proposal_draft && typeof window.applyStudentDraftToUI === "function") {
          window.applyStudentDraftToUI(state.activeWorkspace.proposal_draft);
          if (typeof window.switchFacultyView === "function") {
            window.switchFacultyView("grading");
          }
        }
      });
    }
  }

  function openSharedTeamWorkspace(teamId) {
    state.selectedWorkspaceTeamId = teamId;
    if (typeof window.switchFacultyView === "function") {
      window.switchFacultyView("cohort");
    }
    switchCohortSubTab("workspaces");
    loadTeamWorkspaceDetail(teamId);
  }
  window.openSharedTeamWorkspace = openSharedTeamWorkspace;

  function renderWorkspacesSelectorPanel() {
    const piFilter = document.getElementById("workspace-pi-filter");
    if (piFilter && !piFilter._populated) {
      piFilter.innerHTML = `<option value="">All PIs / Supervisors (Coordinator View)</option>` +
        state.pis.map(p => `<option value="${esc(p.pi_id)}">👨‍🔬 My Supervised Teams: ${esc(p.name)}</option>`).join("");
      piFilter._populated = true;
    }

    const activePiFilter = piFilter ? piFilter.value : "";
    const filteredTeams = activePiFilter
      ? state.teams.filter(t => t.pi_id === activePiFilter)
      : state.teams;

    // Render PI Supervised Teams summary table (Section 11)
    const tbody = document.getElementById("pi-supervised-teams-tbody");
    if (tbody) {
      if (!filteredTeams.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:18px;">No supervised teams match the selected PI filter.</td></tr>`;
      } else {
        tbody.innerHTML = filteredTeams.map(tm => `
          <tr style="${tm.team_id === state.selectedWorkspaceTeamId ? 'background:#eef2ff;' : ''}">
            <td><strong>${esc(tm.team_name)}</strong> (<code>${esc(tm.team_id)}</code>)</td>
            <td><span class="status-pill" style="background:#e0e7ff; color:#3730a3;">${esc(tm.lab_group)}</span></td>
            <td>${esc(tm.pi_name || "Unassigned")}</td>
            <td><strong>${esc(tm.topic_title || "Unassigned")}</strong></td>
            <td>${tm.members.map(m => esc(m.student_name)).join(", ") || "No members"}</td>
            <td>
              <button type="button" class="btn-control-action btn-select-ws-row" data-team="${esc(tm.team_id)}" style="font-size:0.75rem; padding:5px 10px;">
                🌐 Open Shared Workspace
              </button>
            </td>
          </tr>
        `).join("");

        tbody.querySelectorAll(".btn-select-ws-row").forEach(btn => {
          btn.addEventListener("click", () => {
            loadTeamWorkspaceDetail(btn.getAttribute("data-team"));
          });
        });
      }
    }

    const selTeam = document.getElementById("workspace-team-selector");
    if (selTeam) {
      selTeam.innerHTML = filteredTeams.map(t =>
        `<option value="${esc(t.team_id)}">${esc(t.team_id)} — ${esc(t.team_name)} (${esc(t.lab_group)} • PI: ${esc(t.pi_name || 'Unassigned')})</option>`
      ).join("");
      if (!state.selectedWorkspaceTeamId && filteredTeams.length > 0) {
        state.selectedWorkspaceTeamId = filteredTeams[0].team_id;
      }
      if (state.selectedWorkspaceTeamId) {
        selTeam.value = state.selectedWorkspaceTeamId;
        loadTeamWorkspaceDetail(state.selectedWorkspaceTeamId);
      }
    }
  }

  async function loadTeamWorkspaceDetail(teamId) {
    if (!teamId) return;
    state.selectedWorkspaceTeamId = teamId;
    const selTeam = document.getElementById("workspace-team-selector");
    if (selTeam) selTeam.value = teamId;

    try {
      const resp = await cohortApiFetch(`/api/teams/${encodeURIComponent(teamId)}/workspace`);
      if (resp.ok) {
        const res = await resp.json();
        if (res.success && res.workspace) {
          state.activeWorkspace = res.workspace;
          renderActiveTeamWorkspace(res.workspace);
        }
      }
    } catch (e) {}
  }

  function renderActiveTeamWorkspace(ws) {
    const container = document.getElementById("active-team-workspace-box");
    if (!container || !ws) return;
    container.style.display = "block";

    const setEl = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val || "";
    };
    setEl("fac-ws-header-title", `${ws.team_name} (${ws.team_id})`);
    setEl("fac-ws-labgroup", ws.lab_group || "—");
    setEl("fac-ws-pi", ws.pi_name || "Unassigned");
    setEl("fac-ws-topic", ws.topic_title || "Unassigned");
    setEl("fac-ws-updated", `Last updated by ${ws.last_updated_by || 'System'} at ${ws.last_updated_at || 'Recently'}`);

    const membersEl = document.getElementById("fac-ws-members-chips");
    if (membersEl) {
      membersEl.innerHTML = (ws.members || []).length
        ? ws.members.map(m => `<span class="status-pill" style="background:#e0e7ff; color:#312e81; padding:4px 10px;">👤 ${esc(m.student_name)} (<code>${esc(m.student_id)}</code>)</span>`).join(" ")
        : `<span style="color:#94a3b8;">No students assigned to this team yet.</span>`;
    }

    const notesEl = document.getElementById("fac-ws-shared-notes");
    if (notesEl) notesEl.value = ws.shared_notes || "";

    const infoEl = document.getElementById("fac-ws-important-info");
    if (infoEl) infoEl.value = ws.important_info || "";

    const piEl = document.getElementById("fac-ws-pi-guidance");
    if (piEl) piEl.value = ws.pi_feedback_notes || "";

    const draft = ws.proposal_draft || {};
    setEl("fac-ws-proposal-title", draft.title || ws.topic_title || "Untitled Team Proposal");
    setEl("fac-ws-proposal-completion", `${(ws.summary && ws.summary.completion_percentage) || 0}% Complete (${(ws.summary && ws.summary.word_count) || 0} words)`);

    const feedBox = document.getElementById("fac-ws-updates-feed");
    if (feedBox) {
      const feed = ws.updates_feed || [];
      if (!feed.length) {
        feedBox.innerHTML = `<div style="color:#94a3b8; font-size:0.8rem;">No activity updates logged yet.</div>`;
      } else {
        feedBox.innerHTML = feed.slice(0, 15).map(item => `
          <div style="background:#f8fafc; border-left:3px solid #4f46e5; padding:8px 12px; border-radius:6px; margin-bottom:8px; font-size:0.8rem;">
            <div style="display:flex; justify-content:space-between; color:#475569; font-size:0.74rem; margin-bottom:2px;">
              <strong>👤 ${esc(item.author_name)} (${esc(item.author_role.toUpperCase())})</strong>
              <span>🕒 ${esc(item.timestamp)}</span>
            </div>
            <div style="color:#0f172a; font-weight:600;">${esc(item.message)}</div>
          </div>
        `).join("");
      }
    }
  }

  // ============================================================================
  // 8. AUDIT HISTORY
  // ============================================================================
  async function loadAuditHistoryPanel() {
    try {
      const q = new URLSearchParams({ semester: state.semester, course_id: state.course_id });
      const resp = await cohortApiFetch(`/api/faculty/audit_history?${q.toString()}`);
      if (resp.ok) {
        const res = await resp.json();
        if (res.success) {
          state.auditHistory = res.history || [];
          renderAuditHistoryTable(state.auditHistory);
        }
      }
    } catch (e) {}
  }

  function renderAuditHistoryTable(history) {
    const tbody = document.getElementById("cohort-audit-history-tbody");
    if (!tbody) return;
    if (!history || !history.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:24px;">No audit events recorded yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = history.map(h => `
      <tr>
        <td style="font-family:monospace; font-size:0.75rem; color:#475569;">${esc(h.timestamp)}</td>
        <td><span class="status-pill" style="background:#eef2ff; color:#3730a3;">${esc(h.event_type)}</span></td>
        <td><strong>${esc(h.summary)}</strong></td>
        <td>${esc(h.student_id || "—")} / ${esc(h.team_id || "—")}</td>
        <td><code>${esc(h.old_value || "—")}</code> ➔ <code>${esc(h.new_value || "—")}</code></td>
        <td>${esc(h.actor)}</td>
      </tr>
    `).join("");
  }

  document.addEventListener("DOMContentLoaded", () => {
    initFacultyCohortExtension();
  });
})();
