import re

path = 'upload/static/js/studio.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''    if (!res.success) {
      projectState.is_locked_for_grading = currentLock;
      applyLockStateToUI(currentLock);
      saveToStorage();
      showToast(`⛔ ${res.error || "Lock action blocked by citation validation."}`, 7000);
      return;
    }'''

new_block = '''    if (!res.success) {
      projectState.is_locked_for_grading = currentLock;
      applyLockStateToUI(currentLock);
      saveToStorage();
      if (resp.status === 409 || res.status === "draft_changed_retry" || res.conflict) {
        showToast(`⚠️ Conflict: ${res.error || "The proposal draft was modified during citation verification. Please review the updated draft and retry submission."}`, 8000);
      } else {
        showToast(`⛔ ${res.error || "Lock action blocked by citation validation."}`, 7000);
      }
      return;
    }'''

assert old_block in content, "old_block not found in studio.js"
content = content.replace(old_block, new_block)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Successfully updated studio.js with 409 conflict handling!")
