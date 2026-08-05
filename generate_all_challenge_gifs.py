import os
import re
import shutil
from pathlib import Path

OUT_DIR = Path('static/workouts')
APP_PY = Path('app.py')

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")

def choose_base(name: str) -> str:
    n = name.lower()
    if 'push' in n:
        return 'push-up'
    if 'squat' in n or 'step-up' in n or 'goblet' in n or 'pistol' in n or 'split squat' in n or 'jump squat' in n:
        return 'squat'
    if 'plank' in n:
        return 'plank'
    if 'lunge' in n:
        return 'lunge'
    if 'burpee' in n:
        return 'burpee'
    if 'mountain' in n or 'climber' in n:
        return 'mountain-climber'
    if 'jack' in n or 'jump' in n or 'rope' in n or 'run' in n or 'sprint' in n:
        return 'jumping-jacks'
    # rows, pulls, chin-ups, etc. map to push-up as a neutral placeholder
    return 'push-up'

def extract_challenge_names(app_text: str):
    start = app_text.find('REGION_CONFIG')
    if start == -1:
        return []
    # find the opening brace
    brace = app_text.find('{', start)
    if brace == -1:
        return []
    i = brace
    depth = 0
    while i < len(app_text):
        if app_text[i] == '{':
            depth += 1
        elif app_text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
        i += 1
    region_text = app_text[brace:end+1]

    names = []
    # iterate each challenges list
    for m in re.finditer(r'"challenges"\s*:\s*\[', region_text):
        s = m.end()
        # find matching ] bracket
        j = s
        d = 0
        while j < len(region_text):
            if region_text[j] == '[':
                d += 1
            elif region_text[j] == ']':
                if d == 0:
                    end_idx = j
                    break
                d -= 1
            j += 1
        else:
            end_idx = j
        block = region_text[s:end_idx]
        # extract "name": "..."
        found = re.findall(r'"name"\s*:\s*"([^"]+)"', block)
        for name in found:
            names.append(name)

    return names

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = APP_PY.read_text(encoding='utf-8')
    names = extract_challenge_names(text)
    names = list(dict.fromkeys(names))
    print(f'Found {len(names)} unique challenge names')

    created = 0
    for name in names:
        slug = slugify(name)
        base = choose_base(name)
        src = OUT_DIR / f"{base}.gif"
        dst = OUT_DIR / f"{slug}.gif"
        if dst.exists():
            print('Exists', dst)
            continue
        if not src.exists():
            print('Missing base gif for', base, '->', src)
            continue
        shutil.copy(src, dst)
        created += 1
        print('Created', dst)

    print(f'Created {created} new GIFs in {OUT_DIR}')

if __name__ == '__main__':
    main()
