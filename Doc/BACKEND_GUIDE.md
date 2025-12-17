# 后端开发指南
# Backend Development Guide v1.0

> **目标读者**: Python/Flask 后端开发者或 AI  
> **前置阅读**: `API_SPECIFICATION.md`, `DATA_STRUCTURE.md`

---

## 目录
- [环境搭建](#环境搭建)
- [项目结构](#项目结构)
- [核心代码实现](#核心代码实现)
- [数据预处理](#数据预处理)
- [测试与调试](#测试与调试)
- [部署说明](#部署说明)

---

## 环境搭建

### 系统要求
- Python 3.8+
- pip 21.0+
- 可选：虚拟环境工具（venv/conda）

### 依赖安装

创建 `requirements.txt`:

```txt
Flask==3.0.0
Flask-CORS==4.0.0
pandas==2.1.4
numpy==1.26.2
python-dateutil==2.8.2
geopandas==0.14.1
pyarrow==14.0.1
```

安装依赖：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 验证安装

```bash
python3 << EOF
import flask
import pandas as pd
import geopandas as gpd
print("✅ All dependencies installed successfully!")
print(f"Flask version: {flask.__version__}")
print(f"Pandas version: {pd.__version__}")
EOF
```

---

## 项目结构

```
backend/
├── app.py                 # Flask 主程序（核心）
├── config.py              # 配置文件
├── requirements.txt       # 依赖清单
├── api/
│   ├── __init__.py
│   ├── metadata.py        # /metadata 端点
│   ├── routes.py          # /routes 端点
│   └── flow.py            # /passenger-flow 端点
├── data/
│   ├── raw/               # 原始数据
│   │   ├── transit_flow.csv
│   │   ├── routes.geojson
│   │   └── stations.json
│   └── processed/         # 处理后的数据
│       ├── flow_aggregated.parquet
│       ├── routes.json
│       └── metadata.json
├── scripts/
│   └── preprocess.py      # 数据预处理脚本
└── tests/
    └── test_api.py        # API 测试
```

---

## 核心代码实现

### 1. 配置文件 (config.py)

```python
import os

class Config:
    """应用配置"""
    # Flask 配置
    DEBUG = True
    PORT = 5000
    HOST = '0.0.0.0'
    
    # CORS 配置
    CORS_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
    
    # 数据路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')
    
    # 文件路径
    ROUTES_FILE = os.path.join(DATA_DIR, 'routes.json')
    FLOW_FILE = os.path.join(DATA_DIR, 'flow_aggregated.parquet')
    METADATA_FILE = os.path.join(DATA_DIR, 'metadata.json')
    
    # 缓存配置
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # 秒
    
    # API 版本
    API_VERSION = '1.0.0'
```

### 2. Flask 主程序 (app.py)

```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=Config.CORS_ORIGINS)

# ==================== 数据加载 ====================

print("🚀 Loading data...")

try:
    # 加载线路数据
    with open(Config.ROUTES_FILE, 'r', encoding='utf-8') as f:
        routes_data = json.load(f)
    print(f"✅ Loaded {len(routes_data['routes'])} routes")
    
    # 加载客流数据
    flow_df = pd.read_parquet(Config.FLOW_FILE)
    flow_df['timestamp'] = pd.to_datetime(flow_df['timestamp'])
    print(f"✅ Loaded {len(flow_df)} flow records")
    
    # 加载元数据
    with open(Config.METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    print(f"✅ Loaded metadata")
    
    print("✅ All data loaded successfully!")
    
except Exception as e:
    print(f"❌ Error loading data: {e}")
    raise

# ==================== 辅助函数 ====================

def make_error_response(code, message, details=None, status_code=400):
    """创建标准错误响应"""
    error_obj = {
        'error': {
            'code': code,
            'message': message
        }
    }
    if details:
        error_obj['error']['details'] = details
    return jsonify(error_obj), status_code

def validate_datetime(datetime_str):
    """验证并解析时间字符串"""
    try:
        return pd.to_datetime(datetime_str)
    except Exception:
        return None

def validate_types(types_str):
    """验证交通类型参数"""
    valid_types = {'mrt', 'lrt', 'bus'}
    types = set(types_str.split(','))
    if not types.issubset(valid_types):
        invalid = types - valid_types
        return None, invalid
    return list(types), None

# ==================== API 端点 ====================

@app.route('/api/v1/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': Config.API_VERSION,
        'data_loaded': True,
        'total_routes': len(routes_data['routes']),
        'total_records': len(flow_df)
    })

@app.route('/api/v1/metadata', methods=['GET'])
def get_metadata():
    """获取系统元数据"""
    return jsonify(metadata)

@app.route('/api/v1/routes', methods=['GET'])
def get_routes():
    """获取线路数据"""
    types_param = request.args.get('types')
    
    if types_param:
        types, invalid = validate_types(types_param)
        if invalid:
            return make_error_response(
                'INVALID_TYPE',
                f'Invalid transit types: {", ".join(invalid)}',
                {'valid_types': ['mrt', 'lrt', 'bus']}
            )
        
        # 过滤线路
        filtered_routes = [r for r in routes_data['routes'] if r['type'] in types]
        return jsonify({
            'routes': filtered_routes,
            'total_count': len(filtered_routes),
            'filters_applied': {'types': types}
        })
    
    return jsonify(routes_data)

@app.route('/api/v1/passenger-flow', methods=['GET'])
def get_passenger_flow():
    """获取客流数据（核心接口）"""
    # 获取参数
    datetime_str = request.args.get('datetime')
    types_param = request.args.get('types', 'mrt,lrt,bus')
    aggregation = request.args.get('aggregation', 'route')
    
    # 验证必填参数
    if not datetime_str:
        return make_error_response(
            'MISSING_PARAM',
            "Required parameter 'datetime' is missing",
            {'required_params': ['datetime']}
        )
    
    # 验证时间格式
    target_time = validate_datetime(datetime_str)
    if target_time is None:
        return make_error_response(
            'INVALID_DATETIME',
            'Invalid datetime format. Expected ISO 8601 (YYYY-MM-DDTHH:mm:ss)',
            {
                'provided': datetime_str,
                'example': '2024-01-01T08:00:00'
            }
        )
    
    # 验证交通类型
    types, invalid = validate_types(types_param)
    if invalid:
        return make_error_response(
            'INVALID_TYPE',
            f'Invalid transit types: {", ".join(invalid)}',
            {'valid_types': ['mrt', 'lrt', 'bus']}
        )
    
    # 验证聚合方式
    if aggregation not in ['route', 'station']:
        return make_error_response(
            'INVALID_AGGREGATION',
            f'Invalid aggregation: {aggregation}',
            {'valid_values': ['route', 'station']}
        )
    
    # 查询数据
    filtered = flow_df[
        (flow_df['timestamp'] == target_time) &
        (flow_df['type'].isin(types)) &
        (flow_df['aggregation'] == aggregation)
    ]
    
    if filtered.empty:
        return make_error_response(
            'NO_DATA',
            f'No data available for {datetime_str}',
            {
                'requested_time': datetime_str,
                'available_range': {
                    'start': metadata['temporal_range']['start_date'],
                    'end': metadata['temporal_range']['end_date']
                }
            },
            404
        )
    
    # 构建响应
    data_records = filtered.to_dict('records')
    
    # 格式化响应（根据聚合类型）
    if aggregation == 'route':
        # 处理方向数据
        for record in data_records:
            if record['type'] == 'bus':
                record['direction'] = None
            else:
                record['direction'] = {
                    'inbound': record.pop('inbound', 0),
                    'outbound': record.pop('outbound', 0)
                }
    
    result = {
        'timestamp': datetime_str,
        'data': data_records,
        'total_flow': int(filtered['flow'].sum()),
        'filters_applied': {
            'types': types,
            'aggregation': aggregation
        }
    }
    
    # 添加缓存提示
    if Config.CACHE_ENABLED:
        result['cache_hint'] = {
            'ttl': Config.CACHE_TTL,
            'next_update': (target_time + pd.Timedelta(hours=1)).isoformat()
        }
    
    return jsonify(result)

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return make_error_response(
        'NOT_FOUND',
        'The requested endpoint does not exist',
        {'path': request.path},
        404
    )

@app.errorhandler(500)
def internal_error(error):
    return make_error_response(
        'INTERNAL_ERROR',
        'An internal server error occurred',
        {'message': str(error)},
        500
    )

# ==================== 主程序 ====================

if __name__ == '__main__':
    print(f"\n🚀 Starting Flask server on {Config.HOST}:{Config.PORT}")
    print(f"📡 API Base URL: http://localhost:{Config.PORT}/api/v1")
    print(f"🔗 Health Check: http://localhost:{Config.PORT}/api/v1/health\n")
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
```

---

## 数据预处理

### 预处理脚本 (scripts/preprocess.py)

```python
import pandas as pd
import geopandas as gpd
import json
from pathlib import Path

# ==================== 配置 ====================

RAW_DIR = Path('../data/raw')
PROCESSED_DIR = Path('../data/processed')
PROCESSED_DIR.mkdir(exist_ok=True)

# ==================== 1. 加载原始数据 ====================

print("📂 Loading raw data...")

# 客流数据
flow_df = pd.read_csv(RAW_DIR / 'transit_flow.csv')
flow_df['timestamp'] = pd.to_datetime(flow_df['timestamp'])
print(f"✅ Loaded {len(flow_df)} flow records")

# 线路几何数据
routes_gdf = gpd.read_file(RAW_DIR / 'routes.geojson')
print(f"✅ Loaded {len(routes_gdf)} routes")

# 站点数据（可选）
try:
    with open(RAW_DIR / 'stations.json', 'r') as f:
        stations_data = json.load(f)
    print(f"✅ Loaded {len(stations_data['stations'])} stations")
except FileNotFoundError:
    print("⚠️  No stations.json found, skipping...")
    stations_data = None

# ==================== 2. 数据清洗 ====================

print("\n🧹 Cleaning data...")

# 删除缺失值
flow_df = flow_df.dropna(subset=['timestamp', 'route_id', 'passenger_count'])

# 删除异常值
flow_df = flow_df[flow_df['passenger_count'] >= 0]
flow_df = flow_df[flow_df['passenger_count'] <= 20000]

# 标准化类型
flow_df['type'] = flow_df['type'].str.lower()

print(f"✅ Cleaned data: {len(flow_df)} records remaining")

# ==================== 3. 按小时聚合 ====================

print("\n📊 Aggregating by hour and route...")

# 透视方向数据
direction_pivot = flow_df.pivot_table(
    index=['timestamp', 'route_id', 'type'],
    columns='direction',
    values='passenger_count',
    aggfunc='sum',
    fill_value=0
).reset_index()

# 重命名列
if 'inbound' not in direction_pivot.columns:
    direction_pivot['inbound'] = 0
if 'outbound' not in direction_pivot.columns:
    direction_pivot['outbound'] = 0

# 计算总流量
direction_pivot['flow'] = direction_pivot['inbound'] + direction_pivot['outbound']

# 添加容量
capacity_map = {'mrt': 12000, 'lrt': 3500, 'bus': 800}
direction_pivot['capacity'] = direction_pivot['type'].map(capacity_map)

# 计算利用率
direction_pivot['utilization'] = direction_pivot['flow'] / direction_pivot['capacity']

# 添加聚合类型标记
direction_pivot['aggregation'] = 'route'

print(f"✅ Aggregated to {len(direction_pivot)} records")

# ==================== 4. 生成线路 JSON ====================

print("\n🗺️  Generating routes JSON...")

routes_list = []
for idx, row in routes_gdf.iterrows():
    route = {
        'route_id': row['route_id'],
        'route_name': row['route_name'],
        'route_code': row['route_code'],
        'type': row['type'].lower(),
        'capacity': capacity_map[row['type'].lower()],
        'color': row.get('color', '#000000'),
        'geometry': json.loads(row['geometry'].to_json()),
        'operational': row.get('operational', True),
        'operator': row.get('operator', 'Unknown')
    }
    
    # 添加站点（如果有）
    if stations_data:
        route_stations = [
            s for s in stations_data['stations']
            if row['route_id'] in s.get('routes', [])
        ]
        route['stations'] = [
            {
                'id': s['id'],
                'name': s['name'],
                'position': s['position']
            }
            for s in route_stations
        ]
    else:
        route['stations'] = None
    
    routes_list.append(route)

routes_json = {
    'routes': routes_list,
    'total_count': len(routes_list),
    'filters_applied': {'types': ['mrt', 'lrt', 'bus']}
}

print(f"✅ Generated {len(routes_list)} routes")

# ==================== 5. 生成元数据 ====================

print("\n📋 Generating metadata...")

metadata = {
    'version': '1.0',
    'dataset': {
        'name': 'Singapore Public Transit Flow',
        'description': 'Hourly average passenger flow data',
        'source': 'LTA DataMall / Custom Collection',
        'last_updated': pd.Timestamp.now().isoformat()
    },
    'temporal_range': {
        'start_date': direction_pivot['timestamp'].min().isoformat(),
        'end_date': direction_pivot['timestamp'].max().isoformat(),
        'granularity': 'hourly',
        'total_hours': int((direction_pivot['timestamp'].max() - direction_pivot['timestamp'].min()).total_seconds() / 3600)
    },
    'transit_types': [
        {
            'id': 'mrt',
            'name': 'Mass Rapid Transit',
            'name_zh': '地铁',
            'max_capacity': 12000,
            'color_scheme': 'blues',
            'total_routes': len([r for r in routes_list if r['type'] == 'mrt'])
        },
        {
            'id': 'lrt',
            'name': 'Light Rail Transit',
            'name_zh': '轻轨',
            'max_capacity': 3500,
            'color_scheme': 'greens',
            'total_routes': len([r for r in routes_list if r['type'] == 'lrt'])
        },
        {
            'id': 'bus',
            'name': 'Public Bus',
            'name_zh': '公交',
            'max_capacity': 800,
            'color_scheme': 'oranges',
            'total_routes': len([r for r in routes_list if r['type'] == 'bus'])
        }
    ],
    'map_config': {
        'center': [1.3521, 103.8198],
        'zoom_default': 12,
        'zoom_min': 10,
        'zoom_max': 16,
        'bounds': [[1.1, 103.6], [1.5, 104.1]]
    }
}

print("✅ Generated metadata")

# ==================== 6. 保存处理后的数据 ====================

print("\n💾 Saving processed data...")

# 保存客流数据（Parquet 格式，高效）
flow_output = PROCESSED_DIR / 'flow_aggregated.parquet'
direction_pivot.to_parquet(flow_output, index=False, engine='pyarrow')
print(f"✅ Saved flow data to {flow_output}")

# 保存线路数据
routes_output = PROCESSED_DIR / 'routes.json'
with open(routes_output, 'w', encoding='utf-8') as f:
    json.dump(routes_json, f, indent=2, ensure_ascii=False)
print(f"✅ Saved routes to {routes_output}")

# 保存元数据
metadata_output = PROCESSED_DIR / 'metadata.json'
with open(metadata_output, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"✅ Saved metadata to {metadata_output}")

# ==================== 7. 数据质量报告 ====================

print("\n📊 Data Quality Report:")
print(f"  Total flow records: {len(direction_pivot)}")
print(f"  Total routes: {len(routes_list)}")
print(f"  Time range: {metadata['temporal_range']['start_date']} to {metadata['temporal_range']['end_date']}")
print(f"  Transit types: {', '.join([t['id'] for t in metadata['transit_types']])}")
print(f"\n✅ Preprocessing completed successfully!")
```

---

## 测试与调试

### 测试脚本 (tests/test_api.py)

```python
import requests
import json

BASE_URL = 'http://localhost:5000/api/v1'

def test_health():
    """测试健康检查"""
    response = requests.get(f'{BASE_URL}/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    print("✅ Health check passed")

def test_metadata():
    """测试元数据接口"""
    response = requests.get(f'{BASE_URL}/metadata')
    assert response.status_code == 200
    data = response.json()
    assert 'version' in data
    assert 'temporal_range' in data
    print("✅ Metadata test passed")

def test_routes():
    """测试线路接口"""
    # 不带参数
    response = requests.get(f'{BASE_URL}/routes')
    assert response.status_code == 200
    data = response.json()
    assert 'routes' in data
    assert len(data['routes']) > 0
    
    # 带类型过滤
    response = requests.get(f'{BASE_URL}/routes?types=mrt')
    assert response.status_code == 200
    data = response.json()
    assert all(r['type'] == 'mrt' for r in data['routes'])
    
    print("✅ Routes test passed")

def test_passenger_flow():
    """测试客流接口"""
    # 正常请求
    response = requests.get(
        f'{BASE_URL}/passenger-flow',
        params={'datetime': '2024-01-01T08:00:00', 'types': 'mrt,lrt'}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
    assert len(data['data']) > 0
    
    # 缺少参数
    response = requests.get(f'{BASE_URL}/passenger-flow')
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'MISSING_PARAM'
    
    # 无效时间格式
    response = requests.get(
        f'{BASE_URL}/passenger-flow',
        params={'datetime': 'invalid-date'}
    )
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'INVALID_DATETIME'
    
    print("✅ Passenger flow test passed")

if __name__ == '__main__':
    print("🧪 Running API tests...\n")
    test_health()
    test_metadata()
    test_routes()
    test_passenger_flow()
    print("\n✅ All tests passed!")
```

运行测试：

```bash
# 确保后端已启动
python app.py &

# 运行测试
python tests/test_api.py
```

---

## 部署说明

### 开发环境

```bash
# 启动后端
cd backend
source venv/bin/activate
python app.py
```

### 生产环境（使用 Gunicorn）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动（4 个 worker）
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 后台运行
nohup gunicorn -w 4 -b 0.0.0.0:5000 app:app > gunicorn.log 2>&1 &
```

### 使用 systemd（推荐）

创建 `/etc/systemd/system/transit-api.service`:

```ini
[Unit]
Description=Singapore Transit API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable transit-api
sudo systemctl start transit-api
sudo systemctl status transit-api
```

---

## 性能优化建议

### 1. 数据预加载
- ✅ 已实现：启动时加载所有数据到内存
- 优点：查询速度快（< 50ms）
- 缺点：内存占用大（约 100-500MB）

### 2. 使用 Parquet 格式
- ✅ 已实现：客流数据使用 Parquet
- 优点：加载速度快 3-5 倍，压缩率高
- 缺点：需要 pyarrow 依赖

### 3. 添加缓存（可选）
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def query_flow_data(timestamp, types_tuple):
    """缓存查询结果"""
    types = list(types_tuple)
    return flow_df[(flow_df['timestamp'] == timestamp) & (flow_df['type'].isin(types))]
```

### 4. 使用索引
```python
# 在加载数据时设置索引
flow_df = flow_df.set_index(['timestamp', 'route_id']).sort_index()

# 快速查询
result = flow_df.loc[(target_time, route_id)]
```

---

## 常见问题

### Q1: 如何生成模拟数据？
```python
import numpy as np

dates = pd.date_range('2024-01-01', '2024-12-31', freq='H')
routes = ['NS_LINE', 'EW_LINE', 'BUS_14']
types = ['mrt', 'mrt', 'bus']

data = []
for dt in dates:
    for route, type_ in zip(routes, types):
        base = {'mrt': 5000, 'lrt': 1500, 'bus': 300}[type_]
        flow = int(base * (1 + 0.5 * np.sin((dt.hour - 8) * np.pi / 12)))
        data.append({
            'timestamp': dt,
            'route_id': route,
            'type': type_,
            'passenger_count': max(0, flow + np.random.randint(-500, 500))
        })

mock_df = pd.DataFrame(data)
mock_df.to_csv('data/raw/transit_flow.csv', index=False)
```

### Q2: CORS 错误如何解决？
确保 `Flask-CORS` 已正确配置：
```python
CORS(app, origins=['http://localhost:8000'])
```

### Q3: 如何添加日志？
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.route('/api/v1/routes')
def get_routes():
    logger.info(f"Routes requested with params: {request.args}")
    # ...
```

---

**完成后**: 请阅读 `TESTING_DEBUG.md` 进行全面测试。
