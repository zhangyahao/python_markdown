## 常见问题与解决方案

### 1 话题漂移

**问题**：Agent 在长对话中偏离主题，或用户突然切换话题导致上下文污染。

**解决方案**：

| 策略        | 实现方式                                | 代码示例                                         |
|:----------|:------------------------------------|:---------------------------------------------|
| **结构化记忆** | 提取关键事实存入 State，而非依赖原始对话历史           | `state["facts"] = extract_facts(messages)`   |
| **话题检测**  | 用 Embedding 计算当前问题与历史话题的语义相似度       | `cosine_sim < threshold → 触发询问`              |
| **主动确认**  | 检测到漂移时询问用户，确认后挂起旧任务                 | 见下方代码                                        |
| **任务挂起**  | 将旧 State 序列化存入外部存储（ChromaDB/SQLite） | `task_store.save(thread_id, state_snapshot)` |
| **任务恢复**  | 用户通过编号或关键词选择恢复哪个任务                  | `restore_task(task_id)`                      |

**代码实现（漂移检测与挂起）**：

```python
class AntiDriftAgent:
    def __init__(self):
        self.memory = ConversationBufferMemory()
        self.task_store = TaskStore()  # ChromaDB/SQLite
        self.pending_switch = False
        self.drift_threshold = 0.25

    def ask(self, user_input: str) -> str:
        # 等待用户确认切换
        if self.pending_switch:
            if self._is_affirmative(user_input):
                self._save_current_task()  # 挂起旧任务
                self.memory.clear()
                self.pending_switch = False
            else:
                self.pending_switch = False
                return "好的，我们继续之前的话题。"

        # 检测语义漂移
        is_drift, sim = self._check_drift(user_input)
        if is_drift:
            self.pending_switch = True
            return f"⚠️ 检测到话题变化（相似度 {sim:.2f}），是否切换到新话题？"

        # 正常处理
        return self._normal_response(user_input)

    def _save_current_task(self):
        task_data = {
            "thread_id": self.thread_id,
            "messages": self.memory.chat_memory.messages,
            "facts": self.facts,
            "topic_summary": self.topic_summary,
            "timestamp": datetime.now().isoformat()
        }
        self.task_store.save(task_data)
```

**多任务管理**：

```python
def list_suspended_tasks(user_id: str) -> str:
    tasks = task_store.get_all_suspended(user_id)
    if not tasks:
        return "没有挂起的任务。"
    result = f"📋 您有 {len(tasks)} 个挂起的任务：\n"
    for i, task in enumerate(tasks, 1):
        result += f"{i}. {task['topic_summary'][:50]}... (挂起于 {task['timestamp']})\n"
    result += "\n请回复 `恢复任务 [编号]` 或 `恢复任务 [关键词]` 来继续。"
    return result
```

### 2 多智能体死循环与推诿

**问题**：多个 Agent 互相推诿任务，或在两个 Agent 间无限循环。

**解决方案**：

| 策略        | 实现方式              | 说明                                |
|:----------|:------------------|:----------------------------------|
| **硬性限制**  | `recursion_limit` | 设置最大步数，超时抛出 `GraphRecursionError` |
| **语义检测**  | `LoopDetector`    | 检测重复内容，主动中断                       |
| **监督者模式** | 中央调度器路由           | 切断平级推诿链，Worker 只与 Supervisor 通信   |
| **双层路由**  | LLM 决策 + 策略校验     | 二次确认路由合理性                         |

**代码实现**：

```python
# 监督者模式（防推诿）
workflow = create_supervisor(
    agents=[research_agent, math_agent],
    llm=model,
    prompt="你是主管...根据问题路由",
    recursion_limit=10  # 🔑 防死循环硬限制
)


# 语义循环检测
class LoopDetector:
    def __init__(self, threshold=0.85, window=3):
        self.threshold = threshold
        self.window = window
        self.history = []

    def check(self, new_msg: str) -> bool:
        for old in self.history[-self.window:]:
            if self._similarity(old, new_msg) > self.threshold:
                return True
        self.history.append(new_msg)
        return False
```

### 3 工具调用参数遗忘

**问题**：Agent 在第一步获取了 `device_id`，但后续工具调用时忘记了，需要反复询问用户。

**解决方案**：

| 策略             | 实现方式             | 说明             |
|:---------------|:-----------------|:---------------|
| **State 显式存储** | 将关键参数存入 State 字段 | 跨节点共享，不依赖对话历史  |
| **参数校验器**      | 工具执行前检查必需参数      | 缺参数时返回错误，让模型补充 |
| **自包含工具**      | 工具签名包含所有必需参数     | 模型调用时必须显式提供    |
| **自动填充**       | 从历史消息中正则提取参数     | 作为 fallback 手段 |

**代码实现**：

```python
class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    device_id: Optional[str]  # 🔑 共享参数槽
    last_result: Optional[str]


def tool_query_state(state: AgentState):
    # ✅ 直接从 State 读取，无需从消息解析
    device_id = state.get("device_id")
    if not device_id:
        return {"messages": [ToolMessage("错误：未提供设备ID，请先查询设备状态。")]}
    result = call_api(device_id)
    return {"messages": [ToolMessage(str(result))], "last_result": result}


def call_model(state: AgentState):
    # 强制校验：缺参数时引导模型补齐
    if not state.get("device_id") and "设备" in state["messages"][-1].content:
        state["messages"].insert(0, SystemMessage(
            "⚠️ 用户未提供设备ID，你必须先询问用户需要查询哪台设备。"
        ))
    return {"messages": [llm.invoke(state["messages"])]}
```

### 4 权限越界

**问题**：Agent 在某一轮获得权限后，在后续对话中滥用权限执行越权操作。

**解决方案**：

| 策略           | 实现方式               | 说明            |
|:-------------|:-------------------|:--------------|
| **用户隔离**     | 每个用户独立 `thread_id` | 防止跨用户数据泄露     |
| **工具调用权限校验** | 执行前检查用户权限          | 每次调用都校验，不信任缓存 |
| **最小权限原则**   | 只暴露必需工具            | 避免“瑞士军刀”式工具   |
| **记忆隔离**     | 记忆分用户、分会话存储        | 防止记忆污染        |

**代码实现**：

```python
# 用户隔离
config = {"configurable": {"thread_id": f"user_{user_id}_session_{session_id}"}}


# 工具权限校验
@tool
def read_sensitive_data(file_path: str, user_id: str) -> str:
    if not check_permission(user_id, "read_sensitive_data"):
        return "错误：您没有权限读取此文件。"
    return read_file(file_path)

# 最小权限原则：拆解工具
# ❌ 避免：execute_shell(command)  # 万能工具
# ✅ 推荐：restart_service(service_name), read_log_file(file_path)
```

### 5 Token 爆炸（State 过大）

**问题**：工具参数、对话历史全部存入 State 并注入 Prompt，导致 Token 爆炸。

**解决方案**：

| 层级          | 存储内容             | 是否注入 Prompt | 实现方式                    |
|:------------|:-----------------|:------------|:------------------------|
| **L1（热数据）** | 当前轮次关键参数、结果摘要    | ✅ 是         | State 字段（如 `device_id`） |
| **L2（温数据）** | 对话历史（`messages`） | ✅ 是（可控）     | `trim_messages` 或摘要     |
| **L3（冷数据）** | 完整工具返回、历史日志      | ❌ 否         | ChromaDB/Redis/文件       |

**代码实现**：

```python
# 分层存储
class AgentState(TypedDict):
    device_id: str  # L1: 热参数
    last_summary: str  # L1: 结果摘要（仅50字）
    messages: List  # L2: 对话历史（裁剪）
    full_result_id: str  # L3: 指向外部存储


def tool_query_manual(state):
    full_manual = fetch_long_manual(state["device_id"])  # 5000字
    doc_id = str(uuid.uuid4())
    chroma_db.add(doc_id, full_manual)  # L3: 存外部
    summary = full_manual[:50] + "..."  # L1: 仅摘要
    return {"messages": [ToolMessage(summary)], "last_summary": summary, "full_result_id": doc_id}


# 消息修剪
def call_model(state):
    trimmed = trim_messages(
        state["messages"],
        max_tokens=4000,
        strategy="last",
        token_counter=len
    )
    return {"messages": [llm.invoke(trimmed)]}
```

### 6 推理延迟

**问题**：多步推理 + 工具调用导致用户等待时间过长（数秒至数十秒）。

**优化策略**：

| 优化手段                 | 效果             | 实现方式                          |
|:---------------------|:---------------|:------------------------------|
| **工具批量化**            | 3次 LLM 决策 → 1次 | 一个工具内部完成多个步骤                  |
| **延迟 Checkpoint**    | 每步写入 → 结束时写入   | `checkpoint=False` 或自定义 Saver |
| **Plan-and-Execute** | 5轮 LLM → 2轮    | 先生成计划，再批量执行                   |
| **工具级缓存**            | 减少外部调用         | `@lru_cache` 缓存结果             |
| **流式输出**             | 首字延迟降低         | `stream_mode="messages"`      |
| **投机解码**             | 小模型生成，大模型验证    | 需框架支持                         |

**代码实现**：

```python
#  工具批量化
@tool
def batch_calculate(operations: List[dict]) -> float:
    """批量执行多个数学运算，减少 LLM 决策次数"""
    result = 0
    for op in operations:
        if op["op"] == "add":
            result = op["a"] + op["b"]
        elif op["op"] == "multiply":
            result = op["a"] * op["b"]
    return result


#  延迟 Checkpoint
builder.add_node("math_chain", math_node, checkpoint=False)  # 不保存中间步骤
builder.add_node("final", final_node, checkpoint=True)  # 仅保存最终状态


# 3. Command 同轮多步（LangGraph 原生）
def math_chain_node(state):
    a = add(state["x"], state["y"])
    b = multiply(a, state["z"])
    return {"result": b, Command(goto="final_answer")}  # 一步到位


# 4. 工具级缓存
@lru_cache(maxsize=128)
def get_device_param(device_id: str, param: str) -> float:
    return query_db(device_id, param)
```

### 7. 工具多轮调用优化

#### 7.1 核心瓶颈分析

在多步工具调用场景中，延迟主要消耗在三个环节：

| 瓶颈环节                  | 具体表现                                 | 典型耗时占比    |
|:----------------------|:-------------------------------------|:----------|
| **状态持久化（Checkpoint）** | 每调用一个工具，LangGraph 就把整个 State 写入数据库一次 | 约 **40%** |
| **模型反复推理（LLM Calls）** | Agent 每走一步都要向 LLM 请求一次“下一步做什么”       | 约 **50%** |
| **工具本身执行**            | 实际的计算、IO 操作                          | 约 **10%** |

**优化核心**：**减少 LLM 往返次数** + **降低 Checkpoint 频率**。

#### 7.2 优化策略一览

| 优化技术                 | 原理              | 难度 | 收益    | 代码侵入           |
|:---------------------|:----------------|:---|:------|:---------------|
| **工具批量化**            | 一个工具内部完成多个步骤    | 低  | ⭐⭐⭐⭐⭐ | 仅改工具定义         |
| **工具链聚合**            | 将顺序执行的工具固定为一条链路 | 低  | ⭐⭐⭐⭐  | 新增节点           |
| **Command 跳转**       | 同超级步内连续执行多个节点   | 中  | ⭐⭐⭐⭐  | 改节点逻辑          |
| **Plan-and-Execute** | 先生成计划，再批量执行     | 中  | ⭐⭐⭐⭐⭐ | 新增规划节点         |
| **并行执行**             | 独立子任务并发执行       | 中  | ⭐⭐⭐⭐  | 改路由逻辑          |
| **工具级缓存**            | 缓存高频查询结果        | 低  | ⭐⭐⭐   | 加 `@lru_cache` |
| **延迟 Checkpoint**    | 仅关键节点才写入数据库     | 低  | ⭐⭐⭐⭐  | 改图配置           |

#### 7.3 总结

它们的核心思想确实完全相同：用预定义的确定性逻辑，取代 LLM 动态决策的循环。
也就是说，不依赖模型“想一想下一步该调用什么”，而是由代码强制规定“第一步做什么，第二步做什么”。
不过，虽然理论一样，但它们作用于系统的不同层级，这直接决定了对 Prompt 的可见性和代码的可维护性。这就像“把衣服叠好”和“把衣服放进衣柜”本质都是整理衣服，但操作对象和目的不同。
以下为他们的区别：

| 优化方式           | 操作层级              | 对 LLM（Prompt）的可见性                        | 代码侵入度      | 适用场景                            |
|:---------------|:------------------|:-----------------------------------------|:-----------|:--------------------------------|
| **工具批量化**      | **工具（Tool）内部**    | **不可见**（LLM 以为只调用了 1 个工具）                | 低（仅修改工具定义） | **计算密集型**、无外部依赖的纯逻辑（如数学运算、数据清洗） |
| **工具链聚合**      | **节点（Node）内部**    | **可见**（LLM 看到的是聚合后的整体结果）                 | 中（新增或合并节点） | **业务规则固定**的流程（如查状态→查手册→生成报告）    |
| **Command 跳转** | **图（Graph）的执行引擎** | **不可见**（LLM 仍然感知到多个节点，只是跳过保存 Checkpoint） | 中（改节点返回逻辑） | **保持模块化**、想解耦代码但又想提速的场景         |

虽然他们都是硬编码，但*硬编码的位置*决定了以下三个关键因素的差异：
1. 对 LLM 的“欺骗”程度不同（影响 Prompt 结构）
     - **工具批量化**：你把“加、乘、除”塞进一个工具。LLM 在生成 `tool_call` 时，只会生成一次调用。**LLM 的推理负担最轻**，因为它根本不需要决策顺序。
     - **工具链聚合**：你把整个链路的执行逻辑（包含工具调用）封装在节点函数里。LLM 依然只知道这一个节点，但它能感知到返回的结果。
     - **Command 跳转**：LLM 在 `tool_calls` 中看到的依然是多个独立的工具，只是框架层面省去了不必要的存储操作。
2. 错误恢复能力（可观测性）不同
     - **工具批量化**：如果内部第二步出错了，**日志里只会显示这个工具整体报错**，很难定位是内部哪个环节出问题。
     - **Command 跳转**：因为节点依然是独立的，LangSmith 等追踪工具依然会显示 `step1`、`step2` 的分别执行情况，**调试体验最好**。
3. 复用性与维护成本 
     - **工具批量化**：聚合后的工具很难在其他场景下复用（比如我只想单独用其中的“加”法）。
     - **工具链聚合/Command**：节点和工具依然是解耦的，你可以在其他链路中单独调用 `add` 工具。