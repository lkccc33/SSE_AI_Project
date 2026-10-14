from pathlib import Path
import csv,hashlib,json,logging
R=Path(__file__).resolve().parents[1]
logging.basicConfig(filename=R/'logs/log.txt',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
rows=[]
for r in csv.DictReader((R/'data/sample_manifest.csv').open(encoding='utf-8')):
 src=Path(r['original_path']); dst=R/'data/source_md'/r['sample_filename']
 a=digest(src); b=digest(dst); rows.append({'sample_id':r['sample_id'],'original_path':str(src),'copy':str(dst),'sha256_original':a,'sha256_copy':b,'match':a==b})
with (R/'data/source_integrity.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(f'Source copy hash checks: {sum(x["match"] for x in rows)}/{len(rows)} match')
if not all(x['match'] for x in rows): raise SystemExit('Source copy differs; inspect integrity report')
logging.info('Source integrity verified %d/%d copies',len(rows),len(rows))
