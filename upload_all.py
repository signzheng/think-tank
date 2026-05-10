#!/usr/bin/env python3
"""Batch upload 思想者 directory to wiki."""
import json, subprocess, time, sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

LARK_JS = r'C:\nvm4w\nodejs\node_modules\@larksuite\cli\scripts\run.js'
SPACE_ID = '7637912601518672853'
ROOT_TOKEN = 'SSpCwYqvWi0jTtkcWn6cDvv8nsh'

def run_lark(args, timeout=60):
    r = subprocess.run(['node', LARK_JS] + args, capture_output=True, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')

def get_nodes(pt):
    params = json.dumps({"space_id": SPACE_ID, "parent_node_token": pt})
    out = run_lark(['wiki','nodes','list','--params',params,'--page-all','--page-limit','0','--jq','.data.items[]|{node_token,title,has_child}'])
    nodes = []
    for c in out.split('}\n{'):
        c = c.strip()
        if not c.startswith('{'): c = '{' + c
        if not c.endswith('}'): c = c + '}'
        try:
            d = json.loads(c)
            if 'node_token' in d: nodes.append(d)
        except: pass
    return nodes

def create_node(parent, title):
    out = run_lark(['wiki','+node-create','--parent-node-token',parent,'--space-id',SPACE_ID,'--title',title,'--obj-type','docx'])
    for line in out.split('\n'):
        m = re.search(r'"node_token":\s*"([^"]+)"', line.strip())
        if m: return m.group(1)
    return None

def update_doc(token, fpath):
    rel = os.path.relpath(fpath, BASE).replace("\\", "/")
    out = run_lark(['docs','+update','--doc',token,'--markdown','@'+rel,'--mode','overwrite'], timeout=30)
    return '"ok": true' in out

def get_all_titles(pt):
    titles = set()
    for n in get_nodes(pt):
        if n.get('has_child'):
            titles.update(get_all_titles(n['node_token']))
        else:
            titles.add(n['title'])
    return titles

# Step 1: Check root and get existing titles
print("Scanning wiki...")
existing = get_all_titles(ROOT_TOKEN)
print(f"  Wiki has {len(existing)} docs")

# Step 2: Collect all local .md files
all_files = []
for f in glob.glob(os.path.join(BASE, '**', '*.md'), recursive=True):
    all_files.append(f)
print(f"  Local has {len(all_files)} .md files")

# Step 3: Upload - create sub-categories and docs
uploaded = 0
skipped = 0
failed = 0
subcat_cache = {}  # (parent_token, folder_name) -> node_token

for fpath in sorted(all_files):
    title = os.path.splitext(os.path.basename(fpath))[0]

    if title in existing:
        skipped += 1
        continue

    # Determine parent by directory path
    rel = os.path.relpath(fpath, BASE)
    parts = rel.replace("\\", "/").split("/")

    # Navigate/create path
    current = ROOT_TOKEN
    for j in range(len(parts) - 1):
        folder = parts[j]
        key = (current, folder)
        if key in subcat_cache:
            current = subcat_cache[key]
        else:
            # Check if exists
            children = {n['title']: n['node_token'] for n in get_nodes(current) if n.get('has_child')}
            all_children = {n['title']: n['node_token'] for n in get_nodes(current)}
            if folder in children:
                current = children[folder]
            elif folder in all_children:
                current = all_children[folder]
            else:
                # Create sub-category
                nt = create_node(current, folder)
                if nt:
                    current = nt
                else:
                    print(f"  FAIL create folder: {folder}")
                    failed += 1
                    break
                time.sleep(0.1)
            subcat_cache[key] = current
    else:
        # Create doc and upload content
        nt = create_node(current, title)
        if not nt:
            failed += 1
            print(f"  CREATE FAIL: {title[:40]}")
            continue
        time.sleep(0.1)

        if update_doc(nt, fpath):
            uploaded += 1
            if uploaded % 10 == 0:
                print(f"  Progress: {uploaded} uploaded")
        else:
            failed += 1
            print(f"  UPLOAD FAIL: {title[:40]}")
        time.sleep(0.15)

print(f"\nDone: {uploaded} uploaded, {skipped} skipped, {failed} failed")
