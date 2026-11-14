import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = '@app.route("/api/student/toggle_lock", methods=["POST"])'
replacement = '@app.route("/api/student/lock", methods=["POST"])\n@app.route("/api/student/toggle_lock", methods=["POST"])'

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Added /api/student/lock alias to app.py")
