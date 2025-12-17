# API 接口规范
# API Specification v1.0

> **状态**: ✅ 已确定（除非发现重大缺陷，否则不变更）  
> **最后更新**: 2024-12-17

---

## 目录
- [基础约定](#基础约定)
- [核心接口](#核心接口)
  - [1. 获取系统元数据](#1-获取系统元数据)
  - [2. 获取线路元数据](#2-获取线路元数据)
  - [3. 获取客流数据](#3-获取客流数据)
  - [4. 健康检查](#4-健康检查)
- [可选接口](#可选接口)
  - [5. 获取时间序列数据](#5-获取时间序列数据)
- [错误处理](#错误处理)
- [变更日志](#变更日志)

---

## 基础约定

### API Base URL
```
http://localhost:5000/api/v1
```

### 请求头
```http
Content-Type: application/json
Accept: application/json
```

### 编码
- **字符编码**: UTF-8
- **时间格式**: ISO 8601 (`YYYY-MM-DDTHH:mm:ss`)
- **坐标格式**: GeoJSON ([经度, 纬度])

### 响应格式
所有成功响应的 HTTP 状态码为 `200 OK`，响应体为 JSON 对象。

---

## 核心接口

### 1. 获取系统元数据

获取系统配置信息，包括时间范围、交通类型等基础信息。

**用途**: 前端启动时首次调用，用于初始化系统配置。

#### 请求
```http
GET /api/v1/metadata
```

#### 查询参数
无

#### 响应示例
```json
{
  "version": "1.0",
  "dataset": {
    "name": "Singapore Public Transit Flow",
    "description": "Hourly average passenger flow data",
    "source": "LTA DataMall / Custom Collection",
    "last_updated": "2024-12-15T00:00:00"
  },
  "temporal_range": {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-12-31T23:00:00",
    "granularity": "hourly",
    "total_hours": 8784
  },
  "transit_types": [
    {
      "id": "mrt",
      "name": "Mass Rapid Transit",
      "name_zh": "地铁",
      "max_capacity": 12000,
      "color_scheme": "blues",
      "total_routes": 6
    },
    {
      "id": "lrt",
      "name": "Light Rail Transit",
      "name_zh": "轻轨",
      "max_capacity": 3500,
      "color_scheme": "greens",
      "total_routes": 3
    },
    {
      "id": "bus",
      "name": "Public Bus",
      "name_zh": "公交",
      "max_capacity": 800,
      "color_scheme": "oranges",
      "total_routes": 350
    }
  ],
  "map_config": {
    "center": [1.3521, 103.8198],
    "zoom_default": 12,
    "zoom_min": 10,
    "zoom_max": 16,
    "bounds": [[1.1, 103.6], [1.5, 104.1]]
  }
}
```

#### 响应字段说明

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `version` | string | API 版本号 |
| `dataset.name` | string | 数据集名称 |
| `dataset.last_updated` | string | 数据最后更新时间（ISO 8601） |
| `temporal_range.start_date` | string | 数据起始时间 |
| `temporal_range.end_date` | string | 数据结束时间 |
| `temporal_range.granularity` | string | 时间粒度（hourly/daily） |
| `transit_types[].id` | string | 交通类型唯一标识 |
| `transit_types[].max_capacity` | number | 理论最大承载量（人次/小时） |
| `transit_types[].color_scheme` | string | D3 颜色方案名称（小写） |
| `map_config.center` | [number, number] | 地图中心坐标 [纬度, 经度] |
| `map_config.bounds` | [[number, number], [number, number]] | 地图边界 [[西南角], [东北角]] |

---

### 2. 获取线路元数据

获取所有公共交通线路的静态信息（名称、几何形状、容量等）。

**用途**: 前端初始化时加载，用于地图渲染。

#### 请求
```http
GET /api/v1/routes?types=mrt,lrt
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `types` | string | 否 | 逗号分隔的交通类型 | `mrt,lrt` |

**默认值**: 如果不提供，返回所有交通类型。

#### 响应示例
```json
{
  "routes": [
    {
      "route_id": "NS_LINE",
      "route_name": "North-South Line",
      "route_code": "NS",
      "type": "mrt",
      "capacity": 12000,
      "color": "#D42E12",
      "stations": [
        {
          "id": "NS1",
          "name": "Jurong East",
          "position": [1.3330, 103.7423]
        },
        {
          "id": "NS2",
          "name": "Bukit Batok",
          "position": [1.3489, 103.7497]
        }
      ],
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [103.7423, 1.3330],
          [103.7497, 1.3489],
          [103.7564, 1.3587]
        ]
      },
      "operational": true,
      "operator": "SMRT"
    },
    {
      "route_id": "BUS_14",
      "route_name": "Bus Service 14",
      "route_code": "14",
      "type": "bus",
      "capacity": 80,
      "color": "#FF8C00",
      "stations": null,
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [103.8198, 1.3521],
          [103.8234, 1.3567]
        ]
      },
      "operational": true,
      "operator": "SBS Transit"
    }
  ],
  "total_count": 359,
  "filters_applied": {
    "types": ["mrt", "lrt", "bus"]
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `route_id` | string | ✅ | 线路唯一标识符（主键） |
| `route_name` | string | ✅ | 线路名称 |
| `route_code` | string | ✅ | 线路代码（如 NS、14） |
| `type` | string | ✅ | 交通类型（mrt/lrt/bus） |
| `capacity` | number | ✅ | 线路理论最大承载量（人次/小时） |
| `color` | string | ✅ | 线路颜色（HEX 格式） |
| `stations` | array\|null | ⭕ | 站点列表（仅 MRT/LRT，公交为 null） |
| `stations[].id` | string | - | 站点 ID |
| `stations[].name` | string | - | 站点名称 |
| `stations[].position` | [number, number] | - | 站点坐标 [纬度, 经度] |
| `geometry` | object | ✅ | GeoJSON LineString 几何数据 |
| `geometry.type` | string | ✅ | 固定值 "LineString" |
| `geometry.coordinates` | array | ✅ | 坐标数组 [[经度, 纬度], ...] |
| `operational` | boolean | ✅ | 是否运营中 |
| `operator` | string | ✅ | 运营商名称 |

**注意**:
- `geometry.coordinates` 中坐标顺序为 `[经度, 纬度]`（GeoJSON 标准）
- `stations[].position` 中坐标顺序为 `[纬度, 经度]`（Leaflet 标准）

---

### 3. 获取客流数据

根据时间和交通类型查询客流量数据。

**用途**: 这是系统最核心的接口，时间轴播放和用户交互都会频繁调用。

#### 请求
```http
GET /api/v1/passenger-flow?datetime=2024-01-01T08:00:00&types=mrt,lrt&aggregation=route
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `datetime` | string | ✅ | 查询时间（ISO 8601） | `2024-01-01T08:00:00` |
| `types` | string | ⭕ | 逗号分隔的交通类型 | `mrt,lrt` |
| `aggregation` | string | ⭕ | 聚合方式（route/station） | `route` |

**默认值**:
- `types`: `mrt,lrt,bus`（所有类型）
- `aggregation`: `route`（按线路聚合）

#### 响应示例 (aggregation=route)
```json
{
  "timestamp": "2024-01-01T08:00:00",
  "data": [
    {
      "route_id": "NS_LINE",
      "type": "mrt",
      "flow": 8543,
      "capacity": 12000,
      "utilization": 0.712,
      "direction": {
        "inbound": 4821,
        "outbound": 3722
      }
    },
    {
      "route_id": "EW_LINE",
      "type": "mrt",
      "flow": 9210,
      "capacity": 12000,
      "utilization": 0.768,
      "direction": {
        "inbound": 5103,
        "outbound": 4107
      }
    },
    {
      "route_id": "BUS_14",
      "type": "bus",
      "flow": 234,
      "capacity": 80,
      "utilization": 2.925,
      "direction": null
    }
  ],
  "total_flow": 78543,
  "filters_applied": {
    "types": ["mrt", "lrt", "bus"],
    "aggregation": "route"
  },
  "cache_hint": {
    "ttl": 3600,
    "next_update": "2024-01-01T09:00:00"
  }
}
```

#### 响应字段说明（按线路聚合）

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | 数据对应的时间点（ISO 8601） |
| `data[].route_id` | string | 线路 ID（与 routes 接口对应） |
| `data[].type` | string | 交通类型 |
| `data[].flow` | number | 客流量（人次/小时） |
| `data[].capacity` | number | 线路容量 |
| `data[].utilization` | number | 利用率（flow / capacity，可能 > 1） |
| `data[].direction` | object\|null | 方向分布（公交为 null） |
| `data[].direction.inbound` | number | 进城方向客流 |
| `data[].direction.outbound` | number | 出城方向客流 |
| `total_flow` | number | 所有线路总客流 |
| `cache_hint` | object | 缓存建议（可选字段） |
| `cache_hint.ttl` | number | 建议缓存时间（秒） |

#### 响应示例 (aggregation=station)
```json
{
  "timestamp": "2024-01-01T08:00:00",
  "data": [
    {
      "station_id": "NS1",
      "station_name": "Jurong East",
      "type": "mrt",
      "flow": 3214,
      "entry": 1823,
      "exit": 1391,
      "interchange": true,
      "position": [1.3330, 103.7423]
    },
    {
      "station_id": "NS2",
      "station_name": "Bukit Batok",
      "type": "mrt",
      "flow": 1876,
      "entry": 982,
      "exit": 894,
      "interchange": false,
      "position": [1.3489, 103.7497]
    }
  ],
  "total_flow": 78543,
  "filters_applied": {
    "types": ["mrt", "lrt"],
    "aggregation": "station"
  }
}
```

#### 响应字段说明（按站点聚合）

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].station_id` | string | 站点 ID |
| `data[].station_name` | string | 站点名称 |
| `data[].flow` | number | 站点总客流（entry + exit） |
| `data[].entry` | number | 进站人数 |
| `data[].exit` | number | 出站人数 |
| `data[].interchange` | boolean | 是否为换乘站 |
| `data[].position` | [number, number] | 站点坐标 [纬度, 经度] |

---

### 4. 健康检查

检查后端服务可用性。

**用途**: 前端调试时使用，生产环境可用于监控。

#### 请求
```http
GET /api/v1/health
```

#### 查询参数
无

#### 响应示例
```json
{
  "status": "healthy",
  "timestamp": "2024-12-17T10:30:45",
  "version": "1.0.0",
  "data_loaded": true,
  "total_routes": 359,
  "memory_usage_mb": 128.5
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 健康状态（healthy/degraded/unhealthy） |
| `timestamp` | string | 当前服务器时间 |
| `version` | string | 后端版本号 |
| `data_loaded` | boolean | 数据是否已加载 |
| `total_routes` | number | 已加载的线路数量 |
| `memory_usage_mb` | number | 内存使用量（MB，可选） |

---

## 可选接口

以下接口为 Phase 2 扩展功能，初版可不实现。

### 5. 获取时间序列数据

获取指定线路在时间范围内的客流量趋势，用于生成统计图表。

**状态**: ⭕ Phase 2 - 可选实现

#### 请求
```http
GET /api/v1/timeseries?route_id=NS_LINE&start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:00:00&interval=hour
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `route_id` | string | ✅ | 线路 ID | `NS_LINE` |
| `start_date` | string | ✅ | 开始时间（ISO 8601） | `2024-01-01T00:00:00` |
| `end_date` | string | ✅ | 结束时间（ISO 8601） | `2024-01-31T23:00:00` |
| `interval` | string | ⭕ | 时间间隔（hour/day） | `hour` |

#### 响应示例
```json
{
  "route_id": "NS_LINE",
  "interval": "hour",
  "data_points": [
    {"timestamp": "2024-01-01T00:00:00", "flow": 234},
    {"timestamp": "2024-01-01T01:00:00", "flow": 187},
    {"timestamp": "2024-01-01T08:00:00", "flow": 8543}
  ],
  "statistics": {
    "mean": 4521,
    "max": 10234,
    "min": 123,
    "peak_hour": "2024-01-15T18:00:00"
  }
}
```

---

## 错误处理

### 错误响应格式

所有错误响应遵循统一格式，HTTP 状态码为 4xx 或 5xx：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": "datetime",
      "provided": "invalid-format"
    }
  }
}
```

### 错误码定义

| HTTP 状态码 | 错误码 | 说明 | 示例场景 |
|------------|--------|------|---------|
| 400 | `MISSING_PARAM` | 缺少必填参数 | 未提供 datetime 参数 |
| 400 | `INVALID_DATETIME` | 时间格式错误 | datetime 不符合 ISO 8601 |
| 400 | `INVALID_TYPE` | 交通类型无效 | types 包含未知类型 |
| 404 | `NO_DATA` | 查询时间无数据 | 指定时间点无客流记录 |
| 404 | `ROUTE_NOT_FOUND` | 线路不存在 | route_id 不存在 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 | 数据库连接失败 |
| 503 | `SERVICE_UNAVAILABLE` | 服务不可用 | 数据尚未加载 |

### 错误处理示例

**请求**: `GET /api/v1/passenger-flow`（缺少 datetime）

**响应**: 
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "MISSING_PARAM",
    "message": "Required parameter 'datetime' is missing",
    "details": {
      "required_params": ["datetime"]
    }
  }
}
```

**请求**: `GET /api/v1/passenger-flow?datetime=invalid-date`

**响应**:
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "INVALID_DATETIME",
    "message": "Invalid datetime format. Expected ISO 8601 (YYYY-MM-DDTHH:mm:ss)",
    "details": {
      "provided": "invalid-date",
      "example": "2024-01-01T08:00:00"
    }
  }
}
```

---

## 测试用例

### 1. 测试系统元数据
```bash
curl http://localhost:5000/api/v1/metadata
```

**期望**: 返回完整的系统配置信息。

### 2. 测试线路数据（仅 MRT）
```bash
curl "http://localhost:5000/api/v1/routes?types=mrt"
```

**期望**: 仅返回 MRT 线路。

### 3. 测试客流数据（正常情况）
```bash
curl "http://localhost:5000/api/v1/passenger-flow?datetime=2024-01-01T08:00:00&types=mrt,lrt"
```

**期望**: 返回 2024-01-01 08:00 的 MRT 和 LRT 客流数据。

### 4. 测试错误处理（缺少参数）
```bash
curl "http://localhost:5000/api/v1/passenger-flow"
```

**期望**: 返回 400 错误，错误码 `MISSING_PARAM`。

### 5. 测试健康检查
```bash
curl http://localhost:5000/api/v1/health
```

**期望**: 返回 `status: "healthy"`。

---

## 性能要求

| 端点 | 响应时间目标 | 并发请求 |
|------|-------------|---------|
| `/metadata` | < 100ms | 100 req/s |
| `/routes` | < 200ms | 50 req/s |
| `/passenger-flow` | < 500ms | 200 req/s |
| `/health` | < 50ms | 1000 req/s |

---

## 变更日志

| 版本 | 日期 | 变更内容 | 影响 |
|------|------|----------|------|
| 1.0 | 2024-12-17 | 初始版本 | - |

---

## 注意事项

1. **坐标顺序**: 
   - GeoJSON 中为 `[经度, 纬度]`
   - Leaflet 中为 `[纬度, 经度]`
   - 注意前后端转换

2. **时区**: 
   - 所有时间为新加坡时区（UTC+8）
   - 不使用时区后缀（如 +08:00）

3. **缓存策略**:
   - `/metadata` 可长期缓存（1天）
   - `/routes` 可长期缓存（1天）
   - `/passenger-flow` 建议缓存（1小时）

4. **数据一致性**:
   - `route_id` 在 `/routes` 和 `/passenger-flow` 中必须一致
   - `station_id` 在站点数据中必须唯一

---

**API 文档维护者**: Jingren  
**审核状态**: ✅ 已确定  
**下一步**: 请阅读 `DATA_STRUCTURE.md` 了解数据格式规范。
