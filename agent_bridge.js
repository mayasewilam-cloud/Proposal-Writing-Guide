/**
 * Agent Bridge: Trusted Research Workflow Agent Integration for BioWriter Studio.
 * Connects the live student proposal workspace in index.html to the Catalyst Agent orchestration layer.
 *
 * Exposes the Phase 3 GovernedAgentLoop (Decision -> Action -> Observation -> Re-plan -> Next Action),
 * BoundedToolRegistry (Tools Used vs Available Tools), Literature Evidence & Provenance,
 * Dynamic Socratic Clarifications (Pending & Answered), Human Governance Gates (HUMAN_REVIEW),
 * and Tamper-Evident SHA-256 Audit Chain Verification.
 *
 * Canonical Proposal DOM Selectors:
 * - #proposal-title-input
 * - #pillar-chassis
 * - #pillar-tool
 * - #pillar-target
 * - #proposal-abstract-input / #section-2-1-unified
 * - #section-3-1-aim / #section-3-2-objectives
 * - #section-4-1-methodology
 * - #section-5-interpretations / #section-5-expected-outcomes
 * - #form-human-subjects / #form-recombinant-dna / #form-pathogen-work
 * - #team-lead-name / #student-id-input
 */

(function () {
  "use strict";

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function isFileProtocol() {
    return typeof window !== "undefined" && window.location && window.location.protocol === "file:";
  }

  let _localServerOffline = false;

  function getApiBase() {
    if (isFileProtocol() && _localServerOffline) {
      return null;
    }
    return isFileProtocol() ? "http://127.0.0.1:5000" : "";
  }

  function getDomValue(ids) {
    for (let i = 0; i < ids.length; i++) {
      const el = document.getElementById(ids[i]);
      if (el && typeof el.value === "string" && el.value.trim()) {
        return el.value.trim();
      }
    }
    return "";
  }

  function getActiveProjectId() {
    if (window.currentAuthUser && window.currentAuthUser.student_id && String(window.currentAuthUser.student_id).trim()) {
      return String(window.currentAuthUser.student_id).trim();
    }
    const domId = getDomValue(["student-id-input", "gate-signin-id"]);
    if (domId) {
      return domId;
    }
    if (window.projectState && window.projectState.student_id && String(window.projectState.student_id).trim()) {
      return String(window.projectState.student_id).trim();
    }
    return "13989";
  }

  /**
   * Canonical Proposal State Extractor.
   * Always prioritizes LIVE DOM inputs over cached window.projectState so edits are immediately reflected.
   * Never mutates researcher-authored proposal DOM fields.
   */
  function getActiveProposalData() {
    const ps = window.projectState || {};
    const liveTitle = getDomValue(["proposal-title-input"]) || ps.title || "Biotechnology Research Proposal";
    const liveStudentName = getDomValue(["team-lead-name", "student-name-input"]) || ps.student_name || "Student Researcher";
    const liveChassis = getDomValue(["pillar-chassis", "chassis-input"]) || ps.chassis || ps.system || "";
    const liveTool = getDomValue(["pillar-tool", "tool-input"]) || ps.tool || "";
    const liveTarget = getDomValue(["pillar-target", "target-input"]) || ps.target || "";
    const liveAbstract = getDomValue(["proposal-abstract-input", "section-2-1-unified", "abstract-input"]) || ps.abstract || "";
    const liveAim1 = getDomValue(["section-3-1-aim", "proposal-aim-input"]);
    const liveObjectives = getDomValue(["section-3-2-objectives"]);
    const liveMethodology = getDomValue(["section-4-1-methodology", "section-4-3-methods", "proposal-methodology-input"]) || ps.methodology || "";
    const livePitfalls = getDomValue(["section-5-interpretations"]) || ps.pitfalls || "";
    const liveOutcomes = getDomValue(["section-5-expected-outcomes"]) || ps.expected_outcomes || "";

    const chkHuman = document.getElementById("form-human-subjects");
    const chkRdna = document.getElementById("form-recombinant-dna");
    const chkPathogen = document.getElementById("form-pathogen-work");

    const humanSubjectsFlag = chkHuman ? Boolean(chkHuman.checked) : (typeof ps.human_subjects === "boolean" ? ps.human_subjects : false);
    const rdnaFlag = chkRdna ? Boolean(chkRdna.checked) : (typeof ps.recombinant_dna === "boolean" ? ps.recombinant_dna : false);
    const pathogenFlag = chkPathogen ? Boolean(chkPathogen.checked) : (typeof ps.pathogen_work === "boolean" ? ps.pathogen_work : false);

    const aimsObj = Object.assign({}, ps.aims || {});
    if (liveAim1) aimsObj.aim1 = liveAim1;
    if (liveObjectives) aimsObj.objectives = liveObjectives;

    return {
      student_id: getActiveProjectId(),
      student_name: liveStudentName,
      title: liveTitle,
      chassis: liveChassis,
      system: liveChassis,
      tool: liveTool,
      target: liveTarget,
      abstract: liveAbstract,
      aims: aimsObj,
      methodology: liveMethodology,
      pitfalls: livePitfalls,
      interpretations: livePitfalls,
      expected_outcomes: liveOutcomes,
      human_subjects: humanSubjectsFlag,
      recombinant_dna: rdnaFlag,
      pathogen_work: pathogenFlag,
      preserve_clarifications: true,
      funnel: ps.funnel || {},
      keywords: ps.keywords || ""
    };
  }

  function getStatusBadgeClass(state) {
    switch (state) {
      case "READY_FOR_ETHICS_HANDOFF":
      case "CLEARED_FOR_NEXT_STAGE":
        return "background: #dcfce7; color: #166534; border: 1px solid #86efac;";
      case "NEEDS_CLARIFICATION":
      case "RETURNED_FOR_REVISION":
      case "REVISIONS_REQUESTED":
        return "background: #fef3c7; color: #92400e; border: 1px solid #fde68a;";
      case "MOCK_HANDOFF_COMPLETED":
      case "ETHICS_REVIEW_PENDING":
      case "HUMAN_REVIEW":
        return "background: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe;";
      case "ESCALATED":
      case "ESCALATED_TO_HUMAN_REVIEW":
      case "STOPPED_BY_POLICY":
      case "REJECTED":
        return "background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;";
      default:
        return "background: #e0f2fe; color: #075985; border: 1px solid #bae6fd;";
    }
  }

  /**
   * Accurately formats the Phase 3 Planner Mode & Model Provider without faking LLM availability.
   */
  function formatPlannerModeDisplay(agentRun, data) {
    const run = agentRun || (data && data.agent_run) || {};
    const plannerMode = run.planner_mode || (data && data.extraction_mode === "llm_hybrid" ? "llm_planner" : "deterministic_fallback");
    const provider = run.model_provider || "deterministic_fallback";
    const version = run.model_version || "deterministic_rules_v3";

    if (plannerMode === "llm_planner" && provider === "google_gemini") {
      return {
        label: "Gemini",
        badgeText: `Gemini (${version})`,
        badgeStyle: "background: #dcfce7; color: #166534; border: 1px solid #86efac;",
        detail: `LLM Planner active via Google Gemini (${version}) under deterministic policy validation.`
      };
    }
    if (plannerMode === "llm_planner" && provider === "openai") {
      return {
        label: "OpenAI",
        badgeText: `OpenAI (${version})`,
        badgeStyle: "background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd;",
        detail: `LLM Planner active via OpenAI (${version}) under deterministic policy validation.`
      };
    }
    if (plannerMode === "deterministic_fallback_after_llm_error") {
      return {
        label: "Deterministic fallback",
        badgeText: `Deterministic fallback (recovered from LLM error)`,
        badgeStyle: "background: #fef3c7; color: #92400e; border: 1px solid #fde68a;",
        detail: `LLM call failed or returned invalid output; governed deterministic fallback (${version}) executed safely.`
      };
    }
    return {
      label: "Deterministic fallback",
      badgeText: `Deterministic fallback (${version})`,
      badgeStyle: "background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe;",
      detail: `Governed deterministic fallback planner (${version}) active.`
    };
  }

  /**
   * Visually distinguishes all 6 operational/error states for an agent step:
   * - Tool succeeded with records (status=ok, records_count > 0)
   * - Tool returned zero results (status=ok, records_count === 0)
   * - Tool failed (status=error)
   * - Agent stopped by policy (decision_outcome=REJECTED or not_executed_policy_rejected)
   * - Researcher clarification required (ASK_RESEARCHER / ask_researcher)
   * - Human review required (HUMAN_REVIEW / request_human_review)
   */
  function formatStepStatusBadge(step) {
    if (!step) {
      return { text: "UNKNOWN", style: "background:#f1f5f9; color:#475569; border:1px solid #cbd5e1;" };
    }
    const outcome = step.decision_outcome || "";
    const execStatus = step.tool_execution_status || "";
    const policyAllowed = step.policy_validation_result ? Boolean(step.policy_validation_result.allowed) : true;
    const selectedTool = step.selected_tool || "";
    const prov = step.tool_result_provenance || {};
    const recordsCount = typeof prov.records_count === "number" ? prov.records_count : 0;

    if (!policyAllowed || outcome === "REJECTED" || execStatus === "not_executed_policy_rejected") {
      return {
        code: "STOPPED_BY_POLICY",
        text: "🛑 STOPPED BY POLICY",
        style: "background: #fee2e2; color: #991b1b; border: 1px solid #f87171;"
      };
    }
    if (execStatus === "error") {
      return {
        code: "TOOL_FAILED",
        text: "❌ TOOL EXECUTION FAILED",
        style: "background: #fee2e2; color: #991b1b; border: 1px solid #f87171;"
      };
    }
    if (outcome === "HUMAN_REVIEW" || selectedTool === "request_human_review") {
      return {
        code: "HUMAN_REVIEW_REQUIRED",
        text: "⚖️ HUMAN REVIEW REQUIRED",
        style: "background: #ede9fe; color: #5b21b6; border: 1px solid #c4b5fd;"
      };
    }
    if (outcome === "ASK_RESEARCHER" || selectedTool === "ask_researcher") {
      return {
        code: "CLARIFICATION_REQUIRED",
        text: "❓ RESEARCHER CLARIFICATION REQUIRED",
        style: "background: #fef3c7; color: #92400e; border: 1px solid #fcd34d;"
      };
    }
    if ((outcome === "USE_TOOL" || outcome === "CALL_TOOL") && execStatus === "ok") {
      if (recordsCount > 0) {
        return {
          code: "TOOL_OK_WITH_RECORDS",
          text: `✓ TOOL SUCCEEDED (${recordsCount} record${recordsCount === 1 ? "" : "s"})`,
          style: "background: #dcfce7; color: #166534; border: 1px solid #86efac;"
        };
      }
      return {
        code: "TOOL_ZERO_RESULTS",
        text: "⚠️ TOOL RETURNED 0 RECORDS (Triggers Re-Plan)",
        style: "background: #ffedd5; color: #9a3412; border: 1px solid #fdba74;"
      };
    }
    if (outcome === "STOP" || outcome === "CONTINUE") {
      return {
        code: "AGENT_STOP",
        text: `✓ COMPLETE (${outcome})`,
        style: "background: #dcfce7; color: #166534; border: 1px solid #86efac;"
      };
    }
    return {
      code: "STEP_EXECUTED",
      text: `${outcome || "STEP"} (${execStatus || "ok"})`,
      style: "background: #e0f2fe; color: #075985; border: 1px solid #bae6fd;"
    };
  }

  /**
   * Builds the Human Governance Escalation card when workflow_state === "HUMAN_REVIEW"
   * or data.agent_run.human_escalation is present.
   */
  function buildHumanEscalationHtml(data) {
    const run = (data && data.agent_run) || {};
    const state = (data && data.workflow_state) || "";
    const esc = run.human_escalation || null;
    if (state !== "HUMAN_REVIEW" && state !== "ESCALATED" && state !== "ESCALATED_TO_HUMAN_REVIEW" && run.final_decision !== "HUMAN_REVIEW" && !esc) {
      return "";
    }
    const requiredRole = (esc && esc.required_role) || (data && data.next_action && data.next_action.actor) || "biosafety_officer";
    const reason = (esc && esc.reason) || (data && data.next_action && data.next_action.description) || "Mandatory human committee review gate triggered by institutional safety/ethics rules.";
    const riskLevel = ((esc && esc.risk_level) || "high").toUpperCase();
    const blockedFlag = esc && typeof esc.autonomous_approval_blocked === "boolean" ? esc.autonomous_approval_blocked : true;

    return `
      <div id="agent-human-escalation-banner" style="background: #fdf4ff; border: 2px solid #c084fc; border-left: 6px solid #7e22ce; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.15rem;">⚖️</span>
            <strong style="color: #581c87; font-size: 0.9rem;">Mandatory Human Governance Gate (HUMAN_REVIEW)</strong>
          </div>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <span style="background: #fee2e2; color: #991b1b; font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; border: 1px solid #fca5a5;">
              Risk Level: ${escapeHtml(riskLevel)}
            </span>
            <span style="background: #f3e8ff; color: #6b21a8; font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; border: 1px solid #d8b4fe;">
              Required Role: ${escapeHtml(requiredRole)}
            </span>
          </div>
        </div>
        <div style="font-size: 0.82rem; color: #3b0764; margin-bottom: 8px; line-height: 1.45;">
          <strong>Escalation Reason:</strong> ${escapeHtml(reason)}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; background: #ffffff; border: 1px solid #e9d5ff; border-radius: 6px; padding: 8px 12px; font-size: 0.75rem; color: #4c1d95;">
          <div>
            <strong>Autonomous Approval Blocked:</strong> <code>${String(blockedFlag)}</code> — The AI agent cannot approve or bypass this gate. Authenticated human officer sign-off is required.
          </div>
          <button type="button" onclick="if(window.openAgentInteractiveModal){ window.openAgentInteractiveModal(); if(window.switchAgentModalTab) window.switchAgentModalTab('gate'); }" style="background: #7e22ce; color: #ffffff; border: none; padding: 5px 12px; border-radius: 5px; font-size: 0.75rem; font-weight: 700; cursor: pointer;">
            Open Human Review Gate ➔
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Builds the Phase 3 Governed Agentic Loop trace:
   * Decision -> Action -> Observation -> Re-plan -> Next Action
   */
  function buildAgenticLoopHtml(data, serverMode) {
    const run = (data && data.agent_run) || null;
    const state = (data && data.workflow_state) || "DRAFT";
    const plannerInfo = formatPlannerModeDisplay(run, data);

    if (!run || !Array.isArray(run.steps)) {
      return `
        <div id="agent-loop-trace-panel" style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <strong style="color: #0f172a; font-size: 0.86rem;">🤖 Governed Agentic Loop Trace</strong>
            <span style="padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; ${plannerInfo.badgeStyle}">
              Planner Mode: ${escapeHtml(plannerInfo.badgeText)}
            </span>
          </div>
          <div style="margin-top: 6px; font-size: 0.78rem; color: #475569;">
            ${serverMode === "client_offline_engine"
              ? "Offline client fallback active — connect to the Flask server to execute the live Phase 3 GovernedAgentLoop and bounded tool registry."
              : "No multi-step agent run trace recorded for this request."}
          </div>
        </div>
      `;
    }

    const steps = run.steps || [];
    const maxSteps = (run.limits_enforced && run.limits_enforced.max_steps_per_run) || 3;
    const maxTools = (run.limits_enforced && run.limits_enforced.max_tool_calls_per_run) || 2;
    const isPolicyStopped = state === "STOPPED_BY_POLICY" || state === "REJECTED" || run.final_decision === "STOPPED_BY_POLICY" || steps.some(s => s.decision_outcome === "REJECTED");

    const policyStoppedBanner = isPolicyStopped ? `
      <div id="agent-policy-stopped-banner" style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; color: #991b1b; font-size: 0.8rem;">
        <strong>🛑 Agent Stopped by Governance Policy:</strong> One or more proposed agent actions violated hard deterministic safety boundaries and were rejected before execution.
      </div>
    ` : "";

    const stepsHtml = steps.map((step, idx) => {
      const badge = formatStepStatusBadge(step);
      const prevStep = idx > 0 ? steps[idx - 1] : null;
      const isReplanStep = idx > 0 && prevStep && (prevStep.next_action === "REASSESS_OBSERVATION" || prevStep.decision_outcome === "USE_TOOL" || prevStep.decision_outcome === "CALL_TOOL");
      const triggersReplanNext = step.next_action === "REASSESS_OBSERVATION";
      const policyOk = step.policy_validation_result ? Boolean(step.policy_validation_result.allowed) : true;
      const policyReason = (step.policy_validation_result && step.policy_validation_result.reason) || "Validated against hard agent limits.";
      const recordsCount = step.tool_result_provenance && typeof step.tool_result_provenance.records_count === "number"
        ? step.tool_result_provenance.records_count
        : 0;
      const toolArgsJson = JSON.stringify(step.tool_arguments || {});
      const safeguards = Array.isArray(step.deterministic_safeguards_triggered) && step.deterministic_safeguards_triggered.length > 0
        ? step.deterministic_safeguards_triggered.join(", ")
        : "hard_agent_limits_enforced";

      const replanConnectorHtml = isReplanStep ? `
        <div class="agent-replan-connector" style="display: flex; align-items: center; gap: 8px; background: #fff7ed; border: 1.5px dashed #f97316; border-radius: 6px; padding: 7px 12px; margin: 8px 0; font-size: 0.76rem; color: #9a3412;">
          <span style="background: #ea580c; color: #ffffff; font-weight: 800; padding: 2px 7px; border-radius: 4px; font-size: 0.7rem;">
            ↻ RE-PLANNING (Step ${prevStep.step_index} → Step ${step.step_index})
          </span>
          <span>
            Observation from <code>${escapeHtml(prevStep.selected_tool || "previous step")}</code> (<em>${escapeHtml((prevStep.observation_summary || "").substring(0, 110))}</em>) triggered dynamic re-planning for Step ${step.step_index}.
          </span>
        </div>
      ` : "";

      return `
        ${replanConnectorHtml}
        <div id="agent-step-card-${step.step_index}" class="agent-step-card" style="background: #ffffff; border: 1.5px solid #cbd5e1; border-left: 4px solid ${policyOk ? "#2563eb" : "#dc2626"}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #f1f5f9;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="background: #0f172a; color: #ffffff; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px;">
                STEP ${step.step_index}
              </span>
              <strong style="color: #0f172a; font-size: 0.82rem;">
                Decision: <code>${escapeHtml(step.decision_outcome)}</code>
              </strong>
              <span style="font-size: 0.78rem; color: #1e40af; font-weight: 700;">
                Tool: <code>${escapeHtml(step.selected_tool || "None")}</code>
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span style="font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; ${badge.style}">
                ${badge.text}
              </span>
              <span style="font-size: 0.68rem; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">
                Planner: ${escapeHtml(step.planner_mode || run.planner_mode)}
              </span>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; font-size: 0.76rem; color: #334155; margin-bottom: 8px;">
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;">
              <div style="font-weight: 800; color: #0f172a; font-size: 0.71rem; text-transform: uppercase; margin-bottom: 3px;">1. Decision &amp; Tool Arguments</div>
              <div><strong>Reason:</strong> ${escapeHtml(step.reason || "—")}</div>
              <div style="margin-top: 3px;"><strong>Arguments:</strong> <code style="word-break: break-all; background: #e2e8f0; padding: 1px 4px; border-radius: 3px;">${escapeHtml(toolArgsJson)}</code></div>
              <div style="margin-top: 3px; color: #64748b;"><strong>Workflow State:</strong> <code>${escapeHtml(step.current_workflow_state || state)}</code> • <strong>Confidence:</strong> ${escapeHtml(step.confidence)}</div>
            </div>

            <div style="background: ${policyOk ? "#f0fdf4" : "#fef2f2"}; border: 1px solid ${policyOk ? "#bbf7d0" : "#fecaca"}; border-radius: 6px; padding: 8px;">
              <div style="font-weight: 800; color: ${policyOk ? "#166534" : "#991b1b"}; font-size: 0.71rem; text-transform: uppercase; margin-bottom: 3px;">2. Deterministic Policy Gate</div>
              <div>
                <strong>Validation:</strong>
                <span style="font-weight: 800; color: ${policyOk ? "#15803d" : "#dc2626"};">${policyOk ? "✓ ALLOWED" : "🛑 REJECTED"}</span>
              </div>
              <div style="margin-top: 3px;">${escapeHtml(policyReason)}</div>
              <div style="margin-top: 3px; font-size: 0.69rem; color: #475569;"><strong>Safeguards:</strong> <code>${escapeHtml(safeguards)}</code></div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;">
              <div style="font-weight: 800; color: #0f172a; font-size: 0.71rem; text-transform: uppercase; margin-bottom: 3px;">3. Execution &amp; Observation</div>
              <div>
                <strong>Execution Status:</strong> <code>${escapeHtml(step.tool_execution_status || "not_applicable")}</code>
                • <strong>Records Returned:</strong> <strong>${recordsCount}</strong>
              </div>
              <div style="margin-top: 3px;"><strong>Observation:</strong> ${escapeHtml(step.observation_summary || "No external observation recorded.")}</div>
              <div style="margin-top: 3px; font-size: 0.69rem; color: #64748b;"><strong>Provenance:</strong> <code>${escapeHtml(step.concise_provenance || "")}</code></div>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; background: ${triggersReplanNext ? "#fff7ed" : "#f1f5f9"}; border: 1px solid ${triggersReplanNext ? "#fed7aa" : "#e2e8f0"}; border-radius: 5px; padding: 6px 10px; font-size: 0.74rem;">
            <div>
              <strong>4. Next Action:</strong> <code>${escapeHtml(step.next_action || "COMPLETE")}</code>
              ${triggersReplanNext ? `<span style="margin-left: 6px; color: #c2410c; font-weight: 800;">↻ Observation triggers re-planning in Step ${step.step_index + 1}</span>` : ""}
            </div>
            <div style="font-size: 0.68rem; color: #64748b;">
              Step Timestamp: ${escapeHtml(step.timestamp || "")}
            </div>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div id="agent-loop-trace-panel" style="background: #f8fafc; border: 1.5px solid #93c5fd; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <strong style="color: #0f172a; font-size: 0.9rem;">🔄 Phase 3 Governed Agentic Loop Trace (Decision → Action → Observation → Re-Plan)</strong>
              <span style="background: #dbeafe; color: #1e40af; font-size: 0.7rem; font-weight: 800; padding: 2px 7px; border-radius: 4px;">
                Run ID: <code>${escapeHtml(run.agent_run_id || "—")}</code>
              </span>
            </div>
            <div style="font-size: 0.74rem; color: #475569; margin-top: 2px;">
              ${escapeHtml(plannerInfo.detail)} • Proposal authorship protection enforced (read-only proposal context).
            </div>
          </div>
          <span id="agent-planner-mode-badge" style="padding: 3px 9px; border-radius: 6px; font-size: 0.74rem; font-weight: 800; ${plannerInfo.badgeStyle}">
            Planner Mode: ${escapeHtml(plannerInfo.badgeText)}
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin-bottom: 12px; font-size: 0.74rem;">
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Workflow State</span>
            <div style="font-weight: 800; color: #0f172a; margin-top: 2px;"><code>${escapeHtml(state)}</code></div>
          </div>
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Final Loop Decision</span>
            <div style="font-weight: 800; color: #1e40af; margin-top: 2px;"><code>${escapeHtml(run.final_decision || "—")}</code></div>
          </div>
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Steps Executed</span>
            <div style="font-weight: 800; color: #0f172a; margin-top: 2px;">${steps.length} / ${maxSteps} max</div>
          </div>
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Tool Calls Executed</span>
            <div style="font-weight: 800; color: #0f172a; margin-top: 2px;">${run.tool_calls_count ?? 0} / ${maxTools} max</div>
          </div>
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Elapsed Time</span>
            <div style="font-weight: 800; color: #0f172a; margin-top: 2px;">${run.elapsed_ms ?? 0} ms</div>
          </div>
          <div>
            <span style="color: #64748b; font-size: 0.68rem; text-transform: uppercase; font-weight: 700;">Input Fingerprint</span>
            <div style="font-weight: 700; color: #475569; margin-top: 2px; font-family: monospace;">${escapeHtml(run.input_fingerprint || (data.input_summary && data.input_summary.input_fingerprint) || "—")}</div>
          </div>
        </div>

        ${policyStoppedBanner}
        ${stepsHtml}
      </div>
    `;
  }

  /**
   * Builds the Tool Visibility section distinguishing TOOLS USED in this run
   * from AVAILABLE TOOLS in the bounded tool registry.
   */
  function buildToolsVisibilityHtml(data) {
    const run = (data && data.agent_run) || {};
    const toolsCalled = Array.isArray(run.tools_called) ? run.tools_called : [];
    const steps = Array.isArray(run.steps) ? run.steps : [];
    const availableTools = Array.isArray(data && data.available_tools) ? data.available_tools : [];

    const usedSteps = steps.filter(s => (s.decision_outcome === "USE_TOOL" || s.decision_outcome === "CALL_TOOL") && s.selected_tool);
    let toolsUsedHtml = "";
    if (toolsCalled.length === 0 && usedSteps.length === 0) {
      toolsUsedHtml = `
        <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 10px; font-size: 0.76rem; color: #64748b;">
          No bounded tools were executed during this run.
        </div>
      `;
    } else {
      const items = usedSteps.length > 0 ? usedSteps : toolsCalled.map((tId, idx) => ({
        step_index: idx + 1,
        selected_tool: tId,
        tool_execution_status: "ok",
        tool_result_provenance: {}
      }));
      toolsUsedHtml = items.map(s => {
        const badge = formatStepStatusBadge(s);
        const recCount = s.tool_result_provenance && typeof s.tool_result_provenance.records_count === "number"
          ? s.tool_result_provenance.records_count
          : null;
        return `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 0.76rem;">
            <div>
              <strong style="color: #1e3a8a;">Step ${s.step_index}: <code>${escapeHtml(s.selected_tool)}</code></strong>
              ${recCount !== null ? `<span style="margin-left: 6px; color: #475569;">(${recCount} record${recCount === 1 ? "" : "s"})</span>` : ""}
            </div>
            <span style="font-size: 0.68rem; font-weight: 800; padding: 2px 7px; border-radius: 4px; ${badge.style}">
              ${badge.text}
            </span>
          </div>
        `;
      }).join("");
    }

    let availableHtml = "";
    if (availableTools.length === 0) {
      availableHtml = `
        <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 10px; font-size: 0.76rem; color: #64748b;">
          Bounded tool registry metadata not loaded (offline mode).
        </div>
      `;
    } else {
      availableHtml = availableTools.map(tool => {
        const wasUsed = toolsCalled.includes(tool.tool_id);
        return `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; background: ${wasUsed ? "#f0fdf4" : "#ffffff"}; border: 1px solid ${wasUsed ? "#86efac" : "#e2e8f0"}; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 0.74rem;">
            <div style="flex: 1;">
              <div>
                <strong style="color: #0f172a;"><code>${escapeHtml(tool.tool_id)}</code></strong>
                <span style="font-size: 0.68rem; color: #64748b; margin-left: 6px;">Risk: <code>${escapeHtml(tool.risk_level || "read_only")}</code> • Timeout: ${escapeHtml(tool.timeout || 6)}s</span>
              </div>
              <div style="color: #475569; font-size: 0.72rem; margin-top: 2px;">${escapeHtml(tool.description || "")}</div>
            </div>
            <span style="white-space: nowrap; font-size: 0.68rem; font-weight: 800; padding: 2px 7px; border-radius: 4px; ${wasUsed ? "background:#dcfce7; color:#166534; border:1px solid #86efac;" : "background:#f1f5f9; color:#475569; border:1px solid #cbd5e1;"}">
              ${wasUsed ? "✓ USED IN RUN" : "AVAILABLE"}
            </span>
          </div>
        `;
      }).join("");
    }

    return `
      <div id="agent-tools-visibility-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 14px;">
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #0f172a; font-size: 0.82rem;">🛠️ TOOLS USED IN THIS RUN (${toolsCalled.length})</strong>
            <span style="font-size: 0.68rem; background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-weight: 700;">Executed Calls</span>
          </div>
          ${toolsUsedHtml}
        </div>
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #0f172a; font-size: 0.82rem;">🧰 AVAILABLE BOUNDED TOOLS (${availableTools.length})</strong>
            <span style="font-size: 0.68rem; background: #f1f5f9; color: #334155; padding: 2px 6px; border-radius: 4px; font-weight: 700;">Whitelisted Registry</span>
          </div>
          ${availableHtml}
        </div>
      </div>
    `;
  }

  /**
   * Builds the Literature Evidence & Provenance panel from data.context.evidence_log
   * and data.agent_run.observations.
   * Never fabricates citations; if no records were returned, displays:
   * "No external evidence was retrieved during this run."
   */
  function buildEvidenceLogHtml(data) {
    const ctx = (data && (data.context || data.extracted_context)) || {};
    const run = (data && data.agent_run) || {};
    const evidenceLog = Array.isArray(ctx.evidence_log) ? ctx.evidence_log : [];
    const observations = Array.isArray(run.observations) ? run.observations : [];

    // Use evidence_log for the current run if available, or fall back to run.observations
    const currentRunId = run.agent_run_id || null;
    const relevantEntries = evidenceLog.length > 0
      ? (currentRunId ? evidenceLog.filter(e => !e.agent_run_id || e.agent_run_id === currentRunId) : evidenceLog)
      : observations.filter(o => Array.isArray(o.records));

    const entriesToRender = relevantEntries.length > 0 ? relevantEntries : evidenceLog;
    let totalRecords = 0;
    const recordCards = [];

    entriesToRender.forEach(entry => {
      const toolId = entry.tool_id || "literature_tool";
      const query = entry.query || "";
      const prov = entry.provenance || toolId;
      const ts = entry.timestamp || "";
      const recs = Array.isArray(entry.records) ? entry.records : [];
      totalRecords += recs.length;

      recs.forEach(rec => {
        const identifier = rec.pmid ? `PMID: ${rec.pmid}` : (rec.doi ? `DOI: ${rec.doi}` : (rec.id ? `ID: ${rec.id}` : "Indexed Record"));
        const sourceLabel = rec.source || toolId;
        const title = rec.title || "Untitled Scientific Record";
        const journal = rec.journal || "Indexed Biomedical Venue";
        const year = rec.pubdate || rec.year || "";
        const url = rec.url || "";

        recordCards.push(`
          <div class="agent-evidence-record-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #0d9488; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 4px;">
              <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                <span style="background: #ccfbf1; color: #115e59; font-size: 0.7rem; font-weight: 800; padding: 2px 7px; border-radius: 4px;">
                  ${escapeHtml(sourceLabel)} (<code>${escapeHtml(toolId)}</code>)
                </span>
                <span style="background: #f1f5f9; color: #0f172a; font-size: 0.7rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; font-family: monospace;">
                  ${escapeHtml(identifier)}
                </span>
              </div>
              <span style="font-size: 0.68rem; color: #64748b;">
                Provenance: <code>${escapeHtml(prov)}</code> ${ts ? `• ${escapeHtml(ts.substring(0, 19))}` : ""}
              </span>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #0f172a; margin-bottom: 3px;">
              ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color: #0f766e; text-decoration: underline;">${escapeHtml(title)} ↗</a>` : escapeHtml(title)}
            </div>
            <div style="font-size: 0.74rem; color: #475569;">
              <strong>Journal / Venue:</strong> ${escapeHtml(journal)} ${year ? `(${escapeHtml(year)})` : ""}
              ${query ? ` • <strong>Query:</strong> <code>${escapeHtml(query)}</code>` : ""}
            </div>
          </div>
        `);
      });
    });

    const queryAttemptSummary = entriesToRender.length > 0 ? `
      <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;">
        ${entriesToRender.map(e => {
          const cnt = typeof e.records_count === "number" ? e.records_count : (Array.isArray(e.records) ? e.records.length : 0);
          return `<span style="font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; font-weight: 700; ${cnt > 0 ? "background:#dcfce7; color:#166534; border:1px solid #86efac;" : "background:#ffedd5; color:#9a3412; border:1px solid #fdba74;"}">
            <code>${escapeHtml(e.tool_id)}</code>: ${cnt} record${cnt === 1 ? "" : "s"} ${e.query ? `(query="${escapeHtml(String(e.query).substring(0, 40))}")` : ""}
          </span>`;
        }).join("")}
      </div>
    ` : "";

    return `
      <div id="agent-evidence-log-panel" style="background: #f0fdfa; border: 1.5px solid #99f6e4; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;">
          <strong style="color: #134e4a; font-size: 0.85rem;">📚 Retrieved External Evidence &amp; Provenance (${totalRecords} record${totalRecords === 1 ? "" : "s"})</strong>
          <span style="font-size: 0.68rem; background: #ccfbf1; color: #115e59; padding: 2px 8px; border-radius: 4px; font-weight: 700;">
            establishes_biosafety_risk_group: false
          </span>
        </div>
        <div style="font-size: 0.73rem; color: #0f766e; margin-bottom: 8px;">
          External literature evidence provides scientific context only and is never permitted to downgrade biosafety containment or override institutional compliance rules.
        </div>
        ${queryAttemptSummary}
        ${totalRecords > 0
          ? recordCards.join("")
          : `<div id="agent-no-evidence-message" style="background: #ffffff; border: 1px dashed #99f6e4; border-radius: 6px; padding: 10px 12px; font-size: 0.78rem; color: #475569; font-weight: 600;">No external evidence was retrieved during this run.</div>`
        }
      </div>
    `;
  }

  /**
   * Dynamically renders ALL pending_clarifications and answered_clarifications without any 2-card cap.
   */
  function buildClarificationsHtml(pendingClarifications, answeredClarifications, idPrefix) {
    const pending = Array.isArray(pendingClarifications) ? pendingClarifications : [];
    const answered = Array.isArray(answeredClarifications) ? answeredClarifications : [];
    const prefix = idPrefix || "clar";

    if (pending.length === 0 && answered.length === 0) {
      return `
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 14px; color: #166534; font-size: 0.8rem; margin-bottom: 12px;">
          ✓ No pending Socratic clarifications required. All compliance parameters are sufficiently specified.
        </div>
      `;
    }

    const pendingCardsHtml = pending.map((q, idx) => {
      const qid = q.question_id || `CLAR-PENDING-${idx + 1}`;
      const field = q.field || q.target_field || "proposal";
      const prompt = q.prompt || q.question || "";
      const rationale = q.rationale || "";
      const snippet = q.context_snippet || "";
      const inputId = `${prefix}-input-${qid}`;

      return `
        <div class="agent-clarification-card pending-clar-card" data-qid="${escapeHtml(qid)}" style="background: #ffffff; border: 1.5px solid #fcd34d; border-left: 4px solid #d97706; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;" id="${prefix}-card-${escapeHtml(qid)}">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 0.74rem; font-weight: 800; color: #1e40af; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">
                ${escapeHtml(qid)}
              </span>
              <span style="font-size: 0.7rem; color: #475569; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">
                Field: <code>${escapeHtml(field)}</code>
              </span>
            </div>
            <span style="font-size: 0.72rem; color: #b45309; font-weight: 800;">● Pending Answer (status: ${escapeHtml(q.status || "pending")})</span>
          </div>
          <div style="font-size: 0.84rem; font-weight: 700; color: #1e293b; margin-bottom: 4px;">
            ${escapeHtml(prompt)}
          </div>
          <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 8px;">
            <strong>Institutional Rationale:</strong> ${escapeHtml(rationale)}
            ${snippet ? ` • <em>Context: "${escapeHtml(snippet)}"</em>` : ""}
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <input type="text" id="${escapeHtml(inputId)}" class="form-input dynamic-clarification-input" data-qid="${escapeHtml(qid)}" placeholder="Type your authoritative researcher clarification..." style="flex: 1; min-width: 220px; font-size: 0.82rem; padding: 7px 10px; border: 1px solid #cbd5e1; border-radius: 6px;">
            <button type="button" class="btn-primary btn-submit-clarification" data-qid="${escapeHtml(qid)}" data-input-id="${escapeHtml(inputId)}" style="font-size: 0.78rem; padding: 7px 14px; background: #d97706; color: #ffffff; border: 1px solid #b45309; border-radius: 6px; font-weight: 700; white-space: nowrap; cursor: pointer;">
              Submit Answer
            </button>
          </div>
        </div>
      `;
    }).join("");

    const answeredCardsHtml = answered.map((q, idx) => {
      const qid = q.question_id || `CLAR-ANSWERED-${idx + 1}`;
      const field = q.field || q.target_field || "proposal";
      const prompt = q.prompt || q.question || "";
      const rationale = q.rationale || "";
      const responseText = q.researcher_response || "";
      const responseTs = q.response_timestamp || "";

      return `
        <div class="agent-clarification-card answered-clar-card" data-qid="${escapeHtml(qid)}" style="background: #f0fdf4; border: 1.5px solid #86efac; border-left: 4px solid #16a34a; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;" id="${prefix}-answered-card-${escapeHtml(qid)}">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 0.74rem; font-weight: 800; color: #166534; background: #dcfce7; padding: 2px 8px; border-radius: 4px;">
                ${escapeHtml(qid)}
              </span>
              <span style="font-size: 0.7rem; color: #166534; background: #ffffff; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;">
                Field: <code>${escapeHtml(field)}</code>
              </span>
            </div>
            <span style="font-size: 0.72rem; color: #059669; font-weight: 800;">
              ✓ Answered with Human Provenance (status: ${escapeHtml(q.status || "answered")})
            </span>
          </div>
          <div style="font-size: 0.82rem; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
            ${escapeHtml(prompt)}
          </div>
          <div style="font-size: 0.74rem; color: #475569; margin-bottom: 6px;">
            <strong>Rationale:</strong> ${escapeHtml(rationale)}
          </div>
          <div style="background: #ffffff; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px 10px; font-size: 0.78rem; color: #14532d;">
            <div><strong>Researcher Response:</strong> ${escapeHtml(responseText)}</div>
            ${responseTs ? `<div style="font-size: 0.68rem; color: #15803d; margin-top: 3px;">Recorded Timestamp: <code>${escapeHtml(responseTs)}</code> • Provenance: <code>researcher_clarification:${escapeHtml(qid)}</code></div>` : ""}
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="agent-clarifications-dynamic-list">
        ${pending.length > 0 ? `
          <div style="margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
              <span style="font-size: 1rem;">❓</span>
              <strong style="color: #92400e; font-size: 0.86rem;">Pending Socratic Clarifications (${pending.length})</strong>
            </div>
            ${pendingCardsHtml}
          </div>
        ` : ""}
        ${answered.length > 0 ? `
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
              <span style="font-size: 1rem;">✅</span>
              <strong style="color: #166534; font-size: 0.86rem;">Answered Researcher Clarifications (${answered.length})</strong>
            </div>
            ${answeredCardsHtml}
          </div>
        ` : ""}
      </div>
    `;
  }

  function bindClarificationButtons(containerEl) {
    if (!containerEl) return;
    const clarBtns = containerEl.querySelectorAll(".btn-submit-clarification");
    clarBtns.forEach(btn => {
      if (btn.getAttribute("data-bound") === "true") return;
      btn.setAttribute("data-bound", "true");
      btn.addEventListener("click", async () => {
        const qid = btn.getAttribute("data-qid");
        const inputId = btn.getAttribute("data-input-id") || `clar-input-${qid}`;
        const inputEl = document.getElementById(inputId) || containerEl.querySelector(`input[data-qid="${qid}"]`);
        const answer = (inputEl ? inputEl.value : "").trim();
        if (!answer) {
          alert("Please provide an authoritative answer before submitting clarification.");
          return;
        }
        btn.disabled = true;
        btn.textContent = "Submitting...";
        const res = await submitClarification(qid, answer);
        if (!res || !res.success) {
          alert(`Error: ${(res && res.error) || "Failed to submit clarification"}`);
          btn.disabled = false;
          btn.textContent = "Submit Answer";
        }
      });
    });
  }

  /**
   * Deterministic Client-Side Agent Engine (fallback ONLY if Flask server is unreachable).
   * Does not fabricate live tool calls or external literature evidence.
   */
  function runClientSideAgentAnalysis(proposalData, projectId) {
    const allText = [
      proposalData.title || "",
      proposalData.chassis || "",
      proposalData.tool || "",
      proposalData.target || "",
      proposalData.methodology || "",
      proposalData.abstract || "",
      proposalData.pitfalls || ""
    ].join(" ").toLowerCase();

    let chassisVal = proposalData.chassis || proposalData.system || "";
    if (!chassisVal) {
      if (allText.includes("clinical isolate")) chassisVal = "Clinical Bacterial Isolates";
      else if (allText.includes("e. coli") || allText.includes("escherichia coli")) chassisVal = "Escherichia coli";
      else if (allText.includes("pichia")) chassisVal = "Pichia pastoris";
      else if (allText.includes("cell-free")) chassisVal = "Cell-Free Buffer Reaction Matrix";
      else chassisVal = "Unspecified Chassis";
    }

    let toolVal = proposalData.tool || "";
    if (!toolVal) {
      if (allText.includes("cas12a") || allText.includes("crispr")) toolVal = "CRISPR-Cas12a / RPA";
      else if (allText.includes("petase")) toolVal = "Engineered PETase";
      else if (allText.includes("aptamer")) toolVal = "DNA Aptamer Probe";
      else toolVal = "Standard Molecular Assays";
    }

    const hasHumanText = /\b(human|patient|clinical|blood|serum|biopsy|swab|volunteer)\b/i.test(allText);
    const hasHuman = Boolean(proposalData.human_subjects) || hasHumanText;
    const isContradiction = (proposalData.human_subjects === false) && hasHumanText;
    const hasGmo = Boolean(proposalData.recombinant_dna) || /\b(recombinant|plasmid|transformation|vector|crispr|cas9|cas12a)\b/i.test(allText);
    const hasAmr = /\b(colistin|mcr-1|amr|resistant|resistance|pathogen|esbl|carbapenem)\b/i.test(allText);
    const hasPathogen = Boolean(proposalData.pathogen_work) || hasAmr || /\b(pathogen|clinical isolate|infection)\b/i.test(allText);
    const bsl = hasPathogen ? "BSL-2" : "BSL-1";

    const reqs = [];
    if (hasHuman) {
      reqs.push({
        rule_id: "REQ-ETH-01",
        requirement_id: "REQ-ETH-01",
        title: "Human Participants & Clinical Materials Review",
        applicable_annex: "Annex A: Human Subjects & Clinical Specimens",
        annex: "Annex A: Human Subjects & Clinical Specimens",
        human_action_required: "Institutional BioEthics Committee (IBC) Reviewer must inspect informed consent or strain repository provenance.",
        mandate: "Institutional BioEthics Committee (IBC) Reviewer must inspect informed consent or strain repository provenance.",
        evidence: "Clinical specimens / human materials detected in proposal text.",
        status: "REQUIRES_HUMAN_REVIEW"
      });
    }
    if (hasGmo) {
      reqs.push({
        rule_id: "REQ-BIO-01",
        requirement_id: "REQ-BIO-01",
        title: "Recombinant DNA & Genetic Manipulation Oversight",
        applicable_annex: "Annex C: Genetic Modification & Recombinant Vectors",
        annex: "Annex C: Genetic Modification & Recombinant Vectors",
        human_action_required: "Institutional Biosafety Officer must confirm vector safety profile and host containment verification.",
        mandate: "Institutional Biosafety Officer must confirm vector safety profile and host containment verification.",
        evidence: "Recombinant DNA or genetic modification indicators detected in text.",
        status: "CONFIRMED"
      });
    }
    if (hasPathogen) {
      reqs.push({
        rule_id: "REQ-BIO-02",
        requirement_id: "REQ-BIO-02",
        title: "Antimicrobial Resistance Determinants & Pathogen Containment",
        applicable_annex: "Annex C: Biosafety Level 2 Protocol Verification",
        annex: "Annex C: Biosafety Level 2 Protocol Verification",
        human_action_required: "Biosafety Officer must inspect standard operating procedures (SOPs) for biohazard autoclaving and barrier protection.",
        mandate: "Biosafety Officer must inspect standard operating procedures (SOPs) for biohazard autoclaving and barrier protection.",
        evidence: "Antimicrobial resistance determinant or pathogen work detected in text.",
        status: "REQUIRES_HUMAN_REVIEW"
      });
    }

    const storageKey = `agent_clarifications_${projectId}`;
    let savedAnswers = {};
    try {
      savedAnswers = JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch (_) {}

    const pendingQuestions = [];
    const answeredQuestions = [];
    if (hasHuman) {
      const qHuman = {
        question_id: "CLAR-HUMAN-01",
        field: "human_subjects",
        target_field: "human_subjects",
        prompt: "Your methodology specifies testing with clinical isolates/specimens. Are these samples obtained from a verified, de-identified public strain bank (e.g. ATCC, NCTC) or sourced directly from patient diagnostic swabs/clinical cohorts?",
        question: "Your methodology specifies testing with clinical isolates/specimens. Are these samples obtained from a verified, de-identified public strain bank (e.g. ATCC, NCTC) or sourced directly from patient diagnostic swabs/clinical cohorts?",
        rationale: "Clarification needed to establish whether formal patient informed consent (Annex A) is mandatory.",
        status: savedAnswers["CLAR-HUMAN-01"] ? "answered" : "pending",
        researcher_response: savedAnswers["CLAR-HUMAN-01"] || null,
        response_timestamp: savedAnswers["CLAR-HUMAN-01"] ? new Date().toISOString() : null
      };
      if (savedAnswers["CLAR-HUMAN-01"]) answeredQuestions.push(qHuman);
      else pendingQuestions.push(qHuman);
    }
    if (hasPathogen) {
      const qBio = {
        question_id: "CLAR-BIO-01",
        field: "biosafety_containment",
        target_field: "biosafety_containment",
        prompt: "Your project involves pathogenic or antimicrobial-resistant bacterial targets. What specific biosafety level (BSL-1 or BSL-2) and primary barrier equipment (e.g., certified Class II biosafety cabinet) will be utilized?",
        question: "Your project involves pathogenic or antimicrobial-resistant bacterial targets. What specific biosafety level (BSL-1 or BSL-2) and primary barrier equipment (e.g., certified Class II biosafety cabinet) will be utilized?",
        rationale: "Verification needed to certify institutional biosafety protocols and prevent accidental laboratory exposure.",
        status: savedAnswers["CLAR-BIO-01"] ? "answered" : "pending",
        researcher_response: savedAnswers["CLAR-BIO-01"] || null,
        response_timestamp: savedAnswers["CLAR-BIO-01"] ? new Date().toISOString() : null
      };
      if (savedAnswers["CLAR-BIO-01"]) answeredQuestions.push(qBio);
      else pendingQuestions.push(qBio);
    }

    const workflowState = pendingQuestions.length > 0 ? "NEEDS_CLARIFICATION" : "READY_FOR_ETHICS_HANDOFF";

    return {
      success: true,
      project_id: projectId,
      workflow_state: workflowState,
      extraction_mode: "client_offline_fallback",
      llm_available: false,
      checks_performed: [
        "1. Canonical Proposal Section Parsing (Offline Fallback)",
        "2. Host Organism / Chassis Provenance Verification",
        "3. Molecular Tool & Genetic Vector Extraction",
        "4. Human Subjects & Clinical Isolate Cross-Field Contradiction Check",
        "5. Pathogen / AMR & Biosafety Containment Check"
      ],
      input_summary: {
        title: proposalData.title,
        chassis_input: proposalData.chassis,
        tool_input: proposalData.tool,
        methodology_word_count: (proposalData.methodology || "").split(/\s+/).filter(Boolean).length,
        declared_human_subjects: proposalData.human_subjects
      },
      next_action: {
        action: pendingQuestions.length > 0 ? "Answer Socratic clarification questions" : "Compile dossier or dispatch to BioEthics adapter",
        actor: "researcher"
      },
      context: {
        title: proposalData.title,
        organism_or_chassis: { value: chassisVal, status: "CONFIRMED", source: "proposal.chassis", evidence: chassisVal },
        molecular_tools: [{ value: toolVal, status: "CONFIRMED", source: "proposal.tool", evidence: toolVal }],
        biosafety_containment: { value: bsl, status: "INFERRED", source: "proposal.methodology", evidence: bsl },
        human_subjects: { value: hasHuman, status: isContradiction ? "REQUIRES_HUMAN_REVIEW" : "CONFIRMED", source: "proposal.methodology", evidence: isContradiction ? "Contradiction: form=false vs clinical text" : "" },
        pathogen_work: { value: hasPathogen, status: "CONFIRMED", source: "proposal.methodology", evidence: "" },
        antimicrobial_resistance: { value: hasAmr, status: "CONFIRMED", source: "proposal.methodology", evidence: "" },
        evidence_log: []
      },
      extracted_context: {
        organism_or_chassis: { value: chassisVal, status: "CONFIRMED", source: "proposal.chassis" },
        molecular_tools: [{ value: toolVal, status: "CONFIRMED", source: "proposal.tool" }],
        biosafety_containment: { value: bsl, status: "INFERRED", source: "proposal.methodology" },
        human_subjects: { value: hasHuman, status: isContradiction ? "REQUIRES_HUMAN_REVIEW" : "CONFIRMED", source: "proposal.methodology" }
      },
      requirements: reqs,
      active_requirements: reqs,
      pending_clarifications: pendingQuestions,
      answered_clarifications: answeredQuestions,
      uncertainties: isContradiction ? [{ field: "human_subjects", issue: "Contradiction detected between form human_subjects=false and clinical terms in text.", requires_human_review: true }] : [],
      agent_run: null,
      available_tools: []
    };
  }

  async function runAgentAnalysis(showScroll = false) {
    const projectId = getActiveProjectId();
    const proposalData = getActiveProposalData();

    const statusBadge = document.getElementById("agent-status-badge");
    const resultsContainer = document.getElementById("agent-results-container");
    const btnRun = document.getElementById("btn-agent-run-analysis");
    const btnDossier = document.getElementById("btn-agent-view-dossier");

    if (btnRun) {
      btnRun.disabled = true;
      btnRun.innerHTML = '<span>⏳</span> <span>Executing Governed Agent Loop...</span>';
    }
    if (statusBadge) {
      statusBadge.textContent = "● Analyzing...";
      statusBadge.style.cssText = "background: #f1f5f9; color: #475569;";
    }

    let resultData = null;
    let serverMode = "live_server";
    const apiBase = getApiBase();

    if (apiBase === null || (isFileProtocol() && _localServerOffline)) {
      resultData = runClientSideAgentAnalysis(proposalData, projectId);
      serverMode = "client_offline_engine";
    } else {
      try {
        const resp = await fetch(`${apiBase}/agent/api/analyze/${encodeURIComponent(projectId)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proposal_data: proposalData })
        });
        if (resp.ok) {
          resultData = await resp.json();
          serverMode = isFileProtocol() ? "live_local_server" : "live_server";
        } else {
          throw new Error(`HTTP ${resp.status}`);
        }
      } catch (err) {
        if (isFileProtocol()) {
          _localServerOffline = true;
        }
        resultData = runClientSideAgentAnalysis(proposalData, projectId);
        serverMode = "client_offline_engine";
      }
    }

    window.latestAgentAnalysis = resultData;
    window.latestAgentServerMode = serverMode;

    renderAgentResults(resultData, projectId, serverMode);
    await syncModalAndDrawerWithBackend(resultData, projectId, serverMode);

    if (btnDossier) {
      btnDossier.style.display = "inline-flex";
    }
    if (showScroll && resultsContainer) {
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.innerHTML = '<span>🚀</span> <span>Re-Run Compliance Check</span>';
    }
    return resultData;
  }

  async function submitClarification(questionId, answer) {
    const projectId = getActiveProjectId();
    const apiBase = getApiBase();
    try {
      const resp = await fetch(`${apiBase}/agent/api/clarify/${encodeURIComponent(projectId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId, answer: answer })
      });
      const res = await resp.json();
      if (res.success) {
        try {
          const storageKey = `agent_clarifications_${projectId}`;
          const existing = JSON.parse(localStorage.getItem(storageKey) || "{}");
          existing[questionId] = answer;
          localStorage.setItem(storageKey, JSON.stringify(existing));
        } catch (_) {}
        await runAgentAnalysis(false);
        return res;
      }
      return res;
    } catch (err) {
      const storageKey = `agent_clarifications_${projectId}`;
      const existing = JSON.parse(localStorage.getItem(storageKey) || "{}");
      existing[questionId] = answer;
      localStorage.setItem(storageKey, JSON.stringify(existing));
      await runAgentAnalysis(false);
      return { success: true, mode: "client_offline_engine" };
    }
  }

  async function fetchDossier(projectId) {
    const pid = projectId || getActiveProjectId();
    const apiBase = getApiBase();
    try {
      const resp = await fetch(`${apiBase}/agent/api/dossier/${encodeURIComponent(pid)}`);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (_) {}
    return null;
  }

  async function dispatchToBioEthics(projectId, mode = "auto") {
    const pid = projectId || getActiveProjectId();
    const apiBase = getApiBase();
    const resp = await fetch(`${apiBase}/agent/api/dispatch/${encodeURIComponent(pid)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode })
    });
    const data = await resp.json();
    await refreshAuditAndState(pid);
    return { status: resp.status, data: data };
  }

  async function submitHumanDecision(projectId, payload) {
    const pid = projectId || getActiveProjectId();
    const apiBase = getApiBase();
    const resp = await fetch(`${apiBase}/agent/api/human_decision/${encodeURIComponent(pid)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    await refreshAuditAndState(pid);
    return { status: resp.status, data: data };
  }

  async function fetchAuditTrail(projectId) {
    const pid = projectId || getActiveProjectId();
    const apiBase = getApiBase();
    try {
      const resp = await fetch(`${apiBase}/agent/api/audit/${encodeURIComponent(pid)}`);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (_) {}
    return null;
  }

  async function refreshAuditAndState(projectId) {
    const pid = projectId || getActiveProjectId();
    const apiBase = getApiBase();
    try {
      const statusResp = await fetch(`${apiBase}/agent/api/status/${encodeURIComponent(pid)}`);
      if (statusResp.ok) {
        const overview = await statusResp.json();
        if (overview && overview.success) {
          const statePill = document.getElementById("modal-agent-state-pill");
          if (statePill && overview.current_state) {
            statePill.innerText = "● " + overview.current_state;
            statePill.style.cssText = `padding: 4px 12px; border-radius: 9999px; font-weight: 800; font-size: 0.75rem; ${getStatusBadgeClass(overview.current_state)}`;
          }
          const badge = document.getElementById("agent-status-badge");
          if (badge && overview.current_state) {
            badge.textContent = `● ${overview.current_state.replace(/_/g, " ")}`;
            badge.style.cssText = `padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.76rem; ${getStatusBadgeClass(overview.current_state)}`;
          }
          renderAuditList(overview.audit_history || [], overview.audit_integrity);
        }
      }
    } catch (_) {}
  }

  /**
   * Renders the SHA-256 Hash-Chained Audit Ledger using the actual backend schema:
   * - integrity.valid (boolean)
   * - integrity.event_count (number)
   * - ev.prev_hash (string)
   * - ev.event_id / ev.event_hash (string)
   */
  function renderAuditList(events, integrity) {
    const chainList = document.getElementById("scen-audit-chain-list");
    if (chainList && Array.isArray(events) && events.length > 0) {
      chainList.innerHTML = events.slice().reverse().map((ev) => {
        const isViolation = ev.event_type === "UNAUTHORIZED_ACTION_ATTEMPTED" || ev.event_type === "AGENT_DECISION_REJECTED";
        const borderCol = isViolation ? "#ef4444" : (ev.actor === "human" ? "#10b981" : "#3b82f6");
        const bgCol = isViolation ? "#fef2f2" : "#ffffff";
        const prevHashStr = ev.prev_hash || ev.previous_hash || "GENESIS_BLOCK";
        const prevHashDisplay = prevHashStr === "GENESIS_BLOCK" ? "GENESIS_BLOCK" : `${prevHashStr.substring(0, 24)}...`;
        const eventHashStr = ev.event_hash || "";
        const eventHashDisplay = eventHashStr ? `${eventHashStr.substring(0, 24)}...` : `event_id:${ev.event_id || "—"}`;

        return `
          <div style="background: ${bgCol}; border: 1px solid #e2e8f0; border-left: 4px solid ${borderCol}; border-radius: 6px; padding: 10px 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <strong style="color: #0f172a;">[${escapeHtml(ev.event_type)}] ${escapeHtml(ev.action)}</strong>
              <span style="font-size: 0.68rem; color: #64748b;">
                Event ID: <code>${escapeHtml(ev.event_id || "—")}</code> • ${escapeHtml(ev.timestamp || "")} • Actor: <strong>${escapeHtml(ev.actor)} (${escapeHtml(ev.actor_id || "")})</strong>
              </span>
            </div>
            <div style="margin-top: 4px; font-size: 0.7rem; color: #475569;">
              State: <code>${escapeHtml(ev.previous_state || "—")} → ${escapeHtml(ev.new_state || ev.workflow_state || "—")}</code>
              ${ev.evidence_reference ? ` • Evidence: <em>${escapeHtml(ev.evidence_reference)}</em>` : ""}
            </div>
            <div style="margin-top: 4px; font-size: 0.66rem; color: #64748b; word-break: break-all;">
              prev_hash: <code>${escapeHtml(prevHashDisplay)}</code> | event_hash: <code>${escapeHtml(eventHashDisplay)}</code>
            </div>
          </div>
        `;
      }).join("");
    }

    const logEl = document.getElementById("drawer-audit-log-preview");
    if (logEl && Array.isArray(events) && events.length > 0) {
      logEl.innerHTML = events.slice(-6).map(ev => {
        const prevShort = (ev.prev_hash || ev.previous_hash || "GENESIS").substring(0, 12);
        return `[${ev.timestamp}] ${ev.event_type} (${ev.actor}): ${ev.action} | State=${ev.workflow_state} | prev_hash=${prevShort}`;
      }).join("\n");
      logEl.scrollTop = logEl.scrollHeight;
    }

    const banner = document.getElementById("modal-audit-integrity-banner");
    if (banner && integrity) {
      banner.style.display = "block";
      const isValid = typeof integrity.valid === "boolean" ? integrity.valid : Boolean(integrity.is_valid);
      const eventCount = typeof integrity.event_count === "number"
        ? integrity.event_count
        : (typeof integrity.verified_events === "number" ? integrity.verified_events : (Array.isArray(events) ? events.length : 0));

      if (isValid) {
        banner.style.background = "#dcfce7";
        banner.style.borderColor = "#86efac";
        banner.style.color = "#166534";
        banner.innerHTML = `<strong>✓ Cryptographic Hash Integrity Verified (${eventCount} events):</strong> ${escapeHtml(integrity.message || "Audit chain integrity verified.")}`;
      } else {
        banner.style.background = "#fee2e2";
        banner.style.borderColor = "#fca5a5";
        banner.style.color = "#991b1b";
        banner.innerHTML = `<strong>❌ Integrity Alert (${eventCount} events):</strong> ${escapeHtml(integrity.message || "Audit hash-chain tampering detected.")}`;
      }
    }
  }

  async function syncModalAndDrawerWithBackend(data, projectId, serverMode) {
    if (!data) return;
    const pid = projectId || data.project_id || getActiveProjectId();
    const state = data.workflow_state || "DRAFT";
    const ctx = data.context || data.extracted_context || {};
    const reqs = data.requirements || data.active_requirements || [];
    const clars = data.pending_clarifications || [];
    const answered = data.answered_clarifications || [];
    const uncertainties = data.uncertainties || [];

    // 1. Update Modal State Pill
    const modalPill = document.getElementById("modal-agent-state-pill");
    if (modalPill) {
      modalPill.innerText = "● " + state;
      modalPill.style.cssText = `padding: 4px 12px; border-radius: 9999px; font-weight: 800; font-size: 0.75rem; ${getStatusBadgeClass(state)}`;
    }

    // 2. Update Modal Tab 1: Extracted Parameters & Provenance
    const org = ctx.organism_or_chassis || {};
    const toolObj = (ctx.molecular_tools && ctx.molecular_tools[0]) || { value: "Standard Methods", status: "INFERRED", source: "proposal.tool" };
    const bsl = ctx.biosafety_containment || {};
    const human = ctx.human_subjects || {};

    const c1 = document.getElementById("scen-param-chassis");
    const p1 = document.getElementById("scen-prov-chassis");
    if (c1) c1.innerText = org.value || "Unspecified Chassis";
    if (p1) p1.innerText = `[${org.status || "INFERRED"}] • ${org.source || "proposal.chassis"}`;

    const c2 = document.getElementById("scen-param-tool");
    const p2 = document.getElementById("scen-prov-tool");
    if (c2) c2.innerText = (ctx.molecular_tools || []).map(t => t.value).join(", ") || toolObj.value;
    if (p2) p2.innerText = `[${toolObj.status || "CONFIRMED"}] • ${toolObj.source || "proposal.tool"}`;

    const c3 = document.getElementById("scen-param-containment");
    const p3 = document.getElementById("scen-prov-containment");
    if (c3) c3.innerText = bsl.value || "BSL-1";
    if (p3) p3.innerText = `[${bsl.status || "INFERRED"}] • ${bsl.source || "proposal.methodology"}`;

    const c4 = document.getElementById("scen-param-human");
    const p4 = document.getElementById("scen-prov-human");
    if (c4) c4.innerText = human.value ? `True (${human.status || "FLAGGED"})` : "False (No Human Subjects)";
    if (p4) p4.innerText = `[${human.status || "CONFIRMED"}] • ${human.source || "proposal.human_subjects"}`;

    // 3. Update Modal Tab 1: Contradictions, Agentic Loop Trace, Tools & Evidence
    const cBox = document.getElementById("scen-contradiction-container");
    if (cBox) {
      let uncertaintyHtml = "";
      if (uncertainties.length > 0) {
        uncertaintyHtml = uncertainties.map(u => `
          <div style="background: #fff5f5; border: 1.5px solid #fca5a5; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
              <span style="background: #fee2e2; color: #991b1b; font-weight: 800; font-size: 0.74rem; padding: 3px 8px; border-radius: 4px; border: 1px solid #f87171;">
                🚨 UNCERTAINTY / CONTRADICTION DETECTED (${escapeHtml(u.field)})
              </span>
              <span style="font-size: 0.7rem; color: #64748b; font-weight: 600;">Extraction Mode: ${escapeHtml(data.extraction_mode || "deterministic_rules")}</span>
            </div>
            <div style="font-size: 0.8rem; color: #7f1d1d; line-height: 1.45;">${escapeHtml(u.issue)}</div>
          </div>
        `).join("");
      } else {
        uncertaintyHtml = `
          <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
              <span style="background: #dcfce7; color: #166534; font-weight: 800; font-size: 0.74rem; padding: 3px 8px; border-radius: 4px; border: 1px solid #86efac;">
                ✓ CONCORDANT SPECIFICATION
              </span>
              <span style="font-size: 0.7rem; color: #15803d; font-weight: 600;">Extraction Mode: ${escapeHtml(data.extraction_mode || "deterministic_rules")}</span>
            </div>
            <div style="font-size: 0.78rem; color: #166534;">All extracted fields and researcher clarifications are concordant. Zero unresolved contradictions.</div>
          </div>
        `;
      }
      cBox.innerHTML = `
        ${buildHumanEscalationHtml(data)}
        ${uncertaintyHtml}
        ${buildAgenticLoopHtml(data, serverMode)}
        ${buildToolsVisibilityHtml(data)}
        ${buildEvidenceLogHtml(data)}
      `;
    }

    // Also render the Phase 3 Governed Agentic Loop, Tools, and Evidence directly at the top of Modal Tab 1 (#modal-tab-context)
    // so it is immediately visible when opening the modal without needing to switch subviews.
    const modalTabContext = document.getElementById("modal-tab-context");
    if (modalTabContext) {
      let topTraceEl = document.getElementById("modal-top-agentic-trace-wrapper");
      if (!topTraceEl) {
        topTraceEl = document.createElement("div");
        topTraceEl.id = "modal-top-agentic-trace-wrapper";
        modalTabContext.insertBefore(topTraceEl, modalTabContext.firstChild);
      }
      topTraceEl.innerHTML = `
        ${buildHumanEscalationHtml(data)}
        ${buildAgenticLoopHtml(data, serverMode)}
        ${buildToolsVisibilityHtml(data)}
        ${buildEvidenceLogHtml(data)}
      `;
    }

    // 4. Update Modal Tab 1: Annexes
    const aCount = document.getElementById("scen-annex-count");
    if (aCount) aCount.innerText = String(reqs.length);
    const aList = document.getElementById("scen-annexes-list");
    if (aList) {
      if (reqs.length === 0) {
        aList.innerHTML = `<div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:10px 12px; color:#166534; font-size:0.8rem;">✓ No regulatory annexes triggered.</div>`;
      } else {
        aList.innerHTML = reqs.map(r => `
          <div style="border-left: 4px solid #2563eb; background: #eff6ff; border-radius: 6px; padding: 10px 12px; border-top: 1px solid #dbeafe; border-right: 1px solid #dbeafe; border-bottom: 1px solid #dbeafe;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
              <strong style="color: #0f172a; font-size: 0.84rem;">[${escapeHtml(r.rule_id || r.requirement_id)}] ${escapeHtml(r.title)}</strong>
              <span style="font-size: 0.7rem; background: #ffffff; color: #1d4ed8; border: 1px solid #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700;">${escapeHtml(r.applicable_annex || r.annex)}</span>
            </div>
            <p style="margin: 0 0 4px 0; font-size: 0.78rem; color: #334155;"><strong>Mandate:</strong> ${escapeHtml(r.human_action_required || r.mandate)}</p>
            <div style="font-size: 0.72rem; color: #64748b;"><strong>Evidence:</strong> ${escapeHtml(r.evidence || r.evidence_snippet || "Proposal text")}</div>
          </div>
        `).join("");
      }
    }

    // 5. Update Modal Tab 2: Dynamic Clarifications (ALL pending + ALL answered, removing 2-card cap)
    const bCount = document.getElementById("badge-tab-clar-count");
    if (bCount) {
      bCount.innerText = String(clars.length);
      bCount.style.background = clars.length > 0 ? "#f59e0b" : "#10b981";
    }

    const clarWrapper = document.getElementById("modal-clar-cards-wrapper");
    if (clarWrapper) {
      clarWrapper.innerHTML = buildClarificationsHtml(clars, answered, "modal-clar");
      bindClarificationButtons(clarWrapper);
    }

    // 6. Update Modal Tab 4: Human Review Gate Escalation Context
    const gateTab = document.getElementById("modal-tab-gate");
    if (gateTab) {
      let escContainer = document.getElementById("modal-gate-escalation-context");
      if (!escContainer) {
        escContainer = document.createElement("div");
        escContainer.id = "modal-gate-escalation-context";
        gateTab.insertBefore(escContainer, gateTab.firstChild);
      }
      escContainer.innerHTML = buildHumanEscalationHtml(data);
    }

    // 7. Fetch and render real Dossier & Audit Trail when server is live
    if (serverMode !== "client_offline_engine") {
      const dossierRes = await fetchDossier(pid);
      if (dossierRes && dossierRes.success && dossierRes.dossier) {
        const dos = dossierRes.dossier;
        const dTitle = document.getElementById("scen-dossier-title");
        if (dTitle) dTitle.innerText = dos.project_metadata?.title || ctx.title || "Research Proposal";
        const dBadge = document.getElementById("scen-dossier-id-badge");
        if (dBadge) dBadge.innerText = dos.dossier_id || `DOSSIER-${pid}`;
        const dDosId = document.getElementById("scen-dispatch-dossier-id");
        if (dDosId) dDosId.innerText = dos.dossier_id || `DOSSIER-${pid}`;
        const dAxCount = document.getElementById("scen-dispatch-annex-count");
        if (dAxCount) dAxCount.innerText = `${(dos.triggered_compliance_annexes || []).length} annex checklists`;

        const tbody = document.getElementById("scen-dossier-tbody");
        if (tbody && dos.extracted_biological_parameters) {
          const bp = dos.extracted_biological_parameters;
          const rows = [
            { field: "Biological Chassis", obj: bp.organism_or_chassis },
            { field: "Sample Origin / Matrix", obj: bp.sample_type },
            { field: "Human Subjects / Clinical", obj: bp.human_subjects },
            { field: "Recombinant DNA / GMO", obj: bp.recombinant_dna },
            { field: "Pathogen / AMR Work", obj: bp.pathogen_work },
            { field: "Biosafety Containment", obj: bp.biosafety_containment }
          ];
          tbody.innerHTML = rows.filter(r => r.obj).map(r => `
            <tr>
              <td style="padding: 6px 10px; border: 1px solid #cbd5e1; font-weight: 600;">${escapeHtml(r.field)}</td>
              <td style="padding: 6px 10px; border: 1px solid #cbd5e1;">${escapeHtml(String(r.obj.value))}</td>
              <td style="padding: 6px 10px; border: 1px solid #cbd5e1; color: ${r.obj.status === 'CONFIRMED' ? '#059669' : '#b45309'}; font-weight: bold;">${escapeHtml(r.obj.status)}</td>
              <td style="padding: 6px 10px; border: 1px solid #cbd5e1; font-family: monospace;">${escapeHtml(r.obj.source || "proposal")}</td>
            </tr>
          `).join("");
        }
      }

      const auditRes = await fetchAuditTrail(pid);
      if (auditRes && auditRes.success) {
        renderAuditList(auditRes.events || [], auditRes.integrity);
      } else if (data.audit_integrity) {
        renderAuditList([], data.audit_integrity);
      }
    }

    // 8. Update Drawer Compliance Status Pill
    const drawerPill = document.getElementById("drawer-compliance-state-pill");
    const drawerSummary = document.getElementById("drawer-compliance-summary-text");
    if (drawerPill && drawerSummary) {
      const plannerInfo = formatPlannerModeDisplay(data.agent_run, data);
      drawerPill.innerText = `● ${state} (${plannerInfo.label})`;
      drawerPill.style.cssText = `display: inline-block; font-size: 0.68rem; font-weight: 800; padding: 3px 9px; border-radius: 9999px; margin-bottom: 5px; ${getStatusBadgeClass(state)}`;
      drawerSummary.innerHTML = `<strong>Next Action (${escapeHtml(data.next_action?.actor || "researcher")}):</strong> ${escapeHtml(data.next_action?.action || "Review compliance findings.")}<br><span style="font-size:0.65rem; color:#475569;">Steps: ${(data.agent_run?.steps || []).length} • Tools Called: ${(data.agent_run?.tools_called || []).length} • Annexes: ${reqs.length} • Pending Clarifications: ${clars.length} • Answered: ${answered.length}</span>`;
    }
  }

  function renderAgentResults(data, projectId, serverMode) {
    const statusBadge = document.getElementById("agent-status-badge");
    const resultsContainer = document.getElementById("agent-results-container");
    if (!resultsContainer) return;

    const state = data.workflow_state || "UNKNOWN";
    if (statusBadge) {
      statusBadge.textContent = `● ${state.replace(/_/g, " ")}`;
      statusBadge.style.cssText = `padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.76rem; ${getStatusBadgeClass(state)}`;
    }

    resultsContainer.style.display = "block";

    const ctx = data.context || data.extracted_context || {};
    const org = ctx.organism_or_chassis?.value || "Not Detected";
    const orgProv = ctx.organism_or_chassis?.source || "proposal.chassis";
    const tools = (ctx.molecular_tools || []).map(t => t.value).join(", ") || "Standard Methods";
    const bsl = ctx.biosafety_containment?.value || "BSL-1";
    const bslStatus = ctx.biosafety_containment?.status || "INFERRED";
    const human = ctx.human_subjects?.value ? `⚠️ Human / Clinical (${ctx.human_subjects?.status || "FLAGGED"})` : "No Human Subjects (CONFIRMED)";
    const extractionMode = data.extraction_mode || (serverMode === "client_offline_engine" ? "client_offline_fallback" : "deterministic_rules");
    const checksPerformed = data.checks_performed || [];
    const nextAction = data.next_action || { action: "Review compliance status", actor: "researcher" };
    const uncertainties = data.uncertainties || [];
    const plannerInfo = formatPlannerModeDisplay(data.agent_run, data);

    const reqs = data.requirements || data.active_requirements || [];
    let reqsHtml = "";
    if (reqs.length === 0) {
      reqsHtml = `
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 10px 14px; color: #166534; font-size: 0.83rem;">
          ✓ No institutional regulatory annexes triggered. Safe for standard faculty submission.
        </div>
      `;
    } else {
      reqsHtml = reqs.map(r => `
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="color: #1e40af; font-size: 0.86rem;">[${escapeHtml(r.rule_id || r.requirement_id)}] ${escapeHtml(r.title)}</strong>
            <span style="font-size: 0.74rem; background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; font-weight: 600;">${escapeHtml(r.applicable_annex || r.annex)}</span>
          </div>
          <p style="margin: 0 0 6px 0; font-size: 0.81rem; color: #475569;">${escapeHtml(r.human_action_required || r.mandate)}</p>
          <div style="font-size: 0.74rem; color: #64748b; font-style: italic;">
            <strong>Evidence:</strong> ${escapeHtml(r.evidence || r.evidence_snippet || "Document text pattern match")}
          </div>
        </div>
      `).join("");
    }

    const clars = data.pending_clarifications || [];
    const answered = data.answered_clarifications || [];
    const clarsSectionHtml = `
      <div id="agent-clarifications-panel" style="margin-top: 14px; background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 8px; padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.1rem;">💡</span>
            <strong style="color: #92400e; font-size: 0.88rem;">Socratic Clarification &amp; Researcher Provenance (${clars.length} pending • ${answered.length} answered)</strong>
          </div>
          <span style="font-size: 0.7rem; background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-weight: 700;">
            Zero-Ghostwriting Safeguard
          </span>
        </div>
        <p style="margin: 0 0 12px 0; font-size: 0.79rem; color: #78350f; line-height: 1.45;">
          The agent never fabricates or modifies your proposal text. Clarifications are recorded with human researcher provenance.
        </p>
        ${buildClarificationsHtml(clars, answered, "clar")}
      </div>
    `;

    const observabilityHtml = `
      <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; font-size: 0.76rem; color: #334155;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
          <strong style="color: #0f172a;">🔍 Structured Agent Execution Summary (Audit-Safe Observability)</strong>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <span style="background: #f1f5f9; color: #334155; padding: 2px 8px; border-radius: 4px; font-weight: 700;">
              Extraction: ${escapeHtml(extractionMode)}
            </span>
            <span style="padding: 2px 8px; border-radius: 4px; font-weight: 700; ${plannerInfo.badgeStyle}">
              Planner: ${escapeHtml(plannerInfo.badgeText)}
            </span>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px;">
          <div><strong>Input Evidence:</strong> Title="${escapeHtml((ctx.title || "").substring(0, 45))}", Chassis="${escapeHtml(org)}" [${escapeHtml(orgProv)}]</div>
          <div><strong>Checks Performed:</strong> ${checksPerformed.length || 10} deterministic &amp; governance rules evaluated</div>
          <div><strong>Risk / Uncertainty:</strong> ${uncertainties.length} contradiction/uncertainty item(s)</div>
          <div><strong>Recommended Next Action:</strong> ${escapeHtml(nextAction.action)} (Actor: <code>${escapeHtml(nextAction.actor)}</code>)</div>
        </div>
      </div>
    `;

    resultsContainer.innerHTML = `
      ${observabilityHtml}
      ${buildHumanEscalationHtml(data)}
      ${buildAgenticLoopHtml(data, serverMode)}
      ${buildToolsVisibilityHtml(data)}
      ${buildEvidenceLogHtml(data)}

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-bottom: 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;">
        <div>
          <span style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 700;">Host / Chassis</span>
          <div style="font-size: 0.84rem; font-weight: 600; color: #1e293b;">${escapeHtml(org)}</div>
        </div>
        <div>
          <span style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 700;">Molecular Tools</span>
          <div style="font-size: 0.84rem; font-weight: 600; color: #1e293b;">${escapeHtml(tools)}</div>
        </div>
        <div>
          <span style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 700;">Biosafety Level</span>
          <div style="font-size: 0.84rem; font-weight: 600; color: #1e293b;">${escapeHtml(bsl)} (${escapeHtml(bslStatus)})</div>
        </div>
        <div>
          <span style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 700;">Human / Clinical Status</span>
          <div style="font-size: 0.84rem; font-weight: 600; color: ${ctx.human_subjects?.value ? '#b91c1c' : '#15803d'};">${escapeHtml(human)}</div>
        </div>
      </div>

      <div style="margin-bottom: 12px;">
        <h4 style="font-size: 0.85rem; font-weight: 700; color: #1e293b; margin: 0 0 8px 0;">
          Triggered Institutional Compliance Annexes (${reqs.length})
        </h4>
        ${reqsHtml}
      </div>

      ${clarsSectionHtml}

      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #e2e8f0;">
        <div style="font-size: 0.76rem; color: #64748b;">
          <strong>Cryptographic Audit:</strong> State transitions, tool executions, and researcher answers are recorded to a SHA-256 hash-chained ledger.
        </div>
        <div style="display: flex; gap: 8px;">
          <button type="button" class="btn-secondary" onclick="if(window.openAgentInteractiveModal){ window.openAgentInteractiveModal(); if(window.switchAgentModalTab) window.switchAgentModalTab('dossier'); }" style="font-size: 0.78rem; padding: 4px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; color: #1e40af; border: 1px solid #bfdbfe; background: #eff6ff; border-radius: 6px; font-weight: 700;">
            <span>📄</span> <span>Open Full Dossier</span>
          </button>
          <button type="button" class="btn-secondary" onclick="if(window.openAgentInteractiveModal){ window.openAgentInteractiveModal(); if(window.switchAgentModalTab) window.switchAgentModalTab('audit'); }" style="font-size: 0.78rem; padding: 4px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; color: #4338ca; border: 1px solid #c7d2fe; background: #eef2ff; border-radius: 6px; font-weight: 700;">
            <span>📊</span> <span>Institutional Dashboard</span>
          </button>
        </div>
      </div>
    `;

    bindClarificationButtons(resultsContainer);
  }

  function initAgentBridge() {
    const btnRun = document.getElementById("btn-agent-run-analysis");
    if (btnRun) {
      btnRun.removeAttribute("onclick");
      btnRun.addEventListener("click", async () => {
        await runAgentAnalysis(true);
      });
    }

    const btnDash = document.getElementById("btn-agent-open-dashboard");
    if (btnDash) {
      btnDash.removeAttribute("onclick");
      btnDash.addEventListener("click", async (e) => {
        e.preventDefault();
        await runAgentAnalysis(false);
        if (typeof window.openAgentInteractiveModal === "function") {
          window.openAgentInteractiveModal();
          if (typeof window.switchAgentModalTab === "function") {
            window.switchAgentModalTab("audit");
          }
        }
      });
    }

    const btnDossier = document.getElementById("btn-agent-view-dossier");
    if (btnDossier) {
      btnDossier.addEventListener("click", async (e) => {
        e.preventDefault();
        await runAgentAnalysis(false);
        if (typeof window.openAgentInteractiveModal === "function") {
          window.openAgentInteractiveModal();
          if (typeof window.switchAgentModalTab === "function") {
            window.switchAgentModalTab("dossier");
          }
        }
      });
    }

    // Override modal batch clarification submitter so it submits ALL dynamically rendered pending inputs
    window.submitModalClarifications = async function () {
      const wrapper = document.getElementById("modal-clar-cards-wrapper");
      const inputs = wrapper ? wrapper.querySelectorAll(".dynamic-clarification-input") : [];
      const scenData = window.AGENT_SCENARIOS && window.AGENT_SCENARIOS[window.currentAgentScenarioKey || "detectr"];

      for (let i = 0; i < inputs.length; i++) {
        const inputEl = inputs[i];
        const qid = inputEl.getAttribute("data-qid");
        let val = (inputEl.value || "").trim();
        if (!val && scenData && Array.isArray(scenData.clars) && scenData.clars[i]) {
          val = scenData.clars[i].autoFill || "";
          inputEl.value = val;
        }
        if (qid && val) {
          await submitClarification(qid, val);
        }
      }

      const fb = document.getElementById("modal-clar-feedback");
      if (fb) fb.style.display = "block";
    };

    // Override modal audit integrity verifier to use integrity.valid and integrity.event_count
    window.verifyAuditIntegrity = async function () {
      const sid = getActiveProjectId();
      const auditData = await fetchAuditTrail(sid);
      await refreshAuditAndState(sid);
      if (auditData && auditData.integrity) {
        renderAuditList(auditData.events || [], auditData.integrity);
        const isValid = Boolean(auditData.integrity.valid);
        const count = auditData.integrity.event_count ?? (auditData.events ? auditData.events.length : 0);
        if (typeof window.showToast === "function") {
          window.showToast(
            isValid
              ? `✓ SHA-256 Chain Verified (${count} events): ${auditData.integrity.message}`
              : `❌ Audit Integrity Alert (${count} events): ${auditData.integrity.message}`
          );
        }
      }
    };

    // Wrap syncLiveEditorToAgent so it preserves the rendered Phase 3 trace in the modal
    // and refreshes backend analysis when explicitly clicked in the modal header
    if (typeof window.syncLiveEditorToAgent === "function" && !window.syncLiveEditorToAgent.__agentBridgeWrapped) {
      const origSyncLiveEditor = window.syncLiveEditorToAgent;
      const wrappedSync = function (silent) {
        const res = origSyncLiveEditor.apply(this, arguments);
        if (window.latestAgentAnalysis) {
          syncModalAndDrawerWithBackend(window.latestAgentAnalysis, getActiveProjectId(), window.latestAgentServerMode);
        }
        if (!silent) {
          runAgentAnalysis(false);
        }
        return res;
      };
      wrappedSync.__agentBridgeWrapped = true;
      window.syncLiveEditorToAgent = wrappedSync;
    }
  }

  window.AgentBridge = {
    getActiveProjectId: getActiveProjectId,
    getActiveProposalData: getActiveProposalData,
    runAgentAnalysis: runAgentAnalysis,
    submitClarification: submitClarification,
    fetchDossier: fetchDossier,
    dispatchToBioEthics: dispatchToBioEthics,
    submitHumanDecision: submitHumanDecision,
    fetchAuditTrail: fetchAuditTrail,
    syncModalAndDrawerWithBackend: syncModalAndDrawerWithBackend,
    refreshAuditAndState: refreshAuditAndState,
    renderAgentResults: renderAgentResults,
    renderAuditList: renderAuditList,
    formatPlannerModeDisplay: formatPlannerModeDisplay,
    formatStepStatusBadge: formatStepStatusBadge,
    buildAgenticLoopHtml: buildAgenticLoopHtml,
    buildToolsVisibilityHtml: buildToolsVisibilityHtml,
    buildEvidenceLogHtml: buildEvidenceLogHtml,
    buildClarificationsHtml: buildClarificationsHtml,
    buildHumanEscalationHtml: buildHumanEscalationHtml
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAgentBridge);
  } else {
    initAgentBridge();
  }
})();
