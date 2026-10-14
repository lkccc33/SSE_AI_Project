"""Exploratory composition-only baseline for weakly labelled air stability."""
from pathlib import Path
import json, logging, re, sys
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; MODEL=ROOT/'model'; RES=ROOT/'results'
logging.basicConfig(filename=ROOT/'logs/log.txt',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
ELEMENTS='H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi'.split()
def features(formula):
    f={f'el_{e}':0 for e in ELEMENTS}
    if formula:
        toks=re.findall(r'([A-Z][a-z]?)(\d*(?:\.\d+)?)',str(formula))
        counts={}
        for el,n in toks:
            if el in f: counts[el]=counts.get(el,0)+(float(n) if n else 1.0)
        total=sum(counts.values()) or 1
        for el,n in counts.items(): f[f'el_{el}']=n/total
    f['formula_present']=int(bool(formula))
    return f
def main():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.dummy import DummyClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,confusion_matrix,roc_auc_score
    from sklearn.feature_extraction import DictVectorizer
    import joblib
    records=json.loads((DATA/'extracted_records.json').read_text(encoding='utf-8'))
    labeled=[r for r in records if r.get('air_stability') in ('stable','unstable')]
    rawX=[features(r.get('composition_formula')) for r in labeled]; y=[1 if r['air_stability']=='stable' else 0 for r in labeled]
    vectorizer=DictVectorizer(sparse=False)
    X=vectorizer.fit_transform(rawX if rawX else [features(None),features('Li6PS5Cl')])
    if not rawX: X=X[:0,:]
    counts={'unstable':sum(v==0 for v in y),'stable':sum(v==1 for v in y)}
    metrics={'target':'air_stability (LLM/rule weak label; stable=1, unstable=0)','feature_scope':'elemental composition only','n_labeled':len(y),'class_counts':counts,'review_status':'exploratory_weak_labels'}
    if len(y)>=10 and min(counts.values())>=2:
        Xtr,Xte,ytr,yte,idxtr,idxte=train_test_split(X,y,list(range(len(y))),test_size=0.25,random_state=42,stratify=y)
        clf=RandomForestClassifier(n_estimators=300,min_samples_leaf=2,class_weight='balanced',random_state=42)
        clf.fit(Xtr,ytr); pred=clf.predict(Xte)
        metrics.update({'evaluation':'stratified holdout','n_train':len(ytr),'n_test':len(yte),'accuracy':float(accuracy_score(yte,pred)),'balanced_accuracy':float(balanced_accuracy_score(yte,pred)),'macro_f1':float(f1_score(yte,pred,average='macro',zero_division=0)),'confusion_matrix':confusion_matrix(yte,pred,labels=[0,1]).tolist(),'test_sample_ids':[labeled[i]['sample_id'] for i in idxte]})
        if len(set(yte))==2: metrics['roc_auc']=float(roc_auc_score(yte,clf.predict_proba(Xte)[:,1]))
        model=clf
    elif y:
        model=DummyClassifier(strategy='most_frequent'); model.fit(X,y)
        metrics.update({'evaluation':'not statistically evaluable: insufficient labeled examples or one class','n_train':len(y),'n_test':0,'accuracy':None,'balanced_accuracy':None,'macro_f1':None,'confusion_matrix':None})
    else:
        # A runnable neutral baseline; no claims of predictive performance.
        model=DummyClassifier(strategy='prior'); model.fit(vectorizer.transform([features(None),features('Li6PS5Cl')]),[0,1])
        metrics.update({'evaluation':'not evaluable: no stable/unstable labels extracted','n_train':0,'n_test':0,'accuracy':None,'balanced_accuracy':None,'macro_f1':None,'confusion_matrix':None})
    joblib.dump({'model':model,'vectorizer':vectorizer},MODEL/'air_stability_model.joblib')
    (RES/'model_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    # Dependency-free SVG summary.
    vals=[metrics.get('accuracy'),metrics.get('balanced_accuracy'),metrics.get('macro_f1')]
    labels=['Accuracy','Balanced acc.','Macro F1']; W=700; H=380
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><rect width="100%" height="100%" fill="white"/><text x="24" y="34" font-size="20" font-family="sans-serif">Air stability baseline metrics</text>']
    for i,(lab,val) in enumerate(zip(labels,vals)):
        y0=85+i*85; width=max(0,min(1,val or 0))*450
        svg.append(f'<text x="25" y="{y0+20}" font-size="14" font-family="sans-serif">{lab}</text><rect x="170" y="{y0}" width="450" height="30" fill="#edf0f2"/><rect x="170" y="{y0}" width="{width:.1f}" height="30" fill="#2a9d8f"/><text x="630" y="{y0+21}" font-size="13" font-family="sans-serif">{"NA" if val is None else f"{val:.3f}"}</text>')
    svg.append(f'<text x="25" y="350" font-size="12" font-family="sans-serif">n labeled={len(y)}; labels are unverified text-derived candidates</text></svg>')
    (RES/'model_metrics.svg').write_text(''.join(svg),encoding='utf-8')
    logging.info('Model done metrics=%s',metrics); print(f'Model n={len(y)}; evaluation={metrics["evaluation"]}')
if __name__=='__main__':main()
