"""
用户分析模块
功能：RFM 分层、Cohort 留存、留存率分析、流失预警、LTV 预测
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ═══════════════════════════════════════════════════════════
# RFM 分层分析
# ═══════════════════════════════════════════════════════════
def rfm_analysis(
    df: pd.DataFrame, user_col: str, date_col: str, amount_col: str
) -> tuple[pd.DataFrame, object]:
    """RFM分析，返回 (rfm_df, plotly图表)"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    snapshot_date = df[date_col].max() + pd.Timedelta(days=1)

    rfm = (
        df.groupby(user_col)
        .agg(
            Recency=(date_col, lambda x: (snapshot_date - x.max()).days),
            Frequency=(date_col, "count"),
            Monetary=(amount_col, "sum"),
        )
        .reset_index()
    )

    # 分位数打分 1-4（越高越好）
    rfm["R"] = pd.qcut(rfm["Recency"], 4, labels=[4, 3, 2, 1], duplicates="drop").astype(int)
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 4, labels=[1, 2, 3, 4], duplicates="drop").astype(int)
    rfm["RFM_Score"] = rfm["R"] + rfm["F"] + rfm["M"]

    # 用户分层
    def segment(row):
        if row["R"] >= 3 and row["F"] >= 3:
            return "高价值用户"
        if row["R"] >= 3 and row["F"] < 3:
            return "潜力用户"
        if row["R"] < 3 and row["F"] >= 3:
            return "流失风险"
        return "沉睡用户"

    rfm["Segment"] = rfm.apply(segment, axis=1)

    # 可视化 — 气泡图 + 分层饼图
    color_map = {
        "高价值用户": "#10B981",
        "潜力用户": "#3B82F6",
        "流失风险": "#EF4444",
        "沉睡用户": "#6B7280",
    }

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "scatter"}, {"type": "pie"}]],
        subplot_titles=("RFM 用户分层气泡图", "用户层级占比"),
        column_widths=[0.65, 0.35],
    )

    # 左：气泡图
    for seg_name, color in color_map.items():
        seg_data = rfm[rfm["Segment"] == seg_name]
        if len(seg_data) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=seg_data["Recency"],
                y=seg_data["Frequency"],
                mode="markers",
                marker=dict(
                    size=np.clip(seg_data["Monetary"] / seg_data["Monetary"].max() * 30, 6, 40),
                    color=color,
                    opacity=0.7,
                    line=dict(width=1, color="white"),
                ),
                name=seg_name,
                text=seg_data[user_col],
                hovertemplate=f"<b>{seg_name}</b><br>"
                + "用户: %{text}<br>Recency: %{x}天<br>"
                + "Frequency: %{y}次<br><extra></extra>",
            ),
            row=1, col=1,
        )

    # 右：饼图
    seg_counts = rfm["Segment"].value_counts()
    fig.add_trace(
        go.Pie(
            labels=seg_counts.index,
            values=seg_counts.values,
            marker=dict(colors=[color_map.get(s, "#999") for s in seg_counts.index]),
            textinfo="label+percent",
            hole=0.4,
        ),
        row=1, col=2,
    )

    fig.update_layout(
        height=450,
        showlegend=True,
        template="plotly_white",
        font=dict(family="sans-serif"),
    )
    fig.update_xaxes(title_text="Recency (天)", row=1, col=1)
    fig.update_yaxes(title_text="Frequency (次)", row=1, col=1)

    return rfm, fig


# ═══════════════════════════════════════════════════════════
# Cohort 留存分析
# ═══════════════════════════════════════════════════════════
def cohort_analysis(
    df: pd.DataFrame, user_col: str, date_col: str
) -> tuple[pd.DataFrame, object]:
    """Cohort 留存分析，返回 (cohort矩阵, 热图)"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["CohortMonth"] = df.groupby(user_col)[date_col].transform("min").dt.to_period("M")
    df["OrderMonth"] = df[date_col].dt.to_period("M")
    df["CohortIndex"] = (df["OrderMonth"] - df["CohortMonth"]).apply(lambda x: x.n)

    cohort_data = df.groupby(["CohortMonth", "CohortIndex"])[user_col].nunique().reset_index()
    cohort_pivot = cohort_data.pivot(index="CohortMonth", columns="CohortIndex", values=user_col)

    cohort_size = cohort_pivot.iloc[:, 0]
    retention = cohort_pivot.divide(cohort_size, axis=0).round(3) * 100
    retention.index = retention.index.astype(str)

    fig = go.Figure(
        data=go.Heatmap(
            z=retention.values,
            x=[f"第{i}月" for i in retention.columns],
            y=retention.index,
            colorscale="Blues",
            text=retention.round(1).astype(str) + "%",
            texttemplate="%{text}",
            hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Cohort 用户留存热图",
        xaxis_title="距首购月数",
        yaxis_title="首购月份",
        height=max(300, len(retention) * 35 + 100),
        template="plotly_white",
    )
    return retention, fig


# ═══════════════════════════════════════════════════════════
# 留存率分析（按日/周/月维度）
# ═══════════════════════════════════════════════════════════
def retention_analysis(
    df: pd.DataFrame,
    user_col: str,
    date_col: str,
    period: str = "M",  # 'D', 'W', 'M'
) -> tuple[pd.DataFrame, object]:
    """
    留存率趋势分析
    返回 (retention_df, 折线图)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    period_labels = {"D": "日", "W": "周", "M": "月"}
    label = period_labels.get(period, "月")

    # 每个用户的首次活跃期
    df["period"] = df[date_col].dt.to_period(period)
    first_period = df.groupby(user_col)["period"].min().rename("first_period")
    df = df.merge(first_period, on=user_col)
    df["period_offset"] = (df["period"] - df["first_period"]).apply(lambda x: x.n)

    # 各期留存用户数
    total_users = df[user_col].nunique()
    retention_data = []
    max_offset = min(int(df["period_offset"].max()), 12)

    for offset in range(max_offset + 1):
        users_at_offset = df[df["period_offset"] == offset][user_col].nunique()
        retention_data.append(
            {
                f"第N{label}": offset,
                "留存用户数": users_at_offset,
                "留存率": round(users_at_offset / total_users * 100, 1),
            }
        )

    ret_df = pd.DataFrame(retention_data)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ret_df[f"第N{label}"],
            y=ret_df["留存率"],
            mode="lines+markers+text",
            text=ret_df["留存率"].apply(lambda x: f"{x}%"),
            textposition="top center",
            line=dict(color="#3B82F6", width=3),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.1)",
        )
    )
    fig.update_layout(
        title=f"用户{label}留存率趋势",
        xaxis_title=f"第 N {label}",
        yaxis_title="留存率 (%)",
        yaxis_range=[0, 105],
        height=350,
        template="plotly_white",
    )
    return ret_df, fig


# ═══════════════════════════════════════════════════════════
# 流失预警
# ═══════════════════════════════════════════════════════════
def churn_prediction(
    df: pd.DataFrame,
    user_col: str,
    date_col: str,
    churn_days: int = 30,
) -> tuple[pd.DataFrame, object]:
    """
    基于规则的流失预警（N 天未活跃为流失风险）
    返回 (用户状态df, 环形图)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    snapshot = df[date_col].max() + pd.Timedelta(days=1)

    user_last = df.groupby(user_col)[date_col].max().reset_index()
    user_last.columns = [user_col, "last_active"]
    user_last["days_inactive"] = (snapshot - user_last["last_active"]).dt.days

    # 状态分层
    def classify(days):
        if days <= churn_days * 0.3:
            return "活跃用户"
        elif days <= churn_days * 0.7:
            return "沉默用户"
        elif days <= churn_days:
            return "流失风险"
        else:
            return "已流失"

    user_last["status"] = user_last["days_inactive"].apply(classify)

    color_map = {
        "活跃用户": "#10B981",
        "沉默用户": "#F59E0B",
        "流失风险": "#EF4444",
        "已流失": "#6B7280",
    }

    status_counts = user_last["status"].value_counts()
    fig = go.Figure(
        go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=0.55,
            marker=dict(colors=[color_map.get(s, "#999") for s in status_counts.index]),
            textinfo="label+value+percent",
            textposition="outside",
        )
    )
    # 中心文字
    total = len(user_last)
    churn_risk = status_counts.get("流失风险", 0) + status_counts.get("已流失", 0)
    fig.update_layout(
        title=f"用户状态分布（流失标准：{churn_days}天未活跃）",
        annotations=[
            dict(
                text=f"<b>{churn_risk}</b><br>风险用户",
                x=0.5, y=0.5, font_size=16, showarrow=False,
            )
        ],
        height=400,
        template="plotly_white",
    )
    return user_last, fig


# ═══════════════════════════════════════════════════════════
# LTV 预测（简单模型）
# ═══════════════════════════════════════════════════════════
def ltv_prediction(
    df: pd.DataFrame,
    user_col: str,
    date_col: str,
    amount_col: str,
) -> tuple[pd.DataFrame, object]:
    """
    基于历史 ARPU × 预估生命周期的 LTV 估算
    返回 (用户LTV df, 分布图)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    user_metrics = df.groupby(user_col).agg(
        first_order=(date_col, "min"),
        last_order=(date_col, "max"),
        order_count=(date_col, "count"),
        total_revenue=(amount_col, "sum"),
    ).reset_index()

    # 用户活跃天数（最少算 1 天）
    user_metrics["active_days"] = (
        (user_metrics["last_order"] - user_metrics["first_order"]).dt.days + 1
    )

    # 月均消费
    user_metrics["monthly_revenue"] = (
        user_metrics["total_revenue"] / np.maximum(user_metrics["active_days"] / 30, 1)
    ).round(2)

    # 预估生命周期月数（活跃天数换算，加衰减因子）
    user_metrics["est_lifetime_months"] = np.minimum(
        user_metrics["active_days"] / 30 * 1.5, 24
    ).round(1)

    # LTV = 月均消费 × 预估生命周期
    user_metrics["LTV"] = (
        user_metrics["monthly_revenue"] * user_metrics["est_lifetime_months"]
    ).round(2)

    # LTV 分层
    user_metrics["LTV_Tier"] = pd.qcut(
        user_metrics["LTV"], q=4,
        labels=["低 LTV", "中低 LTV", "中高 LTV", "高 LTV"],
        duplicates="drop",
    )

    # 可视化
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "histogram"}, {"type": "pie"}]],
        subplot_titles=("LTV 分布直方图", "LTV 层级占比"),
        column_widths=[0.6, 0.4],
    )
    fig.add_trace(
        go.Histogram(
            x=user_metrics["LTV"],
            nbinsx=30,
            marker_color="#3B82F6",
            opacity=0.8,
        ),
        row=1, col=1,
    )

    tier_counts = user_metrics["LTV_Tier"].value_counts()
    tier_colors = {"低 LTV": "#EF4444", "中低 LTV": "#F59E0B", "中高 LTV": "#3B82F6", "高 LTV": "#10B981"}
    fig.add_trace(
        go.Pie(
            labels=tier_counts.index,
            values=tier_counts.values,
            marker=dict(colors=[tier_colors.get(t, "#999") for t in tier_counts.index]),
            hole=0.4,
            textinfo="label+percent",
        ),
        row=1, col=2,
    )

    avg_ltv = user_metrics["LTV"].mean()
    fig.update_layout(
        title=f"用户 LTV 分析 · 平均 LTV = ¥{avg_ltv:,.0f}",
        height=400,
        template="plotly_white",
    )
    fig.update_xaxes(title_text="LTV (¥)", row=1, col=1)
    fig.update_yaxes(title_text="用户数", row=1, col=1)

    return user_metrics, fig