# Headroom 综合指南：概念、实践与 LangGraph 融合

> 本文档整合了关于 **Headroom** 从概念入门到多 Agent 实战的全部关键内容，形成一份完整的技术指南。

------

## 1. 什么是 Headroom？

**Headroom** 是一个为 AI Agent 和大语言模型（LLM）应用设计的**上下文压缩层**。它定位为一个运行在 AI Agent 和 LLM 服务之间的
**中间件**，旨在通过压缩输入给大模型的上下文，来降低 Token 消耗和 API 成本，同时保证回答质量不变。

### 核心功能

- 压缩 AI Agent 读取的几乎所有内容：
    - 工具（Tools）的输出结果
    - 系统日志（Logs）
    - 代码文件
    - RAG 检索到的文档片段
    - 对话历史

###  性能数据

| 数据类型     | Token 节省率                    |
|:---------|:-----------------------------|
| JSON 数据  | 60% - 95%                    |
| 代码 Agent | 15% - 20%                    |
| 实测案例     | 10,144 → 1,260 Token（节省 88%） |

------

## 2. 核心项目：headroomlabs-ai/headroom

**GitHub 地址**：https://github.com/headroomlabs-ai/headroom

### 核心组件（四大压缩引擎）

| 引擎                   | 功能                          |
|:---------------------|:----------------------------|
| **CacheAligner**     | 缓存对齐，稳定请求前缀以提高 LLM 提供商缓存命中率 |
| **ContentRouter**    | 内容路由器，根据内容类型（JSON、代码等）智能分发  |
| **SmartCrusher**     | 专门压缩 JSON 数据，效率极高           |
| **CodeCompressor**   | 基于 AST 的代码压缩器，支持 6 种语言      |
| **Kompress-v2-base** | 基于 ModernBERT 的通用文本压缩器      |

### 使用方式

| 方式              | 说明                           | 适用场景                    |
|:----------------|:-----------------------------|:------------------------|
| **库 (Library)** | Python/TS 中直接调用 `compress()` | 精细控制压缩逻辑                |
| **代理 (Proxy)**  | 启动本地代理服务器                    | **零代码修改**，最推荐           |
| **Agent 包装**    | 一键包装主流 AI 编程工具               | Claude、Cursor、Copilot 等 |
| **MCP 服务器**     | 提供标准 MCP 工具                  | 支持 MCP 的客户端             |

###  安装



```bash
# Python
pip install headroom-ai

# TypeScript/Node.js
npm install headroom-ai

# Docker
docker pull ghcr.io/headroomlabs-ai/headroom
```

### 许可证

**Apache 2.0**，允许自由使用、修改和再分发。

------

## 3. 架构设计


- **Rust 核心** (`headroom-core`)：负责压缩变换、Tokenization、CCR 存储和代理服务器
- **Python SDK / CLI**：用户接口、与 AI 应用集成
- **PyO3/Maturin**：实现 Python 与 Rust 的无缝调用

###  关键设计决策

1. **可逆压缩 (CCR)**：压缩内容发给 LLM，原始内容缓存在本地。LLM 可通过 `headroom_retrieve` 取回原文。
2. **“活区 (Live-Zone)”压缩**：只压缩最新一轮用户消息和最新工具输出，保护对话缓存。
3. **安全第一**：绝不丢失用户内容，不破坏工具调用配对关系。

------

## 4. 状态管理与持久化

###  SharedContext：多 Agent 共享记忆总线

`SharedContext` 通过**压缩-缓存-检索 (CCR)** 模式，实现跨 Agent 的高效上下文传递。



```python
from headroom.memory import SharedContext

ctx = SharedContext()

# Agent A 存储大型上下文（自动压缩）
ctx.put("project_analysis", large_analysis_result)

# Agent B 读取（默认返回压缩版本）
summary = ctx.get("project_analysis")        # 压缩后，节省 40-60% Token
full = ctx.get("project_analysis", full=True) # 获取原始内容
```

###  持久化记忆系统

| 组件    | 技术                   |
|:------|:---------------------|
| 存储后端  | SQLite               |
| 向量索引  | HNSW / sqlite-vec    |
| 文本索引  | FTS5                 |
| 嵌入生成器 | 本地模型 / ONNX / OpenAI |


### 与 LangGraph Checkpointer 协同

| 组件                         | 职责                   |
|:---------------------------|:---------------------|
| **LangGraph Checkpointer** | 保存工作流执行进度（走到哪个节点）    |
| **Headroom SharedContext** | 保存大体积业务数据（审查报告、测试代码） |

两者互补：**Checkpointer 管理“走到哪了”**，**Headroom 管理“带着什么”**。

------

## 5. 与 LangGraph 融合

###  融合分工

| 组件               | 角色          | 核心价值                               |
|:-----------------|:------------|:-----------------------------------|
| **LangGraph**    | 工作流“编排引擎”   | 定义 Agent 协作逻辑、管理执行状态、提供断点续传        |
| **Headroom**     | 上下文“压缩与共享层” | Agent 间的记忆总线，压缩存储大段上下文，降低 Token 成本 |
| **Checkpointer** | 工作流“持久化”    | 保存图状态，实现任务中断后恢复                    |

###  融合示例



```python
from langgraph.graph import StateGraph, END
from headroom import SharedContext
from headroom.integrations import HeadroomChatModel

ctx = SharedContext()
wrapped_llm = HeadroomChatModel(ChatOpenAI(model="gpt-4o"))

class AgentState(TypedDict):
    code: str
    review_result: str
    test_code: str

def node_code_reviewer(state):
    review = "审查报告：代码整体良好..."
    ctx.put("code_review_report", review)   # 存入 Headroom（自动压缩）
    return {"review_result": review}

def node_test_generator(state):
    review = ctx.get("code_review_report")  # 从 Headroom 读取（自动解压）
    test = f"# 基于审查生成测试\n# {review[:30]}..."
    return {"test_code": test}

# 构建图
builder = StateGraph(AgentState)
builder.add_node("code_review", node_code_reviewer)
builder.add_node("generate_test", node_test_generator)
builder.set_entry_point("code_review")
builder.add_edge("code_review", "generate_test")   # 普通边：固定跳转
builder.add_edge("generate_test", END)

# 编译并加入检查点
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)
```

在上面的示例中，`add_edge` 用于定义确定的执行顺序，而更复杂的条件分支（如根据状态决定下一步）可以使用
`add_conditional_edges`。LangGraph 提供了灵活的边定义来支持各种工作流模式，但在本文中我们不过多展开。

------

## 6. 完整 Demo：多 Agent 协作 + 断点续传

这是融合了 **Headroom + LangGraph** 的完整示例，实现了：

-  多 Agent 协作（代码审查员、测试生成器、报告生成器）
-  跨 Agent 上下文压缩共享（通过 Headroom `SharedContext`）
-  任务半截重启后自动恢复（通过 LangGraph Checkpointer + Headroom 持久化）
-  条件分支（根据审查结果决定是否生成测试）

###  完整代码



```python
import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from headroom import SharedContext
from headroom.integrations import HeadroomChatModel

# ---------- 1. 初始化 ----------
ctx = SharedContext()
wrapped_llm = HeadroomChatModel(ChatOpenAI(model="gpt-4o"))

# ---------- 2. 定义状态 ----------
class AgentState(TypedDict):
    code: str
    review_result: str
    test_code: str
    final_report: str

# ---------- 3. 节点函数 ----------
def node_code_reviewer(state: AgentState) -> dict:
    print("🔍 [节点: 审查员] 开始审查代码...")
    review = f"审查报告：代码 '{state['code'][:30]}...' 整体良好，建议增加错误处理。"
    ctx.put("code_review_report", review)  # 存入 Headroom
    return {"review_result": review}

def node_test_generator(state: AgentState) -> dict:
    print("🧪 [节点: 测试生成器] 生成测试...")
    compressed_review = ctx.get("code_review_report")  # 读取 Headroom
    test = f"# 基于审查生成的测试\n# {compressed_review[:30]}...\ndef test_func(): pass"
    ctx.put("generated_test_code", test)
    return {"test_code": test}

def node_final_reporter(state: AgentState) -> dict:
    print("📝 [节点: 报告生成器] 生成最终报告...")
    review = ctx.get("code_review_report")
    test = ctx.get("generated_test_code")
    report = f"审查结果: {review}\n测试代码: {test}"
    return {"final_report": report}

def should_continue(state: AgentState) -> Literal["generate_test", "end"]:
    """条件路由函数：根据审查结果决定是否生成测试"""
    if state.get("review_result"):
        return "generate_test"
    return "end"

# ---------- 4. 构建图 ----------
builder = StateGraph(AgentState)

# 添加节点
builder.add_node("code_review", node_code_reviewer)
builder.add_node("generate_test", node_test_generator)
builder.add_node("final_report", node_final_reporter)

# 添加边
builder.set_entry_point("code_review")                      # 入口
builder.add_edge("code_review", "final_report")             # 普通边：固定跳转
builder.add_conditional_edges(                              # 条件边：动态决策
    "final_report",
    should_continue,
    {"generate_test": "generate_test", "end": END}
)
builder.add_edge("generate_test", END)

# 编译并加入检查点（支持断点续传）
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

# ---------- 5. 执行 ----------
if __name__ == "__main__":
    initial_state = {"code": "def add(a,b): return a+b"}
    config = {"configurable": {"thread_id": "demo-thread-1"}}

    print(" 开始执行工作流...")
    for event in graph.stream(initial_state, config, stream_mode="values"):
        print(f"   -> 当前状态: {list(event.keys())}")

    print("\n 工作流执行完毕。")
    print(" 存储的最终报告:")
    print(ctx.get("final_report"))
```




------

## 7. 总结

###  Headroom 在不同层面的作用

| 层面             | 核心功能                               |
|:---------------|:-----------------------------------|
| **单次 LLM 调用**  | 压缩输入上下文，降低 Token 消耗                |
| **单 Agent 会话** | 压缩对话历史，保持上下文连贯性                    |
| **多 Agent 协作** | 通过 SharedContext 高效共享上下文           |
| **任务持久化**      | 与 LangGraph Checkpointer 结合，实现断点续传 |

###  关键设计理念

- **分离关注点**：Headroom 负责“如何高效存/传”，LangGraph 负责“如何调度和决策”。
- **可逆压缩**：压缩不是为了丢失信息，而是为了降本，需要时可找回原文。
- **安全优先**：绝不丢失用户数据，绝不破坏工具调用配对。