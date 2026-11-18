# LlamaIndex 开发手册（中文 · 0.14 主线）

面向「要立刻上手用 LlamaIndex 开发真实应用」的工程师。
六章分文件，按需查阅；总字数约 216KB，全部为可直接复制运行的代码与判断依据。

## 版本基线

- 目标写法：**llama-index-core 0.14.x**（2025 年主线）
- 阅读约定：区分 0.10 拆包前后；所有无法确认的 API 标注「需对照官方文档核实」
- 你说「我要用它开发」，那么最重要的两条纪律是：
  1. **锁小版本上界**（见第 4 章 4.10），LlamaIndex 的小版本会破坏 API；
  2. **凡是标「待核实」的断言，上线前用第 4 章 4.9 的探针命令自测。**

## 目录

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| [01-架构与心智模型.md](./01-架构与心智模型.md) | 三平面架构、Document/Node、Index 是访问策略、查询面四段式、ChatEngine、Agent/Workflow、IngestionPipeline、Storage 三层、Settings、与 LangChain/LangGraph 的三方差异与选型、QueryEngine vs Workflow 的选择 | 第一天，建立全局地图 |
| [02-存储检索与性能.md](./02-存储检索与性能.md) | 向量库选型（Chroma/Qdrant/Milvus/pgvector）、Embedding 取舍、chunk 策略、metadata filter、hybrid、rerank、增量 ingestion 与去重、持久化三种组合、延迟与成本调优、0.11→0.12 迁移 | 检索效果不行、成本超标、要上线时 |
| [03-实战代码与工程实践.md](./03-实战代码与工程实践.md) | 安装清单、Loader→IngestionPipeline→VectorStoreIndex→QueryEngine 全链路、QueryEngine/ChatEngine/Agent 三个最小可运行示例、报错区分、版本 pin | 动手写代码时，直接抄 |
| [04-版本差异与事实核查.md](./04-版本差异与事实核查.md) | 0.7→0.14 四次分水岭、命名迁移表、导入路径三段式、ServiceContext→Settings 完整迁移、Agent 世代、断言可信度表、12 个过时写法、自测方法、锁版本策略 | 抄到旧代码报 ImportError 时、升级前 |
| [05-切分粒度与父子检索.md](./05-切分粒度与父子检索.md) | 五种切分器实测默认参数、中文切分两个坑、chunk_overlap 真实机制（为何设了不生效）、分层节点结构、AutoMerging 判定公式、父块分数来源、混排实测、子块/父块决策矩阵与数据判据、完整可运行代码、常见误用 | 检索结果太碎或太长、想上分层、纠结子块还是父块时 |
| [06-文档解析与PDF处理.md](./06-文档解析与PDF处理.md) | PDF 三层信息模型（字符层/坐标层/语义层）、工具站位表、pypdf plain/layout 实测与双栏拼行坑、表格切分与 ragged 锚点算法、docling 依赖坑与 TableFormer 实测、标题树价值、公式为何谁都给不了、OCR 参数、论文双栏专题、docx/xlsx/doc 三个实测坑、分级解析策略、误用清单 | 要处理 PDF/Word/Excel 入库、表格提取不准、扫描件读不出字时 |

## 三条阅读路径

**A. 30 分钟跑通（不花一分钱，全程离线）**
1. 读 01 的第 1、2、3 节（三平面 / Document-Node / Index 是访问策略）。
2. 读 03 的 3.1.2-A：「最小内核」安装命令。
3. 抄 03 的 3.2 完整链路，但把 LLM/Embedding 换成 core 自带的 `MockLLM` / `MockEmbedding`，可完全离线跑通。
4. 拿到第一份 query 结果后，再换成真实模型。

```bash
pip install "llama-index-core>=0.12,<0.15"
python -c "from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings; from llama_index.core.llms import MockLLM; Settings.llm = MockLLM(); print('env ok')"
```

**B. 生产落地**
1. 02 全章：先把向量库、embedding、chunk、rerank 四件事定下来。
2. 06 全章：确定文档解析方案——PDF 走 pypdf 还是 docling，Excel 要不要进向量库。
3. 05 全章：确定切分粒度和子块/父块策略——分层不是默认必选。
4. 03 的 3.2 全链路 + 3.5 Agent。
5. 04 的 4.10 锁版本。
6. 回 02 的 2.10 做埋点与成本核算。

**C. 排错**
- 报错先归类：`ImportError` → 04 的 4.2/4.8；`ModuleNotFoundError` → 03 的 3.1；检索质量差 → 02 的 2.4/2.6/2.7；重启丢索引 → 02 的 2.9。

## 跨章速查：症状 → 章节

| 症状 | 先看 |
|---|---|
| `ImportError: cannot import name ...` | 04 · 4.2 / 4.8 |
| `ModuleNotFoundError: No module named llama_index.xxx` | 03 · 3.1 |
| 搜出来全是无关内容，但不报错 | 02 · 2.3 / 2.4（多半是 embedding 不一致或切块太烂） |
| 重启服务后索引查不到 | 02 · 2.9（持久化只存了一半） |
| 答案缺关键原文 | 02 · 2.6 / 2.7（hybrid + rerank） |
| 检索结果太碎、上下文不够 | 05 · 5.7（该用父块或直接加大 chunk_size） |
| 检索结果整段太长、回答发散 | 05 · 5.7 / 5.9（分层过度合并） |
| 父块从来不出现在结果里 | 05 · 5.4（ratio 未达阈值，或 docstore 没装父块） |
| 每问一次都重建索引 | 01 · 7 / 02 · 2.8（该用 from_vector_store 挂载 + 增量 ingestion） |
| 越权数据被检索到 | 02 · 2.5（metadata filter 必须在检索层做） |
| 扫描件 PDF 解析出来是空的 | 06 · 6.4.7（没有文本层，必须开 OCR） |
| 表格被压成一堆散字 | 06 · 6.3.4 / 6.4.3（该上 docling 的 table_structure） |
| 跨页表格列名变成 0 1 2 | 06 · 6.4.3（TableFormer 不带表头，业务侧要重复表头） |
| docx 读出来没有标题层级 | 06 · 6.6.3（DocxReader 只抽纯文本，改用 python-docx） |
| Excel 求和/比较答案不对 | 06 · 6.6.4（数值问题必须代码执行，不能靠向量检索） |
| 双栏论文左右栏内容交错 | 06 · 6.3.3（layout 把两栏焊成一行，要按 x 坐标分栏） |
| 延迟高、成本高 | 02 · 2.10 |
| Agent 的 run() 报 asyncio 错误 | 04 · 4.5 |

## 建议的工程落地顺序

1. **先跑通**：离线 Mock 链路（路径 A）。
2. **再定层**：按 01 的三平面确定自己的代码分层，别把 ingestion、retrieval、generation 混在一个函数里。
3. **定选型**：按 02 的四个决策点（向量库 / embedding / chunk / rerank）写进技术方案。
4. **定解析**：按 06 的决策矩阵选文档解析方案；PDF 先判有没有文本层、要不要结构，再决定 pypdf 还是 docling。
5. **定粒度**：按 05 的决策矩阵决定要不要分层；用 20–30 条真实查询统计父块占比再定。
6. **锁依赖**：按 04 的 4.10 写死版本上界，并加一条 CI 探针。
7. **建评测**：先用 20 条真实问题做基准（03 的测试脚手架），再调参。

## 维护与核实

- 官方文档：`developers.llamaindex.ai/python/framework/`（中文镜像 `developers.llamaindex.org.cn`）
- CHANGELOG：GitHub `run-llama/llama_index` 根目录
- 本地核实：第 4 章 4.9 的四条命令
- 本文档由专家组并行产出：架构（Software Architect）、存储检索（Database Optimizer）、代码实践（Code Reviewer）、版本核查（本章）、总览合并（协调者）；05 章基于 0.14.26 本机实测脚本补充；06 章基于 pypdf 6.x / docling 2.150.1 的本机实测（含一份 6 页双栏论文的逐项对照）补充。
