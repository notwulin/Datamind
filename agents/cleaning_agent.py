"""
🧹 数据清洗 Agent
职责：自动处理缺失值、异常值，执行数据类型转换和标准化
输出：清洗后的 DataFrame 及"数据质量体检报告"
Temperature: 0.0 （执行型 Agent，确保确定性输出）
"""
import os
from dotenv import load_dotenv
from langchain.tools import tool
from utils.llm_factory import get_llm
from langgraph.prebuilt import create_react_agent
from tools.cleaning import clean_dataframe
from tools.quality import auto_quality_checks, quality_report_summary
from utils.data_store import get, put, get_df, get_data_summary

load_dotenv()


# ═══════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════

@tool
def tool_check_data(question: str) -> str:
    """查看当前数据集的基本信息（行列数、列名、类型、统计摘要）。
    在执行任何清洗操作前，先用此工具了解数据。
    参数 question: 任意描述即可。"""
    return get_data_summary(max_rows=3)


@tool
def tool_clean_data(outlier_method: str = "iqr") -> str:
    """清洗当前数据集：去重、缺失值处理、类型推断、异常检测。
    参数 outlier_method: 异常检测方法，可选 'iqr'(默认), 'zscore', 'none'"""
    df = get("df")
    if df is None:
        return "错误：请先上传数据文件"
    df_clean, report = clean_dataframe(df, outlier_method=outlier_method)
    put("df_clean", df_clean)
    put("clean_report", report)

    outlier_info = ""
    if report.get("outliers"):
        outlier_info = "\n异常值检测：\n" + "\n".join(
            f"  · {col}: {info['count']}个异常（{info['pct']}）" for col, info in report["outliers"].items()
        )

    return (
        f"清洗完成！数据质量评分：{report['quality_score']}/100\n"
        f"- 原始：{report['original_rows']}行 × {report['original_cols']}列\n"
        f"- 清洗后：{report['final_rows']}行 × {report['final_cols']}列\n"
        f"- 去除重复：{report['duplicates_removed']}行\n"
        f"- 类型转换：{len(report.get('type_conversions', {}))}列"
        f"{outlier_info}\n"
        f"数据已保存，可用于后续分析。"
    )


@tool
def tool_quality_check(description: str = "") -> str:
    """对当前数据运行质量校验规则（空值率、负值检测、范围合理性等）。
    参数 description: 可选描述。"""
    df = get_df()
    if df is None:
        return "请先上传数据"
    checks = auto_quality_checks(df)
    summary = quality_report_summary(checks)

    failed = [r for r in summary["results"] if not r["passed"]]
    lines = [
        f"质量检测完成！共 {summary['total_checks']} 条规则，"
        f"通过 {summary['passed']}，未通过 {summary['failed']}。"
    ]
    if failed:
        lines.append("\n未通过的检测项：")
        for r in failed[:10]:
            lines.append(f"  ❌ {r['name']}: {r['details']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 创建 Agent
# ═══════════════════════════════════════════════════════════

CLEANING_PROMPT = """你是 DataMind 的数据清洗专家 Agent 🧹

## 你的职责：
1. 先用 tool_check_data 了解数据概况
2. 用 tool_clean_data 执行自动清洗（去重、缺失值、类型推断、异常检测）
3. 用 tool_quality_check 运行质量校验
4. 根据结果生成一份简短的"数据质量体检报告"，包含：
   - 数据质量评分
   - 主要问题和处理措施
   - 残留的风险/警告

## 输出规范：
- 用中文回复
- 以 Markdown 格式组织信息
- 给出清晰的业务建议（如"XX列缺失率高，建议确认数据源"）
- 不要编造数据，所有数值必须来自工具返回"""


def create_cleaning_agent():
    llm = get_llm(temperature=0.0)
    return create_react_agent(
        llm,
        [tool_check_data, tool_clean_data, tool_quality_check],
        prompt=CLEANING_PROMPT,
    )
