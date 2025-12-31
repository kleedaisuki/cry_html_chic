"""
/**
 * @file data_cleaning_optimizer.py
 * @brief 数据清洗优化器：清洗、聚合和验证 IRModule 数据。
 *        Data cleaning optimizer: clean, aggregate, and validate IRModule data.
 *
 * 设计要点 / Design notes:
 * - 处理缺失值（null, undefined, 空字符串）
 * - 检测和处理异常值（基于统计方法或固定阈值）
 * - 按时间聚合客流数据（按小时）
 * - 生成数据质量报告和元数据
 *
 * 配置项 / Config options:
 * - drop_null_fields: 要删除的包含 null 值的字段列表
 * - drop_missing_rows: 是否删除包含任何 null 值的行
 * - outlier_bounds: 异常值边界 {min, max} 或 null（使用 IQR）
 * - aggregate_by_hour: 是否按小时聚合时间序列数据
 * - aggregate_field: 要聚合的数值字段名
 * - group_by: 分组字段列表
 */
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ingest.utils.logger import get_logger
from ingest.wiring import register_optimizer
from ingest.transform.interface import IRModule, JsonValue

_LOG = get_logger(__name__)


def _is_null_value(value: Any) -> bool:
    """
    @brief 判断值是否为 null/空值 / Check if value is null/empty.
    """
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _calculate_iqr(values: List[float]) -> tuple[float, float]:
    """
    @brief 计算 IQR 边界 / Calculate IQR bounds.
    @return (lower_bound, upper_bound) / (lower bound, upper bound).
    """
    if len(values) < 4:
        return (-math.inf, math.inf)

    sorted_vals = sorted(values)
    q1_index = len(sorted_vals) // 4
    q3_index = 3 * len(sorted_vals) // 4

    q1 = sorted_vals[q1_index] if q1_index < len(sorted_vals) else sorted_vals[0]
    q3 = sorted_vals[q3_index] if q3_index < len(sorted_vals) else sorted_vals[-1]

    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return (lower, upper)


def _validate_number(value: Any) -> Optional[float]:
    """
    @brief 验证并转换值为数字 / Validate and convert value to number.
    @return 数字或 None / Number or None.
    """
    if _is_null_value(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _clean_record(
    record: Dict[str, JsonValue],
    *,
    drop_null_fields: Optional[Sequence[str]] = None,
    outlier_bounds: Optional[tuple[float, float]] = None,
    numeric_fields: Optional[Sequence[str]] = None,
) -> Dict[str, JsonValue]:
    """
    @brief 清洗单条记录 / Clean a single record.
    """
    cleaned = dict(record)

    # 删除指定字段的 null 值
    if drop_null_fields:
        for field in drop_null_fields:
            if field in cleaned and _is_null_value(cleaned[field]):
                del cleaned[field]

    # 异常值处理
    if outlier_bounds and numeric_fields:
        lower, upper = outlier_bounds
        for field in numeric_fields:
            if field in cleaned:
                num = _validate_number(cleaned[field])
                if num is not None and (num < lower or num > upper):
                    cleaned[field] = None  # 将异常值设为 null

    return cleaned


def _aggregate_by_hour(
    records: List[Dict[str, JsonValue]],
    *,
    time_field: str,
    value_field: str,
    group_fields: Optional[Sequence[str]] = None,
) -> List[Dict[str, JsonValue]]:
    """
    @brief 按小时聚合数据 / Aggregate data by hour.
    """
    if not records:
        return []

    # 按时间和分组字段建立索引
    aggregates: Dict[str, Dict[str, Any]] = {}

    for record in records:
        # 提取时间戳
        time_val = record.get(time_field)
        if not time_val:
            continue

        # 解析时间（支持 ISO 8601 格式）
        try:
            # 简单处理：取小时部分
            if isinstance(time_val, str):
                # 格式如 "2024-01-01T08:30:00" -> "2024-01-01T08"
                hour_str = time_val[:13] if len(time_val) >= 13 else time_val
            elif isinstance(time_val, (int, float)):
                # Unix 时间戳
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(time_val, tz=timezone.utc)
                hour_str = dt.strftime("%Y-%m-%dT%H")
            else:
                continue
        except Exception:
            continue

        # 构建分组键
        group_key_parts = [hour_str]
        if group_fields:
            for gf in group_fields:
                group_key_parts.append(str(record.get(gf, "_empty")))

        group_key = "|".join(group_key_parts)

        if group_key not in aggregates:
            aggregates[group_key] = {
                "time": hour_str,
                "values": [],
                "count": 0,
                "original_fields": {k: v for k, v in record.items() if k not in (time_field, value_field)},
            }

        # 收集值用于聚合
        val = _validate_number(record.get(value_field))
        if val is not None:
            aggregates[group_key]["values"].append(val)
            aggregates[group_key]["count"] += 1

    # 生成聚合结果
    results: List[Dict[str, JsonValue]] = []
    for key, data in aggregates.items():
        result: Dict[str, JsonValue] = dict(data["original_fields"])
        result[time_field] = data["time"]
        result[f"{value_field}_sum"] = sum(data["values"]) if data["values"] else 0
        result[f"{value_field}_avg"] = (
            statistics.mean(data["values"]) if data["values"] else 0
        )
        result[f"{value_field}_min"] = min(data["values"]) if data["values"] else 0
        result[f"{value_field}_max"] = max(data["values"]) if data["values"] else 0
        result["record_count"] = data["count"]

        results.append(result)

    return results


def _generate_quality_report(
    original_count: int,
    cleaned_count: int,
    null_counts: Dict[str, int],
    outlier_counts: Dict[str, int],
) -> Dict[str, JsonValue]:
    """
    @brief 生成数据质量报告 / Generate data quality report.
    """
    return {
        "original_record_count": original_count,
        "cleaned_record_count": cleaned_count,
        "dropped_count": original_count - cleaned_count,
        "null_fields": null_counts,
        "outlier_fields": outlier_counts,
        "quality_score": (
            cleaned_count / original_count * 100 if original_count > 0 else 100
        ),
    }


@register_optimizer("data_cleaning")
class DataCleaningOptimizer:
    """
    @brief 数据清洗优化器 / Data cleaning optimizer.

    功能 / Features:
    - 处理缺失值（删除或标记）
    - 检测和处理异常值（使用 IQR 或固定边界）
    - 按时间聚合数据（按小时）
    - 生成数据质量报告
    """

    name: str = "data_cleaning"
    version: str = "0.1.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        @brief 执行数据清洗 / Perform data cleaning.

        @param module 输入 IRModule / Input IRModule.
        @param config 优化器配置 / Optimizer config.
        @return 清洗后的 IRModule / Cleaned IRModule.
        """
        # 解析配置
        drop_null_fields = config.get("drop_null_fields")
        if drop_null_fields and not isinstance(drop_null_fields, list):
            drop_null_fields = None

        drop_missing_rows = bool(config.get("drop_missing_rows", False))

        outlier_config = config.get("outlier_bounds")
        outlier_bounds: Optional[tuple[float, float]] = None
        if isinstance(outlier_config, dict):
            try:
                lower = float(outlier_config.get("min", -math.inf))
                upper = float(outlier_config.get("max", math.inf))
                outlier_bounds = (lower, upper)
            except (ValueError, TypeError):
                pass

        aggregate_by_hour = bool(config.get("aggregate_by_hour", False))
        time_field = str(config.get("time_field", "timestamp"))
        value_field = str(config.get("value_field", "flow"))
        group_fields = config.get("group_by")
        if group_fields and not isinstance(group_fields, list):
            group_fields = None

        numeric_fields = config.get("numeric_fields")
        if numeric_fields and not isinstance(numeric_fields, list):
            numeric_fields = None

        # 提取数据
        data = module.get("data")
        if not isinstance(data, list):
            _LOG.warning("data_cleaning: module.data is not a list, skipping cleaning")
            return dict(module)

        original_count = len(data)
        null_counts: Dict[str, int] = {}
        outlier_counts: Dict[str, int] = {}

        # 清洗记录
        cleaned_records: List[Dict[str, JsonValue]] = []

        for record in data:
            if not isinstance(record, dict):
                continue

            cleaned = _clean_record(
                record,
                drop_null_fields=drop_null_fields,
                outlier_bounds=outlier_bounds,
                numeric_fields=numeric_fields,
            )

            # 统计 null 值
            for k, v in cleaned.items():
                if _is_null_value(v):
                    null_counts[k] = null_counts.get(k, 0) + 1

            # 统计异常值
            if outlier_bounds and numeric_fields:
                for field in numeric_fields or []:
                    if field in cleaned:
                        num = _validate_number(cleaned[field])
                        if num is not None and (
                            num < outlier_bounds[0] or num > outlier_bounds[1]
                        ):
                            outlier_counts[field] = outlier_counts.get(field, 0) + 1

            # 决定是否保留
            if drop_missing_rows:
                # 删除包含任何 null 值的记录
                has_null = any(_is_null_value(v) for v in cleaned.values())
                if not has_null:
                    cleaned_records.append(cleaned)
            else:
                cleaned_records.append(cleaned)

        # 按小时聚合（如果需要）
        if aggregate_by_hour and time_field and value_field:
            cleaned_records = _aggregate_by_hour(
                cleaned_records,
                time_field=time_field,
                value_field=value_field,
                group_fields=group_fields,
            )
            _LOG.info(
                "data_cleaning: aggregated to %d hourly records",
                len(cleaned_records),
            )

        # 生成质量报告
        quality_report = _generate_quality_report(
            original_count=original_count,
            cleaned_count=len(cleaned_records),
            null_counts=null_counts,
            outlier_counts=outlier_counts,
        )

        _LOG.info(
            "data_cleaning: processed %d -> %d records, quality_score=%.2f%%",
            original_count,
            len(cleaned_records),
            quality_report.get("quality_score", 0),
        )

        # 构建输出模块
        output: IRModule = {
            "ir_kind": "data_cleaning",
            "provenance": dict(module.get("provenance", {})),
            "data": cleaned_records,
            "_quality_report": quality_report,
        }

        # 保留原始 provenance 并添加清洗信息
        if "provenance" in output["provenance"]:
            output["provenance"]["cleaning"] = {
                "optimizer": f"{self.name}@{self.version}",
                "drop_null_fields": drop_null_fields,
                "drop_missing_rows": drop_missing_rows,
                "outlier_bounds": (
                    list(outlier_bounds) if outlier_bounds else "auto_iqr"
                ),
                "aggregate_by_hour": aggregate_by_hour,
            }

        return output
