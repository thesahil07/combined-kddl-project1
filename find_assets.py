import re
import glob

all_scripts = set()
for fn in glob.glob("tmp_*.html"):
    with open(fn, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    scripts = re.findall(r'src="(/assets/[^"]+\.js)"', html)
    preloads = re.findall(r'href="(/assets/[^"]+\.js)"', html)
    all_scripts.update(scripts)
    all_scripts.update(preloads)

for s in sorted(all_scripts):
    print(s)
