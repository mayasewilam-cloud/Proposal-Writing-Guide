with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(70, 130):
    print(f"{i+1}: {repr(lines[i])}")
