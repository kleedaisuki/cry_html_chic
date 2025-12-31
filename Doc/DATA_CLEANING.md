# 数据清洗规格
# Data Cleaning Specification

> **版本**: v1.0
> **创建日期**: 2025-12-31
> **状态**: 🚧 开发中

---

## 概述

本文档定义数据清洗优化器（`data_cleaning`）的功能、配置参数和使用方法。

数据清洗优化器是 Transform 工具链中的第二阶段（Optimizer），负责对 `frontend` 解析后的 IRModule 进行清洗、验证和聚合处理。

---

## 功能特性

### 1. 缺失值处理

| 配置项 | 类型 | 说明 |
|-------|------|------|
| `drop_null_fields` | `string[]` | 要删除的包含 null 值的字段列表 |
| `drop_missing_rows` | `boolean` | 是否删除包含任何 null 值的行 |

### 2. 异常值检测

**方法 A：固定边界**
```json
{
  "outlier_bounds": {
    "min": 0,
    "max": 50000
  }
}
```

**方法 B：自动 IQR（默认）**
```json
{
  "outlier_bounds": null
}
```

| 配置项 | 类型 | 说明 |
|-------|------|------|
| `outlier_bounds` | `object \| null` | 异常值边界，`null` 表示使用 IQR 自动计算 |
| `numeric_fields` | `string[]` | 要检查异常值的数值字段列表 |

### 3. 时间聚合

| 配置项 | 类型 | 说明 |
|-------|------|------|
| `aggregate_by_hour` | `boolean` | 是否按小时聚合时间序列数据 |
| `time_field` | `string` | 时间字段名（默认: `timestamp`） |
| `value_field` | `string` | 要聚合的数值字段名（默认: `flow`） |
| `group_by` | `string[]` | 分组字段列表 |

### 4. 数值字段验证

| 配置项 | 类型 | 说明 |
|-------|------|------|
| `numeric_fields` | `string[]` | 指定哪些字段是数值类型，用于异常值检测 |

---

## 配置示例

### 完整配置

```json
{
  "optimizer": {
    "name": "data_cleaning",
    "config": {
      "drop_null_fields": ["flow", "capacity", "utilization"],
      "drop_missing_rows": true,
      "outlier_bounds": {
        "min": 0,
        "max": 50000
      },
      "numeric_fields": ["flow", "capacity", "utilization"],
      "aggregate_by_hour": true,
      "time_field": "timestamp",
      "value_field": "flow",
      "group_by": ["route_id", "transport_type"]
    }
  }
}
```

### 客流数据配置

```json
{
  "optimizer": {
    "name": "data_cleaning",
    "config": {
      "drop_missing_rows": true,
      "outlier_bounds": null,
      "numeric_fields": ["flow"],
      "aggregate_by_hour": true,
      "time_field": "timestamp",
      "value_field": "flow",
      "group_by": ["route_id"]
    }
  }
}
```

### 最小配置

```json
{
  "optimizer": {
    "name": "data_cleaning",
    "config": {}
  }
}
```

---

## 输出格式

### IRModule 结构

```json
{
  "ir_kind": "data_cleaning",
  "provenance": {
    "source_name": "...",
    "fetched_at_iso": "...",
    "cleaning": {
      "optimizer": "data_cleaning@0.1.0",
      "drop_null_fields": [...],
      "drop_missing_rows": true,
      "outlier_bounds": [0, 50000],
      "aggregate_by_hour": true
    }
  },
  "data": [...],
  "_quality_report": {
    "original_record_count": 1000,
    "cleaned_record_count": 980,
    "dropped_count": 20,
    "null_fields": {
      "flow": 5,
      "capacity": 3
    },
    "outlier_fields": {
      "flow": 12
    },
    "quality_score": 98.0
  }
}
```

### 聚合后的数据记录

```json
{
  "route_id": "NS_LINE",
  "timestamp": "2024-01-01T08",
  "flow_sum": 85000,
  "flow_avg": 8500,
  "flow_min": 7500,
  "flow_max": 9500,
  "record_count": 10
}
```

---

## 在配置中使用

### 1. 添加到 plugins 列表

在 `configs/ingest/default.json` 的 `plugins` 数组中添加：

```json
{
  "plugins": [
    "ingest.transform.optimizer.data_cleaning"
  ]
}
```

### 2. 在 job 中配置

```json
{
  "jobs": [
    {
      "name": "passenger_flow",
      "transform": {
        "frontend": {
          "name": "json_payload",
          "config": {
            "extract_key": "value"
          }
        },
        "optimizer": {
          "name": "data_cleaning",
          "config": {
            "drop_missing_rows": true,
            "aggregate_by_hour": true,
            "time_field": "timestamp",
            "value_field": "flow",
            "group_by": ["route_id"]
          }
        },
        "backend": {
          "name": "js_constants",
          "config": {}
        }
      }
    }
  ]
}
```

---

## 质量报告指标

| 指标 | 说明 |
|------|------|
| `original_record_count` | 原始记录数 |
| `cleaned_record_count` | 清洗后记录数 |
| `dropped_count` | 删除的记录数 |
| `null_fields` | 各字段的 null 值统计 |
| `outlier_fields` | 各字段的异常值统计 |
| `quality_score` | 数据质量评分 (0-100%) |

---

## 异常值检测方法

### IQR（四分位距）方法

当 `outlier_bounds` 设为 `null` 时，使用 IQR 自动计算边界：

```
Q1 = 第 25 百分位数
Q3 = 第 75 百分位数
IQR = Q3 - Q1
下界 = Q1 - 1.5 × IQR
上界 = Q3 + 1.5 × IQR
```

### 固定边界方法

当 `outlier_bounds` 设为 `{min, max}` 时，直接使用指定边界。

---

## 时间聚合规则

1. **时间解析**：支持 ISO 8601 格式和 Unix 时间戳
2. **小时提取**：取时间戳的小时部分（如 `2024-01-01T08:30:00` -> `2024-01-01T08`）
3. **分组聚合**：按时间 + `group_by` 字段分组
4. **聚合计算**：
   - `sum`：求和
   - `avg`：平均值
   - `min`：最小值
   - `max`：最大值
   - `count`：记录数

---

## 最佳实践

### MRT 客流量数据

```json
{
  "drop_missing_rows": true,
  "outlier_bounds": {
    "min": 0,
    "max": 12000
  },
  "numeric_fields": ["flow"],
  "aggregate_by_hour": true,
  "time_field": "timestamp",
  "value_field": "flow",
  "group_by": ["route_id"]
}
```

### LRT 客流量数据

```json
{
  "drop_missing_rows": true,
  "outlier_bounds": {
    "min": 0,
    "max": 3500
  },
  "numeric_fields": ["flow"],
  "aggregate_by_hour": true,
  "time_field": "timestamp",
  "value_field": "flow",
  "group_by": ["route_id"]
}
```

### 公交客流量数据

```json
{
  "drop_missing_rows": true,
  "outlier_bounds": {
    "min": 0,
    "max": 800
  },
  "numeric_fields": ["flow"],
  "aggregate_by_hour": true,
  "time_field": "timestamp",
  "value_field": "flow",
  "group_by": ["route_id"]
}
```

---

## 变更历史

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-12-31 | 1.0 | 初始版本 |

---

**下一步**：
- 在 `configs/ingest/default.json` 中添加插件配置
- 测试数据清洗效果
- 根据实际数据调整异常值边界
