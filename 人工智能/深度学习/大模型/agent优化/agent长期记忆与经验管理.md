# Agent 长期记忆与经验管理系统：完整技术方案

## 一、为什么需要积累成功与失败经验？

### 1.1 Agent 的“金鱼记忆”问题

在当前的 Agent 架构中，虽然通过 `Checkpointer` 实现了对话状态的持久化（短期记忆），但这种记忆是**会话级别**的：

- 当用户开启一个新的 `thread_id` 时，Agent 会“忘记”之前所有会话中学到的东西。
- 当同一个用户再次问“CNC-01 报警阈值是多少？”时，Agent 依然可能调用错误的工具或给出错误的参数，**重复消耗 Token 和算力**。

### 1.2 传统“重试”与“经验反思”的本质区别

| 传统方案（重试）                           | 经验反思方案（学习）                             |
|:-----------------------------------|:---------------------------------------|
| **被动防御**：错了就重试，直到成功或耗尽次数。          | **主动避坑**：错了就总结教训，下次直接绕开错误路径。           |
| **无状态**：每次重试都是“第一次”，不知道上次为什么错。     | **有记忆**：知道“上次查 CNC-99 不存在，是因为用户写错了编号”。 |
| **成本线性增长**：同类错误消耗 Token 次数 = 错误次数。 | **成本递减**：同类错误只消耗 1 次 Token，后续靠检索经验即可。  |

**核心结论**：Agent 应该像人类一样，“失败”不是终点，而是“学习”的起点。建立长期记忆的核心价值是**将“踩坑”转化为“经验”**
，实现真正的智能化进化。

## 二、经验的生命周期管理（从生到死）

| 阶段       | 核心动作                            | 关键问题              |
|:---------|:--------------------------------|:------------------|
| **① 采集** | 在线记录原始轨迹（问题、工具链、结果）             | 如何不阻塞主流程？         |
| **② 提炼** | 离线 LLM 总结教训 / 最佳实践              | 如何保证总结质量？         |
| **③ 存储** | 向量库 + 元数据（类型、时间、权重）             | 如何支持快速检索？         |
| **④ 检索** | 语义匹配 + 多路召回                     | 如何提高命中率？          |
| **⑤ 注入** | System Prompt / Few-shot / 规则约束 | 如何让 Agent “遵守”经验？ |
| **⑥ 执行** | 路径引导 + 偏离检测                     | 如何避免“死记硬背”？       |
| **⑦ 评估** | 成功率、耗时、Token 消耗                 | 如何判断经验是否有效？       |
| **⑧ 淘汰** | 降权 / 归档 / 删除                    | 如何防止经验库膨胀？        |

## 三、经验数据结构设计

### 3.1 核心数据结构

```python
# 经验数据结构
class Experience(TypedDict):
    id: str  # 唯一ID (e.g., exp_123456)
    type: Literal["success", "failure", "preventive"]  # 经验类型
    question: str  # 用户原始问题
    context: str  # 当时的上文摘要
    intended_action: str  # 预期操作
    actual_result: str  # 实际结果
    lesson: str  # 总结出的教训/最佳实践
    tool_calls: List[Dict]  # 最终使用的工具调用链
    timestamp: float  # 时间戳
    similar_count: int  # 同类聚合计数
    confidence: float  # 置信度 (0-1)
    scope: Literal["global", "domain", "personal"]  # 经验作用域
    domain: Optional[str]  # 领域标识
    agent_id: Optional[str]  # Agent 标识
```

### 3.2 经验评分维度

| 评分维度                   | 说明                  | 更新逻辑                  |
|:-----------------------|:--------------------|:----------------------|
| **成功率 (Success Rate)** | 这条路径被执行后，验证通过的比例。   | 成功 +1，失败 -2（惩罚比奖励敏感）。 |
| **平均耗时 (Latency)**     | 完成该任务消耗的 Token 和时间。 | 记录每次耗时，取移动平均值。        |
| **调用次数 (Usage Count)** | 被使用的频率。             | 每调用一次 +1。             |
| **最近一次成功时间 (Recency)** | 最后一次成功的时间戳。         | 成功时更新。                |

**综合得分计算**：

````python
def get_score(record):
    success_rate = record.success_count / (record.success_count + record.fail_count + 0.01)
    avg_latency = np.mean(record.total_latency_ms) if record.total_latency_ms else 1000
    speed_score = max(0, 1 - (avg_latency - 50) / 1000)
    return 0.7 * success_rate + 0.3 * speed_score
````

## 四、在线/离线分离架构（核心设计）

### 4.1 为什么必须分离？

如果每次 Agent 交互完成后，都**同步**执行“LLM 总结教训 + 向量化 Embedding + 写入向量库”这一整套流程，每次请求的响应时间会额外增加
**2~5 秒**。

### 4.2 核心架构

| 阶段         | 操作                                           | 耗时         | 是否阻塞用户       |
|:-----------|:---------------------------------------------|:-----------|:-------------|
| **在线（实时）** | 1. 记录原始轨迹（Raw Log） 2. 发送到消息队列                | **< 50ms** | ❌ 不阻塞        |
| **离线（后台）** | 1. 消费队列 2. LLM 总结教训 3. 生成 Embedding 4. 写入向量库 | **2~5s**   | ✅ 完全异步，用户无感知 |

### 4.3 代码实现

#### 在线记录（轻量级）

```python
class OnlineRecorder:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.queue_key = "experience_raw_queue"

    def record_raw(self, state: dict, result: str, is_success: bool):
        raw_record = {
            "timestamp": datetime.now().isoformat(),
            "question": state.get("question"),
            "tool_calls": state.get("used_tools", []),
            "context": state.get("fused_context", ""),
            "final_result": result,
            "is_success": is_success,
            "thread_id": state.get("thread_id", "unknown")
        }
        self.redis_client.lpush(self.queue_key, json.dumps(raw_record))
```

#### 离线学习 Worker

```python
class OfflineLearner:
    def run_forever(self):
        while True:
            item = self.redis_client.brpop("experience_raw_queue", timeout=1)
            if item:
                raw_data = json.loads(item[1])
                self._process(raw_data)

    def _process(self, raw_data):
        # 1. LLM 总结教训（耗时操作）
        if raw_data["is_success"]:
            prompt = f"任务成功，用户问：{raw_data['question']}，工具链：{raw_data['tool_calls']}。请总结 1 条成功经验。"
        else:
            prompt = f"任务失败，用户问：{raw_data['question']}，错误信息：{raw_data['final_result']}。请总结 1 条教训。"
        lesson = self.llm.invoke(prompt).content

        # 2. 生成向量
        embedding = self.embed_model.encode(lesson).tolist()

        # 3. 存入向量库
        self.store.add(document=lesson, embedding=embedding, metadata={...})
```

#### 批量处理优化

```python
def _process_batch(self, raw_records):
    if len(raw_records) < 5:
        return  # 攒够 5 条再处理

    batch_text = "\n".join([f"用户：{r['question']}，结果：{r['final_result']}" for r in raw_records])
    prompt = f"以下是最近一批用户交互记录，请为每一条分别生成 1 条教训：{batch_text}"
    lessons = self.llm.invoke(prompt).content
    # 批量入库
    for lesson in lessons.split('\n\n'):
        self._embed_and_store(lesson.strip())
```

## 五、路径复用与持续进化

### 5.1 核心问题

如果系统无脑地重复第一条“侥幸成功”的路径，就会陷入 **“路径锁定”（Path Dependency）** 陷阱：明明有一条更快的路，但它因为“第一次走通了”就永远不走其他路了。

### 5.2 解决方案：探索-利用平衡（Epsilon-Greedy）

在每一次决策前，掷一个“骰子”：

- **95% 的概率（利用）**：选择当前得分最高的历史路径。
- **5% 的概率（探索）**：故意屏蔽掉历史路径，让 Agent 完全从零开始自由规划。

```python
def decide_path(question, store):
    if random.random() < 0.05:  # 5% 探索概率
        print("🧪 触发探索模式：尝试生成全新路径")
        return None
    else:
        return store.get_best_path(question)
```

### 5.3 路径优化迭代

当 Agent 基于经验路径执行任务时，如果它**发现了一个更优的子步骤**，系统生成一个 **“派生路径”** 并让它与原路径竞争。

```python
def compare_and_update(original_path, new_path_result):
    if new_path_result["latency"] < original_path["avg_latency"] * 0.8:
        store.save_path(new_path, parent_id=original_path.id, is_recommended=True)
        original_path.priority -= 1  # 降低原路径优先级
```

### 5.4 时间衰减与淘汰机制

```python
def get_decayed_score(record):
    hours_since_success = (time.time() - record.last_success_time) / 3600
    decay_factor = max(0.5, 1 - 0.02 * (hours_since_success / 24))
    return record.get_raw_score() * decay_factor
```

当分数低于阈值（如 0.2）时，系统自动将该路径从“活跃经验库”移入“历史归档库”。

## 六、路径引导（让 Agent 复用成功路径）

### 6.1 三层引导体系

| 层级                | 策略                     | 作用                     | 实现方式                                     |
|:------------------|:-----------------------|:-----------------------|:-----------------------------------------|
| **L1：规则层（硬约束）**   | 将成功路径转化为“系统规则”         | 强制 Agent 在特定条件下必须走某条路  | 在 System Prompt 中写入“如果遇到 X 问题，必须调用 Y 工具” |
| **L2：偏好层（软引导）**   | 记录“成功路径”作为 Few-shot 示例 | 让 LLM 在决策时“更倾向于”选择成功路径 | 在每次对话开始时，注入 1-2 个成功案例作为示例                |
| **L3：执行层（运行时检查）** | 在执行前检查是否偏离历史成功路径       | 若 Agent 试图走新路，先验证其合理性  | 在工具调用前做“路径匹配”，若相似度高则自动修正                 |

### 6.2 路径偏离检测

```python
def path_deviation_check(state):
    current_tool = state.get("pending_tool_call")
    question = state["question"]

    success_paths = experience_store.retrieve_success_paths(question, top_k=1)
    if not success_paths:
        return {}

    expected_next_tool = success_paths[0]["tool_chain"][0]["tool"]
    if current_tool and current_tool["name"] != expected_next_tool:
        correction_msg = f"⚠️ 偏离历史成功路径，已自动修正为 {expected_next_tool}"
        return {
            "pending_tool_call": success_paths[0]["tool_chain"][0],
            "messages": [SystemMessage(content=correction_msg)]
        }
    return {}
```

## 七、经验冲突处理

### 7.1 冲突场景示例

- 经验 A：`“查 CNC 状态优先用 query_db，因为速度快”`
- 经验 B：`“查 CNC 状态优先用 search_knowledge，因为数据更全”`

### 7.2 仲裁策略

| 策略         | 说明                    | 适用场景     |
|:-----------|:----------------------|:---------|
| **置信度优先**  | 选择 `confidence` 更高的经验 | 大多数情况    |
| **时效性优先**  | 选择 `timestamp` 更新的经验  | 系统规则经常变化 |
| **上下文匹配度** | 选择与当前上下文更相似的经验        | 复杂决策     |
| **人工仲裁**   | 当两条经验得分接近时，暂停并请求人工标注  | 高价值场景    |

```python
def resolve_conflict(candidates: List[Experience]) -> Experience:
    scored = []
    for exp in candidates:
        score = 0.4 * exp.confidence + 0.3 * exp.recency_score + 0.3 * exp.context_similarity
        scored.append((score, exp))
    return max(scored, key=lambda x: x[0])[1]
```

## 八、多 Agent 经验共享与隔离

当系统有 10+ 个不同领域的 Agent 时，经验管理需要区分“全局”和“局部”。

| 经验类型               | 适用范围         | 示例                                                  |
|:-------------------|:-------------|:----------------------------------------------------|
| **全局经验（Global）**   | 所有 Agent 共享  | “调用工具前必须先校验参数类型”                                    |
| **领域经验（Domain）**   | 同领域 Agent 共享 | “设备 Agent：查 CNC 状态必须传 device_id”                    |
| **个体经验（Personal）** | 仅特定 Agent 使用 | “Agent-A 偏好用 query_db，Agent-B 偏好用 search_knowledge” |

```python
# 检索时按当前 Agent 身份过滤
def retrieve_experiences(question, agent_id, domain):
    filter_scope = {"$or": [
        {"scope": "global"},
        {"scope": "domain", "domain": domain},
        {"scope": "personal", "agent_id": agent_id}
    ]}
    return vector_store.query(question, filter=filter_scope)
```

## 九、反事实经验生成（主动学习）

除了被动记录真实交互，还可以**主动模拟**可能出错但还没发生的场景，提前生成经验。

```python
def generate_preventive_lessons():
    high_risk_questions = analyze_failure_patterns()
    for q in high_risk_questions:
        sim_prompt = f"用户问：{q}。如果 Agent 错误地调用了 `delete` 工具，会发生什么？请生成一条警告经验。"
        lesson = llm.invoke(sim_prompt).content
        experience_store.save(lesson, type="preventive")
```

## 十、用户反馈闭环（纠正“坏经验”）

| 反馈类型     | 触发方式     | 处理动作                               |
|:---------|:---------|:-----------------------------------|
| ** 有用**  | 用户点赞     | 提升该经验的 `confidence`                |
| ** 无用**  | 用户点踩     | 降低该经验的 `confidence`，若低于阈值则标记为“待审核” |
| ** 错误**  | 用户/工程师标记 | 将该经验移入“黑名单”，并从活跃检索库中移除             |
| **️ 修正** | 工程师编辑    | 用新版本覆盖旧经验，记录变更历史                   |

```python
def handle_feedback(exp_id, feedback_type):
    exp = store.get(exp_id)
    if feedback_type == "useful":
        exp.confidence = min(1.0, exp.confidence + 0.1)
    elif feedback_type == "useless":
        exp.confidence = max(0.0, exp.confidence - 0.15)
    elif feedback_type == "wrong":
        store.archive(exp_id, reason="user_marked_wrong")
        notify_human_review(exp_id)
    store.save(exp)
```

## 十一、经验效果度量体系

| 指标                        | 定义              | 计算方式                               |
|:--------------------------|:----------------|:-----------------------------------|
| **命中率（Hit Rate）**         | 检索到相关经验的请求占比    | `命中经验数 / 总请求数`                     |
| **采纳率（Adoption Rate）**    | Agent 实际遵循经验的占比 | `遵循经验数 / 命中经验数`                    |
| **改进率（Improvement Rate）** | 采纳经验后成功率提升      | `(采纳后成功率 - 基线成功率) / 基线成功率`         |
| **Token 节省率**             | 因经验复用节省的 Token  | `(基线 Token - 复用 Token) / 基线 Token` |
| **经验新鲜度**                 | 经验库中有效经验的占比     | `(最近 N 天被命中的经验数 / 总经验数)`           |

```python
def generate_report():
    return {
        "hit_rate": 0.72,
        "adoption_rate": 0.85,
        "improvement_rate": 0.23,
        "token_saved": 0.34,
        "freshness": 0.65
    }
```

## 十二、合并同类项（防止经验库爆炸）

### 12.1 为什么要合并

- **避免信息冗余**：100 个用户都犯了“设备编号多打了个 0”的错误，不需要存 100 条。
- **提升检索质量**：精华经验比碎片经验更精准。
- **节约存储成本**。

### 12.2 离线聚类合并（推荐）

```python
def merge_experiences(store, threshold=0.85):
    all_lessons = store.get_all_unmerged()
    embeddings = store.embed_model.encode([l["text"] for l in all_lessons])

    merged = []
    visited = set()
    for i in range(len(all_lessons)):
        if i in visited: continue
        cluster = [i]
        for j in range(i + 1, len(all_lessons)):
            if j in visited: continue
            if cosine_similarity(embeddings[i], embeddings[j]) > threshold:
                cluster.append(j)
                visited.add(j)

        if len(cluster) > 1:
            combined_text = "\n".join([all_lessons[k]["text"] for k in cluster])
            summary = llm.invoke(f"合并以下相似经验为一条精华：{combined_text}").content
            merged.append(summary)
        else:
            merged.append(all_lessons[i]["text"])
        visited.add(i)

    store.replace_with_merged(merged)
```

### 12.3 在线增量合并

每次新增经验时，先检索 Top-1 已有经验。如果最高相似度 > 0.9，则不新增，而是**更新已有经验的权重**。

```python
def save_or_update(store, new_lesson):
    similar = store.retrieve_top1(new_lesson["text"])
    if similar and similar["score"] > 0.9:
        store.update_existing(similar["id"], count=similar["count"] + 1)
    else:
        store.add_new(new_lesson)
```

## 十三、演进路线图

| 阶段           | 能力                        | 实现复杂度 |
|:-------------|:--------------------------|:------|
| **V1.0（基础）** | 离线总结 + 向量检索 + 强制注入        | 低     |
| **V2.0（优化）** | 置信度评分 + 探索机制 + 路径迭代       | 中     |
| **V3.0（智能）** | 冲突仲裁 + 反事实生成 + 全局/领域/个体分层 | 中高    |
| **V4.0（闭环）** | 用户反馈闭环 + 自动化标注 + 效果度量仪表盘  | 高     |

## 十四、完整闭环流程图

```text
[用户提问]
    ↓
[入口检索] → 查找匹配的历史路径 + 经验教训
    ↓
[Epsilon-Greedy 决策]
    ├─ 5% 概率 → 走【探索模式】→ 自由规划 → 执行
    └─ 95% 概率 → 走【利用模式】→ 加载 Top-1 路径 → 执行
    ↓
[执行&验证]
    ↓
对比【实际表现】与【历史记录】
    ├─ 若表现 > 历史记录 → 更新路径（派生 / 提升权重）
    ├─ 若表现 ≈ 历史记录 → 仅增加调用次数
    └─ 若表现 < 历史记录 → 降低权重，记录失败
    ↓
[在线记录] → 推送原始轨迹到消息队列（< 50ms，不阻塞）
    ↓
[后台 Worker（异步）]
    ├─ 消费队列
    ├─ LLM 总结教训 / 最佳实践
    ├─ 生成 Embedding
    └─ 存入向量库
    ↓
[后台定时任务（每日凌晨）]
    ├─ 聚类合并同类经验
    ├─ 计算衰减分数
    ├─ 淘汰低分路径
    └─ 生成效果报告
```

## 十五、总结

| 问题            | 解决方案                             |
|:--------------|:---------------------------------|
| 记录经验太慢        | **在线/离线分离**：实时只存队列，离线批量总结        |
| Agent 不记得成功路径 | 将经验存入**向量库（长期记忆）**               |
| 记住了但不主动用      | 在 System Prompt 中**强制注入**历史路径提醒  |
| 用了但偏离了        | 在执行前做**路径偏离检测**，自动修正             |
| 第一次路径不是最优     | **Epsilon-Greedy 探索机制** + 路径迭代优化 |
| 旧路径不符合新情况     | **时间衰减 + 成功率监控**，自然淘汰            |
| 多条路径如何管理      | 路径权重 + 置信度 + 过期机制                |
| 跨任务复用         | 后台**聚类合并**同类经验                   |
| 经验冲突          | **综合评分仲裁**（置信度 + 时效性 + 上下文匹配度）   |
| 如何知道系统效果      | **度量仪表盘**（命中率、采纳率、改进率、Token节省率）  |