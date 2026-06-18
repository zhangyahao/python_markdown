# Loop Engineering（循环工程）完全指南 —— 从概念到实践

## 目录

- [一、什么是 Loop Engineering？](#一什么是-loop-engineering)
- [二、起源与推动者](#二起源与推动者)
- [三、范式演进：为什么会诞生 Loop Engineering？](#三范式演进为什么会诞生-loop-engineering)
- [四、Loop Engineering vs Prompt Engineering](#四loop-engineering-vs-prompt-engineering)
- [五、核心架构：一个 Loop 由什么构成？](#五核心架构一个-loop-由什么构成)
- [六、Loop 的工作流程](#六loop-的工作流程)
- [七、相关 API 与生态工具](#七相关-api-与生态工具)
- [八、完整代码示例](#八完整代码示例)
    - [示例一：LangChain `create_agent` —— 零代码实现内置 Loop](#示例一langchain-createagent--零代码实现内置-loop)
    - [示例二：LangGraph —— 自定义条件循环与状态控制](#示例二langgraph--自定义条件循环与状态控制)
    - [示例三：@loop-engine/sdk —— 企业级专业 Loop 框架](#示例三loop-enginesdk--企业级专业-loop-框架)
- [九、挑战与最佳实践](#九挑战与最佳实践)
- [十、总结](#十总结)

## 一、什么是 Loop Engineering？

**Loop Engineering（循环工程）** 是 2026 年 6 月由 OpenClaw 创始人 Peter Steinberger 正式提出的一种 AI Agent 工程新范式。

**一句话定义**：用你设计的系统来替代你自己去给 AI Agent 写提示词（Prompt）。

传统做法是人写提示词 → Agent 执行一次 → 人看结果再写下一条指令。Loop Engineering 彻底打破了“人在中间传话”的模式：你只需定义一个目标，系统便会自动完成
**“执行 → 观察 → 评估 → 修正 → 再执行”** 的闭合回路，Agent 在循环中持续迭代，直到达成预设目标。

Google Cloud AI 总监 Addy Osmani 将其精准概括为：**“把负责下指令的人，从自己换成一套你设计好的系统。”**

## 二、起源与推动者

| 人物                    | 身份                 | 核心观点                                                    |
|-----------------------|--------------------|---------------------------------------------------------|
| **Peter Steinberger** | OpenClaw 创始人       | “你不该再亲自给编程 Agent 写提示词了，你应该设计 Loop，让 Loop 替你去写。”         |
| **Boris Cherny**      | Claude Code 创建者    | “我已经不给 Claude 写提示词了，我有 Loop 在跑，它们自己决定该干什么。我的工作是写 Loop。” |
| **Addy Osmani**       | Google Cloud AI 总监 | 撰写长文系统性阐述 Loop Engineering 的架构与五大核心模块。                  |
| **Andrej Karpathy**   | 知名 AI 研究者          | AutoResearch 等项目体现同类思想：让自己不再成为瓶颈，使系统完全自主运行。             |

## 三、范式演进：为什么会诞生 Loop Engineering？

Loop Engineering 是 AI 工程范式自然演进的结果：

| 阶段   | 工程范式                           | 核心关注点                    |
|------|--------------------------------|--------------------------|
| 第一阶段 | **Prompt Engineering（提示词工程）**  | 怎么问，AI 才更容易答对？           |
| 第二阶段 | **Context Engineering（上下文工程）** | 给 AI 看什么，它才更容易做对？        |
| 第三阶段 | **Harness Engineering（安全工程）**  | 在什么环境里让 AI 安全运行？         |
| 第四阶段 | **Loop Engineering（循环工程）**     | 怎么让 AI Agent 持续、自主地完成任务？ |

四者并非替代关系，而是**层层递进的叠加关系**：Prompt 解决“怎么问”，Context 解决“让它看见什么”，Harness 解决“放在什么环境”，Loop
解决“系统自己怎么转起来”。

## 四、Loop Engineering vs Prompt Engineering

| 维度           | Prompt Engineering                    | Loop Engineering     |
|--------------|---------------------------------------|----------------------|
| **交互方式**     | 人写提示词 → Agent 执行一次 → 人看结果 → 人再写下一个提示词 | 人定义目标 → 系统自动循环执行直到完成 |
| **人的角色**     | **逐句指挥者**                             | **系统设计者 / 架构师**      |
| **Agent 行为** | 单次响应，被动执行                             | 自主迭代、自我修正的闭环         |
| **核心产出**     | 写好一个 Prompt                           | 设计一套能持续运行的循环系统       |
| **适用场景**     | 相对明确、边界清晰的任务                          | 需要持续推进的复杂长期任务        |

## 五、核心架构：一个 Loop 由什么构成？

一个完整的 Loop 系统由 **五大核心模块 + 一个记忆层** 构成：

### 5.1 五大核心模块

| 模块                               | 功能                  | 说明                                    |
|----------------------------------|---------------------|---------------------------------------|
| **Automations（自动化触发）**           | 按计划自动触发，独立完成发现和分类   | 定时任务（Cron）、事件驱动（Webhook）              |
| **Worktrees（工作树）**               | 让并行运行的多个 Agent 互不干扰 | 每个 Agent 拥有独立、隔离的工作空间（如 Git Worktree） |
| **Skills（技能）**                   | 沉淀项目知识，Agent 不再靠“猜” | 代码规范、架构要求、领域背景经验                      |
| **Plugins & Connectors（插件与连接器）** | 将 Agent 接入已有工具链     | GitHub、数据库、Slack、Jira 等               |
| **Sub-Agents（子 Agent）**          | 多 Agent 分工协作        | 一个负责构思，另一个负责审查，第三个负责测试                |

### 5.2 记忆层（Memory）

一个 Markdown 文件、Linear 看板，或任何存在于单次对话之外、记录“已完成”和“下一步”的存储系统。

**为什么重要？** 模型在每次运行之间会遗忘一切，因此记忆必须存储在**磁盘**上，而非仅存在于上下文窗口中。这是所有长期运行
Agent 的共同秘诀。

### 5.3 五大核心要素（另一视角）

除了模块化拆解，一个合格的 Loop 还必须包含五个要素：

1. **明确的目标（Goal）**：不是模糊的“帮我优化代码”，而是可验证的结果定义（如“测试通过率从 72% 提升到 95%”）。
2. **上下文管理（Context Management）**：随迭代动态更新，决定保留什么、压缩什么、遗忘什么。
3. **可调用的工具（Tool Access）**：运行测试、读写文件、搜索代码库、调用 API。
4. **对产出的评估（Output Evaluation）**：Loop 与普通循环脚本的本质区别——能判断输出是否达标。
5. **停止标准（Termination Condition）**：目标达成时停止，或达到最大迭代次数时优雅退出。

## 六、Loop 的工作流程

### 6.1 单次迭代流程

```text
         ┌─────────────────────────────────────┐
         │           定义目标 (Goal)            │
         └─────────────────┬───────────────────┘
                           ▼
         ┌─────────────────────────────────────┐
         │      Agent 制定执行计划 (Plan)       │
         └─────────────────┬───────────────────┘
                           ▼
         ┌─────────────────────────────────────┐
         │  调用工具执行（写代码/运行测试/搜索） │
         └─────────────────┬───────────────────┘
                           ▼
         ┌─────────────────────────────────────┐
         │       观察执行结果 (Observe)         │
         └─────────────────┬───────────────────┘
                           ▼
         ┌─────────────────────────────────────┐
         │      评估：是否达到目标？            │
         └─────────────────┬───────────────────┘
              是 ▼              ▼ 否
         ┌───────────┐  ┌──────────────────────┐
         │ 输出结果  │  │ 分析差距，修正计划   │
         │ 退出循环  │  │ 返回“执行”步骤      │
         └───────────┘  └──────────────────────┘
```

### 6.2 Agentic Loop 的核心要素

一个 agentic loop 只需要两样东西：

- **触发器（Trigger）**：启动循环的事件（PR 开启、定时计划、人工指令）。
- **可验证的目标（Verifiable Goal）**：Agent 自己能判断是否达成的结束状态。

Agent **不等待**你的下一条消息。它启动、运行、检查目标是否达成，如果没有，就再次循环，直到达成或触发停止条件。

### 6.3 Loop vs 普通自动化

|        | 普通自动化（Script）    | Loop（智能循环）        |
|:-------|:-----------------|:------------------|
| **行为** | 执行一系列预设步骤，运行一个脚本 | 内部包含**决策机制**      |
| **判断** | 不决定任何事情，线性执行     | 主动判断是否达到目标，动态调整策略 |
| **本质** | 遵循配方（Recipe）     | 评估、循环、根据发现调整      |

## 七、相关 API 与生态工具

实现 Loop Engineering 的 API 生态正逐渐成型，主要分为三大类：

### 7.1 LangChain 生态（通用 Agent Loop）

| API / 组件                         | 功能描述                                                      |
|:---------------------------------|:----------------------------------------------------------|
| **`create_agent`**               | LangChain 最核心的 API，用于快速创建一个标准的 Agent Loop，内置“思考-行动-观察”循环。 |
| **Middleware（中间件）**              | 在 Agent Loop 执行过程中插入日志记录、重试、降级、PII 检测等自定义逻辑。              |
| **LangGraph `StateGraph`**       | 底层编排框架，允许定义包含**循环（Loops）**、分支和并行任务的自定义工作流。                |
| **LangGraph `interrupt`**        | 在节点中暂停图执行，实现“人机协同”（Human-in-the-Loop）。                    |
| **`MemorySaver` / Checkpointer** | 持久化状态，支持多轮对话记忆和断点续跑。                                      |

### 7.2 Loop Engine SDK（专为循环工程而生）

| API / 组件               | 功能描述                                           |
|:-----------------------|:-----------------------------------------------|
| **`createLoopSystem`** | 创建 Loop 系统的主工厂方法。                              |
| **`parseLoopYaml`**    | 解析 YAML 文件，以声明式方式定义 Loop 的状态、转换和规则。            |
| **`createAIActor`**    | 创建支持 Anthropic Claude、OpenAI GPT 等模型的 AI 执行单元。 |
| **Guards（守卫）**         | 在每次迭代前自动检查状态（如预算、质量阈值），不满足则暂停或重试。              |
| **Signals（信号）**        | 跨组件通信机制。                                       |
| **Adapters（适配器）**      | 预置 OpenAI、Anthropic、Grok、商业网关等适配器。             |

### 7.3 其他新兴框架

| 框架                           | 特点                                   |
|:-----------------------------|:-------------------------------------|
| **LangChain4j `@LoopAgent`** | Java 开发者可通过注解声明式定义多 Agent 循环协作。      |
| **OpenAI Agents SDK**        | OpenAI 官方开源 SDK，支持循环和任务交接能力。         |
| **Claude Agent SDK**         | Anthropic 推出的 Python/TypeScript SDK。 |
| **`aloop` (Python库)**        | 将规划、并行子 Agent、自我验证融入同一个 Agent 循环。    |

## 八、完整代码示例

### 示例一：LangChain `create_agent` —— 零代码实现内置 Loop

LangChain 的 `create_agent` 内置了完整的 ReAct 循环（推理 → 行动 → 观察），无需手动编写循环逻辑。

python

```
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint import MemorySaver

# 1. 定义工具
@tool
def search(query: str) -> str:
    """搜索网络信息"""
    return f"关于 '{query}' 的搜索结果：找到了3篇相关文章..."

@tool
def calculate(expression: str) -> float:
    """执行数学计算"""
    return eval(expression)

# 2. 初始化模型
model = ChatOpenAI(model="gpt-4o", temperature=0)

# 3. 创建 Agent（内置 Loop）
agent = create_agent(
    model=model,
    tools=[search, calculate],
    system_prompt="你是一个研究助手。遇到复杂任务时，请拆解成多个步骤逐步完成。"
)

# 4. 启用记忆（支持多轮对话与状态保持）
memory = MemorySaver()
agent_with_memory = agent.with_checkpointer(memory)

# 5. 运行 Agent（自动循环直到任务完成）
result = agent_with_memory.invoke(
    {"messages": [{"role": "user", "content": "帮我查一下2026年AI Agent相关的研究，然后总结一下"}]},
    config={"configurable": {"thread_id": "session_001"}}
)

print(result["messages"][-1].content)
```

**说明**：`create_agent` 内部自动运行 while 循环：调用模型 → 判断是否需要工具 → 执行工具 → 重复，直到模型不再请求工具调用。开发者无需编写任何循环代码。

### 示例二：LangGraph —— 自定义条件循环与状态控制

当需要精细控制循环逻辑（如自定义停止条件、最大迭代次数）时，使用 LangGraph 构建图结构循环。

python

```
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from typing import TypedDict, List, Literal

# 1. 定义状态（在节点间传递的“黑板”）
class AgentState(TypedDict):
    messages: List[dict]
    iteration_count: int
    is_complete: bool
    research_findings: str

# 2. 定义工具
@tool
def web_search(query: str) -> str:
    return f"搜索结果：{query} 的相关信息..."

@tool
def summarize(text: str) -> str:
    return f"总结：{text[:50]}..."

# 3. 初始化模型并绑定工具
model = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [web_search, summarize]
model_with_tools = model.bind_tools(tools)

# 4. 定义节点函数
def agent_node(state: AgentState):
    """Agent 推理节点：决定下一步行动"""
    response = model_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

def tool_node(state: AgentState):
    """工具执行节点"""
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "web_search":
            result = web_search.invoke(tool_call["args"])
        elif tool_call["name"] == "summarize":
            result = summarize.invoke(tool_call["args"])
        results.append({"role": "tool", "content": result})
    return {
        "messages": state["messages"] + results,
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """条件判断：是否继续循环"""
    last_message = state["messages"][-1]
    # 停止条件1：没有工具调用 → 结束
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "end"
    # 停止条件2：超过最大迭代次数（安全阀）→ 结束
    if state.get("iteration_count", 0) >= 5:
        return "end"
    return "tools"

# 5. 构建图（定义循环）
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")

# 添加条件边 → 形成循环！
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",   # 有工具调用 → 执行工具
        "end": END          # 无工具调用或超限 → 结束
    }
)
graph.add_edge("tools", "agent")  # 工具执行完 → 回到 agent（循环！）

# 6. 编译并运行
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

result = app.invoke(
    {"messages": [{"role": "user", "content": "研究一下2026年的AI趋势并总结"}]},
    config={"configurable": {"thread_id": "session_002"}}
)

print(result["messages"][-1].content)
```

**关键点**：`tools → agent` 的边构成了循环；`should_continue` 函数控制退出时机；`MemorySaver` 赋予跨轮次记忆能力。

### 示例三：`@loop-engine/sdk` —— 企业级专业 Loop 框架

`@loop-engine/sdk` 是专为 Loop Engineering 设计的 TypeScript 框架，提供 Guards（守卫）、Signals（信号）、持久化存储等生产级组件。

typescript

```
import { createLoopSystem, GuardRegistry } from "@loop-engine/sdk";
import { createOpenAIActorAdapter } from "@loop-engine/adapter-openai";
import { createPostgresStore } from "@loop-engine/adapter-postgres";

// 1. 定义 Loop 的目标和停止条件
const loopDefinition = {
  id: "research-loop",
  goal: "完成对 AI Agent 市场的研究报告",
  
  // 停止条件：可验证的目标
  termination: {
    type: "verifiable",
    condition: (state) => 
      state.reportGenerated && 
      state.sections.every((s: any) => s.wordCount > 200)
  },
  
  // 最大迭代次数（安全阀）
  maxIterations: 10
};

// 2. 创建 AI Actor（带 OpenAI 适配器）
const openaiAdapter = createOpenAIActorAdapter({
  apiKey: process.env.OPENAI_API_KEY!,
  model: "gpt-4o"
});

// 3. 配置 Guards（守卫：在每次迭代前检查）
const guards = new GuardRegistry();
guards.register("budgetGuard", {
  check: (state) => state.totalTokensSpent < 1000000,
  onFail: (state) => ({ action: "pause", message: "预算超限，暂停执行" })
});

guards.register("qualityGuard", {
  check: (state) => state.lastOutputQuality > 0.7,
  onFail: (state) => ({ 
    action: "retry", 
    message: "质量不达标，重新生成",
    retryCount: state.retryCount || 0
  })
});

// 4. 创建 Loop 系统
const system = createLoopSystem({
  definition: loopDefinition,
  adapter: openaiAdapter,
  guards: guards,
  // 使用 Postgres 持久化状态（支持断点续跑）
  store: createPostgresStore({ connectionString: process.env.DATABASE_URL! })
});

// 5. 启动 Loop（自动循环直到目标达成）
const result = await system.run({
  initialContext: {
    topic: "AI Agent 市场分析",
    requiredSections: ["市场规模", "主要玩家", "技术趋势", "未来展望"]
  }
});

console.log(`✅ Loop 完成！迭代次数：${result.iterations}`);
console.log(`📊 最终报告：${result.output}`);
```

**说明**：Guards 在每次迭代前自动检查预算与质量；Adapter 封装模型调用；Store 持久化状态支持断点续跑。

### 8.4 三种方案对比

| 方案                     | 适用场景          | 循环控制             | 记忆管理         | 生产级特性 |
|:-----------------------|:--------------|:-----------------|:-------------|:------|
| **`create_agent`**     | 快速原型、标准 Agent | 框架内置，黑盒          | MemorySaver  | 基础    |
| **LangGraph**          | 需要自定义循环逻辑     | 图结构，完全可控         | Checkpointer | 中等    |
| **`@loop-engine/sdk`** | 企业级 Loop 工程   | Guards + Signals | Postgres 等   | 完善    |

## 九、挑战与最佳实践

### 9.1 三大核心挑战

| 挑战             | 说明                                 |
|:---------------|:-----------------------------------|
| **Token 成本**   | 长时间循环可能产生巨额 Token 消耗（如每日数千万 Token） |
| **质量下滑（Slop）** | 代码质量可能随着迭代次数增加而逐渐下降                |
| **无限循环风险**     | 没有良好的停止标准，Loop 可能永远跑下去             |

### 9.2 最佳实践建议

1. **从简单开始**：先用基础的 Tool Calling Supervisor 模式验证可行性，不要一开始就构建复杂系统。
2. **设置明确的停止条件**：目标达成时停止，或设置最大迭代次数（如 10 轮）。
3. **加入“说不”的机制**：在 Loop 里放入测试、类型检查或真实错误反馈，让 Agent 能判断当前方案是否可行。
4. **使用检查点持久化**：支持断点恢复（如 Postgres、Redis），防止因中断导致进度全部丢失。
5. **成本预算控制**：设置每日限额（如 $10/天）和单任务限额（如 $1/任务）。
6. **避免做成“富士康工厂”**：YC CEO Garry Tan 提醒，Agent 通常是具有思考能力的智能体，不要让它们只是重复执行同一个动作而失去灵活性。

## 十、总结

| 维度       | 核心要点                                                             |
|:---------|:-----------------------------------------------------------------|
| **本质**   | 用你设计的系统替代你自己去给 Agent 写提示词                                        |
| **核心机制** | 目标驱动 + 闭环迭代 + 自主决策 + 可验证停止                                       |
| **人的角色** | 从“逐句指挥者”变为“系统设计者 / 架构师”                                          |
| **关键模块** | Automations + Worktrees + Skills + Plugins + Sub-Agents + Memory |
| **主流框架** | LangChain（通用）、@loop-engine/sdk（专业）、LangGraph（自定义）                |
| **核心挑战** | Token 成本、质量下滑、无限循环                                               |

**最后一句话总结**：Loop Engineering 代表了一种从“操控者”到“系统架构师”的范式转移。你不再亲自给 AI
下达每一条指令，而是设计一套能自动运转的循环系统，让它自己去发现任务、分配任务、检查结果、记录状态、决定下一步，直到达成你预设的目标。这是迈向真正自主
AI Agent 的关键一步。