import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="DataMind", page_icon="📊", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()


# ── 侧边栏品牌 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 DataMind")
    st.caption("Multi-Agent Analytics · v3.0")
    st.divider()

    with st.container(border=True):
        st.markdown("**🤖 Agent 矩阵**")
        st.caption("🧹 清洗 · 🔍 EDA · 📊 分析 · 🧪 实验 · 🤖 Router")

# ── 主标题 ─────────────────────────────────────────────────
st.markdown("## 📊 DataMind · Multi-Agent 数据分析平台")
st.caption("上传数据 → 五大 AI Agent 自动协作 — 数据清洗 → 探索分析 → 深度洞察 → 智能报告")

st.markdown("")  # spacer

# ── 文件上传 ───────────────────────────────────────────────
uploaded = st.file_uploader(
    "📁 上传数据文件（支持 CSV / Excel）",
    type=["csv", "xlsx", "xls"],
    help="支持最大 200MB 的 CSV、XLSX、XLS 文件",
)

if uploaded:
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
        st.session_state["df"] = df
        # 清除旧的分析结果
        for key in ["df_clean", "clean_report", "rfm_result", "cohort_result",
                     "ltv_result", "churn_result", "eda_result", "eda_anomalies",
                     "eda_corr", "pipeline_report", "auto_report", "dataset_profile",
                     "domain_type", "analysis_summary"]:
            st.session_state.pop(key, None)
        st.success(f"✅ 已加载 **{uploaded.name}** — {len(df):,} 行 × {len(df.columns)} 列")
    except Exception as e:
        st.error(f"❌ 读取失败：{e}")

# ── 数据概览仪表盘 ─────────────────────────────────────────
if "df" in st.session_state:
    df = st.session_state["df"]

    # ── 一键全自动分析 ────────────────────────────────────
    st.markdown("")
    st.markdown("#### 🚀 一键全自动分析")
    st.caption("5 个 AI Agent 接力协作：数据嗅探 → 智能清洗 → EDA 探索 → 领域建模 → 报告生成")

    # [原则 1] 按钮居中，限制宽度
    _left, btn_center, _right = st.columns([1, 2, 1])
    with btn_center:
        run_pipeline = st.button("✨ 唤醒 Auto-Pipeline", type="primary", use_container_width=True, key="run_pipeline")

    if run_pipeline:
        from agents.pipeline import create_pipeline
        from utils.data_store import sync_from_session, sync_to_session

        pipeline = create_pipeline()
        sync_from_session()

        # 显示 Pipeline 进度
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0, text="🔍 初始化 Pipeline...")

            stages = [
                (0.1, "🔍 数据集嗅探 — 识别业务场景..."),
                (0.3, "🧹 数据清洗 — 处理缺失值与异常..."),
                (0.5, "🔍 数据探索 — 生成洞察..."),
                (0.7, "📊 深度分析 — 领域专项分析..."),
                (0.9, "📝 报告生成 — 汇总结果..."),
            ]

        try:
            # 运行 Pipeline
            result = pipeline.invoke({
                "messages": [],
                "has_data": True,
                "has_clean_data": False,
                "clean_report": None,
                "eda_insights": None,
                "analysis_results": None,
                "ab_results": None,
                "pipeline_stage": None,
                "dataset_profile": None,
                "domain_type": None,
                "pipeline_report": None,
                "next_agent": None,
                "pending_confirmation": None,
            })

            # 同步结果回 session
            sync_to_session()
            progress_bar.progress(1.0, text="✅ 分析完成！")

            # 显示pipeline进度完成信息
            st.success("🎉 **全自动分析完成！** 请前往「报告导出」页面查看完整报告。")

            # 显示分析摘要
            if result.get("domain_type"):
                domain_labels = {
                    "ecommerce": "📦 电商交易", "marketing": "📢 营销投放",
                    "user_growth": "📈 用户增长", "general": "📋 通用数据",
                }
                st.info(f"识别的数据类型：**{domain_labels.get(result['domain_type'], '通用')}**")

            if result.get("clean_report"):
                st.info(f"数据质量评分：**{result['clean_report'].get('quality_score', 'N/A')}/100**")

            if result.get("eda_insights"):
                with st.expander("🔍 EDA 关键发现", expanded=False):
                    for insight in result["eda_insights"][:5]:
                        st.markdown(f"- {insight}")

        except Exception as e:
            progress_bar.progress(1.0, text="❌ 分析出错")
            st.error(f"Pipeline 执行出错：{str(e)}")

    st.divider()

    # ── 数据概览 ──────────────────────────────────────────
    st.markdown("#### 📈 数据概览")

    # [原则 1+2] 指标卡片 — 等高卡片行
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1.container(border=True):
        st.metric("📊 总行数", f"{len(df):,}")
    with col2.container(border=True):
        st.metric("📋 总列数", f"{len(df.columns)}")
    with col3.container(border=True):
        st.metric("⚠️ 缺失值", f"{df.isna().sum().sum():,}")
    with col4.container(border=True):
        st.metric("🔁 重复行", f"{df.duplicated().sum():,}")

    # 数据质量评分（快速估算）
    missing_pct = df.isna().sum().sum() / (len(df) * len(df.columns)) * 100
    dup_pct = df.duplicated().sum() / len(df) * 100
    quick_score = max(0, round(100 - missing_pct * 3 - dup_pct * 2))
    with col5.container(border=True):
        st.metric("✅ 质量评分", f"{quick_score}/100")

    st.markdown("")

    # 可视化面板
    tab1, tab2, tab3 = st.tabs(["📋 数据预览", "📊 列分布", "🔍 列详情"])

    with tab1:
        st.dataframe(df.head(50), use_container_width=True, height=400)

    with tab2:
        vis_col1, vis_col2 = st.columns(2)

        with vis_col1:
            type_counts = df.dtypes.astype(str).value_counts()
            fig_types = go.Figure(
                go.Pie(
                    labels=type_counts.index,
                    values=type_counts.values,
                    hole=0.45,
                    marker=dict(colors=["#2E68ED", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]),
                    textinfo="label+value",
                )
            )
            fig_types.update_layout(
                title="列数据类型分布", height=300,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=40, b=20),
                font=dict(family="Inter, sans-serif"),
            )
            st.plotly_chart(fig_types, use_container_width=True, config={"displayModeBar": False})

        with vis_col2:
            missing = df.isna().sum()
            missing = missing[missing > 0].sort_values(ascending=True)
            if len(missing) > 0:
                fig_missing = go.Figure(
                    go.Bar(
                        x=missing.values,
                        y=missing.index,
                        orientation="h",
                        marker_color="#EF4444",
                        opacity=0.8,
                    )
                )
                fig_missing.update_layout(
                    title="各列缺失值数量", height=300,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=40, b=20),
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_missing, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("🎉 数据无缺失值！")

        # 数值列直方图
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            selected_col = st.selectbox("选择数值列查看分布", num_cols)
            fig_hist = px.histogram(
                df, x=selected_col, nbins=40,
                color_discrete_sequence=["#2E68ED"],
            )
            fig_hist.update_layout(
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                font=dict(family="Inter, sans-serif"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F3F4F6", zeroline=False),
            )
            st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

    with tab3:
        info_df = pd.DataFrame({
            "类型": df.dtypes.astype(str),
            "非空数": df.count(),
            "缺失率": (df.isna().mean() * 100).round(1).astype(str) + "%",
            "唯一值": df.nunique(),
            "示例值": df.iloc[0].astype(str),
        })
        st.dataframe(info_df, use_container_width=True, height=400)

else:
    # [原则 4] 空状态 — 虚线引导收纳区，紧邻上传区
    st.markdown("""
        <div class="empty-state-box">
            <div style="font-size: 3.5rem; margin-bottom: 0.25rem;">📦</div>
            <h3>上传数据，开启 AI 分析之旅</h3>
            <p>拖拽上方区域上传 CSV / Excel 文件<br>系统会自动调度 5 大 AI Agent 进行智能分析</p>
            <div class="agent-chips">
                <span class="agent-chip">🧹 数据清洗</span>
                <span class="agent-chip">🔍 EDA 探索</span>
                <span class="agent-chip">📊 深度分析</span>
                <span class="agent-chip">🧪 A/B 测试</span>
                <span class="agent-chip">🤖 AI Router</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="download-link-center">'
        '<a href="https://raw.githubusercontent.com/guipsamora/pandas_exercises/master/07_Visualization/Online_Retail/Online_Retail.csv">'
        '没有数据？下载示例电商数据集 →'
        '</a></div>',
        unsafe_allow_html=True,
    )