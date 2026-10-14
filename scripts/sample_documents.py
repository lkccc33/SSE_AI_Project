from pathlib import Path
import csv, random, shutil, os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('SSE_SOURCE_DIR', '/root/autodl-tmp/SSE_Agent/workspace/full/papers'))
SEED = 20261014
manifest = ROOT / 'data/sample_manifest.csv'
if manifest.exists():
    print(f'Existing manifest preserved: {manifest}')
    raise SystemExit(0)
files = sorted(SOURCE.glob('*/processed/paper.llm.md'))
if len(files) < 100:
    raise SystemExit(f'Expected >=100 source papers, found {len(files)}')
rng = random.Random(SEED)
samples = sorted(rng.sample(files, 100), key=lambda p: p.parent.parent.name)
rows=[]
for i, src in enumerate(samples, 1):
    paper_id = src.parent.parent.name
    dst_name = f'{i:03d}_{paper_id}.md'
    shutil.copy2(src, ROOT/'data/source_md'/dst_name)
    rows.append({'sample_id': f'{i:03d}', 'paper_id': paper_id, 'sample_filename': dst_name,
                 'original_filename': src.name, 'original_path': str(src), 'size_bytes': src.stat().st_size})
with manifest.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(f'Sampled {len(rows)} of {len(files)} with seed {SEED}; copied read-only source inputs into {ROOT}/data/source_md')
