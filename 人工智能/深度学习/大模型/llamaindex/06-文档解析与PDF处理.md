# 06 文档解析与 PDF 处理

> 版本基线：pypdf 6.x / docling 2.150.1 / docling-ibm-models 4.0.4 / huggingface_hub 1.33.0 / transformers 5.23.0 / llama-index-core 0.14.26
> 本章所有数字均为本机实测（Windows + i5-9400 + 16GB，纯 CPU），不是官方文档抄来的。

## 6.0 一句话结论

PDF 不是"带格式的文本"，而是"打印指令单"。理解这一点，所有工具的行为都能预测：

- **pypdf 拿的是字符层**，快、确定、可编程，但不理解版面；
- **docling 拿的是语义层**，懂标题、表格、图片，但慢 50~600 倍且是推测；
- **OCR 不是解析器**，它是从像素"造出"字符层，只在没有字符层时才需要；
- **公式谁都给不了**，想要精确 LaTeX 只能绕过 PDF 去拿源文件。

选择工具不要看"PDF 里有什么"，要看"下游要什么"：只要文字就 pypdf，要结构才请 docling，要算数（Excel 那类）两者都不要。

---

## 6.1 PDF 是什么：三层信息模型

PDF 从 PostScript 继承而来，本质是一串"在某个坐标、用某个字体、画某个字形"的指令。按这三层理解：

| 层 | 内容 | 在 PDF 里存在吗 | 谁拿得到 |
|---|---|---|---|
| 第一层 字符层 | 页面上有哪些字（字符码） | 存在（/Font + Tj 操作符） | pypdf、pdfplumber |
| 第二层 坐标层 | 每个字形画在哪个 x/y | 存在（文本矩阵 Tm） | pypdf（layout 模式有损）、pdfplumber（无损） |
| 第三层 语义层 | 这块是标题、那是表格、这几行是一张表 | **从来不存在** | 只能靠模型推断（docling） |

还有一个比第一层更底层的"绘图层"：颜色（rg/RG）、矩形（re）、填充（f）、线条（S）。**表格的彩色表头、格线都活在这一层**，所以 pypdf 读得到"参数项目"四个字，读不到它是深蓝底白字。

### 判断一份 PDF 要怎么处理

只要两个问题：

1. **有没有文本层？**（页面里有没有 /Font 和 Tj）→ 决定要不要 OCR
2. **要不要结构？**（表格、标题树、图表位置）→ 决定 pypdf 还是 docling

实测对照：文本型 PDF 的 content stream 里有 `BT / Tf / Tm / Tj`；图片型 PDF 的 Resources 里只有 `/ProcSet` 和 `/XObject`，content stream 只有 47 字节的 `q 800 0 0 400 0 0 cm /image Do Q`，`extract_text()` 返回空字符串。

---

## 6.2 工具站位表

| 工具 | 站在哪层 | 给你什么 | 耗时（4~6 页） |
|---|---|---|---|
| pypdf `plain` | 一层 | 字符流，按绘制顺序拼接 | < 0.1s |
| pypdf `layout` | 一层 + 二层（有损） | 把 x 坐标差编码成空格 | ~0.1s |
| pdfplumber | 一层 + 二层（无损） | 每个字符的精确 bbox | ~0.3s |
| docling | 一层 + 三层 | 渲染成图看版面，输出 markdown/JSON | 11~46s |
| docling + OCR | 造出一层 + 三层 | 扫描件也能出内容 | +5~6s/页 |
| Nougat / MinerU / Marker | 三层（学术特化） | 公式出 LaTeX | 分钟级 |
| GROBID | 元数据层 | 作者、机构、参考文献（TEI XML） | 需 Java 服务 |

---

## 6.3 pypdf 实测

### 6.3.1 plain 与 layout 的长度差

真实业务 PDF（4 页《制造车间质量管控技术规范》）：

| 页 | plain | layout |
|---|---|---|
| 1 | 635 | 829 |
| 2 | 745 | 1168 |
| 3 | 648 | 1144 |
| 4 | 294 | 305 |

双栏论文（6 页，ACL 格式）：

| 页 | plain | layout |
|---|---|---|
| 1 | 5613 | 6905 |
| 2 | 6414 | 9568 |
| 3 | 3278 | 5792 |
| 4 | 5413 | 7313 |
| 5 | 5764 | 7797 |
| 6 | 8119 | 13085 |

layout 多出来的字符**全是空格**。它并没有读到更多字，只是把坐标差编码成了空白。

### 6.3.2 layout 的信息损失

实测同一行"塌落度 ≤0.1mm -"，两种切法：

```python
"塌落度      ≤0.1mm      -".split(" ")        # 35 段，大部分是空串
re.split(r" {2,}", "塌落度      ≤0.1mm      -")  # ['塌落度', '≤0.1mm', '-']
```

**空格是有损编码**：相距 3pt 和相距 30pt 可能都输出一个空格，相距 10pt 和 11pt 却可能差一个。所以 layout 不是"更准"，是"把第二层暴露了一部分，同时引入空格噪声"。

### 6.3.3 双栏拼行（必须知道的坑）

双栏论文里，同一 y 坐标有两段文字。layout 模式按 y 分行，于是把左右栏拼成一行。实测论文第 2 页：

```
[ 116] TABLE I                                    at the word level to capture both the syntactic and semanti
[ 157] Source   Speaker   D(G(.))   Utterance             multi-turn dialogu
[ 185] Context0 Penny     NA        You have to, we all have to be there ... surprise!.
```

左栏的表格和右栏的正文直接焊在一行。**结论：双栏文档不要直接用 layout 输出。**

但 pypdf 的另一半价值在这里：坐标是精确数字。用 `visitor_text` 收集每个块的 x，做 10pt 桶直方图，双栏会呈现双峰：

```
x 桶分布: [40: 40 块, 310: 41 块]   ← 40pt 是左栏，310pt 是右栏
同一高度存在左右两块的 y 行数: 30
```

分栏就这么写：

```python
from pypdf import PdfReader

page = PdfReader(pdf_path).pages[0]
blocks = []
def visitor(text, cm, tm, font_dict, font_size):
    if text.strip():
        blocks.append((round(tm[4], 1), round(tm[5], 1), text))
page.extract_text(visitor_text=visitor)

mid = float(page.mediabox.width) / 2      # 612pt 页面取 306
left  = sorted([b for b in blocks if b[0] <  mid], key=lambda b: -b[1])
right = sorted([b for b in blocks if b[0] >= mid], key=lambda b: -b[1])
```

**结果完全确定**——x 是文件里的真实数字，不是猜的。这就是 pypdf 的核心价值：给你可控的原料，代价是逻辑自己写。

### 6.3.4 表格切分

纯文本表格（无格线、靠空格对齐）用这条规则：

```python
import re
cells = re.split(r" {2,}", line.strip())
```

配合"连续 ≥2 行且列数严格相同"分块：

```python
def table_blocks(page_text, min_rows=2, min_cols=2):
    out, cur = [], []
    for line in page_text.splitlines():
        if not line.strip():
            continue            # 空行必须跳过，不能当边界
        cells = re.split(r" {2,}", line.strip())
        if cur and len(cells) != len(cur[-1]):
            if len(cur) >= min_rows and len(cur[0]) >= min_cols:
                out.append(cur)
            cur = []
        cur.append(cells)
    if len(cur) >= min_rows and len(cur[0]) >= min_cols:
        out.append(cur)
    return out
```

两个反直觉的细节：

- **空行不能当块边界**。layout 输出在每个表格行之间都插空行，把它当边界会导致所有块都是空的。
- **"连续 + 同列数"是判据，"有间隔"不是**。文档抬头「文档编号：QC-2024-0315　　版本：V2.1」中间也有 4 个空格，跟表头行在空格数量上完全没区别。靠空格数区分不了，只能靠"它孤零零一行、上下没有同列数的邻居"。

实测（真实 PDF 四页）：page1 得 1 块（3 列 x 4 行，抬头行被正确过滤）；page2 得 2 块；page3 得 3 块，其中「电话/工号/签字」栏被误判成 2 列 x 2 行的表。**min_rows=3 能滤掉它，但会丢掉跨页续表。**

### 6.3.5 ragged 表格（列数不齐）

合并单元格会导致某几行只有 2 列、其他行 3 列。严格按列数相等切，整个"颗粒度 | 25-45μm"那行会消失。

正解是**列锚点对齐**：先记住每列起始偏移，再按最近锚点分配、缺列补空：

```python
parts = re.split(r"( {2,})", line)     # 保留分隔符，才能累加偏移
pos, cells = 0, []
for seg in parts:
    if seg.strip():
        cells.append((pos, seg.strip()))
    pos += len(seg)
# 每行按 cell 起点匹配锚点（容差 4 字符），匹配不到就补空
```

逆序有讲究：**必须先按"连续同列数"分块，再在块内算锚点**。直接对整页算锚点会串——实测 page1 锚点变成 `[2,14,23,32,46]`，抬头的 2/23 和表格的 14/32/46 混成 5 列，输出全错位。

### 6.3.6 pypdf 的硬限制

| 想要 | pypdf 能给吗 |
|---|---|
| 文字 | 能 |
| 字号大小 | 能（visitor 里拿 font_size） |
| 字体名 | 能（font_dict 的 /BaseFont） |
| 颜色 | **不能**（在绘图层） |
| 粗体/斜体的语义 | 不能，只能靠字体名猜 |
| 表格"这张表有几行几列" | 不能，得自己切 |
| 公式 | 只能给碎片 |
| 图片 | 能枚举并导出原始 XObject（jpg/png） |

---

## 6.4 docling 实测

### 6.4.1 版本与依赖坑（血泪）

docling 的依赖链比 pypdf 脆得多，踩过的坑按出现顺序：

**坑一：HF 缓存符号链接权限。** Windows 上首次下载报 `OSError [WinError 1314] 客户端没有所需的特权`，因为 huggingface_hub 默认用符号链接共享缓存。解法：设环境变量 `HF_HUB_DISABLE_SYMLINKS=1`，并删掉 `~/.cache/huggingface/hub/models--docling-project--docling-layout-heron` 重下。

**坑二：hub 2.x 会让 tableformer 卡死。** docling 2.150.1 要 `transformers>=5.16`，transformers 5.23 要 `hub>=1.31`；但 docling-ibm-models 4.0.4 的元数据写 `huggingface_hub<2,>=0.23`。pip 会装到 2.4.0，越过这条线。

表现为 `do_table_structure=True` 时**卡住不返回**（CPU 时间停在 11.9s 不动）。根因在 `docling/models/utils/hf_model_download.py:116`：它裸调 `snapshot_download(..., local_dir=...)`，没有 `local_files_only`，即使权重已落盘也要做远程元数据校验，网络不通就挂住。

**解法：**

```bash
pip install "huggingface_hub>=1.31,<2"
```

降到 1.33.0 后零改动跑通。**不要升回 hub 2.x**，也别指望"升级 docling"能解决——2.150.1 与 4.0.4 都已是当时最新，是上游自己没对齐。

**坑三：`docling.datamodel.layout_model` 这个模块没了。** 2.150 把它改名为 `layout_model_specs`，且内容从"类定义"变成"模型规格常量"：

```python
from docling.datamodel.layout_model_specs import (
    DOCLING_LAYOUT_HERON, DOCLING_LAYOUT_HERON_101,
    DOCLING_LAYOUT_EGRET_MEDIUM, DOCLING_LAYOUT_EGRET_LARGE,
    DOCLING_LAYOUT_EGRET_XLARGE, LayoutModelConfig,
)
```

顺带纠正一个常见误解：**版面模型不是 LayoutLM**，是 RT-DETR 系（`rt_detr_v2`）的 ObjectDetectionModelSpec，heron/egret 是几个不同规格的权重。默认值是 `layout_heron`（repo `docling-project/docling-layout-heron`）。

### 6.4.2 最小可用调用

```python
import time
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

opts = PdfPipelineOptions()
opts.do_table_structure = True    # TableFormer，出真实行列
opts.do_ocr = False               # 有文本层就别开，中文 OCR 很慢

conv = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
)
t0 = time.perf_counter()
doc = conv.convert(pdf_path).document
print(f"耗时 {time.perf_counter()-t0:.2f}s 页数 {len(doc.pages)} 表格 {len(doc.tables)}")

md = doc.export_to_markdown()
```

**默认值实测**（`PdfPipelineOptions`）：`do_ocr=True`、`do_table_structure=True`、`do_formula_enrichment=False`、`force_backend_text=False`、`images_scale=1.0`、`generate_page_images=False`。

注意 `do_ocr` **默认是 True**——它不会只看有字的页面，它会走 OCR 流程。所以文档说"docling 慢"和"docling 默认没关 OCR"是同一件事。有文本层时第一件事就该关掉它。

### 6.4.3 表格：TableFormer 的真实效果

业务 PDF（4 页，含 5 张表）实测：`18.78s`，markdown 2958 字符，5 张表 28 行表格行。

| 表 | 结果 |
|---|---|
| 表1 锡膏参数 | 3 列 x 4 行，表头正确（参数项目/标准值/允许偏差） |
| 表2 储存条件 | 只有 1 行，**表头丢失**，列名变成 `0 1 2` |
| 表3 贴片精度 | 4 列 x 5 行，完全正确 |
| 表4 温度曲线 | 3 列 x 5 行，**表头丢失**，列名 `0 1 2` |
| 表5 缺陷判定 | 3 列 x 5 行，正确 |

**失败模式很均匀：跨页续表丢表头。** 它会把两页的行合并进来，但不会把上一页的表头带过来。所以拿到 `0 1 2` 这种列名，基本就是遇到了跨页表。

关掉 `do_table_structure` 后同样文档 `10.5s`，markdown 3023 字符，但表格被压平成一行：`| 参数项目 标准值 允许偏差 金属含量 88.5% ... |`，**比 pypdf 切出来的还差**。所以这个开关不能省。

### 6.4.4 标题树：docling 最值钱的地方

双栏论文（6 页，45.75 秒，48371 字符 markdown）的 label 分布：

```
text 56 | section_header 18 | list_item 17 | caption 5
table 4 | formula 4 | picture 1 | footnote 1
```

18 个 section_header 与论文真实章节**完全对得上**：

```
I. INTRODUCTION
II. MODEL ARCHITECTURE
  A. hredGAN: Adversarial Learning Framework
  B. phredGAN: Persona Adversarial Learning Framework
  Algorithm 1 Adversarial Learning of phredGAN
III. MODEL TRAINING AND INFERENCE
  A. Model Training / B. Model Inference
IV. EXPERIMENTS AND RESULTS
  A. Datasets / B. Evaluation Metrics / C. Baseline
  D. Hyperparameter search / E. Results
V. CONCLUSION AND FUTURE WORK
REFERENCES
```

这东西 pypdf **没有任何途径**做到。它不知道 "II. MODEL ARCHITECTURE" 是章标题，也不知道 Algorithm 1 该独立成块。

对 RAG 的直接价值：每个 chunk 能带上"它属于哪一章哪一节"，检索时可以当过滤条件，也能在回答里给出准确出处。

### 6.4.5 公式：docling 知道位置，不知道内容

论文里实测 `formula` 对象 4 个，但导出的 markdown 里是：

```html
<!-- formula-not-decoded -->
```

**边界正确，内容为空。** 原因：`do_formula_enrichment` 默认 `False`（本机确认该字段存在于 `PdfPipelineOptions`）。

要解码得打开它，会额外下载 CodeFormulaV2 模型，CPU 上再慢一截。**注意这是"可能出 LaTeX"，不是保证。**

行内公式更微妙：docling 保留了文本，但上下标被拍平——

```
Xi = (X1, X2, · · · , Xi )      ← 原文是 X_i = (X_i^1, X_i^2, ...)
Xi = (X1 i , X2 i , · · ·       ← X_i^1 变成 "X1 i"
```

因为上下标在 PDF 里只是坐标偏移，不是标记。任何工具都只能猜。

### 6.4.6 耗时汇总（纯 CPU，i5-9400）

| 场景 | 冷（含首次加载） | 热 |
|---|---|---|
| 全新机器首次运行 | 33.5s | — |
| 表格结构（4 页） | 10.99s | 2.77s |
| 扫描件 OCR | 5.79s | 3.81s |
| 业务 PDF 全量（开表格） | — | 18.78s |
| 业务 PDF（关表格） | — | 10.5s |
| 双栏论文 6 页（开表格） | — | 45.75s |
| 无文本层 PDF（关 OCR） | — | 2.6s（md_len=0，符合预期） |

**45 秒对 6 页论文 = 7.6 秒/页。** 这是模型推理的固定成本，不是机器差。

### 6.4.7 OCR：不用装新东西，但要调分辨率

本机环境已有 `rapidocr 3.10.0`（onnxruntime 1.32.0 后端，PP-OCRv6 small 权重本地已有），docling 自带 `RapidOcrOptions`，**不需要额外 pip install**。

关键参数是 `scale`，实测结论反直觉：**分辨率不是越高越好。**

| scale | 结果 |
|---|---|
| 3.0（默认） | 800x400pt 样张只出 59~67 字符，`88.5%` 被认成 `S%ll 8 5%%` |
| **2.8** | 三行全对（配合 `text_score=0.3`） |
| 2.6 / 4.0 | 都比 2.8 差 |

```python
from docling.datamodel.pipeline_options import RapidOcrOptions
opts.do_ocr = True
opts.ocr_options = RapidOcrOptions(scale=2.8, text_score=0.3)
```

约 200 dpi 是这个模型的最优区间。盲目调到 4.0 只会更糟。

---

## 6.5 论文场景专题

### 6.5.1 双栏对照实测

同一篇论文（6 页，ACL 格式，含 4 张表和大量公式）：

| 维度 | pypdf | docling |
|---|---|---|
| 耗时 | < 1 秒 | 45.75 秒 |
| 双栏 | layout 拼行，但坐标能精确分栏 | 读对了，正文不串 |
| 章节树 | 无 | 18 个标题层级完整 |
| 公式 | 碎片，丢上下标 | 4 个 formula 对象，内容 not-decoded |
| 表格 | 需自己切（跨栏表极难） | 4 张，带 caption |
| 图 | 能枚举导出 | picture 定位 |
| 稳定性 | 完全确定 | 模型推断 |

### 6.5.2 公式只有两条路

**路一：绕过 PDF。** arXiv 论文可以从 `https://arxiv.org/e-print/编号` 下原始 TeX。这是唯一 100% 准确的路，做论文处理系统第一步就该判断"有没有源文件"。

**路二：学术特化模型。** Nougat（Meta，输出 markdown + LaTeX 公式）、MinerU（上海 AI Lab，中文强）、Marker。这三个是为密集版面训练的，比通用 docling 强，代价是分钟级耗时。

### 6.5.3 元数据与参考文献用 GROBID

要提作者、机构、参考文献列表，别用 pypdf 正则也别用 docling，用 **GROBID**（论文解析事实标准，输出 TEI XML）。它是 Java 服务，本机未装。

自己用正则从文本抠作者和引用，是能做出 80% 效果然后烂在 80% 的经典陷阱。

### 6.5.4 论文场景判据

| 需求 | 用什么 |
|---|---|
| 全文检索 / 灌 RAG | pypdf + 自写分栏，公式丢掉无所谓 |
| 精读笔记 / 要目录 / 要表格 | docling，公式手动补 |
| 公式要准确 | arXiv LaTeX 源，否则 Nougat/MinerU |
| 作者引用机构 | GROBID |

---

## 6.6 其他格式：docx / xlsx / pptx

### 6.6.1 先分清两类格式

| 类别 | 格式 | 特点 |
|---|---|---|
| **自带结构** | docx、xlsx、pptx、md、html、json、csv | 结构是**文件里真实存在**的（style、sheet、标签），不需要视觉模型 |
| **只有渲染结果** | pdf、扫描图 | 只有字符层和坐标层，语义靠推断 |

**所以 Excel 和 Word 根本不需要 docling。** 给 Excel 上视觉模型是杀鸡用牛刀——它的结构是精确的，猜测反而可能猜错。这条划分是三层模型的直接推论：docx 的第一层和第三层在同一个文件里。

### 6.6.2 三个实测的坑

把 llama-index-core 0.14.26 的 `llama_index.readers.file` 全列出来：

```
CSVReader DocxReader EpubReader FlatReader HTMLTagReader HWPReader
IPYNBReader ImageCaptionReader ImageReader ImageTabularChartReader
ImageVisionLLMReader MarkdownReader MboxReader PDFReader PagedCSVReader
PandasCSVReader PandasExcelReader PptxReader PyMuPDFReader RTFReader
UnstructuredReader VideoAudioReader XMLReader
```

**坑一：没有 `DocReader`。** 只有 `DocxReader`。老 `.doc` 是 OLE 二进制格式，这条工具链里**完全没有解析路径**。

**坑二：`DocxReader` 底层是 `docx2txt`，不是 `python-docx`。** 而它没在标准依赖里，实测直接抛：

```
ImportError: docx2txt is required to read Microsoft Word files: `pip install docx2txt`
```

**坑三：`xlrd` 没装。** openpyxl 只认 `.xlsx`，老 `.xls` 要走 xlrd，所以 `.xls` 也读不了。

### 6.6.3 docx 的三种做法

同一个真实 docx（91 万字节），`python-docx` 读出来：**94 段落、0 表格、12 个 Heading 样式段落**。

那 12 个 Heading 就是 docx 自带的第三层语义。而 docx2txt 的做法是抽纯文本，把它们和正文混成一串，层级全部丢失。

| 做法 | 拿到什么 | 代价 |
|---|---|---|
| `docx2txt`（LlamaIndex 默认） | 纯文本 | 结构全丢，且本机还需先装 |
| `python-docx`（本机 1.2.0 已装） | 段落、表格、`style.name` 层级 | 自己写遍历，约 30 行 |
| docling 的 docx backend | markdown 带 Heading | 慢，但复杂文档省事 |

**建议：docx 不要用 `DocxReader`。** 要结构就用 python-docx 遍历，把 Heading 转成 markdown 的 `#` 层级，比装 docx2txt 再丢结构强得多。

```python
import docx

d = docx.Document(path)
for p in d.paragraphs:
    if p.style.name.startswith("Heading"):
        level = int(p.style.name.split()[-1])
        out.append("#" * level + " " + p.text)
    elif p.text.strip():
        out.append(p.text)
for t in d.tables:                      # 表格单独处理
    for row in t.rows:
        out.append("| " + " | ".join(c.text for c in row.cells) + " |")
```

这样产出的 markdown 可以直接喂给 `MarkdownNodeParser`，免费获得"每块都知道自己在哪一章"的 metadata。

### 6.6.4 Excel：它不是文本，这是最容易翻车的地方

`PandasExcelReader` 的签名（本机实测）：

```python
PandasExcelReader(concat_rows=True, sheet_name=None,
                  field_separator=", ", key_value_separator=": ")
```

注意 `concat_rows=True` 这个默认值。它的行为是**整张表压成一段文本**，每行变成：

```
产品: A, 价格: 100, 库存: 50
产品: B, 价格: 200, 库存: 30
```

两个隐患：

**隐患一：检索没有单位。** 用户问"库存 50 的产品是哪款"，向量命中的是"产品: A, 价格: 100, 库存: 50"这一整行。一行记录没有自然语言语义，embedding 效果天然差。

**隐患二：数值问题 LLM 永远算不对。** "平均价格多少""哪个库存最低"——这类问题不该靠检索 + 心算。算对了也是巧合。

按规模分岔，三种策略：

| 规模 | 做法 | 适用问题 |
|---|---|---|
| 小表（几十行内） | 每行转成一句自然语言 | "有哪些产品""A 的规格是什么" |
| 中表（几百行） | 整表转 markdown 存一个 Document | "这张表讲了什么" |
| 大表 / 要计算 | **不进向量库**，走代码执行（PandasQueryEngine / Text-to-SQL） | "平均价格""库存最低""同比" |

**一条判据：要"找"用向量，要"算"必须代码执行。** 把 Excel 塞进向量库去回答求和问题，是 RAG 项目最常见的翻车点。

### 6.6.5 多格式混在一个目录

```python
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import DocxReader, PandasExcelReader, PDFReader

reader = SimpleDirectoryReader(
    input_dir="docs/",
    file_extractor={
        ".docx": DocxReader(),                      # 或换成自己的 python-docx 包装
        ".xlsx": PandasExcelReader(sheet_name=0),
        ".pdf":  PDFReader(),                       # 想用 docling 就在这里替换
    },
)
docs = reader.load_data()
```

未出现在 `file_extractor` 里的后缀走默认 reader——`.doc`、`.xls` 这类目前会**直接失败**，不静默跳过。

---

## 6.7 决策矩阵总表

| 输入 | 首选 | 关键开关/注意 |
|---|---|---|
| 有文本层 PDF，只要文字 | pypdf `plain` | 双栏要自写 x 分栏 |
| 有文本层 PDF，要表格 | docling | `do_table_structure=True`、`do_ocr=False` |
| 扫描件 PDF | OCR（rapidocr） | `scale=2.8`、`text_score=0.3` |
| 双栏论文 | pypdf + 分栏 / docling | 公式谁都给不了 |
| 要公式 | arXiv LaTeX / Nougat / MinerU | 通用库无解 |
| 要作者引用 | GROBID | Java 服务 |
| `.docx` | python-docx 自写 | 保住 Heading 层级，别用 DocxReader |
| `.doc` | LibreOffice 转换 | `soffice --headless --convert-to docx` |
| `.xlsx` | PandasExcelReader / pandas | 要算数就别向量化 |
| `.xls` | 装 xlrd 或转 xlsx | 本机 xlrd 缺失 |
| `.pptx` | PptxReader | python-pptx 1.0.2 已装 |
| `.md` / `.html` | MarkdownNodeParser / HTMLNodeParser | 自带结构，别先抽成纯文本 |

## 6.8 工程建议：质量检测 + 分级解析

不要按文件类型一刀切，按"这份文件解析出来能不能用"分流：

```python
def parse_page(page):
    txt = page.extract_text()
    if quality_ok(txt, page):        # 字符数够、乱码率低、空格密度不支持有表格
        return cheap_parse(txt)      # 0.05s
    return docling_parse(page)       # 15s，只走这一小部分
```

`quality_ok` 的判据：提取字符数 / 页面面积（太低是扫描件）、非法字符占比、连续空格密度（判断有无表格结构）。

90% 页面走快路径，10% 走慢路径，总耗时约等于 pypdf 加一点零头。这本质是在检测"第一层和第二层拿到多少"，拿到不够才升级工具。

## 6.9 误用清单

- ❌ 用 docling 处理 Excel/Word —— 它们自带结构，上视觉模型是杀鸡用牛刀
- ❌ 相信 "docling 慢是机器差" —— 是模型推理的固定成本，换机器也不会快 10 倍
- ❌ 双栏论文直接用 `layout` 输出 —— 左右栏会被焊成一行
- ❌ 把表格行当独立 chunk 进向量库 —— 一行没有语义，检索必然失效
- ❌ 用向量检索回答 Excel 的求和/比较问题 —— 必须代码执行
- ❌ 用 `DocxReader` 处理 docx 并期待层级 —— 它只给纯文本
- ❌ 把 `.doc` 或 `.xls` 扔给 LlamaIndex —— 本机没有解析路径，会报错
- ❌ 认为 `do_ocr` 默认关闭 —— 它默认 True，有文本层时该主动关掉
- ❌ 把 OCR `scale` 调得越高越好 —— 实测 2.8 最优，4.0 更差

## 6.10 本章对应脚本

| 脚本 | 作用 |
|---|---|
| `12_pdf_load.py` | docling 版 PDF 加载：markdown 导出、表格 DataFrame、结构遍历 |
| `20_docling_basic.py` | docling 五段教学：最小调用 / iterate_items / 两种导出 / 表格开关 / HybridChunker |
| `31_table_ocr.py` | do_table_structure 跑通 + rapidocr 参数调优 |
| `43_paper_compare.py` | 双栏论文 pypdf 坐标层分析：x 直方图、拼行检测、字体统计 |
| `44_paper_docling.py` | 双栏论文 docling 解析：标题树、formula 对象、耗时 |

所有脚本在 `H:\PythonProject\PythonProject\lmtest` 下，运行方式：

```powershell
$env:PYTHONIOENCODING='utf-8'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
& E:\miniconda3\envs\llamaindex\python.exe <脚本>
```
