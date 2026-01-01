/**
 * 全局配置文件
 * Singapore Transit Visualization System
 */

const CONFIG = {
    // 应用配置
    app: {
        name: '新加坡公共交通客流可视化',
        version: '1.0.0'
    },

    // 地图配置
    map: {
        center: [1.3521, 103.8198], // 新加坡中心坐标
        zoom: 12,
        minZoom: 10,
        maxZoom: 18
    },

    // 交通类型配置
    transportTypes: {
        mrt: {
            name: '地铁 (MRT)',
            colorScale: 'Blues',
            flowRange: [0, 12000],
            colorRange: ['#deebf7', '#08519c']
        },
        lrt: {
            name: '轻轨 (LRT)',
            colorScale: 'Greens',
            flowRange: [0, 3500],
            colorRange: ['#e5f5e0', '#006d2c']
        },
        bus: {
            name: '公交 (Bus)',
            colorScale: 'Oranges',
            flowRange: [0, 800],
            colorRange: ['#fee5d9', '#a50f15']
        }
    },

    // 时间轴配置
    timeline: {
        // 默认时间范围（会被数据覆盖）
        startHour: 6,  // 6:00
        endHour: 24,   // 24:00
        playInterval: 1000, // 播放间隔 (ms)
        defaultSpeed: 1     // 默认播放速度
    },

    // 主题配置
    theme: {
        default: 'light',
        storageKey: 'transit-theme'
    },

    // 数据配置
    data: {
        // 数据目录路径（相对于 index.html）
        basePath: '../../data/preprocessed',
        // 数据文件列表
        files: [
            'passenger_flow.js',
            'routes.js'
        ],
        // 数据加载超时时间 (ms)
        timeout: 30000
    }
};

// 导出配置
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
