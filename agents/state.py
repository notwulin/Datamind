"""
DataMind 共享状态定义 (Blackboard Pattern)
所有 Agent 共享同一个 State，通过 LangGraph StateGraph 流转。
DataFrame 存引用 ID（在 data_store 中），消息流只传元数据，避免 Token 超载。
"""
from __future__ import annotations
from typing import Any, Literal
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages


# ═══════════════════════════════════════════════════════════
# 核心共享状态
# ═══════════════════════════════════════════════════════════

class DataMindState(TypedDict):
    """LangGraph 全局共享状态 — 所有 Agent 的 "黑板" """

    # ── 消息流 ────────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── 数据引用 (存 data_store 中的 key，不存 DataFrame 本身) ──
    has_data: bool                   # 是否已加载数据
    has_clean_data: bool             # 是否已清洗

    # ── 分析结果缓存 ─────────────────────────────────────
    clean_report: dict | None        # 清洗质量报告
    eda_insights: list[str] | None   # EDA 洞察列表
    analysis_results: dict | None    # 分析决策结果
    ab_results: dict | None          # AB 测试结果

    # ── Pipeline 控制 ────────────────────────────────────
    pipeline_stage: str | None       # 当前 pipeline 阶段
    dataset_profile: dict | None     # 数据集嗅探结果（场景/领域）
    domain_type: str | None          # 识别的业务领域: ecommerce/marketing/user_growth/general
    pipeline_report: str | None      # 最终生成的 Markdown 报告

    # ── 路由控制 ──────────────────────────────────────────
    next_agent: str | None           # Router 决定的下一个 Agent
    pending_confirmation: dict | None  # 需要用户确认的高级分析参数


# ═══════════════════════════════════════════════════════════
# Pipeline 阶段常量
# ═══════════════════════════════════════════════════════════

PIPELINE_STAGES = [
    "profiling",    # 数据集嗅探
    "cleaning",     # 数据清洗
    "eda",          # 探索性分析
    "analysis",     # 深度分析
    "report",       # 报告生成
    "done",         # 完成
]

# Agent 路由目标
AGENT_NAMES = Literal["cleaning", "eda", "analyst", "ab_test", "end"]
