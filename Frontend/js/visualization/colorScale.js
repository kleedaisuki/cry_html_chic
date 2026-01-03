/**
 * 颜色比例尺模块
 * Singapore Transit Visualization System
 */

const ColorScale = (function() {
    'use strict';

    // D3 颜色插值器缓存
    const interpolators = {
        Blues: d3.interpolateBlues,
        Greens: d3.interpolateGreens,
        Oranges: d3.interpolateOranges,
        Reds: d3.interpolateReds,
        Purples: d3.interpolatePurples,
        Greys: d3.interpolateGreys
    };

    // 预计算的颜色查找表（优化性能）
    const colorTables = {
        mrt: {},
        lrt: {},
        bus: {}
    };

    // 颜色表分辨率（每种类型 256 个颜色值）
    const TABLE_SIZE = 256;

    /**
     * 初始化颜色表
     */
    function initColorTables() {
        Object.entries(CONFIG.transportTypes).forEach(([type, config]) => {
            const interpolator = interpolators[config.colorScale];
            if (interpolator) {
                const range = config.flowRange;
                const table = colorTables[type];

                for (let i = 0; i < TABLE_SIZE; i++) {
                    const t = i / (TABLE_SIZE - 1);
                    const flow = range[0] + t * (range[1] - range[0]);
                    table[Math.round(flow)] = interpolator(t);
                }
            }
        });
    }

    /**
     * 获取颜色值
     * @param {number} flow - 客流量
     * @param {string} type - 交通类型 (mrt/lrt/bus)
     * @returns {string} 颜色值 (hex)
     */
    function getColor(flow, type = 'mrt') {
        if (flow === null || flow === undefined) {
            return '#cccccc';
        }

        const typeKey = type.toLowerCase();
        const config = CONFIG.transportTypes[typeKey];
        const interpolator = interpolators[config?.colorScale];

        if (!interpolator) {
            return '#cccccc';
        }

        // 计算归一化值
        const range = config.flowRange;
        let t = (flow - range[0]) / (range[1] - range[0]);

        // 限制范围
        t = Math.max(0, Math.min(1, t));

        return interpolator(t);
    }

    /**
     * 获取颜色（从预计算的查找表）
     * @param {number} flow - 客流量
     * @param {string} type - 交通类型
     * @returns {string} 颜色值
     */
    function getColorFast(flow, type = 'mrt') {
        const typeKey = type.toLowerCase();
        const table = colorTables[typeKey];

        if (!table || Object.keys(table).length === 0) {
            // 初始化查找表
            initColorTables();
            return getColorFast(flow, type);
        }

        // 四舍五入到最近的整数
        const key = Math.round(flow);

        // 查找最近的键
        const keys = Object.keys(table).map(Number).sort((a, b) => a - b);

        // 二分查找或直接查找
        let closestKey = keys[0];
        for (const k of keys) {
            if (Math.abs(k - flow) < Math.abs(closestKey - flow)) {
                closestKey = k;
            }
        }

        return table[closestKey] || getColor(flow, type);
    }

    /**
     * 获取颜色比例尺函数
     * @param {string} type - 交通类型
     * @returns {Function} D3 比例尺函数
     */
    function getScale(type) {
        const typeKey = type.toLowerCase();
        const config = CONFIG.transportTypes[typeKey];

        if (!config) {
            return d3.scaleLinear().domain([0, 1]).range(['#cccccc', '#cccccc']);
        }

        const interpolator = interpolators[config.colorScale];

        return d3.scaleLinear()
            .domain(config.flowRange)
            .range([interpolator(0), interpolator(1)])
            .clamp(true);
    }

    /**
     * 获取颜色数组（用于图例）
     * @param {string} type - 交通类型
     * @param {number} steps - 颜色阶数
     * @returns {Array} 颜色数组
     */
    function getColorSteps(type, steps = 5) {
        const config = CONFIG.transportTypes[type.toLowerCase()];
        const interpolator = interpolators[config.colorScale];

        if (!interpolator) {
            return [];
        }

        const colors = [];
        for (let i = 0; i < steps; i++) {
            colors.push(interpolator(i / (steps - 1)));
        }
        return colors;
    }

    /**
     * 生成图例渐变定义
     * @param {string} type - 交通类型
     * @param {string} gradientId - SVG 渐变 ID
     * @returns {string} SVG 渐变定义字符串
     */
    function getGradientDefinition(type, gradientId) {
        const steps = 10;
        const colors = getColorSteps(type, steps);

        const stops = colors.map((color, i) => {
            const offset = (i / (steps - 1)) * 100;
            return `<stop offset="${offset}%" stop-color="${color}"/>`;
        }).join('');

        return `
            <linearGradient id="${gradientId}" x1="0%" y1="0%" x2="100%" y2="0%">
                ${stops}
            </linearGradient>
        `;
    }

    /**
     * 获取颜色亮度
     * @param {string} color - 颜色值
     * @returns {number} 亮度值 (0-1)
     */
    function getLuminance(color) {
        if (color.startsWith('#')) {
            const hex = color.slice(1);
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        }
        return 0.5;
    }

    /**
     * 获取适合深色/浅色背景的文字颜色
     * @param {string} backgroundColor - 背景颜色
     * @returns {string} 'black' 或 'white'
     */
    function getTextColor(backgroundColor) {
        return getLuminance(backgroundColor) > 0.5 ? '#1a1a1a' : '#ffffff';
    }

    /**
     * 根据利用率获取状态颜色
     * @param {number} utilization - 利用率 (0-1)
     * @returns {string} 颜色值
     */
    function getUtilizationColor(utilization) {
        if (utilization >= 1) {
            return '#dc3545'; // 红色 - 超载
        } else if (utilization >= 0.8) {
            return '#fd7e14'; // 橙色 - 高负载
        } else if (utilization >= 0.6) {
            return '#ffc107'; // 黄色 - 中等负载
        } else {
            return '#28a745'; // 绿色 - 正常
        }
    }

    /**
     * 颜色混合
     * @param {string} color1 - 颜色1
     * @param {string} color2 - 颜色2
     * @param {number} ratio - 混合比例
     * @returns {string} 混合后的颜色
     */
    function mixColors(color1, color2, ratio = 0.5) {
        const c1 = d3.color(color1);
        const c2 = d3.color(color2);
        return d3.interpolateRgb(c1, c2)(ratio);
    }

    /**
     * 获取数值在颜色表中的位置
     * @param {number} value - 数值
     * @param {string} type - 交通类型
     * @returns {number} 位置 (0-1)
     */
    function getPosition(value, type = 'mrt') {
        const config = CONFIG.transportTypes[type.toLowerCase()];
        if (!config) return 0;

        const range = config.flowRange;
        return (value - range[0]) / (range[1] - range[0]);
    }

    // 初始化颜色表
    initColorTables();

    // 导出公共 API
    return {
        getColor,
        getColorFast,
        getScale,
        getColorSteps,
        getGradientDefinition,
        getLuminance,
        getTextColor,
        getUtilizationColor,
        mixColors,
        getPosition
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ColorScale;
}
