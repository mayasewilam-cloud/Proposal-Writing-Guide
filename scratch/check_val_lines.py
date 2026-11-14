with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(180, 240):
    print(f"{i+1}: {repr(lines[i])}")
