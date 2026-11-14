import os

with open('upload/static/js/studio.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('matrixPdfInput.addEventListener')
print('Index:', idx)
print(text[idx+500:idx+2500])
