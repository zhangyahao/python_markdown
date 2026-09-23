- 一、为什么需要积累成功与失败经验？

  ### 1.1 Agent 的“金鱼记忆”问题

  在当前的 Agent 架构中，虽然通过 `Checkpointer` 实现了对话状态的持久化（短期记忆），但这种记忆是**会话级别**的：

    - 当用户开启一个新的 `thread_id` 时，Agent 会“忘记”之前所有会话中学到的东西。
    - 当同一个用户再次问“CNC-01 报警阈值是多少？”时，Agent 依然可能调用错误的工具或给出错误的参数，**重复消耗 Token 和算力
      **。

### 1.2 传统“重试”与“经验反思”的本质区别

| 传统方案（重试）                           | 经验反思方案（学习）                             |
    |:-----------------------------------|:---------------------------------------|
| **被动防御**：错了就重试，直到成功或耗尽次数。          | **主动避坑**：错了就总结教训，下次直接绕开错误路径。           |
| **无状态**：每次重试都是“第一次”，不知道上次为什么错。     | **有记忆**：知道“上次查 CNC-99 不存在，是因为用户写错了编号”。 |
| **成本线性增长**：同类错误消耗 Token 次数 = 错误次数。 | **成本递减**：同类错误只消耗 1 次 Token，后续靠检索经验即可。  |

**核心结论**：Agent 应该像人类一样，“失败”不是终点，而是“学习”的起点。建立长期记忆的核心价值是**将“踩坑”转化为“经验”**
，实现真正的智能化进化。

## 二、长记忆的核心难点

长期记忆的难度不在于“存”和“取”，而在于**不知道该存什么、存了不知道对不对、对了不知道什么时候会变错、错了会自我强化**。

### 2.1 信用分配难

一次任务成功或失败，到底是哪个环节决定的？

| 场景                                                    | 问题                       |
    |:------------------------------------------------------|:-------------------------|
| 用户问“黄芪价格走势”，Agent 调了中医 Agent + 社科 Agent + 经济数据，最后回答不错 | 是路由对了？检索对了？融合对了？还是纯粹运气好？ |
| 同一个问题，下次调用顺序不同，结果变差了                                  | 是经验本身错了，还是这次执行有偶然因素？     |
| 失败时，是工具调用参数错了，还是检索没召回，还是 LLM 生成跑偏                     | 归因不到具体环节，总结出的“教训”就是错的    |

**信用分配是长记忆最根本的难点。** 如果归因错了，存进去的“经验”不仅没用，还会误导后续决策。Agent 的执行链通常有 5–10
个步骤，每一步都可能是原因，也可能只是相关而非因果。

### 2.2 泛化粒度难

从一次具体交互中总结出的经验，放到下次用时，粒度很难把握。

| 粒度  | 例子                                               | 问题               |
    |:----|:-------------------------------------------------|:-----------------|
| 太具体 | “查 CNC-01 报警阈值时用 query_db，参数 device_id=‘CNC-01’” | 换个设备就失效，等于没总结    |
| 太抽象 | “查设备信息时要用合适的工具”                                  | 等于废话，Agent 本来就知道 |
| 刚好  | “查设备状态类问题优先用 query_db，因为比 search_knowledge 快”    | 但“刚好”的边界在哪里？没人知道 |

**每一次总结，都在做一个抽象层级的决策。** 太具体无法泛化，太抽象没有信息量。这个平衡点因任务而异、因领域而异，而且会随着系统演化而变化。

### 2.3 评价难题

这是最容易被低估的难点。

  - **没有 ground truth**：知识库的文本有明确来源，对错可以溯源。经验是 Agent 自己总结的，没有外部标签告诉你它对不对。
  - **成功不等于经验对**：一次任务成功，可能因为经验是对的，也可能因为 LLM 自己纠正了，或者任务本身简单蒙对了。
  - **失败不等于经验错**：可能因为经验本身错了，也可能因为经验对但执行时没遵循，或者任务超出了经验适用范围。
  - **验证成本高**：要真正验证一条经验是否有效，需要做 A/B 测试、控制变量、积累足够样本。这在 Agent 场景下几乎做不到。

**结果就是：你存了大量经验，但不知道哪些真正有用。**

### 2.4 时效性与分布漂移

经验会过时，但你不知道什么时候该淘汰。

| 变化类型   | 例子                                   | 影响            |
    |:-------|:-------------------------------------|:--------------|
| 工具变了   | 原来 query_db 快，现在 search_knowledge 更快 | 旧经验变成错误引导     |
| 数据变了   | 药材价格数据源换了，字段名变了                      | 旧经验中的参数失效     |
| 用户变了   | 用户群体从专业人士变成普通消费者                     | 旧经验的语气和深度不再适用 |
| 任务分布变了 | 原来多是单领域查询，现在多是跨域分析                   | 旧经验的适用场景减少    |

**难点在于**：无法实时感知这些变化。等你发现经验失效时，可能已经被错误引导了很多次。

### 2.5 自我强化与反馈回路

这是长记忆最危险的特性。

  ```  text
  存了一条错误经验
     ↓
  下次检索命中，Agent 遵循
     ↓
  任务失败（因为经验错了）
     ↓
  失败被记录，但归因错了（以为是别的原因）
     ↓
  总结出一条新的错误经验
     ↓
  两条错误经验互相强化
     ↓
  系统越来越自信地犯错
  ```

**坏经验比没有经验更糟糕。** 没有经验时，Agent 至少会从零推理；有了坏经验，Agent 会自信地走错路。而且这个回路是**自我指涉**
的：Agent 用自己的输出训练自己的记忆，没有任何外部校正机制。

### 2.6 检索精度：语义相似 ≠ 情境相似

经验检索通常用向量相似度。但**语义相似的 query，可能需要完全不同的处理方式**。

| Query A       | Query B       | 语义相似度     | 实际需要的经验        |
  |:--------------|:--------------|:----------|:---------------|
| “黄芪价格走势”      | “黄芪功效”        | 高（都含“黄芪”） | 完全不同（经济 vs 中医） |
| “甘肃黄芪种植”      | “山西黄芪种植”      | 极高        | 可能不同（地区差异）     |
| “黄芪 2020 年价格” | “黄芪 2024 年价格” | 极高        | 时间范围不同，经验可能不适用 |

**语义相似度捕捉不到情境差异**。你需要在经验检索中额外考虑：领域、时间范围、地区、任务类型、Agent 身份。这些维度的组合爆炸，让检索精度很难保证。

### 2.7 与知识库的对比

| 维度   | 知识库        | 经验库              |
  |:-----|:-----------|:-----------------|
| 数据来源 | 外部文本，有明确出处 | Agent 自己总结，无外部验证 |
| 对错判断 | 可溯源、可验证    | 无 ground truth   |
| 更新频率 | 低，数据相对稳定   | 高，每次交互都可能新增      |
| 淘汰机制 | 按来源和时效管理   | 不知道何时该淘汰         |
| 错误后果 | 检索不到或检索到旧版 | 自信地走错路，且自我强化     |
| 泛化要求 | 低，原文即答案    | 高，必须从具体中抽象       |
| 评价成本 | 低，人工抽检即可   | 高，需要 A/B 测试      |

**知识库是“读”，经验库是“学”。读容易，学难。**

## 三、经验的生命周期管理（从生到死）

| 阶段       | 核心动作                            | 关键问题               |
  |:---------|:--------------------------------|:-------------------|
| **① 采集** | 在线记录原始轨迹（问题、工具链、结果）             | 如何不阻塞主流程？          |
| **② 提炼** | 离线 LLM 总结教训 / 最佳实践，并做归因         | 如何保证总结质量？如何定位出错环节？ |
| **③ 存储** | 向量库 + 元数据（类型、时间、权重、置信度、适用范围）    | 如何支持快速检索？          |
| **④ 检索** | 语义匹配 + 多路召回 + 多维度过滤             | 如何提高命中率？如何避免情境误配？  |
| **⑤ 注入** | System Prompt / Few-shot / 规则约束 | 如何让 Agent “遵守”经验？  |
| **⑥ 执行** | 路径引导 + 偏离检测（软引导）                | 如何避免“死记硬背”？        |
| **⑦ 评估** | 成功率、耗时、Token 消耗、归因准确率           | 如何判断经验是否有效？        |
| **⑧ 淘汰** | 降权 / 归档 / 删除                    | 如何防止经验库膨胀？         |

## 四、经验数据结构设计

### 4.1 核心数据结构



  ```python
  class Experience(TypedDict):
      id: str                          # 唯一ID
      type: Literal["success", "failure", "preventive"]  # 经验类型
      question: str                    # 用户原始问题
      context: str                     # 当时的上文摘要
      intended_action: str             # 预期操作
      actual_result: str               # 实际结果
      lesson: str                      # 总结出的教训/最佳实践
      attribution: List[Dict]          # 归因结果：最可能出错的环节及证据
      tool_calls: List[Dict]           # 最终使用的工具调用链
      timestamp: float                 # 时间戳
      similar_count: int               # 同类聚合计数
      confidence: float                # 置信度 (0-1)
      scope: Literal["global", "domain", "personal"]  # 经验作用域
      domain: Optional[str]            # 领域标识
      agent_id: Optional[str]          # Agent 标识
      # 新增：情境元数据
      time_range: Optional[str]        # 适用时间范围
      region: Optional[str]            # 适用地区
      task_type: Optional[str]         # 任务类型
      status: Literal["quarantine", "active", "archived"]  # 隔离/活跃/归档
      validation_count: int            # 验证次数
      success_after_use: int           # 使用后成功次数
      fail_after_use: int              # 使用后失败次数
  ```

### 4.2 经验评分维度

| 评分维度         | 说明                  | 更新逻辑                 |
  |:-------------|:--------------------|:---------------------|
| **成功率**      | 这条路径被执行后，验证通过的比例。   | 成功 +1，失败 -2（惩罚比奖励敏感） |
| **平均耗时**     | 完成该任务消耗的 Token 和时间。 | 记录每次耗时，取移动平均值        |
| **调用次数**     | 被使用的频率。             | 每调用一次 +1             |
| **最近一次成功时间** | 最后一次成功的时间戳。         | 成功时更新                |
| **归因准确率**    | 归因结果与人工抽检的一致率。      | 人工抽检后更新              |
| **情境匹配度**    | 检索时与当前情境的匹配程度。      | 检索时计算                |

**综合得分计算**：

python

  ```
  def get_score(record):
      success_rate = record.success_count / (record.success_count + record.fail_count + 0.01)
      avg_latency = np.mean(record.total_latency_ms) if record.total_latency_ms else 1000
      speed_score = max(0, 1 - (avg_latency - 50) / 1000)
      attribution_score = record.attribution_accuracy  # 人工抽检校准
      return 0.5 * success_rate + 0.2 * speed_score + 0.3 * attribution_score
  ```

## 五、在线/离线分离架构（核心设计）

### 5.1 为什么必须分离？

如果每次 Agent 交互完成后，都**同步**执行“LLM 总结教训 + 向量化 Embedding + 写入向量库”这一整套流程，每次请求的响应时间会额外增加
**2~5 秒**。

### 5.2 核心架构

| 阶段         | 操作                                                     | 耗时         | 是否阻塞用户     |
  |:-----------|:-------------------------------------------------------|:-----------|:-----------|
| **在线（实时）** | 1. 记录原始轨迹（Raw Log） 2. 发送到 SQLite 队列表                   | **< 50ms** | 不阻塞        |
| **离线（后台）** | 1. 消费队列 2. LLM 总结教训 + 归因 3. 生成 Embedding 4. 写入经验库（隔离区） | **2~5s**   | 完全异步，用户无感知 |

### 5.3 代码实现

#### 在线记录（轻量级）

python

  ```
  class OnlineRecorder:
      def __init__(self, db_path="experience.db"):
          self.conn = sqlite3.connect(db_path)
          self._init_table()
  
      def record_raw(self, state: dict, result: str, is_success: bool):
          raw_record = {
              "timestamp": datetime.now().isoformat(),
              "question": state.get("question"),
              "tool_calls": json.dumps(state.get("used_tools", []), ensure_ascii=False),
              "context": state.get("fused_context", ""),
              "final_result": result,
              "is_success": is_success,
              "thread_id": state.get("thread_id", "unknown"),
              "step_trace": json.dumps(state.get("step_trace", []), ensure_ascii=False)
          }
          self.conn.execute(
              "INSERT INTO raw_queue (data) VALUES (?)",
              (json.dumps(raw_record, ensure_ascii=False),)
          )
          self.conn.commit()
  ```

#### 离线学习 Worker

python

  ```
  class OfflineLearner:
      def run_forever(self):
          while True:
              row = self._fetch_one()
              if row:
                  raw_data = json.loads(row)
                  self._process(raw_data)
              else:
                  time.sleep(1)
  
      def _process(self, raw_data):
          # 1. LLM 总结教训 + 归因（耗时操作）
          if raw_data["is_success"]:
              prompt = f"""任务成功。用户问：{raw_data['question']}
  工具链：{raw_data['tool_calls']}
  执行轨迹：{raw_data['step_trace']}
  请总结 1 条可复用的成功经验，并指出最关键的 1-3 个有效环节。"""
          else:
              prompt = f"""任务失败。用户问：{raw_data['question']}
  错误信息：{raw_data['final_result']}
  执行轨迹：{raw_data['step_trace']}
  请总结 1 条可复用的教训，并归因最可能出错的 1-3 个环节，每个环节给出证据。"""
          response = self.llm.invoke(prompt).content
          lesson, attribution = self._parse_response(response)
  
          # 2. 生成向量
          embedding = self.embed_model.encode(lesson).tolist()
  
          # 3. 存入经验库（隔离区）
          self.store.add(
              document=lesson,
              embedding=embedding,
              metadata={
                  "type": "success" if raw_data["is_success"] else "failure",
                  "attribution": attribution,
                  "status": "quarantine",
                  "confidence": 0.5,
                  "scope": "domain",
                  "domain": raw_data.get("domain", "general"),
                  "timestamp": time.time()
              }
          )
  
      def _parse_response(self, response):
          # 解析 LLM 返回的总结和归因，要求结构化输出
          # 例如 JSON 格式：{"lesson": "...", "attribution": [...]}
          try:
              data = json.loads(response)
              return data["lesson"], data["attribution"]
          except:
              return response, []
  ```

#### 批量处理优化

python

  ```
  def _process_batch(self, raw_records):
      if len(raw_records) < 5:
          return  # 攒够 5 条再处理
  
      batch_text = "\n".join([
          f"用户：{r['question']}，结果：{r['final_result']}，轨迹：{r['step_trace']}"
          for r in raw_records
      ])
      prompt = f"""以下是最近一批用户交互记录，请为每一条分别生成 1 条教训，并归因最可能出错的环节：
  {batch_text}"""
      lessons = self.llm.invoke(prompt).content
      for lesson in lessons.split('\n\n'):
          self._embed_and_store(lesson.strip())
  ```

## 六、路径复用与持续进化

### 6.1 核心问题

如果系统无脑地重复第一条“侥幸成功”的路径，就会陷入 **“路径锁定”（Path Dependency）** 陷阱：明明有一条更快的路，但它因为“第一次走通了”就永远不走其他路了。

### 6.2 解决方案：探索-利用平衡（Epsilon-Greedy）

在每一次决策前，掷一个“骰子”：

- **95% 的概率（利用）**：选择当前得分最高的历史路径。
- **5% 的概率（探索）**：故意屏蔽掉历史路径，让 Agent 完全从零开始自由规划。

python

  ```
  def decide_path(question, store):
      if random.random() < 0.05:  # 5% 探索概率
          print("🧪 触发探索模式：尝试生成全新路径")
          return None
      else:
          return store.get_best_path(question)
  ```

### 6.3 路径优化迭代

当 Agent 基于经验路径执行任务时，如果它**发现了一个更优的子步骤**，系统生成一个 **“派生路径”** 并让它与原路径竞争。

python

  ```
  def compare_and_update(original_path, new_path_result):
      if new_path_result["latency"] < original_path["avg_latency"] * 0.8:
          store.save_path(new_path, parent_id=original_path.id, is_recommended=True)
          original_path.priority -= 1  # 降低原路径优先级
  ```

### 6.4 时间衰减与淘汰机制

python

  ```
  def get_decayed_score(record):
      hours_since_success = (time.time() - record.last_success_time) / 3600
      decay_factor = max(0.5, 1 - 0.02 * (hours_since_success / 24))
      return record.get_raw_score() * decay_factor
  ```

当分数低于阈值（如 0.2）时，系统自动将该路径从“活跃经验库”移入“历史归档库”。

## 七、路径引导（让 Agent 复用成功路径）

### 7.1 三层引导体系

| 层级                | 策略                     | 作用                     | 实现方式                                     |
  |:------------------|:-----------------------|:-----------------------|:-----------------------------------------|
| **L1：规则层（硬约束）**   | 将成功路径转化为“系统规则”         | 强制 Agent 在特定条件下必须走某条路  | 在 System Prompt 中写入“如果遇到 X 问题，必须调用 Y 工具” |
| **L2：偏好层（软引导）**   | 记录“成功路径”作为 Few-shot 示例 | 让 LLM 在决策时“更倾向于”选择成功路径 | 在每次对话开始时，注入 1-2 个成功案例作为示例                |
| **L3：执行层（运行时检查）** | 在执行前检查是否偏离历史成功路径       | 若 Agent 试图走新路，先验证其合理性  | 在工具调用前做“路径匹配”，若相似度高则提示，但不强制修正            |

### 7.2 路径偏离检测（软引导版）

python

  ```
  def path_deviation_check(state):
      current_tool = state.get("pending_tool_call")
      question = state["question"]
  
      success_paths = experience_store.retrieve_success_paths(question, top_k=1)
      if not success_paths:
          return {}
  
      best_path = success_paths[0]
      if best_path["confidence"] < 0.8:
          return {}  # 置信度不足，不干预
  
      expected_next_tool = best_path["tool_chain"][0]["tool"]
      if current_tool and current_tool["name"] != expected_next_tool:
          correction_msg = (
              f"⚠️ 检测到偏离历史成功路径。历史路径建议下一步使用 {expected_next_tool}，"
              f"当前计划使用 {current_tool['name']}。请确认是否继续当前计划。"
          )
          return {
              "messages": [SystemMessage(content=correction_msg)]
          }
      return {}
  ```

**关键改动**：不强制修正，只提示，让 LLM 自己决定。如果 LLM 决定继续偏离，记录这次偏离，后续根据结果更新经验权重。

## 八、经验冲突处理

### 8.1 冲突场景示例

- 经验 A：`“查 CNC 状态优先用 query_db，因为速度快”`
- 经验 B：`“查 CNC 状态优先用 search_knowledge，因为数据更全”`

### 8.2 仲裁策略

| 策略         | 说明                    | 适用场景     |
  |:-----------|:----------------------|:---------|
| **置信度优先**  | 选择 `confidence` 更高的经验 | 大多数情况    |
| **时效性优先**  | 选择 `timestamp` 更新的经验  | 系统规则经常变化 |
| **上下文匹配度** | 选择与当前上下文更相似的经验        | 复杂决策     |
| **人工仲裁**   | 当两条经验得分接近时，暂停并请求人工标注  | 高价值场景    |

python

  ```
  def resolve_conflict(candidates: List[Experience]) -> Experience:
      scored = []
      for exp in candidates:
          score = 0.4 * exp.confidence + 0.3 * exp.recency_score + 0.3 * exp.context_similarity
          scored.append((score, exp))
      return max(scored, key=lambda x: x[0])[1]
  ```

## 九、多 Agent 经验共享与隔离

当系统有 10+ 个不同领域的 Agent 时，经验管理需要区分“全局”和“局部”。

| 经验类型               | 适用范围         | 示例                                                  |
  |:-------------------|:-------------|:----------------------------------------------------|
| **全局经验（Global）**   | 所有 Agent 共享  | “调用工具前必须先校验参数类型”                                    |
| **领域经验（Domain）**   | 同领域 Agent 共享 | “设备 Agent：查 CNC 状态必须传 device_id”                    |
| **个体经验（Personal）** | 仅特定 Agent 使用 | “Agent-A 偏好用 query_db，Agent-B 偏好用 search_knowledge” |

python

  ```
  def retrieve_experiences(question, agent_id, domain):
      filter_scope = {"$or": [
          {"scope": "global"},
          {"scope": "domain", "domain": domain},
          {"scope": "personal", "agent_id": agent_id}
      ]}
      return vector_store.query(question, filter=filter_scope)
  ```

## 十、反事实经验生成（主动学习）

除了被动记录真实交互，还可以**主动模拟**可能出错但还没发生的场景，提前生成经验。

python

  ```
  def generate_preventive_lessons():
      high_risk_questions = analyze_failure_patterns()
      for q in high_risk_questions:
          sim_prompt = f"用户问：{q}。如果 Agent 错误地调用了 `delete` 工具，会发生什么？请生成一条警告经验。"
          lesson = llm.invoke(sim_prompt).content
          experience_store.save(lesson, type="preventive", status="quarantine")
  ```

**注意**：反事实生成的经验**不能直接进入活跃区**，必须标记为“隔离”状态，经过真实任务验证后才能激活。

## 十一、用户反馈闭环（纠正“坏经验”）

| 反馈类型   | 触发方式     | 处理动作                               |
  |:-------|:---------|:-----------------------------------|
| **有用** | 用户点赞     | 提升该经验的 `confidence`                |
| **无用** | 用户点踩     | 降低该经验的 `confidence`，若低于阈值则标记为“待审核” |
| **错误** | 用户/工程师标记 | 将该经验移入“黑名单”，并从活跃检索库中移除             |
| **修正** | 工程师编辑    | 用新版本覆盖旧经验，记录变更历史                   |

python

  ```
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

## 十二、经验效果度量体系

| 指标            | 定义              | 计算方式                               |
  |:--------------|:----------------|:-----------------------------------|
| **命中率**       | 检索到相关经验的请求占比    | `命中经验数 / 总请求数`                     |
| **采纳率**       | Agent 实际遵循经验的占比 | `遵循经验数 / 命中经验数`                    |
| **改进率**       | 采纳经验后成功率提升      | `(采纳后成功率 - 基线成功率) / 基线成功率`         |
| **Token 节省率** | 因经验复用节省的 Token  | `(基线 Token - 复用 Token) / 基线 Token` |
| **经验新鲜度**     | 经验库中有效经验的占比     | `(最近 N 天被命中的经验数 / 总经验数)`           |
| **归因准确率**     | 归因结果与人工抽检的一致率   | `人工抽检一致数 / 抽检总数`                   |

python

  ```
  def generate_report():
      return {
          "hit_rate": 0.72,
          "adoption_rate": 0.85,
          "improvement_rate": 0.23,
          "token_saved": 0.34,
          "freshness": 0.65,
          "attribution_accuracy": 0.78
      }
  ```

## 十三、合并同类项（防止经验库爆炸）

### 13.1 为什么要合并

- **避免信息冗余**：100 个用户都犯了“设备编号多打了个 0”的错误，不需要存 100 条。
- **提升检索质量**：精华经验比碎片经验更精准。
- **节约存储成本**。

### 13.2 离线聚类合并

python

  ```
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

### 13.3 在线增量合并

每次新增经验时，先检索 Top-1 已有经验。如果最高相似度 > 0.9，则不新增，而是**更新已有经验的权重**。

python

  ```
  def save_or_update(store, new_lesson):
      similar = store.retrieve_top1(new_lesson["text"])
      if similar and similar["score"] > 0.9:
          store.update_existing(similar["id"], count=similar["count"] + 1)
      else:
          store.add_new(new_lesson)
  ```

## 十四、针对长记忆难点的补强方案

### 14.1 信用分配：加归因层

**在轨迹记录中增加每一步的结构化标记**：

- 路由决策：选择了哪个 Agent，置信度多少
- 检索决策：用了什么 query，召回了哪些父块，RRF 分数
- 融合决策：哪些证据被采用，哪些被丢弃
- 生成决策：LLM 用了哪些证据

**在离线总结时，让 LLM 做归因**：

- 不要只总结“一条教训”
- 要求它指出“最可能出错的 1–3 个环节”
- 每个环节标注证据（如“路由模块未识别经济意图”）

**归因结果存入结构化字段**，而不是混在一段文本里。这样后续可以按环节统计错误率。

### 14.2 评价难题：引入人工抽检 + 延迟验证

**第一层：置信度门槛**

- 只有高置信度经验才注入
- 低置信度经验只记录，不注入
- 置信度初始值由来源决定（人工标注 > LLM 总结 > 反事实生成）

**第二层：人工抽检**

- 每周抽检 50–100 条新经验
- 标注“正确 / 错误 / 不确定”
- 用标注结果校准自动评分

**第三层：延迟验证**

- 经验存入时标记“待验证”
- 后续任务中如果命中并成功，增加置信度
- 如果命中但失败，降低置信度
- 积累 N 次后，从“待验证”转为“已验证”

**不要在第一次使用后就确定经验质量。**

### 14.3 泛化粒度：约束总结 prompt

在 LLM 总结 prompt 中明确要求：

> 请总结一条可复用的经验，要求：
>
> 1. 不包含具体参数值（如设备编号、具体日期）
> 2. 不包含过于宽泛的表述（如“要选对工具”）
> 3. 说明适用条件（什么情况下用）
> 4. 说明不适用条件（什么情况下不要用）
> 5. 长度控制在 50–150 字

**同时对总结结果做后处理**：

- 如果包含具体参数值，提示 LLM 重写或标记为“具体经验”
- 如果长度过短且无信息量，丢弃
- 如果长度过长，要求压缩

### 14.4 自我强化：加“经验隔离期”和“反向验证”

**隔离期**：

- 新经验存入后，先进入“隔离区”
- 隔离期内不注入 system prompt
- 只有被验证 N 次后才进入“活跃区”

**反向验证**：

- 定期抽样活跃经验
- 构造“如果不用这条经验会怎样”的对照
- 如果对照结果相同或更好，降低经验置信度

**禁止反事实生成的经验直接进入活跃区**。反事实经验只能作为“待验证”候选，必须经过真实任务验证。

### 14.5 检索精度：多维度过滤

在向量检索基础上，增加：

- 时间范围过滤
- 地区过滤
- 任务类型过滤
- 数据源过滤

**实现方式**：

- 经验元数据中增加这些字段
- 检索时根据当前 query 解析出的条件做过滤
- 如果没有明确条件，用默认范围

**同时增加“情境相似度”评分**：

- 不只看 query 向量相似度
- 还看元数据匹配度
- 综合排序

### 14.6 路径偏离检测：改成软引导

**不要强制修正**，改成：

- 检测到偏离时，注入一条提示：“历史成功路径是 X，当前路径是 Y，请确认是否继续”
- 让 LLM 自己决定
- 如果 LLM 决定继续偏离，记录这次偏离
- 如果偏离后成功，提升新路径权重
- 如果偏离后失败，降低偏离倾向

**同时加置信度门槛**：

- 只有历史路径置信度 > 0.8 时才提示
- 置信度低于 0.8 时不干预

### 14.7 与 TokenPilot 协同

TokenPilot 压缩上下文后，经验管理总结的是压缩后的轨迹。这有两个影响：

- **好处**：总结输入更短，成本更低
- **坏处**：压缩可能丢失归因所需的关键细节

**解决方案**：

- 在线记录时保留完整轨迹到 SQLite
- 离线总结时，从 SQLite 读完整轨迹，而不是从 TokenPilot 的压缩上下文读
- TokenPilot 只管 prompt 构造，不管经验总结

## 十五、修正后的实现优先级

| 优先级 | 模块               | 说明            |
  |:----|:-----------------|:--------------|
| P0  | 在线记录完整轨迹（SQLite） | 归因的基础         |
| P0  | 离线总结 + 归因层       | 不只总结教训，还要定位环节 |
| P0  | 置信度门槛 + 隔离期      | 防止坏经验污染       |
| P1  | 多维度检索过滤          | 提升检索精度        |
| P1  | 人工抽检机制           | 校准自动评分        |
| P1  | 延迟验证             | 不要第一次使用就定质量   |
| P2  | Epsilon-Greedy   | 探索机制          |
| P2  | 软引导替代强制修正        | 降低路径偏离检测风险    |
| P3  | 聚类合并             | 控制库规模         |
| 暂不做 | 反事实生成            | 风险高，收益不确定     |
| 暂不做 | 用户反馈闭环           | 需要 UI，信号稀疏    |
| 暂不做 | 效果度量仪表盘          | 等 V1.0 跑通再做   |

## 十六、演进路线图

| 阶段           | 能力                            | 实现复杂度 |
  |:-------------|:------------------------------|:------|
| **V1.0（基础）** | 离线总结 + 归因 + 隔离期 + 向量检索 + 强制注入 | 中     |
| **V2.0（优化）** | 置信度评分 + 探索机制 + 路径迭代 + 多维度过滤   | 中高    |
| **V3.0（智能）** | 冲突仲裁 + 分层 + 软引导 + 人工抽检校准      | 高     |
| **V4.0（闭环）** | 用户反馈闭环 + 自动化标注 + 效果度量仪表盘      | 高     |

## 十七、完整闭环流程图



  ```text
  [用户提问]
      ↓
  [入口检索] → 查找匹配的历史路径 + 经验教训（多维度过滤）
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
  [在线记录] → 推送完整轨迹到 SQLite 队列表（< 50ms，不阻塞）
      ↓
  [后台 Worker（异步）]
      ├─ 消费队列
      ├─ LLM 总结教训 + 归因
      ├─ 生成 Embedding
      └─ 存入经验库（隔离区）
      ↓
  [隔离期验证]
      ├─ 被检索命中 → 注入前先检查置信度
      ├─ 使用后成功 → 增加置信度
      ├─ 使用后失败 → 降低置信度
      └─ 积累 N 次后 → 从隔离区转入活跃区
      ↓
  [后台定时任务（每日凌晨）]
      ├─ 聚类合并同类经验
      ├─ 计算衰减分数
      ├─ 淘汰低分路径
      ├─ 人工抽检校准
      └─ 生成效果报告
  ```

## 十八、总结

| 问题            | 解决方案                                  |
  |:--------------|:--------------------------------------|
| 记录经验太慢        | **在线/离线分离**：实时只存队列，离线批量总结             |
| Agent 不记得成功路径 | 将经验存入**向量库（长期记忆）**                    |
| 记住了但不主动用      | 在 System Prompt 中**强制注入**历史路径提醒       |
| 用了但偏离了        | 在执行前做**路径偏离检测（软引导）**，提示但不强制修正         |
| 第一次路径不是最优     | **Epsilon-Greedy 探索机制** + 路径迭代优化      |
| 旧路径不符合新情况     | **时间衰减 + 成功率监控**，自然淘汰                 |
| 多条路径如何管理      | 路径权重 + 置信度 + 过期机制                     |
| 跨任务复用         | 后台**聚类合并**同类经验                        |
| 经验冲突          | **综合评分仲裁**（置信度 + 时效性 + 上下文匹配度）        |
| 如何知道系统效果      | **度量仪表盘**（命中率、采纳率、改进率、Token节省率、归因准确率） |
| **信用分配难**     | **归因层**：记录每一步，让 LLM 定位出错环节            |
| **评价难**       | **隔离期 + 延迟验证 + 人工抽检**                 |
| **泛化粒度难**     | **约束总结 prompt + 后处理**                 |
| **自我强化**      | **隔离区 + 置信度门槛 + 反向验证**                |
| **检索精度**      | **多维度过滤 + 情境相似度评分**                   |
| **路径偏离风险**    | **软引导替代强制修正 + 置信度门槛**                 |
