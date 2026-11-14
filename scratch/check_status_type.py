import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('is_ret = bool(metadata.get("is_retracted"))')
print(text[idx:idx+1500])
