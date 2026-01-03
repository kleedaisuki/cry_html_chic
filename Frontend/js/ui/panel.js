/**
 * 控制面板组件
 * Singapore Transit Visualization System
 */

const Panel = (function() {
    'use strict';

    // 面板元素
    let panel = null;

    // 是否已初始化
    let initialized = false;

    /**
     * 初始化控制面板
     */
    function init() {
        if (initialized) return;

        panel = Helpers.$('#control-panel');
        if (!panel) {
            console.warn('Control panel not found');
            return;
        }

        // 初始化图层控制
        initLayerControls();

        // 初始化拖拽功能
        initDraggable();

        // 初始化收起/展开
        initCollapsible();

        initialized = true;
    }

    /**
     * 初始化图层控制
     */
    function initLayerControls() {
        const toggles = {
            mrt: Helpers.$('#toggle-mrt'),
            lrt: Helpers.$('#toggle-lrt'),
            bus: Helpers.$('#toggle-bus')
        };

        // 恢复保存的状态
        Object.entries(toggles).forEach(([type, toggle]) => {
            if (toggle) {
                const savedState = localStorage.getItem(`layer-${type}`);
                if (savedState !== null) {
                    toggle.checked = savedState === 'true';
                }
            }
        });

        // 绑定事件
        Object.entries(toggles).forEach(([type, toggle]) => {
            if (toggle) {
                toggle.addEventListener('change', function() {
                    // 保存状态
                    localStorage.setItem(`layer-${type}`, this.checked);

                    // 更新全局状态
                    if (window.App && App.state && App.state.activeLayers) {
                        App.state.activeLayers[type] = this.checked;
                    }

                    // 触发自定义事件
                    dispatchLayerChange(type, this.checked);
                });
            }
        });
    }

    /**
     * 初始化拖拽功能
     */
    function initDraggable() {
        const header = panel.querySelector('.panel-section:first-child');
        if (!header) return;

        let isDragging = false;
        let startX, startY, startLeft, startTop;

        header.style.cursor = 'grab';

        header.addEventListener('mousedown', function(e) {
            if (e.target.tagName === 'INPUT') return; // 不在输入框上拖拽

            isDragging = true;
            header.style.cursor = 'grabbing';

            const rect = panel.getBoundingClientRect();
            startX = e.clientX;
            startY = e.clientY;
            startLeft = rect.left;
            startTop = rect.top;

            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            panel.style.left = `${startLeft + dx}px`;
            panel.style.top = `${startTop + dy}px`;
        });

        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                header.style.cursor = 'grab';
            }
        });
    }

    /**
     * 初始化收起/展开
     */
    function initCollapsible() {
        const header = panel.querySelector('.panel-section:first-child');
        if (!header) return;

        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'collapse-btn';
        toggleBtn.innerHTML = '▼';
        toggleBtn.title = '收起/展开';

        const style = document.createElement('style');
        style.textContent = `
            .collapse-btn {
                position: absolute;
                right: 10px;
                top: 12px;
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                font-size: 12px;
                padding: 4px 8px;
            }
            .collapse-btn:hover {
                color: var(--text-primary);
            }
            .control-panel.collapsed .panel-section:not(:first-child) {
                display: none;
            }
        `;
        document.head.appendChild(style);

        header.style.position = 'relative';
        header.appendChild(toggleBtn);

        toggleBtn.addEventListener('click', function() {
            panel.classList.toggle('collapsed');
            this.innerHTML = panel.classList.contains('collapsed') ? '▲' : '▼';
        });
    }

    /**
     * 派发图层变化事件
     * @param {string} type - 图层类型
     * @param {boolean} visible - 是否可见
     */
    function dispatchLayerChange(type, visible) {
        const event = new CustomEvent('layerchange', {
            detail: { type, visible }
        });
        document.dispatchEvent(event);
    }

    /**
     * 显示面板
     */
    function show() {
        if (panel) {
            Helpers.show(panel);
        }
    }

    /**
     * 隐藏面板
     */
    function hide() {
        if (panel) {
            Helpers.hide(panel);
        }
    }

    /**
     * 切换面板显示
     */
    function toggle() {
        if (panel) {
            Helpers.toggle(panel);
        }
    }

    /**
     * 设置图层可见性
     * @param {string} type - 图层类型
     * @param {boolean} visible - 是否可见
     */
    function setLayerVisibility(type, visible) {
        const toggle = Helpers.$(`#toggle-${type}`);
        if (toggle) {
            toggle.checked = visible;
            toggle.dispatchEvent(new Event('change'));
        }
    }

    /**
     * 获取所有图层状态
     * @returns {Object} 图层状态
     */
    function getLayerStates() {
        return {
            mrt: Helpers.$('#toggle-mrt')?.checked ?? true,
            lrt: Helpers.$('#toggle-lrt')?.checked ?? true,
            bus: Helpers.$('#toggle-bus')?.checked ?? true
        };
    }

    /**
     * 更新图例数据
     * @param {Object} data - 图例数据
     */
    function updateLegend(data) {
        // 图例是静态的，这里可以用于动态更新范围
        const legendTexts = Helpers.$$('.legend-text');
        legendTexts.forEach(el => {
            const text = el.textContent;
            if (text.includes('MRT')) {
                el.textContent = `MRT (0-${data.mrt?.max || 12000})`;
            } else if (text.includes('LRT')) {
                el.textContent = `LRT (0-${data.lrt?.max || 3500})`;
            } else if (text.includes('Bus')) {
                el.textContent = `Bus (0-${data.bus?.max || 800})`;
            }
        });
    }

    /**
     * 重置位置
     */
    function resetPosition() {
        if (panel) {
            panel.style.left = '20px';
            panel.style.top = `calc(var(--header-height) + 20px)`;
        }
    }

    // 导出公共 API
    return {
        init,
        show,
        hide,
        toggle,
        setLayerVisibility,
        getLayerStates,
        updateLegend,
        resetPosition
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Panel;
}
