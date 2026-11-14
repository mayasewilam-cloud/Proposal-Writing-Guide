import json
manifest_path = r"C:\Users\Lenovo\.gemini\antigravity\brain\d4f217ee-1064-43a4-b719-3a8627874e18\scratch\phase4_1_4_pre_data_manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    pre_manifest = json.load(f)

for k in list(pre_manifest.keys())[:5]:
    print("pre_manifest key:", repr(k))
