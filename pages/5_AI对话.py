"""
🤖 AI 分析师对话页面
接入 Router Agent（LangGraph StateGraph）
支持自然语言交互，自动路由到专业子 Agent
"""
import streamlit as st
from agents.router import create_router_agent
from utils.data_store import sync_from_session, sync_to_session

st.set_page_config(page_title="AI 对话 - DataMind", page_icon="🤖", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()

st.markdown("## 🤖 AI 分析师对话")
st.caption("用自然语言描述你的分析需求，AI 会自动识别意图并路由到专业 Agent")

# ── 初始化 ─────────────────────────────────────────────────
if "router_agent" not in st.session_state:
    with st.spinner("正在初始化 AI 路由系统..."):
        st.session_state["router_agent"] = create_router_agent()

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "你好！我是 DataMind AI 分析师 🤖\n\n"
                "我的背后有 **5 个专业 Agent** 协同工作，会自动识别你的意图并调用最合适的分析能力：\n\n"
                "| Agent | 能力 |\n"
                "|---|---|\n"
                "| 🧹 清洗 Agent | 数据清洗、异常检测、质量校验 |\n"
                "| 🔍 EDA Agent | 探索分析、相关性、分布、洞察 |\n"
                "| 📊 分析 Agent | RFM 分群、Cohort 留存、LTV、漏斗、中介/调节效应 |\n"
                "| 🧪 实验 Agent | A/B 测试、t 检验、样本量计算 |\n"
                "| 🤖 Router | 理解你的意图，自动分发任务 |\n\n"
                "**试试这样说：**\n"
                '- "帮我清洗数据并检查数据质量"\n'
                '- "分析一下数据的分布和相关性"\n'
                '- "做 RFM 用户分层，用户列 user_id，日期 order_date，金额 amount"\n'
                '- "对照组5000人3.2%，实验组5200人3.8%，显著吗？"\n'
                '- "为什么流失率变高了？"\n'
            ),
        }
    ]

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 AI 对话设置")
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state["messages"] = st.session_state["messages"][:1]
        st.rerun()

    st.markdown("---")
    st.markdown("**数据状态**")
    if "df" in st.session_state:
        df = st.session_state["df"]
        st.success(f"✅ 已加载 {len(df):,} 行 × {len(df.columns)} 列")
        if "df_clean" in st.session_state:
            st.info("🧹 数据已清洗")
        st.markdown("**列名：**")
        st.caption(", ".join(df.columns[:15]))
        if len(df.columns) > 15:
            st.caption(f"... 共 {len(df.columns)} 列")
    else:
        st.warning("⚠️ 暂未上传数据")

    st.markdown("---")
    st.markdown("**Agent 路由日志**")
    if "last_route" in st.session_state:
        route_icons = {
            "cleaning": "🧹", "eda": "🔍", "analyst": "📊",
            "ab_test": "🧪", "general": "💬",
        }
        route = st.session_state["last_route"]
        st.info(f"{route_icons.get(route, '📌')} 上次路由 → {route}")

# ── 显示对话历史 ───────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 显示分析图表（如果有） ─────────────────────────────────
chart_keys = [
    ("rfm_result", "RFM 分析图表"),
    ("cohort_result", "Cohort 留存图表"),
    ("ltv_result", "LTV 分析图表"),
    ("funnel_result", "漏斗分析图表"),
    ("eda_corr_fig", "相关性热图"),
]
for key, label in chart_keys:
    if key in st.session_state:
        data = st.session_state[key]
        fig = data.get("fig") if isinstance(data, dict) else data
        if fig is not None:
            with st.expander(f"📊 {label}", expanded=False):
                st.plotly_chart(fig, use_container_width=True)

# ── 输入框 ─────────────────────────────────────────────────
if prompt := st.chat_input("描述你的分析需求..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🔍 AI 分析中..."):
            try:
                # 同步数据到共享存储
                sync_from_session()

                # 调用 Router Agent
                result = st.session_state["router_agent"].invoke({
                    "messages": [{"role": "user", "content": prompt}],
                    "has_data": "df" in st.session_state,
                    "has_clean_data": "df_clean" in st.session_state,
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

                # 同步回 session
                sync_to_session()

                # 记录路由结果
                if result.get("next_agent"):
                    st.session_state["last_route"] = result["next_agent"]

                # 提取最后一条 assistant 消息
                response = ""
                for msg in reversed(result.get("messages", [])):
                    content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                    role = msg.type if hasattr(msg, "type") else msg.get("role", "")
                    if role in ("assistant", "ai"):
                        if isinstance(content, list):
                            response = "\n".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in content
                            ).strip()
                        elif isinstance(content, str):
                            response = content
                        else:
                            response = str(content)
                        break

                if not response:
                    response = "分析完成，但未生成文字回复。请检查工具输出。"

            except Exception as e:
                response = f"❌ 出错了：{str(e)}"

        st.markdown(response)

    st.session_state["messages"].append({"role": "assistant", "content": response})
    st.rerun()
