/**
 * 数据加载模块
 * Singapore Transit Visualization System
 */

const API = (function() {
    'use strict';

    // 数据缓存
    let cache = {
        passengerFlow: null,
        routes: null,
        busStops: null,
        populationHeatmap: null,
        timestamps: []
    };

    /**
     * 加载所有数据文件
     * @returns {Promise<Object>} 加载结果
     */
    async function loadAll() {
        showLoading(true);

        try {
            // 并行加载所有数据文件
            const [passengerFlow, routes] = await Promise.all([
                loadPassengerFlow(),
                loadRoutes()
            ]);

            // 处理时间戳列表
            if (passengerFlow && passengerFlow.data) {
                cache.timestamps = Object.keys(passengerFlow.data).sort();
            }

            return {
                success: true,
                passengerFlow,
                routes,
                timestamps: cache.timestamps
            };
        } catch (error) {
            console.error('Failed to load data:', error);
            return {
                success: false,
                error: error.message
            };
        } finally {
            showLoading(false);
        }
    }

    /**
     * 加载客流数据
     * @returns {Promise<Object>} 客流数据
     */
    async function loadPassengerFlow() {
        if (cache.passengerFlow) {
            return cache.passengerFlow;
        }

        try {
            // 尝试加载 passenger_flow.js
            const data = await Helpers.loadJSConstant(`${CONFIG.data.basePath}/passenger_flow.js`);
            cache.passengerFlow = data;
            return data;
        } catch (error) {
            console.warn('Could not load passenger_flow.js:', error);
            // 返回空数据对象，避免后续崩溃
            cache.passengerFlow = {
                ir_kind: 'passenger_flow',
                data: {}
            };
            return cache.passengerFlow;
        }
    }

    /**
     * 加载线路数据
     * @returns {Promise<Object>} 线路数据
     */
    async function loadRoutes() {
        if (cache.routes) {
            return cache.routes;
        }

        try {
            // 尝试加载 routes.js
            const data = await Helpers.loadJSConstant(`${CONFIG.data.basePath}/routes.js`);
            cache.routes = data;
            return data;
        } catch (error) {
            console.warn('Could not load routes.js:', error);
            // 返回空数据对象
            cache.routes = {};
            return cache.routes;
        }
    }

    /**
     * 加载公交站点数据（适配 BusStops 数据集）
     * @returns {Promise<Object>} 站点数据
     */
    async function loadBusStops() {
        if (cache.busStops) {
            return cache.busStops;
        }

        try {
            const data = await Helpers.loadJSConstant(`${CONFIG.data.basePath}/bus_stops.js`);
            cache.busStops = data;
            return data;
        } catch (error) {
            console.warn('Could not load bus_stops.js:', error);
            cache.busStops = {
                ir_kind: 'bus_stops',
                data: { value: [] }
            };
            return cache.busStops;
        }
    }

    /**
     * 获取所有公交站点
     * @returns {Array} 站点数组
     */
    async function getAllBusStops() {
        const data = await loadBusStops();
        if (data && data.data && data.data.value) {
            return data.data.value;
        }
        return [];
    }

    /**
     * 加载人口热力图数据
     * @returns {Promise<Object>} 热力图数据
     */
    async function loadPopulationHeatmap() {
        if (cache.populationHeatmap) {
            return cache.populationHeatmap;
        }

        try {
            const data = await Helpers.loadJSConstant(`${CONFIG.data.basePath}/population_heatmap.js`);
            cache.populationHeatmap = data;
            return data;
        } catch (error) {
            console.warn('Could not load population_heatmap.js:', error);
            cache.populationHeatmap = {
                ir_kind: 'population_heatmap',
                data: { points: [], stats: { count: 0, min: 0, max: 0, sum: 0 } }
            };
            return cache.populationHeatmap;
        }
    }

    /**
     * 获取人口热力图数据点
     * @returns {Array} 热力图数据点数组
     */
    async function getPopulationHeatmapPoints() {
        const data = await loadPopulationHeatmap();
        if (data && data.data && data.data.points) {
            return data.data.points;
        }
        return [];
    }

    /**
     * 获取指定时间点的客流数据
     * @param {string} timestamp - 时间戳
     * @returns {Object|null} 该时间点的客流数据
     */
    async function getFlowAt(timestamp) {
        const data = await loadPassengerFlow();
        if (data && data.data && data.data[timestamp]) {
            return data.data[timestamp];
        }
        return null;
    }

    /**
     * 获取所有时间戳
     * @returns {string[]} 时间戳列表
     */
    async function getTimestamps() {
        if (cache.timestamps.length > 0) {
            return cache.timestamps;
        }

        const data = await loadPassengerFlow();
        if (data && data.data) {
            cache.timestamps = Object.keys(data.data).sort();
        }
        return cache.timestamps;
    }

    /**
     * 获取指定线路的信息
     * @param {string} routeId - 线路 ID
     * @returns {Object|null} 线路信息
     */
    async function getRouteInfo(routeId) {
        const routes = await loadRoutes();
        if (routes && routes[routeId]) {
            return routes[routeId];
        }
        return null;
    }

    /**
     * 获取指定时间点、指定线路的客流数据
     * @param {string} timestamp - 时间戳
     * @param {string} routeId - 线路 ID
     * @returns {Object|null} 客流数据项
     */
    async function getFlowItem(timestamp, routeId) {
        const flowData = await getFlowAt(timestamp);
        if (flowData && flowData.data) {
            return Helpers.findByKey(flowData.data, 'route_id', routeId);
        }
        return null;
    }

    /**
     * 获取指定线路的所有时间点客流数据
     * @param {string} routeId - 线路 ID
     * @returns {Array} 客流数据数组
     */
    async function getRouteFlowHistory(routeId) {
        const timestamps = await getTimestamps();
        const history = [];

        for (const timestamp of timestamps) {
            const item = await getFlowItem(timestamp, routeId);
            if (item) {
                history.push({
                    timestamp,
                    ...item
                });
            }
        }

        return history;
    }

    /**
     * 获取指定时间点的所有线路客流数据
     * @param {string} timestamp - 时间戳
     * @param {string[]} types - 可选的交通类型过滤
     * @returns {Array} 客流数据数组
     */
    async function getFlowsAt(timestamp, types = null) {
        const flowData = await getFlowAt(timestamp);
        if (!flowData || !flowData.data) {
            return [];
        }

        let flows = flowData.data;

        // 按类型过滤
        if (types && types.length > 0) {
            flows = flows.filter(item => types.includes(item.type));
        }

        return flows;
    }

    /**
     * 清空缓存
     */
    function clearCache() {
        cache = {
            passengerFlow: null,
            routes: null,
            busStops: null,
            populationHeatmap: null,
            timestamps: []
        };
    }

    /**
     * 显示/隐藏加载遮罩
     * @param {boolean} show - 是否显示
     */
    function showLoading(show) {
        const overlay = Helpers.$('#loading-overlay');
        if (overlay) {
            if (show) {
                Helpers.show(overlay);
            } else {
                Helpers.hide(overlay);
            }
        }
    }

    // 导出公共 API
    return {
        loadAll,
        loadPassengerFlow,
        loadRoutes,
        loadBusStops,
        loadPopulationHeatmap,
        getAllBusStops,
        getPopulationHeatmapPoints,
        getFlowAt,
        getTimestamps,
        getRouteInfo,
        getFlowItem,
        getRouteFlowHistory,
        getFlowsAt,
        clearCache
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
