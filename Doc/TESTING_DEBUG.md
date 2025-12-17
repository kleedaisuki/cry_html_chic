# 测试与调试指南
# Testing & Debugging Guide v1.0

> **目标读者**: 全体开发者  
> **前置阅读**: `BACKEND_GUIDE.md` 或 `FRONTEND_GUIDE.md`

---

## 后端测试

### API 端点测试

#### 1. 健康检查
```bash
curl http://localhost:5000/api/v1/health
```
**期望响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-17T10:30:45",
  "version": "1.0.0",
  "data_loaded": true,
  "total_routes": 359
}
```

#### 2. 系统元数据
```bash
curl http://localhost:5000/api/v1/metadata
```
**检查**:
- `temporal_range` 包含 start_date 和 end_date
- `transit_types` 数组有 3 个元素
- `map_config` 包含 center 坐标

#### 3. 线路数据（所有类型）
```bash
curl http://localhost:5000/api/v1/routes
```
**检查**:
- `routes` 数组非空
- 每个 route 包含 `route_id`, `geometry`
- `geometry.type` 为 "LineString"

#### 4. 线路数据（仅 MRT）
```bash
curl "http://localhost:5000/api/v1/routes?types=mrt"
```
**检查**:
- 所有返回的 route 的 `type` 字段为 "mrt"
- `filters_applied.types` 为 ["mrt"]

#### 5. 客流数据（正常）
```bash
curl "http://localhost:5000/api/v1/passenger-flow?datetime=2024-01-01T08:00:00&types=mrt,lrt"
```
**检查**:
- `data` 数组非空
- 每个 item 包含 `route_id`, `flow`, `utilization`
- `timestamp` 与请求一致

#### 6. 客流数据（缺少参数）
```bash
curl "http://localhost:5000/api/v1/passenger-flow"
```
**期望响应**: HTTP 400
```json
{
  "error": {
    "code": "MISSING_PARAM",
    "message": "Required parameter 'datetime' is missing"
  }
}
```

#### 7. 客流数据（无效时间格式）
```bash
curl "http://localhost:5000/api/v1/passenger-flow?datetime=invalid-date"
```
**期望响应**: HTTP 400
```json
{
  "error": {
    "code": "INVALID_DATETIME",
    "message": "Invalid datetime format..."
  }
}
```

### 性能测试

#### 响应时间测试
```bash
# 使用 curl 的 -w 参数测量时间
for i in {1..10}; do
  curl -w "\nTime: %{time_total}s\n" -o /dev/null -s \
    "http://localhost:5000/api/v1/passenger-flow?datetime=2024-01-01T08:00:00&types=mrt"
done
```
**指标**: 所有请求应 < 500ms

#### 并发测试
```bash
# 使用 Apache Bench (需安装 ab)
ab -n 100 -c 10 "http://localhost:5000/api/v1/routes"
```
**指标**: 
- 成功率 100%
- 平均响应时间 < 200ms

---

## 前端测试

### 功能测试清单

#### 地图模块
- [ ] 地图正确加载新加坡区域
- [ ] 可以缩放和平移
- [ ] 线路在地图上可见
- [ ] 点击线路显示弹窗
- [ ] 弹窗显示正确的线路信息

#### 时间轴模块
- [ ] 时间轴正确显示时间范围
- [ ] 滑块可拖动
- [ ] 拖动滑块时时间显示更新
- [ ] 点击播放按钮开始自动播放
- [ ] 自动播放时线路颜色变化
- [ ] 点击暂停按钮停止播放
- [ ] 点击重置按钮回到起始时间

#### 图层控制模块
- [ ] 所有图层默认可见
- [ ] 取消勾选 MRT 后地铁线路消失
- [ ] 取消勾选 LRT 后轻轨线路消失
- [ ] 取消勾选 Bus 后公交线路消失
- [ ] 重新勾选后线路重新显示

#### 图例模块
- [ ] 图例显示三种交通类型
- [ ] 渐变色条正确显示
- [ ] 最小值和最大值标注正确
- [ ] 切换图层时图例同步更新

#### API 集成
- [ ] 启动时加载元数据成功
- [ ] 启动时加载线路数据成功
- [ ] 时间变化时请求客流数据成功
- [ ] 网络错误时显示友好提示

### 浏览器兼容性测试

| 浏览器 | 版本 | 地图 | 时间轴 | 图层控制 | 状态 |
|--------|------|------|--------|----------|------|
| Chrome | 最新 | ✅ | ✅ | ✅ | 通过 |
| Firefox | 最新 | ✅ | ✅ | ✅ | 通过 |
| Safari | 最新 | ✅ | ✅ | ✅ | 通过 |
| Edge | 最新 | ✅ | ✅ | ✅ | 通过 |

### 性能测试

#### 帧率测试
```javascript
// 在浏览器控制台运行
let frameCount = 0;
let lastTime = performance.now();

function measureFPS() {
  frameCount++;
  const currentTime = performance.now();
  if (currentTime >= lastTime + 1000) {
    console.log(`FPS: ${frameCount}`);
    frameCount = 0;
    lastTime = currentTime;
  }
  requestAnimationFrame(measureFPS);
}

measureFPS();
```
**指标**: 时间轴播放时 FPS > 30

#### 内存使用
1. 打开 Chrome DevTools → Performance Monitor
2. 观察 JS Heap Size
3. 播放时间轴完整一轮

**指标**: 内存占用 < 200MB

#### API 响应时间
在浏览器 Network 标签中查看 `/passenger-flow` 请求：
- **指标**: 响应时间 < 500ms

---

## 常见问题排查

### 问题 1: CORS 错误

**症状**:
```
Access to fetch at 'http://localhost:5000/api/v1/routes' from origin 'http://localhost:8000' 
has been blocked by CORS policy
```

**排查步骤**:
1. 检查后端是否安装 Flask-CORS
```bash
pip list | grep Flask-CORS
```

2. 检查 CORS 配置
```python
# app.py
from flask_cors import CORS
CORS(app, origins=['http://localhost:8000'])
```

3. 验证响应头
```bash
curl -I http://localhost:5000/api/v1/health
# 应该看到: Access-Control-Allow-Origin: *
```

**解决方案**:
```python
# app.py
from flask_cors import CORS
CORS(app)  # 允许所有来源（开发环境）
```

---

### 问题 2: 地图上看不到线路

**症状**: 地图加载正常，但线路不显示

**排查步骤**:
1. 检查 API 是否返回数据
```javascript
// 浏览器控制台
const response = await fetch('http://localhost:5000/api/v1/routes');
const data = await response.json();
console.log(data.routes.length);  // 应该 > 0
```

2. 检查坐标顺序
```javascript
// 确认 GeoJSON 坐标格式
const route = data.routes[0];
console.log(route.geometry.coordinates[0]);  // 应该是 [lng, lat]
```

3. 检查坐标范围
```javascript
// 新加坡范围: lng [103.6, 104.1], lat [1.1, 1.5]
const coord = route.geometry.coordinates[0];
console.log('Lng:', coord[0], 'Lat:', coord[1]);
```

4. 检查线路颜色
```javascript
// 确认颜色不是白色或透明
console.log(route.color);  // 应该是有效的 HEX 颜色
```

**解决方案**:
```javascript
// map.js - 确保坐标转换正确
const coords = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
//                                                      ^^^^^^  ^^^^^^
//                                                       lat     lng
```

---

### 问题 3: 时间轴拖动卡顿

**症状**: 拖动时间轴滑块时地图更新延迟

**排查步骤**:
1. 检查 Network 面板
   - 是否每次拖动都发送请求？
   - 响应时间是否过长？

2. 检查是否实现节流
```javascript
// timeline.js - 应该使用 debounce 或 throttle
slider.on('input', _.throttle((event) => {
  this.setTime(...);
}, 200));  // 200ms 节流
```

**解决方案**:
```javascript
// 实现简单的节流
let throttleTimer = null;
slider.on('input', (event) => {
  if (throttleTimer) return;
  throttleTimer = setTimeout(() => {
    this.setTime(...);
    throttleTimer = null;
  }, 200);
});
```

---

### 问题 4: 颜色映射不合理

**症状**: 所有线路颜色都很浅或都很深

**排查步骤**:
1. 检查客流数据范围
```javascript
// 控制台
const flowValues = flowData.data.map(d => d.flow);
console.log('Min:', Math.min(...flowValues));
console.log('Max:', Math.max(...flowValues));
```

2. 检查颜色域配置
```javascript
// config.js
console.log(CONFIG.COLORS.mrt.domain);  // [0, 12000]
```

3. 对比实际数据与配置域
```
实际数据: [100, 500, 800]
配置域: [0, 12000]
→ 所有值都在域的前 7%，颜色会很浅
```

**解决方案**:
```javascript
// colorScale.js - 使用动态域
const flowValues = data.map(d => d.flow).sort((a, b) => a - b);
const dynamicDomain = [
  d3.quantile(flowValues, 0.1),  // 10% 分位数
  d3.quantile(flowValues, 0.9)   // 90% 分位数
];

this.scales[type].domain(dynamicDomain);
```

---

### 问题 5: 数据不更新

**症状**: 时间轴播放时线路颜色不变

**排查步骤**:
1. 检查 API 请求是否发送
```javascript
// 在 api.js 中添加日志
async fetchPassengerFlow(datetime, types) {
  console.log('Fetching flow for', datetime);
  // ...
}
```

2. 检查回调函数是否绑定
```javascript
// main.js
console.log('Timeline onChange:', this.timeline.onChange);
// 应该是一个函数，不是 null
```

3. 检查地图更新逻辑
```javascript
// map.js - updateFlow 方法
updateFlow(flowData) {
  console.log('Updating', flowData.data.length, 'routes');
  // ...
}
```

**解决方案**:
```javascript
// main.js - 确保绑定回调
this.timeline.onChange = async (datetime) => {
  console.log('Time changed to', datetime);
  await this.updatePassengerFlow(datetime);
};
```

---

## 调试工具

### Chrome DevTools

#### Network 标签
- 查看所有 API 请求
- 检查响应状态码
- 查看响应时间
- 检查响应内容

#### Console 标签
- 查看错误信息
- 测试 JavaScript 代码
- 查看日志输出

#### Performance 标签
- 录制性能分析
- 查看帧率
- 识别性能瓶颈

#### Memory 标签
- 堆快照
- 查找内存泄漏
- 监控内存使用

### Python 调试

#### 使用 print 调试
```python
@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    print(f"Received request: {request.args}")
    # ...
    print(f"Returning {len(data_records)} records")
    return jsonify(result)
```

#### 使用 pdb 调试器
```python
import pdb

@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    pdb.set_trace()  # 断点
    datetime_str = request.args.get('datetime')
    # ...
```

#### 使用日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    app.logger.info(f"Received request: {request.args}")
    # ...
```

---

## 边界情况测试

### 后端边界情况

#### 1. 空数据
```bash
# 请求不存在的时间点
curl "http://localhost:5000/api/v1/passenger-flow?datetime=2025-12-31T23:00:00"
```
**期望**: HTTP 404, 错误码 `NO_DATA`

#### 2. 无效交通类型
```bash
curl "http://localhost:5000/api/v1/routes?types=invalid"
```
**期望**: HTTP 400, 错误码 `INVALID_TYPE`

#### 3. 极端客流量
测试 `utilization > 1` 的情况（超载）

### 前端边界情况

#### 1. 快速拖动时间轴
- 连续快速拖动
- 应该节流，不会发送过多请求

#### 2. 网络断开
```javascript
// 在 DevTools Console 模拟
window.fetch = () => Promise.reject(new Error('Network error'));
```
**期望**: 显示友好错误提示

#### 3. 所有图层关闭
- 取消所有图层的勾选
- 地图应该为空，但不报错

---

## 性能优化检查清单

### 后端优化
- [ ] 数据已预加载到内存
- [ ] 使用 Parquet 格式存储数据
- [ ] 时间索引已建立
- [ ] 避免重复计算
- [ ] 使用 Gunicorn 多 worker

### 前端优化
- [ ] API 响应已缓存
- [ ] 时间轴拖动已节流
- [ ] 使用 requestAnimationFrame
- [ ] 图层渲染使用 Canvas（如果线路很多）
- [ ] 图片和资源已压缩

---

## 自动化测试（可选）

### 后端单元测试
```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_health(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_passenger_flow_missing_param(client):
    response = client.get('/api/v1/passenger-flow')
    assert response.status_code == 400
    data = response.get_json()
    assert data['error']['code'] == 'MISSING_PARAM'
```

运行测试:
```bash
pytest tests/test_api.py -v
```

---

**完成测试后**: 请阅读 `AI_COLLABORATION.md` 了解 AI 协作最佳实践。
