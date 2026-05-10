#!/usr/bin/env python3
"""
Incremental upload: only upload files changed since last git commit.
Usage: python sync_to_wiki.py [wiki_root_token] [space_id]
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDIjb2qNitz/yNrozeoEFdPA02U6J7hmYFfqCtIsLZlofla/S+aMRjgEOae1JhKbEAXgrBhk92twbi83nJgfoXuhQ5rYXU044depVl0Kelm5IwJJgjgfh
  90R2XMfvESrMvANgJl+IwA2Ya14BBTOA0/clGvmlHhxRyXJH8DuVl+DtDHTE1Y3i+kRuDtvA9+g6FspEsJIYE2FHYBHu0k+csNkejo42OMtDaK8OV6Tf+eC9JBWTcMPl8BgE//vCLPpL9kvsrLr4wv1wzS
  8KEngiQZEIaAY2duqIhlEQ7wUFiFCr9dKplg3Y5tnUT1kgpCUbMJ3cm5bgJC3QrDfhT/HHWHK4NnrVMIrU2k90psPQOBOitYoqJz2czJbSm0DEmzSPie6DumD9lOiL1gPhwHSCk83X4oonqwi4D84B6khH
  7uO6cEg4u5HxfrY1Gi3pjozB95qhGY4QsyVrnAF2LsbCrkRBrPc0678CSYPDIzYyu8J0M8867M7051F8WQ7weOTSDSHJfPbGTiXqtHxj44ciCSenPyxGaGZGpyqUaLat5IJlCoOgn91thYVKeu0lBz04CZ
  DzndCmt+2Vogs+v1oxvOevoKdaxOL/93fc7spmJ2U2Ekc/za9W5zZ2g8Vg0YJYnvh0NJYOszu3pPDYccY0UHLap1M6NtNuHSGb5GqngGGQ== your_email@example.com
Works for both 思想者 and 数据面试 directories.
First run uploads all; subsequent runs only upload changed/new files.
"""
import json, subprocess, time, sys, os, re, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

LARK_JS = r'C:\nvm4w\nodejs\node_modules\@larksuite\cli\scripts\run.js'

# Config per project - detected automatically
CONFIGS = {
    '思想者': {
        'space_id': '7637912601518672853',
        'root_token': 'SSpCwYqvWi0jTtkcWn6cDvv8nsh',
    },
    '数据面试': {
        'space_id': '7637545856980847573',
        'root_token': 'YevSwoBVeieLiqkyagPcewroni8',
        'folder_map': {
            'Java篇': 'ReVgwZ7OSilpbakd4vNcJ7Zrnbd',
            'Mysql': 'Mbp2wxqZAijBtBkr4n8crCBznZc',
            'Redis篇': 'S6QFwojTgi4uAUk6qUUcQyJhnj1',
            '大数据面试': 'ZxM7wtx1Iiaw5SkaFBccp5Kznqd',
            'Node全栈知识': 'HGbDwbu2niOE3ekrH34cf1QWnhe',
            '操作系统': 'N6MZwAVKIiJpHKkMt5icN8vtnAd',
            '计算机网络': 'YrY6wMZHxiNx8qk47j0c6vJrnae',
            '人工智能': 'Q9sqw816PiH26PkE9UocWOzxnVd',
            '场景架构': 'Q57dwyz3viOrpEkjzJfcQm83nwh',
            '数据结构': 'JGZZwcpAoieXwlkRDQyccGNFnsL',
            '简历篇': 'FDbEwXiPTiaTbOkjKCVchRrDnrc',
            'Netty解读': 'QyL3wWkuZisPu1klG0rcZCDVnSe',
            '番外篇': 'QMQBwezH1i6eWxkqhUFc8xxUncf',
            '运维篇': 'H4h9w6kXji9eX7kOsAbckBBZnhh',
        },
    },
}

def detect_project():
    """Auto-detect which project we're in."""
    dirname = os.path.basename(BASE)
    if dirname in CONFIGS:
        return dirname, CONFIGS[dirname]
    # fallback: check for known folders
    for name, cfg in CONFIGS.items():
        if os.path.exists(os.path.join(BASE, '.git')):
            # check folder names
            pass
    return dirname, None

def run_lark(args, timeout=60):
    r = subprocess.run(['node', LARK_JS] + args, capture_output=True, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.stderr or '')

def get_nodes(space_id, pt):
    params = json.dumps({"space_id": space_id, "parent_node_token": pt})
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

def create_node(space_id, parent, title):
    out = run_lark(['wiki','+node-create','--parent-node-token',parent,'--space-id',space_id,'--title',title,'--obj-type','docx'])
    for line in out.split('\n'):
        m = re.search(r'"node_token":\s*"([^"]+)"', line.strip())
        if m: return m.group(1)
    return None

def update_doc(space_id, token, fpath):
    rel = os.path.relpath(fpath, BASE).replace("\\", "/")
    out = run_lark(['docs','+update','--doc',token,'--markdown','@'+rel,'--mode','overwrite'], timeout=30)
    return '"ok": true' in out

def get_all_titles(space_id, pt):
    titles = set()
    for n in get_nodes(space_id, pt):
        if n.get('has_child'):
            titles.update(get_all_titles(space_id, n['node_token']))
        else:
            titles.add(n['title'])
    return titles

def get_changed_files():
    """Get list of .md files changed since last commit (or untracked)."""
    # Get staged + unstaged changes
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], capture_output=True, encoding='utf-8', errors='replace')
    changed = result.stdout.strip().split('\n') if result.stdout.strip() else []

    result2 = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, encoding='utf-8', errors='replace')
    staged = result2.stdout.strip().split('\n') if result2.stdout.strip() else []

    result3 = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, encoding='utf-8', errors='replace')
    untracked = result3.stdout.strip().split('\n') if result3.stdout.strip() else []

    all_changed = set(changed + staged + untracked)
    return [f for f in all_changed if f.endswith('.md') and os.path.exists(f)]

def resolve_parent(space_id, fpath, cfg):
    """Resolve the wiki parent token for a local file path."""
    rel = os.path.relpath(fpath, BASE).replace("\\", "/")
    parts = rel.split("/")

    if 'folder_map' in cfg:
        fmap = cfg['folder_map']
        top_folder = parts[0]
        if top_folder in fmap:
            return fmap[top_folder], True
        # Not in map - skip
        return None, False

    # 思想者 style: create sub-categories under root
    root = cfg['root_token']
    current = root
    for j in range(len(parts) - 1):
        folder = parts[j]
        children = {n['title']: n['node_token'] for n in get_nodes(space_id, current)}
        if folder in children:
            current = children[folder]
        else:
            nt = create_node(space_id, current, folder)
            if nt:
                current = nt
            else:
                return None, False
            time.sleep(0.1)
    return current, True

# === Main ===
project_name, cfg = detect_project()
if not cfg:
    print(f"Unknown project: {project_name}")
    print(f"Create a CONFIGS entry for '{project_name}' in this script.")
    sys.exit(1)

space_id = cfg['space_id']
root_token = cfg['root_token']

print(f"Project: {project_name}")
print(f"Space: {space_id}")
print(f"Root: {root_token}")

# Get changed files
changed = get_changed_files()
print(f"\nChanged .md files: {len(changed)}")

if not changed:
    print("No changes to sync!")
    sys.exit(0)

for f in changed:
    print(f"  {f}")

# Get existing wiki titles
print(f"\nScanning wiki...")
existing = get_all_titles(space_id, root_token)
print(f"  Wiki has {len(existing)} docs")

# Upload
print(f"\nSyncing...")
uploaded = 0
updated = 0
failed = 0

for fpath in sorted(changed):
    title = os.path.splitext(os.path.basename(fpath))[0]

    parent, ok = resolve_parent(space_id, fpath, cfg)
    if not ok:
        print(f"  SKIP (no parent): {fpath}")
        continue

    if title in existing:
        # Find the node token to update content
        # For simplicity, search in parent
        nodes = get_nodes(space_id, parent)
        node = next((n for n in nodes if n['title'] == title), None)
        if node:
            if update_doc(space_id, node['node_token'], fpath):
                updated += 1
                print(f"  UPDATED [{updated}]: {title[:50]}")
            else:
                failed += 1
                print(f"  UPDATE FAIL: {title[:50]}")
            time.sleep(0.15)
        else:
            print(f"  SKIP (not found in wiki): {title[:50]}")
    else:
        # New file - create node and upload
        nt = create_node(space_id, parent, title)
        if not nt:
            failed += 1
            print(f"  CREATE FAIL: {title[:50]}")
            continue
        time.sleep(0.1)
        if update_doc(space_id, nt, fpath):
            uploaded += 1
            print(f"  NEW [{uploaded}]: {title[:50]}")
        else:
            failed += 1
            print(f"  UPLOAD FAIL: {title[:50]}")
        time.sleep(0.15)

print(f"\nDone: {uploaded} new, {updated} updated, {failed} failed")
if failed == 0:
    print("Tip: commit your changes with 'git add -A && git commit -m \"sync\"' after uploading.")
