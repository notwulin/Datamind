"""
数据清洗层 — pandas 增强版
功能：去重、缺失值处理、类型转换、异常检测、数据质量校验
"""
import pandas as pd
import numpy as np
from io import StringIO


def clean_dataframe(df: pd.DataFrame, outlier_method: str = "iqr") -> tuple[pd.DataFrame, dict]:
    """
    清洗 DataFrame，返回 (清洗后的df, 质量报告)
    
    参数:
        df: 原始 DataFrame
        outlier_method: 异常检测方法 'iqr' | 'zscore' | 'none'
    """
    report = {
        "original_rows": len(df),
        "original_cols": len(df.columns),
        "steps": [],
    }

    # ── 1. 去重 ────────────────────────────────────────────
    dup_count = df.duplicated().sum()
    df = df.drop_duplicates()
    report["duplicates_removed"] = int(dup_count)
    report["steps"].append(f"去除重复行 {dup_count} 行")

    # ── 2. 删除全空列 / 全空行 ─────────────────────────────
    empty_cols = df.columns[df.isna().all()].tolist()
    df = df.dropna(axis=1, how="all")
    empty_rows = df.index[df.isna().all(axis=1)].tolist()
    df = df.dropna(axis=0, how="all")
    report["empty_cols_removed"] = empty_cols
    report["empty_rows_removed"] = len(empty_rows)
    report["steps"].append(f"去除全空列 {len(empty_cols)} 列，全空行 {len(empty_rows)} 行")

    # ── 3. 智能类型推断 ────────────────────────────────────
    type_conversions = {}
    for col in df.columns:
        original_dtype = str(df[col].dtype)

        # 尝试转数值
        if df[col].dtype == object:
            numeric_converted = pd.to_numeric(df[col], errors="coerce")
            if numeric_converted.notna().sum() > len(df) * 0.5:
                non_null_match = numeric_converted.notna().sum() / df[col].notna().sum()
                if non_null_match > 0.8:
                    df[col] = numeric_converted
                    type_conversions[col] = f"{original_dtype} → {df[col].dtype}"
                    continue

        # 尝试转日期
        if df[col].dtype == object:
            sample = df[col].dropna().head(20)
            date_pattern = sample.astype(str).str.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
            if date_pattern.any() and date_pattern.mean() > 0.5:
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    type_conversions[col] = f"{original_dtype} → datetime64"
                except Exception:
                    pass

    report["type_conversions"] = type_conversions
    report["steps"].append(f"类型推断转换 {len(type_conversions)} 列")

    # ── 4. 缺失值处理 ─────────────────────────────────────
    missing_summary = {}
    cols_dropped_missing = []
    for col in df.columns:
        missing_pct = df[col].isna().mean()
        if missing_pct > 0:
            missing_summary[col] = f"{missing_pct:.1%}"

        if missing_pct > 0.5:  # >50% 缺失则删列
            df = df.drop(columns=[col])
            cols_dropped_missing.append(col)
        elif missing_pct > 0:
            if pd.api.types.is_numeric_dtype(df[col]):
                fill_val = df[col].median()
                df[col] = df[col].fillna(fill_val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                pass  # 日期列保留 NaT
            else:
                mode_vals = df[col].mode()
                fill_val = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
                df[col] = df[col].fillna(fill_val)

    report["missing_summary"] = missing_summary
    report["cols_dropped_high_missing"] = cols_dropped_missing
    report["steps"].append(
        f"处理缺失值：{len(missing_summary)} 列有缺失，{len(cols_dropped_missing)} 列因>50%缺失被删除"
    )

    # ── 5. 异常值检测 ──────────────────────────────────────
    outlier_info = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if outlier_method == "iqr" and numeric_cols:
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (df[col] < lower) | (df[col] > upper)
            n_outliers = int(outlier_mask.sum())
            if n_outliers > 0:
                outlier_info[col] = {
                    "count": n_outliers,
                    "pct": f"{n_outliers / len(df):.1%}",
                    "range": f"[{lower:.2f}, {upper:.2f}]",
                }
    elif outlier_method == "zscore" and numeric_cols:
        from scipy import stats as sp_stats

        for col in numeric_cols:
            z = np.abs(sp_stats.zscore(df[col].dropna()))
            n_outliers = int((z > 3).sum())
            if n_outliers > 0:
                outlier_info[col] = {
                    "count": n_outliers,
                    "pct": f"{n_outliers / len(df):.1%}",
                    "threshold": "Z > 3",
                }

    report["outliers"] = outlier_info
    total_outliers = sum(v["count"] for v in outlier_info.values())
    report["steps"].append(
        f"异常值检测（{outlier_method}）：{len(outlier_info)} 列存在共 {total_outliers} 个异常值"
    )

    # ── 汇总 ───────────────────────────────────────────────
    report["final_rows"] = len(df)
    report["final_cols"] = len(df.columns)
    report["missing_handled"] = report["original_rows"] - report["final_rows"]
    report["dtypes"] = df.dtypes.astype(str).to_dict()

    # 数据质量评分（0-100）
    score = 100
    if report["duplicates_removed"] > 0:
        score -= min(10, report["duplicates_removed"] / report["original_rows"] * 100)
    if missing_summary:
        avg_missing = np.mean([float(v.strip("%")) for v in missing_summary.values()])
        score -= min(30, avg_missing)
    if total_outliers > 0:
        score -= min(20, total_outliers / report["original_rows"] * 100)
    report["quality_score"] = max(0, round(score))

    return df, report