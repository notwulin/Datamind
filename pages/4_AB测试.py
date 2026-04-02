import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from tools.ab_testing import run_ab_test, sample_size_calculator, multi_metric_correction, run_ttest

st.set_page_config(page_title="A/B 测试 - DataMind", page_icon="⚗️", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()


st.markdown("## ⚗️ A/B 测试分析")
st.caption("假设检验 · t 检验 · 样本量计算 · 多指标校正")

tab_test, tab_ttest, tab_sample, tab_multi = st.tabs(
    ["🧪 比例检验", "📊 t 检验", "📐 样本量计算器", "🔗 多指标校正"]
)

# ═══════════════════════════════════════════════════════════
# Tab 1: 比例检验（Z 检验）
# ═══════════════════════════════════════════════════════════
with tab_test:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔵 对照组")
        n_ctrl = st.number_input("样本量", value=5000, step=100, key="nc",
                                 min_value=10)
        cr_ctrl = st.number_input("转化率 (0-1)", value=0.032, step=0.001,
                                  format="%.4f", key="cc", min_value=0.0, max_value=1.0)
    with col2:
        st.markdown("#### 🟢 实验组")
        n_trt = st.number_input("样本量", value=5200, step=100, key="nt",
                                min_value=10)
        cr_trt = st.number_input("转化率 (0-1)", value=0.038, step=0.001,
                                 format="%.4f", key="ct", min_value=0.0, max_value=1.0)

    alpha = st.select_slider("显著性水平 α", options=[0.01, 0.05, 0.10], value=0.05)

    _l, _btn, _r = st.columns([1, 2, 1])
    if _btn.button("🚀 运行检验", type="primary", use_container_width=True, key="run_test"):
        result = run_ab_test(n_ctrl, n_trt, cr_ctrl, cr_trt, alpha)

        if result["significant"]:
            st.success(f"### ✅ 差异显著\n{result['conclusion']}")
        else:
            st.warning(f"### ⚠️ 差异不显著\n{result['conclusion']}")

        c1, c2, c3, c4 = st.columns(4)
        with c1.container(border=True):
            st.metric("📈 提升幅度", f"{result['lift_pct']:+.1f}%")
        with c2.container(border=True):
            st.metric("📐 p 值", f"{result['p_value']:.4f}")
        with c3.container(border=True):
            st.metric("📏 Z 统计量", result["z_stat"])
        with c4.container(border=True):
            st.metric("⚡ 统计功效", f"{result['power']:.1%}")

        fig = go.Figure()
        for grp, ci, cr, color in [
            ("对照组", result["ci_control"], cr_ctrl, "#6B7280"),
            ("实验组", result["ci_treatment"], cr_trt, "#3B82F6"),
        ]:
            fig.add_trace(
                go.Scatter(
                    x=[ci[0], cr, ci[1]],
                    y=[grp, grp, grp],
                    mode="lines+markers",
                    marker=dict(size=[10, 14, 10], symbol=["line-ns", "circle", "line-ns"], color=color),
                    line=dict(color=color, width=3),
                    name=grp,
                )
            )
        fig.update_layout(
            title="转化率 95% 置信区间",
            xaxis_tickformat=".1%",
            height=220,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# Tab 2: t 检验（连续型指标）
# ═══════════════════════════════════════════════════════════
with tab_ttest:
    st.markdown("#### 📊 连续指标 t 检验")
    st.caption("适用于均值类指标（ARPU、停留时长、订单金额等）")

    metric_name = st.text_input("指标名称", value="ARPU", key="tt_metric")
    tt_col1, tt_col2 = st.columns(2)
    with tt_col1:
        st.markdown("**🔵 对照组数据**")
        ctrl_input = st.text_area(
            "输入对照组数值（逗号分隔）",
            value="45.2, 38.1, 52.3, 41.7, 39.5, 48.6, 43.2, 47.1, 36.8, 50.4",
            key="tt_ctrl",
            height=80,
        )
    with tt_col2:
        st.markdown("**🟢 实验组数据**")
        trt_input = st.text_area(
            "输入实验组数值（逗号分隔）",
            value="51.3, 44.7, 55.8, 48.2, 46.1, 53.4, 49.8, 52.6, 42.3, 57.1",
            key="tt_trt",
            height=80,
        )

    tt_alpha = st.select_slider("显著性水平 α", options=[0.01, 0.05, 0.10], value=0.05, key="tt_alpha")

    _tl, _tbtn, _tr = st.columns([1, 2, 1])
    if _tbtn.button("🚀 运行 t 检验", type="primary", use_container_width=True, key="run_ttest"):
        try:
            ctrl_vals = [float(x.strip()) for x in ctrl_input.split(",") if x.strip()]
            trt_vals = [float(x.strip()) for x in trt_input.split(",") if x.strip()]

            result = run_ttest(ctrl_vals, trt_vals, alpha=tt_alpha, metric_name=metric_name)

            if result["significant"]:
                st.success(f"### ✅ 差异显著\n{result['conclusion']}")
            else:
                st.warning(f"### ⚠️ 差异不显著\n{result['conclusion']}")

            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1.container(border=True):
                st.metric("提升幅度", f"{result['lift_pct']:+.1f}%")
            with tc2.container(border=True):
                st.metric("p 值", f"{result['p_value']:.4f}")
            with tc3.container(border=True):
                st.metric("t 统计量", result["t_stat"])
            with tc4.container(border=True):
                st.metric("统计功效", f"{result['power']:.1%}")

            st.markdown("<br>", unsafe_allow_html=True)
            tc5, tc6, tc7 = st.columns(3)
            with tc5.container(border=True):
                st.metric("对照组均值", f"{result['control_mean']:.4f}")
            with tc6.container(border=True):
                st.metric("实验组均值", f"{result['treatment_mean']:.4f}")
            with tc7.container(border=True):
                st.metric("差异 95%CI", f"[{result['ci_diff'][0]:.3f}, {result['ci_diff'][1]:.3f}]")

        except ValueError:
            st.error("❌ 输入格式错误，请用逗号分隔数字")


# ═══════════════════════════════════════════════════════════
# Tab 3: 样本量计算器
# ═══════════════════════════════════════════════════════════
with tab_sample:
    st.markdown("#### 📐 计算所需最小样本量")
    st.caption("输入基线转化率和最小可检测效应（MDE），计算每组所需样本量")

    sc1, sc2 = st.columns(2)
    with sc1:
        baseline = st.number_input("基线转化率", value=0.05, step=0.01, format="%.3f",
                                   min_value=0.001, max_value=0.999, key="ss_baseline")
        mde = st.number_input("最小可检测效应 (MDE)", value=0.01, step=0.005, format="%.3f",
                              min_value=0.001, key="ss_mde",
                              help="希望检测到的最小绝对转化率提升")
    with sc2:
        ss_alpha = st.select_slider("显著性水平 α", options=[0.01, 0.05, 0.10],
                                     value=0.05, key="ss_alpha")
        ss_power = st.select_slider("统计功效 1-β", options=[0.7, 0.8, 0.9, 0.95],
                                     value=0.8, key="ss_power")

    _sl, _sbtn, _sr = st.columns([1, 2, 1])
    if _sbtn.button("📊 计算样本量", type="primary", use_container_width=True, key="calc_ss"):
        result = sample_size_calculator(baseline, mde, ss_alpha, ss_power)

        rc1, rc2, rc3 = st.columns(3)
        with rc1.container(border=True):
            st.metric("对照组样本量", f"{result['n_control']:,}")
        with rc2.container(border=True):
            st.metric("实验组样本量", f"{result['n_treatment']:,}")
        with rc3.container(border=True):
            st.metric("总计样本量", f"{result['total']:,}")

        st.info(f"基线 {result['baseline']:.1%} → 目标 {result['target_rate']:.1%}，"
                f"效应量 = {result['effect_size']:.4f}")

        if result.get("curve_data"):
            import plotly.graph_objects as go
            curve_df = pd.DataFrame(result["curve_data"])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=curve_df["mde"] * 100,
                y=curve_df["sample_size"],
                mode="lines+markers",
                line=dict(color="#3B82F6", width=3),
                marker=dict(size=6),
            ))
            fig.add_trace(go.Scatter(
                x=[mde * 100],
                y=[result["n_control"]],
                mode="markers+text",
                marker=dict(size=14, color="#EF4444", symbol="star"),
                text=[f"{result['n_control']:,}"],
                textposition="top center",
                name="当前选择",
            ))
            fig.update_layout(
                title="MDE vs 所需样本量曲线",
                xaxis_title="MDE (百分点)",
                yaxis_title="每组样本量",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# Tab 4: 多指标校正
# ═══════════════════════════════════════════════════════════
with tab_multi:
    st.markdown("#### 🔗 多指标 p 值校正")
    st.caption("同时检验多个指标时，需要使用校正方法避免假阳性")

    method = st.radio("校正方法", ["bonferroni", "holm"],
                      format_func=lambda x: {"bonferroni": "Bonferroni（保守）", "holm": "Holm（逐步，推荐）"}[x],
                      horizontal=True)

    multi_alpha = st.select_slider("总体显著性水平 α", options=[0.01, 0.05, 0.10], value=0.05, key="multi_alpha")

    n_metrics = st.number_input("指标数量", min_value=2, max_value=10, value=3, key="n_metrics")

    metric_inputs = []
    for i in range(n_metrics):
        mc1, mc2 = st.columns([2, 1])
        with mc1:
            name = st.text_input(f"指标{i+1}名称", value=f"指标{i+1}", key=f"mn_{i}")
        with mc2:
            pval = st.number_input(f"p值", value=0.03 if i == 0 else 0.08,
                                   step=0.01, format="%.4f", key=f"mp_{i}",
                                   min_value=0.0, max_value=1.0)
        metric_inputs.append((name, pval))

    _ml, _mbtn, _mr = st.columns([1, 2, 1])
    if _mbtn.button("🔍 执行校正", type="primary", use_container_width=True, key="run_multi"):
        names = [m[0] for m in metric_inputs]
        pvals = [m[1] for m in metric_inputs]

        result = multi_metric_correction(pvals, names, method=method, alpha=multi_alpha)

        st.markdown(f"**{result['method'].upper()} 校正结果** — "
                    f"共 {result['n_metrics']} 个指标，{result['n_significant']} 个显著")

        results_data = []
        for r in result["results"]:
            results_data.append({
                "指标": r["metric"],
                "原始 p 值": f"{r['p_value']:.4f}",
                "校正阈值": f"{r['corrected_alpha']:.4f}",
                "结论": "✅ 显著" if r["significant"] else "❌ 不显著",
            })
        st.dataframe(pd.DataFrame(results_data), use_container_width=True, hide_index=True)

        if result["n_significant"] < len(pvals):
            st.warning(
                f"⚠️ 经 {method} 校正后，部分原本'显著'的指标变为不显著。"
                f"这是多重检验校正的正常结果，避免了假阳性。"
            )
