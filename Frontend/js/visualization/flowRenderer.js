/**
 * 客流渲染器
 * Singapore Transit Visualization System
 */

const FlowRenderer = (function() {
    'use strict';

    // 当前渲染的数据
    let currentData = [];

    // 是否已初始化
    let initialized = false;

    /**
     * 初始化渲染器
     */
    function init() {
        if (initialized) return;

        // 初始化图层管理器
        if (LayerManager) {
            LayerManager.init();
        }

        initialized = true;
    }

    /**
     * 渲染客流数据
     * @param {Array} flows - 客流数据数组
     */
    function render(flows) {
        if (!initialized) {
            init();
        }

        currentData = flows || [];

        // 更新图层颜色
        if (LayerManager) {
            LayerManager.updateRouteColors(flows);
        }
    }

    /**
     * 渲染单个线路的客流
     * @param {string} routeId - 线路 ID
     * @param {Object} flowData - 客流数据
     */
    function renderRoute(routeId, flowData) {
        if (!flowData || !LayerManager) return;

        const color = ColorScale.getColor(flowData.flow, flowData.type);

        const layer = LayerManager.getRouteLayer(routeId);
        if (layer) {
            layer.eachLayer(function(l) {
                if (l.setStyle) {
                    l.setStyle({
                        color: color,
                        weight: 4,
                        opacity: 0.8
                    });
                }
            });
        }
    }

    /**
     * 批量渲染
     * @param {Array} flowDataList - 客流数据数组
     */
    function renderBatch(flowDataList) {
        flowDataList.forEach(({ route_id, ...flowData }) => {
            renderRoute(route_id, flowData);
        });
    }

    /**
     * 动画过渡到新的客流数据
     * @param {Array} flows - 新客流数据
     * @param {number} duration - 动画时长 (ms)
     */
    function animateTo(flows, duration = 500) {
        if (!initialized) {
            init();
        }

        const oldData = currentData;
        const newData = flows || [];

        // 创建旧数据的映射
        const oldMap = new Map(oldData.map(item => [item.route_id, item]));

        // 逐个更新线路
        newData.forEach(item => {
            const oldItem = oldMap.get(item.route_id);

            if (!oldItem || oldItem.flow !== item.flow) {
                // 颜色变化，使用动画
                animateRouteColor(item.route_id, item, duration);
            } else {
                // 无变化，直接设置
                renderRoute(item.route_id, item);
            }
        });

        currentData = newData;
    }

    /**
     * 动画过渡线路颜色
     * @param {string} routeId - 线路 ID
     * @param {Object} flowData - 客流数据
     * @param {number} duration - 动画时长
     */
    function animateRouteColor(routeId, flowData, duration = 500) {
        const layer = LayerManager?.getRouteLayer(routeId);
        if (!layer) return;

        const startColor = layer.options?.color || '#3182bd';
        const endColor = ColorScale.getColor(flowData.flow, flowData.type);

        const layerGroup = layer;

        // 使用 D3 过渡
        d3.selectAll(layerGroup.getLayers().map(l => l._path))
            .transition()
            .duration(duration)
            .style('stroke', endColor);
    }

    /**
     * 获取当前数据
     * @returns {Array} 当前客流数据
     */
    function getCurrentData() {
        return [...currentData];
    }

    /**
     * 获取指定线路的当前客流
     * @param {string} routeId - 线路 ID
     * @returns {Object|null} 客流数据
     */
    function getRouteFlow(routeId) {
        return currentData.find(item => item.route_id === routeId) || null;
    }

    /**
     * 获取最高客流的线路
     * @param {string} type - 可选的类型过滤
     * @returns {Object|null} 最高客流线路数据
     */
    function getMaxFlowRoute(type = null) {
        let data = currentData;

        if (type) {
            data = data.filter(item => item.type === type);
        }

        if (data.length === 0) return null;

        return data.reduce((max, item) =>
            item.flow > (max?.flow || 0) ? item : max
        , null);
    }

    /**
     * 获取平均客流
     * @param {string} type - 可选的类型过滤
     * @returns {number} 平均客流
     */
    function getAverageFlow(type = null) {
        let data = currentData;

        if (type) {
            data = data.filter(item => item.type === type);
        }

        if (data.length === 0) return 0;

        const total = data.reduce((sum, item) => sum + (item.flow || 0), 0);
        return total / data.length;
    }

    /**
     * 获取总客流
     * @param {string} type - 可选的类型过滤
     * @returns {number} 总客流
     */
    function getTotalFlow(type = null) {
        let data = currentData;

        if (type) {
            data = data.filter(item => item.type === type);
        }

        return data.reduce((sum, item) => sum + (item.flow || 0), 0);
    }

    /**
     * 获取客流统计摘要
     * @returns {Object} 统计摘要
     */
    function getSummary() {
        const mrtFlow = getTotalFlow('mrt');
        const lrtFlow = getTotalFlow('lrt');
        const busFlow = getTotalFlow('bus');

        return {
            mrt: {
                total: mrtFlow,
                count: currentData.filter(d => d.type === 'mrt').length,
                avg: getAverageFlow('mrt'),
                max: getMaxFlowRoute('mrt')
            },
            lrt: {
                total: lrtFlow,
                count: currentData.filter(d => d.type === 'lrt').length,
                avg: getAverageFlow('lrt'),
                max: getMaxFlowRoute('lrt')
            },
            bus: {
                total: busFlow,
                count: currentData.filter(d => d.type === 'bus').length,
                avg: getAverageFlow('bus'),
                max: getMaxFlowRoute('bus')
            },
            all: {
                total: mrtFlow + lrtFlow + busFlow,
                count: currentData.length,
                avg: getAverageFlow()
            }
        };
    }

    /**
     * 清除渲染
     */
    function clear() {
        currentData = [];
        if (LayerManager) {
            LayerManager.clearRoutes();
        }
    }

    /**
     * 设置高亮线路
     * @param {string} routeId - 线路 ID
     */
    function highlightRoute(routeId) {
        if (LayerManager) {
            LayerManager.highlightRoute(routeId);
        }
    }

    /**
     * 清除高亮
     */
    function clearHighlight() {
        if (LayerManager) {
            LayerManager.clearSelection();
        }
    }

    // 导出公共 API
    return {
        init,
        render,
        renderRoute,
        renderBatch,
        animateTo,
        getCurrentData,
        getRouteFlow,
        getMaxFlowRoute,
        getAverageFlow,
        getTotalFlow,
        getSummary,
        clear,
        highlightRoute,
        clearHighlight
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlowRenderer;
}
