# AI 协作指南
# AI Collaboration Guide v1.0

> **目标读者**: 参与本项目的所有 AI 助手  
> **作用**: 确保多 AI 协作时的一致性和效率

---

## 协作原则

### 1. 文档先行
- 所有 AI 必须先阅读相关文档，再开始编码
- API 定义是契约，不可擅自更改
- 数据结构必须严格遵守规范

### 2. 职责清晰
- 后端 AI 专注于数据处理和 API 实现
- 前端 AI 专注于可视化和交互
- 不跨界干预对方的实现细节

### 3. 沟通透明
- 遇到问题立即通知相关方
- API 变更必须更新文档
- 重要决策需要讨论确认

---

## 后端开发 AI 指令

### 角色定位
你是一个专业的 Python/Flask 后端开发者。你的任务是实现符合 API 规范的后端服务。

### 必读文档
1. `API_SPECIFICATION.md` (完整阅读，这是核心契约)
2. `DATA_STRUCTURE.md` (了解数据格式要求)
3. `BACKEND_GUIDE.md` (学习实现细节)

### 关键要求

#### 数据格式
- 所有响应必须是 JSON 格式
- 时间格式必须是 ISO 8601: `YYYY-MM-DDTHH:mm:ss`
- GeoJSON 坐标顺序是 `[经度, 纬度]`
- 错误响应必须包含统一的 `error` 对象

#### 性能要求
- `/passenger-flow` 响应时间 < 500ms
- `/metadata` 和 `/routes` 响应时间 < 200ms
- 启动时预加载所有数据到内存

#### 代码规范
```python
# 好的例子
@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    datetime_str = request.args.get('datetime')
    if not datetime_str:
        return make_error_response(
            'MISSING_PARAM',
            "Required parameter 'datetime' is missing",
            {'required_params': ['datetime']}
        ), 400
    # ...
```

```python
# 避免的例子
@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    # ❌ 没有参数验证
    datetime_str = request.args['datetime']
    # ❌ 没有错误处理
    # ❌ 直接崩溃
```

### 检查清单
在提交代码前，请确认：
- [ ] 所有 API 端点已实现
- [ ] 响应格式完全符合 `API_SPECIFICATION.md`
- [ ] 错误处理完善
- [ ] CORS 已配置
- [ ] 数据已预加载
- [ ] 通过所有 curl 测试

---

## 前端开发 AI 指令

### 角色定位
你是一个专业的 JavaScript/D3.js 前端开发者。你的任务是创建交互式地图可视化应用。

### 必读文档
1. `API_SPECIFICATION.md` (了解后端提供的数据)
2. `DATA_STRUCTURE.md` (了解数据格式，特别是坐标转换)
3. `FRONTEND_GUIDE.md` (学习实现细节)

### 关键要求

#### 技术栈
- **必须使用**: Vanilla JavaScript + D3.js + Leaflet.js
- **禁止使用**: Vue, React, Angular 等框架
- **原因**: 用户已熟悉 D3.js，学习成本最低

#### 坐标转换
```javascript
// ⚠️ 非常重要！GeoJSON 和 Leaflet 坐标顺序不同

// GeoJSON (后端返回): [经度, 纬度]
const geoJsonCoords = [103.8198, 1.3521];

// Leaflet (地图渲染): [纬度, 经度]
const leafletCoords = [geoJsonCoords[1], geoJsonCoords[0]];
```

#### 颜色映射
```javascript
// 必须使用预定义的颜色方案
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
```

#### Mock 数据开发
```javascript
// config.js
const CONFIG = {
  USE_MOCK_DATA: true,  // 开发时设为 true
  // ...
};

// api.js
async fetchPassengerFlow(datetime, types) {
  if (this.useMock) {
    return MOCK_DATA.passengerFlow;  // 返回 mock 数据
  }
  // 正常 fetch 逻辑
}
```

### 检查清单
在提交代码前，请确认：
- [ ] 地图正确加载新加坡区域
- [ ] 线路渲染正确（注意坐标转换）
- [ ] 时间轴可拖动和播放
- [ ] 图层控制正常工作
- [ ] 颜色映射符合规范
- [ ] Mock 数据模式可用
- [ ] 浏览器控制台无错误

---

## 协作场景示例

### 场景 1: 后端 AI 完成 API，前端 AI 开始集成

**后端 AI 交付**:
```
✅ 所有 API 端点已实现
✅ 测试脚本已通过
✅ 服务运行在 http://localhost:5000

请前端 AI 测试以下端点:
- GET /api/v1/health
- GET /api/v1/metadata  
- GET /api/v1/routes
- GET /api/v1/passenger-flow?datetime=2024-01-01T08:00:00
```

**前端 AI 响应**:
```
收到。我将:
1. 测试所有端点
2. 验证响应格式
3. 集成到前端代码
4. 如有问题会立即反馈
```

---

### 场景 2: 前端 AI 发现 API 问题

**前端 AI 反馈**:
```
❌ 发现问题: /api/v1/routes 返回的 geometry.coordinates 
   坐标顺序似乎是 [纬度, 经度]，但 API 文档规定应该是 [经度, 纬度]

测试结果:
{
  "geometry": {
    "coordinates": [[1.3330, 103.7423]]  // 错误：应该是 [103.7423, 1.3330]
  }
}

请后端 AI 确认并修复。
```

**后端 AI 响应**:
```
确认问题。正在修复...

✅ 已修复，坐标顺序已改为 [经度, 纬度]
✅ 已更新测试用例
✅ 请重新测试
```

---

### 场景 3: 需要协商 API 变更

**前端 AI 提议**:
```
建议: 在 /passenger-flow 响应中添加 peak_hour 字段，
用于在 UI 中高亮显示高峰时段。

提议新增字段:
{
  "data": [...],
  "peak_hour": "08:00:00"  // 新增
}

理由: 提升用户体验，无需前端额外计算。
```

**后端 AI 响应**:
```
同意添加此字段。
预计实现时间: 30 分钟
更新后会通知并更新 API_SPECIFICATION.md
```

---

## 常见问题处理

### Q1: 发现文档与实现不一致怎么办？

**步骤**:
1. 停止当前工作
2. 在协作平台提出问题
3. 引用具体的文档和代码
4. 等待讨论确认
5. 更新文档或代码

**示例**:
```
问题: API_SPECIFICATION.md 第 123 行定义 flow 字段为 number，
但实际返回的是 string "8543"

建议: 统一为 number 类型

请确认。
```

---

### Q2: 不确定某个设计决策怎么办？

**步骤**:
1. 检查文档是否有说明
2. 如果没有，提出问题并说明考虑因素
3. 提供 2-3 个备选方案
4. 等待确认后再实施

**示例**:
```
问题: 客流量为 0 时线路应该如何显示？

选项：
A. 使用最浅的颜色
B. 使用灰色
C. 完全隐藏线路

我倾向于选项 A，因为...

请确认。
```

---

### Q3: 遇到性能瓶颈怎么办？

**步骤**:
1. 用数据量化问题（如响应时间、内存占用）
2. 分析瓶颈原因
3. 提出优化方案
4. 如果需要修改架构，先讨论

**示例**:
```
性能问题: /passenger-flow 响应时间 1.2s，超出 500ms 目标

分析: 
- 数据查询耗时 800ms
- Pandas groupby 操作慢

优化方案:
1. 建立时间索引 (预计提升 50%)
2. 使用 Parquet 替代 CSV (预计提升 30%)

请确认是否可以实施。
```

---

## 代码审查标准

### 后端代码审查

**必须检查**:
- [ ] 响应格式符合 API 规范
- [ ] 错误处理完善
- [ ] CORS 配置正确
- [ ] 无硬编码路径
- [ ] 日志输出适当
- [ ] 性能满足要求

**好的例子**:
```python
@app.route('/api/v1/passenger-flow')
def get_passenger_flow():
    try:
        datetime_str = request.args.get('datetime')
        if not datetime_str:
            return make_error_response('MISSING_PARAM', ...), 400
        
        target_time = validate_datetime(datetime_str)
        if not target_time:
            return make_error_response('INVALID_DATETIME', ...), 400
        
        # 查询数据...
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in passenger_flow: {e}")
        return make_error_response('INTERNAL_ERROR', str(e)), 500
```

---

### 前端代码审查

**必须检查**:
- [ ] 坐标转换正确
- [ ] API 错误处理
- [ ] 颜色映射符合规范
- [ ] 无内存泄漏
- [ ] 浏览器控制台无错误
- [ ] 代码模块化

**好的例子**:
```javascript
class TransitMap {
  loadRoutes(routesData, colorScales) {
    routesData.routes.forEach(route => {
      // ✅ 正确的坐标转换
      const coords = route.geometry.coordinates.map(
        coord => [coord[1], coord[0]]  // GeoJSON -> Leaflet
      );
      
      // ✅ 错误处理
      if (!coords.length) {
        console.warn(`Route ${route.route_id} has no coordinates`);
        return;
      }
      
      // 渲染...
    });
  }
}
```

---

## 最佳实践

### 1. 小步提交
- 每完成一个功能模块就提交
- 附上简短说明
- 方便回滚和调试

### 2. 测试驱动
- 写代码前先写测试用例
- 确保通过所有测试
- 添加新功能时更新测试

### 3. 文档同步
- 代码和文档同步更新
- 变更必须记录在文档中
- 版本号递增

### 4. 主动沟通
- 遇到阻塞立即提出
- 完成里程碑主动通知
- 定期同步进度

---

## 结语

多 AI 协作的关键是：
1. **统一认知**：所有 AI 都基于相同的文档工作
2. **职责清晰**：各司其职，不越界
3. **及时沟通**：问题不过夜
4. **质量优先**：宁可慢一点，不要返工

记住：**API 文档是法律，数据结构是宪法。**

祝协作顺利！🚀
