# LangChain 多 Agent 系统深度解析：架构、多轮对话与工具调用

## 1. 为什么需要多 Agent？——单 Agent 的三大痛点

单 Agent 系统在复杂业务场景中会暴露出明显局限：

- **工具选择困难**：单个 Agent 被赋予过多工具（数据库、邮件、数据分析等）时，容易误用或调用效率低下。
- **上下文爆炸**：工作记忆需承载用户历史、中间结果、工具调用记录，导致信息过载，性能随上下文增大而显著下降。
- **角色迷失**：迫使一个 Agent 同时扮演多个角色，系统提示词冗长矛盾，影响决策准确性。

多 Agent 系统借鉴现代公司的分工模式——每个 Agent 专注特定领域，独立开发、测试、维护，行为更可预测。实验数据表明，**多 Agent
协作成功率比单一 Agent 高出 90.2%**。

---

## 2. 多 Agent 核心架构：Supervisor 模式

LangChain 生态中最主流的多 Agent 架构是 **Supervisor（主管）模式**。其核心思想是：一个中央“主管”Agent 负责接收任务、判断该调用哪个子
Agent、协调整个流程。

```text
用户
  ↓
Supervisor（调度员 Agent）
  ├── ResearchAgent（研究/信息搜集）
  ├── MathAgent（数学计算）
  ├── WeatherAgent（天气查询）
  └── WritingAgent（内容撰写）
```

LangGraph 官方推荐使用 基于工具调用（tool‑calling）的方式 来实现 Supervisor，而非专门的库。这种方式对上下文工程有更强的控制力。

核心实现思路：将每一个子 Agent 包装成一个 Tool，挂载给 Supervisor 使用。Supervisor 通过工具调用“调用”子 Agent，子 Agent
返回结果，流程循环直至任务完成。

## 3. 工具调用（Tool Calling）机制

### 3.1 工具定义

使用 @tool 装饰器将普通函数转为 LangChain 工具：

```python
from langchain_core.tools import tool


@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    # 执行搜索逻辑
    return search_results
```

### 3.2 子 Agent 创建

使用 create_react_agent 创建带有特定工具集的子 Agent：

```python
from langgraph.prebuilt import create_react_agent

math_agent = create_react_agent(
    model=model,
    tools=[add, multiply],
    name="math_expert",
    prompt="You are a math expert. Always use one tool at a time."
)

research_agent = create_react_agent(
    model=model,
    tools=[web_search],
    name="research_expert",
    prompt="You are a world class researcher with access to web search."
)
```

### 3.3 ToolNode：工具执行节点

LangGraph 预置了 ToolNode，专门负责执行工具调用：

支持 并行执行 多个工具调用

输出为 ToolMessage 列表，追加到状态中

可处理同步或异步执行

### 3.4 Supervisor 创建工作流

```python
from langgraph_supervisor import create_supervisor

workflow = create_supervisor(
    [research_agent, math_agent],
    model=model,
    prompt=(
        "You are a team supervisor managing a research expert and a math expert. "
        "For current events, use research_agent. "
        "For math problems, use math_agent."
    )
)
app = workflow.compile()
```

### 3.5 两种 Agent 交接模式

| 模式                      | 适用场景      | 特点                                   |
|-------------------------|-----------|--------------------------------------|
| Tool Calling Supervisor | 90% 的常规场景 | Supervisor 通过工具调用分配任务，Worker 一次性返回结果 | 
| Handoff（交接） Worker      | 需要与用户多轮对话 | 如医疗问诊中专科 Agent 需向患者追问症状              

## 4. 多轮对话：状态管理与记忆

### 4.1 LangGraph 的状态管理机制

LangGraph 通过 集中式状态管理 在不同节点间传递和维护状态，实现长期记忆和多轮对话。

```python
from langgraph.checkpoint import MemorySaver

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 每次对话指定 thread_id 保持同一会话

config = {"configurable": {"thread_id": "user_session_123"}}
result = app.invoke({"messages": [HumanMessage(content="你好")]}, config)
```

### 4.2 短期记忆 vs 长期记忆

| 记忆类型 | 管理方式                      | 生命周期  |
|------|---------------------------|-------|
| 短期记忆 | 通过线程范围的检查点持久化（对话历史、上传文件等） | 单次会话  |
| 长期记忆 | 跨线程存储，通常结合向量数据库实现语义检索     | 跨会话持久 |

### 4.3 多轮对话流程示例

以 Supervisor 架构为例：

第1轮：用户问“今天北京天气怎么样？” → Supervisor 路由到 WeatherAgent → 返回天气信息

第2轮：用户追问“那适合出门跑步吗？” → 状态保留前一轮天气数据 → Supervisor 路由到 LifeAdvisorAgent → 给出建议

第3轮：用户再问“明天呢？” → 状态包含完整对话历史 → WeatherAgent 自动查询“明天”的天气

整个过程中，状态在节点间流转，每个 Agent 都能访问历史上下文。

## 5. 高级话题

### 5.1 分层 Supervisor（Hierarchical Supervisors）

Supervisor 可以嵌套管理其他 Supervisor，形成层级结构：

```text
顶层 Supervisor
├── 研究组 Supervisor
│ ├── ResearchAgent
│ └── AnalysisAgent
└── 内容组 Supervisor
├── WritingAgent
└── EditingAgent
```

### 5.2 上下文隔离

LangGraph 将复杂任务拆解成独立模块，每个子任务在专门的“房间”里处理，避免相互干扰。Anthropic 的研究表明，经过隔离上下文的
multi‑agent 表现优于单一智能体。

### 5.3 人机协作（Human‑in‑the‑Loop）

LangGraph 原生支持在关键节点暂停执行，等待人工输入或审批。

## 6. 完整实战示例：智能生活助手系统

### 6.1 系统架构

本示例构建一个“智能生活助手”多 Agent 系统，包含：

| Agent            | 职责       | 工具               |
|------------------|----------|------------------|
| DateAgent        | 获取当前日期   | get_current_date |
| WeatherAgent     | 查询指定城市天气 | get_weather      |
| LifeAdvisorAgent | 综合信息给出建议 | 无（纯推理）           |
| Supervisor       | 调度与协调    | 三个子 Agent（作为工具）  |

### 6.2 环境准备

```bash
pip install langgraph langgraph-supervisor langchain-openai
export OPENAI_API_KEY="your-api-key"
```

### 6.3 完整代码

```python

"""
智能生活助手 - 多Agent系统完整示例
架构：Supervisor调度三个专业子Agent
功能：多轮对话 + 工具调用 + 状态管理
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# ------------------------------------------------------------
# 第一步：初始化模型
# ------------------------------------------------------------
model = ChatOpenAI(model="gpt-4o", temperature=0)


# ------------------------------------------------------------
# 第二步：定义工具
# ------------------------------------------------------------
@tool
def get_current_date() -> str:
    """获取当前日期，返回格式 'YYYY-MM-DD'"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


@tool
def get_weather(city: str, date: str) -> str:
    """
    查询指定城市在指定日期的天气信息。
    Args:
        city: 城市名称，如 '北京'
        date: 日期，格式 'YYYY-MM-DD'
    Returns:
        天气描述字符串
    """
    # 模拟天气数据库（可替换为真实API）
    weather_db = {
        "北京": {"2026-06-17": "晴，25-32°C，南风3级，空气质量良好"},
        "上海": {"2026-06-17": "小雨，22-28°C，东风2级，注意带伞"},
        "广州": {"2026-06-17": "多云转阴，26-33°C，湿度65%"},
        "深圳": {"2026-06-17": "晴间多云，27-34°C，适合户外活动"},
    }
    default = f"{city}，晴，20-30°C，微风"
    result = weather_db.get(city, {}).get(date, default)
    return f"{city} {date} 天气：{result}"


# ------------------------------------------------------------
# 第三步：创建子Agent
# ------------------------------------------------------------
date_agent = create_react_agent(
    model=model,
    tools=[get_current_date],
    name="date_expert",
    prompt=(
        "你是一个日期专家。唯一职责是获取当前日期。\n"
        "当用户询问日期时，使用 get_current_date 工具。\n"
        "只返回日期信息，不要做其他事情。"
    )
)

weather_agent = create_react_agent(
    model=model,
    tools=[get_weather],
    name="weather_expert",
    prompt=(
        "你是一个天气专家。职责是查询指定城市的天气。\n"
        "当用户询问天气时，使用 get_weather 工具。\n"
        "需要知道城市和日期。若未提供日期，先向日期专家获取当前日期。\n"
        "只返回天气信息。"
    )
)

life_advisor_agent = create_react_agent(
    model=model,
    tools=[],
    name="life_advisor",
    prompt=(
        "你是一个生活顾问。根据天气信息给用户提供生活建议。\n"
        "例如：是否适合跑步、是否需要带伞、穿衣建议等。\n"
        "用亲切、专业的语气给出建议。"
    )
)

# ------------------------------------------------------------
# 第四步：创建Supervisor
# ------------------------------------------------------------
workflow = create_supervisor(
    agents=[date_agent, weather_agent, life_advisor_agent],
    model=model,
    prompt=(
        "你是一个生活助手的调度主管（Supervisor）。\n\n"
        "管理以下三个专家：\n"
        "1. date_expert：获取当前日期\n"
        "2. weather_expert：查询天气\n"
        "3. life_advisor：给出生活建议\n\n"
        "工作流程：\n"
        "- 若用户问日期 → 调用 date_expert\n"
        "- 若用户问天气 → 先调用 date_expert 获取日期，再调用 weather_expert\n"
        "- 若用户问生活建议 → 依次调用 date_expert → weather_expert → life_advisor\n"
        "- 若用户问综合问题 → 按需调用多个专家\n"
        "根据用户问题合理调度，确保信息完整后给出最终回答。"
    )
)

# ------------------------------------------------------------
# 第五步：启用记忆（支持多轮对话）
# ------------------------------------------------------------
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


# ------------------------------------------------------------
# 第六步：多轮对话交互函数
# ------------------------------------------------------------
def chat(user_input: str, thread_id: str = "default_session"):
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config
    )
    last_message = result["messages"][-1]
    print(f"🤖 助手: {last_message.content}\n")
    return result


# ------------------------------------------------------------
# 第七步：运行演示
# ------------------------------------------------------------
if __name__ == "__main__":
    session_id = "user_zhang_san"
    print("=" * 60)
    print(f"🏠 智能生活助手已启动（会话ID: {session_id}）")
    print("=" * 60)
    print()

    # 第1轮：查询天气
    print("【第1轮】")
    print("👤 用户: 今天北京天气怎么样？")
    chat("今天北京天气怎么样？", session_id)

    # 第2轮：基于前文追问
    print("【第2轮】")
    print("👤 用户: 那适合出门跑步吗？")
    chat("那适合出门跑步吗？", session_id)

    # 第3轮：切换话题
    print("【第3轮】")
    print("👤 用户: 那上海呢？")
    chat("那上海呢？", session_id)

    # 第4轮：综合建议
    print("【第4轮】")
    print("👤 用户: 结合北京和上海的天气，给我一些出行建议")
    chat("结合北京和上海的天气，给我一些出行建议", session_id)

    print("=" * 60)
    print("✅ 演示结束")
```

## 7. 最佳实践与扩展建议

1. 从简单的 Tool Calling Supervisor 开始：90% 的场景用这种方式即可。
2. 每个 Agent 只负责一个角色：Prompt 保持简单清晰，便于调试。
3. 使用 LangSmith 监控调试：实时追踪 Agent 内部执行情况。
4. Handoff 模式用于多轮交互场景：如客服、医疗问诊等。
5. 利用检查点实现断点续跑：支持长时间运行的任务恢复。
6. 扩展方向：
    - 分层 Supervisor：嵌套管理子 Supervisor。
    - 接入真实 API：替换模拟天气为 OpenWeatherMap 等。
    - 人机协作：在关键节点暂停等待人工输入。

## 8. 总结

| 维度   | 单 Agent          | 多 Agent（Supervisor 模式）        |
|------|------------------|-------------------------------|
| 架构   | 一个 Agent 处理所有任务  | Supervisor 调度 + 专家 Agent 各司其职 |
| 工具管理 | 所有工具在一个列表中       | 每个 Agent 只拥有相关工具              |
| 上下文  | 单一窗口承载所有信息       | 每个 Agent 独立上下文，隔离管理           |
| 多轮对话 | 依赖外部记忆机制         | LangGraph 原生状态管理              |
| 扩展性  | 新增功能需修改核心 Prompt | 新增 Agent 即可，模块化扩展             |

总结：多 Agent 系统通过 Supervisor 架构实现任务的专业化分工与集中调度，结合 LangGraph
的状态管理机制实现多轮对话上下文保持，通过工具调用完成具体任务执行——三者共同构成生产级 AI 应用的核心能力。

