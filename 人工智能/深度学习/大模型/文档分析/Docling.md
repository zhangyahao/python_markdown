# Docling 详解

> Docling 是由 IBM Research 开源的文档解析与转换工具，专为构建 RAG（检索增强生成）和 AI 应用而设计。它能将多种格式的文档（PDF、DOCX、PPTX、HTML
> 等）解析为结构化、可检索的内容表示，并输出为 JSON、Markdown 等格式。

------

## 1. 概述

Docling 是一个文档理解库，支持将异构文档转换为统一的、模型友好的表示。其核心能力包括：版面分析、表格结构识别、阅读顺序恢复、标题层级提取、以及多模态信息整合。Docling
提供了 Python API，可独立使用或集成到更大的数据处理流水线中。

主要特性：

- 支持多种文档格式：PDF、DOCX、PPTX、XLSX、HTML、Images、AsciiDoc、Markdown 等
- 高级 PDF 解析：结合布局分析与表格识别
- 输出结构化 JSON 或 Markdown
- 支持 OCR（通过集成的 RapidOCR 或 EasyOCR）
- 跨页元素合并与阅读顺序重建
- 可扩展的解析选项

------

## 2. 核心能力

### 2.1 版面分析

Docling 使用基于深度学习的版面分析模型，检测文档中的文本块、标题、图像、表格、页眉页脚等区域。模型基于 LayoutLM
或专用检测架构，输出带类别标签和几何坐标的版面对象。

### 2.2 表格识别

对于检测到的表格区域，Docling 调用表格结构识别模型，还原表格的行列结构，并将其表示为 HTML 或 CSV 形式，保留单元格合并信息。

### 2.3 阅读顺序恢复

Docling 根据版面元素的空间位置和语义特征，推断正确的阅读顺序，生成线性文本流。该过程对于多栏、复杂布局的 PDF 尤为重要。

### 2.4 标题层级提取

Docling 能识别文档中的标题样式（字体、字号、编号等），提取标题层级，构建文档大纲，输出的结构化内容中包含标题与正文之间的层次关系。

### 2.5 多格式支持

除 PDF 外，Docling 能直接解析 Office 文档（基于 python-docx、python-pptx 等），并统一转换为相同的内部表示。

------

## 3. 架构与工作流程

Docling 的解析流程分为多个阶段：

1. **格式检测与后端选择**：根据文件类型选择解析后端。
2. **初步解析**：提取文本和图像，获取页面元数据。
3. **版面分析**：在 PDF 页面渲染图像上运行版面检测模型。
4. **表格结构识别**：对表格区域进行结构识别。
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

python

```
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 输出 Markdown
markdown_text = result.document.export_to_markdown()

# 输出 JSON
json_output = result.document.export_to_dict()
```

### 高级用法：启用 OCR 和表格识别



```python
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
result = converter.convert("scanned.pdf")
```

------

## 5. 输出示例

Docling 导出的 JSON 包含完整的版面层级，示例结构：



```json
{
  "schema_name": "DoclingDocument",
  "version": "1.0",
  "body": {
    "children": [
      {
        "type": "title",
        "text": "第一章 引言",
        "level": 1
      },
      {
        "type": "paragraph",
        "text": "这是正文内容..."
      },
      {
        "type": "table",
        "data": "<table><tr><td>...</td></tr></table>"
      }
    ]
  }
}
```

------

## 6. 应用场景

- **RAG 数据预处理**：将 PDF 转换为 Markdown 或 JSON，便于分块和向量化。
- **文档转换**：作为企业内容管理流水线的一部分，统一多种格式。
- **信息抽取**：基于结构化输出提取标题、表格等字段。
- **知识库构建**：与向量数据库配合，实现可追溯的智能问答。

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