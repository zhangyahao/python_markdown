# LangChain + DeepSeek/OpenAI API 开发实践指南

> 本指南按照从零到一的开发顺序编排，每个步骤均给出可直接运行的代码示例。  
> 基于 LangChain 框架与 DeepSeek API（兼容 OpenAI 格式），涵盖环境配置、基础调用、参数调优、提示词工程、多轮对话、RAG、Agent
> 等核心开发模式。

---

## 第一步：环境准备与第一个 API 调用

### 1.1 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境（推荐 Python 3.9+）
python -m venv langchain_env

# 激活环境（Windows）
langchain_env\Scripts\activate
# 激活环境（Linux/Mac）
source langchain_env/bin/activate

# 安装核心依赖
pip install langchain openai python-dotenv tiktoken
```

### 1.2 配置 API Key

在项目根目录创建 `.env` 文件：

```env
api_key=sk-your-deepseek-or-openai-api-key
```

### 1.3 实现最小调用封装（不使用 LangChain，直接调用 API）

```python
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv('api_key'),
    base_url="https://api.deepseek.com"  # DeepSeek 端点；如用 OpenAI 则去掉此参数
)


def simple_invoke(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1
    )
    return response.choices[0].message.content


print(simple_invoke("请用一句话介绍 LangChain"))
```

### 1.4 使用 LangChain 的 ChatOpenAI 封装（推荐）

```python
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv('api_key'),
    openai_api_base="https://api.deepseek.com",  # 如使用 OpenAI 则注释此行
    temperature=1
)

response = llm.invoke("请用一句话介绍 LangChain")
print(response.content)
```

---

## 第二步：Token 计数与成本估算

在使用 API 前，学会计算文本的 token 数量，以便控制预算和上下文长度。

```python
import tiktoken

enc = tiktoken.get_encoding('cl100k_base')  # 适用于 GPT-4/DeepSeek 等模型

text = '''
LangChain 是一个用于开发 LLM 应用的框架，它简化了与模型交互、检索外部数据、多轮对话等复杂任务。
'''

tokens = enc.encode(text)
print(f"文本长度: {len(text)} 字符")
print(f"Token 数量: {len(tokens)}")
print(f"Token 列表（前20个）: {tokens[:20]}")
```

---

## 第三步：理解核心参数 —— 温度与 top_p

### 3.1 温度参数（temperature）实验

温度越低 → 输出越确定；温度越高 → 输出越随机多样。

```python
prompt = "续写：今天天气真好，"

for temp in [0, 0.5, 1.5]:
    print(f"\n--- temperature = {temp} ---")
    for _ in range(2):
        response = llm.invoke(prompt, temperature=temp)
        print(response.content)
```

### 3.2 top_p 采样（核采样）实验

top_p 从累积概率达到该值的词中采样，值越小候选词越少。

```python
prompt = "随机推荐一种颜色，只输出颜色名称："

for p in [0.2, 0.5, 0.9]:
    print(f"\n=== top_p = {p} ===")
    for _ in range(3):
        response = llm.invoke(prompt, top_p=p)
        print(response.content)
```

### 3.3 温度参数的数学原理

```python
import math


def softmax_with_temperature(logits, T):
    """模拟 softmax 函数受温度影响"""
    exp_logits = [math.e ** (l / T) for l in logits]
    total = sum(exp_logits)
    return [e / total for e in exp_logits]


# 假设模型对三个词的原始输出分数为 [2.0, 1.0, 0.5]
logits = [2.0, 1.0, 0.5]

print("T=0.3（极低）:", softmax_with_temperature(logits, 0.3))  # 最高分接近1
print("T=1.0（正常）:", softmax_with_temperature(logits, 1.0))
print("T=5.0（很高）:", softmax_with_temperature(logits, 5.0))  # 分布趋于均匀
```

---

## 第四步：使用停止符（stop）控制生成终点

遇到指定字符串时立即停止生成，避免模型“说太多”。

```python
prompt = "写一首五言绝句，主题是春天。"

response = llm.invoke(prompt, stop=["。", "\n\n"])  # 遇到句号或空行就停止
print(response.content)
```

---

## 第五步：提示词模板（PromptTemplate）

### 5.1 为什么需要模板？

原生字符串的 `format()` 只能一次性填充，无法保留占位符。LangChain 的 `PromptTemplate` 支持部分传参。

### 5.2 基础用法

```python
from langchain_core.prompts import PromptTemplate

template = """
你是一个天气助手。请告诉我{city}在{date}的天气。
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["city", "date"],
    partial_variables={"date": "明天"}  # 预设 date 为“明天”
)

# 只需提供 city 即可
final_prompt = prompt.format(city="北京")
print(final_prompt)

# 也可以覆盖预设值
final_prompt2 = prompt.format(city="上海", date="后天")
print(final_prompt2)
```

### 5.3 使用 `partial()` 动态生成子模板

```python
prompt = PromptTemplate(
    template=template,
    input_variables=["city", "date"]
)

# 生成特化的模板
only_city = prompt.partial(date="今天")
only_date = prompt.partial(city="广州")

print(only_city.format(city="深圳"))
print(only_date.format(date="下周一"))
```

---

## 第六步：系统角色（System Role）与角色扮演

通过设置系统消息，让模型扮演特定角色，显著改变回答风格。

```python
system_roles = [
    "你是一名专业的美食评论家，擅长评价菜品的色香味。",
    "你是一名营养师，从健康角度分析食物。",
    "You are a helpful assistant."
]

prompt = "请评价一下北京小吃——豆汁。"

for role in system_roles:
    print(f"\n=== 角色：{role} ===")
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": prompt}
    ]
    response = llm.invoke(messages)
    print(response.content)
```

---

## 第七步：对话消息结构（System / Human / AI Message）

### 7.1 显式构造消息列表

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage(content="你是一个数学专家。"),
    HumanMessage(content="请计算 123 + 456 = ?"),
    AIMessage(content="计算结果为 579。")
]

response = llm.invoke(messages)
print(response.content)
```

### 7.2 使用 ChatPromptTemplate 生成消息

```python
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

system_temp = SystemMessagePromptTemplate.from_template("你是一位{role}专家。")
user_temp = HumanMessagePromptTemplate.from_template("{user_question}")

chat_template = ChatPromptTemplate.from_messages([system_temp, user_temp])

messages = chat_template.format_messages(role="数学", user_question="解方程 2x + 5 = 13")
response = llm.invoke(messages)
print(response.content)
```

---

## 第八步：多轮对话与记忆管理（滑动窗口）

维持最近 N 条消息，超出则丢弃最早的对话，实现有限记忆。

```python
from langchain_core.messages import HumanMessage, AIMessage

# 初始化对话记录（保留最近 6 条）
history = []


def chat_loop(memory_size=6):
    print("开始对话（输入 '0' 退出）")
    while True:
        user_input = input("你: ")
        if user_input == '0':
            break

        # 添加用户消息
        history.append(HumanMessage(content=user_input))
        if len(history) > memory_size:
            history.pop(0)

        # 调用模型
        response = llm.invoke(history)

        # 添加 AI 回复
        history.append(AIMessage(content=response.content))
        if len(history) > memory_size:
            history.pop(0)

        print(f"AI: {response.content}")


# 启动对话
chat_loop()
```

---

## 第九步：检索增强生成（RAG）—— 让模型读取你的文档

### 9.1 完整 RAG 流程（从文档到问答）

```bash
# 需要额外安装向量数据库和文档加载器
pip install faiss-cpu pypdf langchain-community
```

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# 1. 加载 PDF 文档
loader = PyPDFLoader("your_document.pdf")
documents = loader.load()

# 2. 分割文本（块大小500，重叠50）
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

# 3. 创建向量存储
embeddings = OpenAIEmbeddings()  # 需要 OpenAI embedding 或 DeepSeek 兼容的
vectorstore = FAISS.from_documents(docs, embeddings)

# 4. 构建检索问答链
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # 直接将检索到的文本填入 prompt
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
)

# 5. 提问
query = "文档中提到了哪些关键参数？"
answer = qa_chain.invoke(query)
print(answer["result"])
```

### 9.2 优化策略：上下文压缩（减少无用信息）

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

compressor = LLMChainExtractor.from_llm(llm)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vectorstore.as_retriever()
)

qa_compressed = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=compression_retriever
)
```

---

## 第十步：Agent 智能体 —— 让模型自主调用工具

### 10.1 定义工具并创建 Agent

```python
from langchain.agents import create_agent
from langchain.tools import tool


@tool
def get_weather(city: str) -> str:
    """获取指定城市当前天气（模拟）"""
    # 实际可调用 API
    return f"{city}今天天气晴朗，气温22°C。"


@tool
def calculate(expr: str) -> str:
    """计算数学表达式结果"""
    try:
        return str(eval(expr))
    except:
        return "表达式无效"


agent = create_agent(
    model=llm,
    tools=[get_weather, calculate],
    system_prompt="你是一个智能助手，可以查询天气和计算数学表达式。"
)

# 调用 Agent
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "北京天气如何？另外，帮我算 25 * 4 + 10"}
    ]
})
print(result)
```

### 10.2 使用 LCEL 手动编排工具调用（简单场景）

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda


@tool
def google_search(query: str) -> str:
    return f"模拟搜索结果：关于 {query} 的信息..."


chain = RunnableLambda(lambda q: google_search.invoke(q)) | llm
response = chain.invoke("LangChain 最新版本")
```

---

## 第十一步：流式输出（Streaming）—— 提升响应体验

### 11.1 同步流式

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("讲一个关于{topic}的短故事")
chain = prompt | llm

for chunk in chain.stream({"topic": "流浪猫"}):
    print(chunk.content, end="", flush=True)  # 逐字打印
```

### 11.2 异步流式（适用于 FastAPI 等）

```python
import asyncio
from langchain_core.prompts import ChatPromptTemplate


async def async_stream():
    prompt = ChatPromptTemplate.from_template("写一首关于{season}的诗")
    chain = prompt | llm
    async for chunk in chain.astream({"season": "秋天"}):
        print(chunk.content, end="", flush=True)


asyncio.run(async_stream())
```

---

## 第十二步：部署与监控建议

### 12.1 使用 LangServe 将链部署为 API

```bash
pip install langserve
```

```python
# server.py
from langserve import add_routes
from fastapi import FastAPI
from langchain_core.runnables import RunnableLambda

app = FastAPI()
chain = RunnableLambda(lambda x: f"收到: {x}")
add_routes(app, chain, path="/my-chain")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 12.2 使用 LangSmith 进行调试与追踪

设置环境变量开启 LangSmith 追踪：

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=ls_xxx   # 从 langsmith 平台获取
```

然后在代码中自动记录所有调用链。

---

## 总结：开发顺序一览表

| 阶段        | 内容                       | 对应步骤  |
|-----------|--------------------------|-------|
| 1️⃣ 基础    | 环境配置、首次调用                | 第一步   |
| 2️⃣ 成本控制  | Token 计数                 | 第二步   |
| 3️⃣ 参数调优  | temperature, top_p, stop | 第三、四步 |
| 4️⃣ 提示词工程 | 模板、系统角色                  | 第五、六步 |
| 5️⃣ 对话管理  | 消息结构、多轮记忆                | 第七、八步 |
| 6️⃣ 知识增强  | RAG（检索+生成）               | 第九步   |
| 7️⃣ 自主决策  | Agent + 工具调用             | 第十步   |
| 8️⃣ 交互体验  | 流式输出                     | 第十一步  |
| 9️⃣ 生产部署  | 部署、监控                    | 第十二步  |

按此顺序逐步实践，即可掌握 LangChain + DeepSeek/OpenAI API 从零到生产级的核心开发技能。
