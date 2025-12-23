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
│   ├── raw/            # 原始数据
│   │   └── <timestamp>-<config_name>-<hash>/
│   │          ├── meta.json # 元数据 
│   │          └── ...
│   │
│   └── preprocessed/   # 转换为`*.js`的数据
│       └── <timestamp>-<config_name>-<hash>/
│              ├── meta.json # 元数据 
│              └── ...[.]js
│
├── configs/ 
│   └── ingest/                 # CLI 根据 name 自动查找 config               
│       └── <config_name>.json                
│
├── backend/
│   │
│   └── ingest/                        # 离线采集 + 产物生成（唯一系统）
│       ├── README.md                  # 后端用法：如何抓取/构建数据产物
│       ├── __init__.py
│       │
│       ├── wiring.py                   # 声明全局注册表
│       │
│       ├── cli/
│       │   ├── configs.py              # 解析配置  
│       │   ├── bootstrap.py            # 自检和初始化
│       │   ├── runtime.py              # 定义状态机和 RuntimeEnvironment，仅管理资源，不执行任务
│       │   ├── tasks/                  # ingest <command> [options] <config_names...> 可执行的指令
│       │   │   ├── interface.py        # 算子接口，通过继承定义新的算子, 
                                        # 每个 task 需要统一携带的：产物列表、meta、错误信息、diagnostics
│       │   │   ├── run.py              # 运行一个配置
│       │   │   └── ...                 # 运行一个配置                              
│       │   └── main.py                 # CLI 入口：ingest ...，解析参数
│       │
│       ├── sources/
│       │   ├── interface.py            # 算子接口，通过继承定义新的算子       
│       │   ├── data_gov_sg.py          # HTTP 获取：data.gov.sg         
│       │   └── datamall.py             # HTTP 获取：datamall
│       │
│       ├── cache/
│       │   ├── interface.py              # 统一向外暴露    
│       │   ├── raw.py                    # 缓存网络 IO 获取的数据       
│       │   └── preprocessed.py           # 缓存成品数据
│       │
│       ├── transform/
│       │   ├── interface.py                # 算子接口，通过继承定义新的算子
│       │   ├── transformer.py              # 管理 raw -> IR (Python builtin) -> preprocessed
│       │   ├── front/                      # operators for raw -> IR
│       │   │   ├── json_payload.py         # 解析被理解为 JSON 的 bytes               
│       │   │   └── ... 
│       │   ├── optimizer/                  # operators for cleaning
│       │   │   ├── plain_optimizer.py      # 什么都不做，单纯传递 IR 的优化器               
│       │   │   └── ...       
│       │   └── output/                     # operators for IR -> preprocessed
│       │       ├── js_constants.py         # 输出为 js 常量的编译后端
│       │       └── ... 
│       │   
│       └──  utils/
│           ├── registry.py             # 注册表
│           └── logger.py               # 日志，使用 logging       
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

---

ingest 为了不烂，对于使用基类统一接口的部分，两条硬约束：

A1) 继承只做“接口”，不做“框架”

基类只定义抽象方法 + 最小共享工具

禁止在基类里写复杂控制流（否则未来 debug 会痛）

A2) 注册表只负责“名字→类”，不负责“对象生命周期”

registry 存的是 {"datamall": DataMallSource, ...}

pipeline 在运行时用 config 实例化对象

不要在 registry 里塞已经构造好的单例（否则 state 泄漏）

为了保持模块边界清晰，cli/pipeline.py 只能做三件事：

load config（通过 utils/configs.py）

从 registry 取类并实例化

调用统一接口串起来（source→cache→transform→cache）

禁止它直接处理数据内容（不 parse、不 transform 具体字段）。

如有配置需求使用 dataclass 独立出来，后续由 utils.configs.py 统一处理解耦
