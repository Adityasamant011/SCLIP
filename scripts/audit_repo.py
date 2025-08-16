import os
import sys
import hashlib
from pathlib import Path

"""
Repo Audit Script
- Lists duplicate files by content hash
- Flags likely-unused Python files (no imports/refs) within apps/sidecar
- Flags multiple entrypoints and confusing duplicates
Usage: python scripts/audit_repo.py
"""

ROOT = Path(__file__).resolve().parents[1]

def file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def find_duplicates(base: Path):
    hashes = {}
    for p in base.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.py', '.ts', '.tsx', '.json', '.css', '.md'}:
            try:
                h = file_hash(p)
                hashes.setdefault(h, []).append(p)
            except Exception:
                pass
    dups = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    return dups

def guess_unused_python(base: Path):
    # naive heuristic: python files under apps/sidecar not imported anywhere
    py_files = [p for p in (base / 'apps' / 'sidecar').rglob('*.py') if p.is_file()]
    index = {}
    for p in py_files:
        index[p.stem] = p
    # scan for import mentions
    mentioned = set()
    for p in py_files:
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            for name in index.keys():
                if name == p.stem:
                    continue
                if f'import {name}' in text or f'from {name} ' in text or f'.{name} import' in text:
                    mentioned.add(index[name])
        except Exception:
            continue
    unused = [p for p in py_files if p not in mentioned and p.name not in {'__init__.py'}]
    return unused

def main():
    print(f"Auditing repo at {ROOT}")
    dups = find_duplicates(ROOT)
    if dups:
        print("\nDuplicate files (by SHA-256):")
        for h, paths in dups.items():
            print(f"- {h[:12]}:")
            for p in paths:
                try:
                    print(f"  • {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")
                except Exception:
                    print(f"  • {p}")
    else:
        print("\nNo duplicates found among scanned file types.")

    unused = guess_unused_python(ROOT)
    if unused:
        print("\nPossibly unused Python files under apps/sidecar (heuristic):")
        for p in unused:
            print(f"- {p.relative_to(ROOT)}")
    else:
        print("\nNo obviously unused Python files detected by heuristic.")

    # Multiple entrypoints
    entrypoints = list((ROOT / 'apps' / 'sidecar' / 'app').glob('main*.py'))
    if len(entrypoints) > 1:
        print("\nMultiple FastAPI entrypoints detected:")
        for p in entrypoints:
            print(f"- {p.relative_to(ROOT)}")

if __name__ == '__main__':
    main()


