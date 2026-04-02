"""
🔍 数据探索 (EDA) 页面
相关性热图 · 分布分析 · 异常洞察
"""
import streamlit as st
import pandas as pd
from tools.eda import (
    run_eda_summary,
    correlation_analysis,
    distribution_analysis,
    detect_anomalies_insight,
)

st.set_page_config(page_title="数据探索 - DataMind", page_icon="🔍", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()

st.markdown("## 🔍 数据探索")
st.caption("相关性分析 · 分布检验 · 异常洞察 · 自动 Insight 生成")

if "df" not in st.session_state:
    st.warning("⚠️ 请先在主页上传数据文件")
    st.stop()

df = st.session_state.get("df_clean", st.session_state["df"])

# ── 一键 EDA — [原则 1] 居中按钮 ─────────────────────────
_l, btn_col, _r = st.columns([1, 2, 1])
with btn_col:
    run_eda = st.button("🚀 运行自动探索分析", type="primary", use_container_width=True)

if run_eda:
    with st.spinner("🧠 正在调度 EDA Agent 分析数据..."):
        eda_result = run_eda_summary(df)
        anomalies = detect_anomalies_insight(df)
        corr_df, corr_fig = correlation_analysis(df)
        st.session_state["eda_result"] = eda_result
        st.session_state["eda_anomalies"] = anomalies
        st.session_state["eda_corr"] = {"df": corr_df, "fig": corr_fig}
    st.success("✅ 探索分析完成！")

# ── 展示 EDA 结果 ─────────────────────────────────────────
if "eda_result" in st.session_state:
    eda = st.session_state["eda_result"]

    # 顶部指标卡片
    st.markdown("#### 📊 数据概况")
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1.container(border=True):
        st.metric("📊 总行数", f"{eda['shape']['rows']:,}")
    with mc2.container(border=True):
        st.metric("📋 总列数", f"{eda['shape']['cols']}")
    with mc3.container(border=True):
        st.metric("🔢 数值列", f"{len(eda.get('numeric_stats', {}))}")
    with mc4.container(border=True):
        st.metric("🏷️ 类别列", f"{len(eda.get('categorical_stats', {}))}")
    with mc5.container(border=True):
        st.metric("⚠️ 缺失列", f"{len(eda.get('missing', {}))}")

    st.markdown("")

    # Tabs
    tab_anomaly, tab_corr, tab_dist, tab_cat = st.tabs(
        ["⚠️ 异常洞察", "🔗 相关性", "📊 分布分析", "📋 类别列"]
    )

    # ── 异常洞察 Tab ──────────────────────────────────────
    with tab_anomaly:
        anomalies = st.session_state.get("eda_anomalies", [])
        if not anomalies:
            st.success("✅ 数据质量良好，未检测到显著异常。")
        else:
            st.markdown(f"检测到 **{len(anomalies)}** 条数据洞察：")
            icons = {"anomaly": "🔴", "warning": "⚠️", "highlight": "💡"}
            severity_colors = {"high": "#EF4444", "medium": "#F59E0B", "low": "#6B7280"}

            for ins in sorted(anomalies, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3)):
                icon = icons.get(ins["type"], "📌")
                sev = ins["severity"].upper()
                sev_color = severity_colors.get(ins["severity"], "#6B7280")
                desc = ins["description"]
                html_block = (
                    f"<div style='padding:16px; margin:8px 0; border-radius:8px; "
                    f"border:1px solid #E5E7EB; border-left:4px solid {sev_color}; "
                    f"background:#FFFFFF; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);'>"
                    f"<b style='color:#111827;'>{icon} [{sev}]</b> <span style='color:#374151;'>{desc}</span>"
                    f"</div>"
                )
                st.markdown(html_block, unsafe_allow_html=True)

    # ── 相关性 Tab ────────────────────────────────────────
    with tab_corr:
        corr_data = st.session_state.get("eda_corr", {})
        if corr_data.get("fig"):
            st.plotly_chart(corr_data["fig"], use_container_width=True)

            # 高相关性配对
            pairs = eda.get("high_correlation_pairs", [])
            if pairs:
                st.markdown("**🔗 高相关性配对 (|r| > 0.7)：**")
                pair_data = []
                for p in pairs:
                    direction = "正相关 📈" if p["correlation"] > 0 else "负相关 📉"
                    pair_data.append({
                        "列 A": p["col_a"],
                        "列 B": p["col_b"],
                        "相关系数": p["correlation"],
                        "方向": direction,
                    })
                st.dataframe(pd.DataFrame(pair_data), hide_index=True, use_container_width=True)
        else:
            st.info("数值列不足 2 列，无法计算相关性。")

    # ── 分布分析 Tab ──────────────────────────────────────
    with tab_dist:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            selected_col = st.selectbox("选择数值列分析分布", num_cols)
            if st.button("📊 分析分布", key="dist_btn"):
                with st.spinner("正在分析..."):
                    result, fig = distribution_analysis(df, selected_col)

                st.plotly_chart(fig, use_container_width=True)

                # 统计结果卡片
                st.markdown("<br>", unsafe_allow_html=True)
                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1.container(border=True):
                    st.metric("均值", f"{result['mean']:.4f}")
                with dc2.container(border=True):
                    st.metric("中位数", f"{result['median']:.4f}")
                with dc3.container(border=True):
                    st.metric("偏度", f"{result['skewness']:.2f}")
                with dc4.container(border=True):
                    st.metric("峰度", f"{result['kurtosis']:.2f}")

                normal_str = "✅ 符合正态" if result["is_normal"] else "❌ 非正态"
                st.info(
                    f"正态性检验（{result['normality_test']}）：p = {result['normality_p']:.4f} → {normal_str}"
                )

            # 显示偏态列警告
            skewed = eda.get("skewed_columns", [])
            if skewed:
                st.markdown("**⚠️ 严重偏态列：**")
                for s in skewed:
                    st.markdown(f"  · `{s['column']}`: 偏度 = {s['skewness']}")
        else:
            st.info("数据中没有数值列。")

    # ── 类别列 Tab ────────────────────────────────────────
    with tab_cat:
        cat_stats = eda.get("categorical_stats", {})
        if cat_stats:
            for col, stats in cat_stats.items():
                with st.expander(f"📋 {col} — {stats['n_unique']} 个类别", expanded=False):
                    if stats.get("top5"):
                        top_df = pd.DataFrame([
                            {"值": k, "数量": v, "占比": f"{v/eda['shape']['rows']:.1%}"}
                            for k, v in stats["top5"].items()
                        ])
                        st.dataframe(top_df, hide_index=True, use_container_width=True)
                    st.caption(f"最多类别: {stats['mode']} ({stats['mode_pct']}%)")
        else:
            st.info("数据中没有类别列。")

        # 疑似 ID 列
        id_cols = eda.get("potential_id_columns", [])
        if id_cols:
            st.warning(f"🆔 以下列可能是 ID 列（高基数），已跳过类别分析：{', '.join(id_cols)}")
