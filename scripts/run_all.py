"""One-command orchestration. Inputs are only the 100 fixed local copies."""
from pathlib import Path
import logging, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
logging.basicConfig(filename=ROOT/'logs/log.txt',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
for script in ['sample_documents.py','verify_sources.py','extract.py','build_kg.py','train_model.py','write_summary.py']:
    path=ROOT/'scripts'/script
    logging.info('Starting stage %s',script)
    try:
        p=subprocess.run([sys.executable,str(path)],cwd=ROOT,text=True,capture_output=True,timeout=86400)
        if p.stdout: print(p.stdout.strip())
        if p.stderr: print(p.stderr[-5000:],file=sys.stderr)
        if p.returncode: logging.error('Stage %s failed rc=%d stderr=%s',script,p.returncode,p.stderr[-5000:]); print(f'WARNING: stage {script} failed; continuing')
        else: logging.info('Completed stage %s',script)
    except Exception as e:
        logging.exception('Stage %s exception: %s',script,e); print(f'WARNING: stage {script} exception: {e}')
print(f'Pipeline finished. See {ROOT}/logs/log.txt')
