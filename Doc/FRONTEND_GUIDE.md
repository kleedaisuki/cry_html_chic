# 前端开发指南
# Frontend Development Guide v1.0

> **目标读者**: JavaScript/D3.js 前端开发者或 AI  
> **前置阅读**: `API_SPECIFICATION.md`, `DATA_STRUCTURE.md`

---

## 目录
- [技术选型](#技术选型)
- [项目结构](#项目结构)
- [核心模块实现](#核心模块实现)
- [Mock 数据开发](#mock-数据开发)
- [样式与布局](#样式与布局)
- [调试技巧](#调试技巧)

---

## 技术选型

### 核心库

| 库 | 版本 | 用途 | CDN |
|---|------|------|-----|
| Leaflet.js | 1.9.4 | 地图渲染 | `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js` |
| D3.js | 7.8.5 | 数据可视化 + 时间轴 | `https://d3js.org/d3.v7.min.js` |
| Day.js | 1.11.10 | 时间处理 | `https://unpkg.com/dayjs@1.11.10/dayjs.min.js` |

### 为什么不用框架？

- ✅ **学习成本低**: 你已熟悉 D3.js
- ✅ **性能更好**: 直接 DOM 操作，无虚拟 DOM 开销
- ✅ **灵活性高**: D3 数据绑定非常适合地理可视化
- ❌ **开发效率**: 相比 Vue/React 略慢（但在你的技术栈下最快）

---

## 项目结构

```
frontend/
├── index.html              # 主页面
├── css/
│   └── style.css          # 样式文件
├── js/
│   ├── config.js          # 配置常量
│   ├── api.js             # API 封装
│   ├── map.js             # 地图渲染
│   ├── timeline.js        # 时间轴控制
│   ├── colorScale.js      # 颜色映射
│   ├── legend.js          # 图例组件
│   ├── controls.js        # 图层控制器
│   └── main.js            # 主逻辑入口
├── data/
│   └── mockData.js        # Mock 数据（开发阶段）
└── assets/
    └── icons/             # 图标资源
```

---

## 核心模块实现

### 1. 配置文件 (js/config.js)

```javascript
const CONFIG = {
  // API 配置
  API_BASE_URL: 'http://localhost:5000/api/v1',
  USE_MOCK_DATA: false,  // 开发时设为 true
  
  // 地图配置
  MAP: {
    CENTER: [1.3521, 103.8198],  // [纬度, 经度]
    ZOOM: 12,
    MIN_ZOOM: 10,
    MAX_ZOOM: 16,
    TILE_URL: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    ATTRIBUTION: '© OpenStreetMap contributors'
  },
  
  // 颜色方案
  COLORS: {
    mrt: {
      scheme: 'Blues',
      domain: [0, 12000]
    },
    lrt: {
      scheme: 'Greens',
      domain: [0, 3500]
    },
    bus: {
      scheme: 'Oranges',
      domain: [0, 800]
    }
  },
  
  // 动画配置
  ANIMATION: {
    PLAY_INTERVAL: 500,      // 自动播放间隔（毫秒）
    TRANSITION_DURATION: 300  // 过渡动画时长（毫秒）
  },
  
  // 性能配置
  CACHE: {
    ENABLED: true,
    MAX_SIZE: 100  // 最多缓存 100 个时间点
  }
};
```

### 2. API 封装 (js/api.js)

```javascript
class TransitAPI {
  constructor(baseURL, useMock = false) {
    this.baseURL = baseURL;
    this.useMock = useMock;
    this.cache = new Map();
  }
  
  /**
   * 通用请求方法
   */
  async _fetch(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`);
    Object.keys(params).forEach(key => 
      url.searchParams.append(key, params[key])
    );
    
    try {
      const response = await fetch(url);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error.message);
      }
      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }
  
  /**
   * 获取系统元数据
   */
  async fetchMetadata() {
    if (this.useMock) return MOCK_DATA.metadata;
    return this._fetch('/metadata');
  }
  
  /**
   * 获取线路数据
   * @param {string[]} types - 交通类型数组，如 ['mrt', 'lrt']
   */
  async fetchRoutes(types = null) {
    if (this.useMock) return MOCK_DATA.routes;
    
    const params = {};
    if (types) params.types = types.join(',');
    
    return this._fetch('/routes', params);
  }
  
  /**
   * 获取客流数据（带缓存）
   * @param {string} datetime - ISO 8601 格式时间
   * @param {string[]} types - 交通类型数组
   */
  async fetchPassengerFlow(datetime, types = ['mrt', 'lrt', 'bus']) {
    if (this.useMock) return MOCK_DATA.passengerFlow;
    
    // 检查缓存
    const cacheKey = `${datetime}_${types.join(',')}`;
    if (this.cache.has(cacheKey)) {
      console.log(`📦 Cache hit: ${cacheKey}`);
      return this.cache.get(cacheKey);
    }
    
    const params = {
      datetime: datetime,
      types: types.join(',')
    };
    
    const data = await this._fetch('/passenger-flow', params);
    
    // 存入缓存
    if (CONFIG.CACHE.ENABLED) {
      this.cache.set(cacheKey, data);
      
      // 限制缓存大小
      if (this.cache.size > CONFIG.CACHE.MAX_SIZE) {
        const firstKey = this.cache.keys().next().value;
        this.cache.delete(firstKey);
      }
    }
    
    return data;
  }
  
  /**
   * 健康检查
   */
  async checkHealth() {
    return this._fetch('/health');
  }
}
```

### 3. 地图渲染 (js/map.js)

```javascript
class TransitMap {
  constructor(containerId, config) {
    // 初始化地图
    this.map = L.map(containerId, {
      center: config.center,
      zoom: config.zoom,
      minZoom: config.minZoom,
      maxZoom: config.maxZoom
    });
    
    // 添加底图
    L.tileLayer(config.tileUrl, {
      attribution: config.attribution
    }).addTo(this.map);
    
    // 创建图层组
    this.layers = {
      mrt: L.layerGroup().addTo(this.map),
      lrt: L.layerGroup().addTo(this.map),
      bus: L.layerGroup().addTo(this.map)
    };
    
    // 存储线路数据和颜色映射
    this.routesData = null;
    this.colorScales = null;
    
    // 当前显示的线路对象（用于更新）
    this.routeObjects = new Map();
  }
  
  /**
   * 加载线路数据并渲染
   */
  loadRoutes(routesData, colorScales) {
    this.routesData = routesData;
    this.colorScales = colorScales;
    
    routesData.routes.forEach(route => {
      // 转换 GeoJSON 坐标 [lng, lat] -> Leaflet [lat, lng]
      const coords = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
      
      // 创建折线
      const polyline = L.polyline(coords, {
        color: route.color,
        weight: 3,
        opacity: 0.7
      });
      
      // 添加弹窗
      polyline.bindPopup(`
        <b>${route.route_name}</b><br>
        Type: ${route.type.toUpperCase()}<br>
        Capacity: ${route.capacity.toLocaleString()} pax/hr
      `);
      
      // 添加到对应图层
      this.layers[route.type].addLayer(polyline);
      
      // 存储引用（用于更新颜色）
      this.routeObjects.set(route.route_id, polyline);
    });
    
    console.log(`✅ Rendered ${routesData.routes.length} routes`);
  }
  
  /**
   * 更新客流数据（改变线路颜色和宽度）
   */
  updateFlow(flowData) {
    flowData.data.forEach(item => {
      const polyline = this.routeObjects.get(item.route_id);
      if (!polyline) return;
      
      // 根据客流量计算颜色
      const color = this.colorScales.getColor(item.type, item.flow);
      
      // 根据客流量计算线宽（2-10）
      const weight = Math.max(2, Math.min(10, 2 + item.flow / 1000));
      
      // 更新样式
      polyline.setStyle({
        color: color,
        weight: weight,
        opacity: item.utilization > 1 ? 1 : 0.7  // 超载时更明显
      });
      
      // 更新弹窗内容
      const route = this.routesData.routes.find(r => r.route_id === item.route_id);
      polyline.setPopupContent(`
        <b>${route.route_name}</b><br>
        Flow: ${item.flow.toLocaleString()} pax/hr<br>
        Utilization: ${(item.utilization * 100).toFixed(1)}%<br>
        ${item.utilization > 1 ? '<span style="color:red">⚠️ Overcapacity</span>' : ''}
      `);
    });
  }
  
  /**
   * 切换图层可见性
   */
  toggleLayer(type, visible) {
    if (visible) {
      this.map.addLayer(this.layers[type]);
    } else {
      this.map.removeLayer(this.layers[type]);
    }
  }
  
  /**
   * 获取当前可见的图层类型
   */
  getVisibleLayers() {
    const visible = [];
    for (const [type, layer] of Object.entries(this.layers)) {
      if (this.map.hasLayer(layer)) {
        visible.push(type);
      }
    }
    return visible;
  }
}
```

### 4. 颜色映射 (js/colorScale.js)

```javascript
class ColorScaleManager {
  constructor(config) {
    this.scales = {};
    
    // 为每种交通类型创建色标
    Object.keys(config).forEach(type => {
      const { scheme, domain } = config[type];
      this.scales[type] = d3.scaleSequential()
        .domain(domain)
        .interpolator(d3[`interpolate${scheme}`]);
    });
  }
  
  /**
   * 获取颜色
   * @param {string} type - 交通类型
   * @param {number} value - 客流量值
   * @returns {string} RGB 颜色字符串
   */
  getColor(type, value) {
    return this.scales[type](value);
  }
  
  /**
   * 获取域范围
   */
  getDomain(type) {
    return this.scales[type].domain();
  }
  
  /**
   * 获取所有配置
   */
  getAllConfigs() {
    const configs = {};
    for (const [type, scale] of Object.entries(this.scales)) {
      configs[type] = {
        domain: scale.domain(),
        interpolator: scale.interpolator()
      };
    }
    return configs;
  }
}
```

### 5. 时间轴控制 (js/timeline.js)

```javascript
class Timeline {
  constructor(containerId, timeRange, config) {
    this.container = d3.select(`#${containerId}`);
    this.startTime = dayjs(timeRange.start_date);
    this.endTime = dayjs(timeRange.end_date);
    this.currentTime = this.startTime;
    this.config = config;
    
    this.playing = false;
    this.playTimer = null;
    this.onChange = null;  // 回调函数
    
    this.render();
  }
  
  render() {
    const width = this.container.node().offsetWidth - 40;
    const height = 80;
    
    // 创建 SVG
    const svg = this.container.append('svg')
      .attr('width', '100%')
      .attr('height', height);
    
    const g = svg.append('g')
      .attr('transform', 'translate(20, 10)');
    
    // 时间比例尺
    this.timeScale = d3.scaleTime()
      .domain([this.startTime.toDate(), this.endTime.toDate()])
      .range([0, width]);
    
    // 时间轴
    const axis = d3.axisBottom(this.timeScale)
      .ticks(d3.timeHour.every(6))
      .tickFormat(d3.timeFormat('%H:%M'));
    
    g.append('g')
      .attr('class', 'axis')
      .attr('transform', 'translate(0, 40)')
      .call(axis);
    
    // 当前时间指示器
    this.timeIndicator = g.append('line')
      .attr('class', 'time-indicator')
      .attr('y1', 0)
      .attr('y2', 40)
      .attr('stroke', '#e74c3c')
      .attr('stroke-width', 2);
    
    this.updateIndicator();
    
    // 滑块
    const slider = this.container.append('input')
      .attr('type', 'range')
      .attr('class', 'time-slider')
      .attr('min', 0)
      .attr('max', this.endTime.diff(this.startTime, 'hour'))
      .attr('value', 0)
      .attr('step', 1)
      .on('input', (event) => {
        const hours = parseInt(event.target.value);
        this.setTime(this.startTime.add(hours, 'hour'));
      });
    
    // 控制按钮
    this.renderControls();
  }
  
  renderControls() {
    const controls = this.container.append('div')
      .attr('class', 'timeline-controls');
    
    // 播放/暂停按钮
    this.playButton = controls.append('button')
      .attr('class', 'btn-play')
      .text('▶ Play')
      .on('click', () => {
        if (this.playing) {
          this.pause();
        } else {
          this.play();
        }
      });
    
    // 重置按钮
    controls.append('button')
      .attr('class', 'btn-reset')
      .text('⏮ Reset')
      .on('click', () => {
        this.setTime(this.startTime);
        this.pause();
      });
    
    // 时间显示
    this.timeDisplay = controls.append('span')
      .attr('class', 'time-display')
      .text(this.currentTime.format('YYYY-MM-DD HH:mm'));
  }
  
  updateIndicator() {
    const x = this.timeScale(this.currentTime.toDate());
    this.timeIndicator.attr('x1', x).attr('x2', x);
    this.timeDisplay.text(this.currentTime.format('YYYY-MM-DD HH:mm'));
    
    // 更新滑块
    const hours = this.currentTime.diff(this.startTime, 'hour');
    this.container.select('.time-slider').property('value', hours);
  }
  
  setTime(time) {
    this.currentTime = time;
    this.updateIndicator();
    
    // 触发回调
    if (this.onChange) {
      this.onChange(this.currentTime.format('YYYY-MM-DDTHH:mm:ss'));
    }
  }
  
  play() {
    this.playing = true;
    this.playButton.text('⏸ Pause');
    
    this.playTimer = setInterval(() => {
      const nextTime = this.currentTime.add(1, 'hour');
      
      if (nextTime.isAfter(this.endTime)) {
        this.pause();
        return;
      }
      
      this.setTime(nextTime);
    }, this.config.PLAY_INTERVAL);
  }
  
  pause() {
    this.playing = false;
    this.playButton.text('▶ Play');
    
    if (this.playTimer) {
      clearInterval(this.playTimer);
      this.playTimer = null;
    }
  }
}
```

### 6. 图例组件 (js/legend.js)

```javascript
class Legend {
  constructor(containerId, colorScales) {
    this.container = d3.select(`#${containerId}`);
    this.colorScales = colorScales;
    this.visibleTypes = ['mrt', 'lrt', 'bus'];
  }
  
  render() {
    this.container.selectAll('*').remove();
    
    const legendData = [
      { type: 'mrt', name: 'MRT (地铁)' },
      { type: 'lrt', name: 'LRT (轻轨)' },
      { type: 'bus', name: 'Bus (公交)' }
    ];
    
    legendData.forEach(item => {
      if (!this.visibleTypes.includes(item.type)) return;
      
      const domain = this.colorScales.getDomain(item.type);
      
      // 创建图例项
      const legendItem = this.container.append('div')
        .attr('class', 'legend-item');
      
      // 标题
      legendItem.append('div')
        .attr('class', 'legend-title')
        .text(item.name);
      
      // 渐变色条
      const svg = legendItem.append('svg')
        .attr('width', 200)
        .attr('height', 30);
      
      // 定义渐变
      const defs = svg.append('defs');
      const gradient = defs.append('linearGradient')
        .attr('id', `gradient-${item.type}`);
      
      // 生成渐变色
      for (let i = 0; i <= 10; i++) {
        const value = domain[0] + (domain[1] - domain[0]) * i / 10;
        const color = this.colorScales.getColor(item.type, value);
        
        gradient.append('stop')
          .attr('offset', `${i * 10}%`)
          .attr('stop-color', color);
      }
      
      // 绘制矩形
      svg.append('rect')
        .attr('width', 180)
        .attr('height', 15)
        .attr('x', 10)
        .attr('y', 5)
        .style('fill', `url(#gradient-${item.type})`);
      
      // 刻度标签
      svg.append('text')
        .attr('x', 10)
        .attr('y', 28)
        .attr('text-anchor', 'start')
        .attr('font-size', 10)
        .text(domain[0]);
      
      svg.append('text')
        .attr('x', 190)
        .attr('y', 28)
        .attr('text-anchor', 'end')
        .attr('font-size', 10)
        .text(domain[1]);
      
      svg.append('text')
        .attr('x', 100)
        .attr('y', 28)
        .attr('text-anchor', 'middle')
        .attr('font-size', 10)
        .text('pax/hr');
    });
  }
  
  updateVisibleTypes(types) {
    this.visibleTypes = types;
    this.render();
  }
}
```

### 7. 图层控制器 (js/controls.js)

```javascript
class LayerControls {
  constructor(containerId, transitTypes) {
    this.container = document.getElementById(containerId);
    this.transitTypes = transitTypes;
    this.onChange = null;  // 回调函数
    
    this.render();
  }
  
  render() {
    this.container.innerHTML = '<h3>图层控制</h3>';
    
    this.transitTypes.forEach(type => {
      const label = document.createElement('label');
      label.className = 'layer-control';
      
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = true;
      checkbox.dataset.type = type.id;
      checkbox.addEventListener('change', (e) => {
        if (this.onChange) {
          this.onChange(e.target.dataset.type, e.target.checked);
        }
      });
      
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(` ${type.name} (${type.name_zh})`));
      
      this.container.appendChild(label);
    });
  }
  
  getVisibleTypes() {
    const checkboxes = this.container.querySelectorAll('input[type="checkbox"]');
    const visible = [];
    checkboxes.forEach(cb => {
      if (cb.checked) {
        visible.push(cb.dataset.type);
      }
    });
    return visible;
  }
}
```

### 8. 主逻辑 (js/main.js)

```javascript
// 主应用类
class TransitVisualization {
  constructor() {
    this.api = new TransitAPI(CONFIG.API_BASE_URL, CONFIG.USE_MOCK_DATA);
    this.map = null;
    this.timeline = null;
    this.legend = null;
    this.controls = null;
    this.colorScales = null;
    
    this.init();
  }
  
  async init() {
    try {
      // 显示加载指示器
      this.showLoading('正在加载系统数据...');
      
      // 1. 加载元数据
      const metadata = await this.api.fetchMetadata();
      console.log('✅ Loaded metadata:', metadata);
      
      // 2. 初始化颜色映射
      this.colorScales = new ColorScaleManager(CONFIG.COLORS);
      
      // 3. 初始化地图
      this.map = new TransitMap('map', CONFIG.MAP);
      
      // 4. 加载线路数据
      this.showLoading('正在加载线路数据...');
      const routesData = await this.api.fetchRoutes();
      this.map.loadRoutes(routesData, this.colorScales);
      
      // 5. 初始化时间轴
      this.timeline = new Timeline(
        'timeline',
        metadata.temporal_range,
        CONFIG.ANIMATION
      );
      
      // 6. 初始化图层控制器
      this.controls = new LayerControls('controls', metadata.transit_types);
      
      // 7. 初始化图例
      this.legend = new Legend('legend', this.colorScales);
      this.legend.render();
      
      // 8. 绑定事件
      this.bindEvents();
      
      // 9. 加载初始客流数据
      await this.updatePassengerFlow();
      
      this.hideLoading();
      console.log('✅ Application initialized successfully!');
      
    } catch (error) {
      console.error('❌ Initialization error:', error);
      this.showError(`初始化失败: ${error.message}`);
    }
  }
  
  bindEvents() {
    // 时间轴变化
    this.timeline.onChange = async (datetime) => {
      await this.updatePassengerFlow(datetime);
    };
    
    // 图层控制变化
    this.controls.onChange = (type, visible) => {
      this.map.toggleLayer(type, visible);
      this.legend.updateVisibleTypes(this.controls.getVisibleTypes());
    };
  }
  
  async updatePassengerFlow(datetime = null) {
    try {
      // 如果没有指定时间，使用时间轴当前时间
      if (!datetime) {
        datetime = this.timeline.currentTime.format('YYYY-MM-DDTHH:mm:ss');
      }
      
      // 获取可见的图层类型
      const visibleTypes = this.controls.getVisibleTypes();
      
      // 获取客流数据
      const flowData = await this.api.fetchPassengerFlow(datetime, visibleTypes);
      
      // 更新地图
      this.map.updateFlow(flowData);
      
    } catch (error) {
      console.error('❌ Failed to update passenger flow:', error);
      this.showError(`更新数据失败: ${error.message}`);
    }
  }
  
  showLoading(message) {
    document.getElementById('loading').textContent = message;
    document.getElementById('loading').style.display = 'block';
  }
  
  hideLoading() {
    document.getElementById('loading').style.display = 'none';
  }
  
  showError(message) {
    alert(message);
    this.hideLoading();
  }
}

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
  window.app = new TransitVisualization();
});
```

---

## Mock 数据开发

### data/mockData.js

```javascript
const MOCK_DATA = {
  metadata: {
    version: '1.0',
    dataset: {
      name: 'Singapore Public Transit Flow (Mock)',
      last_updated: '2024-12-17T00:00:00'
    },
    temporal_range: {
      start_date: '2024-01-01T00:00:00',
      end_date: '2024-01-01T23:00:00',
      granularity: 'hourly'
    },
    transit_types: [
      { id: 'mrt', name: 'Mass Rapid Transit', name_zh: '地铁', max_capacity: 12000, color_scheme: 'blues' },
      { id: 'lrt', name: 'Light Rail Transit', name_zh: '轻轨', max_capacity: 3500, color_scheme: 'greens' },
      { id: 'bus', name: 'Public Bus', name_zh: '公交', max_capacity: 800, color_scheme: 'oranges' }
    ],
    map_config: {
      center: [1.3521, 103.8198],
      zoom_default: 12
    }
  },
  
  routes: {
    routes: [
      {
        route_id: 'NS_LINE',
        route_name: 'North-South Line',
        route_code: 'NS',
        type: 'mrt',
        capacity: 12000,
        color: '#D42E12',
        geometry: {
          type: 'LineString',
          coordinates: [[103.7423, 1.3330], [103.8198, 1.3521], [103.8525, 1.4304]]
        },
        stations: [
          { id: 'NS1', name: 'Jurong East', position: [1.3330, 103.7423] },
          { id: 'NS24', name: 'Dhoby Ghaut', position: [1.3521, 103.8198] }
        ],
        operational: true,
        operator: 'SMRT'
      }
    ],
    total_count: 1
  },
  
  passengerFlow: {
    timestamp: '2024-01-01T08:00:00',
    data: [
      {
        route_id: 'NS_LINE',
        type: 'mrt',
        flow: 8500,
        capacity: 12000,
        utilization: 0.708,
        direction: { inbound: 5000, outbound: 3500 }
      }
    ],
    total_flow: 8500
  }
};
```

---

## 样式与布局

### index.html

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>新加坡公共交通可视化</title>
  
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  
  <!-- 自定义 CSS -->
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <div id="app">
    <!-- 加载指示器 -->
    <div id="loading">正在加载...</div>
    
    <!-- 头部 -->
    <header>
      <h1>🚇 新加坡公共交通时空可视化</h1>
    </header>
    
    <!-- 主容器 -->
    <div class="container">
      <!-- 左侧：地图 -->
      <div class="map-container">
        <div id="map"></div>
      </div>
      
      <!-- 右侧：控制面板 -->
      <div class="sidebar">
        <div id="controls"></div>
        <div id="legend"></div>
      </div>
    </div>
    
    <!-- 底部：时间轴 -->
    <div class="timeline-container">
      <div id="timeline"></div>
    </div>
  </div>
  
  <!-- 依赖库 -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script src="https://unpkg.com/dayjs@1.11.10/dayjs.min.js"></script>
  
  <!-- Mock 数据（开发时使用） -->
  <script src="data/mockData.js"></script>
  
  <!-- 应用代码 -->
  <script src="js/config.js"></script>
  <script src="js/api.js"></script>
  <script src="js/colorScale.js"></script>
  <script src="js/map.js"></script>
  <script src="js/timeline.js"></script>
  <script src="js/legend.js"></script>
  <script src="js/controls.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
```

### css/style.css

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
  background: #f5f5f5;
}

header {
  background: #2c3e50;
  color: white;
  padding: 15px 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

header h1 {
  font-size: 24px;
  font-weight: 600;
}

.container {
  display: flex;
  height: calc(100vh - 220px);
}

.map-container {
  flex: 1;
  position: relative;
}

#map {
  width: 100%;
  height: 100%;
}

.sidebar {
  width: 280px;
  background: white;
  padding: 20px;
  overflow-y: auto;
  box-shadow: -2px 0 4px rgba(0,0,0,0.1);
}

.timeline-container {
  background: white;
  padding: 20px;
  border-top: 1px solid #ddd;
  height: 160px;
}

/* 图层控制 */
#controls h3 {
  font-size: 16px;
  margin-bottom: 10px;
  color: #2c3e50;
}

.layer-control {
  display: block;
  padding: 8px 0;
  cursor: pointer;
  user-select: none;
}

.layer-control input {
  margin-right: 8px;
}

/* 图例 */
#legend {
  margin-top: 30px;
}

.legend-item {
  margin-bottom: 20px;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #2c3e50;
}

/* 时间轴 */
#timeline {
  position: relative;
}

.time-slider {
  width: 100%;
  margin-top: 10px;
}

.timeline-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
}

.timeline-controls button {
  padding: 8px 16px;
  border: none;
  background: #3498db;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.timeline-controls button:hover {
  background: #2980b9;
}

.time-display {
  font-weight: 600;
  color: #2c3e50;
  font-size: 16px;
}

/* 加载指示器 */
#loading {
  display: none;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.8);
  color: white;
  padding: 20px 40px;
  border-radius: 8px;
  z-index: 9999;
  font-size: 18px;
}

/* Leaflet 弹窗样式 */
.leaflet-popup-content {
  margin: 12px;
  line-height: 1.6;
}
```

---

## 调试技巧

### 1. 使用 Mock 数据
在 `config.js` 中设置：
```javascript
USE_MOCK_DATA: true
```

### 2. 查看 API 请求
在浏览器开发者工具的 Network 标签查看所有请求。

### 3. 调试坐标转换
```javascript
// 在控制台测试
const geoJsonCoords = [103.8198, 1.3521];
const leafletCoords = [geoJsonCoords[1], geoJsonCoords[0]];
console.log('GeoJSON:', geoJsonCoords, 'Leaflet:', leafletCoords);
```

### 4. 性能监控
```javascript
console.time('API Request');
await api.fetchPassengerFlow(datetime, types);
console.timeEnd('API Request');
```

---

**完成后**: 请阅读 `TESTING_DEBUG.md` 进行全面测试。
