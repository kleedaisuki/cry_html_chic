# 新加坡公共交通时空可视化系统
# Singapore Public Transit Spatiotemporal Visualization System

**项目代号**: `SG-TRANSIT-VIS`  
**文档版本**: v1.0 (Initial Draft)  
**创建日期**: 2024-12-17  
**架构模式**: 前后端分离 REST API

---

## 📋 项目概述

本项目旨在构建一个交互式地理时空数据可视化系统，展示新加坡公共交通系统的实时客流量变化。

### 核心功能
- ✅ **时间轴动态展示**：通过可交互的时间轴控制器展示客流量变化
- ✅ **多模式交通支持**：独立管理地铁（MRT）、轻轨（LRT）、公交（Bus）
- ✅ **差异化可视化**：根据不同交通工具承载能力，采用独立的颜色映射标准
- ✅ **图层控制系统**：允许用户独立切换或组合展示不同交通模式

### 技术栈

**后端**
- Python 3.8+
- Flask (Web 框架)
- Pandas (数据处理)
- GeoPandas (地理空间数据，可选)

**前端**
- Vanilla JavaScript (无框架)
- Leaflet.js (地图渲染)
- D3.js (数据可视化 + 时间轴)
- Day.js (时间处理)

---

## 📁 文档结构

本项目采用模块化文档结构，便于多 AI 并行协作：

```
docs/
├── README.md                    # 本文件 - 项目总览
├── API_SPECIFICATION.md         # API 接口定义（核心文档）
├── DATA_STRUCTURE.md            # 数据结构规范
├── BACKEND_GUIDE.md             # 后端开发指南
├── FRONTEND_GUIDE.md            # 前端开发指南
├── DEVELOPMENT_WORKFLOW.md      # 开发流程与任务分解
├── TESTING_DEBUG.md             # 测试与调试指南
└── AI_COLLABORATION.md          # AI 协作提示词
```

### 文档阅读指南

**后端开发者/AI** 应该阅读：
1. `API_SPECIFICATION.md` (必读)
2. `DATA_STRUCTURE.md` (必读)
3. `BACKEND_GUIDE.md` (必读)
4. `TESTING_DEBUG.md` (参考)

**前端开发者/AI** 应该阅读：
1. `API_SPECIFICATION.md` (必读)
2. `DATA_STRUCTURE.md` (必读)
3. `FRONTEND_GUIDE.md` (必读)
4. `TESTING_DEBUG.md` (参考)

**项目管理者** 应该阅读：
1. `DEVELOPMENT_WORKFLOW.md` (必读)
2. `AI_COLLABORATION.md` (必读)

---

## 🚀 快速开始

### 后端启动
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/preprocess.py
python app.py
```

后端将在 `http://localhost:5000` 启动。

### 前端启动
```bash
cd frontend
python3 -m http.server 8000
```

访问 `http://localhost:8000` 查看应用。

---

## 📊 开发阶段

### Phase 1: 数据准备与后端 API (3-4 天)
- [ ] 数据收集和清洗
- [ ] 数据预处理和聚合
- [ ] Flask 后端开发
- [ ] API 接口测试

### Phase 2: 前端地图与基础渲染 (2-3 天)
- [ ] 项目结构搭建
- [ ] 地图初始化
- [ ] API 集成
- [ ] 静态线路渲染

### Phase 3: 时间轴与交互功能 (2 天)
- [ ] D3 时间轴组件
- [ ] 图层控制器
- [ ] 动态更新逻辑
- [ ] 图例组件

### Phase 4: 优化与调试 (1-2 天)
- [ ] 性能优化
- [ ] UI/UX 改进
- [ ] 错误处理

详细任务清单见 `DEVELOPMENT_WORKFLOW.md`。

---

## 🔗 核心 API 端点

### 基础信息
- **Base URL**: `http://localhost:5000/api/v1`
- **Content-Type**: `application/json`
- **编码**: UTF-8
- **时间格式**: ISO 8601 (`YYYY-MM-DDTHH:mm:ss`)

### 核心接口（Phase 1 必须实现）

| 端点 | 方法 | 用途 | 状态 |
|------|------|------|------|
| `/metadata` | GET | 获取系统元数据 | ✅ 必须 |
| `/routes` | GET | 获取线路信息 | ✅ 必须 |
| `/passenger-flow` | GET | 获取客流数据 | ✅ 必须 |
| `/health` | GET | 健康检查 | ✅ 必须 |

### 可选接口（Phase 2）

| 端点 | 方法 | 用途 | 状态 |
|------|------|------|------|
| `/timeseries` | GET | 时间序列数据 | ⭕ 可选 |

完整 API 文档见 `API_SPECIFICATION.md`。

---

## 🎨 颜色方案

为确保前后端视觉一致性，预定义以下颜色方案：

| 交通类型 | D3 插值器 | 域范围 | 说明 |
|---------|----------|--------|------|
| MRT | `d3.interpolateBlues` | [0, 12000] | 浅蓝→深蓝 |
| LRT | `d3.interpolateGreens` | [0, 3500] | 浅绿→深绿 |
| Bus | `d3.interpolateOranges` | [0, 800] | 浅橙→深橙 |

---

## 🤝 协作模式

### API First 原则
- 接口定义优先，前后端可并行开发
- API 契约一旦确定，除非发现重大缺陷，否则不变更
- 使用 Mock 数据实现前端独立开发

### 版本控制
- 所有 API 变更必须更新 `API_SPECIFICATION.md`
- 变更必须记录在文档的 `变更日志` 部分
- 版本号遵循语义化版本（Semantic Versioning）

### 沟通协议
- 前端遇到 API 问题：在 `API_SPECIFICATION.md` 中提 Issue
- 后端 API 变更：必须通知前端并更新文档
- 数据格式问题：参考 `DATA_STRUCTURE.md` 解决

---

## 📝 项目目录结构

```
transit-visualization/
├── README.md
├── docs/                        # 文档目录
│   ├── API_SPECIFICATION.md
│   ├── DATA_STRUCTURE.md
│   ├── BACKEND_GUIDE.md
│   ├── FRONTEND_GUIDE.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   ├── TESTING_DEBUG.md
│   └── AI_COLLABORATION.md
│
├── backend/                     # 后端代码
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── metadata.py
│   │   ├── routes.py
│   │   └── flow.py
│   ├── data/
│   │   ├── raw/
│   │   └── processed/
│   └── scripts/
│       └── preprocess.py
│
└── frontend/                    # 前端代码
    ├── index.html
    ├── css/
    │   └── style.css
    ├── js/
    │   ├── config.js
    │   ├── api.js
    │   ├── map.js
    │   ├── timeline.js
    │   ├── colorScale.js
    │   ├── legend.js
    │   └── main.js
    └── data/
        └── mockData.js
```

---

## 🐛 常见问题

### CORS 错误
确保后端已配置 Flask-CORS：
```python
from flask_cors import CORS
CORS(app)
```

### 地图线路不显示
检查：
- GeoJSON 坐标顺序是否为 `[经度, 纬度]`
- 线路颜色是否与背景色冲突
- 坐标是否在地图边界内

### 时间轴卡顿
优化方案：
- 实现前端缓存
- 使用 `requestAnimationFrame`
- 预加载下一时间点数据

更多问题见 `TESTING_DEBUG.md`。

---

## 📚 参考资源

**官方文档**
- [Leaflet.js](https://leafletjs.com/reference.html)
- [D3.js](https://d3js.org/)
- [Flask](https://flask.palletsprojects.com/)
- [Pandas](https://pandas.pydata.org/docs/)

**数据源**
- [新加坡 LTA DataMall](https://datamall.lta.gov.sg/)
- [OpenStreetMap](https://www.openstreetmap.org/)

---

## 📄 License

本项目为学术作业项目，仅供教育用途。

---

## 🔄 变更日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2024-12-17 | 初始版本，定义核心 API 和开发流程 |

---

## 👥 贡献者

- 项目发起人：Jingren
- 后端开发：待分配
- 前端开发：待分配

---

**下一步**: 请阅读 `API_SPECIFICATION.md` 开始开发。
