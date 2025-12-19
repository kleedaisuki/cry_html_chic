# 新加坡公共交通时空可视化系统

**项目代号**: `SG-TRANSIT-VIS`  
**文档版本**: v2.0 (后端JS常量交付版)  
**创建日期**: 2025-12-17  
**架构模式**: 前后端分离的JS常量边界

---

## 概述

本项目旨在构建一个交互式地理时空数据可视化系统，展示新加坡公共交通系统的实时客流量变化。

### 核心功能

- **时间轴动态展示**：通过可交互的时间轴控制器展示客流量变化
- **多模式交通支持**：独立管理地铁（MRT）、轻轨（LRT）、公交（Bus）
- **差异化可视化**：根据不同交通工具承载能力，采用独立的颜色映射标准
- **图层控制系统**：允许用户独立切换或组合展示不同交通模式

### 技术栈

**后端**
Python 3.11.0

**前端**

- Vanilla JavaScript (无框架)
- Leaflet.js (地图渲染)
- D3.js (数据可视化 + 时间轴)
- Day.js (时间处理)

---

## 颜色方案

为确保前端视觉一致性，预定义以下颜色方案：

| 交通类型 | D3 插值器 | 域范围 | 说明 |
|---------|----------|--------|------|
| MRT | `d3.interpolateBlues` | [0, 12000] | 浅蓝→深蓝 |
| LRT | `d3.interpolateGreens` | [0, 3500] | 浅绿→深绿 |
| Bus | `d3.interpolateOranges` | [0, 800] | 浅橙→深橙 |

---

## 项目目录结构

```
cry_html_chic/
│
├── README.md
│
├── pyproject.toml
│
├── docs/                        # 文档目录
│   └── AGENT.md                 # 推荐的提示词（修改自 Cursor CLI）
│
├── scripts/
│   ├── install-pyproject.sh
│   └── install-pyproject.ps1
│
├── data/ 
│   │
│   ├── README.md       # 数据清单
│   │
│   ├── raw/            # 原始数据集
│   │   └── ...
│   │
│   └── preprocessed/   # 转换为`*.js`的数据
│       └── ...
│
├── backend/            # 后端代码（Python）
│   └── ...
│
└── frontend/           # 前端代码
    ├── index.html      # 直接由此启动
    ├── css/
    │   └── style.css
    ├── src/
    │   └── ...
    └── ...
```

---

## 参考资源

**官方文档**

- [Leaflet.js](https://leafletjs.com/reference.html)
- [D3.js](https://d3js.org/)
- [Flask](https://flask.palletsprojects.com/)
- [Pandas](https://pandas.pydata.org/docs/)

**数据源**

- [新加坡 LTA DataMall](https://datamall.lta.gov.sg/)
- [OpenStreetMap](https://www.openstreetmap.org/)

---

统一使用 Doxygen 注释（尽可能），branch 和 commit 按照标准模式进行，尽量维护线性历史。  

文件结构的变化反应在这个 `STRUCTURE.md` 中即可。  

前端按照 web 安全模型不访问本地文件，使用 `data/preprocessed` 中的 JS 常量提供的数据。  

Python 后端将各式各样的数据统一到若干 JS 文件中以 JSON 呈现，并在 `data/README.md` 中说明。
