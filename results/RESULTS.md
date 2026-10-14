# 结果简报

- 样本：100 篇，来自 2,645 篇清洗稿；固定随机种子 `20261014`。
- 源文件保护：100/100 份抽样副本与原文 SHA-256 一致；原始 Markdown 未修改。
- 抽取记录：100 条，方法 `{'local:Qwen3.5-4B': 99, 'regex_fallback': 1}`；记录状态 `{'ok': 74, 'partial': 26}`。
- 空气稳定性标签：`{'unclear': 86, 'stable': 8, 'unstable': 5, 'mixed': 1}`；仅 stable/unstable 共 13 条进入模型。
- 知识图谱：292 个实体、451 条关系。
- 模型：元素组成 → 空气稳定性二分类；分层留出 9 条训练 / 4 条测试。
- 评估状态：stratified holdout。
- accuracy: 0.2500
- balanced_accuracy: 0.2500
- macro_f1: 0.2000
- roc_auc: 0.2500

限制：标签来自未人工核验的小型本地 LLM 或规则；stable/unstable 仅 13 条，测试集 4 条，指标只证明链路可运行，不代表泛化预测能力。建议人工核验后扩充金标准。
