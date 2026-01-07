/**
 * 客流蒙版渲染器
 * Singapore Transit Visualization System
 *
 * 使用 IDW (反距离加权) 插值生成连续客流密度图
 * 为线路着色提供蒙版值
 */

const FlowMaskRenderer = (function() {
    'use strict';

    // 内部状态
    let stationFlowData = null;
    let currentTimestamp = null;
    let currentStations = [];
    let mapInstance = null;
    let canvasOverlay = null;
    let enabled = true;

    // 蒙版配置
    const CONFIG = {
        searchRadius: 5000,      // 搜索半径（米）
        interpolationPower: 2,   // IDW 幂参数
        minStations: 2,          // 最少站点数才能进行插值
        flowRange: [0, 100000],  // 客流量范围（用于归一化）
        canvasZIndex: 350        // Canvas 层级（在底图之上，线路之下）
    };

    // 数据范围缓存
    let dataRange = { min: 0, max: 100000 };

    /**
     * 计算两点间的 Haversine 距离（米）
     */
    function haversineDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000; // 地球半径（米）

        const lat1Rad = lat1 * Math.PI / 180;
        const lat2Rad = lat2 * Math.PI / 180;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(dLat / 2) ** 2 +
                  Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLon / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c;
    }

    /**
     * IDW 插值计算指定位置的客流值
     * @param {number} lat - 纬度
     * @param {number} lon - 经度
     * @param {Array} stations - 站点数据数组
     * @returns {number|null} 插值后的客流值，null 表示无法计算
     */
    function interpolateFlow(lat, lon, stations) {
        if (!stations || stations.length < CONFIG.minStations) {
            return null;
        }

        let numerator = 0;
        let denominator = 0;
        let nearbyCount = 0;

        for (const station of stations) {
            const dist = haversineDistance(lat, lon, station.lat, station.lon);

            // 只考虑搜索半径内的站点
            if (dist < CONFIG.searchRadius && dist > 0) {
                const weight = 1 / (dist ** CONFIG.interpolationPower);
                numerator += weight * station.flow;
                denominator += weight;
                nearbyCount++;
            }
        }

        if (nearbyCount < CONFIG.minStations || denominator === 0) {
            return null;
        }

        return numerator / denominator;
    }

    /**
     * 获取归一化的客流值（0-1）
     * @param {number} lat - 纬度
     * @param {number} lon - 经度
     * @returns {number} 归一化后的值（0-1），0 表示无数据
     */
    function getNormalizedValue(lat, lon) {
        const flow = getValueAt(lat, lon);
        if (flow === null) {
            return 0;
        }

        const range = dataRange.max - dataRange.min;
        if (range <= 0) {
            return 0;
        }

        return Math.min(Math.max((flow - dataRange.min) / range, 0), 1);
    }

    /**
     * 获取指定位置的客流值
     * @param {number} lat - 纬度
     * @param {number} lon - 经度
     * @returns {number|null} 客流值，null 表示无法计算
     */
    function getValueAt(lat, lon) {
        if (!currentStations || currentStations.length === 0) {
            return null;
        }
        return interpolateFlow(lat, lon, currentStations);
    }

    /**
     * 获取当前时间戳
     * @returns {string|null}
     */
    function getCurrentTimestamp() {
        return currentTimestamp;
    }

    /**
     * 获取当前站点数据
     * @returns {Array}
     */
    function getCurrentStations() {
        return [...currentStations];
    }

    /**
     * 检查数据是否就绪
     * @returns {boolean}
     */
    function isReady() {
        return stationFlowData !== null && currentStations.length > 0;
    }

    /**
     * 设置客流数据
     * @param {Object} data - station_flow.js 数据格式
     */
    function setData(data) {
        stationFlowData = data;

        if (data && data.data) {
            // 计算数据范围
            let allFlows = [];
            for (const entry of Object.values(data.data)) {
                for (const station of entry.stations || []) {
                    allFlows.push(station.flow);
                }
            }

            if (allFlows.length > 0) {
                dataRange.min = Math.min(...allFlows);
                dataRange.max = Math.max(...allFlows);
                console.log('FlowMaskRenderer: data range', dataRange.min, '-', dataRange.max);
            }
        }

        console.log('FlowMaskRenderer: data loaded, timestamps:', Object.keys(data?.data || {}).length);
    }

    /**
     * 设置当前时间并更新站点数据
     * @param {string} timestamp - 时间戳
     */
    function setTimestamp(timestamp) {
        currentTimestamp = timestamp;

        if (!stationFlowData || !stationFlowData.data) {
            currentStations = [];
            return;
        }

        const entry = stationFlowData.data[timestamp];
        if (entry && entry.stations) {
            currentStations = entry.stations;
            console.log('FlowMaskRenderer: set timestamp', timestamp, 'with', currentStations.length, 'stations');
        } else {
            // 尝试找最接近的时间
            const timestamps = Object.keys(stationFlowData.data).sort();
            const closest = findClosestTimestamp(timestamp, timestamps);

            if (closest) {
                const closestEntry = stationFlowData.data[closest];
                if (closestEntry && closestEntry.stations) {
                    currentStations = closestEntry.stations;
                    console.log('FlowMaskRenderer: using closest timestamp', closest);
                }
            }

            if (!closestEntry) {
                currentStations = [];
            }
        }

        // 更新 Canvas 渲染
        if (canvasOverlay) {
            canvasOverlay.setData(currentStations);
        }
    }

    /**
     * 找到最接近的时间戳
     */
    function findClosestTimestamp(target, timestamps) {
        if (!timestamps || timestamps.length === 0) {
            return null;
        }

        // 解析时间戳获取小时
        const getHour = (ts) => {
            if (ts.includes('|')) {
                const parts = ts.split('|');
                return parseInt(parts[2], 10) || 0;
            }
            return 0;
        };

        const targetHour = getHour(target);

        let closest = timestamps[0];
        let minDiff = Math.abs(getHour(closest) - targetHour);

        for (const ts of timestamps) {
            const diff = Math.abs(getHour(ts) - targetHour);
            if (diff < minDiff) {
                minDiff = diff;
                closest = ts;
            }
        }

        return closest;
    }

    /**
     * 设置启用状态
     */
    function setEnabled(val) {
        enabled = val;

        if (canvasOverlay) {
            canvasOverlay.setEnabled(val);
        }
    }

    /**
     * 获取启用状态
     */
    function getEnabled() {
        return enabled;
    }

    /**
     * 获取数据范围
     */
    function getDataRange() {
        return { ...dataRange };
    }

    /**
     * Canvas 叠加层类（用于可视化）
     */
    const FlowMaskCanvas = L.Layer.extend({
        _stations: [],
        _enabled: true,

        initialize: function(options) {
            L.setOptions(this, options);
        },

        onAdd: function(map) {
            this._map = map;
            this._container = L.DomUtil.create('div', 'leaflet-flowmask-layer');
            this._container.style.position = 'absolute';
            this._container.style.top = '0';
            this._container.style.left = '0';
            this._container.style.width = '100%';
            this._container.style.height = '100%';
            this._container.style.pointerEvents = 'none';
            this._container.style.zIndex = CONFIG.canvasZIndex;

            this._canvas = L.DomUtil.create('canvas', '');
            this._canvas.style.width = '100%';
            this._canvas.style.height = '100%';
            this._container.appendChild(this._canvas);

            map.getPanes().overlayPane.appendChild(this._container);

            map.on('moveend', this._redraw, this);
            map.on('resize', this._redraw, this);
            map.on('zoomend', this._redraw, this);

            this._redraw();
        },

        onRemove: function(map) {
            map.getPanes().overlayPane.removeChild(this._container);
            map.off('moveend', this._redraw, this);
            map.off('resize', this._redraw, this);
            map.off('zoomend', this._redraw, this);
        },

        setData: function(stations) {
            this._stations = stations || [];
            this._redraw();
        },

        setEnabled: function(enabled) {
            this._enabled = enabled;
            this._redraw();
        },

        _redraw: function() {
            if (!this._canvas) return;

            const canvas = this._canvas;
            const ctx = canvas.getContext('2d');
            const map = this._map;

            if (!map) return;

            const size = map.getSize();
            const pixelRatio = window.devicePixelRatio || 1;

            canvas.width = size.x * pixelRatio;
            canvas.height = size.y * pixelRatio;
            canvas.style.width = size.x + 'px';
            canvas.style.height = size.y + 'px';

            ctx.scale(pixelRatio, pixelRatio);
            ctx.clearRect(0, 0, size.x, size.y);

            if (!this._enabled || this._stations.length === 0) return;

            // 绘制站点圆点（可选的调试可视化）
            const maxFlow = Math.max(...this._stations.map(s => s.flow || 0), 1);

            this._stations.forEach(station => {
                const pointPos = map.latLngToContainerPoint([station.lat, station.lon]);
                const radius = 3 + (station.flow / maxFlow) * 10;

                // 根据客流量设置颜色
                const intensity = station.flow / maxFlow;
                const color = FlowMaskRenderer.getColorForIntensity(intensity);

                ctx.beginPath();
                ctx.arc(pointPos.x, pointPos.y, radius, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
            });
        }
    });

    /**
     * 初始化渲染器（可选的可视化层）
     */
    function init() {
        if (canvasOverlay) return;

        const map = MapManager?.getMap();
        if (!map) {
            console.warn('FlowMaskRenderer: Map not available');
            return;
        }

        mapInstance = map;

        // 创建 Canvas 叠加层
        canvasOverlay = new FlowMaskCanvas();
        canvasOverlay.addTo(map);

        console.log('FlowMaskRenderer initialized');
    }

    /**
     * 获取颜色（辅助方法，供外部使用）
     * @param {number} intensity - 强度 (0-1)
     * @returns {string} 颜色值
     */
    function getColorForIntensity(intensity) {
        // 使用 ColorScale
        if (window.ColorScale) {
            const flow = intensity * 100000; // 假设最大 100k
            return ColorScale.getColor(flow, 'mrt');
        }

        // 备用颜色方案
        const r = Math.round(255 * intensity);
        const g = Math.round(255 * (1 - intensity));
        const b = 100;
        return `rgb(${r},${g},${b})`;
    }

    /**
     * 清除数据
     */
    function clear() {
        currentStations = [];
        currentTimestamp = null;

        if (canvasOverlay) {
            canvasOverlay.setData([]);
        }
    }

    /**
     * 销毁渲染器
     */
    function destroy() {
        if (canvasOverlay && mapInstance) {
            mapInstance.removeLayer(canvasOverlay);
        }
        canvasOverlay = null;
        stationFlowData = null;
        currentStations = [];
        mapInstance = null;
        enabled = false;
    }

    // 导出公共 API
    return {
        setData,
        setTimestamp,
        getValueAt,
        getNormalizedValue,
        getCurrentTimestamp,
        getCurrentStations,
        getDataRange,
        isReady,
        setEnabled,
        getEnabled,
        init,
        clear,
        destroy,
        // 导出供内部使用的辅助函数
        _getColorForIntensity: getColorForIntensity,
        _interpolateFlow: interpolateFlow,
        _haversineDistance: haversineDistance
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlowMaskRenderer;
}

// 挂载到 window 对象
window.FlowMaskRenderer = FlowMaskRenderer;
