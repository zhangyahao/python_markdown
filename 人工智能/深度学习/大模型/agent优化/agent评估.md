# Agent 评估实践指南

> 本文提供一套可执行的 Agent 评估实施方案，覆盖评估设计、环境搭建、指标计算、工具使用与结果分析。目标是为开发者提供从零开始构建
> Agent 评估流水线的技术参考。

---

## 1. 评估设计

### 1.1 确定评估目标

在开始评估前，需明确以下问题：

- 评估的是单智能体还是多智能体系统？
- 评估的任务类型是什么？（问答、工具调用、代码生成、网页操作等）
- 评估的核心维度有哪些？（成功率、效率、鲁棒性、安全性等）
- 评估结果用于什么目的？（模型选型、提示词优化、架构比较等）

### 1.2 选择评估数据集

根据任务类型选择或构建评估数据集。数据集应满足：

- 与目标场景分布一致
- 具有明确的任务输入和期望输出
- 每条样本应包含标准答案、参考轨迹或可自动判定的成功条件

可选项：

- 公开基准：AgentBench、SWE-bench、WebArena、ToolBench、GAIA
- 自建数据集：从生产日志中采样，由人工标注标准答案

### 1.3 定义成功条件

成功条件需明确且可自动判定。常见形式：

- 结构化输出与标准答案完全匹配
- 输出满足正则表达式或 JSON Schema
- 代码通过单元测试
- 网页任务满足最终状态条件
- 对话任务由 LLM-as-a-Judge 评分高于阈值

---

## 2. 评估环境搭建

### 2.1 选择评估框架

| 框架           | 适用场景                   | 特点              |
|--------------|------------------------|-----------------|
| LangSmith    | LangChain/LangGraph 生态 | 轨迹追踪、数据集管理、在线评估 |
| Langfuse     | 通用 LLM 应用              | 开源、自托管、成本追踪     |
| TruLens      | RAG 与 Agent            | 反馈函数、仪表盘        |
| RAGAS        | RAG 系统                 | 忠实度、相关性等指标      |
| OpenAI Evals | 通用                     | 评估集管理与自动化流程     |
| 自研脚本         | 自定义场景                  | 灵活但开发成本高        |

### 2.2 配置 Agent 运行环境

- 隔离执行环境：使用 Docker 或沙箱，避免 Agent 执行危险操作
- 工具模拟器：对于外部 API，搭建 Mock 服务或使用离线替代
- 轨迹记录：配置日志系统，记录每一步的输入、输出、工具调用、状态变化

### 2.3 准备评估数据

将评估数据集导入所选框架，或组织为 JSON/CSV 格式。字段建议包括：

```json
{
  "id": "sample_001",
  "input": "用户查询或任务描述",
  "expected_output": "标准答案或成功条件",
  "metadata": {
    "difficulty": "easy",
    "domain": "weather"
  }
}
```

------

## 3. 评估指标与计算

### 3.1 核心指标

| 指标          | 计算公式             | 说明        |
|:------------|:-----------------|:----------|
| 成功率         | 成功样本数 / 总样本数     | 最基础的完成度指标 |
| 平均轨迹长度      | Σ步数 / 样本数        | 衡量效率      |
| 工具调用精确率     | 正确工具调用次数 / 总调用次数 | 衡量工具选择能力  |
| 平均 Token 消耗 | ΣToken / 样本数     | 成本指标      |
| 平均延迟        | Σ耗时 / 样本数        | 性能指标      |

### 3.2 指标实现示例

使用 Python 统计成功率：



```python
def calculate_success_rate(results: list[dict]) -> float:
    success = sum(1 for r in results if r["success"])
    return success / len(results) if results else 0.0
```

使用 LangSmith 获取轨迹长度：

python

```
from langsmith import Client

client = Client()

def get_trajectory_length(run_id: str) -> int:
    run = client.read_run(run_id)
    return len(run.child_run_ids)
```

### 3.3 加权综合评分

对于多维度评估，可定义加权综合指标：



```text
综合得分 = w1 × 成功率 + w2 × (1 - 归一化轨迹长度) + w3 × 工具调用精确率
```

权重根据业务需求设定。

------

## 4. 评估执行

### 4.1 使用 LangSmith 进行评估



```python
from langsmith import Client
from langsmith.evaluation import evaluate

client = Client()

# 定义评估器
def correct_answer(root_run, example):
    # 比较 root_run 输出与标准答案
    expected = example.outputs["expected_output"]
    actual = root_run.outputs["answer"]
    return {"score": 1 if expected == actual else 0}

# 执行评估
results = evaluate(
    lambda inputs: run_agent(inputs),
    data="your_dataset_name",
    evaluators=[correct_answer],
    experiment_prefix="agent-eval"
)
```

### 4.2 使用 Langfuse 记录与评估



```python
from langfuse import Langfuse

langfuse = Langfuse()

# 记录轨迹
trace = langfuse.trace(name="agent_run")
trace.generation(name="llm_output", input=query, output=answer)

# 评分
trace.score(name="success", value=1)
```

### 4.3 自定义评估脚本



```python
import json
import time

def run_evaluation(agent, dataset):
    results = []
    for sample in dataset:
        start = time.time()
        try:
            output = agent.run(sample["input"])
            success = check_success(output, sample["expected_output"])
            trajectory = agent.get_trajectory()
            results.append({
                "id": sample["id"],
                "success": success,
                "output": output,
                "steps": len(trajectory),
                "time": time.time() - start
            })
        except Exception as e:
            results.append({
                "id": sample["id"],
                "success": False,
                "error": str(e),
                "steps": 0,
                "time": time.time() - start
            })
    return results
```

------

## 5. 结果分析与优化

### 5.1 失败模式分类

对失败的样本进行分类，常见类别：

- 工具选择错误
- 工具参数错误
- 推理逻辑错误
- 上下文丢失
- 超出最大步数限制
- 安全拦截

### 5.2 错误归因

基于轨迹数据定位失败环节：

- 是规划阶段出错还是执行阶段出错？
- 是工具本身的问题还是 Agent 使用不当？
- 是提示词缺陷还是模型能力不足？

### 5.3 迭代优化

根据评估结果进行调整：

- 优化提示词：补充工具说明、增加示例
- 调整工具设计：简化参数、增加校验
- 修改架构：引入反思机制、增加子智能体
- 更换模型：使用更强推理能力的 LLM
- 调整超参数：增加最大步数、调整温度

优化后重新执行评估，形成闭环。

------

## 6. 示例：评估一个工具调用 Agent

### 6.1 Agent 定义



```python
from langchain.agents import create_openai_functions_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-3.5-turbo")
tools = [search_tool, calculator_tool]

agent = create_openai_functions_agent(llm, tools, prompt)
```

### 6.2 评估数据集



```json
[
  {
    "id": "1",
    "input": "What is 25 * 4?",
    "expected_output": "100"
  },
  {
    "id": "2",
    "input": "Search for the weather in Paris today",
    "expected_output": "The weather in Paris is sunny"
  }
]
```

### 6.3 执行与评分



```python
from langchain.evaluation import load_evaluator

evaluator = load_evaluator("exact_match")

results = evaluate(
    agent.invoke,
    data="tool_agent_dataset",
    evaluators=[evaluator],
    experiment_prefix="tool-agent-v1"
)
```

### 6.4 结果输出



```python
for r in results:
    print(f"ID: {r['id']}, Score: {r['score']}")
```

------

## 7. 自动化与持续评估

- 将评估脚本集成到 CI/CD 流水线
- 每次 Agent 更新后自动触发评估
- 设置质量阈值，不达标则阻断发布
- 定期在真实生产流量中采样进行人工抽检

------

## 8. 总结

Agent 评估的实施包括评估设计、环境搭建、指标定义、执行评估、结果分析到持续优化。使用 LangSmith、Langfuse
等工具可大幅降低开发成本，同时需结合场景自定义成功条件和失败分析逻辑。评估不是一次性活动，而应作为 Agent 开发周期中的常态化环节。

