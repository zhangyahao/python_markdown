本 Markdown 文档整合了 **TokenPilot: Cache-Efficient Context Management for LLM Agents** 论文的核心思想、关键方法、实验结果，以及一个
**完全自包含的、不依赖 LightMem2 的实践 Demo**，展示如何将论文思想落地为可用代码。

------

## 1. 论文核心思想与贡献

### 1.1 背景与问题

在长期运行的 LLM Agent 中，每轮交互都会累积执行轨迹（用户输入、思考过程、工具调用及返回），导致上下文长度无界增长，推理成本急剧上升（输入
Token 可能膨胀至数十万）。现有上下文压缩方法（如剪枝、摘要、分页）虽然减少了 Token 数量，但**破坏了 Prompt 前缀的连续性**
，使得硬件层面的 **KV Cache 无法复用**，预填充（Prefill）成本反而增加，最终抵消了文本缩减带来的收益。

论文首次明确指出并系统研究了这一矛盾：**文本稀疏性优化与缓存连续性之间存在根本性权衡**。

### 1.2 核心贡献

1. **揭示关键权衡**：通过实验量化了文本压缩与缓存命中率的对立关系。
2. **提出 TokenPilot 框架**：一个双粒度上下文管理方案，兼顾**文本缩减**与**缓存对齐**。
    - **全局层（Ingestion-Aware Compaction）**：在信息进入上下文前进行稳定化与结构化压缩。
    - **局部层（Lifecycle-Aware Eviction）**：在上下文内部按生命周期批量驱逐低效用片段。
3. **显著降本增效**：在 PinchBench 和 Claw-Eval 上实现 **最高 87% 的成本降低**，同时保持甚至提升任务准确率。
4. **实际部署验证**：已集成至 LightRSI 项目，并在多款主流 Agent 框架（OpenClaw, Codex CLI, Claude Code）中得到验证。

------

## 2. 方法详解：双粒度上下文管理

### 2.1 全局层：感知摄入的压缩 (Ingestion-Aware Compaction)

该层在**外部数据进入上下文之前**进行预处理，目的是**最大化前缀的字节级一致性**。

- **消息空间划分**
  将消息分为两类：
    - **内部意图消息（Ω_int）**：系统提示、Agent 思维链、工具调用序列等——具有高内在效用密度，应尽量保留。
    - **环境反馈消息（Ω_env）**：工具返回的 HTML、日志、JSON 等——往往包含大量冗余噪声。
- **前缀稳定化（Prefix Stabilization）**
  通过规范化算子，将运行时易变字段（如时间戳、文件路径、会话 ID）替换为静态占位符（如 `[WORKSPACE]`、`[TIMESTAMP]`）。这确保跨请求的
  Prompt 前缀（包含 System Prompt 和工具定义）字节级一致，使冷启动转为热启动，大幅提高缓存命中率。
- **观测缩减（Observation Trimming）**
  对环境消息应用确定性缩减策略（例如只提取 HTML 正文、保留日志首尾行），并建立**外部工件注册表**
  （以内容哈希为索引），若后续需要完整内容，可通过轻量级恢复工具动态召回。

### 2.2 局部层：生命周期感知驱逐 (Lifecycle-Aware Eviction)

该层在上下文内部动态调整历史窗口，核心是**状态管理与批量调度**。

- **三阶段状态管理**
  每个上下文段（一个完整的交互回合）维护三种状态：
    - `active`：刚产生，对当前任务很可能有用。
    - `completed`：其所依赖的原子任务已完成，不再被直接需要。
    - `evictable`：残差效用归零，可被清理。
- **保守的批处理调度**
  为避免每轮都修改上下文布局破坏缓存连续性，TokenPilot 以**固定批次（如每 3 轮）**触发状态评估和清理，而非每步执行。状态转换遵循严格流水线：
  `active → completed → evictable`，只有在效用彻底消失后才执行结构删除。
- **轻量级效用估计器**
  采用 Qwen3.5-35B-A3B 作为零样本验证器，评估每个片段的残差效用，总运行成本低于 $0.03。

------

## 3. 实验结果与关键发现

### 3.1 主要基准测试结果

| 模式   | 基准         | TokenPilot 成本 | 成本降幅 | 性能（准确率/得分）   |
|:-----|:-----------|:--------------|:-----|:-------------|
| 隔离模式 | PinchBench | **$3.22**     | 61%  | **81.0**（最高） |
| 隔离模式 | Claw-Eval  | **$2.27**     | 56%  | **63.1**（最高） |
| 连续模式 | PinchBench | **$2.79**     | 61%  | **81.3**（最高） |
| 连续模式 | Claw-Eval  | **$10.58**    | 87%  | **60.8**（次高） |

在连续模式下，Vanilla 基线成本高达 $81.52，TokenPilot 将其削减至 $10.58。

### 3.2 消融实验揭示的机制

| 配置      | PinchBench 连续模式成本 | 缓存未命中 (M) |
|:--------|:------------------|:----------|
| Vanilla | $7.24             | 5.943     |
| + 全局层   | $4.22             | 1.589     |
| + 局部层   | **$2.79**         | 1.549     |

- **全局层**通过规则剪枝和前缀稳定化，缓存未命中从 5.943M 降至 1.589M。
- **局部层**进一步将缓存命中 Token 从 26.716M 降至 8.551M（减少 65.0%）。

### 3.3 关键洞察

- **前缀稳定化是基石**：仅此一项即可将 PinchBench 成本从 $8.31 降至 $4.35，缓存命中率从 38.7% 跃升至 79.2%。
- **恢复工具不可或缺**：禁用恢复工具会导致性能下降（81.0→77.1）且成本上升。
- **最优批大小为 3**：B=3*B*=3 在防止内存膨胀与保障缓存复用间取得最佳平衡。

------

## 4. 自实现 Demo：从论文到代码

下面我们提供一个**完整的、零依赖（除 tiktoken 外）的 Python 实现**，完全复现 TokenPilot 的核心机制。它不依赖
LightMem2，可直接运行并观察效果。

### 4.1 设计目标

- 实现**前缀稳定化**：固定 System Prompt 和工具定义，动态字段占位符替换。
- 实现**结构化压缩**：对 HTML 和日志进行智能截断，并存储完整内容至外部注册表。
- 实现**生命周期状态管理**：为每个回合维护 `active/completed/evictable` 状态。
- 实现**批量驱逐**：每 N 轮触发一次清理，且从尾部删除以保护前缀。
- 提供**统计报告**：输出 Token 总数、缓存命中预估、各状态片段数量。

### 4.2 核心模块实现

#### 4.2.1 状态与片段定义

```python
from enum import Enum
from typing import List, Dict


class SegmentState(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EVICTABLE = "evictable"


class ContextSegment:
    def __init__(self, turn_id, user_msg, assistant_msg, tool_calls, tool_results):
        self.turn_id = turn_id
        self.user_msg = user_msg
        self.assistant_msg = assistant_msg
        self.tool_calls = tool_calls
        self.tool_results = tool_results  # 已压缩
        self.state = SegmentState.ACTIVE
```

#### 4.2.2 管理器主类

```python
import re, json
import tiktoken


class TokenPilotContextManager:
    def __init__(self, system_prompt, tools, eviction_interval=3):
        self.system_prompt = system_prompt
        self.tools = tools
        self.static_prefix = self._build_static_prefix()
        self.segments = []
        self.eviction_interval = eviction_interval
        self.turn_counter = 0
        self.external_store = {}  # 存储完整原文

    def _build_static_prefix(self):
        # 占位符替换
        stable_system = self.system_prompt.replace("{current_time}", "[CURRENT_TIME]")
            .replace("{workspace}", "[WORKSPACE]")
        tools_text = json.dumps(self.tools, sort_keys=True, ensure_ascii=False)
        return [
            {"role": "system", "content": stable_system},
            {"role": "system", "content": f"Tools:\n{tools_text}"}
        ]
```

#### 4.2.3 压缩函数（HTML/日志/普通文本）

```python
def _compress_html(self, html):
    title = re.search(r"<title>(.*?)</title>", html, re.I)
    title_text = title.group(1) if title else "No Title"
    clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL)
    body = re.search(r"<body.*?>(.*?)</body>", clean, re.DOTALL | re.I)
    body_text = body.group(1) if body else clean[:200]
    summary = body_text[:200].strip()
    store_id = f"html_{hash(html) % 1000000}"
    self.external_store[store_id] = html
    return f"[HTML_SUMMARY] Title: {title_text}\n{summary}... [FULL_ID:{store_id}]"


def _compress_log(self, log):
    lines = log.splitlines()
    if len(lines) > 50:
        compressed = "\n".join(lines[:10] + ["... (truncated) ..."] + lines[-10:])
    else:
        compressed = log
    store_id = f"log_{hash(log) % 1000000}"
    self.external_store[store_id] = log
    return compressed + f"\n[FULL_ID:{store_id}]"
```

#### 4.2.4 添加回合与状态更新

```python
def add_turn(self, user_msg, assistant_msg, tool_calls, tool_results, tool_content_types=None):
    if tool_content_types is None:
        tool_content_types = ["text"] * len(tool_results)
    compressed_results = [
        self.compress_tool_output(res, ctype)
        for res, ctype in zip(tool_results, tool_content_types)
    ]
    segment = ContextSegment(self.turn_counter, user_msg, assistant_msg,
                             tool_calls, compressed_results)
    self.segments.append(segment)
    self.turn_counter += 1

    if self.turn_counter % self.eviction_interval == 0:
        self._evict_expired()
    self._update_states()


def _update_states(self):
    # 保留最近2轮active，其余先变completed，更老的变evictable
    for i, seg in enumerate(self.segments):
        if i >= len(self.segments) - 2:
            seg.state = SegmentState.ACTIVE
        else:
            if seg.state == SegmentState.ACTIVE:
                seg.state = SegmentState.COMPLETED
            if (self.turn_counter - seg.turn_id) > self.eviction_interval:
                seg.state = SegmentState.EVICTABLE
```

#### 4.2.5 批量驱逐（从尾部删除）

```python
def _evict_expired(self):
    new_segments = []
    kept_any = False
    for seg in reversed(self.segments):
        if seg.state == SegmentState.EVICTABLE and kept_any:
            continue  # 跳过，即删除
        else:
            new_segments.insert(0, seg)
            kept_any = True
    self.segments = new_segments
```

#### 4.2.6 构建 Prompt 与统计

```python
def build_prompt(self):
    messages = self.static_prefix.copy()
    for seg in self.segments:
        if seg.state == SegmentState.EVICTABLE:
            continue
        messages.append({"role": "user", "content": seg.user_msg})
        if seg.tool_calls:
            tool_calls_text = json.dumps(seg.tool_calls, ensure_ascii=False)
            messages.append({"role": "assistant",
                             "content": f"{seg.assistant_msg}\nTool calls: {tool_calls_text}"})
        else:
            messages.append({"role": "assistant", "content": seg.assistant_msg})
        for result in seg.tool_results:
            messages.append({"role": "tool", "content": result})
    return messages


def estimate_tokens(self, messages):
    enc = tiktoken.get_encoding("cl100k_base")
    text = json.dumps(messages, ensure_ascii=False)
    return len(enc.encode(text))


def get_stats(self):
    msgs = self.build_prompt()
    total = self.estimate_tokens(msgs)
    prefix_tokens = self.estimate_tokens(self.static_prefix)
    return {
        "total_segments": len(self.segments),
        "active": sum(1 for s in self.segments if s.state == SegmentState.ACTIVE),
        "completed": sum(1 for s in self.segments if s.state == SegmentState.COMPLETED),
        "evictable": sum(1 for s in self.segments if s.state == SegmentState.EVICTABLE),
        "total_tokens": total,
        "cache_hit_tokens": prefix_tokens,  # 前缀固定可缓存
        "cache_miss_tokens": total - prefix_tokens
    }
```

### 4.3 完整代码（可直接运行）

将上述片段整合为一个完整的 Python 文件，名为 `tokenpilot_demo.py`。下面给出全量代码（已包含模拟 Agent 的运行示例）：

```python
import json
import re
from enum import Enum
from typing import List, Dict, Optional
import tiktoken


# ---------- 1. 生命周期状态 ----------
class SegmentState(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EVICTABLE = "evictable"


class ContextSegment:
    def __init__(self, turn_id: int, user_msg: str, assistant_msg: str,
                 tool_calls: List[Dict], tool_results: List[str]):
        self.turn_id = turn_id
        self.user_msg = user_msg
        self.assistant_msg = assistant_msg
        self.tool_calls = tool_calls
        self.tool_results = tool_results
        self.state = SegmentState.ACTIVE


# ---------- 2. 上下文管理器 ----------
class TokenPilotContextManager:
    def __init__(self, system_prompt: str, tools: List[Dict], eviction_interval: int = 3):
        self.system_prompt = system_prompt
        self.tools = tools
        self.static_prefix = self._build_static_prefix()
        self.segments: List[ContextSegment] = []
        self.eviction_interval = eviction_interval
        self.turn_counter = 0
        self.external_store: Dict[str, str] = {}

    def _build_static_prefix(self) -> List[Dict[str, str]]:
        stable_system = self.system_prompt.replace("{current_time}", "[CURRENT_TIME]")
            .replace("{workspace}", "[WORKSPACE]")
        tools_text = json.dumps(self.tools, sort_keys=True, ensure_ascii=False)
        return [
            {"role": "system", "content": stable_system},
            {"role": "system", "content": f"Tools:\n{tools_text}"}
        ]

    def compress_tool_output(self, output: str, content_type: str = "text") -> str:
        if content_type == "html":
            return self._compress_html(output)
        elif content_type in ("log", "terminal"):
            return self._compress_log(output)
        else:
            if len(output) > 500:
                store_id = f"text_{hash(output) % 1000000}"
                self.external_store[store_id] = output
                return output[:500] + f"... [FULL_ID:{store_id}]"
            return output

    def _compress_html(self, html: str) -> str:
        title = re.search(r"<title>(.*?)</title>", html, re.I)
        title_text = title.group(1) if title else "No Title"
        clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
        clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL)
        body = re.search(r"<body.*?>(.*?)</body>", clean, re.DOTALL | re.I)
        body_text = body.group(1) if body else clean[:200]
        summary = body_text[:200].strip()
        store_id = f"html_{hash(html) % 1000000}"
        self.external_store[store_id] = html
        return f"[HTML_SUMMARY] Title: {title_text}\n{summary}... [FULL_ID:{store_id}]"

    def _compress_log(self, log: str) -> str:
        lines = log.splitlines()
        if len(lines) > 50:
            compressed = "\n".join(lines[:10] + ["... (truncated) ..."] + lines[-10:])
        else:
            compressed = log
        store_id = f"log_{hash(log) % 1000000}"
        self.external_store[store_id] = log
        return compressed + f"\n[FULL_ID:{store_id}]"

    def add_turn(self, user_msg: str, assistant_msg: str,
                 tool_calls: List[Dict], tool_results: List[str],
                 tool_content_types: Optional[List[str]] = None):
        if tool_content_types is None:
            tool_content_types = ["text"] * len(tool_results)
        compressed_results = [
            self.compress_tool_output(res, ctype)
            for res, ctype in zip(tool_results, tool_content_types)
        ]
        segment = ContextSegment(
            turn_id=self.turn_counter,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            tool_calls=tool_calls,
            tool_results=compressed_results
        )
        self.segments.append(segment)
        self.turn_counter += 1

        if self.turn_counter % self.eviction_interval == 0:
            self._evict_expired()
        self._update_states()

    def _update_states(self):
        for i, seg in enumerate(self.segments):
            if i >= len(self.segments) - 2:
                seg.state = SegmentState.ACTIVE
            else:
                if seg.state == SegmentState.ACTIVE:
                    seg.state = SegmentState.COMPLETED
                if (self.turn_counter - seg.turn_id) > self.eviction_interval:
                    seg.state = SegmentState.EVICTABLE

    def _evict_expired(self):
        new_segments = []
        kept_any = False
        for seg in reversed(self.segments):
            if seg.state == SegmentState.EVICTABLE and kept_any:
                continue
            else:
                new_segments.insert(0, seg)
                kept_any = True
        self.segments = new_segments

    def build_prompt(self) -> List[Dict[str, str]]:
        messages = self.static_prefix.copy()
        for seg in self.segments:
            if seg.state == SegmentState.EVICTABLE:
                continue
            messages.append({"role": "user", "content": seg.user_msg})
            if seg.tool_calls:
                tool_calls_text = json.dumps(seg.tool_calls, ensure_ascii=False)
                messages.append({
                    "role": "assistant",
                    "content": f"{seg.assistant_msg}\nTool calls: {tool_calls_text}"
                })
            else:
                messages.append({"role": "assistant", "content": seg.assistant_msg})
            for result in seg.tool_results:
                messages.append({"role": "tool", "content": result})
        return messages

    def estimate_tokens(self, messages: List[Dict]) -> int:
        enc = tiktoken.get_encoding("cl100k_base")
        text = json.dumps(messages, ensure_ascii=False)
        return len(enc.encode(text))

    def get_stats(self):
        msgs = self.build_prompt()
        total = self.estimate_tokens(msgs)
        prefix_tokens = self.estimate_tokens(self.static_prefix)
        return {
            "total_segments": len(self.segments),
            "active": sum(1 for s in self.segments if s.state == SegmentState.ACTIVE),
            "completed": sum(1 for s in self.segments if s.state == SegmentState.COMPLETED),
            "evictable": sum(1 for s in self.segments if s.state == SegmentState.EVICTABLE),
            "total_tokens": total,
            "cache_hit_tokens": prefix_tokens,
            "cache_miss_tokens": total - prefix_tokens
        }


# ---------- 3. 模拟 Agent 使用 ----------
def simulate_agent():
    SYSTEM_PROMPT = """You are a helpful assistant with tools.
Current time: {current_time}
Workspace: {workspace}
"""
    TOOLS = [
        {"name": "search_web", "description": "Search the web"},
        {"name": "read_file", "description": "Read a file"},
    ]

    manager = TokenPilotContextManager(SYSTEM_PROMPT, TOOLS, eviction_interval=3)

    rounds = [
        {
            "user": "Find latest AI news",
            "assistant": "I will search web",
            "tool_calls": [{"name": "search_web", "args": {"query": "AI news"}}],
            "tool_results": [
                """<html><head><title>AI News</title></head>
                <body><h1>AI Breakthrough</h1><p>This is a very long article content...""" * 50
            ],
            "content_type": ["html"]
        },
        {
            "user": "Summarize the article",
            "assistant": "Here is summary",
            "tool_calls": [],
            "tool_results": [],
            "content_type": []
        },
        {
            "user": "Read config file",
            "assistant": "Reading file",
            "tool_calls": [{"name": "read_file", "args": {"path": "/etc/config"}}],
            "tool_results": [
                "\n".join([f"line {i}: config param" for i in range(200)])
            ],
            "content_type": ["log"]
        },
        {
            "user": "What is the config?",
            "assistant": "The config contains...",
            "tool_calls": [],
            "tool_results": [],
            "content_type": []
        },
        {
            "user": "Any more news?",
            "assistant": "Search again",
            "tool_calls": [{"name": "search_web", "args": {"query": "AI"}}],
            "tool_results": [
                "<html><body>Short news</body></html>"
            ],
            "content_type": ["html"]
        }
    ]

    for r in rounds:
        manager.add_turn(
            user_msg=r["user"],
            assistant_msg=r["assistant"],
            tool_calls=r["tool_calls"],
            tool_results=r["tool_results"],
            tool_content_types=r.get("content_type", ["text"] * len(r["tool_results"]))
        )
        stats = manager.get_stats()
        print(f"\n--- After turn {manager.turn_counter} ---")
        print(f"Total tokens: {stats['total_tokens']}")
        print(f"Cache hit tokens (prefix): {stats['cache_hit_tokens']}")
        print(f"Cache miss tokens: {stats['cache_miss_tokens']}")
        print(f"Active: {stats['active']}, Completed: {stats['completed']}, Evictable: {stats['evictable']}")
        print(f"Messages length: {len(manager.build_prompt())}")

    print("\n--- External store contains compressed full data ---")
    for key, value in manager.external_store.items():
        print(f"{key}: {len(value)} chars")


if __name__ == "__main__":
    simulate_agent()
```

### 4.4 运行与效果

1. **安装依赖**

   bash

   ```
   pip install tiktoken
   ```

（若想调用真实 API，可加 `openai`，但本 Demo 仅做统计，无需联网。）

2. **运行**

   bash

   ```
   python tokenpilot_demo.py
   ```


3. **观察输出**
   每轮结束后会打印：

    - 总 Token 数（模拟）
    - 缓存命中 Token（即固定前缀的长度）
    - 各状态片段数量
    - 当前消息条数

   你可以看到随着轮次增加，`evictable` 片段被驱逐，Token 总数增长放缓，而前缀 Token 始终不变，体现了缓存复用的收益。

### 4.5 与论文的对应关系

| 论文模块   | Demo 实现                                           |
|:-------|:--------------------------------------------------|
| 前缀稳定化  | `_build_static_prefix()` 中替换动态字段，工具定义排序固定         |
| 环境消息压缩 | `compress_tool_output()` 区分 HTML/日志/文本，截断并外存      |
| 外部注册表  | `external_store` 字典存储完整原文，标记 `[FULL_ID]`          |
| 三阶段状态  | `SegmentState` 枚举及 `_update_states()` 逻辑          |
| 批量驱逐   | `eviction_interval` 控制周期，`_evict_expired()` 从尾部删除 |
| 缓存命中统计 | `get_stats()` 计算前缀 Token 作为缓存命中量                  |

------

## 5. 总结

TokenPilot 为长期运行的 LLM Agent 提供了一套**缓存优先**的上下文管理范式，其核心洞见在于：**压缩不仅要减少
Token，更要保持结构的稳定性**。通过全局压缩与局部驱逐的协同，它实现了显著的降本增效。

  -  论文核心: TokenPilot 是一个 Agent 上下文管理框架，核心主张是压缩 token 的同时必须维持 prompt cache 的前缀连续性，否则缓存失效的重复预计算开销会抵消省下的 token 费用。
  -  问题背景: Agent 长任务会不断累积工具调用记录，输入 token 越来越多；已有的截断、摘要、记忆换出方法虽然减少了 token，却频繁改变 prompt 布局，让后端 KV cache 大量失效。
  -  全局模块: Ingestion-Aware Compaction 在外部内容进入上下文之前做处理，把 agent id、工作目录、时间戳等动态字段替换成稳定占位符，并把工具定义移到 system prompt 末尾，从第一轮就保证字节级一致的 prompt 前缀。
  -  观察压缩与恢复: 对工具返回的网页 HTML、日志、执行输出做规则式精简，原始完整内容按 hash 存进外部 artifact registry，压缩版本缺细节时可通过恢复工具找回，避免硬截断造成信息损失。
  -  局部模块: Lifecycle-Aware Eviction 给每个上下文片段标记 active、completed、evictable 三种生命周期状态；已完成但有残余价值的片段继续保留，避免后续任务重复读取同一份材料。
  -  保守清理节奏: 状态判断由一个轻量模型 estimator 每 3 轮批量触发一次，而不是每步都清理，用更低的扰动换取缓存布局稳定；整个连续评测流里 estimator 成本不到 0.03 美元。
  -  TokenPilot 主要作用是"内容怎么摆才能持续命中缓存"。
  -  局限: 收益依赖后端支持 prefix caching；estimator 在任务信号模糊时可能误判；批次大小和频率阈值需要按部署环境调参；混杂任务流下缓存复用率会下降。

