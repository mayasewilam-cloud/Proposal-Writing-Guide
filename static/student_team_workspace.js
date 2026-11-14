/**
 * BioWriter Student Studio — My Project & Shared Team Workspace Controller.
 * Connects the Student Portal (index.html) to the Team ID-scoped Shared Team Workspace
 * so all students assigned to the same team see and edit the exact same workspace and proposal data.
 */

(function () {
  let activeStudentProject = null;
  let activeTeamWorkspace = null;

  function esc(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function toast(msg) {
    if (typeof window.showToast === "function") {
      window.showToast(msg);
    }
  }

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

  function ensureDefaultCohortDbInLocalStorage() {
    const ts = nowStamp();
    const def = {
      active_semester: "Fall 2026",
      active_course_id: "BT_301",
      pis: {
        "PI-RANIA": { pi_id: "PI-RANIA", name: "Dr. Rania Hassan", email: "r.hassan@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-AHMED": { pi_id: "PI-AHMED", name: "Dr. Ahmed Hassan", email: "a.hassan@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-TARIK": { pi_id: "PI-TARIK", name: "Dr. Tarek El-Sayed", email: "t.elsayed@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-TAREK": { pi_id: "PI-TAREK", name: "Dr. Tarek Mansour", email: "t.mansour@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-MONA": { pi_id: "PI-MONA", name: "Dr. Mona Abdelrahman", email: "m.abdelrahman@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-NADIA": { pi_id: "PI-NADIA", name: "Dr. Nadia El-Sayed", email: "n.elsayed@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" },
        "PI-KARIM": { pi_id: "PI-KARIM", name: "Dr. Karim Fawzy", email: "k.fawzy@nu.edu.eg", department: "Biotechnology & Genetic Engineering", role: "pi" }
      },
      students: {
        "13989": { student_id: "13989", student_name: "Maya Abdelrazek", email: "m.abdelrazek@nu.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301" },
        "20230001": { student_id: "20230001", student_name: "Ahmed Ali", email: "ahmed.ali@student.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301" },
        "20230002": { student_id: "20230002", student_name: "Sara Mohamed", email: "sara.mohamed@student.edu.eg", lab_group: "L1", team_id: "L1-T1", semester: "Fall 2026", course_id: "BT_301" },
        "20230003": { student_id: "20230003", student_name: "Mariam Hassan", email: "mariam.hassan@student.edu.eg", lab_group: "L1", team_id: "L1-T2", semester: "Fall 2026", course_id: "BT_301" },
        "20230004": { student_id: "20230004", student_name: "Karim Adel", email: "karim.adel@student.edu.eg", lab_group: "L1", team_id: "L1-T2", semester: "Fall 2026", course_id: "BT_301" },
        "20230005": { student_id: "20230005", student_name: "Omar Khaled", email: "omar.khaled@student.edu.eg", lab_group: "L1", team_id: "", semester: "Fall 2026", course_id: "BT_301" },
        "20230006": { student_id: "20230006", student_name: "Nour Hany", email: "nour.hany@student.edu.eg", lab_group: "L1", team_id: "", semester: "Fall 2026", course_id: "BT_301" },
        "20230007": { student_id: "20230007", student_name: "Youssef Tarek", email: "youssef.tarek@student.edu.eg", lab_group: "L2", team_id: "L2-T1", semester: "Fall 2026", course_id: "BT_301" }
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
          status: "active"
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
          status: "active"
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
          status: "active"
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
      }
    };
    try {
      const raw = localStorage.getItem(COHORT_DB_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && parsed.students && Object.keys(parsed.students).length > 0) {
          return parsed;
        }
      }
      localStorage.setItem(COHORT_DB_KEY, JSON.stringify(def));
    } catch (e) {}
    return def;
  }

  function getLocalStudentContext(studentId) {
    const cleanId = String(studentId || localStorage.getItem("biowriter_student_id") || "").trim().toUpperCase();
    if (!cleanId) return null;
    try {
      const db = ensureDefaultCohortDbInLocalStorage();
      const st = (db.students || {})[cleanId];
      if (st) {
        const tid = st.team_id || "";
        const team = (tid && db.teams && db.teams[tid] && db.teams[tid].status !== "archived") ? db.teams[tid] : null;
        const piObj = (team && team.pi_id && db.pis) ? db.pis[team.pi_id] : null;
        const members = team ? (team.member_ids || []).map(sid => {
          const m = (db.students || {})[sid] || {};
          return {
            student_id: sid,
            student_name: m.student_name || sid,
            email: m.email || "",
            lab_group: m.lab_group || ""
          };
        }) : [];

        const myProj = {
          student_id: cleanId,
          student_name: st.student_name || cleanId,
          course_id: st.course_id || db.active_course_id || "BT_301",
          semester: st.semester || db.active_semester || "Fall 2026",
          lab_group: st.lab_group || "Unassigned",
          team_id: team ? tid : "",
          team_name: team ? (team.team_name || tid) : "Unassigned",
          pi_id: team ? (team.pi_id || "") : "",
          pi_name: piObj ? piObj.name : "Unassigned",
          topic_title: team && team.topic_title ? team.topic_title : "Unassigned",
          topic_description: team && team.topic_description ? team.topic_description : "",
          members: members
        };

        let ws = null;
        if (team) {
          const rawWs = (db.team_workspaces || {})[tid] || {};
          ws = {
            team_id: tid,
            team_name: team.team_name || tid,
            lab_group: team.lab_group || "",
            pi_name: piObj ? piObj.name : "Unassigned",
            topic_title: team.topic_title || "",
            members: members,
            shared_notes: rawWs.shared_notes || "",
            important_info: rawWs.important_info || "",
            pi_feedback_notes: rawWs.pi_feedback_notes || "",
            proposal_draft: rawWs.proposal_draft || {},
            updates_feed: rawWs.updates_feed || [],
            last_updated_at: rawWs.last_updated_at || "Recently",
            last_updated_by: rawWs.last_updated_by || "Team"
          };
        }
        return { my_project: myProj, workspace: ws };
      }
    } catch (e) {}
    return null;
  }

  function saveLocalTeamWorkspaceFromStudent(teamId, payload) {
    try {
      const raw = localStorage.getItem(COHORT_DB_KEY);
      if (!raw) return null;
      const db = JSON.parse(raw);
      const team = (db.teams || {})[teamId];
      if (!team) return null;
      db.team_workspaces = db.team_workspaces || {};
      const ws = db.team_workspaces[teamId] || {
        team_id: teamId,
        shared_notes: "",
        important_info: "",
        pi_feedback_notes: "",
        proposal_draft: {},
        updates_feed: []
      };
      const ts = nowStamp();
      const authorName = (window.currentUser && window.currentUser.student_name) || localStorage.getItem("biowriter_student_name") || "Team Member";
      const authorId = (window.currentUser && window.currentUser.student_id) || localStorage.getItem("biowriter_student_id") || "student";

      if (payload.shared_notes !== undefined) ws.shared_notes = payload.shared_notes;
      if (payload.important_info !== undefined) ws.important_info = payload.important_info;
      if (payload.proposal_draft && typeof payload.proposal_draft === "object") {
        ws.proposal_draft = { ...(ws.proposal_draft || {}), ...payload.proposal_draft };
      }
      ws.last_updated_at = ts;
      ws.last_updated_by = `${authorName} (${authorId})`;
      ws.updates_feed = ws.updates_feed || [];
      ws.updates_feed.unshift({
        timestamp: ts,
        author_id: authorId,
        author_name: authorName,
        author_role: "student",
        action: "workspace_updated",
        message: payload.update_message || "Updated shared team workspace & proposal"
      });
      db.team_workspaces[teamId] = ws;
      localStorage.setItem(COHORT_DB_KEY, JSON.stringify(db));

      // Also sync to every teammate's bt301_student_draft_<SID>
      for (const sid of (team.member_ids || [])) {
        try {
          const dKey = "bt301_student_draft_" + sid;
          const dRaw = localStorage.getItem(dKey);
          const draft = dRaw ? JSON.parse(dRaw) : { student_id: sid };
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
      return ws;
    } catch (e) {
      return null;
    }
  }

  async function fetchAndRenderStudentTeamContext(studentId) {
    const panel = document.getElementById("student-my-project-panel");
    if (!panel) return;

    if (!isStaticEnv()) {
      try {
        const resp = await fetch("/api/student/my_project");
        if (resp.ok) {
          const data = await resp.json();
          if (data.success && data.my_project) {
            activeStudentProject = data.my_project;
            activeTeamWorkspace = data.workspace || null;
            renderStudentMyProjectAndWorkspace(activeStudentProject, activeTeamWorkspace);
            syncOfficialTeamToProposalForm(activeStudentProject, activeTeamWorkspace);
            return;
          }
        }
      } catch (e) {
        // Fall through to client-side localStorage Cohort DB
      }
    }

    const localCtx = getLocalStudentContext(studentId);
    if (localCtx && localCtx.my_project) {
      activeStudentProject = localCtx.my_project;
      activeTeamWorkspace = localCtx.workspace || null;
      renderStudentMyProjectAndWorkspace(activeStudentProject, activeTeamWorkspace);
      syncOfficialTeamToProposalForm(activeStudentProject, activeTeamWorkspace);
    } else {
      panel.style.display = "none";
    }
  }
  window.fetchAndRenderStudentTeamContext = fetchAndRenderStudentTeamContext;

  function syncOfficialTeamToProposalForm(myProj, ws) {
    if (!myProj) return;
    if (typeof window.projectState === "object" && window.projectState) {
      if (myProj.members && myProj.members.length > 0) {
        const officialRoster = myProj.members.map((m, idx) => ({
          name: m.student_name,
          id: m.student_id,
          email: m.email || "",
          role: idx === 0 ? "Principal Investigator" : "Co-Investigator"
        }));
        window.projectState.team_members = officialRoster;
        window.projectState.team_roster = officialRoster;
        if (typeof window.renderTeamRosterTable === "function") {
          window.renderTeamRosterTable();
        }
      }
      if (myProj.topic_title && myProj.topic_title !== "Unassigned" && !window.projectState.title) {
        window.projectState.title = myProj.topic_title;
        const titleIn = document.getElementById("proposal-title-input");
        if (titleIn && !titleIn.value) {
          titleIn.value = myProj.topic_title;
        }
      }
    }
  }

  function renderStudentMyProjectAndWorkspace(myProj, ws) {
    const panel = document.getElementById("student-my-project-panel");
    if (!panel) return;
    panel.style.display = "block";

    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val || "—";
    };

    setTxt("st-proj-course", `${myProj.course_id || "BT_301"} • ${myProj.semester || "Fall 2026"}`);
    setTxt("st-proj-labgroup", myProj.lab_group || "Unassigned");
    setTxt("st-proj-team", myProj.team_id ? `${myProj.team_name} (${myProj.team_id})` : "Unassigned");
    setTxt("st-proj-pi", myProj.pi_name || "Unassigned");
    setTxt("st-proj-topic", myProj.topic_title || "Unassigned");

    const membersWrap = document.getElementById("st-proj-members-list");
    if (membersWrap) {
      if (myProj.members && myProj.members.length) {
        membersWrap.innerHTML = myProj.members.map(m =>
          `<span style="background:#e0e7ff; color:#312e81; font-size:0.76rem; font-weight:700; padding:3px 10px; border-radius:999px; border:1px solid #c7d2fe;">👤 ${esc(m.student_name)} (<code>${esc(m.student_id)}</code>)</span>`
        ).join(" ");
      } else {
        membersWrap.innerHTML = `<span style="color:#64748b; font-size:0.78rem;">Not yet assigned to a project team by Faculty.</span>`;
      }
    }

    const wsBody = document.getElementById("st-shared-workspace-body");
    const unassignedNotice = document.getElementById("st-unassigned-workspace-notice");

    if (!myProj.team_id || !ws) {
      if (wsBody) wsBody.style.display = "none";
      if (unassignedNotice) unassignedNotice.style.display = "block";
      return;
    }

    if (unassignedNotice) unassignedNotice.style.display = "none";
    if (wsBody) wsBody.style.display = "block";

    setTxt("st-ws-team-badge", `Team ID: ${ws.team_id}`);
    setTxt("st-ws-last-updated", `Last saved by ${ws.last_updated_by || "Team"} • ${ws.last_updated_at || "Recently"}`);

    const notesIn = document.getElementById("st-ws-shared-notes");
    if (notesIn) notesIn.value = ws.shared_notes || "";

    const infoIn = document.getElementById("st-ws-important-info");
    if (infoIn) infoIn.value = ws.important_info || "";

    const piBanner = document.getElementById("st-ws-pi-guidance-box");
    const piText = document.getElementById("st-ws-pi-guidance-text");
    if (piBanner && piText) {
      if (ws.pi_feedback_notes && ws.pi_feedback_notes.trim()) {
        piBanner.style.display = "block";
        piText.innerText = ws.pi_feedback_notes;
      } else {
        piBanner.style.display = "none";
      }
    }

    const feedWrap = document.getElementById("st-ws-updates-feed");
    if (feedWrap) {
      const feed = ws.updates_feed || [];
      if (!feed.length) {
        feedWrap.innerHTML = `<div style="font-size:0.78rem; color:#64748b; font-style:italic;">No team updates posted yet. Save shared notes or post an update to share with your teammates and PI!</div>`;
      } else {
        feedWrap.innerHTML = feed.slice(0, 10).map(f => `
          <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:3px solid #4f46e5; border-radius:6px; padding:8px 10px; margin-bottom:6px; font-size:0.78rem;">
            <div style="display:flex; justify-content:space-between; color:#475569; font-size:0.72rem; margin-bottom:2px;">
              <strong>👤 ${esc(f.author_name)} (${esc((f.author_role || 'member').toUpperCase())})</strong>
              <span>🕒 ${esc(f.timestamp)}</span>
            </div>
            <div style="color:#0f172a; font-weight:600;">${esc(f.message)}</div>
          </div>
        `).join("");
      }
    }
  }

  function wireStudentTeamWorkspaceEvents() {
    const btnToggleWs = document.getElementById("btn-toggle-student-team-ws");
    const wsCollapse = document.getElementById("st-team-ws-collapsible");
    if (btnToggleWs && wsCollapse) {
      btnToggleWs.addEventListener("click", () => {
        const isHidden = wsCollapse.style.display === "none";
        wsCollapse.style.display = isHidden ? "block" : "none";
        btnToggleWs.innerText = isHidden ? "▾ Hide Shared Team Workspace" : "🌐 Open Shared Team Workspace";
      });
    }

    const btnSaveWs = document.getElementById("btn-st-save-team-workspace");
    if (btnSaveWs) {
      btnSaveWs.addEventListener("click", async () => {
        if (!activeStudentProject || !activeStudentProject.team_id) {
          toast("You must be assigned to a team to save to the Shared Team Workspace.");
          return;
        }
        const tid = activeStudentProject.team_id;
        const notes = document.getElementById("st-ws-shared-notes")?.value || "";
        const info = document.getElementById("st-ws-important-info")?.value || "";
        const msg = document.getElementById("st-ws-update-msg")?.value || "";

        if (typeof window.scrapeAllDynamicTablesToState === "function") {
          window.scrapeAllDynamicTablesToState();
        }

        const payload = {
          shared_notes: notes,
          important_info: info,
          update_message: msg || "Updated shared team workspace & proposal",
          proposal_draft: typeof window.projectState === "object" ? window.projectState : undefined
        };

        btnSaveWs.disabled = true;
        btnSaveWs.innerText = "⏳ Syncing to Team Workspace...";
        try {
          if (!isStaticEnv()) {
            try {
              const resp = await fetch(`/api/teams/${encodeURIComponent(tid)}/workspace`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
              });
              const res = await resp.json();
              if (res.success && res.workspace) {
                activeTeamWorkspace = res.workspace;
                const msgIn = document.getElementById("st-ws-update-msg");
                if (msgIn) msgIn.value = "";
                renderStudentMyProjectAndWorkspace(activeStudentProject, activeTeamWorkspace);
                toast(`✅ Saved to Shared Team Workspace (${tid})! All teammates & your PI now see this update.`);
                return;
              }
            } catch (e) {
              // Fall through to localStorage sync
            }
          }

          const localWs = saveLocalTeamWorkspaceFromStudent(tid, payload);
          if (localWs) {
            activeTeamWorkspace = localWs;
            const msgIn = document.getElementById("st-ws-update-msg");
            if (msgIn) msgIn.value = "";
            renderStudentMyProjectAndWorkspace(activeStudentProject, activeTeamWorkspace);
            toast(`✅ Saved to Shared Team Workspace (${tid})! All teammates & your PI now see this update.`);
          } else {
            toast("Could not save team workspace.");
          }
        } finally {
          btnSaveWs.disabled = false;
          btnSaveWs.innerText = "💾 Save Shared Team Notes & Sync Proposal";
        }
      });
    }

    const btnRefreshWs = document.getElementById("btn-st-refresh-team-workspace");
    if (btnRefreshWs) {
      btnRefreshWs.addEventListener("click", async () => {
        await fetchAndRenderStudentTeamContext();
        if (activeTeamWorkspace && activeTeamWorkspace.proposal_draft && typeof window.projectState === "object") {
          Object.assign(window.projectState, activeTeamWorkspace.proposal_draft);
          if (typeof window.populateFormFields === "function") {
            window.populateFormFields();
          }
          if (typeof window.updateLiveScore === "function") {
            window.updateLiveScore();
          }
        }
        toast("🔄 Pulled latest Shared Team Workspace & teammate updates!");
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireStudentTeamWorkspaceEvents();

    // Hook into studio.js setAuthenticatedUser and handleLogout so team workspace loads automatically on sign-in
    const origSetAuth = window.setAuthenticatedUser;
    if (typeof origSetAuth === "function") {
      window.setAuthenticatedUser = function (user, draftData) {
        origSetAuth(user, draftData);
        if (user && user.student_id) {
          fetchAndRenderStudentTeamContext(user.student_id);
        }
      };
    }

    const origLogout = window.handleLogout;
    if (typeof origLogout === "function") {
      window.handleLogout = async function () {
        const panel = document.getElementById("student-my-project-panel");
        if (panel) panel.style.display = "none";
        activeStudentProject = null;
        activeTeamWorkspace = null;
        return await origLogout();
      };
    }
  });
})();
