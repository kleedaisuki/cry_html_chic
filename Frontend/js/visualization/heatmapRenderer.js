/**
 * 人口热力图渲染器
 * Singapore Transit Visualization System
 *
 * 使用 Canvas 叠加层在地图上绘制人口密度热力图
 */

const HeatmapRenderer = (function() {
    'use strict';

    // 内部状态
    let canvasOverlay = null;
    let enabled = true;
    let heatmapData = [];
    let mapInstance = null;

    // 热力图配置
    const CONFIG = {
        radius: 35,           // 热力点半径
        gradient: [           // 颜色渐变（从冷到热）
            { pos: 0.0, color: 'rgba(0, 0, 255, 0)' },
            { pos: 0.2, color: 'rgba(0, 255, 255, 0.3)' },
            { pos: 0.4, color: 'rgba(0, 255, 0, 0.4)' },
            { pos: 0.6, color: 'rgba(255, 255, 0, 0.5)' },
            { pos: 0.8, color: 'rgba(255, 127, 0, 0.6)' },
            { pos: 1.0, color: 'rgba(255, 0, 0, 0.7)' }
        ]
    };

    /**
     * 创建 Canvas 叠加层类
     */
    const HeatmapCanvas = L.Layer.extend({
        _heatmapData: [],
        _enabled: true,

        initialize: function(options) {
            L.setOptions(this, options);
        },

        onAdd: function(map) {
            this._map = map;
            this._container = L.DomUtil.create('div', 'leaflet-heatmap-layer');
            this._container.style.position = 'absolute';
            this._container.style.top = '0';
            this._container.style.left = '0';
            this._container.style.width = '100%';
            this._container.style.height = '100%';
            this._container.style.pointerEvents = 'none';
            this._container.style.zIndex = '400'; // 在底图之上，线路之下

            // 创建 canvas
            this._canvas = L.DomUtil.create('canvas', '');
            this._canvas.style.width = '100%';
            this._canvas.style.height = '100%';
            this._container.appendChild(this._canvas);

            map.getPanes().overlayPane.appendChild(this._container);

            // 绑定事件
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

        setData: function(data) {
            this._heatmapData = data || [];
            this._redraw();
        },

        setEnabled: function(enabled) {
            this._enabled = enabled;
            this._redraw();
        },

        _redraw: function() {
            if (!this._canvas) {
                console.log('HeatmapRenderer: _canvas not available');
                return;
            }

            const canvas = this._canvas;
            const ctx = canvas.getContext('2d');
            const map = this._map;

            if (!map) {
                console.log('HeatmapRenderer: map not available in _redraw');
                return;
            }

            // 获取画布的实际尺寸
            const size = map.getSize();
            const pixelRatio = window.devicePixelRatio || 1;

            canvas.width = size.x * pixelRatio;
            canvas.height = size.y * pixelRatio;
            canvas.style.width = size.x + 'px';
            canvas.style.height = size.y + 'px';

            ctx.scale(pixelRatio, pixelRatio);

            // 清空画布
            ctx.clearRect(0, 0, size.x, size.y);

            if (!this._enabled) {
                console.log('HeatmapRenderer: disabled');
                return;
            }

            if (this._heatmapData.length === 0) {
                console.log('HeatmapRenderer: no data to render');
                return;
            }

            console.log('HeatmapRenderer: rendering', this._heatmapData.length, 'points');

            // 获取最大密度值用于归一化
            const maxValue = Math.max(...this._heatmapData.map(p => p.value || 0), 1);

            // 绘制每个热力点
            this._heatmapData.forEach(point => {
                const lat = point.lat;
                const lon = point.lon;
                const value = point.value || 0;

                // 将经纬度转换为屏幕坐标
                const pointPos = map.latLngToContainerPoint([lat, lon]);

                // 归一化密度值 (0-1)
                const intensity = Math.min(value / maxValue, 1.0);

                // 绘制热力点
                this._drawHeatPoint(ctx, pointPos.x, pointPos.y, CONFIG.radius, intensity);
            });
        },

        _drawHeatPoint: function(ctx, x, y, radius, intensity) {
            // 根据强度调整半径
            const adjustedRadius = radius * (0.5 + intensity * 0.5);

            // 创建径向渐变
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, adjustedRadius);

            // 设置渐变颜色（根据强度调整透明度）
            for (const stop of CONFIG.gradient) {
                const baseOpacity = parseFloat(stop.color.match(/[\d.]+\)$/)?.[0]) || 0.7;
                const adjustedColor = stop.color.replace(/[\d.]+\)$/, `${baseOpacity * intensity})`);
                gradient.addColorStop(stop.pos, adjustedColor);
            }

            // 绘制圆形
            ctx.beginPath();
            ctx.arc(x, y, adjustedRadius, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();
        }
    });

    /**
     * 初始化渲染器
     */
    function init() {
        if (canvasOverlay) return;

        const map = MapManager?.getMap();
        if (!map) {
            console.warn('HeatmapRenderer: Map not available');
            return;
        }

        mapInstance = map;
        enabled = true;

        // 创建 Canvas 叠加层
        canvasOverlay = new HeatmapCanvas();
        canvasOverlay.addTo(map);

        console.log('HeatmapRenderer initialized successfully');
        console.log('Canvas overlay z-index:', canvasOverlay._container?.style?.zIndex);
    }

    /**
     * 渲染热力图数据
     * @param {Array} data - 热力图数据点 [{ lat, lon, value, name }]
     */
    function render(data) {
        console.log('HeatmapRenderer.render called with', data?.length, 'points');
        if (data?.length > 0) {
            console.log('Sample point:', JSON.stringify(data[0]));
        }

        if (!data || !Array.isArray(data)) {
            heatmapData = [];
            if (canvasOverlay) {
                canvasOverlay.setData([]);
            }
            return;
        }

        heatmapData = data;

        if (canvasOverlay) {
            canvasOverlay.setData(data);
        }
    }

    /**
     * 设置启用状态
     * @param {boolean} val - 是否启用
     */
    function setEnabled(val) {
        enabled = val;

        if (canvasOverlay) {
            canvasOverlay.setEnabled(val);
        }
    }

    /**
     * 获取启用状态
     * @returns {boolean}
     */
    function getEnabled() {
        return enabled;
    }

    /**
     * 获取当前数据
     * @returns {Array}
     */
    function getData() {
        return [...heatmapData];
    }

    /**
     * 清除热力图
     */
    function clear() {
        heatmapData = [];
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
        heatmapData = [];
        mapInstance = null;
        enabled = false;
    }

    // 导出公共 API
    return {
        init,
        render,
        setEnabled,
        getEnabled,
        getData,
        clear,
        destroy
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeatmapRenderer;
}
