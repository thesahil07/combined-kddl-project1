with open('tmp_utils.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re
matches = [m.start() for m in re.finditer(r'ready_now', code)]
for idx in matches[-5:]:
    print(code[max(0, idx - 100): min(len(code), idx + 200)])
    print("---")
