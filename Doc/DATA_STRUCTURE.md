# 数据结构规范
# Data Structure Specification v1.0

> **状态**: ✅ 已确定  
> **最后更新**: 2024-12-17

---

## 目录
- [GeoJSON 格式规范](#geojson-格式规范)
- [时间格式规范](#时间格式规范)
- [颜色方案规范](#颜色方案规范)
- [数据类型定义](#数据类型定义)
- [原始数据格式](#原始数据格式)

---

## GeoJSON 格式规范

所有地理空间数据必须遵循 **GeoJSON RFC 7946** 标准。

### 坐标顺序
⚠️ **重要**: GeoJSON 中坐标顺序为 `[经度, 纬度]`（与 Leaflet 相反）

```json
{
  "type": "Point",
  "coordinates": [103.8198, 1.3521]  // [经度, 纬度]
}
```

### 线路几何数据（LineString）

```json
{
  "type": "LineString",
  "coordinates": [
    [103.7423, 1.3330],  // 起点 [经度, 纬度]
    [103.7497, 1.3489],  // 中间点
    [103.7564, 1.3587]   // 终点
  ]
}
```

**使用场景**:
- MRT/LRT 线路
- 公交线路

**注意事项**:
- 坐标点数量建议在 20-100 个之间（过少导致不平滑，过多影响性能）
- 坐标点应按线路实际走向排序
- 经度范围：103.6 ~ 104.1（新加坡）
- 纬度范围：1.1 ~ 1.5（新加坡）

### 站点几何数据（Point）

```json
{
  "type": "Point",
  "coordinates": [103.7423, 1.3330]  // [经度, 纬度]
}
```

**使用场景**:
- MRT/LRT 站点
- 公交站点（可选）

### 前后端坐标转换

```javascript
// 前端代码示例

// GeoJSON → Leaflet (后端 API 返回的数据)
const geoJsonCoords = [103.8198, 1.3521];  // [lng, lat]
const leafletCoords = [geoJsonCoords[1], geoJsonCoords[0]];  // [lat, lng]

// Leaflet → GeoJSON (前端发送数据到后端，如果需要)
const leafletCoords = [1.3521, 103.8198];  // [lat, lng]
const geoJsonCoords = [leafletCoords[1], leafletCoords[0]];  // [lng, lat]
```

---

## 时间格式规范

### ISO 8601 标准

统一使用 ISO 8601 格式，时区为 **UTC+8**（新加坡标准时间）。

#### 完整日期时间
```
2024-01-01T08:00:00
```
- `YYYY-MM-DD`: 日期部分
- `T`: 分隔符
- `HH:mm:ss`: 时间部分
- **不包含时区后缀**（约定为 UTC+8）

#### 仅日期
```
2024-01-01
```

#### 仅时间
```
08:00:00
```

### 前端时间处理

推荐使用 **Day.js**（轻量级，2KB）：

```javascript
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

// 设置默认时区
dayjs.tz.setDefault('Asia/Singapore');

// 解析 API 返回的时间
const apiTime = '2024-01-01T08:00:00';
const parsed = dayjs.tz(apiTime, 'Asia/Singapore');

// 格式化显示
parsed.format('YYYY-MM-DD HH:mm');  // "2024-01-01 08:00"
parsed.format('h:mm A');             // "8:00 AM"

// 时间运算
parsed.add(1, 'hour');               // 增加1小时
parsed.subtract(30, 'minute');       // 减少30分钟
```

### 后端时间处理

```python
import pandas as pd
from datetime import datetime

# 解析 ISO 8601 字符串
time_str = '2024-01-01T08:00:00'
dt = pd.to_datetime(time_str)

# 生成 ISO 8601 字符串
dt.isoformat()  # '2024-01-01T08:00:00'

# 时区处理（如果需要）
import pytz
singapore_tz = pytz.timezone('Asia/Singapore')
dt_sg = dt.tz_localize(singapore_tz)
```

---

## 颜色方案规范

为确保前后端视觉一致性，预定义以下颜色方案。

### 交通类型颜色映射

| 交通类型 | ID | D3 插值器 | 域范围 [min, max] | 说明 |
|---------|----|-----------|--------------------|------|
| 地铁 | `mrt` | `d3.interpolateBlues` | [0, 12000] | 浅蓝→深蓝 |
| 轻轨 | `lrt` | `d3.interpolateGreens` | [0, 3500] | 浅绿→深绿 |
| 公交 | `bus` | `d3.interpolateOranges` | [0, 800] | 浅橙→深橙 |

### 前端颜色映射实现

```javascript
// 定义颜色比例尺
const colorScales = {
  mrt: d3.scaleSequential()
    .domain([0, 12000])
    .interpolator(d3.interpolateBlues),
  
  lrt: d3.scaleSequential()
    .domain([0, 3500])
    .interpolator(d3.interpolateGreens),
  
  bus: d3.scaleSequential()
    .domain([0, 800])
    .interpolator(d3.interpolateOranges)
};

// 使用示例
const mrtFlow = 8500;
const color = colorScales.mrt(mrtFlow);  // 返回 RGB 颜色字符串
```

### 颜色值示例

**MRT (Blues)** - 客流量 0 → 12000:
- 0: `rgb(247, 251, 255)` (浅蓝)
- 6000: `rgb(107, 174, 214)` (中蓝)
- 12000: `rgb(8, 48, 107)` (深蓝)

**LRT (Greens)** - 客流量 0 → 3500:
- 0: `rgb(247, 252, 245)` (浅绿)
- 1750: `rgb(116, 196, 118)` (中绿)
- 3500: `rgb(0, 68, 27)` (深绿)

**Bus (Oranges)** - 客流量 0 → 800:
- 0: `rgb(255, 245, 235)` (浅橙)
- 400: `rgb(253, 174, 97)` (中橙)
- 800: `rgb(127, 39, 4)` (深橙)

### 线路固有颜色

MRT/LRT 线路有官方颜色，用于图例和静态展示：

```json
{
  "NS_LINE": "#D42E12",  // 红色（南北线）
  "EW_LINE": "#009645",  // 绿色（东西线）
  "NE_LINE": "#9900AA",  // 紫色（东北线）
  "CC_LINE": "#FA9E0D",  // 橙色（环线）
  "DT_LINE": "#005EC4",  // 蓝色（滨海市区线）
  "TE_LINE": "#9D5B25"   // 棕色（汤申-东海岸线）
}
```

**使用场景**:
- 图例中显示线路名称
- 未加载客流数据时的默认颜色
- 站点标记颜色

---

## 数据类型定义

### TransitType (交通类型)

```typescript
type TransitType = 'mrt' | 'lrt' | 'bus';
```

### Route (线路)

```typescript
interface Route {
  route_id: string;          // 唯一标识符，如 "NS_LINE"
  route_name: string;        // 线路名称，如 "North-South Line"
  route_code: string;        // 线路代码，如 "NS"
  type: TransitType;         // 交通类型
  capacity: number;          // 理论最大承载量（人次/小时）
  color: string;             // 线路颜色（HEX 格式）
  stations: Station[] | null; // 站点列表（公交为 null）
  geometry: GeoJSON.LineString; // 线路几何
  operational: boolean;       // 是否运营中
  operator: string;           // 运营商名称
}
```

### Station (站点)

```typescript
interface Station {
  id: string;                // 站点 ID，如 "NS1"
  name: string;              // 站点名称，如 "Jurong East"
  position: [number, number]; // [纬度, 经度]
}
```

### PassengerFlow (客流数据 - 线路级别)

```typescript
interface PassengerFlowRoute {
  route_id: string;          // 线路 ID
  type: TransitType;         // 交通类型
  flow: number;              // 客流量（人次/小时）
  capacity: number;          // 线路容量
  utilization: number;       // 利用率（flow / capacity）
  direction: {               // 方向分布（公交为 null）
    inbound: number;         // 进城方向
    outbound: number;        // 出城方向
  } | null;
}
```

### PassengerFlow (客流数据 - 站点级别)

```typescript
interface PassengerFlowStation {
  station_id: string;        // 站点 ID
  station_name: string;      // 站点名称
  type: TransitType;         // 交通类型
  flow: number;              // 站点总客流
  entry: number;             // 进站人数
  exit: number;              // 出站人数
  interchange: boolean;      // 是否为换乘站
  position: [number, number]; // [纬度, 经度]
}
```

### Metadata (系统元数据)

```typescript
interface Metadata {
  version: string;
  dataset: {
    name: string;
    description: string;
    source: string;
    last_updated: string;    // ISO 8601
  };
  temporal_range: {
    start_date: string;      // ISO 8601
    end_date: string;        // ISO 8601
    granularity: 'hourly' | 'daily';
    total_hours: number;
  };
  transit_types: TransitTypeConfig[];
  map_config: {
    center: [number, number]; // [纬度, 经度]
    zoom_default: number;
    zoom_min: number;
    zoom_max: number;
    bounds: [[number, number], [number, number]]; // [[西南], [东北]]
  };
}
```

---

## 原始数据格式

### 客流数据 CSV

后端预处理前的原始数据格式：

```csv
timestamp,route_id,type,passenger_count,direction
2024-01-01T00:00:00,NS_LINE,mrt,1234,inbound
2024-01-01T00:00:00,NS_LINE,mrt,987,outbound
2024-01-01T00:00:00,EW_LINE,mrt,2341,inbound
2024-01-01T00:00:00,BUS_14,bus,45,
```

**字段说明**:
- `timestamp`: ISO 8601 格式
- `route_id`: 线路 ID
- `type`: 交通类型
- `passenger_count`: 客流量（原始值）
- `direction`: 方向（inbound/outbound，公交为空）

### 线路几何数据 GeoJSON

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "route_id": "NS_LINE",
        "route_name": "North-South Line",
        "type": "mrt",
        "color": "#D42E12",
        "operator": "SMRT"
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [103.7423, 1.3330],
          [103.7497, 1.3489]
        ]
      }
    }
  ]
}
```

### 站点数据 JSON

```json
{
  "stations": [
    {
      "id": "NS1",
      "name": "Jurong East",
      "routes": ["NS_LINE", "EW_LINE"],
      "interchange": true,
      "position": [1.3330, 103.7423]
    },
    {
      "id": "NS2",
      "name": "Bukit Batok",
      "routes": ["NS_LINE"],
      "interchange": false,
      "position": [1.3489, 103.7497]
    }
  ]
}
```

---

## 数据预处理流程

### 步骤 1: 加载原始数据

```python
import pandas as pd

# 加载客流数据
flow_df = pd.read_csv('data/raw/transit_flow.csv')
flow_df['timestamp'] = pd.to_datetime(flow_df['timestamp'])

# 加载线路几何数据
import geopandas as gpd
routes_gdf = gpd.read_file('data/raw/routes.geojson')
```

### 步骤 2: 按小时聚合

```python
# 按时间和线路聚合
aggregated = flow_df.groupby(['timestamp', 'route_id', 'type', 'direction']).agg({
    'passenger_count': 'sum'
}).reset_index()

# 透视方向数据
direction_pivot = aggregated.pivot_table(
    index=['timestamp', 'route_id', 'type'],
    columns='direction',
    values='passenger_count',
    fill_value=0
).reset_index()

direction_pivot.rename(columns={'inbound': 'inbound', 'outbound': 'outbound'}, inplace=True)

# 计算总流量
direction_pivot['flow'] = direction_pivot['inbound'] + direction_pivot['outbound']
```

### 步骤 3: 添加容量和利用率

```python
# 容量映射
capacity_map = {'mrt': 12000, 'lrt': 3500, 'bus': 800}
direction_pivot['capacity'] = direction_pivot['type'].map(capacity_map)

# 计算利用率
direction_pivot['utilization'] = direction_pivot['flow'] / direction_pivot['capacity']
```

### 步骤 4: 保存处理后的数据

```python
# 保存为 CSV（用于 API）
direction_pivot.to_csv('data/processed/flow_aggregated.csv', index=False)

# 或保存为 Parquet（更高效）
direction_pivot.to_parquet('data/processed/flow_aggregated.parquet', index=False)
```

---

## 数据质量检查

### 必要的数据检查

```python
# 1. 检查缺失值
assert flow_df['timestamp'].notna().all(), "timestamp 有缺失值"
assert flow_df['route_id'].notna().all(), "route_id 有缺失值"

# 2. 检查时间范围
assert flow_df['timestamp'].min() >= pd.Timestamp('2024-01-01'), "起始时间过早"
assert flow_df['timestamp'].max() <= pd.Timestamp('2024-12-31'), "结束时间过晚"

# 3. 检查客流量范围
assert (flow_df['passenger_count'] >= 0).all(), "客流量不能为负"
assert (flow_df['passenger_count'] <= 20000).all(), "客流量异常过高"

# 4. 检查交通类型
valid_types = {'mrt', 'lrt', 'bus'}
assert flow_df['type'].isin(valid_types).all(), "存在无效的交通类型"

# 5. 检查坐标范围
assert (routes_gdf.bounds['minx'] >= 103.6).all(), "经度超出新加坡范围"
assert (routes_gdf.bounds['maxx'] <= 104.1).all(), "经度超出新加坡范围"
assert (routes_gdf.bounds['miny'] >= 1.1).all(), "纬度超出新加坡范围"
assert (routes_gdf.bounds['maxy'] <= 1.5).all(), "纬度超出新加坡范围"
```

---

## 数据存储建议

### 小规模数据（< 100MB）
- **格式**: JSON 文件
- **优点**: 简单，易于调试
- **缺点**: 加载速度慢

```python
# 保存
import json
with open('data/processed/routes.json', 'w') as f:
    json.dump(routes_data, f, indent=2)

# 加载
with open('data/processed/routes.json', 'r') as f:
    routes_data = json.load(f)
```

### 中规模数据（100MB - 1GB）
- **格式**: Parquet
- **优点**: 压缩率高，加载速度快
- **缺点**: 需要额外依赖（pyarrow）

```python
# 保存
flow_df.to_parquet('data/processed/flow.parquet', engine='pyarrow')

# 加载
flow_df = pd.read_parquet('data/processed/flow.parquet')
```

### 大规模数据（> 1GB）
- **格式**: SQLite 数据库
- **优点**: 支持索引和查询
- **缺点**: 需要 SQL 知识

```python
import sqlite3

# 保存
conn = sqlite3.connect('data/processed/transit.db')
flow_df.to_sql('passenger_flow', conn, if_exists='replace', index=False)

# 创建索引
conn.execute('CREATE INDEX idx_timestamp ON passenger_flow(timestamp)')
conn.execute('CREATE INDEX idx_route_id ON passenger_flow(route_id)')
conn.close()

# 查询
conn = sqlite3.connect('data/processed/transit.db')
query = "SELECT * FROM passenger_flow WHERE timestamp = '2024-01-01T08:00:00'"
result = pd.read_sql_query(query, conn)
conn.close()
```

---

## 性能优化建议

### 1. 数据预加载
后端启动时将数据加载到内存：

```python
# app.py
print("Loading data...")
routes_data = json.load(open('data/processed/routes.json'))
flow_df = pd.read_parquet('data/processed/flow_aggregated.parquet')
print(f"Loaded {len(routes_data['routes'])} routes and {len(flow_df)} records")
```

### 2. 时间索引
对时间列建立索引加速查询：

```python
flow_df = flow_df.set_index('timestamp').sort_index()

# 快速查询
target_time = pd.Timestamp('2024-01-01T08:00:00')
result = flow_df.loc[target_time]
```

### 3. 数据缓存
前端缓存已请求的数据：

```javascript
const cache = new Map();

async function fetchPassengerFlow(datetime, types) {
  const cacheKey = `${datetime}_${types.join(',')}`;
  
  if (cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }
  
  const data = await api.fetchPassengerFlow(datetime, types);
  cache.set(cacheKey, data);
  return data;
}
```

---

## 常见问题

### Q1: 为什么 GeoJSON 和 Leaflet 的坐标顺序不同？
**A**: 这是历史原因。GeoJSON 遵循地理学惯例（经度在前），Leaflet 遵循数学惯例（纬度在前）。务必在前端进行转换。

### Q2: 如何处理超载情况（utilization > 1）？
**A**: 超载是真实情况（如早高峰）。前端应正常显示，可以用特殊颜色（如红色）标记。

### Q3: 公交线路为什么没有站点信息？
**A**: 公交站点数量过多（数千个），且变化频繁。初版仅提供线路级别的客流数据。

### Q4: 时间粒度为什么是小时而非分钟？
**A**: 小时粒度已足够展示客流趋势，且大幅减少数据量。如需分钟级数据，可在 Phase 2 扩展。

---

**文档维护者**: Jingren  
**审核状态**: ✅ 已确定  
**下一步**: 请阅读 `BACKEND_GUIDE.md` 或 `FRONTEND_GUIDE.md` 开始开发。
