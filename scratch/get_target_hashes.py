import os
import hashlib

files = [
    "upload/core/reference_service.py",
    "upload/core/impact_novelty_engine.py",
    "upload/core/paper_analyst_llm.py",
    "upload/core/breakthroughs_manager.py",
    "upload/static/js/studio.js",
    "upload/studio.js",
    "upload/app.py",
    "upload/tests/test_breakthroughs.py",
    "upload/tests/test_phase3b_repair.py",
    "upload/tests/test_phase4_1_4_scientific_integrity.py"
]

for p in files:
    if os.path.exists(p):
        with open(p, "rb") as f:
            content = f.read()
            h = hashlib.sha256(content).hexdigest()
            print(f"{p}: SHA256={h} Size={len(content)} bytes")
    else:
        print(f"Missing: {p}")
