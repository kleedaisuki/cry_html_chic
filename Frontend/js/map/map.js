/**
 * 地图管理器
 * Singapore Transit Visualization System
 */

const MapManager = (function() {
    'use strict';

    // Leaflet 地图实例
    let map = null;

    // 底图图层组
    let tileLayers = {
        light: null,
        dark: null
    };

    // 当前底图类型
    let currentBaseMap = 'light';

    // 标记图标配置
    const defaultIcon = L.icon({
        iconUrl: 'css/lib/images/marker-icon.png',
        iconRetinaUrl: 'css/lib/images/marker-icon-2x.png',
        shadowUrl: 'css/lib/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    /**
     * 初始化地图
     * @param {string|Element} container - 容器元素或选择器
     * @returns {Promise<Map>} Leaflet 地图实例
     */
    async function init(container) {
        const mapContainer = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!mapContainer) {
            console.error('Map container not found!');
            throw new Error('Map container not found');
        }

        console.log('Map container found:', mapContainer);
        console.log('Container size:', mapContainer.offsetWidth, 'x', mapContainer.offsetHeight);

        // 创建地图
        map = L.map(mapContainer, {
            center: CONFIG.map.center,
            zoom: CONFIG.map.zoom,
            minZoom: CONFIG.map.minZoom,
            maxZoom: CONFIG.map.maxZoom,
            zoomControl: false // 使用自定义控件
        });

        console.log('Map created:', !!map);
        console.log('Initial center:', map.getCenter());
        console.log('Initial zoom:', map.getZoom());

        // 添加底图
        addTileLayers();

        // 添加缩放控件到左上角
        L.control.zoom({
            position: 'topleft'
        }).addTo(map);

        return map;
    }

    /**
     * 添加底图图层
     */
    function addTileLayers() {
        // 浅色底图（OpenStreetMap）
        tileLayers.light = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19,
                crossOrigin: 'anonymous'
            }
        ).on('load', function() {
            console.log('Tile layer loaded successfully');
        }).on('error', function(e) {
            console.error('Tile layer error:', e);
        }).addTo(map);

        // 深色底图（CartoDB Dark Matter）
        tileLayers.dark = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                maxZoom: 20,
                crossOrigin: 'anonymous'
            }
        );

        console.log('Tile layers initialized');
        console.log('Map container size:', map.getSize());
    }

    /**
     * 设置深色模式
     * @param {boolean} isDark - 是否深色模式
     */
    function setDarkMode(isDark) {
        if (!map || !tileLayers.light || !tileLayers.dark) {
            return;
        }

        if (isDark && currentBaseMap !== 'dark') {
            // 切换到深色底图
            map.removeLayer(tileLayers.light);
            tileLayers.dark.addTo(map);
            currentBaseMap = 'dark';
            document.body.classList.add('dark-map');
        } else if (!isDark && currentBaseMap !== 'light') {
            // 切换到浅色底图
            map.removeLayer(tileLayers.dark);
            tileLayers.light.addTo(map);
            currentBaseMap = 'light';
            document.body.classList.remove('dark-map');
        }
    }

    /**
     * 获取地图实例
     * @returns {Map} Leaflet 地图实例
     */
    function getMap() {
        return map;
    }

    /**
     * 获取当前底图类型
     * @returns {string} 'light' 或 'dark'
     */
    function getCurrentBaseMap() {
        return currentBaseMap;
    }

    /**
     * 设置地图视图
     * @param {Array} center - 中心坐标 [lat, lng]
     * @param {number} zoom - 缩放级别
     */
    function setView(center, zoom) {
        if (map) {
            map.setView(center, zoom);
        }
    }

    /**
     * 飞往指定位置
     * @param {Array} center - 中心坐标 [lat, lng]
     * @param {number} zoom - 缩放级别
     * @param {number} duration - 动画时长 (ms)
     */
    function flyTo(center, zoom, duration = 1500) {
        if (map) {
            map.flyTo(center, zoom, { duration });
        }
    }

    /**
     * 添加 GeoJSON 图层
     * @param {Object} geojson - GeoJSON 数据
     * @param {Object} options - Leaflet GeoJSON 选项
     * @returns {LayerGroup} 图层组
     */
    function addGeoJSON(geojson, options = {}) {
        if (!map) {
            console.warn('Map not initialized');
            return null;
        }

        const layer = L.geoJSON(geojson, {
            style: options.style || defaultLineStyle,
            onEachFeature: options.onEachFeature,
            pointToLayer: options.pointToLayer || defaultPointToLayer
        });

        if (options.addToMap !== false) {
            layer.addTo(map);
        }

        return layer;
    }

    /**
     * 默认线样式
     * @param {Object} feature - GeoJSON 特征
     * @returns {Object} 线样式对象
     */
    function defaultLineStyle(feature) {
        return {
            color: '#3182bd',
            weight: 4,
            opacity: 0.8
        };
    }

    /**
     * 默认点转换函数
     * @param {Object} latlng - 经纬度对象
     * @param {Object} feature - GeoJSON 特征
     * @returns {Marker} 标记
     */
    function defaultPointToLayer(latlng, feature) {
        return L.marker(latlng, { icon: defaultIcon });
    }

    /**
     * 清空所有图层（保留底图）
     * @param {string} layerGroupId - 要清空的图层组 ID
     */
    function clearLayers(layerGroupId) {
        if (!map) return;

        // 清除指定图层组的图层
        if (layerGroupId && map[layerGroupId]) {
            map.removeLayer(map[layerGroupId]);
        }
    }

    /**
     * 添加事件监听器
     * @param {string} event - 事件名称
     * @param {Function} handler - 处理函数
     */
    function on(event, handler) {
        if (map) {
            map.on(event, handler);
        }
    }

    /**
     * 移除事件监听器
     * @param {string} event - 事件名称
     * @param {Function} handler - 处理函数
     */
    function off(event, handler) {
        if (map) {
            map.off(event, handler);
        }
    }

    /**
     * 获取地图边界
     * @returns {Object} 边界对象
     */
    function getBounds() {
        if (map) {
            return map.getBounds();
        }
        return null;
    }

    /**
     * 销毁地图
     */
    function destroy() {
        if (map) {
            map.remove();
            map = null;
        }
    }

    // 导出公共 API
    return {
        init,
        setDarkMode,
        getMap,
        getCurrentBaseMap,
        setView,
        flyTo,
        addGeoJSON,
        clearLayers,
        on,
        off,
        getBounds,
        destroy
    };
})();

// 挂载到 window 对象（确保全局可访问）
window.MapManager = MapManager;

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapManager;
}
