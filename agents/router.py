"""
🤖 交互总控 Agent (AI Copilot / Router)
基于 LangGraph StateGraph 实现意图识别 → Agent 路由 → 结果汇总
作为前端唯一入口，接收用户模糊提问，拆解并分发给子 Agent
Temperature: 0.3 （需要语义泛化能力理解模糊问题）
"""
import os
from dotenv import load_dotenv
from utils.llm_factory import get_llm
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from agents.state import DataMindState
from agents.cleaning_agent import create_cleaning_agent
from agents.eda_agent import create_eda_agent
from agents.analyst_agent import create_analyst_agent
from agents.ab_agent import create_ab_agent
from utils.data_store import get_data_summary, has_data

load_dotenv()


# ═══════════════════════════════════════════════════════════
# Router 意图分类 Prompt
# ═══════════════════════════════════════════════════════════

ROUTER_SYSTEM_PROMPT = """你是 DataMind 的智能路由器。你的唯一任务是分析用户的问题，并决定应该由哪个 Agent 来处理。

## 可用 Agent：
1. **cleaning** — 数据清洗、数据质量检查、缺失值处理、去重、异常检测
2. **eda** — 数据探索、分布分析、相关性分析、数据概况、统计摘要
3. **analyst** — 用户分群(RFM)、留存分析(Cohort)、流失预警、LTV预测、漏斗分析、中介效应、调节效应、因果分析
4. **ab_test** — A/B测试、假设检验、t检验、p值、样本量计算、统计显著性
5. **general** — 通用对话，不涉及具体分析工具的闲聊、问候或一般数据问题

## 路由规则：
- 如果是"清洗/去重/缺失/异常检测/数据质量"相关 → cleaning
- 如果是"看看数据/数据概况/分布/相关性/探索/EDA"相关 → eda
- 如果是"RFM/留存/流失/LTV/分群/漏斗/中介/调节/归因"相关 → analyst
- 如果是"AB测试/对照组/实验组/p值/样本量/显著性/转化率对比"相关 → ab_test
- 如果无法判断或是一般性问题 → general

## 输出格式：
只输出一个单词：cleaning / eda / analyst / ab_test / general
不要输出任何其他内容。"""


def _get_router_llm():
    return get_llm(temperature=0.3)


def _get_general_llm():
    return get_llm(temperature=0.3)


# ═══════════════════════════════════════════════════════════
# 各 Agent 单例缓存
# ═══════════════════════════════════════════════════════════

_agent_cache = {}


def _get_agent(name: str):
    if name not in _agent_cache:
        creators = {
            "cleaning": create_cleaning_agent,
            "eda": create_eda_agent,
            "analyst": create_analyst_agent,
            "ab_test": create_ab_agent,
        }
        if name in creators:
            _agent_cache[name] = creators[name]()
    return _agent_cache.get(name)


# ═══════════════════════════════════════════════════════════
# Router Node 定义
# ═══════════════════════════════════════════════════════════

def router_node(state: DataMindState) -> dict:
    """路由节点：分析用户意图，决定下一个 Agent"""
    messages = state["messages"]
    if not messages:
        return {"next_agent": "general"}

    # 获取最后一条用户消息
    user_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    if not user_msg:
        return {"next_agent": "general"}

    # 调用 LLM 做意图分类
    llm = _get_router_llm()
    context = ""
    if has_data():
        context = f"\n\n当前数据概况：{get_data_summary(max_rows=1)[:500]}"

    response = llm.invoke([
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": f"用户提问：{user_msg}{context}"},
    ])

    content = response.content
    if isinstance(content, list):
        route = "".join([part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in content]).strip().lower()
    else:
        route = str(content).strip().lower()

    # 清理可能的多余输出
    for valid in ["cleaning", "eda", "analyst", "ab_test", "general"]:
        if valid in route:
            route = valid
            break
    else:
        route = "general"

    return {"next_agent": route}


def sub_agent_node(state: DataMindState) -> dict:
    """子 Agent 执行节点：调用对应的子 Agent"""
    agent_name = state.get("next_agent", "general")
    messages = state["messages"]

    # 获取最后一条用户消息
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    if agent_name == "general":
        # General 直接用 LLM 回复
        llm = _get_general_llm()
        data_context = ""
        if has_data():
            data_context = f"\n\n（当前已加载数据，用户可在侧边栏各功能页面操作）"
        response = llm.invoke([
            {"role": "system", "content": (
                "你是 DataMind AI 数据分析助手。用中文友好地回复用户。"
                "你可以引导用户使用以下功能：数据清洗、数据探索(EDA)、"
                "用户分析(RFM/Cohort/LTV)、A/B测试、报告导出。"
                f"{data_context}"
            )},
            {"role": "user", "content": user_msg},
        ])
        return {"messages": [{"role": "assistant", "content": response.content}]}

    # 调用子 Agent
    agent = _get_agent(agent_name)
    if agent is None:
        return {"messages": [{"role": "assistant", "content": f"Agent '{agent_name}' 未找到。"}]}

    result = agent.invoke({"messages": [{"role": "user", "content": user_msg}]})

    # 提取最后一条 AI 回复
    raw_content = result["messages"][-1].content
    if isinstance(raw_content, list):
        response_text = "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw_content
        ).strip()
    elif isinstance(raw_content, str):
        response_text = raw_content
    else:
        response_text = str(raw_content)

    if not response_text:
        response_text = "分析完成，但未生成文字回复。"

    return {"messages": [{"role": "assistant", "content": response_text}]}


# ═══════════════════════════════════════════════════════════
# 构建 Router Graph
# ═══════════════════════════════════════════════════════════

def create_router_agent():
    """创建 Router Agent（LangGraph StateGraph）"""
    graph = StateGraph(DataMindState)

    # 添加节点
    graph.add_node("router", router_node)
    graph.add_node("execute", sub_agent_node)

    # 边：START → router → execute → END
    graph.add_edge(START, "router")
    graph.add_edge("router", "execute")
    graph.add_edge("execute", END)

    return graph.compile()
