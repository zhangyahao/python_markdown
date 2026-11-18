# Docling 详解

> Docling 是由 IBM Research 开源的文档解析与转换工具，专为构建 RAG（检索增强生成）和 AI 应用而设计。它能将多种格式的文档（PDF、DOCX、PPTX、HTML
> 等）解析为结构化、可检索的内容表示，并输出为 JSON、Markdown 等格式。
>
> 本文的接口与默认值均以本机安装的 docling 2.150.1 / docling-core 2.107.1 实测为准（环境 E:\miniconda3\envs\llamaindex）。

------

## 1. 概述

Docling 是一个文档理解库，支持将异构文档转换为统一的、模型友好的表示。其核心能力包括：版面分析、表格结构识别、阅读顺序恢复、标题层级提取、以及多模态信息整合。Docling
提供了 Python API，可独立使用或集成到更大的数据处理流水线中。

主要特性：

- 支持多种文档格式：PDF、DOCX、PPTX、XLSX、HTML、Images、AsciiDoc、Markdown 等
- 高级 PDF 解析：结合版面目标检测与表格结构识别
- 输出结构化 JSON 或 Markdown
- 支持 OCR：默认使用 OcrAutoOptions，按平台自动挑选已安装的 OCR 引擎（EasyOCR / RapidOCR 等）
- 阅读顺序重建
- 可扩展的解析选项

------

## 2. 核心能力

### 2.1 版面分析

Docling 的版面分析**不是** LayoutLM 这类文档理解预训练模型，而是一个自研的 RT-DETR 系目标检测模型：输入 PDF 页面的渲染图，
输出带类别标签与几何框的版面区域（正文、标题、表格、图片、页眉页脚、公式等）。"RT-DETR 系"指的是检测头/结构沿用 RT-DETR
这一实时检测路线，而不是直接加载某个公开的 RT-DETR 权重。

模型清单与预设名可在源码里直接查到（E:\miniconda3\envs\llamaindex\Lib\site-packages\docling\datamodel\layout_model_specs.py:11-13）：

| 常量                        | preset 名               | 说明            |
|:--------------------------|:-----------------------|:--------------|
| DOCLING_LAYOUT_HERON      | layout_heron_default   | 默认版面模型        |
| DOCLING_LAYOUT_HERON_101  | layout_heron_101       | Heron 的 101 变体 |
| DOCLING_LAYOUT_EGRET_MEDIUM | layout_egret_medium  | Egret 系列（中等规格） |
| DOCLING_LAYOUT_EGRET_LARGE | layout_egret_large    | Egret 系列（大规格）   |
| DOCLING_LAYOUT_EGRET_XLARGE | layout_egret_xlarge  | Egret 系列（超大规格）  |

选择预设的入口是 LayoutObjectDetectionOptions.from_preset("layout_heron_default")（见 docling/datamodel/pipeline_options.py:1721）。

**不要与 LayoutLM 混淆**：LayoutLM 是文档理解预训练模型，输入文本+版面坐标，输出 token 级表示，用于分类/抽取等下游任务，
它本身不产出"这是表格区域、坐标是 x1y1x2y2"这种检测结果。Docling 用的是检测模型，两者不是一回事。

### 2.2 表格识别

对于检测到的表格区域，Docling 调用表格结构识别模型（TableFormer）还原行列结构，保留单元格合并信息，结果存为
TableItem。表格导出有 HTML、Markdown、DataFrame 三种出口，CSV 需要自己从 DataFrame 落盘——TableItem 没有
export_to_csv 方法（实测 hasattr(table, "export_to_csv") 为 False）：

```python
table.export_to_html(doc=document)             # HTML 字符串
table.export_to_markdown(doc=document)         # Markdown 表格
df = table.export_to_dataframe(doc=document)   # pandas DataFrame
df.to_csv("table.csv", index=False)            # CSV 自己落盘
```

这三个方法**必须传 doc**。不传 doc 的旧写法已废弃，实测会打印
"Usage of TableItem.export_to_html() without `doc` argument is deprecated." 并且 HTML 返回空串。

### 2.3 阅读顺序恢复

Docling 根据版面元素的空间位置和语义特征，推断正确的阅读顺序，生成线性文本流。该过程对于多栏、复杂布局的 PDF 尤为重要。

### 2.4 标题层级提取

Docling 能识别文档中的标题样式（字体、字号、编号等），提取标题层级，构建文档大纲，输出的结构化内容中包含标题与正文之间的层次关系。

### 2.5 多格式支持

除 PDF 外，Docling 能直接解析 Office 文档（基于 python-docx、python-pptx 等），并统一转换为相同的内部表示。

### 2.6 现代能力（2025 后）

Docling 2.x 有两条明显超出"版面检测 + 表格识别 + 阅读顺序"老流水线的新路线，落地时值得先评估：

**（1）VLM 管道**：把整页图像交给视觉语言模型，直接生成 Markdown/结构化文本，跳过多个专用模型串联。
实装类是 docling.pipeline.vlm_pipeline.VlmPipeline（本机实测可导入），配套选项 VlmPipelineOptions，
其中 vlm_options 可以是 InlineVlmOptions（本地推理，字段含 repo_id、revision、prompt、scale、max_size、
temperature、max_new_tokens 等，本机已核实字段名）或 ApiVlmOptions（调用远程 API）。CLI 里的内置视觉模型预设名为
DEFAULT_VLM_PRESET = "granite_docling"（docling/cli/main.py:295），对应 Granite-Docling 系小模型。
注意：本机未下载这些权重，**转换效果未实测**，只在源码层面核对了类名与字段。

**（2）面向 RAG 的分块**：docling-core 自带 HybridChunker，可在标题层级分块的基础上按 tokenizer 的
max_tokens 继续切分，直接产出带标题路径与元数据的 DocChunk，省去自己按标题切分的工作。
本机实测可导入 `from docling_core.transforms.chunker import HybridChunker`，其配置字段为
delim、tokenizer、repeat_table_header、merge_peers、omit_header_on_overflow、serializer_provider、
always_emit_headings；tokenizer 用 HuggingFaceTokenizer(tokenizer=..., max_tokens=...)（字段实测为
tokenizer、max_tokens）：

```python
from docling_core.transforms.chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2"),
    max_tokens=512,
)
chunker = HybridChunker(tokenizer=tokenizer)
chunks = list(chunker.chunk(result.document))   # 每项是 DocChunk，带 headings 与元数据
```

------

## 3. 架构与工作流程

Docling 的解析流程分为多个阶段：

1. **格式检测与后端选择**：根据文件类型选择解析后端。
2. **初步解析**：提取文本和图像，获取页面元数据。
3. **版面分析**：在 PDF 页面渲染图像上运行 RT-DETR 系版面检测模型。
4. **表格结构识别**：对表格区域运行 TableFormer 做结构识别。
5. **元素聚类与阅读顺序**：将所有版面元素聚类并排序。
6. **后处理与输出**：生成结构化 JSON 或 Markdown。

Docling 使用 `docling-core` 定义统一的数据模型，所有解析结果都转换为该模型，确保跨格式一致性。

------

## 4. 安装与使用

### 安装

```bash
pip install docling
```

### 基本用法

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 输出 Markdown
markdown_text = result.document.export_to_markdown()

# 输出 JSON（dict，可直接 json.dump）
json_output = result.document.export_to_dict()
```

### 高级用法：OCR 与表格识别的取舍

docling 2.150.1 的 PdfPipelineOptions 默认值实测如下（不要照抄"把 do_ocr 打开"的旧教程，它本来就是开的）：

| 选项                                       | 实测默认值                     |
|:-----------------------------------------|:--------------------------|
| do_ocr                                   | True                      |
| do_table_structure                       | True                      |
| force_backend_text                       | False                     |
| images_scale                             | 1.0                       |
| ocr_options                              | OcrAutoOptions            |
| table_structure_options.do_cell_matching | True                      |
| table_structure_options.mode             | TableFormerMode.ACCURATE  |

因此正确的判断是：**只有扫描件需要 OCR**。电子版 PDF 有文本层，可以让 OCR 空转，也可显式关掉以提速：

```python
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = False          # 电子版 PDF 关 OCR；扫描件保持默认 True
pipeline_options.do_table_structure = True   # 默认即 True，写出来只是显式声明

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
result = converter.convert("report.pdf")
```

补充：`images_scale` 影响页面渲染分辨率，版面检测与 OCR 都吃这个值，调高会同时增加内存与耗时；调低则小字号
文本的检测与识别更容易失效。这一项本机只核对了默认值 1.0，未做质量对比实验。

------

## 5. 输出示例

`export_to_dict()` 返回的 dict 顶层键顺序固定为：schema_name、version、name、furniture、body、groups、
texts、pictures、tables、key_value_items、form_items、pages。version 实测为 "1.11.0"（不是旧教程里的 "1.0"）。

关键结构特征是**引用而非内联**：body.children 里存放的是指向 texts / tables 等集合元素的指针（形如
{"$ref": "#/texts/0"}），真正的文本内容在顶层 texts 数组里，元素通过 self_ref 与 parent 互指。
下面是本机用 docling-core 手工构造一个含"标题 + 段落 + 2x2 表格"的文档后，实际 export_to_dict() 的输出
（只截取关键字段，未经任何手工改写）：

```json
{
  "schema_name": "DoclingDocument",
  "version": "1.11.0",
  "name": "demo",
  "furniture": {
    "self_ref": "#/furniture",
    "children": [],
    "content_layer": "furniture",
    "name": "_root_",
    "label": "unspecified"
  },
  "body": {
    "self_ref": "#/body",
    "children": [
      {"$ref": "#/texts/0"},
      {"$ref": "#/texts/1"},
      {"$ref": "#/tables/0"}
    ],
    "content_layer": "body",
    "name": "_root_",
    "label": "unspecified"
  },
  "groups": [],
  "texts": [
    {
      "self_ref": "#/texts/0",
      "parent": {"$ref": "#/body"},
      "children": [],
      "content_layer": "body",
      "label": "section_header",
      "prov": [],
      "orig": "第一章 引言",
      "text": "第一章 引言",
      "level": 1
    },
    {
      "self_ref": "#/texts/1",
      "parent": {"$ref": "#/body"},
      "children": [],
      "content_layer": "body",
      "label": "text",
      "prov": [],
      "orig": "这是正文内容。",
      "text": "这是正文内容。"
    }
  ],
  "pictures": [],
  "tables": [
    {
      "self_ref": "#/tables/0",
      "parent": {"$ref": "#/body"},
      "children": [],
      "content_layer": "body",
      "label": "table",
      "prov": [],
      "captions": [],
      "references": [],
      "footnotes": [],
      "data": {
        "num_rows": 2,
        "num_cols": 2,
        "table_cells": [
          {"row_span": 1, "col_span": 1, "start_row_offset_idx": 0, "end_row_offset_idx": 1,
           "start_col_offset_idx": 0, "end_col_offset_idx": 1, "text": "名称",
           "column_header": false, "row_header": false, "row_section": false, "fillable": false},
          {"row_span": 1, "col_span": 1, "start_row_offset_idx": 0, "end_row_offset_idx": 1,
           "start_col_offset_idx": 1, "end_col_offset_idx": 2, "text": "数量",
           "column_header": false, "row_header": false, "row_section": false, "fillable": false},
          {"row_span": 1, "col_span": 1, "start_row_offset_idx": 1, "end_row_offset_idx": 2,
           "start_col_offset_idx": 0, "end_col_offset_idx": 1, "text": "苹果",
           "column_header": false, "row_header": false, "row_section": false, "fillable": false},
          {"row_span": 1, "col_span": 1, "start_row_offset_idx": 1, "end_row_offset_idx": 2,
           "start_col_offset_idx": 1, "end_col_offset_idx": 2, "text": "3",
           "column_header": false, "row_header": false, "row_section": false, "fillable": false}
        ]
      }
    }
  ],
  "key_value_items": [],
  "form_items": [],
  "pages": {}
}
```

读这份结构时要注意三点：

- **遍历方式**：不要假设 body.children 里直接有 text 字段。正确做法是取 children 的 `$ref`，按
  `#/texts/0` 这类路径去对应顶层集合里取元素。
- **分类靠 label**：标题是 `label: "section_header"`（并带 level），正文是 `label: "text"`，
  表格是 `label: "table"`。不同 label 对应不同的 pydantic 子类，字段并不一样。
- **上例是手工构造的最小文档**，所以 prov 与 pages 为空。真实 PDF 转换后，每个元素会带
  prov（页码 page_no + bbox 坐标）以及 pages 里的页面尺寸记录，这是做引文定位与页面回溯的依据。

------

## 6. 应用场景

- **RAG 数据预处理**：将 PDF 转换为 Markdown 或 JSON，便于分块和向量化。
- **文档转换**：作为企业内容管理流水线的一部分，统一多种格式。
- **信息抽取**：基于结构化输出提取标题、表格等字段。
- **知识库构建**：与向量数据库配合，实现可追溯的智能问答。

一个必须提前知道的工程限制：**Docling 不会自动合并跨页表格**。一张表如果横跨两页，通常会被识别成两个独立的
TableItem（各自带自己的表头和页码），下游拿到的是两张残表。需要自己按"表头一致性 + 页码连续 + 列数一致"
做后处理拼接，或者改用能整页理解的 VLM 管道。这一限制本机未做多页表格实测，依据的是实现上表格按页解析的
行为，落地前建议用你们的真实跨页表格样本验证一次。

------

## 7. 与其他工具对比

| 特性     | Docling            | unstructured  | PaddleStructure |
|:-------|:-------------------|:--------------|:----------------|
| 版面分析   | 是                  | 是             | 是               |
| 表格识别   | 是                  | 是（部分）         | 强（中文）           |
| OCR 集成 | 可选                 | 是             | 是               |
| 多格式支持  | 广（PDF/Office/HTML） | 广             | 主要 PDF/图片       |
| 输出结构化  | JSON/Markdown      | JSON          | JSON            |
| 开源     | 是（MIT）             | 是（Apache-2.0） | 是               |

Docling 的优势在于统一的文档模型和丰富的输出选项，适合作为标准化的文档解析层。
