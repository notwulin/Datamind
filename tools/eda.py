"""
EDA 探索性分析工具层
功能：自动统计摘要、相关性分析、分布分析、漏斗转化、异常洞察
所有函数返回 (数据结果, Plotly 图表) 或 (数据结果, None)
LLM 只负责"解读业务含义"，不负责"计算数值"
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats


# ═══════════════════════════════════════════════════════════
# 自动 EDA 摘要
# ═══════════════════════════════════════════════════════════

def run_eda_summary(df: pd.DataFrame) -> dict:
    """
    全自动 EDA 摘要，返回结构化结果字典
    LLM 基于此字典生成业务 Insight
    """
    result = {
        "shape": {"rows": len(df), "cols": len(df.columns)},
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": {},
        "numeric_stats": {},
        "categorical_stats": {},
        "high_correlation_pairs": [],
        "skewed_columns": [],
        "potential_id_columns": [],
    }

    # ── 缺失值分析 ────────────────────────────────────────
    for col in df.columns:
        null_pct = df[col].isna().mean()
        if null_pct > 0:
            result["missing"][col] = round(null_pct * 100, 1)

    # ── 数值列分析 ────────────────────────────────────────
    num_cols = df.select_dtypes(include="number").columns.tolist()
    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 5:
            continue
        skewness = float(series.skew())
        result["numeric_stats"][col] = {
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "std": round(float(series.std()), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "skewness": round(skewness, 2),
            "zeros_pct": round(float((series == 0).mean()) * 100, 1),
        }
        if abs(skewness) > 1.5:
            result["skewed_columns"].append({"column": col, "skewness": round(skewness, 2)})

    # ── 高相关性对 ────────────────────────────────────────
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                r = corr.iloc[i, j]
                if abs(r) > 0.7:
                    result["high_correlation_pairs"].append({
                        "col_a": num_cols[i],
                        "col_b": num_cols[j],
                        "correlation": round(float(r), 3),
                    })

    # ── 类别列分析 ────────────────────────────────────────
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for col in cat_cols:
        n_unique = df[col].nunique()
        # 高基数检测（可能是 ID 列）
        if n_unique > len(df) * 0.8:
            result["potential_id_columns"].append(col)
            continue
        top5 = df[col].value_counts().head(5)
        result["categorical_stats"][col] = {
            "n_unique": n_unique,
            "top5": {str(k): int(v) for k, v in top5.items()},
            "mode": str(top5.index[0]) if len(top5) > 0 else None,
            "mode_pct": round(float(top5.iloc[0] / len(df)) * 100, 1) if len(top5) > 0 else 0,
        }

    return result


# ═══════════════════════════════════════════════════════════
# 相关性矩阵热图
# ═══════════════════════════════════════════════════════════

def correlation_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, go.Figure | None]:
    """相关性分析，返回 (相关矩阵 DataFrame, 热图)"""
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if len(num_cols) < 2:
        return pd.DataFrame(), None

    # 最多取 15 列避免图表过密
    if len(num_cols) > 15:
        num_cols = num_cols[:15]

    corr = df[num_cols].corr().round(3)

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale="RdBu_r",
        zmid=0,
        text=corr.round(2).astype(str),
        texttemplate="%{text}",
        hovertemplate="%{x} × %{y}: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title="数值列相关性矩阵",
        height=max(400, len(num_cols) * 40 + 100),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return corr, fig


# ═══════════════════════════════════════════════════════════
# 单列分布分析
# ═══════════════════════════════════════════════════════════

def distribution_analysis(df: pd.DataFrame, col: str) -> tuple[dict, go.Figure]:
    """
    单列深度分布分析
    返回 (统计结果字典, 组合图表：直方图+箱线图)
    """
    series = df[col].dropna()
    result = {
        "column": col,
        "count": len(series),
        "mean": round(float(series.mean()), 4),
        "median": round(float(series.median()), 4),
        "std": round(float(series.std()), 4),
        "skewness": round(float(series.skew()), 4),
        "kurtosis": round(float(series.kurtosis()), 4),
    }

    # 正态性检验 (Shapiro-Wilk, 样本量 > 5000 用 K-S)
    if len(series) <= 5000:
        stat, p = stats.shapiro(series.sample(min(len(series), 5000)))
        result["normality_test"] = "Shapiro-Wilk"
    else:
        stat, p = stats.kstest(series, "norm", args=(series.mean(), series.std()))
        result["normality_test"] = "Kolmogorov-Smirnov"
    result["normality_stat"] = round(float(stat), 4)
    result["normality_p"] = round(float(p), 4)
    result["is_normal"] = p > 0.05

    # 组合图表：上方直方图 + 下方箱线图
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.75, 0.25],
        shared_xaxes=True,
        vertical_spacing=0.05,
    )
    fig.add_trace(
        go.Histogram(x=series, nbinsx=40, marker_color="#3B82F6", opacity=0.8, name="分布"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Box(x=series, marker_color="#8B5CF6", name="箱线图", boxmean=True),
        row=2, col=1,
    )
    fig.update_layout(
        title=f"'{col}' 分布分析",
        height=400,
        showlegend=False,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return result, fig


# ═══════════════════════════════════════════════════════════
# 漏斗转化分析
# ═══════════════════════════════════════════════════════════

def funnel_analysis(
    stage_names: list[str],
    stage_values: list[int],
) -> tuple[dict, go.Figure]:
    """
    漏斗分析
    参数:
        stage_names: 各阶段名称列表
        stage_values: 各阶段数量列表
    返回: (分析结果, 漏斗图)
    """
    result = {"stages": []}
    for i, (name, val) in enumerate(zip(stage_names, stage_values)):
        stage = {
            "name": name,
            "value": val,
            "overall_rate": round(val / stage_values[0] * 100, 1) if stage_values[0] > 0 else 0,
        }
        if i > 0:
            prev_val = stage_values[i - 1]
            stage["step_rate"] = round(val / prev_val * 100, 1) if prev_val > 0 else 0
            stage["drop_off"] = prev_val - val
            stage["drop_off_pct"] = round((prev_val - val) / prev_val * 100, 1) if prev_val > 0 else 0
        result["stages"].append(stage)

    # 找到最大流失环节
    max_drop = max(result["stages"][1:], key=lambda x: x.get("drop_off_pct", 0))
    result["bottleneck"] = max_drop["name"]
    result["bottleneck_drop_pct"] = max_drop["drop_off_pct"]

    # 漏斗图
    fig = go.Figure(go.Funnel(
        y=stage_names,
        x=stage_values,
        textinfo="value+percent initial",
        marker=dict(color=["#3B82F6", "#6366F1", "#8B5CF6", "#A855F7", "#C084FC",
                           "#D8B4FE", "#E9D5FF"][:len(stage_names)]),
        connector=dict(line=dict(color="#475569", width=1)),
    ))
    fig.update_layout(
        title=f"漏斗转化分析 · 瓶颈：{max_drop['name']}（流失 {max_drop['drop_off_pct']}%）",
        height=400,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return result, fig


# ═══════════════════════════════════════════════════════════
# 异常洞察检测
# ═══════════════════════════════════════════════════════════

def detect_anomalies_insight(df: pd.DataFrame) -> list[dict]:
    """
    自动检测数据中的异常和亮点，返回结构化洞察列表
    每个洞察包含: type(异常/亮点/警告), column, description, severity(high/medium/low)
    LLM 基于此列表生成自然语言 Insight
    """
    insights = []
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # ── 数值列异常 ────────────────────────────────────────
    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue

        # 极端偏态
        skew = series.skew()
        if abs(skew) > 3:
            insights.append({
                "type": "warning",
                "column": col,
                "description": f"'{col}' 严重偏态（偏度={skew:.1f}），可能需要对数变换",
                "severity": "high",
                "metric": {"skewness": round(float(skew), 2)},
            })

        # 零值占比过高
        zero_pct = (series == 0).mean()
        if zero_pct > 0.5:
            insights.append({
                "type": "warning",
                "column": col,
                "description": f"'{col}' 零值占比 {zero_pct:.0%}，可能存在数据质量问题",
                "severity": "medium",
                "metric": {"zero_pct": round(float(zero_pct), 3)},
            })

        # IQR 异常值
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outlier_pct = ((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).mean()
            if outlier_pct > 0.1:
                insights.append({
                    "type": "anomaly",
                    "column": col,
                    "description": f"'{col}' 异常值占比 {outlier_pct:.1%}，远超正常水平",
                    "severity": "high",
                    "metric": {"outlier_pct": round(float(outlier_pct), 3)},
                })

    # ── 类别列异常 ────────────────────────────────────────
    for col in cat_cols:
        vc = df[col].value_counts()
        if len(vc) < 2:
            continue

        # 单值主导
        top_pct = vc.iloc[0] / len(df)
        if top_pct > 0.9:
            insights.append({
                "type": "warning",
                "column": col,
                "description": f"'{col}' 被单一值 '{vc.index[0]}' 主导（占 {top_pct:.0%}），分析价值有限",
                "severity": "low",
                "metric": {"dominant_value": str(vc.index[0]), "pct": round(float(top_pct), 3)},
            })

        # 类别不均衡
        if len(vc) >= 3:
            min_pct = vc.iloc[-1] / len(df)
            max_pct = vc.iloc[0] / len(df)
            if max_pct / max(min_pct, 0.001) > 50:
                insights.append({
                    "type": "anomaly",
                    "column": col,
                    "description": f"'{col}' 类别严重不均衡，最多类别占 {max_pct:.0%}，最少仅 {min_pct:.1%}",
                    "severity": "medium",
                    "metric": {"imbalance_ratio": round(float(max_pct / max(min_pct, 0.001)), 1)},
                })

    # ── 缺失值洞察 ────────────────────────────────────────
    high_missing = [(col, df[col].isna().mean()) for col in df.columns if df[col].isna().mean() > 0.3]
    if high_missing:
        cols_str = ", ".join(f"'{c}' ({p:.0%})" for c, p in sorted(high_missing, key=lambda x: -x[1]))
        insights.append({
            "type": "warning",
            "column": "multiple",
            "description": f"以下列缺失率超过 30%：{cols_str}",
            "severity": "high",
            "metric": {"columns": [c for c, _ in high_missing]},
        })

    return insights
