"""
📤 报告导出页面
支持：Auto Pipeline 报告、Excel 报告、Markdown 报告、对话记录
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="报告导出 - DataMind", page_icon="📤", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()

st.markdown("## 📤 报告导出")
st.caption("一键导出 · Auto Pipeline 报告 · Excel 分析报告 · 对话记录")


# ═══════════════════════════════════════════════════════════
# Auto Pipeline 智能报告
# ═══════════════════════════════════════════════════════════
st.markdown("#### 🤖 AI 智能分析报告")

if "pipeline_report" in st.session_state:
    st.success("📝 已生成 Auto Pipeline 智能分析报告！")

    with st.expander("📋 查看报告内容", expanded=True):
        st.markdown(st.session_state["pipeline_report"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # 下载 Markdown
    st.download_button(
        label="⬇️ 下载 Markdown 报告",
        data=st.session_state["pipeline_report"],
        file_name=f"DataMind_智能报告_{timestamp}.md",
        mime="text/markdown",
        use_container_width=True,
        key="dl_pipeline_md",
    )

    # 显示分析元信息
    if "dataset_profile" in st.session_state:
        profile = st.session_state["dataset_profile"]
        st.info(f"📊 数据类型：{profile.get('label', '通用数据')} | "
                f"列数：{len(profile.get('columns', []))} | "
                f"领域：{profile.get('domain', 'general')}")
elif "auto_report" in st.session_state:
    st.markdown("**AI 生成的分析报告预览：**")
    with st.expander("查看报告内容", expanded=True):
        st.markdown(st.session_state["auto_report"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        label="⬇️ 下载 Markdown 报告",
        data=st.session_state["auto_report"],
        file_name=f"DataMind_AI报告_{timestamp}.md",
        mime="text/markdown",
        use_container_width=True,
        key="dl_auto_md",
    )
else:
    st.info("💡 请先在主页运行 **一键全自动分析**，或在 AI 对话中让 AI 生成报告。")


# ═══════════════════════════════════════════════════════════
# Excel 报告导出
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("#### 📊 Excel 分析报告")
st.caption("将所有分析结果汇总为一份多 Sheet 的 Excel 文件")

available_sheets = []
if "df" in st.session_state:
    available_sheets.append("原始数据")
if "df_clean" in st.session_state:
    available_sheets.append("清洗后数据")
if "rfm_result" in st.session_state:
    available_sheets.append("RFM 分析")
if "cohort_result" in st.session_state:
    available_sheets.append("Cohort 留存")
if "ltv_result" in st.session_state:
    available_sheets.append("LTV 预测")
if "churn_result" in st.session_state:
    available_sheets.append("流失预警")

if not available_sheets:
    st.info("📋 暂无可导出的数据。请先在其他页面完成分析后再来导出。")
else:
    st.success(f"✅ 已检测到 {len(available_sheets)} 个可导出的数据表：{', '.join(available_sheets)}")

    selected = st.multiselect("选择要导出的内容", available_sheets, default=available_sheets)

    _el, _ebtn, _er = st.columns([1, 2, 1])
    if _ebtn.button("📥 生成 Excel 报告", type="primary", use_container_width=True):
        with st.spinner("正在生成报告..."):
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                if "原始数据" in selected and "df" in st.session_state:
                    st.session_state["df"].to_excel(writer, sheet_name="原始数据", index=False)

                if "清洗后数据" in selected and "df_clean" in st.session_state:
                    st.session_state["df_clean"].to_excel(writer, sheet_name="清洗后数据", index=False)
                    if "clean_report" in st.session_state:
                        report = st.session_state["clean_report"]
                        summary_data = {
                            "项目": ["原始行数", "清洗后行数", "去除重复", "质量评分"],
                            "值": [
                                report["original_rows"],
                                report["final_rows"],
                                report["duplicates_removed"],
                                f"{report['quality_score']}/100",
                            ],
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name="清洗摘要", index=False)

                if "RFM 分析" in selected and "rfm_result" in st.session_state:
                    st.session_state["rfm_result"]["df"].to_excel(writer, sheet_name="RFM分析", index=False)

                if "Cohort 留存" in selected and "cohort_result" in st.session_state:
                    st.session_state["cohort_result"]["df"].to_excel(writer, sheet_name="Cohort留存")

                if "LTV 预测" in selected and "ltv_result" in st.session_state:
                    st.session_state["ltv_result"]["df"].to_excel(writer, sheet_name="LTV预测", index=False)

                if "流失预警" in selected and "churn_result" in st.session_state:
                    st.session_state["churn_result"]["df"].to_excel(writer, sheet_name="流失预警", index=False)

            buffer.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"DataMind_分析报告_{timestamp}.xlsx"

            st.download_button(
                label=f"⬇️ 下载 {filename}",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.success("✅ 报告已生成！点击上方按钮下载。")


# ═══════════════════════════════════════════════════════════
# 对话记录导出
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("#### 💬 对话记录导出")

if "messages" in st.session_state and len(st.session_state["messages"]) > 1:
    chat_log = []
    for msg in st.session_state["messages"]:
        role = "🤖 AI" if msg["role"] == "assistant" else "👤 用户"
        chat_log.append(f"### {role}\n\n{msg['content']}\n")

    chat_text = "\n---\n\n".join(chat_log)
    chat_text = f"# DataMind AI 对话记录\n\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{chat_text}"

    st.download_button(
        label="⬇️ 下载对话记录",
        data=chat_text,
        file_name=f"DataMind_对话记录_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.caption(f"共 {len(st.session_state['messages'])} 条消息")
else:
    st.info("💡 暂无对话记录。请先在 AI 对话页面进行分析对话。")
