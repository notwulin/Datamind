"""
轻量数据质量校验引擎
替代 Great Expectations，支持自定义规则验证
"""
import pandas as pd
import numpy as np
from typing import Any


class DataQualityCheck:
    """单条质量规则"""

    def __init__(self, name: str, column: str, check_type: str, params: dict | None = None):
        self.name = name
        self.column = column
        self.check_type = check_type
        self.params = params or {}
        self.passed = None
        self.details = ""

    def run(self, df: pd.DataFrame) -> bool:
        try:
            col = df[self.column]
        except KeyError:
            self.passed = False
            self.details = f"列 '{self.column}' 不存在"
            return False

        try:
            if self.check_type == "not_null":
                null_pct = col.isna().mean()
                threshold = self.params.get("max_null_pct", 0.0)
                self.passed = null_pct <= threshold
                self.details = f"空值率 {null_pct:.1%}（阈值 ≤{threshold:.0%}）"

            elif self.check_type == "unique":
                dup_pct = 1 - col.nunique() / len(col)
                self.passed = dup_pct <= self.params.get("max_dup_pct", 0.0)
                self.details = f"重复率 {dup_pct:.1%}"

            elif self.check_type == "in_range":
                lo, hi = self.params.get("min", -np.inf), self.params.get("max", np.inf)
                numeric_col = pd.to_numeric(col, errors="coerce")
                out_of_range = ((numeric_col < lo) | (numeric_col > hi)).sum()
                self.passed = out_of_range == 0
                self.details = f"越界数 {out_of_range}（范围 [{lo}, {hi}]）"

            elif self.check_type == "non_negative":
                numeric_col = pd.to_numeric(col, errors="coerce")
                negatives = (numeric_col < 0).sum()
                self.passed = negatives == 0
                self.details = f"负值数 {negatives}"

            elif self.check_type == "regex":
                pattern = self.params.get("pattern", "")
                match_pct = col.dropna().astype(str).str.match(pattern).mean()
                threshold = self.params.get("min_match_pct", 1.0)
                self.passed = match_pct >= threshold
                self.details = f"匹配率 {match_pct:.1%}（阈值 ≥{threshold:.0%}）"

            elif self.check_type == "dtype":
                expected = self.params.get("dtype", "")
                actual = str(col.dtype)
                self.passed = expected in actual
                self.details = f"实际类型 {actual}（期望 {expected}）"

            elif self.check_type == "cardinality":
                n_unique = col.nunique()
                lo = self.params.get("min", 0)
                hi = self.params.get("max", np.inf)
                self.passed = lo <= n_unique <= hi
                self.details = f"唯一值 {n_unique}（范围 [{lo}, {hi}]）"

            else:
                self.passed = False
                self.details = f"未知检测类型: {self.check_type}"

        except Exception as e:
            self.passed = False
            self.details = f"检测异常: {str(e)}"

        return self.passed


def auto_quality_checks(df: pd.DataFrame) -> list[DataQualityCheck]:
    """
    根据 DataFrame 自动生成一组质量规则并执行
    返回检测结果列表
    """
    checks = []

    for col in df.columns:
        # 所有列检测空值率
        check = DataQualityCheck(
            name=f"'{col}' 空值率 ≤ 20%",
            column=col,
            check_type="not_null",
            params={"max_null_pct": 0.20},
        )
        check.run(df)
        checks.append(check)

        # 数值列检测非负
        if pd.api.types.is_numeric_dtype(df[col]):
            if col.lower() in ("amount", "price", "revenue", "cost", "quantity",
                               "金额", "价格", "收入", "成本", "数量"):
                check = DataQualityCheck(
                    name=f"'{col}' 不含负值",
                    column=col,
                    check_type="non_negative",
                )
                check.run(df)
                checks.append(check)

            # 数值列范围合理性
            check = DataQualityCheck(
                name=f"'{col}' 值在合理范围内",
                column=col,
                check_type="in_range",
                params={"min": df[col].quantile(0.001), "max": df[col].quantile(0.999)},
            )
            check.run(df)
            checks.append(check)

        # 日期列检测范围
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            check = DataQualityCheck(
                name=f"'{col}' 日期在合理范围",
                column=col,
                check_type="in_range",
                params={
                    "min": pd.Timestamp("2000-01-01").timestamp(),
                    "max": pd.Timestamp("2030-12-31").timestamp(),
                },
            )
            # 日期范围检查用特殊逻辑
            min_date = df[col].min()
            max_date = df[col].max()
            check.passed = min_date >= pd.Timestamp("2000-01-01") and max_date <= pd.Timestamp("2030-12-31")
            check.details = f"范围 {min_date:%Y-%m-%d} ~ {max_date:%Y-%m-%d}"
            checks.append(check)

    return checks


def quality_report_summary(checks: list[DataQualityCheck]) -> dict:
    """生成质量检测摘要"""
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = total - passed

    return {
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed / total:.0%}" if total > 0 else "N/A",
        "results": [
            {
                "name": c.name,
                "column": c.column,
                "passed": c.passed,
                "details": c.details,
            }
            for c in checks
        ],
    }
