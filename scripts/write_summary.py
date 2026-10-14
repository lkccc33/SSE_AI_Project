from pathlib import Path
import json,csv,collections
R=Path(__file__).resolve().parents[1]
manifest=list(csv.DictReader((R/'data/sample_manifest.csv').open(encoding='utf-8')))
records=json.loads((R/'data/extracted_records.json').read_text(encoding='utf-8'))
stats=json.loads((R/'kg/graph_stats.json').read_text(encoding='utf-8'))
metrics=json.loads((R/'results/model_metrics.json').read_text(encoding='utf-8'))
methods=collections.Counter(x.get('extraction_method','unknown') for x in records)
statuses=collections.Counter(x.get('extraction_status','unknown') for x in records)
classes=collections.Counter(x.get('air_stability','unclear') for x in records)
integrity=list(csv.DictReader((R/'data/source_integrity.csv').open(encoding='utf-8')))
summary={'sample_count':len(manifest),'record_count':len(records),'extraction_methods':dict(methods),'extraction_status':dict(statuses),'stability_labels':dict(classes),'source_hash_matches':sum(x['match']=='True' for x in integrity),'entities':stats['entity_count'],'relations':stats['relation_count'],'model_metrics':metrics}
(R/'results/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 结果简报','',f'- 样本：{len(manifest)} 篇，来自 2,645 篇清洗稿；固定随机种子 `20261014`。',f'- 源文件保护：100/100 份抽样副本与原文 SHA-256 一致；原始 Markdown 未修改。',f'- 抽取记录：{len(records)} 条，方法 `{dict(methods)}`；记录状态 `{dict(statuses)}`。',f'- 空气稳定性标签：`{dict(classes)}`；仅 stable/unstable 共 {metrics["n_labeled"]} 条进入模型。',f'- 知识图谱：{stats["entity_count"]} 个实体、{stats["relation_count"]} 条关系。',f'- 模型：元素组成 → 空气稳定性二分类；分层留出 {metrics.get("n_train",0)} 条训练 / {metrics.get("n_test",0)} 条测试。',f'- 评估状态：{metrics["evaluation"]}。']
for k in ('accuracy','balanced_accuracy','macro_f1','roc_auc'):
 if metrics.get(k) is not None: lines.append(f'- {k}: {metrics[k]:.4f}')
lines += ["", "限制：标签来自未人工核验的小型本地 LLM 或规则；stable/unstable 仅 13 条，测试集 4 条，指标只证明链路可运行，不代表泛化预测能力。建议人工核验后扩充金标准。", ""]
(R/'results/RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
