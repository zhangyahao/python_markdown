# OpenAI API 核心操作与开发指南

> 本指南专注于 OpenAI Chat Completions API 的常用操作和最佳实践，覆盖从环境配置、参数调优到工具调用、流式响应等核心功能。基于当前
> OpenAI 最新 API 端点 **`https://api.openai.com/v1/chat/completions`** 编写，Python 示例均使用官方 `openai` 库。

---

## 一、准备工作

### 1.1 注册账号与获取 API Key

访问 [OpenAI 开发者平台](https://platform.openai.com)，完成注册并设置支付方式后，在 **API Keys** 页面生成密钥。

### 1.2 安装与配置

Python 环境建议 3.9+，安装官方库后添加 API Key 至环境变量：

```bash
pip install openai

export OPENAI_API_KEY="sk-xxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    # 多组织用户可指定 organization 参数
    organization="org-xxx"
)
```

### 1.3 快速测试

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",  # 或 gpt-4o
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

输出中包含 `finish_reason: "stop"` 表示生成完整，若值为 `length` 则因达到 `max_tokens` 截断。

---

## 二、核心参数详解

### 2.1 参数速查表

| 参数                  | 类型    | 默认值 | 范围     | 作用              |
|---------------------|-------|-----|--------|-----------------|
| `temperature`       | float | 1   | 0–2    | 控制随机性，值越高越多样    |
| `top_p`             | float | 1   | 0–1    | 核采样，限制候选词范围     |
| `max_tokens`        | int   | ∞   | —      | 限制输出长度          |
| `presence_penalty`  | float | 0   | -2 到 2 | 惩罚重复话题，鼓励引入新主题  |
| `frequency_penalty` | float | 0   | -2 到 2 | 惩罚重复用词，抑制“词穷”现象 |
| `n`                 | int   | 1   | —      | 单次请求生成 n 个回复    |

> 💡 **建议**：修改 `temperature` 和 `top_p` 时可先固定其中一个，不宜频繁调取。事实问答类任务推荐低温度，创意生成类则适当提高。

---

## 三、核心 API 操作

### 3.1 文本对话

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一位专业的技术文档撰写专家。"},
        {"role": "user", "content": "请解释一下什么是API"}
    ],
    temperature=0.7
)
```

### 3.2 多轮对话

```python
messages = [
    {"role": "system", "content": "你是一个有耐心的AI助手"},
    {"role": "user", "content": "昨天是星期三，那明天是星期几？"},
    {"role": "assistant", "content": "明天是星期五。"},
    {"role": "user", "content": "那后天呢？"}
]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)
```

### 3.3 流式输出

```python
stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "讲一个简短的笑话"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

此异步逐字输出可极大提升交互体验[5†L10-L13][18†L22-L25]。

### 3.4 处理 JSON 或结构化输出

通过 `response_format` 强制模型返回合法 JSON：

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "提取以下文本中的姓名、公司和职位"}],
    response_format={"type": "json_object"}
)
```

### 3.5 同时生成多个回复

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "推荐一个周末活动"}],
    n=3  # 一次性生成 3 个候选回复
)
```

### 3.6 惩罚参数调优示例

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "为何天空是蓝色的"}],
    presence_penalty=0.6,  # 倾向于引入新论点
    frequency_penalty=0.3  # 抑制流行词重复出现
)
```

### 3.7 控制停止符

设置 `stop` 可设定结束标识：

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇介绍 Python 的短文"}],
    stop=["。", "\n\n"],  # 遇见句号或空行时停止
    max_tokens=100
)
```

### 3.8 高级参数组合配置示例

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the FIFA World Cup in 2010?"}
    ],
    temperature=1.0,
    top_p=0.9,
    n=2,
    max_tokens=200,
    presence_penalty=0.6,
    frequency_penalty=0.3,
    stream=False
    # stop=["\n"]
)
```

---

## 四、工具调用 (Tools / Function Calling)

OpenAI 已不推荐旧的 `functions` 与 `function_call` 参数，统一采用 **`tools`** 与 **`tool_choice`**。该功能让模型识别用户意图，返回
**JSON 格式函数调用而非纯文本**。

### 4.1 基本流程

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "获取指定城市的实时天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"}
            },
            "required": ["city"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "北京的天气怎么样？"}],
    tools=tools,
    tool_choice="auto"
)

if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    # 此处调用本地函数执行相应操作
```

### 4.2 完整调用示例

```python
import json
from openai import OpenAI

client = OpenAI(api_key="sk-xxx")

# 定义工具（JSON Schema）
tools_weather = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather of a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"}
            },
            "required": ["city"]
        }
    }
}]


def get_weather_info(city):
    # 模拟 API 调用
    return f"{city}: sunny, 23°C"


response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What's the weather in Tokyo today?"}],
    tools=tools_weather,
    tool_choice="auto"
)

# 解析并执行工具
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    weather_result = get_weather_info(args["city"])
    print(weather_result)
```

---

## 五、Embeddings 与 RAG

### 5.1 生成 Embeddings

```python
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="这是一个需要向量化的文本"
)
vector = response.data[0].embedding
```

### 5.2 RAG 应用架构

1. **知识准备**：将私有文档划分片段→调用 Embedding 存入向量数据库。
2. **检索增强**：用户提问→向量检索相似上下文→**将相关片段注入 prompt**。
3. **生成回答**：发送 prompt + 检索结果至 Chat Completions 模型，获得事实增强的回答。

常见向量库方案：FAISS（推荐试验阶段）、Pinecone（生产用）、Chroma（本地轻量级）[22†L4-L8]。

---

## 六、常见错误与应对策略

### 6.1 错误速查表

| 状态码 | 类型                  | 解决方案                      |
|-----|---------------------|---------------------------|
| 401 | 无效身份验证 / API Key 错误 | 检查 `Authorization` 头或环境变量 |
| 429 | 触发速率限制              | 降低 QPS，更换更高层级套餐           |
| 429 | 超额消费限额              | 提升配额上限或充值                 |
| 400 | 格式参数校验失败            | 检查 messages 结构是否规范        |
| 500 | 服务端异常               | 稍等重试                      |
| 503 | 引擎过载                | 稍后重试                      |

### 6.2 退避重试示例

```python
import time, random


def call_with_retry(max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(...)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** attempt + random.random(), 8)
            time.sleep(wait)
```

### 6.3 安全最佳实践

- API Key 务必存放于环境变量或密钥管理系统；
- Embedding、tools 等高级功能会消耗更多 token，提前估算成本；
- 测试阶段可用 **`gpt-4o-mini`** 降低了开销，并启用 **`logprobs`** 检查模型置信度。

---

## 七、一般性提示设计准则

在执行具体的代码开发之前，可参考 OpenAI 官方建议的 Prompt 前序原则，针对特定任务改善输出稳定性（如客服指令式对话）：

- **优先列出目标与限制**：“目标：解决客户需求 → 规则：仅提及内部政策”。
- **明确停止条件**：当检索结果足够支撑核心应答时，不再进行额外搜索。
- **纳入代码时标注验证方式**：例如“修改后执行单元测试”。

遵循这些思路可有效降低模型幻觉与无效搜索，提升应用可复现性。

---

*文档基于 OpenAI 官方 API 与当前主流实践整理，适用于 gpt-4o / gpt-4o-mini 等模型，部分示例可无缝迁移至 Azure OpenAI 服务。*
