"""
DataMind 共享数据存储 (增强版)
解决 LangGraph Agent 工具在后台线程中无法访问 Streamlit session_state 的问题。
在调用 Agent 前，将数据从 session_state 同步到此模块；工具从此模块读取数据。

增强点：
- 线程安全的读写（使用 threading.Lock）
- 数据摘要功能（避免将完整 DataFrame 传给 LLM）
- Pipeline 结果存储
"""
import pandas as pd
import numpy as np
import threading
from typing import Any

# 模块级数据存储 + 线程锁
_store: dict[str, Any] = {}
_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════
# 基础读写（线程安全）
# ═══════════════════════════════════════════════════════════

def sync_from_session():
    """从 Streamlit session_state 同步数据到共享存储（在主线程中调用）"""
    import streamlit as st
    with _lock:
        for key in ["df", "df_clean", "clean_report", "rfm_result",
                     "cohort_result", "ltv_result", "churn_result",
                     "auto_report", "eda_insights", "pipeline_report",
                     "retention_result", "dataset_profile", "domain_type"]:
            if key in st.session_state:
                _store[key] = st.session_state[key]


def sync_to_session():
    """将共享存储的数据同步回 Streamlit session_state（在主线程中调用）"""
    import streamlit as st
    with _lock:
        for key, value in _store.items():
            st.session_state[key] = value


def get(key: str, default=None):
    """从共享存储获取数据（在工具线程中安全调用）"""
    with _lock:
        return _store.get(key, default)


def put(key: str, value: Any):
    """写入共享存储（工具线程中调用）"""
    with _lock:
        _store[key] = value


def get_df() -> pd.DataFrame | None:
    """获取当前 DataFrame（优先清洗后的）"""
    with _lock:
        return _store.get("df_clean", _store.get("df"))


def has_data() -> bool:
    """检查是否已加载数据"""
    with _lock:
        return "df" in _store and _store["df"] is not None


def has_clean_data() -> bool:
    """检查是否已有清洗后的数据"""
    with _lock:
        return "df_clean" in _store and _store["df_clean"] is not None


# ═══════════════════════════════════════════════════════════
# 数据摘要（安全传递给 LLM，避免 Token 超载）
# ═══════════════════════════════════════════════════════════

def get_data_summary(max_rows: int = 3) -> str:
    """生成数据摘要字符串，适合传给 LLM 上下文"""
    df = get_df()
    if df is None:
        return "未找到数据，请先上传文件。"

    lines = [
        f"数据集：{len(df)} 行 × {len(df.columns)} 列",
        f"列名：{list(df.columns)}",
        f"数据类型：",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_pct = df[col].isna().mean()
        nunique = df[col].nunique()
        lines.append(f"  · {col} ({dtype}) — {nunique} 个唯一值, 缺失 {null_pct:.1%}")

    # 数值列快速统计
    num_cols = df.select_dtypes(include="number").columns
    if len(num_cols) > 0:
        lines.append(f"\n数值列统计摘要：")
        desc = df[num_cols].describe().round(2)
        lines.append(desc.to_string())

    # 前 N 行预览
    lines.append(f"\n前 {max_rows} 行预览：")
    lines.append(df.head(max_rows).to_string())

    return "\n".join(lines)


def get_column_info() -> dict:
    """获取列信息字典，用于 Agent 参考"""
    df = get_df()
    if df is None:
        return {}

    info = {}
    for col in df.columns:
        col_info = {
            "dtype": str(df[col].dtype),
            "nunique": int(df[col].nunique()),
            "null_pct": round(float(df[col].isna().mean()), 3),
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["min"] = float(df[col].min()) if not df[col].isna().all() else None
            col_info["max"] = float(df[col].max()) if not df[col].isna().all() else None
            col_info["mean"] = round(float(df[col].mean()), 2) if not df[col].isna().all() else None
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info["min"] = str(df[col].min())
            col_info["max"] = str(df[col].max())
        else:
            top3 = df[col].value_counts().head(3)
            col_info["top3"] = {str(k): int(v) for k, v in top3.items()}
        info[col] = col_info

    return info
