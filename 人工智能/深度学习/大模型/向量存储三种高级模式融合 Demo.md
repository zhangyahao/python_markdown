# 向量存储三种高级模式融合 Demo

> 该 Demo 整合父子查询、粗细分组与关键点 ID 三种模式，构建一个可运行的知识库检索流程。仅包含术语定义与代码实现。

## 1. 术语定义

| 术语     | 定义                                                                |
|--------|-------------------------------------------------------------------|
| 父子查询   | 将文档分割为子文档（小块）用于嵌入与检索，每个子文档在元数据中关联其父文档（章节或大块）。检索命中子文档后，返回父文档作为上下文。 |
| 粗细分组   | 建立两级索引：粗粒度集合存储文档摘要向量，用于快速定位相关文档；细粒度集合存储具体文本块向量，在候选文档内进行精确检索。      |
| 关键点 ID | 由"关键点短语 + 内容哈希"组成的唯一标识符，其中关键点通过 LLM 提取，哈希保证唯一性。                   |

## 2. 架构设计

- **粗粒度集合**：存储每个父文档的摘要向量，元数据包含父文档 ID。
- **细粒度集合**：存储子文档（文本块）向量，元数据包含父文档 ID 与关键点短语，ID 使用关键点 ID。
- **父文档集合**：存储完整父文档文本，供最终返回。
- **查询流程**：
    1. 查询向量在粗粒度集合中检索，得到 Top-K 个父文档 ID。
    2. 在细粒度集合中，限定这些父文档 ID，进行精确检索，得到 Top-N 个子文档。
    3. 根据子文档元数据中的父文档 ID，从父文档集合中取出完整父文档文本。
    4. 将父文档文本作为上下文返回。

## 3. 完整代码实现

```python
import hashlib
import re
import chromadb
from chromadb.utils import embedding_functions
from langchain_openai import ChatOpenAI

# 初始化 LLM（用于关键点提取与摘要生成）
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# 初始化嵌入函数  也可以使用本地安装的向量数据分析
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="YOUR_OPENAI_API_KEY",
    model_name="text-embedding-3-small"
)

# 初始化 ChromaDB 客户端（持久化模式）
client = chromadb.PersistentClient(path="./fusion_demo_db")

# 创建三个集合
coarse_collection = client.get_or_create_collection(
    name="coarse_summaries",
    embedding_function=openai_ef
)
fine_collection = client.get_or_create_collection(
    name="fine_chunks",
    embedding_function=openai_ef
)
parent_collection = client.get_or_create_collection(
    name="parents",
    embedding_function=openai_ef
)


# ---------- 工具函数 ----------

def extract_keypoint(chunk: str) -> str:
    """使用 LLM 提取文本块的关键点短语（不超过5个词）。"""
    prompt = f"请用不超过5个词概括以下文本的核心内容，只输出短语本身：\n\n{chunk}"
    response = llm.invoke(prompt)
    keypoint = response.content.strip()
    # 清洗为合法字符串（只保留中英文、数字、连字符、下划线）
    keypoint = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", keypoint)
    return keypoint


def generate_chunk_id(chunk: str, keypoint: str) -> str:
    """生成关键点 ID：关键点 + 内容哈希前8位。"""
    content_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()[:8]
    return f"{keypoint}-{content_hash}"


def generate_summary(parent_text: str) -> str:
    """使用 LLM 生成父文档的简短摘要。"""
    prompt = f"请用一句话概括以下文本的主旨：\n\n{parent_text}"
    response = llm.invoke(prompt)
    return response.content.strip()


# ---------- 数据准备 ----------

# 模拟长文档：两个父文档（章节）
parent_docs = [
    {
        "parent_id": "chapter_1",
        "text": "第一章 杭州旅游指南。杭州是中国著名的旅游城市，西湖是其标志性景点。西湖周边有断桥、雷峰塔等历史遗迹。游客还可以体验龙井茶文化。杭州美食包括东坡肉、西湖醋鱼等。"
    },
    {
        "parent_id": "chapter_2",
        "text": "第二章 股票投资基础。股票是股份公司所有权的凭证。投资者通过买卖股票获取收益。常见的股票指数有道琼斯、标普500等。投资股票需要关注公司基本面和技术分析。"
    }
]

# 模拟子文档（从父文档中分割出的文本块）
# 实际应用中应使用分割工具（如 RecursiveCharacterTextSplitter）
child_chunks = {
    "chapter_1": [
        "西湖是杭州最著名的景点，湖光山色美不胜收。",
        "断桥是西湖十景之一，传说白娘子与许仙在此相会。",
        "龙井茶是杭州特产，以色绿、香郁、味甘、形美著称。",
        "东坡肉是杭州传统名菜，肥而不腻，入口即化。"
    ],
    "chapter_2": [
        "股票代表对公司的所有权，是资本市场的主要投资工具。",
        "道琼斯工业平均指数是美国最重要的股票指数之一。",
        "技术分析通过研究历史价格和成交量来预测股票走势。"
    ]
}

# ---------- 存储数据 ----------

# 1. 存储父文档
parent_ids = [doc["parent_id"] for doc in parent_docs]
parent_texts = [doc["text"] for doc in parent_docs]
parent_collection.add(
    documents=parent_texts,
    ids=parent_ids
)

# 2. 为每个父文档生成摘要并存入粗粒度集合
coarse_ids = []
coarse_docs = []
coarse_metas = []
for doc in parent_docs:
    summary = generate_summary(doc["text"])
    coarse_ids.append(doc["parent_id"])
    coarse_docs.append(summary)
    coarse_metas.append({"parent_id": doc["parent_id"]})

coarse_collection.add(
    documents=coarse_docs,
    ids=coarse_ids,
    metadatas=coarse_metas
)

# 3. 存储子文档到细粒度集合，使用关键点 ID
fine_ids = []
fine_docs = []
fine_metas = []
for parent_id, chunks in child_chunks.items():
    for chunk in chunks:
        keypoint = extract_keypoint(chunk)
        chunk_id = generate_chunk_id(chunk, keypoint)
        fine_ids.append(chunk_id)
        fine_docs.append(chunk)
        fine_metas.append({
            "parent_id": parent_id,
            "keypoint": keypoint
        })

fine_collection.add(
    documents=fine_docs,
    ids=fine_ids,
    metadatas=fine_metas
)

print("数据存储完成：")
print(f"父文档数：{parent_collection.count()}")
print(f"粗粒度摘要数：{coarse_collection.count()}")
print(f"细粒度块数：{fine_collection.count()}")


# ---------- 查询流程 ----------

def fusion_query(user_query: str, coarse_top_k: int = 2, fine_top_n: int = 3):
    """
    融合三种模式的查询：
    1. 粗粒度检索相关父文档
    2. 在候选父文档内进行细粒度检索
    3. 返回命中的父文档全文作为上下文
    """
    # Step 1: 粗粒度检索
    coarse_results = coarse_collection.query(
        query_texts=[user_query],
        n_results=coarse_top_k,
        include=["metadatas"]
    )
    parent_ids_candidates = [meta["parent_id"] for meta in coarse_results["metadatas"][0]]
    print(f"粗粒度候选父文档ID：{parent_ids_candidates}")

    # Step 2: 细粒度检索，限定在候选父文档内
    where_filter = {"parent_id": {"$in": parent_ids_candidates}}
    fine_results = fine_collection.query(
        query_texts=[user_query],
        n_results=fine_top_n,
        where=where_filter,
        include=["metadatas", "documents", "distances"]
    )
    print(f"细粒度命中块数：{len(fine_results['documents'][0])}")
    for doc, meta, dist in zip(fine_results["documents"][0], fine_results["metadatas"][0],
                               fine_results["distances"][0]):
        print(f"  - 块ID：{meta['keypoint']}，距离：{dist:.4f}，内容：{doc[:50]}...")

    # Step 3: 根据命中块的父文档ID，提取父文档全文
    if fine_results["metadatas"][0]:
        # 取第一个命中块的父文档ID（实际可对所有命中块聚合）
        target_parent_id = fine_results["metadatas"][0][0]["parent_id"]
        parent_result = parent_collection.get(ids=[target_parent_id])
        return parent_result["documents"][0]
    else:
        return "未找到相关文档"


# 测试查询
user_query = "我想了解杭州西湖的景点和美食"
context = fusion_query(user_query)
print("\n=== 最终返回的父文档上下文 ===")
print(context)
```

## 4. 运行说明

1. 安装依赖：

bash

```
pip install chromadb langchain langchain-openai
```

1. 设置环境变量或直接在代码中填入有效的 `OPENAI_API_KEY`。
2. 运行脚本，将完成数据存储并执行一次示例查询。

## 5. 关键点说明

- **关键点 ID** 在存储子文档时生成，并保存于元数据中，便于追踪。
- **粗细分组** 通过两个集合实现：`coarse_summaries` 用于初筛，`fine_chunks` 用于精搜。
- **父子查询** 在查询的最后一步，通过父文档集合返回完整章节文本，提供充分上下文。
- 三个模式互不干扰，共同提升了检索的效率和上下文完整性。