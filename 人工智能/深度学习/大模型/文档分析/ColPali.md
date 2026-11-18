# ColPali 详解

> ColPali 是一种基于视觉语言模型（VLM）的文档检索模型，由法国国家信息与自动化研究所（Inria）等机构提出。它利用文档页面的图像嵌入和后期交互（Late Interaction）机制，实现无需 OCR 的复杂版面 PDF 检索。

> **⚠️ 弃用提示（选型前必读）**
>
> colpali-engine 已官方弃用。GitHub 仓库 illuin-tech/colpali 的 README 原话是：
>
> "colpali-engine is now deprecated. The repository and package remain available for research, reproducibility, and existing projects, but we recommend Sentence Transformers for new projects and production use."
>
> sentence-transformers v6 通过 MultiVectorEncoder 提供同类多向量编码能力，官方因此建议新项目直接用后者。
> 注意：本机装有 sentence-transformers 6.3.0，但导入时抛
> ImportError: cannot import name 'is_kernels_available' from 'transformers.utils'
> （与该环境的 transformers 版本不兼容），所以 MultiVectorEncoder 这个类名**未在本机验证**，此处依据的是官方说明。
>
> **选型建议**：研究与复现（对照论文结果、跑 ViDoRe 基准）用 colpali-engine；新项目与生产上 sentence-transformers。

------

## 1. 背景与动机

传统 PDF 检索流程通常依赖 OCR 提取文本，然后基于文本嵌入进行向量检索。但 OCR 存在以下问题：

- 版面复杂时文本顺序混乱
- 表格、图表、公式等信息丢失
- 版式视觉特征被忽略
- OCR 错误会传播到检索结果

ColPali 提出直接对文档页面图像进行嵌入，保留完整视觉信息，并通过视觉语言模型（PaliGemma）生成高维向量，实现端到端的视觉文档检索。

------

## 2. 核心技术

### 2.1 视觉语言模型后端

ColPali 使用 PaliGemma-3B 作为特征提取器。PaliGemma 是 Google 开源的视觉语言模型，能处理图像和文本输入，输出多模态表示。ColPali 将其适配为仅图像编码的检索模型。

### 2.2 后期交互（Late Interaction）

ColPali 引入 ColBERT 风格的后期交互机制：查询和文档页面分别编码为多个 token 级向量，检索时使用最大相似度求和（MaxSim）计算相关性分数，而非将整个页面压缩为单一向量。这保留了细粒度匹配能力。

### 2.3 多向量表示

文档页面图像经过 PaliGemma 编码后，输出一个 token 向量序列（而非单个 CLS 向量）。查询文本也编码为 token 向量序列。两者通过后期交互计算相似度。这种多向量表示显著提升了检索精度。

------

## 3. 工作流程

1. **页面图像生成**：将 PDF 每页渲染为高分辨率图像。
2. **图像编码**：使用 ColPali 模型（PaliGemma-3B）对页面图像编码，输出每个图像 patch 的向量，构成多向量表示。
3. **查询编码**：使用同一模型的文本编码器对查询文本编码，输出查询 token 向量。
4. **相似度计算**：对查询向量与文档页面向量执行后期交互，计算 MaxSim 分数。
5. **排序与返回**：按分数排序返回相关页面。

------

## 4. 模型与训练

ColPali 基于 PaliGemma-3B 进行微调，训练数据为文档页面图像与对应文本查询对。训练目标为对比学习，拉近相关页面与查询的向量空间距离。

- 模型参数：约 30 亿
- 视觉编码器：SigLIP
- 文本解码器：Gemma-2B
- 输出向量维度：128（每个 token）
- 支持语言：多语言

以上为 PaliGemma / ColPali 的公开模型规格与论文描述，**本机未下载权重复测**，仅用于理解结构。

------

## 5. 使用方式

### 5.1 安装

```bash
pip install colpali_engine
```

### 5.2 当前包内的模型类（实测，colpali-engine 0.3.8）

从顶层一次性导入即可，**不要用内部深层路径**（早期笔记里的
`colpali_engine.models.paligemma.colpali.processing_colpali` 是内部实现路径，重构后会失效）：

```python
from colpali_engine.models import ColPali, ColPaliProcessor
```

本机实测 `colpali_engine.models` 导出这些类：ColPali / ColPaliProcessor、BiPali /
BiPaliProcessor / BiPaliProj、ColQwen2 / ColQwen2Processor、BiQwen2 / BiQwen2Processor、
ColIdefics2 / ColIdefics2Processor、ColIdefics3 / ColIdefics3Processor。

后续版本又追加了 ColQwen2_5、ColQwen3、BiGemma3、ColGemma3、ColModernVBert 等名字——本机 0.3.8 **不含**
这些，升级后才可用（升级后先跑一次 `dir(colpali_engine.models)` 核实再写进代码）。
社区主流已转向 ColQwen2.5 一类约 2B 的后继模型，显存与推理成本比原始 ColPali（PaliGemma-3B）低一档。

### 5.3 加载模型

```python
import torch
from colpali_engine.models import ColPali, ColPaliProcessor
from colpali_engine.utils.torch_utils import get_torch_device

device = get_torch_device("auto")
model = ColPali.from_pretrained(
    "vidore/colpali-v1.2",
    torch_dtype=torch.bfloat16,
    device_map=device,
).eval()
processor = ColPaliProcessor.from_pretrained("vidore/colpali-v1.2")
```

### 5.4 检索示例（MaxSim 打分）

旧写法 `model(**processor(text=queries, return_tensors="pt"))` 混用了原始 HuggingFace 调用约定，
新版应走 processor 的 `process_images` / `process_queries` 两个专用方法：

```python
from PIL import Image

images = [Image.open("page_01.png").convert("RGB")]
queries = ["合同约定的付款账期是多少？"]

with torch.no_grad():
    image_inputs = processor.process_images(images).to(model.device)
    image_embeddings = model(**image_inputs)          # (n_pages, n_patches, dim)

    query_inputs = processor.process_queries(queries).to(model.device)
    query_embeddings = model(**query_inputs)          # (n_queries, n_tokens, dim)

# 后期交互 / MaxSim 打分，返回 (n_queries, n_pages)
scores = processor.score_multi_vector(query_embeddings, image_embeddings)
```

`score_multi_vector` 内部就是 MaxSim，源码实测核心一行：
`torch.einsum("bnd,csd->bcns", qs_batch, ps_batch).max(dim=3)[0].sum(dim=2)`
——即对每个 query token 取所有文档 token 的最大相似度，再求和。

关于 `get_scores` / `get_top_k_multi_vector`：这两个封装在较新版本的
`colpali_engine.utils.torch_utils` 里提供，**本机 0.3.8 的 torch_utils 只有
get_torch_device、tear_down_torch、ListDataset 等，没有这两个函数**（实测）。如果你装的版本有，
可以写成 `from colpali_engine.utils.torch_utils import get_scores`；没有就用上面的
`processor.score_multi_vector`，效果一致。

说明：本机未下载模型权重（离线环境），上面两段代码只做了 API 级核对，**未端到端跑通**。

### 5.5 集成到 RAG 流水线

ColPali 可与向量数据库（如 Qdrant、Vespa）集成，将多向量存储为嵌套向量，并在查询时执行 MaxSim。

------

## 6. 应用场景

- **复杂版面 PDF 检索**：对含有表格、图表、多栏排版的 PDF 进行精确页面定位。
- **RAG 中的文档检索**：替代 OCR+文本嵌入，提高召回率和准确性。
- **视觉问答**：结合页面图像，为多模态大模型提供相关页面。
- **页面级召回后再抽取**：先用它筛出相关页，再把页面图像交给 VLM 或版面模型做字段抽取（它本身不抽取）。

------

## 7. 适用与不适用

ColPali 类模型只解决**页面级召回**一个问题：给定查询，告诉你"哪一页相关"，输出的是页面排序，不是字段。

**适用**：

- 语料是 PDF 扫描件/复杂版式，OCR 文本质量差，想绕开 OCR。
- 只需要"定位到页"，后续再人工或模型处理。
- 需要版式/图表信息参与匹配（纯文本检索会丢的信息）。

**不适用（常见的误用）**：

- **字段级抽取**：比如"抽取合同里的付款条款、违约金比例、终止条件"。ColPali 不产出结构化字段，
  它只给页面打分，答不出"付款账期是多少天"。字段抽取要靠版面模型（Docling 等）+ LLM 抽取，
  或直接把页面图像交给 VLM。
- **需要精确引用的合规场景**：它给的是页级相关性分数，不是可核验的字符级出处。
- **无 GPU 或索引规模极大**：多向量存储与 MaxSim 打分的成本远高于单向量，纯文本场景没必要上。

一句话：把 ColPali 当"视觉版 BM25 召回器"，不要当解析器。

------

## 8. 性能与局限

### 优势

- 无需 OCR，避免 OCR 错误传播
- 保留视觉和版式信息，适用于复杂文档
- 多向量后期交互显著提升精度
- 在 ViDoRe 等基准上领先（基准数字见原论文，本文不复述未复测的指标）

### 局限

- 计算开销大：每页需要生成较多 token 向量，存储和计算成本高
- 需要 GPU 推理
- 模型较大（3B），对硬件有要求
- 索引构建速度较慢，适合离线构建
- 包本身已弃用，长期维护要靠 sentence-transformers 路线

------

## 9. 总结

ColPali 通过视觉语言模型与后期交互机制，实现了基于图像的高性能 PDF 检索，为复杂版式文档的检索增强生成提供了新的技术路线。
但它的定位是"页面召回"而非"文档解析"，且官方已把新项目导向 sentence-transformers，新工程应优先评估
sentence-transformers 的多向量能力，只在复现与兼容存量时才继续用 colpali-engine。
