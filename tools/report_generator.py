"""
报告生成器
将 Pipeline 各阶段产出汇总为结构化 Markdown 报告
"""
from datetime import datetime
from utils.data_store import get, get_df


def generate_markdown_report(
    dataset_profile: dict | None = None,
    clean_report: dict | None = None,
    eda_insights: list[str] | None = None,
    analysis_summary: str | None = None,
    domain_type: str | None = None,
) -> str:
    """
    生成完整的 Markdown 分析报告

    参数:
        dataset_profile: 数据集嗅探结果
        clean_report: 清洗质量报告
        eda_insights: EDA 洞察列表
        analysis_summary: AI 分析总结
        domain_type: 识别的业务领域
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    domain_labels = {
        "ecommerce": "📦 电商交易",
        "marketing": "📢 营销投放",
        "user_growth": "📈 用户增长",
        "general": "📋 通用数据",
    }
    domain_label = domain_labels.get(domain_type, "📋 通用数据")

    sections = []

    # ── 报告头部 ───────────────────────────────────────────
    sections.append(f"# 📊 DataMind 智能分析报告\n")
    sections.append(f"> 生成时间：{timestamp} | 数据类型：{domain_label}\n")

    # ── 数据概览 ───────────────────────────────────────────
    df = get_df()
    if df is not None:
        sections.append("## 📋 数据概览\n")
        sections.append(f"| 指标 | 值 |")
        sections.append(f"|---|---|")
        sections.append(f"| 总行数 | {len(df):,} |")
        sections.append(f"| 总列数 | {len(df.columns)} |")
        sections.append(f"| 数值列 | {len(df.select_dtypes(include='number').columns)} |")
        sections.append(f"| 文本列 | {len(df.select_dtypes(include='object').columns)} |")
        sections.append(f"| 日期列 | {len(df.select_dtypes(include='datetime64').columns)} |")
        missing_total = df.isna().sum().sum()
        sections.append(f"| 总缺失值 | {missing_total:,} |")
        sections.append("")

    # ── 数据集嗅探 ─────────────────────────────────────────
    if dataset_profile:
        sections.append("## 🔍 数据集嗅探\n")
        if "description" in dataset_profile:
            sections.append(f"{dataset_profile['description']}\n")
        if "key_columns" in dataset_profile:
            sections.append("**关键列识别：**\n")
            for col_type, col_name in dataset_profile["key_columns"].items():
                sections.append(f"- {col_type}: `{col_name}`")
            sections.append("")

    # ── 数据质量体检 ───────────────────────────────────────
    if clean_report:
        sections.append("## 🧹 数据质量体检\n")
        score = clean_report.get("quality_score", "N/A")
        sections.append(f"**数据质量评分：{score}/100**\n")

        sections.append("| 检测项 | 结果 |")
        sections.append("|---|---|")
        sections.append(f"| 原始行数 | {clean_report.get('original_rows', 'N/A'):,} |")
        sections.append(f"| 清洗后行数 | {clean_report.get('final_rows', 'N/A'):,} |")
        sections.append(f"| 去除重复行 | {clean_report.get('duplicates_removed', 0):,} |")
        sections.append(f"| 类型转换 | {len(clean_report.get('type_conversions', {}))} 列 |")
        sections.append("")

        # 清洗步骤
        steps = clean_report.get("steps", [])
        if steps:
            sections.append("**清洗步骤：**\n")
            for i, step in enumerate(steps, 1):
                sections.append(f"{i}. {step}")
            sections.append("")

        # 异常值
        outliers = clean_report.get("outliers", {})
        if outliers:
            sections.append("**⚠️ 异常值检测：**\n")
            for col, info in outliers.items():
                sections.append(f"- `{col}`: {info['count']} 个异常（{info['pct']}）")
            sections.append("")

    # ── EDA 洞察 ───────────────────────────────────────────
    if eda_insights:
        sections.append("## 🔍 数据探索洞察\n")
        for insight in eda_insights:
            sections.append(f"- {insight}")
        sections.append("")

    # ── AI 深度分析 ────────────────────────────────────────
    if analysis_summary:
        sections.append("## 📊 AI 深度分析\n")
        sections.append(analysis_summary)
        sections.append("")

    # ── 结尾 ───────────────────────────────────────────────
    sections.append("---\n")
    sections.append("*本报告由 DataMind AI 数据分析平台自动生成*")

    return "\n".join(sections)
