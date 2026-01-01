/**
 * 悬浮提示框组件
 * Singapore Transit Visualization System
 */

const Tooltip = (function() {
    'use strict';

    // 提示框元素
    let tooltip = null;

    // 偏移量
    const offset = { x: 15, y: 15 };

    // 延迟显示定时器
    let showTimer = null;

    // 延迟隐藏定时器
    let hideTimer = null;

    // 当前显示的内容
    let currentContent = null;

    // 是否已初始化
    let initialized = false;

    /**
     * 初始化提示框
     */
    function init() {
        if (initialized) return;

        tooltip = Helpers.$('#tooltip');
        if (!tooltip) {
            console.warn('Tooltip element not found');
            return;
        }

        // 绑定事件
        bindEvents();

        initialized = true;
    }

    /**
     * 绑定事件
     */
    function bindEvents() {
        // 鼠标移动事件
        document.addEventListener('mousemove', onMouseMove, { passive: true });

        // 触摸移动事件（移动端）
        document.addEventListener('touchmove', onTouchMove, { passive: true });
    }

    /**
     * 鼠标移动处理
     * @param {Event} e - 鼠标事件
     */
    function onMouseMove(e) {
        if (currentContent && isVisible()) {
            const x = e.clientX + offset.x;
            const y = e.clientY + offset.y;

            // 防止超出屏幕
            const rect = tooltip.getBoundingClientRect();
            const maxX = window.innerWidth - rect.width - 10;
            const maxY = window.innerHeight - rect.height - 10;

            tooltip.style.left = `${Math.min(x, maxX)}px`;
            tooltip.style.top = `${Math.min(y, maxY)}px`;
        }
    }

    /**
     * 触摸移动处理
     * @param {Event} e - 触摸事件
     */
    function onTouchMove(e) {
        if (currentContent && isVisible()) {
            const touch = e.touches[0];
            const x = touch.clientX + offset.x;
            const y = touch.clientY + offset.y;

            tooltip.style.left = `${x}px`;
            tooltip.style.top = `${y}px`;
        }
    }

    /**
     * 显示提示框
     * @param {string} routeName - 线路名称
     * @param {Object} flowData - 客流数据（可选）
     * @param {number} delay - 延迟显示时间 (ms)
     */
    function show(routeName, flowData = null, delay = 300) {
        // 清除隐藏定时器
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }

        // 设置延迟显示
        if (showTimer) {
            clearTimeout(showTimer);
        }

        if (delay === 0) {
            doShow(routeName, flowData);
        } else {
            showTimer = setTimeout(() => {
                doShow(routeName, flowData);
            }, delay);
        }
    }

    /**
     * 执行显示
     * @param {string} routeName - 线路名称
     * @param {Object} flowData - 客流数据
     */
    function doShow(routeName, flowData) {
        if (!tooltip) return;

        // 构建内容
        let content = `<strong>${routeName}</strong>`;

        if (flowData) {
            const typeNames = {
                mrt: '地铁',
                lrt: '轻轨',
                bus: '公交'
            };

            content += `<span>${typeNames[flowData.type] || flowData.type} · `;
            content += `客流: ${Helpers.formatFlow(flowData.flow)} · `;

            if (flowData.utilization !== undefined) {
                const color = ColorScale.getUtilizationColor(flowData.utilization);
                content += `<span style="color: ${color}">`;
                content += `${Helpers.formatPercent(flowData.utilization)}</span>`;
            }

            content += '</span>';
        }

        // 设置内容
        Helpers.setHTML('#tooltip .tooltip-content', content);
        currentContent = content;

        // 显示
        tooltip.classList.remove('hidden');

        // 触发显示事件
        tooltip.dispatchEvent(new CustomEvent('tooltipshow', {
            detail: { routeName, flowData }
        }));
    }

    /**
     * 隐藏提示框
     * @param {number} delay - 延迟隐藏时间 (ms)
     */
    function hide(delay = 100) {
        // 清除显示定时器
        if (showTimer) {
            clearTimeout(showTimer);
            showTimer = null;
        }

        // 设置延迟隐藏
        if (hideTimer) {
            clearTimeout(hideTimer);
        }

        hideTimer = setTimeout(() => {
            doHide();
        }, delay);
    }

    /**
     * 执行隐藏
     */
    function doHide() {
        if (!tooltip) return;

        tooltip.classList.add('hidden');
        currentContent = null;

        // 触发隐藏事件
        tooltip.dispatchEvent(new CustomEvent('tooltiphide'));
    }

    /**
     * 立即隐藏（无延迟）
     */
    function hideNow() {
        if (showTimer) {
            clearTimeout(showTimer);
            showTimer = null;
        }
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        doHide();
    }

    /**
     * 更新内容
     * @param {string} routeName - 线路名称
     * @param {Object} flowData - 客流数据
     */
    function update(routeName, flowData) {
        if (isVisible()) {
            doShow(routeName, flowData);
        }
    }

    /**
     * 设置位置
     * @param {number} x - X 坐标
     * @param {number} y - Y 坐标
     */
    function setPosition(x, y) {
        if (tooltip) {
            tooltip.style.left = `${x}px`;
            tooltip.style.top = `${y}px`;
        }
    }

    /**
     * 设置偏移量
     * @param {number} x - X 偏移
     * @param {number} y - Y 偏移
     */
    function setOffset(x, y) {
        offset.x = x;
        offset.y = y;
    }

    /**
     * 检查是否可见
     * @returns {boolean} 是否可见
     */
    function isVisible() {
        return tooltip && !tooltip.classList.contains('hidden');
    }

    /**
     * 获取当前内容
     * @returns {string} 当前内容
     */
    function getContent() {
        return currentContent;
    }

    /**
     * 启用跟随鼠标模式
     */
    function enableFollowMouse() {
        document.addEventListener('mousemove', onMouseMove, { passive: true });
    }

    /**
     * 禁用跟随鼠标模式
     */
    function disableFollowMouse() {
        document.removeEventListener('mousemove', onMouseMove);
    }

    /**
     * 为元素绑定提示
     * @param {Element} element - DOM 元素
     * @param {Function} contentGetter - 内容获取函数
     */
    function bindTo(element, contentGetter) {
        if (!element) return;

        element.addEventListener('mouseenter', function() {
            const content = contentGetter();
            if (content) {
                show(content.name, content.flow);
            }
        });

        element.addEventListener('mouseleave', function() {
            hide();
        });

        element.addEventListener('mousemove', function(e) {
            // 更新位置
            const x = e.clientX + offset.x;
            const y = e.clientY + offset.y;
            tooltip.style.left = `${x}px`;
            tooltip.style.top = `${y}px`;
        });
    }

    /**
     * 为 Leaflet 图层绑定提示
     * @param {Layer} layer - Leaflet 图层
     * @param {string} routeName - 线路名称
     */
    function bindToLeafletLayer(layer, routeName) {
        if (!layer) return;

        layer.on('mouseover', function(e) {
            // 获取客流数据
            const flowData = FlowRenderer?.getRouteFlow(routeName);
            show(routeName, flowData, 0);
        });

        layer.on('mouseout', function() {
            hide(0);
        });
    }

    /**
     * 销毁提示框
     */
    function destroy() {
        hideNow();
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('touchmove', onTouchMove);
        initialized = false;
    }

    // 导出公共 API
    return {
        init,
        show,
        hide,
        hideNow,
        update,
        setPosition,
        setOffset,
        isVisible,
        getContent,
        enableFollowMouse,
        disableFollowMouse,
        bindTo,
        bindToLeafletLayer,
        destroy
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Tooltip;
}
