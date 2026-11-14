import os
import shutil

studio_js_path = os.path.abspath('upload/static/js/studio.js')
root_studio_js_path = os.path.abspath('upload/studio.js')

with open(studio_js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Block 1: PhotoRecoveryError and prepareDraftPayloadForServer
t1 = """// Photo rehydration state and save sequence tracking
let isRehydratingPhotos = false;
let photoRehydrationPromise = null;
let currentSaveSequence = 0;

async function prepareDraftPayloadForServer(state, sid) {
  if (isRehydratingPhotos && photoRehydrationPromise) {
    try {
      await photoRehydrationPromise;
    } catch (_) {}
  }
  const payload = JSON.parse(JSON.stringify(state));
  const key = getStudentStorageKey(sid);

  // Results figure rehydration verification
  if (payload.results_figure) {
    const rfUrl = payload.results_figure.data_url;
    if (rfUrl === "[stored_in_idb]" || (typeof rfUrl === "string" && rfUrl.startsWith("[stored_in_idb"))) {
      if (window.BioWriterPhotoDB && typeof window.BioWriterPhotoDB.getPhoto === "function") {
        const recovered = await window.BioWriterPhotoDB.getPhoto(key + "_results_photo");
        if (recovered) {
          payload.results_figure.data_url = recovered;
          if (state.results_figure) state.results_figure.data_url = recovered;
        } else {
          delete payload.results_figure.data_url;
        }
      } else {
        delete payload.results_figure.data_url;
      }
    }
  }

  // Flowchart img rehydration verification
  const fcUrl = payload.flowchart_img;
  if (fcUrl === "[stored_in_idb]" || (typeof fcUrl === "string" && fcUrl.startsWith("[stored_in_idb"))) {
    if (window.BioWriterPhotoDB && typeof window.BioWriterPhotoDB.getPhoto === "function") {
      const recovered = await window.BioWriterPhotoDB.getPhoto(key + "_flowchart_img");
      if (recovered) {
        payload.flowchart_img = recovered;
        state.flowchart_img = recovered;
      } else {
        delete payload.flowchart_img;
      }
    } else {
      delete payload.flowchart_img;
    }
  }

  return payload;
}"""

r1 = """// Photo rehydration state and save sequence tracking
let isRehydratingPhotos = false;
let photoRehydrationPromise = null;
let currentSaveSequence = 0;

class PhotoRecoveryError extends Error {
  constructor(message, photoKey, photoField) {
    super(message);
    this.name = "PhotoRecoveryError";
    this.photoKey = photoKey;
    this.photoField = photoField;
  }
}
if (typeof window !== "undefined") {
  window.PhotoRecoveryError = PhotoRecoveryError;
}

async function prepareDraftPayloadForServer(state, sid) {
  if (isRehydratingPhotos && photoRehydrationPromise) {
    try {
      await photoRehydrationPromise;
    } catch (_) {}
  }
  const payload = JSON.parse(JSON.stringify(state));
  const key = getStudentStorageKey(sid);

  // Results figure rehydration verification
  if (payload.results_figure) {
    const rfUrl = payload.results_figure.data_url;
    if (rfUrl === "[stored_in_idb]" || (typeof rfUrl === "string" && rfUrl.startsWith("[stored_in_idb"))) {
      if (window.BioWriterPhotoDB && typeof window.BioWriterPhotoDB.getPhoto === "function") {
        const recovered = await window.BioWriterPhotoDB.getPhoto(key + "_results_photo");
        if (recovered) {
          payload.results_figure.data_url = recovered;
          if (state.results_figure) state.results_figure.data_url = recovered;
        } else {
          throw new PhotoRecoveryError("Failed to recover results figure from IndexedDB.", key + "_results_photo", "results_figure");
        }
      } else {
        throw new PhotoRecoveryError("BioWriterPhotoDB not available to recover results figure.", key + "_results_photo", "results_figure");
      }
    }
  }

  // Flowchart img rehydration verification
  const fcUrl = payload.flowchart_img;
  if (fcUrl === "[stored_in_idb]" || (typeof fcUrl === "string" && fcUrl.startsWith("[stored_in_idb"))) {
    if (window.BioWriterPhotoDB && typeof window.BioWriterPhotoDB.getPhoto === "function") {
      const recovered = await window.BioWriterPhotoDB.getPhoto(key + "_flowchart_img");
      if (recovered) {
        payload.flowchart_img = recovered;
        state.flowchart_img = recovered;
      } else {
        throw new PhotoRecoveryError("Failed to recover flowchart image from IndexedDB.", key + "_flowchart_img", "flowchart_img");
      }
    } else {
      throw new PhotoRecoveryError("BioWriterPhotoDB not available to recover flowchart image.", key + "_flowchart_img", "flowchart_img");
    }
  }

  return payload;
}"""

assert t1 in content, "Target 1 not found"
content = content.replace(t1, r1, 1)

# 2. Block 2: Recheck sequence before LocalStorage write and sequence return in saveToStorage
t2a = """        if (allIdbOk) {
          localStorage.setItem(key, JSON.stringify(lightweightState));
          saveSuccess = true;
        } else {"""

r2a = """        if (allIdbOk) {
          // Condition 3 / Repair C1: Recheck seq !== currentSaveSequence immediately before writing to LocalStorage
          if (seq !== currentSaveSequence) {
            console.warn("Stale save sequence detected before writing to localStorage; aborting write.");
            return false;
          }
          localStorage.setItem(key, JSON.stringify(lightweightState));
          saveSuccess = true;
        } else {"""

assert t2a in content, "Target 2a not found"
content = content.replace(t2a, r2a, 1)

t2b = """  // Prevent older asynchronous saves from overwriting newer save status
  if (seq !== currentSaveSequence) {
    return saveSuccess;
  }"""

r2b = """  // Prevent older asynchronous saves from overwriting newer save status
  if (seq !== currentSaveSequence) {
    return false;
  }"""

assert t2b in content, "Target 2b not found"
content = content.replace(t2b, r2b, 1)

# 3. Block 3: syncDraftToServer
t3 = """async function syncDraftToServer(showNotification = true) {
  if (isStaticEnvironment()) {
    await saveToStorage();
    if (showNotification) showToast("Draft saved locally (Offline/Static Mode)", "info");
    return;
  }
  const sid = (projectState.student_id || "").trim();
  if (!sid) {
    if (showNotification) showToast("Please enter a Student ID / Team Code first.", "warning");
    const idEl = document.getElementById("student-id-input");
    if (idEl) idEl.focus();
    return;
  }
  const payloadState = await prepareDraftPayloadForServer(projectState, sid);
  try {
    const resp = await fetch("/api/student/save_draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        student_data: payloadState
      })
    });
    const res = await resp.json();
    if (res.success) {
      if (showNotification) {
        showToast(`✅ Proposal draft synced to server under ID ${res.student_id} (${res.updated_at})!`);
      }
      const stEl = document.querySelector(".save-status-text");
      if (stEl) stEl.innerText = `Synced to Server (${res.updated_at})`;
    }
  } catch (e) {
    console.error("Draft sync error:", e);
    if (showNotification) showToast("Network error syncing draft to server.");
  }
}"""

r3 = """async function syncDraftToServer(showNotification = true) {
  if (isStaticEnvironment()) {
    await saveToStorage();
    if (showNotification) showToast("Draft saved locally (Offline/Static Mode)", "info");
    return;
  }
  const sid = (projectState.student_id || "").trim();
  if (!sid) {
    if (showNotification) showToast("Please enter a Student ID / Team Code first.", "warning");
    const idEl = document.getElementById("student-id-input");
    if (idEl) idEl.focus();
    return;
  }

  // Condition 3 / Repair C2: Require successful local persistence before cloud sync
  const localOk = await saveToStorage();
  if (!localOk) {
    if (showNotification) showToast("⚠️ Cannot sync to server: Local browser save failed.", "warning");
    const saveIndicator = document.getElementById("save-status");
    if (saveIndicator) {
      saveIndicator.innerText = "⚠️ Local Save Failed - Storage Error (Click to retry)";
      saveIndicator.style.color = "#dc2626";
      saveIndicator.style.cursor = "pointer";
      saveIndicator.onclick = () => syncDraftToServer(showNotification);
    }
    return false;
  }

  // Condition 2 / Repair B: Handle PhotoRecoveryError during payload preparation
  let payloadState;
  try {
    payloadState = await prepareDraftPayloadForServer(projectState, sid);
  } catch (photoErr) {
    console.error("Photo recovery failed during server sync:", photoErr);
    if (showNotification) {
      showToast(`⚠️ Sync halted: Unable to recover photograph (${photoErr.photoField || "attached image"}). Please re-upload or retry.`, "warning");
    }
    const saveIndicator = document.getElementById("save-status");
    if (saveIndicator) {
      saveIndicator.innerText = "⚠️ Sync halted: Image recovery error (Click to retry)";
      saveIndicator.style.color = "#dc2626";
      saveIndicator.style.cursor = "pointer";
      saveIndicator.onclick = () => syncDraftToServer(true);
    }
    return false;
  }

  try {
    const resp = await fetch("/api/student/save_draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        student_data: payloadState
      })
    });
    const res = await resp.json();
    if (res.success) {
      if (showNotification) {
        showToast(`✅ Proposal draft synced to server under ID ${res.student_id} (${res.updated_at})!`);
      }
      const stEl = document.querySelector(".save-status-text");
      if (stEl) stEl.innerText = `Synced to Server (${res.updated_at})`;
    }
  } catch (e) {
    console.error("Draft sync error:", e);
    if (showNotification) showToast("Network error syncing draft to server.");
  }
}"""

assert t3 in content, "Target 3 not found"
content = content.replace(t3, r3, 1)

# 4. Block 4: saveStudentDraftToServer
t4 = """async function saveStudentDraftToServer(userInitiated = false) {
  scrapeAllDomInputsToProjectState();
  await saveToStorage();
  if (isStaticEnvironment() || (currentAuthUser && currentAuthUser.is_guest)) {
    const saveIndicator = document.getElementById("save-status");
    if (saveIndicator) {
      saveIndicator.innerText = "🟡 Local Browser Storage Only (Not Synced to Server)";
      saveIndicator.style.color = "#b45309";
    }
    if (userInitiated) showToast("Draft saved to local browser storage (Offline/Guest mode).");
    return;
  }

  const sid = (projectState.student_id || (currentAuthUser ? currentAuthUser.student_id : "") || "ST-2026-01").trim();
  const btn = document.getElementById("btn-sync-server-draft");
  const saveIndicator = document.getElementById("save-status");

  if (btn && userInitiated) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> <span>Saving...</span>`;
  }

  const payloadState = await prepareDraftPayloadForServer(projectState, sid);
  try {
    const resp = await fetch("/api/student/save_draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        student_data: payloadState
      })
    });
    const res = await resp.json();
    if (resp.ok && res.success) {
      if (saveIndicator) {
        saveIndicator.innerText = `🟢 Cloud Server Synced (${res.updated_at || "now"})`;
        saveIndicator.style.color = "#059669";
      }
      if (userInitiated) showToast(`Draft synced to server database for ${res.student_id}!`);
    } else {
      if (saveIndicator) {
        saveIndicator.innerText = "🟡 Saved in Browser Storage Only (Server Sync Rejected)";
        saveIndicator.style.color = "#b45309";
      }
    }
  } catch (e) {
    console.error("Cloud save failed", e);
    if (saveIndicator) {
      saveIndicator.innerText = "🟡 Saved in Browser Storage Only (Cloud Server Unreachable)";
      saveIndicator.style.color = "#b45309";
    }
  } finally {
    if (btn && userInitiated) {
      btn.disabled = false;
      btn.innerHTML = `<span>💾</span> <span class="btn-save-text">Save Draft</span>`;
    }
  }
}"""

r4 = """async function saveStudentDraftToServer(userInitiated = false) {
  scrapeAllDomInputsToProjectState();
  const saveIndicator = document.getElementById("save-status");

  // Condition 3 / Repair C2: Require successful local persistence before cloud sync
  const localOk = await saveToStorage();
  if (!localOk) {
    if (saveIndicator) {
      saveIndicator.innerText = "⚠️ Local Save Failed - Storage Error (Click to retry)";
      saveIndicator.style.color = "#dc2626";
      saveIndicator.style.cursor = "pointer";
      saveIndicator.onclick = () => saveStudentDraftToServer(userInitiated);
    }
    if (userInitiated) {
      showToast("⚠️ Could not persist draft to local browser storage. Server sync halted.", "warning");
    }
    return false;
  }

  if (isStaticEnvironment() || (currentAuthUser && currentAuthUser.is_guest)) {
    if (saveIndicator) {
      saveIndicator.innerText = "🟡 Local Browser Storage Only (Not Synced to Server)";
      saveIndicator.style.color = "#b45309";
    }
    if (userInitiated) showToast("Draft saved to local browser storage (Offline/Guest mode).");
    return;
  }

  const sid = (projectState.student_id || (currentAuthUser ? currentAuthUser.student_id : "") || "ST-2026-01").trim();
  const btn = document.getElementById("btn-sync-server-draft");

  if (btn && userInitiated) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> <span>Saving...</span>`;
  }

  // Condition 2 / Repair B: Handle PhotoRecoveryError during payload preparation
  let payloadState;
  try {
    payloadState = await prepareDraftPayloadForServer(projectState, sid);
  } catch (photoErr) {
    console.error("Photo recovery failed during server sync:", photoErr);
    if (saveIndicator) {
      saveIndicator.innerText = "⚠️ Server Sync Halted: Image recovery error (Click to retry)";
      saveIndicator.style.color = "#dc2626";
      saveIndicator.style.cursor = "pointer";
      saveIndicator.onclick = () => saveStudentDraftToServer(userInitiated);
    }
    if (userInitiated) {
      showToast(`⚠️ Sync halted: Unable to recover photograph (${photoErr.photoField || "attached image"}) from browser storage. Your text draft is safe locally. Please re-upload the photo or click to retry.`, "warning");
    }
    return false;
  }

  try {
    const resp = await fetch("/api/student/save_draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: sid,
        student_data: payloadState
      })
    });
    const res = await resp.json();
    if (resp.ok && res.success) {
      if (saveIndicator) {
        saveIndicator.innerText = `🟢 Cloud Server Synced (${res.updated_at || "now"})`;
        saveIndicator.style.color = "#059669";
      }
      if (userInitiated) showToast(`Draft synced to server database for ${res.student_id}!`);
    } else {
      if (saveIndicator) {
        saveIndicator.innerText = "🟡 Saved in Browser Storage Only (Server Sync Rejected)";
        saveIndicator.style.color = "#b45309";
      }
    }
  } catch (e) {
    console.error("Cloud save failed", e);
    if (saveIndicator) {
      saveIndicator.innerText = "🟡 Saved in Browser Storage Only (Cloud Server Unreachable)";
      saveIndicator.style.color = "#b45309";
    }
  } finally {
    if (btn && userInitiated) {
      btn.disabled = false;
      btn.innerHTML = `<span>💾</span> <span class="btn-save-text">Save Draft</span>`;
    }
  }
}"""

assert t4 in content, "Target 4 not found"
content = content.replace(t4, r4, 1)

# 5. Block 5: fetchPaperMetadataClient timeout 6000 -> 30000
t5 = """  // Tier 1: Try Flask Backend if reachable (/api/paper/fetch)
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    const resp = await fetch("/api/paper/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: cleanId }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);"""

r5 = """  // Tier 1: Try Flask Backend if reachable (/api/paper/fetch)
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    const resp = await fetch("/api/paper/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: cleanId }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);"""

assert t5 in content, "Target 5 not found"
content = content.replace(t5, r5, 1)

# 6. Block 6: runDecodePaper add AbortController
t6 = """      // Tier 1: Try Python Flask Backend if reachable
      try {
        const resp = await fetch("/api/paper/decode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const contentType = resp.headers.get("content-type") || "";
        if (resp.ok && contentType.includes("json")) {
          const json = await resp.json();
          if (json && json.status !== "error") {
            data = json;
          }
        }
      } catch (beErr) {
        console.warn("Backend /api/paper/decode unreachable or static host, switching to client NLP decoder:", beErr);
      }"""

r6 = """      // Tier 1: Try Python Flask Backend if reachable
      try {
        const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        const timeoutId = controller ? setTimeout(() => controller.abort(), 30000) : null;
        try {
          const resp = await fetch("/api/paper/decode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller ? controller.signal : undefined
          });
          const contentType = resp.headers.get("content-type") || "";
          if (resp.ok && contentType.includes("json")) {
            const json = await resp.json();
            if (json && json.status !== "error") {
              data = json;
            }
          }
        } finally {
          if (timeoutId) clearTimeout(timeoutId);
        }
      } catch (beErr) {
        console.warn("Backend /api/paper/decode unreachable or timed out, switching to client NLP decoder:", beErr);
      }"""

assert t6 in content, "Target 6 not found"
content = content.replace(t6, r6, 1)

# Write updated content back to upload/static/js/studio.js
with open(studio_js_path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Successfully patched upload/static/js/studio.js")

# Copy upload/static/js/studio.js to root upload/studio.js for absolute parity
shutil.copy2(studio_js_path, root_studio_js_path)
print("Copied to upload/studio.js - absolute byte parity achieved")
