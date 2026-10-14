"""Candidate extraction from the fixed 100 paper copies; all outputs are unverified."""
from pathlib import Path
import csv,json,logging,os,re,ast
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
logging.basicConfig(filename=ROOT/'logs/log.txt',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')

class LocalLLM:
 def __init__(self):
  self.model=None; self.proc=None; self.name='regex_fallback'
  path=Path(os.environ.get('SSE_LLM_MODEL','/root/autodl-tmp/HaloAgent/models/huggingface/Qwen3.5-4B'))
  if os.environ.get('SSE_USE_LLM','1')!='1' or not path.exists(): return
  try:
   import torch
   from transformers import AutoProcessor,AutoModelForImageTextToText
   self.proc=AutoProcessor.from_pretrained(str(path),local_files_only=True)
   self.model=AutoModelForImageTextToText.from_pretrained(str(path),torch_dtype='auto',device_map='auto',local_files_only=True)
   self.name='local:'+path.name
  except Exception as e:
   logging.exception('LLM load failed; fallback: %s',e); self.model=None
 def extract(self,context,paper_id):
  if self.model is None: return None
  import torch
  schema='{"material_name":null,"composition_formula":null,"dopants":[],"synthesis_method":null,"synthesis_conditions":null,"ionic_conductivity_value":null,"ionic_conductivity_unit":null,"conductivity_temperature_C":null,"air_stability":"unclear","air_stability_evidence":null,"electrochemical_window_value":null,"electrochemical_window_unit":null,"evidence":null}'
  prompt=('Extract explicit solid electrolyte facts only. Return exactly one JSON object, no explanation, double-quoted keys. '
   'Use null for unknown, [] for dopants; air_stability is stable, unstable, mixed, or unclear. Do not infer numbers. '
   'Copy short evidence phrases from text. Schema: '+schema+'\nTEXT:\n'+context[:4200])
  msgs=[{'role':'user','content':prompt}]
  try:
   ids=self.proc.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors='pt').to(self.model.device)
  except TypeError:
   ids=self.proc.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True,return_tensors='pt').to(self.model.device)
  mask=torch.ones_like(ids)
  with torch.inference_mode(): out=self.model.generate(input_ids=ids,attention_mask=mask,max_new_tokens=240,do_sample=False)
  answer=self.proc.decode(out[0][ids.shape[-1]:],skip_special_tokens=True).strip()
  (DATA/'llm_responses'/f'{paper_id}.txt').write_text(answer,encoding='utf-8')
  answer=re.sub(r'```(?:json)?|```','',answer,flags=re.I).strip()
  m=re.search(r'\{.*\}',answer,re.S)
  if not m: raise ValueError('no JSON in response: '+answer[:180])
  chunk=m.group(0)
  try: obj=json.loads(chunk)
  except Exception:
   fixed=re.sub(r'([{,]\s*)([A-Za-z_][\w]*)(\s*:)',r'\1"\2"\3',chunk)
   try: obj=ast.literal_eval(fixed)
   except Exception: obj=json.loads(fixed.replace("'",'"'))
  return obj

def fallback(text):
 formulas=[]
 for x in re.findall(r'(?<![A-Za-z])Li\d*(?:\.\d+)?[A-Z][A-Za-z0-9().]*',text):
  if x not in formulas: formulas.append(x)
 cond=re.search(r'(?i)(\d+(?:\.\d+)?\s*(?:mS|S)\s*cm\s*(?:−1|-1))',text)
 low=text.lower(); stable=any(t in low for t in ['air stable','moisture stable','stable in air','stable against moisture'])
 unstable=any(t in low for t in ['air-sensitive','air sensitive','moisture-sensitive','moisture sensitive','h2s release','h2s evolution'])
 label='mixed' if stable and unstable else 'stable' if stable else 'unstable' if unstable else 'unclear'
 terms=['air stable','moisture stable','stable in air','stable against moisture'] if stable else ['air-sensitive','air sensitive','moisture-sensitive','moisture sensitive','h2s release','h2s evolution']
 quote=None
 for t in terms:
  i=low.find(t)
  if i>=0: quote=text[max(0,i-100):i+180].replace('\n',' '); break
 synth=next((x for x in ['ball milling','mechanochemical','solid-state reaction','melt quenching','sintering'] if x in low),None)
 return {'material_name':None,'composition_formula':formulas[0] if formulas else None,'dopants':[],'synthesis_method':synth,'synthesis_conditions':None,'ionic_conductivity_value':cond.group(1) if cond else None,'ionic_conductivity_unit':None,'conductivity_temperature_C':None,'air_stability':label,'air_stability_evidence':quote,'electrochemical_window_value':None,'electrochemical_window_unit':None,'evidence':None}

def main():
 (DATA/'llm_responses').mkdir(exist_ok=True)
 llm=LocalLLM(); rows=list(csv.DictReader((DATA/'sample_manifest.csv').open(encoding='utf-8'))); records=[]; evidence=[]
 for n,r in enumerate(rows,1):
  p=DATA/'source_md'/r['sample_filename']; rec={'sample_id':r['sample_id'],'paper_id':r['paper_id'],'source_filename':r['sample_filename'],'source_path':r['original_path'],'extraction_method':llm.name,'review_status':'candidate_unverified'}
  try:
   text=p.read_text(encoding='utf-8',errors='replace'); ctx='\n'.join(text.splitlines()[:45])+'\n'+text[:3500]
   try: obj=llm.extract(ctx,r['paper_id']); data=obj if isinstance(obj,dict) else fallback(text)
   except Exception as e: logging.exception('LLM failed %s: %s',r['sample_id'],e); data=fallback(text); rec['extraction_method']='regex_fallback'
   fields=['material_name','composition_formula','dopants','synthesis_method','synthesis_conditions','ionic_conductivity_value','ionic_conductivity_unit','conductivity_temperature_C','air_stability','air_stability_evidence','electrochemical_window_value','electrochemical_window_unit','evidence']
   for k in fields: rec[k]=data.get(k)
   if not isinstance(rec['dopants'],list): rec['dopants']=[] if not rec['dopants'] else [str(rec['dopants'])]
   if rec['air_stability'] not in ('stable','unstable','mixed','unclear'): rec['air_stability']='unclear'
   rec['extraction_status']='ok' if any(rec.get(k) for k in ('composition_formula','ionic_conductivity_value','air_stability_evidence')) else 'partial'
   for field in ('composition_formula','ionic_conductivity_value','air_stability','air_stability_evidence','synthesis_method'):
    v=rec.get(field)
    if v not in (None,'','unclear',[]): evidence.append({'sample_id':r['sample_id'],'paper_id':r['paper_id'],'field':field,'value':v,'quote':rec.get('air_stability_evidence') if field=='air_stability' else rec.get('evidence'),'source_filename':r['sample_filename'],'review_status':'candidate_unverified'})
  except Exception as e: logging.exception('Skipped %s: %s',r['sample_id'],e); rec.update({'extraction_status':'skipped','extraction_error':str(e)})
  records.append(rec)
  if n%10==0: logging.info('Extracted %d/100 papers',n); print(f'Extracted {n}/100',flush=True)
 (DATA/'extracted_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 fields=list(dict.fromkeys(k for r in records for k in r))
 with (DATA/'extracted_records.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict)) else r.get(k) for k in fields} for r in records])
 with (DATA/'extraction_evidence.jsonl').open('w',encoding='utf-8') as f:
  for e in evidence:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 logging.info('Extraction completed records=%d llm=%s',len(records),llm.name); print(f'Extraction complete: {len(records)} records; {llm.name}')
if __name__=='__main__': main()
