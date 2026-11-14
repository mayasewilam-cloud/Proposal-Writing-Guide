// Comprehensive verification test suite for Phase 3B.2.2 Client-side fixes (Repairs B, C, D)
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const studioJsCode = fs.readFileSync(path.join(__dirname, "../static/js/studio.js"), "utf8");

// Mock browser DOM environment
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

global.projectState = { student_id: "20230001" };
global.getStudentStorageKey = (sid) => {
  const id = sid || (global.projectState && global.projectState.student_id) || "GUEST";
  return `bt301_student_draft_${id.toUpperCase()}`;
};
global.isStaticEnvironment = () => false;

// Extract lines for PhotoRecoveryError, prepareDraftPayloadForServer, saveToStorage, syncDraftToServer
const startIdx = studioJsCode.indexOf("let isRehydratingPhotos = false;");
const endIdx = studioJsCode.indexOf("function loadFromStorage(studentId)");
eval(studioJsCode.slice(startIdx, endIdx));

// Also extract syncDraftToServer
const syncStart = studioJsCode.indexOf("async function syncDraftToServer(showNotification = true)");
const syncEnd = studioJsCode.indexOf("function copyAnalystTLDR()");
eval(studioJsCode.slice(syncStart, syncEnd));

console.log("=== Running Phase 3B.2.2 Client-Side Unit Tests ===");

async function testRepairB_PhotoRecoveryError_ThrowsWhenMissing() {
  console.log("\n[Test B.1] Verify prepareDraftPayloadForServer throws PhotoRecoveryError on missing IDB photo...");
  
  // Set up mock state with [stored_in_idb]
  const state = {
    student_id: "20230001",
    title: "Test Proposal",
    results_figure: {
      caption: "Gel electrophoresis",
      data_url: "[stored_in_idb]"
    }
  };
  
  // Mock BioWriterPhotoDB returning null (photo lost/missing)
  global.BioWriterPhotoDB = {
    getPhoto: async (key) => null
  };
  
  let threw = false;
  try {
    await prepareDraftPayloadForServer(state, "20230001");
  } catch (err) {
    threw = true;
    assert.strictEqual(err.name, "PhotoRecoveryError", "Should be PhotoRecoveryError");
    assert.strictEqual(err.photoField, "results_figure");
    assert.strictEqual(err.photoKey, "bt301_student_draft_20230001_results_photo");
  }
  assert.strictEqual(threw, true, "Must throw PhotoRecoveryError when IDB image cannot be recovered");
  // Crucial: Original state must NOT have deleted the data_url or wiped the figure
  assert.ok(state.results_figure.data_url, "Local state data_url must NOT be deleted");
  console.log("  PASS: PhotoRecoveryError thrown and local draft photograph reference preserved.");
}

async function testRepairB_PhotoRecoveryError_RecoversWhenPresent() {
  console.log("\n[Test B.2] Verify prepareDraftPayloadForServer rehydrates data_url when present...");
  
  const state = {
    student_id: "20230001",
    title: "Test Proposal",
    results_figure: {
      caption: "Gel electrophoresis",
      data_url: "[stored_in_idb]"
    }
  };
  
  const fakeDataUrl = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
  global.BioWriterPhotoDB = {
    getPhoto: async (key) => fakeDataUrl
  };
  
  const payload = await prepareDraftPayloadForServer(state, "20230001");
  assert.strictEqual(payload.results_figure.data_url, fakeDataUrl, "Payload must have rehydrated photo");
  assert.strictEqual(state.results_figure.data_url, fakeDataUrl, "State must have rehydrated photo");
  console.log("  PASS: Photo properly rehydrated when present in IndexedDB.");
}

async function testRepairC1_SaveSequenceInterleaving() {
  console.log("\n[Test C.1] Verify saveToStorage aborts stale save write when newer save sequence started...");
  
  // Mock localStorage
  let storage = {};
  global.localStorage = {
    getItem: (k) => storage[k] || null,
    setItem: (k, v) => {
      // Simulate quota error on full state
      if (v.length > 1000) {
        const err = new Error("QuotaExceededError");
        err.name = "QuotaExceededError";
        throw err;
      }
      storage[k] = v;
    }
  };

  global.currentAuthUser = { student_id: "20230001" };
  global.projectState = {
    student_id: "20230001",
    title: "Large Draft with image",
    results_figure: {
      data_url: "data:image/png;base64," + "A".repeat(2000)
    }
  };

  // Delayed IDB save to simulate race condition
  let idbResolve;
  global.BioWriterPhotoDB = {
    savePhoto: (key, data) => new Promise(resolve => {
      idbResolve = resolve;
    })
  };

  // Start save 1 (which will hit quota error and await IDB)
  const save1Promise = saveToStorage();

  // Now, before save 1 IDB completes, trigger save 2 (e.g. user keystroke)
  global.projectState.title = "Updated Draft Title";
  // For save 2, make it fit within quota so it finishes immediately
  global.projectState.results_figure = null;
  const save2Promise = saveToStorage();
  const save2Result = await save2Promise;
  assert.strictEqual(save2Result, true, "Save 2 should succeed immediately");
  assert.ok(storage["bt301_student_draft_20230001"].includes("Updated Draft Title"));

  // Now resolve save 1 IDB write
  idbResolve(true);
  const save1Result = await save1Promise;
  
  // Verify save 1 recognized it was superseded and did NOT overwrite storage with older state
  assert.strictEqual(save1Result, false, "Save 1 must return false because it was superseded");
  const finalStorage = storage["bt301_student_draft_20230001"];
  assert.ok(finalStorage.includes("Updated Draft Title"), "Storage must retain Save 2 content and not be overwritten by Save 1");
  console.log("  PASS: Stale asynchronous save write properly aborted; LocalStorage protected from corruption.");
}

async function testRepairC2_LocalSaveFailureHaltsCloudSync() {
  console.log("\n[Test C.2] Verify failed local save halts cloud sync in syncDraftToServer...");
  
  // Mock localStorage failing completely
  global.localStorage = {
    setItem: () => {
      throw new Error("Storage failure");
    }
  };
  global.BioWriterPhotoDB = null;

  global.projectState = {
    student_id: "20230001",
    title: "Draft that fails local save"
  };

  let serverFetchCalled = false;
  global.fetch = async () => {
    serverFetchCalled = true;
    return { ok: true, json: async () => ({ success: true }) };
  };

  const syncResult = await syncDraftToServer(true);
  assert.strictEqual(syncResult, false, "syncDraftToServer should return false on local save failure");
  assert.strictEqual(serverFetchCalled, false, "Server fetch must NOT be called if local save failed");
  const saveIndicator = document.getElementById("save-status");
  assert.ok(saveIndicator.innerText.includes("⚠️ Local Save Failed"), "Indicator must display warning");
  console.log("  PASS: Local storage failure correctly halts server sync and alerts student.");
}

async function testRepairD_Timeouts() {
  console.log("\n[Test D] Verify 30-second AbortController timeouts on fetch and decode...");
  
  // Check static source code for AbortController timeouts
  assert.ok(studioJsCode.includes("setTimeout(() => controller.abort(), 30000)"), "Must include 30000ms timeout");
  
  // Verify fetchPaperMetadataClient source has 30000 timeout
  const fetchMetadataSection = studioJsCode.slice(
    studioJsCode.indexOf("async function fetchPaperMetadataClient"),
    studioJsCode.indexOf("async function fetchPaperMetadataClient") + 700
  );
  assert.ok(fetchMetadataSection.includes("30000"), "fetchPaperMetadataClient must use 30000ms timeout");

  // Verify runDecodePaper source has 30000 timeout and AbortController
  const runDecodeSection = studioJsCode.slice(
    studioJsCode.indexOf("async function runDecodePaper(payload)"),
    studioJsCode.indexOf("async function runDecodePaper(payload)") + 1200
  );
  assert.ok(runDecodeSection.includes("controller ? setTimeout(() => controller.abort(), 30000) : null"), "runDecodePaper must use 30000ms timeout");
  assert.ok(runDecodeSection.includes("signal: controller ? controller.signal : undefined"), "runDecodePaper must pass AbortSignal");

  console.log("  PASS: 30-second AbortController timeout consistently configured across paper decode and fetch endpoints.");
}

async function runAll() {
  try {
    await testRepairB_PhotoRecoveryError_ThrowsWhenMissing();
    await testRepairB_PhotoRecoveryError_RecoversWhenPresent();
    await testRepairC1_SaveSequenceInterleaving();
    await testRepairC2_LocalSaveFailureHaltsCloudSync();
    await testRepairD_Timeouts();
    console.log("\n>>> ALL CLIENT-SIDE REPAIR TESTS PASSED (5/5) <<<\n");
  } catch (err) {
    console.error("Test failed:", err);
    process.exit(1);
  }
}

runAll();
