#!/usr/bin/env python
"""Fix structlog-style logger calls → standard logging format across the project"""
import re, os, glob

APP_DIR = os.path.join(os.path.dirname(__file__), '..', 'app')

def fix_file(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    def fix_call(m):
        method = m.group(1)
        msg = m.group(2)
        kwargs_str = m.group(3)

        pairs = []
        for pair in kwargs_str.split(','):
            pair = pair.strip()
            if '=' not in pair:
                continue
            key, _, val = pair.partition('=')
            pairs.append((key.strip(), val.strip()))

        new_msg = msg
        args = []
        for key, val in pairs:
            new_msg += f' {key}=%s'
            args.append(val)

        if args:
            return f'logger.{method}("{new_msg}", {", ".join(args)})'
        return m.group(0)

    pattern = re.compile(
        r'logger\.(info|error|warning|debug)\("([^"]+)",\s*([^)]+)\)'
    )

    new_content = pattern.sub(fix_call, content)

    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return 1
    return 0

fixed = 0
for root, dirs, files in os.walk(APP_DIR):
    for f in files:
        if f.endswith('.py'):
            fpath = os.path.join(root, f)
            try:
                fixed += fix_file(fpath)
            except:
                pass

print(f'Fixed {fixed} files')
