import streamlit as st
import pandas as pd
from tools.user_analysis import rfm_analysis, cohort_analysis, retention_analysis, churn_prediction, ltv_prediction

st.set_page_config(page_title="用户分析 - DataMind", page_icon="👥", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()


st.markdown("## 👥 用户分析")
st.caption("RFM 分层 · Cohort 留存 · 流失预警 · LTV 预测")

if "df" not in st.session_state:
    st.warning("⚠️ 请先在主页上传数据文件")
    st.stop()

df = st.session_state.get("df_clean", st.session_state["df"])

# ── 列选择器 ───────────────────────────────────────────────
st.markdown("### ⚙️ 列映射")
st.caption("请选择数据中对应的列名")
col1, col2, col3 = st.columns(3)
with col1:
    user_col = st.selectbox("用户ID列", df.columns, index=0)
with col2:
    date_candidates = [c for c in df.columns if any(kw in c.lower() for kw in ["date", "time", "日期", "时间"])]
    date_col = st.selectbox("日期列", df.columns, index=df.columns.tolist().index(date_candidates[0]) if date_candidates else 1)
with col3:
    num_candidates = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    amount_col = st.selectbox("金额列", num_candidates if num_candidates else df.columns, index=0)

st.markdown("---")

# ── 分析模块 Tabs ──────────────────────────────────────────
tab_rfm, tab_cohort, tab_retention, tab_churn, tab_ltv = st.tabs(
    ["📊 RFM 分层", "🔥 Cohort 留存", "📈 留存趋势", "⚠️ 流失预警", "💰 LTV 预测"]
)

# ── RFM 分层 ───────────────────────────────────────────────
with tab_rfm:
    _rl, _rbtn, _rr = st.columns([1, 2, 1])
    if _rbtn.button("运行 RFM 分析", type="primary", use_container_width=True, key="btn_rfm"):
        with st.spinner("正在分析..."):
            try:
                rfm_df, fig = rfm_analysis(df, user_col, date_col, amount_col)
                st.session_state["rfm_result"] = {"df": rfm_df, "fig": fig}
            except Exception as e:
                st.error(f"分析出错：{e}")

    if "rfm_result" in st.session_state:
        result = st.session_state["rfm_result"]

        seg_counts = result["df"]["Segment"].value_counts()
        cols = st.columns(len(seg_counts))
        colors = {"高价值用户": "🟢", "潜力用户": "🔵", "流失风险": "🔴", "沉睡用户": "⚪"}
        for i, (seg, cnt) in enumerate(seg_counts.items()):
            with cols[i].container(border=True):
                st.metric(f"{colors.get(seg, '⚪')} {seg}", f"{cnt} 人",
                               delta=f"{cnt / len(result['df']) * 100:.1f}%")

        st.plotly_chart(result["fig"], use_container_width=True)

        with st.expander("📋 查看 RFM 详情表"):
            st.dataframe(result["df"], use_container_width=True, height=300)

# ── Cohort 留存 ────────────────────────────────────────────
with tab_cohort:
    _cl, _cbtn, _cr = st.columns([1, 2, 1])
    if _cbtn.button("运行 Cohort 分析", type="primary", use_container_width=True, key="btn_cohort"):
        with st.spinner("正在分析..."):
            try:
                retention_df, fig = cohort_analysis(df, user_col, date_col)
                st.session_state["cohort_result"] = {"df": retention_df, "fig": fig}
            except Exception as e:
                st.error(f"分析出错：{e}")

    if "cohort_result" in st.session_state:
        result = st.session_state["cohort_result"]
        st.plotly_chart(result["fig"], use_container_width=True)

        avg_ret = result["df"].iloc[:, 1].mean() if result["df"].shape[1] > 1 else 0
        st.info(f"📊 次月平均留存率：**{avg_ret:.1f}%**")

# ── 留存趋势 ───────────────────────────────────────────────
with tab_retention:
    period = st.radio("留存粒度", ["M", "W", "D"],
                      format_func=lambda x: {"M": "月留存", "W": "周留存", "D": "日留存"}[x],
                      horizontal=True)
    _rtl, _rtbtn, _rtr = st.columns([1, 2, 1])
    if _rtbtn.button("运行留存趋势分析", type="primary", use_container_width=True, key="btn_retention"):
        with st.spinner("正在分析..."):
            try:
                ret_df, fig = retention_analysis(df, user_col, date_col, period=period)
                st.session_state["retention_result"] = {"df": ret_df, "fig": fig}
            except Exception as e:
                st.error(f"分析出错：{e}")

    if "retention_result" in st.session_state:
        result = st.session_state["retention_result"]
        st.plotly_chart(result["fig"], use_container_width=True)

        with st.expander("📋 留存数据表"):
            st.dataframe(result["df"], use_container_width=True, hide_index=True)

# ── 流失预警 ───────────────────────────────────────────────
with tab_churn:
    churn_days = st.slider("流失判定天数", min_value=7, max_value=90, value=30,
                           help="用户超过该天数未活跃，则被判定为已流失")
    _chl, _chbtn, _chr = st.columns([1, 2, 1])
    if _chbtn.button("运行流失预警", type="primary", use_container_width=True, key="btn_churn"):
        with st.spinner("正在分析..."):
            try:
                churn_df, fig = churn_prediction(df, user_col, date_col, churn_days=churn_days)
                st.session_state["churn_result"] = {"df": churn_df, "fig": fig}
            except Exception as e:
                st.error(f"分析出错：{e}")

    if "churn_result" in st.session_state:
        result = st.session_state["churn_result"]
        st.plotly_chart(result["fig"], use_container_width=True)

        status_summary = result["df"]["status"].value_counts()
        cols = st.columns(len(status_summary))
        status_icons = {"活跃用户": "🟢", "沉默用户": "🟡", "流失风险": "🔴", "已流失": "⚫"}
        for i, (status, cnt) in enumerate(status_summary.items()):
            with cols[i].container(border=True):
                st.metric(f"{status_icons.get(status, '⚪')} {status}", f"{cnt} 人")

        with st.expander("📋 用户状态详情"):
            st.dataframe(result["df"].sort_values("days_inactive", ascending=False),
                         use_container_width=True, height=300)

# ── LTV 预测 ──────────────────────────────────────────────
with tab_ltv:
    _ll, _lbtn, _lr = st.columns([1, 2, 1])
    if _lbtn.button("运行 LTV 预测", type="primary", use_container_width=True, key="btn_ltv"):
        with st.spinner("正在预测..."):
            try:
                ltv_df, fig = ltv_prediction(df, user_col, date_col, amount_col)
                st.session_state["ltv_result"] = {"df": ltv_df, "fig": fig}
            except Exception as e:
                st.error(f"预测出错：{e}")

    if "ltv_result" in st.session_state:
        result = st.session_state["ltv_result"]

        lc1, lc2, lc3 = st.columns(3)
        with lc1.container(border=True):
            st.metric("平均 LTV", f"¥{result['df']['LTV'].mean():,.0f}")
        with lc2.container(border=True):
            st.metric("中位 LTV", f"¥{result['df']['LTV'].median():,.0f}")
        with lc3.container(border=True):
            st.metric("最高 LTV", f"¥{result['df']['LTV'].max():,.0f}")

        st.plotly_chart(result["fig"], use_container_width=True)

        with st.expander("📋 用户 LTV 详情"):
            st.dataframe(
                result["df"].sort_values("LTV", ascending=False),
                use_container_width=True, height=300,
            )
