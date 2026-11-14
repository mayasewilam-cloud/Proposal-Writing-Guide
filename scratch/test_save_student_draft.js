const assert = require("assert");
const fs = require("fs");
const path = require("path");

const studioJsCode = fs.readFileSync(path.join(__dirname, "../static/js/studio.js"), "utf8");

global.window = global;
global.document = {
  getElementById: (id) => {
    if (!global._elements[id]) {
      global._elements[id] = {
        id,
        value: "",
        innerText: "",
        style: {},
        disabled: false,
        innerHTML: "",
        onclick: null,
        focus: () => {}
      };
    }
    return global._elements[id];
  },
  querySelector: () => ({ innerText: "" })
};
global._elements = {};
global.showToast = (msg, type) => {
  global._lastToast = { msg, type };
};
global.scrapeAllDomInputsToProjectState = () => {};
global.isStaticEnvironment = () => false;
global.isRehydratingPhotos = false;
global.photoRehydrationPromise = null;
global.currentAuthUser = { student_id: "20230001" };
global.projectState = { student_id: "20230001", title: "Test Draft" };
global.getStudentStorageKey = (sid) => `bt301_student_draft_${(sid || "GUEST").toUpperCase()}`;

// Eval PhotoRecoveryError, prepareDraftPayloadForServer
const p1Start = studioJsCode.indexOf("class PhotoRecoveryError extends Error");
const p1End = studioJsCode.indexOf("async function saveToStorage()");
eval(studioJsCode.slice(p1Start, p1End));

// Eval saveStudentDraftToServer
const sStart = studioJsCode.indexOf("async function saveStudentDraftToServer(userInitiated = false)");
const sEnd = studioJsCode.indexOf("// PART 1 & 3: GOVERNANCE");
eval(studioJsCode.slice(sStart, sEnd));

async function testSaveStudentDraftToServer() {
  console.log("=== Testing saveStudentDraftToServer error handling ===");

  // Scenario 1: Local save fails -> halts server sync
  global.saveToStorage = async () => false;
  let serverFetchCalled = false;
  global.fetch = async () => {
    serverFetchCalled = true;
    return { ok: true, json: async () => ({ success: true }) };
  };

  const res1 = await saveStudentDraftToServer(true);
  assert.strictEqual(res1, false, "Must return false when local save fails");
  assert.strictEqual(serverFetchCalled, false, "Must not call server fetch when local save fails");
  const saveIndicator = document.getElementById("save-status");
  assert.ok(saveIndicator.innerText.includes("⚠️ Local Save Failed"), "Indicator must reflect local save failure");
  console.log("  PASS: Local save failure halts server sync");

  // Scenario 2: Photo recovery error -> halts server sync
  global.saveToStorage = async () => true;
  global.BioWriterPhotoDB = { getPhoto: async () => null };
  global.projectState.results_figure = { data_url: "[stored_in_idb]" };
  serverFetchCalled = false;

  const res2 = await saveStudentDraftToServer(true);
  assert.strictEqual(res2, false, "Must return false when PhotoRecoveryError thrown");
  assert.strictEqual(serverFetchCalled, false, "Must not call server fetch on PhotoRecoveryError");
  assert.ok(saveIndicator.innerText.includes("⚠️ Server Sync Halted"), "Indicator must reflect sync halt");
  assert.strictEqual(global.projectState.results_figure.data_url, "[stored_in_idb]", "Local draft figure must not be deleted");
  console.log("  PASS: PhotoRecoveryError halts server sync and preserves local photo reference");

  // Scenario 3: Normal successful sync
  global.projectState.results_figure = null;
  serverFetchCalled = false;
  global.fetch = async () => {
    serverFetchCalled = true;
    return {
      ok: true,
      json: async () => ({ success: true, student_id: "20230001", updated_at: "Nov 09, 2026 - 23:50" })
    };
  };
  const res3 = await saveStudentDraftToServer(true);
  assert.strictEqual(serverFetchCalled, true, "Server fetch called on valid draft");
  assert.ok(saveIndicator.innerText.includes("🟢 Cloud Server Synced"), "Indicator reflects successful sync");
  console.log("  PASS: Normal draft saves to server and reflects green indicator");

  console.log("\n>>> ALL saveStudentDraftToServer TESTS PASSED <<<");
}

testSaveStudentDraftToServer();
