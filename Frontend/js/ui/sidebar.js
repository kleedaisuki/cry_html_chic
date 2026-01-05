/**
 * 侧边栏组件
 * Singapore Transit Visualization System
 */

const Sidebar = (function() {
    'use strict';

    // 侧边栏元素
    let sidebar = null;

    // 是否已初始化
    let initialized = false;

    /**
     * 初始化侧边栏
     */
    function init() {
        if (initialized) return;

        sidebar = Helpers.$('#sidebar');
        if (!sidebar) {
            console.warn('Sidebar not found');
            return;
        }

        // 初始化关闭按钮
        initCloseButton();

        // 初始化动画
        initAnimations();

        initialized = true;
    }

    /**
     * 初始化关闭按钮
     */
    function initCloseButton() {
        const closeBtn = Helpers.$('#sidebar-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                close();
            });
        }

        // ESC 键关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                close();
            }
        });
    }

    /**
     * 初始化动画
     */
    function initAnimations() {
        sidebar.addEventListener('transitionend', function(e) {
            if (e.propertyName === 'transform') {
                // 动画完成后的处理
            }
        });
    }

    /**
     * 打开侧边栏
     */
    function open() {
        if (sidebar) {
            sidebar.classList.remove('hidden');
        }
    }

    /**
     * 关闭侧边栏
     */
    function close() {
        if (sidebar) {
            sidebar.classList.add('hidden');
        }

        // 清除选中状态
        if (window.FlowRenderer) {
            FlowRenderer.clearHighlight();
        }
    }

    /**
     * 切换侧边栏
     */
    function toggle() {
        if (sidebar) {
            if (sidebar.classList.contains('hidden')) {
                open();
            } else {
                close();
            }
        }
    }

    /**
     * 设置标题
     * @param {string} title - 标题
     */
    function setTitle(title) {
        Helpers.setText('#route-name', title);
    }

    /**
     * 设置线路类型
     * @param {string} type - 线路类型
     */
    function setType(type) {
        const typeNames = {
            mrt: '地铁 (MRT)',
            lrt: '轻轨 (LRT)',
            bus: '公交 (Bus)'
        };
        Helpers.setText('#route-type', typeNames[type] || type || '-');
    }

    /**
     * 设置起点
     * @param {string} start - 起点名称
     */
    function setStartStation(start) {
        Helpers.setText('#route-start', start || '-');
    }

    /**
     * 设置终点
     * @param {string} end - 终点名称
     */
    function setEndStation(end) {
        Helpers.setText('#route-end', end || '-');
    }

    /**
     * 设置客流数据
     * @param {Object} flowData - 客流数据
     */
    function setFlowData(flowData) {
        if (flowData) {
            Helpers.setText('#current-flow-value', Helpers.formatFlow(flowData.flow));
            Helpers.setText('#current-capacity', Helpers.formatFlow(flowData.capacity));
            Helpers.setText('#current-utilization', Helpers.formatPercent(flowData.utilization));

            // 根据利用率设置颜色
            const utilEl = Helpers.$('#current-utilization');
            if (utilEl) {
                const color = ColorScale.getUtilizationColor(flowData.utilization);
                utilEl.style.color = color;
            }
        } else {
            Helpers.setText('#current-flow-value', '-');
            Helpers.setText('#current-capacity', '-');
            Helpers.setText('#current-utilization', '-');
        }
    }

    /**
     * 设置站点列表
     * @param {Array} stations - 站点数组
     */
    function setStations(stations) {
        const ul = Helpers.$('#stations-ul');
        if (!ul) return;

        if (!stations || stations.length === 0) {
            ul.innerHTML = '<li style="color: var(--text-secondary);">暂无站点信息</li>';
            return;
        }

        const html = stations.map(s =>
            `<li>${s.name || s}</li>`
        ).join('');

        ul.innerHTML = html;
    }

    /**
     * 填充完整线路信息
     * @param {Object} routeInfo - 线路信息
     * @param {Object} flowData - 客流数据
     */
    function fill(routeInfo, flowData) {
        if (!routeInfo) return;

        setTitle(routeInfo.name || '未知线路');
        setType(routeInfo.type);
        setStartStation(routeInfo.startStation || routeInfo.start || '-');
        setEndStation(routeInfo.endStation || routeInfo.end || '-');
        setFlowData(flowData);
        setStations(routeInfo.stations);

        // 打开侧边栏
        open();
    }

    /**
     * 清空内容
     */
    function clear() {
        setTitle('-');
        setType('-');
        setStartStation('-');
        setEndStation('-');
        setFlowData(null);
        setStations([]);
    }

    /**
     * 检查是否打开
     * @returns {boolean} 是否打开
     */
    function isOpen() {
        return sidebar && !sidebar.classList.contains('hidden');
    }

    /**
     * 设置位置（左侧/右侧）
     * @param {string} side - 'left' 或 'right'
     */
    function setSide(side) {
        if (!sidebar) return;

        if (side === 'left') {
            sidebar.style.right = 'auto';
            sidebar.style.left = '20px';
        } else {
            sidebar.style.left = 'auto';
            sidebar.style.right = '20px';
        }
    }

    /**
     * 设置宽度
     * @param {string} width - 宽度值
     */
    function setWidth(width) {
        if (sidebar) {
            sidebar.style.width = width;
        }
    }

    /**
     * 添加统计卡片
     * @param {string} id - 卡片 ID
     * @param {Object} data - 卡片数据
     */
    function addStatCard(id, data) {
        const container = sidebar.querySelector('.sidebar-content');
        if (!container) return;

        // 检查是否已存在
        if (Helpers.$(`#stat-${id}`)) {
            return;
        }

        const card = document.createElement('div');
        card.id = `stat-${id}`;
        card.className = 'stat-card';
        card.innerHTML = `
            <h3>${data.title}</h3>
            <p><strong>${data.label}:</strong> <span>${data.value}</span></p>
        `;

        // 添加样式
        card.style.cssText = `
            margin-top: 16px;
            padding: 12px;
            background: var(--bg-secondary);
            border-radius: var(--border-radius);
        `;

        container.appendChild(card);
    }

    /**
     * 添加时间序列图表容器
     * @param {string} routeId - 线路 ID
     */
    function addTimeSeriesChart(routeId) {
        const container = sidebar.querySelector('.sidebar-content');
        if (!container) return;

        // 检查是否已存在
        if (Helpers.$('#time-series-chart')) {
            return;
        }

        const chartContainer = document.createElement('div');
        chartContainer.id = 'time-series-chart';
        chartContainer.className = 'chart-container';
        chartContainer.innerHTML = `
            <h3>客流变化趋势</h3>
            <div id="chart-${routeId}" class="mini-chart"></div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .chart-container {
                margin-top: 16px;
                padding: 12px;
                background: var(--bg-secondary);
                border-radius: var(--border-radius);
            }
            .chart-container h3 {
                margin-bottom: 12px;
                font-size: 14px;
            }
            .mini-chart {
                height: 100px;
            }
        `;
        document.head.appendChild(style);

        container.appendChild(chartContainer);
    }

    // 导出公共 API
    return {
        init,
        open,
        close,
        toggle,
        setTitle,
        setType,
        setStartStation,
        setEndStation,
        setFlowData,
        setStations,
        fill,
        clear,
        isOpen,
        setSide,
        setWidth,
        addStatCard,
        addTimeSeriesChart
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Sidebar;
}
