/**
 * 图层管理器
 * Singapore Transit Visualization System
 */

const LayerManager = (function() {
    'use strict';

    // 线路图层组
    let routeLayerGroup = null;

    // 站点图层组
    let stationLayerGroup = null;

    // 当前所有线路图层的引用
    let routeLayers = {};

    // 当前选中的线路
    let selectedRouteId = null;

    /**
     * 初始化图层管理器
     */
    function init() {
        // 创建图层组
        routeLayerGroup = L.layerGroup().addTo(MapManager.getMap());
        stationLayerGroup = L.layerGroup().addTo(MapManager.getMap());

        // 绑定线路点击事件
        bindRouteClickEvents();
    }

    /**
     * 绑定线路点击事件
     */
    function bindRouteClickEvents() {
        // 使用 map 的 click 事件来处理
        MapManager.on('click', function(e) {
            // 点击地图本身时的处理
            clearSelection();
        });
    }

    /**
     * 添加线路图层
     * @param {string} routeId - 线路 ID
     * @param {Object} routeInfo - 线路信息
     * @param {Object} geojson - GeoJSON 数据
     * @returns {Layer} 图层
     */
    function addRoute(routeId, routeInfo, geojson) {
        if (!routeLayerGroup || !geojson) {
            return null;
        }

        // 创建样式函数
        const styleFunction = (feature) => {
            const type = feature.properties?.type || routeInfo?.type || 'mrt';
            const config = CONFIG.transportTypes[type] || CONFIG.transportTypes.mrt;
            return {
                color: config.colorRange[0],
                weight: 4,
                opacity: 0.8
            };
        };

        // 创建点击处理函数
        const onEachFeature = (feature, layer) => {
            layer.on('click', function(e) {
                // 阻止事件冒泡到地图
                L.DomEvent.stopPropagation(e);

                // 选中高亮并显示详情
                selectRoute(routeId);

                // 触发自定义事件
                if (window.App) {
                    App.showRouteDetail(routeId);
                }
            });

            layer.on('mouseover', function(e) {
                // 悬浮高亮
                if (routeId !== selectedRouteId) {
                    this.setStyle({
                        weight: 6,
                        opacity: 1
                    });
                }
            });

            layer.on('mouseout', function(e) {
                // 移除悬浮高亮
                if (routeId !== selectedRouteId) {
                    this.setStyle({
                        weight: 4,
                        opacity: 0.8
                    });
                }
            });
        };

        // 创建图层
        const layer = L.geoJSON(geojson, {
            style: styleFunction,
            onEachFeature: onEachFeature
        });

        // 存储引用
        routeLayers[routeId] = {
            layer,
            info: routeInfo
        };

        // 添加到图层组
        layer.addTo(routeLayerGroup);

        return layer;
    }

    /**
     * 添加站点标记
     * @param {Array} stations - 站点数组
     * @returns {Array} 标记数组
     */
    function addStations(stations) {
        if (!stationLayerGroup || !stations) {
            return [];
        }

        const markers = [];

        stations.forEach(station => {
            if (station.position) {
                const marker = L.circleMarker(station.position, {
                    radius: 5,
                    fillColor: '#666',
                    color: '#fff',
                    weight: 1,
                    fillOpacity: 0.8
                });

                marker.bindPopup(`
                    <strong>${station.name}</strong><br>
                    <small>${station.id || ''}</small>
                `);

                marker.addTo(stationLayerGroup);
                markers.push(marker);
            }
        });

        return markers;
    }

    /**
     * 根据客流数据更新线路颜色
     * @param {Array} flowData - 客流数据数组
     */
    function updateRouteColors(flowData) {
        if (!flowData || !routeLayerGroup) {
            return;
        }

        flowData.forEach(item => {
            const route = routeLayers[item.route_id];
            if (route) {
                const config = CONFIG.transportTypes[item.type] || CONFIG.transportTypes.mrt;
                const color = ColorScale.getColor(item.flow, item.type);

                // 更新图层样式
                route.layer.eachLayer(function(layer) {
                    if (layer.setStyle) {
                        layer.setStyle({
                            color: color,
                            weight: selectedRouteId === item.route_id ? 6 : 4,
                            opacity: selectedRouteId === item.route_id ? 1 : 0.8
                        });
                    }
                });
            }
        });
    }

    /**
     * 选中线路
     * @param {string} routeId - 线路 ID
     */
    function selectRoute(routeId) {
        // 清除之前的选中状态
        clearSelection();

        selectedRouteId = routeId;

        const route = routeLayers[routeId];
        if (route) {
            // 高亮选中的线路
            route.layer.eachLayer(function(layer) {
                if (layer.setStyle) {
                    layer.setStyle({
                        weight: 6,
                        opacity: 1
                    });
                }
            });

            // 确保选中的线路在最上层
            route.layer.bringToFront();
        }

        // 降低其他线路的透明度
        Object.entries(routeLayers).forEach(([id, routeData]) => {
            if (id !== routeId) {
                routeData.layer.eachLayer(function(layer) {
                    if (layer.setStyle) {
                        layer.setStyle({
                            opacity: 0.3
                        });
                    }
                });
            }
        });
    }

    /**
     * 清除选中状态
     */
    function clearSelection() {
        if (selectedRouteId) {
            const route = routeLayers[selectedRouteId];
            if (route) {
                route.layer.eachLayer(function(layer) {
                    if (layer.setStyle) {
                        layer.setStyle({
                            weight: 4,
                            opacity: 0.8
                        });
                    }
                });
            }
            selectedRouteId = null;
        }

        // 恢复所有线路的透明度
        Object.values(routeLayers).forEach(routeData => {
            routeData.layer.eachLayer(function(layer) {
                if (layer.setStyle) {
                    layer.setStyle({
                        opacity: 0.8
                    });
                }
            });
        });
    }

    /**
     * 高亮指定线路
     * @param {string} routeId - 线路 ID
     */
    function highlightRoute(routeId) {
        selectRoute(routeId);
    }

    /**
     * 切换图层显示
     * @param {string} type - 交通类型 (mrt/lrt/bus)
     * @param {boolean} visible - 是否显示
     */
    function toggleLayer(type, visible) {
        Object.entries(routeLayers).forEach(([routeId, routeData]) => {
            const routeType = routeData.info?.type || 'mrt';
            if (routeType === type) {
                if (visible) {
                    routeLayerGroup.addLayer(routeData.layer);
                } else {
                    routeLayerGroup.removeLayer(routeData.layer);
                }
            }
        });
    }

    /**
     * 获取线路信息
     * @param {string} routeId - 线路 ID
     * @returns {Object|null} 线路信息
     */
    function getRouteInfo(routeId) {
        return routeLayers[routeId]?.info || null;
    }

    /**
     * 获取所有线路信息
     * @returns {Object} 线路信息对象
     */
    function getAllRoutes() {
        return Object.entries(routeLayers).reduce((acc, [id, data]) => {
            acc[id] = data.info;
            return acc;
        }, {});
    }

    /**
     * 清除所有线路
     */
    function clearRoutes() {
        if (routeLayerGroup) {
            routeLayerGroup.clearLayers();
        }
        routeLayers = {};
        selectedRouteId = null;
    }

    /**
     * 清除所有站点
     */
    function clearStations() {
        if (stationLayerGroup) {
            stationLayerGroup.clearLayers();
        }
    }

    /**
     * 获取线路图层
     * @param {string} routeId - 线路 ID
     * @returns {Layer|null} 图层
     */
    function getRouteLayer(routeId) {
        return routeLayers[routeId]?.layer || null;
    }

    /**
     * 缩放到指定线路
     * @param {string} routeId - 线路 ID
     */
    function fitToRoute(routeId) {
        const route = routeLayers[routeId];
        if (route && route.layer) {
            const map = MapManager.getMap();
            if (map) {
                map.fitBounds(route.layer.getBounds(), {
                    padding: [50, 50]
                });
            }
        }
    }

    // 导出公共 API
    return {
        init,
        addRoute,
        addStations,
        updateRouteColors,
        selectRoute,
        clearSelection,
        highlightRoute,
        toggleLayer,
        getRouteInfo,
        getAllRoutes,
        clearRoutes,
        clearStations,
        getRouteLayer,
        fitToRoute
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LayerManager;
}
