"""
🧪 实验分析 Agent (AB Test Agent)
职责：严谨的统计学检验，自动生成业务级结论
输出："实验显著提升转化率(p<0.05)，建议全量上线"
Temperature: 0.0
"""
import os
from dotenv import load_dotenv
from langchain.tools import tool
from utils.llm_factory import get_llm
from langgraph.prebuilt import create_react_agent
from tools.ab_testing import (
    run_ab_test, sample_size_calculator, multi_metric_correction, run_ttest,
)
from utils.data_store import get_df, put

load_dotenv()


# ═══════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════

@tool
def tool_ab_test(
    n_control: int, n_treatment: int,
    conv_control: float, conv_treatment: float,
    alpha: float = 0.05,
) -> str:
    """A/B 测试比例检验（Z 检验）。
    参数：n_control=对照组样本量, n_treatment=实验组样本量,
    conv_control=对照组转化率(0-1), conv_treatment=实验组转化率(0-1),
    alpha=显著性水平(默认0.05)"""
    result = run_ab_test(n_control, n_treatment, conv_control, conv_treatment, alpha)
    put("ab_result", result)
    return (
        f"A/B测试结果：\n{result['conclusion']}\n"
        f"- Z统计量：{result['z_stat']}\n"
        f"- p值：{result['p_value']}\n"
        f"- 提升幅度：{result['lift_pct']:+.1f}%\n"
        f"- 统计功效：{result['power']:.1%}\n"
        f"- 对照组95%CI：{result['ci_control']}\n"
        f"- 实验组95%CI：{result['ci_treatment']}"
    )


@tool
def tool_ttest(
    control_values: str,
    treatment_values: str,
    metric_name: str = "指标",
    alpha: float = 0.05,
) -> str:
    """连续指标 t 检验（适用均值类指标：ARPU、停留时长等）。
    参数：control_values=对照组数值逗号分隔, treatment_values=实验组数值逗号分隔,
    metric_name=指标名称, alpha=显著性水平"""
    try:
        ctrl = [float(x.strip()) for x in control_values.split(",")]
        trt = [float(x.strip()) for x in treatment_values.split(",")]
    except ValueError:
        return "数值格式错误，请用逗号分隔数字"

    result = run_ttest(ctrl, trt, alpha=alpha, metric_name=metric_name)
    put("ttest_result", result)
    return (
        f"t 检验结果：\n{result['conclusion']}\n"
        f"- t统计量：{result['t_stat']}\n"
        f"- p值：{result['p_value']}\n"
        f"- 对照组均值：{result['control_mean']}\n"
        f"- 实验组均值：{result['treatment_mean']}\n"
        f"- 差异95%CI：{result['ci_diff']}\n"
        f"- 统计功效：{result['power']:.1%}"
    )


@tool
def tool_sample_size(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> str:
    """计算 A/B 测试所需最小样本量。
    参数：baseline_rate=基线转化率, mde=最小可检测效应(绝对值如0.01=1%),
    alpha=显著性水平, power=统计功效"""
    result = sample_size_calculator(baseline_rate, mde, alpha, power)
    put("sample_size_result", result)
    return (
        f"样本量计算结果：\n"
        f"- 基线 {result['baseline']:.1%} → 目标 {result['target_rate']:.1%}\n"
        f"- 每组最少样本量：{result['n_control']:,}\n"
        f"- 总计最少样本量：{result['total']:,}\n"
        f"- 效应量：{result['effect_size']}"
    )


@tool
def tool_multi_correction(
    metric_names: str,
    p_values: str,
    method: str = "holm",
    alpha: float = 0.05,
) -> str:
    """多指标 p 值校正（避免多重检验假阳性）。
    参数：metric_names=指标名逗号分隔, p_values=各p值逗号分隔,
    method='bonferroni'或'holm'(推荐), alpha=显著性水平"""
    names = [s.strip() for s in metric_names.split(",")]
    pvals = [float(s.strip()) for s in p_values.split(",")]
    if len(names) != len(pvals):
        return "指标名和p值数目不匹配"

    result = multi_metric_correction(pvals, names, method=method, alpha=alpha)
    put("multi_correction_result", result)

    lines = [f"{method.upper()} 校正结果（{result['n_significant']}/{result['n_metrics']} 个显著）："]
    for r in result["results"]:
        sig = "✅ 显著" if r["significant"] else "❌ 不显著"
        lines.append(f"  · {r['metric']}: p={r['p_value']}, 校正阈值={r['corrected_alpha']} → {sig}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 创建 Agent
# ═══════════════════════════════════════════════════════════

AB_PROMPT = """你是 DataMind 的实验分析专家 Agent 🧪

## 你的职责：
执行严谨的统计学检验，输出业务级结论。

## 核心原则：
1. **所有统计计算由工具完成**，你只负责解读结论
2. 不要自行计算 p 值、z 统计量等任何数学公式
3. 结论必须包含：
   - 是否显著（p < α？）
   - 业务影响（提升/下降了多少？）
   - 行动建议（全量上线 / 继续观测 / 放弃实验）
   - 统计功效评估（样本量是否充足？）

## 可用工具：
- tool_ab_test: 比例检验（转化率等比例型指标）
- tool_ttest: t 检验（ARPU、时长等均值型指标）
- tool_sample_size: 样本量计算器
- tool_multi_correction: 多指标校正

## 行动建议模板：
- p < 0.05 且 power > 0.8 → "实验效果显著且统计可靠，建议全量上线"
- p < 0.05 但 power < 0.8 → "效果显著但统计功效不足，建议扩大样本继续验证"
- p >= 0.05 → "未检测到显著差异，建议继续观测或调整实验方案"

## 输出规范：
- 中文回复，Markdown 格式
- 不要编造数据"""


def create_ab_agent():
    llm = get_llm(temperature=0.0)
    return create_react_agent(
        llm,
        [tool_ab_test, tool_ttest, tool_sample_size, tool_multi_correction],
        prompt=AB_PROMPT,
    )
