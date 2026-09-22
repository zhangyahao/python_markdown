# Jev 决策模型完全指南

> 从核心概念到生产级 Agent 架构的完整技术参考

## 一、Jev 是什么？

**Jev 是 TypeSafe AI 于 2026 年 9 月 15 日发布的首个 “System One” 模型**，由 ChatGPT 核心技术 RLHF 的早期贡献者、前 OpenAI
研究员 Diogo Almeida 创立，团队历经两年隐身研发后推出，并获得 4000 万美元种子轮融资。

Jev **不生成任何文本**，专为 AI Agent 运行中的结构化决策而设计——它接收一段非结构化的“状态”（state），返回带校准概率的类型化答案，典型响应延迟为
**70~500 毫秒**。

### 核心定位：Agent 的“快思考”决策层

Jev 的命名源自心理学中的“系统一”（System 1）——快速、直觉式的判断。它和 LLM 形成 **“双核搭档”**：

| 角色      | 模型                    | 职责                  |
|:--------|:----------------------|:--------------------|
| **慢思考** | LLM (GPT/Claude/Qwen) | 复杂规划、推理、内容生成        |
| **快判断** | Jev                   | 高频结构化决策：路由、分类、评分、验证 |

TypeSafe 报告称，在结构化决策任务上，Jev 比前沿 LLM **快 20~200 倍**，成本低至 **1/40~1/400**。

## 二、核心概念：三种判断原语

Jev 的 API 围绕三种基本问题类型构建，可在单次请求中并行评估多个问题：

### 1. Choice（选择）

从预设的互斥选项中选出最匹配的一个，返回选中项及完整概率分布。最多支持 **255 个选项**。

### 2. Noul（是非判断）

判断某件事是否成立，返回 **0~1 之间的校准概率**，表示“是”的可能性。

### 3. Score（评分）

将结果放入有序量表（如低/中/高），返回概率加权的连续得分及各级别概率分布。

## 三、为什么 Jev 更适合决策层？（与 LLM 对比）

### LLM 的置信度到底指什么？

当你让 LLM 输出一个选项时，它本质上是在**生成文本**。它返回的 logprobs 或 token 概率，是“下一个词是某个
token”的概率，而不是“这个选项是否正确”的概率。这种概率**未经校准**，不能直接用于可靠的决策。

### LLM 做决策的三个硬伤

1. **概率不校准**：LLM 经常过度自信，可能给错误答案 0.99 的概率。
2. **输出需要解析**：返回自然语言文本，必须写正则、JSON 解析器或额外 LLM 调用来提取结构。
3. **成本和延迟高**：即使只输出一个词，也要跑完整的自回归解码。

### Jev 的本质优势

| 维度        | LLM           | Jev                     |
|:----------|:--------------|:------------------------|
| **输出**    | 文本序列，需解析      | 结构化的选项+校准概率             |
| **概率含义**  | token 概率，未校准  | 选项概率，经过 RLCD 校准         |
| **延迟**    | 数百毫秒~数秒       | 70~500 毫秒               |
| **成本**    | 按 token 计费，较高 | 输入 $0.042/百万 token，输出免费 |
| **决策可靠性** | 需额外校验，易出错     | 概率可直接用于阈值               |
| **失败模式**  | 格式错误、幻觉、选错    | 只可能选错（格式永不出错）           |
| **动态任务**  | 需重新写 Prompt   | 每次请求动态定义选项              |

**关键差异**：Jev 的概率是**校准的**。LLM 说“90% 把握”时，实际可能只有 60%；Jev 说“90% 把握”时，长期统计下确实约 90%
正确。这让“置信度阈值”真正可用。

## 四、接入方式与代码示例

### 准备工作：获取 API Key

1. 访问 TypeSafe 控制台 `console.typesafe.ai` 注册账号
2. 创建 API Key 并保存
3. 设置环境变量：



```bash
export TYPESAFE_API_KEY="ts_..."
```

### 方式一：原生 HTTP 请求（最通用）



```python
import requests, os

payload = {
    "model": "jev-latest",
    "state": "Help! My payments have been failing for 3 days.",
    "questions": {
        "is_urgent": {
            "type": "noul",
            "instructions": "Does this convey urgency?"
        },
        "department": {
            "type": "choice",
            "instructions": "Which team should handle this?",
            "criteria": {
                "billing": "Payments, invoicing, refunds",
                "technical": "Bugs, outages, integrations",
                "sales": "Pricing, upgrades, new accounts"
            }
        },
        "frustration": {
            "type": "score",
            "instructions": "How frustrated is the customer?",
            "criteria": ["Calm", "Frustrated", "Very angry"]
        }
    }
}

response = requests.post(
    "https://api.typesafe.ai/v1/systemone",
    headers={
        "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
        "Content-Type": "application/json"
    },
    json=payload
)

answers = response.json()["answers"]
print(f"紧急程度: {answers['is_urgent']['noul']:.2f}")
print(f"处理部门: {answers['department']['choice']}")
print(f"客户情绪: {answers['frustration']['score']}")
```

### 方式二：Python SDK (`@jev.fn` 装饰器)



```python
from typing import Literal
from pydantic import BaseModel, Field
import jev

class Triage(BaseModel):
    department: Literal["billing", "technical", "sales"]
    is_urgent: bool
    frustration: int = Field(ge=0, le=2)

@jev.fn
def triage(ticket: str) -> Triage:
    """A customer support ticket: {{ ticket }}"""
    return triage.state()

result = triage("I was charged twice. Fix this NOW.")
print(result)
# Triage(department='billing', is_urgent=True, frustration=2)
```

### 方式三：LangChain 集成 (`TypeSafeClassifier`)



```bash
pip install langchain-typesafe
```



```python
from langchain_typesafe import TypeSafeClassifier, Noul, Choice, Score

classifier = TypeSafeClassifier(
    questions={
        "is_urgent": Noul(instructions="Does this convey urgency?"),
        "department": Choice(
            instructions="Which team should handle this?",
            criteria={"billing": "Payments", "technical": "Bugs", "sales": "Pricing"}
        ),
        "frustration": Score(
            instructions="How frustrated is the customer?",
            criteria=["Calm", "Frustrated", "Very angry"]
        )
    }
)

result = classifier.invoke("Help! My payments have been failing for 3 days.")
print(result["department"]["choice"])  # 'billing'
print(result["is_urgent"]["noul"])     # 0.95
```

### 方式四：OpenRouter（免等待）



```python
import requests, json, os

response = requests.post(
    "https://openrouter.ai/api/alpha/decisions",
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json"
    },
    data=json.dumps({
        "model": "~typesafe/jev-latest",
        "state": "Help! My payouts have been failing for 3 days.",
        "questions": {
            "is_urgent": {
                "type": "noul",
                "instructions": "Does this message convey urgency?"
            }
        }
    })
)
answers = response.json()["answers"]
print(answers["is_urgent"]["noul"])
```

## 五、置信度校准与阈值设定

### 为什么阈值不能靠直觉？

Jev 的“校准”承诺的是**统计可靠性**，而非绝对正确。当 Jev 说“90% 置信度”时，长期来看它大约有 90% 的概率是正确的。但这不代表每一个具体的判断都一定对。

你担心的“低置信度反而是对的”这种情况，不是系统缺陷，而是**概率系统的固有属性**。处理这种情况的关键，不在于追求“100%
准确”，而在于通过**策略性地校准阈值和构建兜底流程**，来管理这种不确定性。

### 校准方法：分桶验证

1. **数据分桶**：将 Jev 的置信度分成若干区间（如 0.0-0.1, 0.1-0.2...）
2. **统计真实准确率**：在每个置信度区间内，用验证集跑一批数据，计算 Jev 判断正确的实际比例
3. **绘制可靠性图**：将“预测置信度”与“实际准确率”绘制成图。理想情况下应大致落在对角线上
4. **计算校准误差**：使用**期望校准误差（ECE）** 等指标量化偏差

### 使用 `jevcal` 工具

`jevcal` 是专门为 Jev 设计的校准工具，可以在你的数据上自动完成分桶验证，根据你设定的**准确率目标**（如“置信度高于 X 时准确率达到
99%”），自动计算最优阈值。

### 差异化阈值参考

| 动作类型    | 自动执行阈值       | 回退阈值 |
|:--------|:-------------|:-----|
| 客服分流    | 0.70         | 0.50 |
| 退款复核    | 0.55（进入人工复核） | —    |
| 内容限流    | 0.75（先限流）    | —    |
| 高风险工具执行 | 0.85         | 0.65 |
| 批准退款    | 0.95         | 0.80 |

### 处理“提示词导致的低置信度正确”

如果发现“低置信度才是对的”，这是一个需要诊断和优化的信号：

- **诊断**：问题设计是否太模糊？状态信息是否不足？指令是否清晰？
- **优化**：用样本回放验证改动效果；将“Jev 判断错误”的样本收集为反例，批量回填用于后续优化。

### 置信度路由架构



```python
def route_jev_decision(decision, action_type):
    thresholds = {
        "classify_ticket": {"auto": 0.70, "fallback": 0.50},
        "execute_tool": {"auto": 0.85, "fallback": 0.65},
        "approve_refund": {"auto": 0.95, "fallback": 0.80},
    }
    conf = decision.confidence
    thr = thresholds.get(action_type)
    
    if conf >= thr["auto"]:
        return "auto_execute"
    elif conf >= thr["fallback"]:
        return "fallback_review"
    else:
        return "human_review"
```

## 六、错误处理与分层路由

### Jev 不会出错吗？

Jev 并非“不会出错”，而是通过**架构设计**和**概率校准**，将错误的影响控制在工程可处理的范围内。

**零格式与零幻觉错误**：Jev 不生成文本，直接在预设选项空间中进行判断。它从物理上无法创造不存在的工具名、生成格式错误的
JSON、或返回不符合 Schema 的结果。官方对比中，Jev 的结构化输出错误率和工具调用错误率均为 **0%**，而对照组主流 LLM
错误率从零点几个百分点到 **45.5%** 不等。

**置信度校准：知道“自己不知道”**：Jev 采用 **RLCD（用于校准决策的强化学习）** 训练，其输出的概率是校准的。当 Jev 说它有 80%
的把握时，长期运行中大约 80% 的判断是正确的。

### 三层防御体系

| 层级      | 置信度范围         | 处理方式              |
|:--------|:--------------|:------------------|
| **第一层** | > 自动执行阈值      | 直接采纳，自动执行         |
| **第二层** | 回退阈值 ~ 自动执行阈值 | 回退给 LLM 复核，或标记待复核 |
| **第三层** | < 回退阈值        | 转人工处理，或返回安全默认动作   |

## 七、与长期记忆 + LLM 的对比

### 核心质疑

> “如果 Jev 置信度不够时还是要回退给 LLM 校验，那和直接让 LLM 判断有什么区别？而且我已经使用了长期记忆，LLM 的判断也很准了，Jev
> 的优势是不是就不大了？”

### 回退 LLM 的频率：不是 100% vs 100%

| 指标       | 纯 LLM | Jev + 回退 |
|:---------|:------|:---------|
| LLM 调用次数 | 100 次 | 5~15 次   |
| Jev 调用次数 | 0 次   | 100 次    |
| 总成本（示例）  | $1.00 | 约 $0.14  |
| 总延迟（示例）  | 200s  | 约 50s    |

**结论**：回退 LLM 不是“退回旧方案”，而是“只在 Jev 不确定时才花大钱”。成本和延迟差距是 **4~7 倍**。

### 长期记忆缩小了差距，但没有消除差距

| 维度     | 长期记忆 + LLM     | Jev                  |
|:-------|:---------------|:---------------------|
| 准确率    | 高              | 中高（约 67.8%，低于顶级 LLM） |
| 每次判断成本 | 仍需完整推理（$0.01+） | **$0.0004**          |
| 每次判断延迟 | 1~5s           | **70~500ms**         |
| 格式可靠性  | 仍可能输出格式错误      | **100% 结构化**         |
| 记忆维护成本 | 需要存储、检索、更新、淘汰  | **不需要**              |

长期记忆解决的是“知识复用”问题，Jev 解决的是“实时判断成本”问题。两者互补，而非替代。

### 何时使用 Jev？

| 场景                    | 用 Jev？  | 原因                        |
|:----------------------|:--------|:--------------------------|
| 高频、简单、格式严格（工单分类、模型路由） | ✅ 强烈推荐  | 省 90% LLM 调用              |
| 需要动态选项（从 50 个工具中选一个）  | ✅ 推荐    | Jev 支持动态定义，LLM 需要长 Prompt |
| 需要校准概率做阈值决策           | ✅ 推荐    | LLM 概率不可靠                 |
| 低频、复杂、需要深度推理          | ❌ 用 LLM | Jev 不擅长                   |
| 需要生成内容（写作、代码）         | ❌ 用 LLM | Jev 不生成文本                 |
| 任务只有 2~3 个固定选项        | ❌ 用规则   | 不需要模型                     |

## 八、Jev 与 LLM 的分工架构（快慢双系统）

### 核心架构



```text
用户请求
    ↓
┌─────────────────────────────────────────────┐
│            LLM（系统 2）                      │
│  规划、推理、生成、复杂决策                    │
│  低频、慢、贵、但智能                         │
└─────────────────────────────────────────────┘
    ↓ 拆解为原子决策点
┌─────────────────────────────────────────────┐
│         轻量级 ML（系统 1）                   │
│  路由、分类、评分、校验、门控                  │
│  高频、快、便宜、但智能有限                    │
└─────────────────────────────────────────────┘
    ↓ 高置信度自动执行 / 低置信度回退 LLM
最终输出
```

### 哪些“低智能问题”可以交给 ML？

| 决策类型   | 示例                | 适合的 ML 模型            |
|:-------|:------------------|:---------------------|
| 意图分类   | 用户问的是“查状态”还是“报修”？ | 微调 BERT / 逻辑回归 / Jev |
| 工具路由   | 从 50 个工具中选一个      | Jev / 微调分类器          |
| 结果校验   | 工具返回的结果是否有效？      | Jev / 轻量级二分类器        |
| 质量评分   | 回答质量 1~5 分        | Jev / 回归模型           |
| 风险判断   | 这个操作是否需要人工审批？     | Jev / XGBoost        |
| 优先级排序  | 这个工单应该多快处理？       | Jev / 规则引擎           |
| 是否需要检索 | 这个问题依赖外部知识吗？      | 语义匹配 / 小模型           |

### 代码示例



```python
class HybridAgent:
    def __init__(self):
        self.fast = FastDecisionLayer()  # 语义匹配 + Jev
        self.tool_registry = {...}
    
    def route(self, question: str) -> RoutingResult:
        intent, intent_conf = self.fast.classify_intent(question)
        need_retrieve, retrieve_conf = self.fast.should_retrieve(question)
        
        if intent_conf > 0.75 and intent == "query_status":
            return RoutingResult(action="query_device", route="fast_path", ...)
        elif intent_conf > 0.5:
            return RoutingResult(action="llm_plan", route="slow_path", ...)
        else:
            return RoutingResult(action="escalate", route="human_review", ...)
    
    def execute(self, question: str) -> str:
        routing = self.route(question)
        
        if routing.route == "fast_path":
            return TOOL_REGISTRY["query_device"]["func"](...)
        
        if routing.route == "slow_path":
            plan = llm_plan(question, "complex")
            results = [execute_step(step) for step in plan]
            return llm_generate_answer(question, results)
        
        return "已转人工处理。"
```

## 九、ReAct + 语义路由：LLM 规划 + 低智能模型选工具

### 为什么需要这样分工？

标准 ReAct 的问题在于：当工具有 50 个以上时，LLM 的 Prompt 会被工具描述撑爆，导致 Token 成本飙升、模型注意力分散、选错工具概率上升。而生产级架构的做法是：
**LLM 只在“意图层”工作，工具选择交给专门的匹配层。**

### 架构对比

**标准 ReAct（工具少时可用）**：



```text
LLM 看到所有工具描述 → 直接输出工具名和参数 → 执行 → 看结果 → 继续
```

**ReAct + 语义路由（工具多时推荐）**：



```text
LLM 分析状态 → 输出"意图描述"
    ↓
语义路由层（低智能模型）→ 从50个工具中匹配 Top-3 候选
    ↓
LLM 看到候选列表 → 确认或微调 → 输出最终工具调用
    ↓
执行 → 看结果 → 继续循环
```

### 核心代码



```python
def semantic_route(intent_text: str, top_k: int = 3) -> List[dict]:
    """低智能模型：根据意图描述，从所有工具中匹配 Top-K 候选。延迟 < 20ms。"""
    intent_emb = embed_model.encode([intent_text])
    sims = np.dot(intent_emb, tool_embeddings.T) / (
        np.linalg.norm(intent_emb) * np.linalg.norm(tool_embeddings, axis=1)
    )
    top_indices = np.argsort(sims[0])[-top_k:][::-1]
    return [{"name": tool_names[i], "description": TOOL_REGISTRY[tool_names[i]]["description"],
             "score": float(sims[0][i])} for i in top_indices]
```

### 收益

| 维度               | 标准 ReAct  | ReAct + 语义路由 |
|:-----------------|:----------|:-------------|
| LLM Prompt 中的工具数 | 50+ 个     | **3 个（候选）**  |
| 单次决策 Token       | ~3000     | **~500**     |
| 工具选择准确率          | 随工具数增加而下降 | **稳定**       |
| 单步延迟             | 2~5s      | **0.5~1.5s** |

## 十、Top-K 之后是否要 LLM 确认？

### 三种策略

| 策略            | 流程                    | 延迟       | 准确率 | 适用场景     |
|:--------------|:----------------------|:---------|:----|:---------|
| A：纯语义路由       | 路由直接选 Top-1 执行        | < 20ms   | 中   | 工具少、意图清晰 |
| B：路由 + LLM 确认 | 路由筛 Top-K → LLM 从候选中选 | 0.5~1.5s | 高   | 工具多、容错低  |
| C：分层策略（推荐）    | 高置信度走 A，低置信度走 B       | 自适应      | 高   | 生产环境     |

### LLM 确认的真正价值

LLM 确认不是“重新选”，而是做语义路由做不了的事：

| 语义路由能做的      | 语义路由做不了的（需要 LLM） |
|:-------------|:-----------------|
| 根据意图描述匹配工具描述 | 理解完整上下文中的隐含约束    |
| 计算语义相似度      | 判断工具在当前场景下是否真的适用 |
| 快速筛选候选       | 生成正确的调用参数        |
| 处理标准意图       | 处理模糊、矛盾、边界情况     |

### 置信度差距（Score Gap）是关键指标

除了 Top-1 的绝对分数，**Top-1 与 Top-2 的差距**更能反映路由的确定性：

| 场景   | Top-1 分数 | Top-2 分数 | 差距   | 决策     |
|:-----|:---------|:---------|:-----|:-------|
| 明确   | 0.92     | 0.31     | 0.61 | 直接执行   |
| 较明确  | 0.85     | 0.72     | 0.13 | LLM 确认 |
| 模糊   | 0.65     | 0.63     | 0.02 | LLM 确认 |
| 无法判断 | 0.35     | 0.33     | 0.02 | 重新描述意图 |

### 分层路由实现



```python
def smart_route(intent_text: str, context: str = "") -> RouteResult:
    intent_emb = embed_model.encode([intent_text])
    sims = np.dot(intent_emb, tool_embeddings.T) / (
        np.linalg.norm(intent_emb) * np.linalg.norm(tool_embeddings, axis=1)
    )
    top_indices = np.argsort(sims[0])[-3:][::-1]
    top_score = float(sims[0][top_indices[0]])
    second_score = float(sims[0][top_indices[1]])
    score_gap = top_score - second_score
    
    if top_score > 0.85 and score_gap > 0.15:
        return RouteResult(tool_name=tool_names[top_indices[0]], route="auto_execute")
    elif top_score > 0.5:
        return RouteResult(tool_name="", route="llm_confirm")
    else:
        return RouteResult(tool_name="", route="re_route")
```

## 十一、在 Agent 架构中的集成点

### 1. Supervisor 路由决策

用 Jev 的 Choice 能力替代或辅助 LLM 路由，大幅降低路由延迟。

### 2. 工具调用安全门控

在工具执行前用 Noul 判断是否需要人工审批。有 `jevgate` 项目专门用于此场景，可在约 300ms 内自动批准大多数良性工具调用。

### 3. 输出质量验证

用 Score 对 LLM 回答进行快速打分，替代或辅助 LLM-as-Judge。

## 十二、定价与开源生态

### 定价

| 项目           | 价格                    |
|:-------------|:----------------------|
| **输入 Token** | **$0.042 / 百万 Token** |
| **输出 Token** | **免费**（不存在自回归生成过程）    |
| **单次决策成本**   | 约 **$0.0004**         |

新用户注册可获得 **$5 额度**（约 1.2 亿 Token）。

### 开源生态

| 项目                   | 说明                                                            |
|:---------------------|:--------------------------------------------------------------|
| **Minecraft Agent**  | GPT-6 Astra 规划 + Jev 选择动作，8 分 43 秒击败末影龙，仅花费 $0.01             |
| **daf-jev**          | 组合式 Python 工具包，含问题构建器、客户端、置信度门控、MCP 服务器                       |
| **jevlang**          | Python 决策工作流，`pip install jevlang`，定位“Python with a smart if” |
| **LLM2Jev**          | 将本地 LLM 适配为 Jev 兼容的决策引擎                                       |
| **fast-browser-use** | APUS 开源，基于 Jev 的浏览器自动化，全程离线、零 API 费用                          |

## 十三、局限性与注意事项

- **不生成文本**：无法写作、对话、生成代码
- **需要预定义 schema**：必须提前指定问题和答案格式
- **不擅长多步推理**：本质是“更聪明的 if 语句”
- **概率校准需验证**：官方基准显示约 **67.8%** 准确率，实际效果需在业务场景中验证
- **依赖任务拆分**：在单一复杂问题上表现可能不佳。有测试显示，将任务拆分为 5 个更窄的问题后，准确率从 62.6% 提升至 **95%**

## 十四、总结

| 问题                | 回答                                         |
|:------------------|:-------------------------------------------|
| Jev 是什么？          | 专为 Agent 决策层设计的结构化判断模型，不生成文本，只输出带校准概率的选项   |
| 为什么比 LLM 适合决策？    | 概率校准、格式绝对可靠、延迟低 20~200 倍、成本低 40~400 倍      |
| 回退 LLM 是否退回旧方案？   | 不是。只有 5~15% 请求回退，85~95% 走 Jev，成本和延迟差 4~7 倍 |
| 长期记忆是否让 Jev 优势消失？ | 不会。长期记忆提升准确率，但不改变单次推理的成本和延迟                |
| 阈值怎么确定？           | 用 `jevcal` 等工具在验证集上分桶校准，按动作风险设置差异化阈值       |
| 如何融入 Agent？       | LLM 规划 + Jev 执行层判断；ReAct + 语义路由；快慢双系统      |

**核心原则**：

> **LLM 负责“想”（规划、推理、生成），Jev 负责“判”（路由、校验、评分），你的代码负责“管”（根据置信度决定自动执行、回退 LLM 还是转人工）。
**

这个模式让系统在保持 LLM 强大推理能力的同时，把高频、重复的判断任务外包给 Jev，实现**成本降低 10~40 倍、延迟降低 20~200 倍**
的效果。
