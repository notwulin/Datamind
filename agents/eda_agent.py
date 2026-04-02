"""
🔍 数据理解 Agent (EDA Agent)
职责：执行探索性数据分析，生成业务语境化的 Insight（不是裸统计量）
输出：总结性 Insight 列表（如"某渠道转化率显著高，建议关注"）
Temperature: 0.0
"""
import os
import json
from dotenv import load_dotenv
from langchain.tools import tool
from utils.llm_factory import get_llm
from langgraph.prebuilt import create_react_agent
from tools.eda import (
    run_eda_summary,
    correlation_analysis,
    distribution_analysis,
    detect_anomalies_insight,
)
from utils.data_store import get_df, put, get_data_summary

load_dotenv()


# ═══════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════

@tool
def tool_eda_summary(question: str = "") -> str:
    """对数据集做全面的探索性分析摘要：数值列统计、类别列分布、高相关性对、偏态检测。
    参数 question: 可选描述。"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    result = run_eda_summary(df)
    put("eda_summary", result)

    lines = [f"EDA 摘要：{result['shape']['rows']}行 × {result['shape']['cols']}列"]

    # 数值列统计
    if result["numeric_stats"]:
        lines.append(f"\n数值列（{len(result['numeric_stats'])}个）：")
        for col, s in list(result["numeric_stats"].items())[:8]:
            lines.append(f"  · {col}: 均值={s['mean']}, 中位数={s['median']}, 标准差={s['std']}, 零值占{s['zeros_pct']}%")

    # 偏态列
    if result["skewed_columns"]:
        lines.append(f"\n⚠️ 严重偏态列：")
        for s in result["skewed_columns"]:
            lines.append(f"  · {s['column']}: 偏度={s['skewness']}")

    # 高相关性
    if result["high_correlation_pairs"]:
        lines.append(f"\n🔗 高相关性配对（|r| > 0.7）：")
        for p in result["high_correlation_pairs"]:
            lines.append(f"  · {p['col_a']} ↔ {p['col_b']}: r={p['correlation']}")

    # 类别列
    if result["categorical_stats"]:
        lines.append(f"\n类别列（{len(result['categorical_stats'])}个）：")
        for col, s in list(result["categorical_stats"].items())[:5]:
            lines.append(f"  · {col}: {s['n_unique']}个类别, 最多: {s['mode']}({s['mode_pct']}%)")

    # 疑似ID列
    if result["potential_id_columns"]:
        lines.append(f"\n🆔 疑似ID列（高基数）：{', '.join(result['potential_id_columns'])}")

    return "\n".join(lines)


@tool
def tool_correlation(question: str = "") -> str:
    """分析数值列之间的相关性，生成相关性矩阵。
    参数 question: 可选描述。"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    corr_df, fig = correlation_analysis(df)
    if corr_df.empty:
        return "数据中数值列不足2列，无法计算相关性。"
    if fig is not None:
        put("eda_corr_fig", fig)

    # 筛选高相关对
    lines = ["相关性分析完成！"]
    num_cols = corr_df.columns
    high_pairs = []
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            r = corr_df.iloc[i, j]
            if abs(r) > 0.5:
                high_pairs.append((num_cols[i], num_cols[j], round(float(r), 3)))

    if high_pairs:
        high_pairs.sort(key=lambda x: -abs(x[2]))
        lines.append("显著相关列对（|r| > 0.5）：")
        for a, b, r in high_pairs[:10]:
            direction = "正相关" if r > 0 else "负相关"
            strength = "强" if abs(r) > 0.7 else "中等"
            lines.append(f"  · {a} ↔ {b}: r={r} ({strength}{direction})")
    else:
        lines.append("未发现显著相关的列对。")
    lines.append("\n图表已生成，可在数据探索页面查看。")
    return "\n".join(lines)


@tool
def tool_anomaly_insight(question: str = "") -> str:
    """自动检测数据中的异常和亮点，返回业务级别的洞察。
    参数 question: 可选描述。"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    insights = detect_anomalies_insight(df)
    put("anomaly_insights", insights)

    if not insights:
        return "✅ 数据质量良好，未检测到显著异常。"

    lines = [f"检测到 {len(insights)} 条洞察：\n"]
    icons = {"anomaly": "🔴", "warning": "⚠️", "highlight": "💡"}
    for ins in sorted(insights, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3)):
        icon = icons.get(ins["type"], "📌")
        lines.append(f"{icon} [{ins['severity'].upper()}] {ins['description']}")

    return "\n".join(lines)


@tool
def tool_distribution(col_name: str) -> str:
    """分析某一数值列的分布特征（直方图、箱线图、正态性检验）。
    参数 col_name: 要分析的数值列列名"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    if col_name not in df.columns:
        return f"列 '{col_name}' 不存在。可用列：{list(df.columns)}"
    if not str(df[col_name].dtype).startswith(("int", "float")):
        return f"列 '{col_name}' 不是数值类型，无法做分布分析。"

    result, fig = distribution_analysis(df, col_name)
    put(f"dist_fig_{col_name}", fig)

    normal_str = "符合正态分布" if result["is_normal"] else "不符合正态分布"
    return (
        f"'{col_name}' 分布分析：\n"
        f"  均值={result['mean']}, 中位数={result['median']}, 标准差={result['std']}\n"
        f"  偏度={result['skewness']}, 峰度={result['kurtosis']}\n"
        f"  正态性检验（{result['normality_test']}）: p={result['normality_p']} — {normal_str}\n"
        f"  图表已生成。"
    )


# ═══════════════════════════════════════════════════════════
# 创建 Agent
# ═══════════════════════════════════════════════════════════

EDA_PROMPT = """你是 DataMind 的数据探索专家 Agent 🔍

## 你的职责：
1. 对数据做全面的探索性分析（EDA）
2. 你的核心价值不是列出统计数字，而是**将数据转化为业务洞察（Insight）**
3. 对每个发现，必须给出"这意味着什么"和"建议采取什么行动"

## 工作流程：
1. 先用 tool_eda_summary 获取全面的统计摘要
2. 用 tool_correlation 检查相关性
3. 用 tool_anomaly_insight 检测异常和亮点
4. 如需深入某列分布，用 tool_distribution

## 输出规范：
- 用中文回复
- 以 **Insight（洞察）** 为核心，不要罗列原始统计数字
- 例如：不要说 "col_A 均值=3.2, std=1.1"
  要说 "col_A 的数据分布呈右偏态（均值>中位数），说明存在少量极高值拉高平均水平，建议关注这些极端用户/订单"
- 每条 Insight 用 💡 开头
- 最后给出"下一步建议分析方向"
- 不要编造数据，所有数值必须来自工具返回"""


def create_eda_agent():
    llm = get_llm(temperature=0.0)
    return create_react_agent(
        llm,
        [tool_eda_summary, tool_correlation, tool_anomaly_insight, tool_distribution],
        prompt=EDA_PROMPT,
    )
