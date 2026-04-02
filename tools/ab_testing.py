"""
A/B 测试分析模块
功能：假设检验、样本量计算、置信区间、多指标校正、连续型指标 t 检验
"""
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.power import NormalIndPower, TTestIndPower
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ═══════════════════════════════════════════════════════════
# 比例检验（原有功能增强）
# ═══════════════════════════════════════════════════════════
def run_ab_test(
    n_control: int,
    n_treatment: int,
    conv_control: float,
    conv_treatment: float,
    alpha: float = 0.05,
) -> dict:
    """完整A/B测试：假设检验 + 功效分析 + 置信区间"""

    # Z 检验
    count = np.array([int(conv_control * n_control), int(conv_treatment * n_treatment)])
    nobs = np.array([n_control, n_treatment])
    z_stat, p_value = proportions_ztest(count, nobs)

    # 置信区间（Wilson score）
    def wilson_ci(p, n, z=1.96):
        denom = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denom
        margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
        return center - margin, center + margin

    ci_ctrl = wilson_ci(conv_control, n_control)
    ci_trt = wilson_ci(conv_treatment, n_treatment)

    # 提升幅度 & 功效
    lift = (conv_treatment - conv_control) / conv_control * 100 if conv_control > 0 else 0
    effect = abs(conv_treatment - conv_control)
    pooled_var = (conv_control * (1 - conv_control) + conv_treatment * (1 - conv_treatment)) / 2
    effect_size = effect / np.sqrt(pooled_var) if pooled_var > 0 else 0

    power_analysis = NormalIndPower()
    try:
        power = power_analysis.solve_power(
            effect_size=effect_size,
            nobs1=n_control,
            ratio=n_treatment / n_control,
            alpha=alpha,
        )
    except Exception:
        power = 0.0

    return {
        "significant": p_value < alpha,
        "p_value": round(p_value, 4),
        "z_stat": round(z_stat, 3),
        "lift_pct": round(lift, 2),
        "power": round(power, 3),
        "ci_control": (round(ci_ctrl[0], 4), round(ci_ctrl[1], 4)),
        "ci_treatment": (round(ci_trt[0], 4), round(ci_trt[1], 4)),
        "conclusion": (
            f"差异{'显著' if p_value < alpha else '不显著'}"
            f"（p={p_value:.4f}），实验组提升 {lift:+.1f}%"
        ),
    }


# ═══════════════════════════════════════════════════════════
# 样本量计算器
# ═══════════════════════════════════════════════════════════
def sample_size_calculator(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0,
) -> dict:
    """
    计算达到指定 MDE 所需的最小样本量
    
    参数:
        baseline_rate: 基线转化率
        mde: 最小可检测效应（绝对值，如 0.01 表示 1%）
        alpha: 显著性水平
        power: 统计功效
        ratio: 实验组与对照组的样本量比
    """
    target_rate = baseline_rate + mde
    pooled_var = (baseline_rate * (1 - baseline_rate) + target_rate * (1 - target_rate)) / 2
    effect_size = abs(mde) / np.sqrt(pooled_var) if pooled_var > 0 else 0

    analysis = NormalIndPower()
    try:
        n_per_group = int(np.ceil(analysis.solve_power(
            effect_size=effect_size,
            power=power,
            alpha=alpha,
            ratio=ratio,
        )))
    except Exception:
        n_per_group = 0

    n_treatment = int(np.ceil(n_per_group * ratio))
    total = n_per_group + n_treatment

    # 不同 MDE 下的样本量曲线数据
    mde_range = np.linspace(max(mde * 0.3, 0.001), mde * 3, 20)
    curve_data = []
    for m in mde_range:
        t = baseline_rate + m
        pv = (baseline_rate * (1 - baseline_rate) + t * (1 - t)) / 2
        es = abs(m) / np.sqrt(pv) if pv > 0 else 0
        try:
            n = int(np.ceil(analysis.solve_power(
                effect_size=es, power=power, alpha=alpha, ratio=ratio,
            )))
        except Exception:
            n = 0
        curve_data.append({"mde": m, "sample_size": n})

    return {
        "n_control": n_per_group,
        "n_treatment": n_treatment,
        "total": total,
        "effect_size": round(effect_size, 4),
        "baseline": baseline_rate,
        "target_rate": target_rate,
        "mde": mde,
        "alpha": alpha,
        "power": power,
        "curve_data": curve_data,
    }


# ═══════════════════════════════════════════════════════════
# 多指标校正
# ═══════════════════════════════════════════════════════════
def multi_metric_correction(
    p_values: list[float],
    metric_names: list[str],
    method: str = "bonferroni",
    alpha: float = 0.05,
) -> dict:
    """
    多指标 p 值校正
    
    参数:
        p_values: 各指标的原始 p 值列表
        metric_names: 各指标名称列表
        method: 'bonferroni' | 'holm'
        alpha: 显著性水平
    """
    n = len(p_values)
    results = []

    if method == "bonferroni":
        corrected_alpha = alpha / n
        for name, p in zip(metric_names, p_values):
            results.append({
                "metric": name,
                "p_value": round(p, 4),
                "corrected_alpha": round(corrected_alpha, 4),
                "significant": p < corrected_alpha,
            })
    elif method == "holm":
        # Holm–Bonferroni 逐步校正
        sorted_indices = np.argsort(p_values)
        for rank, idx in enumerate(sorted_indices):
            corrected_alpha = alpha / (n - rank)
            results.append({
                "metric": metric_names[idx],
                "p_value": round(p_values[idx], 4),
                "corrected_alpha": round(corrected_alpha, 4),
                "significant": p_values[idx] < corrected_alpha,
                "rank": rank + 1,
            })
    else:
        for name, p in zip(metric_names, p_values):
            results.append({
                "metric": name,
                "p_value": round(p, 4),
                "corrected_alpha": alpha,
                "significant": p < alpha,
            })

    return {
        "method": method,
        "original_alpha": alpha,
        "n_metrics": n,
        "n_significant": sum(1 for r in results if r["significant"]),
        "results": results,
    }


# ═══════════════════════════════════════════════════════════
# 连续型指标 t 检验
# ═══════════════════════════════════════════════════════════
def run_ttest(
    control_data: list | np.ndarray,
    treatment_data: list | np.ndarray,
    alpha: float = 0.05,
    metric_name: str = "指标",
) -> dict:
    """
    独立样本 t 检验（适用于均值类指标：ARPU、停留时长等）
    """
    control = np.array(control_data)
    treatment = np.array(treatment_data)

    t_stat, p_value = stats.ttest_ind(control, treatment)

    ctrl_mean, trt_mean = control.mean(), treatment.mean()
    ctrl_std, trt_std = control.std(ddof=1), treatment.std(ddof=1)
    lift = (trt_mean - ctrl_mean) / ctrl_mean * 100 if ctrl_mean != 0 else 0

    # 95% CI for difference
    se_diff = np.sqrt(ctrl_std**2 / len(control) + trt_std**2 / len(treatment))
    ci_diff = (
        round(trt_mean - ctrl_mean - 1.96 * se_diff, 4),
        round(trt_mean - ctrl_mean + 1.96 * se_diff, 4),
    )

    # 功效
    pooled_std = np.sqrt((ctrl_std**2 + trt_std**2) / 2)
    effect_size = abs(trt_mean - ctrl_mean) / pooled_std if pooled_std > 0 else 0
    try:
        power = TTestIndPower().solve_power(
            effect_size=effect_size,
            nobs1=len(control),
            ratio=len(treatment) / len(control),
            alpha=alpha,
        )
    except Exception:
        power = 0.0

    return {
        "metric": metric_name,
        "significant": p_value < alpha,
        "t_stat": round(t_stat, 3),
        "p_value": round(p_value, 4),
        "control_mean": round(ctrl_mean, 4),
        "treatment_mean": round(trt_mean, 4),
        "lift_pct": round(lift, 2),
        "ci_diff": ci_diff,
        "power": round(power, 3),
        "conclusion": (
            f"{metric_name}：差异{'显著' if p_value < alpha else '不显著'}"
            f"（p={p_value:.4f}），实验组提升 {lift:+.1f}%"
        ),
    }