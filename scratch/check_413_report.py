import os
artifact_dir = r"C:\Users\Lenovo\.gemini\antigravity\brain\d4f217ee-1064-43a4-b719-3a8627874e18"
report_path = os.path.join(artifact_dir, "BIOWRITER_PHASE_4_1_3_INDEPENDENT_VERIFICATION_REPORT.md")

with open(report_path, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("test_phase3b_repair")
while idx != -1:
    print(text[max(0, idx-100):min(len(text), idx+300)])
    print("-" * 50)
    idx = text.find("test_phase3b_repair", idx + 20)
