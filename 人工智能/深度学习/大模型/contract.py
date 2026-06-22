import re

from crewai import LLM, Agent, Task, Crew, Process
from dotenv import load_dotenv

load_dotenv()

import os
import glob
from typing import Union, List
from langchain_community.document_loaders import PyMuPDFLoader
from crewai.tools import tool


@tool
def load_pdf(paths: Union[str, List[str]] = None):
    '''
    读取一个或多个 PDF / TXT / MD 文件的内容。
    如果不传 paths，则默认读取脚本所在目录下的 "合同包" 文件夹中的所有支持文件。
    支持传入单个文件路径、目录路径或路径列表（相对路径或绝对路径）。
    '''
    # 1. 获取脚本所在目录（用于解析相对路径）
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. 处理默认值
    if paths is None:
        paths = os.path.join(script_dir, "合同包")

    # 3. 统一转换为列表
    if isinstance(paths, str):
        paths = [paths]

    # 4. 展开路径：将目录替换为其下的所有支持文件（pdf/txt/md）
    expanded_paths = []
    # 支持的扩展名
    supported_extensions = ("*.pdf", "*.txt", "*.md")

    for p in paths:
        # 转换为绝对路径（支持相对路径）
        if not os.path.isabs(p):
            # 优先相对当前工作目录解析，失败则回退到脚本目录
            abs_p = os.path.abspath(os.path.join(os.getcwd(), p))
            if not os.path.exists(abs_p):
                abs_p = os.path.join(script_dir, p)
        else:
            abs_p = p

        if os.path.isdir(abs_p):
            # 收集目录下所有支持的文件
            files = []
            for ext in supported_extensions:
                files.extend(glob.glob(os.path.join(abs_p, ext)))
                # 如果需要递归子目录，可将上面一行改为：
                # files.extend(glob.glob(os.path.join(abs_p, "**", ext), recursive=True))
            if not files:
                expanded_paths.append(f"【错误】目录 {p} 中没有找到任何 PDF/TXT/MD 文件")
            else:
                expanded_paths.extend(files)
        else:
            # 单个文件：检查扩展名是否支持
            if not os.path.isfile(abs_p):
                expanded_paths.append(f"【错误】文件不存在：{p}")
            elif not any(abs_p.lower().endswith(ext.replace('*', '')) for ext in supported_extensions):
                expanded_paths.append(f"【错误】不支持的文件类型：{p}（仅支持 pdf/txt/md）")
            else:
                expanded_paths.append(abs_p)

    # 5. 读取每个文件的内容
    all_text = []
    for file_path in expanded_paths:
        if file_path.startswith("【错误】"):
            all_text.append(file_path)
            continue

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                loader = PyMuPDFLoader(file_path)
                docs = loader.load()
                text = "\n".join([doc.page_content for doc in docs])
            elif ext in ('.txt', '.md'):
                # 使用 utf-8 编码读取文本文件，忽略无法解码的字符（可选）
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                # 理论上不会进入这里，因为前面已过滤
                text = f"【错误】不支持的文件类型：{file_path}"
                all_text.append(text)
                continue

            if not text:
                text = f"【错误】{os.path.basename(file_path)} 文件为空或无法提取内容"
            all_text.append(f"【文件：{file_path}】\n{text.strip()}")
        except Exception as e:
            all_text.append(f"【错误】读取 {os.path.basename(file_path)} 失败：{str(e)}")

    # 6. 返回结果
    if not all_text:
        return "未找到任何可读取的合同文件。"
    return "\n\n" + "\n\n".join(all_text)


@tool
def clean_contract(raw_text: str):
    '''
    对合同文本进行专业清洗（去除乱码、多余空格、页眉页脚、特殊字符等）
    Args:
        raw_text:每行文件内容

    Returns:对合同文本进行专业清洗（去除乱码、多余空格、页眉页脚、特殊字符等）

    '''
    try:
        # 1. 去除多余空白字符和重复换行
        text = re.sub(r'\s+', ' ', raw_text)
        # 2. 去除常见页眉页脚噪声（示例，可根据实际合同调整）
        text = re.sub(r'第 \d+ 页|共 \d+ 页|合同编号.*|签署日期.*', '', text)
        # 3. 去除特殊符号和乱码
        text = re.sub(r'[■◆□●◆★※]', '', text)
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)  # 零宽字符
        # 4. 保留必要的标点和结构
        text = re.sub(r'\s+([，。；：？！])', r'\1', text)
        return text.strip()
    except Exception as e:
        return f"文本清洗失败: {str(e)}"


OUTPUT_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")


@tool
def save_final_report(report_content: str, filename: str = "") -> str:
    """保存最终审查报告为 Markdown 文件"""
    try:
        if not filename:
            filename = os.path.join(OUTPUT_BASE, "contract_review_report.md")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"审查报告已保存至：{filename}"
    except Exception as e:
        return f"保存失败: {str(e)}"


@tool
def save_modified_clauses(modified_clauses: str, filename: str = "") -> str:
    """保存修改后的合同条文"""
    try:
        if not filename:
            filename = os.path.join(OUTPUT_BASE, "modified_clauses.md")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(modified_clauses)
        return f"修改后的条文已保存至：{filename}"
    except Exception as e:
        return f"保存失败: {str(e)}"


@tool
def save_contract_report(contract_name: str, report_content: str) -> str:
    """将单个合同的审查报告保存到该合同专属的文件夹中
    Args:
        contract_name: 合同名称（如 劳务合同、房屋租赁合同、设备租赁合同）
        report_content: 该合同的审查报告内容
    """
    try:
        contract_dir = os.path.join(OUTPUT_BASE, contract_name)
        os.makedirs(contract_dir, exist_ok=True)
        filepath = os.path.join(contract_dir, f"{contract_name}_审查报告.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"合同「{contract_name}」审查报告已保存至：{filepath}"
    except Exception as e:
        return f"保存合同「{contract_name}」报告失败: {str(e)}"


@tool
def save_overall_comparison(comparison_content: str) -> str:
    """保存所有合同的整体对比版报告
    Args:
        comparison_content: 所有合同的整体对比分析内容（含风险矩阵、对比表格等）
    """
    try:
        os.makedirs(OUTPUT_BASE, exist_ok=True)
        filepath = os.path.join(OUTPUT_BASE, "整体对比版.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(comparison_content)
        return f"整体对比版报告已保存至：{filepath}"
    except Exception as e:
        return f"保存整体对比版失败: {str(e)}"


llm_deepseek = LLM(
    model="deepseek-v4-flash",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.7
)
clean_agent = Agent(
    role='合同读取与清洗专员',
    goal="读取一个或多个合同文件（路径由 input 中的 file_paths 提供），对每个文件分别进行专业文本清洗，合并输出所有清洗后的合同全文。",
    backstory="你是一位专业的文档处理专家，擅长从文档中提取干净、结构清晰的合同文本。",
    expected_output="所有合同清洗后的完整文本，不同合同之间用分隔符分开。",
    tools=[load_pdf, clean_contract],
    verbose=True,
    llm=llm_deepseek
)
review_agent = Agent(
    role="合同审核专家",
    goal="全面识别合同中的法律、商业和合规风险",
    backstory="你是一位严谨的风险控制律师，专注于发现不公平条款、法律漏洞和潜在风险。",
    verbose=True,
    llm=llm_deepseek
)
modifier_agent = Agent(
    role="合同修改建议专家",
    goal="针对风险点提出具体、可操作的修改建议",
    backstory="你是一位合同优化专家，擅长给出保护企业利益的实用修改方案。",
    llm=llm_deepseek,
    verbose=True
)
validator_agent = Agent(
    role="终审专家",
    goal="对审查结果进行最终把关，并生成包含前后对比的完整报告",
    backstory="你是一位资深法务总监，对合同审查报告的质量有极高要求。",
    llm=llm_deepseek,
    verbose=True
)

manager_agent = Agent(
    role="合同审查项目经理",
    goal="统筹整个审查流程，协调各 Agent 工作，确保最终报告高质量输出",
    backstory="你是一位经验丰富的项目经理，负责分配任务、监控进度和最终交付。",
    llm=llm_deepseek,
    verbose=True
)
save_agent = Agent(
    role="合同保存专家",
    goal="将最终审查后的合同进行整理保存，每个合同分开保存到各自文件夹，同时生成整体对比版",
    backstory="你是一位经验丰富的合同保存专家，负责将审查结果逐一保存到各合同专属文件夹中，并整理所有合同的整体对比分析版本。",
    llm=llm_deepseek,
    tools=[save_final_report, save_modified_clauses, save_contract_report, save_overall_comparison],
    verbose=True
)
task1_clean = Task(
    description="读取 input 中 file_paths 指定的目录或文件列表，对每个合同文件进行专业文本清洗，合并输出所有清洗后的合同全文。",
    expected_output="所有合同清洗后的完整文本，不同合同之间用分隔符分开。",
    agent=clean_agent
)
task2_review = Task(
    description="基于清洗后的合同文本，全面识别法律、商业和合规风险，并给出风险等级和详细说明。",
    expected_output="风险点清单（包含风险等级、具体条款位置、风险描述）",
    agent=review_agent,
    context=[task1_clean]
)
task3_modify = Task(
    description="针对审查出的风险点，提出具体、可操作的修改建议，并给出修改前后的条文对比。",
    expected_output="修改建议列表 + 修改前后的条文对比",
    agent=modifier_agent,
    context=[task2_review]
)
task4_validate = Task(
    description="对整个审查结果进行最终审核，生成包含漏洞、修改建议、前后对比的完整结构化报告。",
    expected_output="完整的合同审查报告（包含关键条款、风险点、修改建议、前后对比、总体意见）",
    agent=save_agent,
    context=[task1_clean, task2_review, task3_modify]
)
task5_save = Task(
    description="对审核后的合同进行保存。要求：1. 使用 save_contract_report 将每个合同的审查报告分别保存到各自合同专属文件夹；2. 使用 save_overall_comparison 将包含风险矩阵、对比表格等的整体对比版报告保存到 output 目录；3. 最后使用 save_final_report 保存完整版总报告。",
    expected_output="每个合同已单独保存，整体对比版已生成",
    agent=validator_agent,
    context=[task1_clean, task2_review, task3_modify, task4_validate]
)

crew = Crew(
    agents=[clean_agent, review_agent, modifier_agent, validator_agent,save_agent],
    tasks=[task1_clean, task2_review, task3_modify, task4_validate,task5_save],
    process=Process.hierarchical,
    manager_agent=manager_agent,
    verbose=True
)
if __name__ == '__main__':
    print("🚀 企业合同智能审查多 Agent 系统启动...\n")
    path='./合同包/'
    result = crew.kickoff(inputs={"file_paths":path})
    print("\n" + "=" * 80)
    print("最终审查报告")
    print("=" * 80)
    print(result)