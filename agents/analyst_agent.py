"""
📊 分析决策 Agent [系统核心]
职责：解析自然语言问题，动态匹配最佳分析模型
能力映射：用户分群→RFM/聚类，增长分析→留存/漏斗，深度归因→中介/调节效应
Temperature: 0.0
"""
import os
import json
from dotenv import load_dotenv
from langchain.tools import tool
from utils.llm_factory import get_llm
from langgraph.prebuilt import create_react_agent
from tools.user_analysis import (
    rfm_analysis, cohort_analysis, retention_analysis,
    churn_prediction, ltv_prediction,
)
from tools.advanced_stats import mediation_analysis, moderation_analysis
from tools.eda import funnel_analysis
from utils.data_store import get_df, put, get_data_summary

load_dotenv()


# ═══════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════

@tool
def tool_data_overview(question: str = "") -> str:
    """查看数据概况（列名、类型、统计摘要）。分析前先了解数据。
    参数 question: 可选描述。"""
    return get_data_summary(max_rows=3)


@tool
def tool_rfm(user_col: str, date_col: str, amount_col: str) -> str:
    """RFM 用户分层分析。
    参数：user_col=用户ID列名, date_col=日期列名, amount_col=金额列名"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    try:
        rfm_df, fig = rfm_analysis(df, user_col, date_col, amount_col)
        put("rfm_result", {"df": rfm_df, "fig": fig})
        seg = rfm_df["Segment"].value_counts()
        return (
            f"RFM分析完成！共 {len(rfm_df)} 个用户\n"
            f"用户分层：\n" + "\n".join(f"  {k}: {v}人 ({v/len(rfm_df):.0%})" for k, v in seg.items())
        )
    except Exception as e:
        return f"分析出错：{str(e)}。请检查列名是否正确。可用列：{list(df.columns)}"


@tool
def tool_cohort(user_col: str, date_col: str) -> str:
    """Cohort 留存分析，生成留存热图。
    参数：user_col=用户ID列名, date_col=日期列名"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    try:
        retention_df, fig = cohort_analysis(df, user_col, date_col)
        put("cohort_result", {"df": retention_df, "fig": fig})
        avg_ret = retention_df.iloc[:, 1].mean() if retention_df.shape[1] > 1 else 0
        return (
            f"Cohort留存分析完成！\n- 共 {len(retention_df)} 个月份群组\n"
            f"- 次月平均留存率：{avg_ret:.1f}%\n图表已生成。"
        )
    except Exception as e:
        return f"Cohort分析出错：{str(e)}"


@tool
def tool_retention(user_col: str, date_col: str, period: str = "M") -> str:
    """用户留存率趋势分析。
    参数：user_col=用户ID列名, date_col=日期列名, period='M'月/'W'周/'D'日"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    try:
        ret_df, fig = retention_analysis(df, user_col, date_col, period=period)
        put("retention_result", {"df": ret_df, "fig": fig})
        return f"留存趋势分析完成！\n{ret_df.to_string(index=False)}"
    except Exception as e:
        return f"留存分析出错：{str(e)}"


@tool
def tool_churn(user_col: str, date_col: str, churn_days: int = 30) -> str:
    """流失预警分析。
    参数：user_col=用户ID列名, date_col=日期列名, churn_days=流失判定天数(默认30)"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    try:
        churn_df, fig = churn_prediction(df, user_col, date_col, churn_days=churn_days)
        put("churn_result", {"df": churn_df, "fig": fig})
        status = churn_df["status"].value_counts()
        return (
            f"流失预警完成！\n用户状态分布：\n"
            + "\n".join(f"  {k}: {v}人" for k, v in status.items())
        )
    except Exception as e:
        return f"流失分析出错：{str(e)}"


@tool
def tool_ltv(user_col: str, date_col: str, amount_col: str) -> str:
    """LTV 生命周期价值预测。
    参数：user_col=用户ID列名, date_col=日期列名, amount_col=金额列名"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    try:
        ltv_df, fig = ltv_prediction(df, user_col, date_col, amount_col)
        put("ltv_result", {"df": ltv_df, "fig": fig})
        avg_ltv = ltv_df["LTV"].mean()
        tier_dist = ltv_df["LTV_Tier"].value_counts()
        return (
            f"LTV预测完成！共 {len(ltv_df)} 个用户\n"
            f"- 平均 LTV：¥{avg_ltv:,.0f}\n"
            f"- 层级分布：\n" + "\n".join(f"  {k}: {v}人" for k, v in tier_dist.items())
        )
    except Exception as e:
        return f"LTV预测出错：{str(e)}"


@tool
def tool_funnel(stage_names: str, stage_values: str) -> str:
    """漏斗转化分析。
    参数：
      stage_names: 阶段名称列表，逗号分隔，如 "浏览,加购,下单,支付"
      stage_values: 各阶段数量列表，逗号分隔，如 "10000,3000,1500,800" """
    try:
        names = [s.strip() for s in stage_names.split(",")]
        values = [int(s.strip()) for s in stage_values.split(",")]
        if len(names) != len(values):
            return "阶段名称和数量数目不匹配"
        result, fig = funnel_analysis(names, values)
        put("funnel_result", {"data": result, "fig": fig})
        lines = ["漏斗分析完成！"]
        for s in result["stages"]:
            step_rate = f", 环节转化率={s['step_rate']}%" if "step_rate" in s else ""
            lines.append(f"  {s['name']}: {s['value']:,} (总转化={s['overall_rate']}%{step_rate})")
        lines.append(f"\n🔴 瓶颈环节：{result['bottleneck']}（流失 {result['bottleneck_drop_pct']}%）")
        return "\n".join(lines)
    except Exception as e:
        return f"漏斗分析出错：{str(e)}"


@tool
def tool_mediation(x_col: str, m_col: str, y_col: str) -> str:
    """中介效应分析（Baron & Kenny + Sobel Test）。
    ⚠️ 需要用户确认变量选择后才能执行。
    参数：x_col=自变量, m_col=中介变量, y_col=因变量"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    result = mediation_analysis(df, x_col, m_col, y_col)
    if "error" in result:
        return f"分析出错：{result['error']}"
    put("mediation_result", result)
    return result["conclusion"]


@tool
def tool_moderation(x_col: str, w_col: str, y_col: str) -> str:
    """调节效应分析（交互项回归）。
    ⚠️ 需要用户确认变量选择后才能执行。
    参数：x_col=自变量, w_col=调节变量, y_col=因变量"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    result = moderation_analysis(df, x_col, w_col, y_col)
    if "error" in result:
        return f"分析出错：{result['error']}"
    put("moderation_result", result)
    return result["conclusion"]


# ═══════════════════════════════════════════════════════════
# 创建 Agent
# ═══════════════════════════════════════════════════════════

ANALYST_PROMPT = """你是 DataMind 的高级分析决策师 Agent 📊

## 你的核心价值：
不仅是调用工具出结果，而是**从业务角度解读数据，给出可操作的建议**。

## 能力矩阵（根据用户需求选择工具）：
- **用户分群** → tool_rfm (RFM 分层)
- **留存分析** → tool_cohort (Cohort 分析) / tool_retention (留存趋势)
- **流失预警** → tool_churn
- **用户价值** → tool_ltv (LTV 预测)
- **转化分析** → tool_funnel (漏斗分析)
- **因果归因** → tool_mediation (中介效应) / tool_moderation (调节效应)

## 工作原则：
1. **先了解数据** — 用 tool_data_overview 确认列名和数据类型
2. **精准匹配** — 根据用户问题选择最合适的分析方法
3. **业务导向** — 输出必须包含可执行的业务建议
4. **因果分析谨慎** — 中介/调节效应分析需要明确的变量选择，必须向用户确认

## ⚠️ 中介/调节效应的特殊规则：
当用户请求因果分析时，你必须：
1. 先分析用户的描述，推断可能的 X、M/W、Y 变量
2. **明确告知用户你推荐的变量选择**
3. 只有在用户确认后才调用 tool_mediation 或 tool_moderation
4. 如果用户已经明确指定了变量名，可以直接执行

## 输出规范：
- 中文回复，Markdown 格式
- 用 💡 标注关键洞察
- 用 📋 标注行动建议
- 不要编造数据"""


def create_analyst_agent():
    llm = get_llm(temperature=0.0)
    return create_react_agent(
        llm,
        [tool_data_overview, tool_rfm, tool_cohort, tool_retention,
         tool_churn, tool_ltv, tool_funnel, tool_mediation, tool_moderation],
        prompt=ANALYST_PROMPT,
    )
