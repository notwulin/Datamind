"""
🔄 自动分析 Pipeline
基于 LangGraph StateGraph 实现一键全自动分析流
Pipeline: 数据集嗅探 → 清洗 → EDA → 领域专项分析 → 报告生成

核心设计：
1. 数据集嗅探 (Dataset Profiling) — AI 推断数据场景（电商/营销/用户增长/通用）
2. 领域模板 (Domain-Specific Pipeline) — 根据场景加载特定分析流
3. 所有计算由 Python 工具执行，LLM 只负责"总结解读"
"""
import os
from dotenv import load_dotenv
from utils.llm_factory import get_llm
from langgraph.graph import StateGraph, START, END
from agents.state import DataMindState
from tools.cleaning import clean_dataframe
from tools.eda import run_eda_summary, detect_anomalies_insight, correlation_analysis
from tools.report_generator import generate_markdown_report
from utils.data_store import get, put, get_df, get_data_summary

load_dotenv()


def _get_llm(temperature: float = 0.0):
    return get_llm(temperature=temperature)


# ═══════════════════════════════════════════════════════════
# 领域分析模板
# ═══════════════════════════════════════════════════════════

DOMAIN_TEMPLATES = {
    "ecommerce": {
        "label": "📦 电商交易分析",
        "focus_areas": [
            "品类销售额排行与趋势",
            "客单价分布与异常值",
            "用户复购率与复购周期",
            "高价值用户特征（消费金额 Top 20%）",
            "退货/取消率异常检测",
        ],
        "key_columns": ["user_id/customer_id", "order_date/date", "amount/revenue/price", "product/category"],
    },
    "marketing": {
        "label": "📢 营销投放分析",
        "focus_areas": [
            "各渠道 ROI（投资回报率）对比",
            "渠道获客成本 (CAC) 排行",
            "转化漏斗各环节流失分析",
            "投放时段效果差异",
            "异常渠道识别（ROI 突降/突升）",
        ],
        "key_columns": ["channel/source", "cost/spend", "conversion/revenue", "date/time"],
    },
    "user_growth": {
        "label": "📈 用户增长分析",
        "focus_areas": [
            "新用户增长趋势与增速变化",
            "用户活跃度分层（日活/周活/月活）",
            "留存率衰减曲线",
            "流失用户特征画像",
            "关键行为转化路径",
        ],
        "key_columns": ["user_id", "date/timestamp", "event/action", "status"],
    },
    "general": {
        "label": "📋 通用数据分析",
        "focus_areas": [
            "数值列分布异常检测",
            "类别列不均衡性分析",
            "高相关性变量对识别",
            "缺失值模式分析",
            "关键指标间的关联关系",
        ],
        "key_columns": [],
    },
}


# ═══════════════════════════════════════════════════════════
# Pipeline 节点
# ═══════════════════════════════════════════════════════════

def profiling_node(state: DataMindState) -> dict:
    """Step 1: 数据集嗅探 — 推断业务场景"""
    df = get("df")
    if df is None:
        return {
            "pipeline_stage": "error",
            "messages": [{"role": "assistant", "content": "❌ 未找到数据，请先上传文件。"}],
        }

    # 提取表头 + 5 行样例给 AI 推断
    header = list(df.columns)
    sample = df.head(5).to_string()
    dtypes = df.dtypes.astype(str).to_dict()

    prompt = f"""分析以下数据集的列名和样例，判断这属于什么类型的业务数据。

列名：{header}
数据类型：{dtypes}
前5行样例：
{sample}

请从以下类型中选择一个最匹配的：
- ecommerce（电商交易数据：含用户ID、日期、金额/价格、商品/品类）
- marketing（营销投放数据：含渠道、花费、转化、日期）
- user_growth（用户增长数据：含用户ID、日期/时间戳、行为/事件）
- general（无法归类的通用数据）

只输出一个单词：ecommerce / marketing / user_growth / general"""

    llm = _get_llm(temperature=0.0)
    response = llm.invoke([{"role": "user", "content": prompt}])
    
    content = response.content
    if isinstance(content, list):
        domain = "".join([part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in content]).strip().lower()
    else:
        domain = str(content).strip().lower()

    # 清理输出
    for valid in ["ecommerce", "marketing", "user_growth", "general"]:
        if valid in domain:
            domain = valid
            break
    else:
        domain = "general"

    template = DOMAIN_TEMPLATES[domain]
    profile = {
        "domain": domain,
        "label": template["label"],
        "focus_areas": template["focus_areas"],
        "columns": header,
        "dtypes": dtypes,
    }
    put("dataset_profile", profile)
    put("domain_type", domain)

    return {
        "pipeline_stage": "cleaning",
        "dataset_profile": profile,
        "domain_type": domain,
        "messages": [{"role": "assistant", "content": f"🔍 数据集嗅探完成 — 识别为 **{template['label']}** 数据"}],
    }


def cleaning_node(state: DataMindState) -> dict:
    """Step 2: 自动数据清洗"""
    df = get("df")
    if df is None:
        return {"pipeline_stage": "error"}

    df_clean, report = clean_dataframe(df, outlier_method="iqr")
    put("df_clean", df_clean)
    put("clean_report", report)

    return {
        "pipeline_stage": "eda",
        "clean_report": report,
        "has_clean_data": True,
        "messages": [{"role": "assistant", "content": (
            f"🧹 数据清洗完成 — 质量评分 **{report['quality_score']}/100**\n"
            f"  · {report['original_rows']}→{report['final_rows']} 行，去重 {report['duplicates_removed']} 行"
        )}],
    }


def eda_node(state: DataMindState) -> dict:
    """Step 3: 探索性分析 + 异常洞察"""
    df = get_df()
    if df is None:
        return {"pipeline_stage": "error"}

    # 运行全面 EDA
    eda_result = run_eda_summary(df)
    anomalies = detect_anomalies_insight(df)
    corr_df, corr_fig = correlation_analysis(df)
    if corr_fig is not None:
        put("eda_corr_fig", corr_fig)
    put("eda_summary", eda_result)
    put("anomaly_insights", anomalies)

    # 组装关键发现
    findings = []
    if eda_result["high_correlation_pairs"]:
        for p in eda_result["high_correlation_pairs"][:3]:
            findings.append(f"'{p['col_a']}' 与 '{p['col_b']}' 高度相关 (r={p['correlation']})")

    if eda_result["skewed_columns"]:
        for s in eda_result["skewed_columns"][:3]:
            findings.append(f"'{s['column']}' 严重偏态（偏度={s['skewness']}）")

    for a in anomalies[:5]:
        findings.append(a["description"])

    put("eda_insights", findings)

    return {
        "pipeline_stage": "analysis",
        "eda_insights": findings,
        "messages": [{"role": "assistant", "content": f"🔍 数据探索完成 — 发现 **{len(findings)}** 条关键洞察"}],
    }


def analysis_node(state: DataMindState) -> dict:
    """Step 4: 领域专项分析 — 基于 AI 生成业务洞察"""
    df = get_df()
    if df is None:
        return {"pipeline_stage": "error"}

    domain = state.get("domain_type", "general")
    template = DOMAIN_TEMPLATES.get(domain, DOMAIN_TEMPLATES["general"])
    eda_insights = state.get("eda_insights", [])
    clean_report = state.get("clean_report", {})

    # 构建上下文给 AI 做领域分析
    data_summary = get_data_summary(max_rows=5)
    insights_str = "\n".join(f"- {i}" for i in eda_insights) if eda_insights else "无"

    prompt = f"""你是一位资深的数据分析师。基于以下信息，对这份 **{template['label']}** 数据集进行深度业务分析。

## 数据概况
{data_summary[:2000]}

## 数据质量
- 质量评分：{clean_report.get('quality_score', 'N/A')}/100
- 去除重复：{clean_report.get('duplicates_removed', 0)} 行

## EDA 发现
{insights_str}

## 分析要求
请聚焦以下 **{template['label']}** 领域的关键问题：
{chr(10).join(f"  {i+1}. {area}" for i, area in enumerate(template['focus_areas']))}

## 输出要求
1. 用中文输出
2. 每条洞察以 💡 开头
3. 每条建议以 📋 开头
4. 基于数据事实分析，不要编造具体数字
5. 给出 3-5 条核心洞察和 2-3 条行动建议
6. 最后给出综合评估和下一步分析建议"""

    llm = _get_llm(temperature=0.1)
    response = llm.invoke([{"role": "user", "content": prompt}])
    
    content = response.content
    if isinstance(content, list):
        analysis_text = "\n".join([part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in content]).strip()
    else:
        analysis_text = str(content).strip()

    put("analysis_summary", analysis_text)

    return {
        "pipeline_stage": "report",
        "analysis_results": {"summary": analysis_text, "domain": domain},
        "messages": [{"role": "assistant", "content": f"📊 领域深度分析完成"}],
    }


def report_node(state: DataMindState) -> dict:
    """Step 5: 生成综合报告"""
    report = generate_markdown_report(
        dataset_profile=state.get("dataset_profile"),
        clean_report=state.get("clean_report"),
        eda_insights=state.get("eda_insights"),
        analysis_summary=get("analysis_summary"),
        domain_type=state.get("domain_type"),
    )
    put("pipeline_report", report)
    put("auto_report", report)

    return {
        "pipeline_stage": "done",
        "pipeline_report": report,
        "messages": [{"role": "assistant", "content": "📝 综合分析报告已生成！请前往「报告导出」页面查看和下载。"}],
    }


# ═══════════════════════════════════════════════════════════
# 构建 Pipeline Graph
# ═══════════════════════════════════════════════════════════

def create_pipeline():
    """创建自动分析 Pipeline（LangGraph StateGraph）"""
    graph = StateGraph(DataMindState)

    graph.add_node("profiling", profiling_node)
    graph.add_node("cleaning", cleaning_node)
    graph.add_node("eda", eda_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "profiling")
    graph.add_edge("profiling", "cleaning")
    graph.add_edge("cleaning", "eda")
    graph.add_edge("eda", "analysis")
    graph.add_edge("analysis", "report")
    graph.add_edge("report", END)

    return graph.compile()
