# gentic Document Processing 详解

> Agentic Document Processing（智能体文档处理）是指利用大语言模型驱动的智能体（Agent）对文档进行理解、抽取、推理和决策的方法。与传统的确定性解析流水线不同，Agentic
> 方法将文档处理视为一个动态、可交互的任务，由智能体自主规划、调用工具、自我修正，以完成复杂的信息抽取与知识整合。

------

## 1. 定义与特征

Agentic Document Processing 将文档解析与理解任务分解为多个步骤，由一个或多个智能体（通常基于
LLM）通过工具调用（OCR、版面分析、代码执行、数据库查询等）逐步完成。其核心特征包括：

- **动态规划**：智能体根据文档内容和任务目标，动态决定下一步操作。
- **工具使用**：调用外部工具（如 OCR 引擎、表格识别器、向量检索器）辅助处理。
- **自我反思与修正**：智能体能检查自身输出，发现错误并重新执行。
- **多模态理解**：支持文本、图像、表格等混合内容的理解与关联。
- **可编排性**：可设计为单智能体循环或多智能体协作流程。

------

## 2. 架构模式

### 2.1 单智能体循环（ReAct 模式）

一个智能体在“思考-行动-观察”循环中工作。它接收文档和任务，自主决定调用哪些工具（如“提取表格”、“OCR
图像”），观察工具返回结果，并决定下一步，直到完成目标。

流程：



```text
输入文档 + 任务描述
    ↓
[智能体] 分析需求，选择工具
    ↓
[工具] 执行（如 OCR、版面分析、文本提取）
    ↓
[智能体] 检查结果，决定下一步
    ↓
最终输出结构化结果
```

### 2.2 多智能体协作

采用多个角色化智能体协同处理文档，例如：

- **解析智能体**：负责布局分析与文本提取。
- **抽取智能体**：负责从解析结果中抽取关键信息。
- **校验智能体**：负责检查抽取结果的一致性与完整性。
- **汇总智能体**：整合各阶段结果，生成最终输出。

该模式通常使用 LangGraph、CrewAI 等框架进行编排。

### 2.3 智能体 + 确定性工具混合

将确定性解析工具（如 Docling、PaddleOCR）作为智能体的工具之一，智能体负责高层决策、异常处理和语义理解，底层解析仍依赖专业工具。

------

## 3. 关键组件

### 3.1 智能体框架

常用框架：

- **LangGraph**：基于图状态机，支持循环、条件分支、人工介入。
- **CrewAI**：角色化多智能体编排。
- **AutoGen**：多智能体对话与协作。
- **OpenAI Swarm**：轻量级多智能体路由。

### 3.2 文档解析工具

作为智能体的工具集，可包括：

- OCR：PaddleOCR、Tesseract
- 版面分析：Docling、unstructured
- 表格识别：Table Transformer、PaddleStructure
- 视觉问答：多模态大模型（如 GPT-4o、Claude Vision）

### 3.3 知识库与记忆

智能体可将处理结果写入向量数据库，支持后续检索与复用。常用向量数据库：ChromaDB、Qdrant、Milvus。

### 3.4 校验与评估

使用 LLM-as-a-Judge 或规则校验器对抽取结果进行评分，低于阈值则触发重新处理。

------

## 4. 工作流程示例

以“从合同 PDF 中提取关键条款”为例：

1. **输入**：上传合同 PDF，任务为提取“付款条款、违约责任、终止条件”。
2. **智能体规划**：决定先解析 PDF 文本，再定位相关章节，最后抽取条款。
3. **执行工具**：调用 Docling 提取文本；使用正则或 LLM 定位标题；对复杂表格使用视觉模型。
4. **自我检查**：智能体检查是否已覆盖所有要求字段；若缺失，则回溯搜索。
5. **输出**：生成结构化 JSON 结果，包含条款内容和引用页码。

------

## 5. 实现示例（伪代码）



```python
from langgraph.graph import StateGraph, END
from langchain.tools import Tool

# 定义状态
class State(dict):
    document: str
    task: str
    extracted_data: dict
    messages: list

# 工具定义
tools = [
    Tool(name="extract_text", func=extract_text_from_pdf),
    Tool(name="detect_tables", func=detect_tables),
    Tool(name="ask_vlm", func=ask_visual_model),
    Tool(name="validate", func=validate_extraction)
]

# 智能体节点（LLM 决策循环）
def agent_node(state):
    # 调用 LLM，决定使用哪个工具
    response = llm.invoke(state["messages"], tools=tools)
    return response

# 条件路由
def route(state):
    if state["done"]:
        return END
    else:
        return "agent_node"

# 构建图
graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", route)
app = graph.compile()
```

------

## 6. 优势与挑战

### 优势

- 能处理非标准、复杂版式文档，自适应性强
- 利用 LLM 语义理解，可抽取隐含信息
- 支持动态任务，无需为每种文档设计独立流水线
- 可以组合多种工具，能力可扩展

### 挑战

- 延迟和成本较高（多次 LLM 调用和工具执行）
- 结果不稳定，可能出现幻觉或遗漏
- 调试和评估复杂
- 对长文档需要有效的上下文管理

------

## 7. 应用场景

- **复杂合同/法律文档分析**：动态定位并抽取条款。
- **研究报告信息提取**：从非结构化 PDF 中提取数据、图表结论。
- **多语言文档处理**：借助 LLM 翻译和跨语言理解。
- **RAG 数据预处理增强**：智能体决定如何分块、标注元数据。
- **自动化表单填写**：从扫描件中提取字段并映射到目标格式。