"""Build a dependency-light SSE knowledge graph from extracted candidates."""
from pathlib import Path
import csv, json, re, urllib.parse, html, logging, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; KG=ROOT/'kg'
logging.basicConfig(filename=ROOT/'logs/log.txt',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
ELEMENTS=set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi'.split())
def uri(s): return 'urn:sse:'+urllib.parse.quote(str(s).strip().replace(' ','_'),safe='._-')
def add_node(nodes, typ, name, **attrs):
    if not name: return None
    key=f'{typ}:{str(name).strip()}'
    if key not in nodes: nodes[key]={'id':key,'type':typ,'name':str(name).strip(),**attrs}
    else: nodes[key].update({k:v for k,v in attrs.items() if v not in (None,'')})
    return key
def main():
    records=json.loads((DATA/'extracted_records.json').read_text(encoding='utf-8')); nodes={}; edges=[]; seen=set()
    def edge(a, rel, b, paper):
        if not a or not b:return
        key=(a,rel,b,paper)
        if key not in seen: edges.append({'source':a,'relation':rel,'target':b,'paper_id':paper}); seen.add(key)
    for r in records:
        paper=add_node(nodes,'Paper',r.get('paper_id'),sample_id=r.get('sample_id'))
        formula=r.get('composition_formula'); name=r.get('material_name') or formula
        material=add_node(nodes,'Electrolyte',name,formula=formula,review_status='candidate_unverified')
        edge(paper,'reports',material,r.get('paper_id'))
        if formula:
            for el in re.findall(r'[A-Z][a-z]?',str(formula)):
                if el in ELEMENTS: edge(material,'contains_element',add_node(nodes,'Element',el),r.get('paper_id'))
        for dop in r.get('dopants') or []:
            if dop: edge(material,'doped_with',add_node(nodes,'Dopant',dop),r.get('paper_id'))
        if r.get('synthesis_method'):
            edge(material,'synthesized_by',add_node(nodes,'SynthesisMethod',r['synthesis_method']),r.get('paper_id'))
        for field,label in [('ionic_conductivity_value','ionic_conductivity'),('air_stability','air_stability'),('electrochemical_window_value','electrochemical_window')]:
            val=r.get(field)
            if val not in (None,'','unclear'):
                unit=r.get('ionic_conductivity_unit') if field=='ionic_conductivity_value' else (r.get('electrochemical_window_unit') if field=='electrochemical_window_value' else '')
                metric=add_node(nodes,'Performance',f'{label}={val} {unit or ""}'.strip(),metric=label,value=val,unit=unit or None)
                edge(material,'has_performance',metric,r.get('paper_id'))
        stab=r.get('air_stability')
        if stab in ('stable','unstable','mixed'):
            edge(material,'stability_is',add_node(nodes,'Stability',stab),r.get('paper_id'))
    graph={'schema_version':'1.0','source':'100-paper fixed sample','review_status':'candidate_unverified','nodes':list(nodes.values()),'edges':edges}
    (KG/'graph.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
    with (KG/'graph.nt').open('w',encoding='utf-8') as f:
        for e in edges:f.write(f'<{uri(e["source"])}> <{uri(e["relation"])}> <{uri(e["target"])}> .\n')
    # Deterministic SVG preview of a compact subset.
    visible=graph['nodes'][:80]; ids={n['id']:i for i,n in enumerate(visible)}; W=1100; H=850; cx=W/2; cy=H/2; radius=310
    pos={n['id']:(cx+radius*math.cos(2*math.pi*i/max(1,len(visible))),cy+radius*math.sin(2*math.pi*i/max(1,len(visible)))) for i,n in enumerate(visible)}
    colors={'Electrolyte':'#e76f51','Element':'#2a9d8f','Dopant':'#e9c46a','Performance':'#457b9d','SynthesisMethod':'#8d5fd3','Paper':'#adb5bd','Stability':'#f4a261'}
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/><text x="20" y="32" font-size="22" font-family="sans-serif">SSE knowledge graph preview (first {len(visible)} entities)</text>']
    for e in graph['edges']:
        if e['source'] in pos and e['target'] in pos:
            x1,y1=pos[e['source']]; x2,y2=pos[e['target']]; svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#ccd2d8" stroke-width="1"/>')
    for n in visible:
        x,y=pos[n['id']]; color=colors.get(n['type'],'#777'); label=html.escape(n['name'][:28])
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}"/><text x="{x+9:.1f}" y="{y+4:.1f}" font-size="9" font-family="sans-serif">{label}</text>')
    svg.append('</svg>'); (KG/'knowledge_graph.svg').write_text(''.join(svg),encoding='utf-8')
    stats={'entity_count':len(nodes),'relation_count':len(edges),'entity_types':{},'relation_types':{},'review_status':'candidate_unverified'}
    for n in nodes.values():stats['entity_types'][n['type']]=stats['entity_types'].get(n['type'],0)+1
    for e in edges:stats['relation_types'][e['relation']]=stats['relation_types'].get(e['relation'],0)+1
    (KG/'graph_stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    logging.info('KG built entities=%d relations=%d',len(nodes),len(edges)); print(f'KG: {len(nodes)} entities, {len(edges)} relations')
if __name__=='__main__':main()
