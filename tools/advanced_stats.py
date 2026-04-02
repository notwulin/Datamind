"""
高级统计分析工具
功能：中介效应 (Mediation)、调节效应 (Moderation) 检验
所有计算使用强类型 Python 代码，LLM 只负责"总结解读"，不负责"直接计算"
"""
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm


# ═══════════════════════════════════════════════════════════
# 中介效应检验 (Sobel Test)
# ═══════════════════════════════════════════════════════════

def mediation_analysis(
    df: pd.DataFrame,
    x_col: str,
    m_col: str,
    y_col: str,
) -> dict:
    """
    中介效应分析 (Baron & Kenny + Sobel Test)

    模型路径：
        X → Y (总效应 c)
        X → M (路径 a)
        M → Y | X (路径 b)
        X → Y | M (直接效应 c')
        间接效应 = a × b
        中介效应占比 = (c - c') / c

    参数:
        df: 数据集
        x_col: 自变量列名
        m_col: 中介变量列名
        y_col: 因变量列名

    返回: 包含各路径系数和 Sobel 检验结果的字典
    """
    data = df[[x_col, m_col, y_col]].dropna()
    if len(data) < 30:
        return {"error": f"有效样本量不足（{len(data)} < 30），无法进行中介效应分析"}

    # 标准化（便于系数比较）
    for col in [x_col, m_col, y_col]:
        if pd.api.types.is_numeric_dtype(data[col]):
            data[col] = (data[col] - data[col].mean()) / data[col].std()
        else:
            return {"error": f"列 '{col}' 不是数值类型，无法做中介效应分析"}

    # ── Step 1: X → Y (总效应 c) ─────────────────────────
    X1 = sm.add_constant(data[x_col])
    model_c = sm.OLS(data[y_col], X1).fit()
    c = model_c.params.iloc[1]
    c_p = model_c.pvalues.iloc[1]

    # ── Step 2: X → M (路径 a) ───────────────────────────
    model_a = sm.OLS(data[m_col], X1).fit()
    a = model_a.params.iloc[1]
    a_p = model_a.pvalues.iloc[1]
    a_se = model_a.bse.iloc[1]

    # ── Step 3: X + M → Y (路径 b, 直接效应 c') ──────────
    X2 = sm.add_constant(data[[x_col, m_col]])
    model_bc = sm.OLS(data[y_col], X2).fit()
    c_prime = model_bc.params.iloc[1]  # X 的系数（直接效应）
    b = model_bc.params.iloc[2]        # M 的系数（路径 b）
    b_p = model_bc.pvalues.iloc[2]
    b_se = model_bc.bse.iloc[2]

    # ── Sobel Test ────────────────────────────────────────
    indirect = a * b
    sobel_se = np.sqrt(a**2 * b_se**2 + b**2 * a_se**2)
    sobel_z = indirect / sobel_se if sobel_se > 0 else 0
    sobel_p = 2 * (1 - stats.norm.cdf(abs(sobel_z)))

    # 中介效应占比
    mediation_ratio = abs(c - c_prime) / abs(c) if abs(c) > 1e-10 else 0

    # 中介类型判断
    if sobel_p >= 0.05:
        mediation_type = "无中介效应"
    elif abs(c_prime) < 0.05 or (c_p < 0.05 and model_bc.pvalues.iloc[1] >= 0.05):
        mediation_type = "完全中介"
    else:
        mediation_type = "部分中介"

    return {
        "x": x_col, "m": m_col, "y": y_col,
        "n": len(data),
        "path_c": {"coef": round(float(c), 4), "p": round(float(c_p), 4), "label": "总效应 (X→Y)"},
        "path_a": {"coef": round(float(a), 4), "p": round(float(a_p), 4), "label": "路径 a (X→M)"},
        "path_b": {"coef": round(float(b), 4), "p": round(float(b_p), 4), "label": "路径 b (M→Y|X)"},
        "path_c_prime": {"coef": round(float(c_prime), 4), "p": round(float(model_bc.pvalues.iloc[1]), 4), "label": "直接效应 (X→Y|M)"},
        "indirect_effect": round(float(indirect), 4),
        "sobel_z": round(float(sobel_z), 3),
        "sobel_p": round(float(sobel_p), 4),
        "mediation_ratio": round(float(mediation_ratio), 3),
        "mediation_type": mediation_type,
        "conclusion": (
            f"中介效应分析 ({x_col} → {m_col} → {y_col}):\n"
            f"  总效应 c = {c:.3f} (p={c_p:.4f})\n"
            f"  间接效应 a×b = {indirect:.3f} (Sobel Z={sobel_z:.3f}, p={sobel_p:.4f})\n"
            f"  直接效应 c' = {c_prime:.3f}\n"
            f"  中介效应占比 = {mediation_ratio:.1%}\n"
            f"  结论: {mediation_type}"
        ),
    }


# ═══════════════════════════════════════════════════════════
# 调节效应检验 (Moderation / Interaction)
# ═══════════════════════════════════════════════════════════

def moderation_analysis(
    df: pd.DataFrame,
    x_col: str,
    w_col: str,
    y_col: str,
) -> dict:
    """
    调节效应分析（交互项回归）

    模型: Y = β0 + β1·X + β2·W + β3·X×W + ε
    如果 β3 显著，则 W 对 X→Y 有调节效应

    参数:
        df: 数据集
        x_col: 自变量列名
        w_col: 调节变量列名
        y_col: 因变量列名

    返回: 回归分析结果字典
    """
    data = df[[x_col, w_col, y_col]].dropna()
    if len(data) < 30:
        return {"error": f"有效样本量不足（{len(data)} < 30），无法进行调节效应分析"}

    # 处理类别型调节变量（虚拟编码）
    w_is_categorical = not pd.api.types.is_numeric_dtype(data[w_col])
    if w_is_categorical:
        unique_vals = data[w_col].unique()
        if len(unique_vals) > 10:
            return {"error": f"调节变量 '{w_col}' 类别数过多（{len(unique_vals)}），请选择类别数 ≤ 10 的变量"}
        # 虚拟编码
        dummies = pd.get_dummies(data[w_col], prefix=w_col, drop_first=True, dtype=float)
        data = pd.concat([data, dummies], axis=1)
        w_dummy_cols = dummies.columns.tolist()
    else:
        w_dummy_cols = [w_col]

    # 确保 X, Y 数值
    for col in [x_col, y_col]:
        if not pd.api.types.is_numeric_dtype(data[col]):
            return {"error": f"列 '{col}' 不是数值类型"}

    # 中心化数值变量
    x_centered = data[x_col] - data[x_col].mean()

    if not w_is_categorical:
        w_centered = data[w_col] - data[w_col].mean()
        interaction = x_centered * w_centered
        X = sm.add_constant(pd.DataFrame({
            x_col: x_centered,
            w_col: w_centered,
            f"{x_col}×{w_col}": interaction,
        }))
    else:
        interaction_cols = {}
        for wc in w_dummy_cols:
            interaction_cols[f"{x_col}×{wc}"] = x_centered * data[wc]
        X = sm.add_constant(pd.concat([
            pd.DataFrame({x_col: x_centered}),
            data[w_dummy_cols],
            pd.DataFrame(interaction_cols),
        ], axis=1))

    model = sm.OLS(data[y_col], X).fit()

    # 提取交互项结果
    interaction_terms = [c for c in model.params.index if "×" in c]
    interaction_significant = any(model.pvalues[c] < 0.05 for c in interaction_terms)

    result = {
        "x": x_col, "w": w_col, "y": y_col,
        "n": len(data),
        "r_squared": round(float(model.rsquared), 4),
        "adj_r_squared": round(float(model.rsquared_adj), 4),
        "f_stat": round(float(model.fvalue), 3),
        "f_p": round(float(model.f_pvalue), 4),
        "coefficients": {},
        "interaction_significant": interaction_significant,
        "w_is_categorical": w_is_categorical,
    }

    for name in model.params.index:
        if name == "const":
            continue
        result["coefficients"][name] = {
            "coef": round(float(model.params[name]), 4),
            "se": round(float(model.bse[name]), 4),
            "t": round(float(model.tvalues[name]), 3),
            "p": round(float(model.pvalues[name]), 4),
        }

    # 生成结论
    if interaction_significant:
        int_details = ", ".join(
            f"{c}: β={model.params[c]:.3f}, p={model.pvalues[c]:.4f}"
            for c in interaction_terms
        )
        conclusion = (
            f"调节效应显著！{w_col} 显著调节了 {x_col} 对 {y_col} 的影响。\n"
            f"交互项：{int_details}\n"
            f"模型 R² = {model.rsquared:.3f}"
        )
    else:
        conclusion = (
            f"调节效应不显著。{w_col} 未显著改变 {x_col} 对 {y_col} 的影响方向或强度。\n"
            f"模型 R² = {model.rsquared:.3f}"
        )

    result["conclusion"] = conclusion
    return result
