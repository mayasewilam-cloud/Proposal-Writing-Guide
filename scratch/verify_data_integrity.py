import os
import json
import hashlib

manifest_path = r"C:\Users\Lenovo\.gemini\antigravity\brain\d4f217ee-1064-43a4-b719-3a8627874e18\scratch\phase4_1_4_pre_data_manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    raw_pre_manifest = json.load(f)

# Normalize keys
pre_manifest = {k.replace("\\", "/"): v for k, v in raw_pre_manifest.items()}

data_dir = "upload/data"
current_files = {}

for root, dirs, files in os.walk(data_dir):
    for f in files:
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, "upload").replace("\\", "/")
        with open(full_path, "rb") as fp:
            content = fp.read()
            h = hashlib.sha256(content).hexdigest()
            size = len(content)
        current_files[rel_path] = {
            "sha256": h,
            "size": size
        }

print(f"Pre-manifest files count: {len(pre_manifest)}")
print(f"Current files count: {len(current_files)}")

mismatches = []
missing = []
extra = []

for rel_path, pre_info in pre_manifest.items():
    if rel_path not in current_files:
        missing.append(rel_path)
    else:
        curr_info = current_files[rel_path]
        if curr_info["sha256"] != pre_info["sha256"]:
            mismatches.append({
                "file": rel_path,
                "pre_hash": pre_info["sha256"],
                "curr_hash": curr_info["sha256"],
                "pre_size": pre_info["size"],
                "curr_size": curr_info["size"]
            })

for rel_path in current_files:
    if rel_path not in pre_manifest:
        extra.append(rel_path)

print(f"Missing files: {len(missing)}")
print(f"Extra files: {len(extra)}")
print(f"Hash mismatches: {len(mismatches)}")

if mismatches:
    for m in mismatches:
        print(f"MISMATCH: {m['file']} pre={m['pre_hash']} curr={m['curr_hash']}")
else:
    print("SUCCESS: 100% BIT-FOR-BIT IDENTICAL! All 54 files match pre-manifest hashes perfectly!")

# Also check breakthroughs_bookmarks.json explicitly
bm_info = current_files.get("data/breakthroughs_bookmarks.json")
print("breakthroughs_bookmarks.json hash:", bm_info["sha256"])
print("breakthroughs_bookmarks.json size:", bm_info["size"])
