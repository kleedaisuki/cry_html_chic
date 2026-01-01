/**
 * 时间轴组件
 * Singapore Transit Visualization System
 */

const Timeline = (function() {
    'use strict';

    // DOM 容器
    let container = null;

    // SVG 元素
    let svg = null;

    // 时间戳列表
    let timestamps = [];

    // 当前时间
    let currentTime = null;

    // 当前视图范围
    let viewExtent = null;

    // 比例尺
    let xScale = null;

    // 回调函数
    let callbacks = {
        onTimeChange: null
    };

    // 刷子选择器
    let brush = null;

    // D3 选择集
    let gx = null;
    let currentLine = null;

    // 尺寸配置
    const margin = { top: 5, right: 30, bottom: 20, left: 30 };
    let width = 0;
    let height = 0;

    /**
     * 初始化时间轴
     * @param {string|Element} selector - 容器选择器或元素
     * @param {string[]} timeStamps - 时间戳列表
     * @param {Object} options - 选项
     */
    function init(selector, timeStamps, options = {}) {
        container = typeof selector === 'string'
            ? document.querySelector(selector)
            : selector;

        if (!container) {
            console.error('Timeline container not found');
            return;
        }

        // 保存配置
        timestamps = timeStamps || [];
        callbacks = { ...callbacks, ...options };

        // 设置容器尺寸
        setupDimensions();

        // 创建 SVG
        createSVG();

        // 创建比例尺
        createScales();

        // 绘制坐标轴
        drawAxis();

        // 创建刷子/选择器
        createBrush();

        // 创建当前时间指示器
        createCurrentTimeIndicator();

        // 初始化视图范围
        if (timestamps.length > 0) {
            // 默认显示所有时间
            setViewExtent([timestamps[0], timestamps[timestamps.length - 1]]);
        }

        // 绑定事件
        bindEvents();
    }

    /**
     * 设置尺寸
     */
    function setupDimensions() {
        const rect = container.getBoundingClientRect();
        width = rect.width - margin.left - margin.right;
        height = rect.height - margin.top - margin.bottom;
    }

    /**
     * 创建 SVG
     */
    function createSVG() {
        // 清空容器
        container.innerHTML = '';

        svg = d3.select(container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // 添加背景
        g.append('rect')
            .attr('class', 'timeline-bg')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'var(--bg-secondary)')
            .attr('rx', 4);

        // 创建坐标轴组
        gx = g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${height})`);

        // 创建刷子组
        const brushG = g.append('g')
            .attr('class', 'brush');
    }

    /**
     * 创建比例尺
     */
    function createScales() {
        if (timestamps.length === 0) return;

        // 解析时间戳为日期
        const parseTime = (ts) => {
            // 支持 "2024-01-01T08" 和 "2024-01-01T08:00:00" 格式
            const str = ts.includes(':') ? ts : ts + ':00:00';
            return dayjs(str).toDate();
        };

        const extent = d3.extent(timestamps, parseTime);

        xScale = d3.scaleTime()
            .domain(extent)
            .range([0, width]);
    }

    /**
     * 绘制坐标轴
     */
    function drawAxis() {
        if (!xScale) return;

        const axis = d3.axisBottom(xScale)
            .ticks(8)
            .tickFormat(d => {
                const h = d.getHours();
                return h < 10 ? `0${h}:00` : `${h}:00`;
            });

        gx.call(axis);
    }

    /**
     * 创建刷子选择器
     */
    function createBrush() {
        if (!xScale) return;

        brush = d3.brushX()
            .extent([[0, 0], [width, height]])
            .on('brush end', brushed);

        const brushG = svg.select('.brush');
        brushG.call(brush);

        // 默认选择整个范围
        brushG.call(brush.move, [0, width]);
    }

    /**
     * 创建当前时间指示器
     */
    function createCurrentTimeIndicator() {
        const g = svg.select('g');
        const parseTime = (ts) => {
            const str = ts.includes(':') ? ts : ts + ':00:00';
            return dayjs(str).toDate();
        };

        if (timestamps.length > 0 && currentTime) {
            currentLine = g.append('line')
                .attr('class', 'current-time-line')
                .attr('y1', 0)
                .attr('y2', height)
                .attr('x1', xScale(parseTime(currentTime)))
                .attr('x2', xScale(parseTime(currentTime)));
        } else {
            currentLine = g.append('line')
                .attr('class', 'current-time-line')
                .attr('y1', 0)
                .attr('y2', height)
                .attr('x1', 0)
                .attr('x2', 0)
                .style('opacity', 0);
        }
    }

    /**
     * 刷子事件处理
     */
    function brushed(event) {
        if (!event.selection) return;

        const [x0, x1] = event.selection;
        const date0 = xScale.invert(x0);
        const date1 = xScale.invert(x1);

        // 更新视图范围
        const startTs = formatTimestamp(date0);
        const endTs = formatTimestamp(date1);

        viewExtent = [startTs, endTs];

        // 调用回调
        if (callbacks.onTimeChange) {
            const selectedTime = formatTimestamp(date0);
            callbacks.onTimeChange(selectedTime);
        }

        // 更新当前时间指示器
        setCurrentTime(formatTimestamp(date0));
    }

    /**
     * 格式化时间戳
     * @param {Date} date - 日期对象
     * @returns {string} 格式化的时间戳
     */
    function formatTimestamp(date) {
        return dayjs(date).format('YYYY-MM-DDTHH');
    }

    /**
     * 设置当前时间
     * @param {string} timestamp - 时间戳
     */
    function setCurrentTime(timestamp) {
        if (!xScale) return;

        currentTime = timestamp;

        const parseTime = (ts) => {
            const str = ts.includes(':') ? ts : ts + ':00:00';
            return dayjs(str).toDate();
        };

        const x = xScale(parseTime(timestamp));

        if (currentLine) {
            currentLine
                .attr('x1', x)
                .attr('x2', x)
                .style('opacity', 1);
        }
    }

    /**
     * 设置视图范围
     * @param {Array} extent - 视图范围 [start, end]
     */
    function setViewExtent(extent) {
        if (!xScale || !brush) return;

        const parseTime = (ts) => {
            const str = ts.includes(':') ? ts : ts + ':00:00';
            return dayjs(str).toDate();
        };

        const x0 = xScale(parseTime(extent[0]));
        const x1 = xScale(parseTime(extent[1]));

        const brushG = svg.select('.brush');
        brushG.call(brush.move, [x0, x1]);

        viewExtent = extent;
    }

    /**
     * 获取时间戳列表
     * @returns {string[]} 时间戳列表
     */
    function getTimestamps() {
        return [...timestamps];
    }

    /**
     * 获取当前时间
     * @returns {string} 当前时间戳
     */
    function getCurrentTime() {
        return currentTime;
    }

    /**
     * 跳转到指定时间
     * @param {string} timestamp - 时间戳
     */
    function jumpTo(timestamp) {
        if (!timestamps.includes(timestamp)) {
            // 找到最接近的时间
            const index = findClosestTimestampIndex(timestamp);
            if (index >= 0) {
                timestamp = timestamps[index];
            } else {
                return;
            }
        }

        setCurrentTime(timestamp);

        // 移动刷子
        if (brush && xScale) {
            const parseTime = (ts) => {
                const str = ts.includes(':') ? ts : ts + ':00:00';
                return dayjs(str).toDate();
            };

            const x = xScale(parseTime(timestamp));
            const brushG = svg.select('.brush');

            // 计算刷子的宽度
            const brushWidth = viewExtent
                ? xScale(parseTime(viewExtent[1])) - xScale(parseTime(viewExtent[0]))
                : width * 0.1;

            brushG.call(brush.move, [x - brushWidth / 2, x + brushWidth / 2]);
        }

        // 调用回调
        if (callbacks.onTimeChange) {
            callbacks.onTimeChange(timestamp);
        }
    }

    /**
     * 找到最接近的时间戳索引
     * @param {string} timestamp - 目标时间戳
     * @returns {number} 索引
     */
    function findClosestTimestampIndex(timestamp) {
        if (timestamps.length === 0) return -1;

        const target = dayjs(timestamp);

        let closestIndex = 0;
        let minDiff = Infinity;

        timestamps.forEach((ts, index) => {
            const diff = Math.abs(dayjs(ts).diff(target, 'hour'));
            if (diff < minDiff) {
                minDiff = diff;
                closestIndex = index;
            }
        });

        return closestIndex;
    }

    /**
     * 获取当前时间索引
     * @returns {number} 当前时间在数组中的索引
     */
    function getCurrentIndex() {
        if (!currentTime) return -1;
        return timestamps.indexOf(currentTime);
    }

    /**
     * 设置播放状态样式
     * @param {boolean} isPlaying - 是否正在播放
     */
    function setPlaying(isPlaying) {
        const container = Helpers.$('#timeline-container');
        if (container) {
            if (isPlaying) {
                container.classList.add('playing');
            } else {
                container.classList.remove('playing');
            }
        }
    }

    /**
     * 绑定事件
     */
    function bindEvents() {
        // 响应式调整
        window.addEventListener('resize', debouncedResize);
    }

    /**
     * 防抖调整大小
     */
    function debouncedResize() {
        clearTimeout(window._resizeTimer);
        window._resizeTimer = setTimeout(() => {
            if (container) {
                const oldWidth = width;
                setupDimensions();

                if (oldWidth !== width) {
                    // 重新创建 SVG
                    createSVG();
                    createScales();
                    drawAxis();
                    createBrush();
                    createCurrentTimeIndicator();

                    if (currentTime) {
                        setCurrentTime(currentTime);
                    }

                    if (viewExtent) {
                        setViewExtent(viewExtent);
                    }
                }
            }
        }, 250);
    }

    /**
     * 销毁时间轴
     */
    function destroy() {
        if (container) {
            container.innerHTML = '';
        }
        svg = null;
        timestamps = [];
        currentTime = null;
    }

    // 导出公共 API
    return {
        init,
        setCurrentTime,
        setViewExtent,
        getTimestamps,
        getCurrentTime,
        getCurrentIndex,
        jumpTo,
        findClosestTimestampIndex,
        setPlaying,
        destroy
    };
})();

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Timeline;
}
