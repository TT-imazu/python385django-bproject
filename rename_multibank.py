import os

src = 'budget/templates/budget/multibank_sample_with_accordion.html'
dst = 'budget/templates/budget/multibank.html'

if os.path.exists(src):
    os.rename(src, dst)
    print(f'Renamed: {src} -> {dst}')
else:
    print(f'File not found: {src}') 