# Agentic Document Processing 详解

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

一个智能体在"思考-行动-观察"循环中工作。它接收文档和任务，自主决定调用哪些工具（如"提取表格"、"OCR
图像"），观察工具返回结果，并决定下一步，直到完成目标。

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

为什么必须这么分工，而不是让 agent 包办一切：解析这一步是**确定性的**——同一份 PDF 交给同一版本的
Docling/PaddleOCR，输出的文本、坐标、表格单元格可以复现、可以断言、可以写单元测试，失败模式也清楚
（漏字、串行、表格错列）。这种活不需要"判断"，只需要算力和规则，用 LLM 去调它只会多花钱、多引入不确定性，
还让结果无法回归测试。

反过来，**决策与异常处理是不确定的**，没有固定规则可写：这页是扫描件还是电子版、抽到的字段缺失是文档里
真没有还是解析失败、"第 3 页这张表和附件里的表是不是同一张"、两个候选条款哪个才是付款条款。这些判断才是
LLM 该花的地方。

所以正确的形态是：确定性工具产出结构化中间态（带页码、坐标、表格），agent 只在这层之上做路由、查漏、
交叉验证和取舍。凡是能被规则写成 if-else 的步骤，都不应该出现在 agent 的循环里。

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

以"从合同 PDF 中提取关键条款"为例：

1. **输入**：上传合同 PDF，任务为提取"付款条款、违约责任、终止条件"。
2. **智能体规划**：决定先解析 PDF 文本，再定位相关章节，最后抽取条款。
3. **执行工具**：调用 Docling 提取文本；使用正则或 LLM 定位标题；对复杂表格使用视觉模型。
4. **自我检查**：智能体检查是否已覆盖所有要求字段；若缺失，则回溯搜索。
5. **输出**：生成结构化 JSON 结果，包含条款内容和引用页码。

------

## 5. 实现示例（LangGraph）

下面这份代码按 LangGraph 现代写法组织：状态用 TypedDict，工具用 @tool 装饰器，决策节点先 bind_tools 再
invoke，条件边用第三个参数 path_map 把路由返回值映射到节点名。

环境说明：本机环境（E:\miniconda3\envs\llamaindex）**未安装 langgraph / langchain-core**，
因此这份代码只做了 Python 语法编译检查（py_compile 通过），**未安装依赖、未端到端运行**；
装好依赖后还需把三个工具的 `...` 换成真实实现。

```python
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """图的全局状态。add_messages 让消息按追加方式合并，而不是整体覆盖。"""

    messages: Annotated[list[AnyMessage], add_messages]
    document_path: str
    extracted: dict
    done: bool


@tool
def extract_text(path: str) -> str:
    """用 Docling 解析文档，返回 Markdown 文本。"""
    from docling.document_converter import DocumentConverter

    return DocumentConverter().convert(path).document.export_to_markdown()


@tool
def detect_tables(path: str) -> str:
    """返回文档中表格的 Markdown 表示，用于核对结构化字段。"""
    from docling.document_converter import DocumentConverter

    doc = DocumentConverter().convert(path).document
    return "\n\n".join(t.export_to_markdown(doc=doc) for t in doc.tables)


@tool
def ask_vlm(question: str, path: str) -> str:
    """把页面图像交给视觉模型提问，用于图表、扫描页、非文本版式。"""
    # 这里接你们自己的 VLM 客户端（例如 docling 的 VlmPipeline 或远程 API）
    raise NotImplementedError("接入具体 VLM 客户端")


tools = [extract_text, detect_tables, ask_vlm]
llm_with_tools = llm.bind_tools(tools)     # 决策权通过 bind_tools 绑定，不是给 invoke 传 tools 参数


def agent_node(state: State) -> dict:
    """决策节点：让模型看着历史消息决定下一步调用哪个工具。"""
    resp = llm_with_tools.invoke(
        [SystemMessage(content="你是合同抽取助手，先解析、再定位、最后校验，用工具完成。")]
        + state["messages"]
    )
    return {"messages": [resp]}


def route_after_agent(state: State) -> Literal["tools", "finalize"]:
    """收敛条件：模型不再发起工具调用，就认为它给出了最终答案。"""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "finalize"


def finalize_node(state: State) -> dict:
    """收尾节点：把最终消息标成完成态，供下游或外层循环判断。"""
    return {"done": True}


graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("finalize", finalize_node)

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    route_after_agent,
    {"tools": "tools", "finalize": "finalize"},   # path_map：把路由返回值映射到节点名
)
graph.add_edge("tools", "agent")                  # 工具执行完回到决策节点
graph.add_edge("finalize", END)                   # 收尾节点结束整个图

app = graph.compile()

# 运行：recursion_limit 是防止模型反复调工具不收敛的硬闸门
result = app.invoke(
    {"messages": [("user", "抽取付款条款与违约责任")],
     "document_path": "contract.pdf",
     "extracted": {},
     "done": False},
    config={"recursion_limit": 25},
)
```

几个容易踩的坑：

- **State 不要写成 `class State(dict)`**：LangGraph 依赖 TypedDict/pydantic 的注解来做状态合并，
  写成普通 dict 子类注解会被忽略，`add_messages` 这类 reducer 也不生效。
- **工具不要用老式 `from langchain.tools import Tool`**：`Tool(name=..., func=...)`
  在 langchain 0.2 之后已不推荐，@tool 装饰器会把函数签名和 docstring 自动变成工具的 schema。
- **不要给 `invoke` 传 tools 参数**：工具绑定在模型对象上（`bind_tools`），
  invoke 只接收消息。
- **`add_conditional_edges` 一定要给 path_map**：否则路由函数返回的字符串必须是节点名，
  返回 `END` 常量或中文状态词时很容易连不上边。
- **必须有收敛条件**：本例用"最后一条消息没有 tool_calls"作为收敛判据，同时用 `recursion_limit`
  兜底；不要依赖"模型自己说完成了"。

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
- **成本由 LLM 调用次数决定**：整条流程的耗时与费用基本与串行 LLM 调用次数成正比。超过 5 次串行调用的
  流水线，通常比确定性解析慢一到两个数量级；能批处理就别逐页调用，能规则判断就别让模型判断。

------

## 7. 应用场景

- **复杂合同/法律文档分析**：动态定位并抽取条款。
- **研究报告信息提取**：从非结构化 PDF 中提取数据、图表结论。
- **多语言文档处理**：借助 LLM 翻译和跨语言理解。
- **RAG 数据预处理增强**：智能体决定如何分块、标注元数据。
- **自动化表单填写**：从扫描件中提取字段并映射到目标格式。
