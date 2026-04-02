import streamlit as st
import pandas as pd
from tools.cleaning import clean_dataframe
from tools.quality import auto_quality_checks, quality_report_summary

st.set_page_config(page_title="数据清洗 - DataMind", page_icon="🧹", layout="wide")

from utils.ui_enhancer import apply_saas_style
apply_saas_style()

st.markdown("## 🧹 数据清洗")
st.caption("一键清洗 · 异常检测 · 质量校验")

if "df" not in st.session_state:
    st.warning("⚠️ 请先在主页上传数据文件")
    st.stop()

df_raw = st.session_state["df"]

# ── 清洗配置 ───────────────────────────────────────────────
with st.expander("⚙️ 清洗参数配置", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        outlier_method = st.selectbox(
            "异常检测方法",
            ["iqr", "zscore", "none"],
            format_func=lambda x: {"iqr": "IQR 四分位距法", "zscore": "Z-Score 标准分法", "none": "不检测"}[x],
        )
    with col2:
        st.info(
            {
                "iqr": "标记超出 Q1-1.5×IQR ~ Q3+1.5×IQR 范围的值",
                "zscore": "标记 Z 分数 > 3 的值",
                "none": "跳过异常检测步骤",
            }[outlier_method]
        )

# ── 执行清洗 — [原则 1] 居中按钮 ───────────────────────────
_l, btn_col, _r = st.columns([1, 2, 1])
with btn_col:
    start_cleaning = st.button("🚀 开始清洗并生成质量报告", type="primary", use_container_width=True)

if start_cleaning:
    with st.spinner("🧠 正在调用 AI 分析与清洗数据..."):
        df_clean, report = clean_dataframe(df_raw, outlier_method=outlier_method)
        st.session_state["df_clean"] = df_clean
        st.session_state["clean_report"] = report

    st.success(f"✅ 清洗完成！数据质量综合评分：**{report['quality_score']}/100**")

# ── 展示清洗结果 ───────────────────────────────────────────
if "clean_report" in st.session_state:
    report = st.session_state["clean_report"]
    df_clean = st.session_state["df_clean"]

    # [原则 1+2+3] 指标卡 — 等高、带 Icon
    st.markdown("#### 📊 清洗前后对比")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1.container(border=True):
        st.metric("📄 原始行数", f"{report['original_rows']:,}")
    with c2.container(border=True):
        st.metric("✅ 清洗后", f"{report['final_rows']:,}",
                  delta=f"-{report['original_rows'] - report['final_rows']}")
    with c3.container(border=True):
        st.metric("🔁 去除重复", f"{report['duplicates_removed']:,}")
    with c4.container(border=True):
        st.metric("🔄 类型转换", f"{len(report.get('type_conversions', {}))} 列")
    with c5.container(border=True):
        st.metric("⭐ 质量评分", f"{report['quality_score']}/100")

    # [原则 4] 清洗步骤收纳到 expander
    with st.expander("🛠️ 查看详细清洗日志", expanded=False):
        for i, step in enumerate(report.get("steps", []), 1):
            st.markdown(f"**{i}.** {step}")

    # 异常值详情
    if report.get("outliers"):
        st.markdown("#### ⚠️ 异常值检测结果")
        outlier_data = []
        for col, info in report["outliers"].items():
            outlier_data.append({
                "列名": col,
                "异常数": info["count"],
                "占比": info["pct"],
                "合理范围": info.get("range", info.get("threshold", "-")),
            })
        st.dataframe(pd.DataFrame(outlier_data), use_container_width=True, hide_index=True)
        st.caption("💡 异常值已标记但未删除，你可以根据业务需求决定是否处理。")

    # 类型转换详情
    if report.get("type_conversions"):
        with st.expander("🔄 自动类型转换详情"):
            conv_data = [{"列名": col, "转换": conv} for col, conv in report["type_conversions"].items()]
            st.dataframe(pd.DataFrame(conv_data), use_container_width=True, hide_index=True)

    # 数据质量校验
    st.markdown("#### ✅ 数据质量校验")
    with st.spinner("运行质量检测规则..."):
        checks = auto_quality_checks(df_clean)
        summary = quality_report_summary(checks)

    qc1, qc2, qc3 = st.columns(3)
    with qc1.container(border=True):
        st.metric("📏 检测规则", summary["total_checks"])
    with qc2.container(border=True):
        st.metric("✅ 通过", summary["passed"])
    with qc3.container(border=True):
        st.metric("❌ 未通过", summary["failed"],
                   delta=f"-{summary['failed']}" if summary["failed"] > 0 else None)

    # 检测结果表格
    results_df = pd.DataFrame(summary["results"])
    results_df["状态"] = results_df["passed"].map({True: "✅ 通过", False: "❌ 未通过"})

    failed = results_df[~results_df["passed"]]
    if len(failed) > 0:
        st.markdown("**未通过的检测项：**")
        st.dataframe(
            failed[["name", "column", "details", "状态"]].rename(
                columns={"name": "规则", "column": "列", "details": "详情", "状态": "结果"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("📋 查看全部检测结果"):
        st.dataframe(
            results_df[["name", "column", "details", "状态"]].rename(
                columns={"name": "规则", "column": "列", "details": "详情", "状态": "结果"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    # 数据预览
    st.markdown("#### 📋 清洗后数据预览")
    st.dataframe(df_clean.head(30), use_container_width=True)
