/**
 * 工具函数集合
 * Singapore Transit Visualization System
 */

const Helpers = (function() {
    'use strict';

    /**
     * 格式化数字（添加千位分隔符）
     * @param {number} num - 数字
     * @returns {string} 格式化后的字符串
     */
    function formatNumber(num) {
        if (num === null || num === undefined) return '-';
        return num.toLocaleString('en-US');
    }

    /**
     * 格式化客流量
     * @param {number} flow - 客流量
     * @returns {string} 格式化后的客流量字符串
     */
    function formatFlow(flow) {
        if (flow === null || flow === undefined) return '-';
        return formatNumber(Math.round(flow));
    }

    /**
     * 格式化百分比
     * @param {number} value - 值 (0-1)
     * @param {number} decimals - 小数位数
     * @returns {string} 格式化后的百分比字符串
     */
    function formatPercent(value, decimals = 1) {
        if (value === null || value === undefined) return '-';
        return (value * 100).toFixed(decimals) + '%';
    }

    /**
     * 格式化时间（小时:分钟）
     * @param {string} timestamp - ISO 时间戳或复合键格式
     * @returns {string} 格式化的时间字符串
     */
    function formatTime(timestamp) {
        if (!timestamp) return '--:--';

        // 新格式: "2025-11|WEEKDAY|08" -> "08:00"
        if (timestamp.includes('|')) {
            const parts = timestamp.split('|');
            if (parts.length >= 3) {
                const hour = parts[2].padStart(2, '0');
                return `${hour}:00`;
            }
            return timestamp;
        }

        // 传统格式: "2024-01-01T08" 或 "2024-01-01T08:30:00"
        const match = timestamp.match(/T(\d{2})(?::(\d{2}))?/);
        if (match) {
            const hour = match[1];
            const minute = match[2] || '00';
            return `${hour}:${minute}`;
        }
        return timestamp;
    }

    /**
     * 格式化完整日期时间
     * @param {string} timestamp - ISO 时间戳或复合键格式
     * @returns {string} 格式化的日期时间字符串
     */
    function formatDateTime(timestamp) {
        if (!timestamp) return '-';

        // 新格式: "2025-11|WEEKDAY|08" -> "2025-11 WEEKDAY 08:00"
        if (timestamp.includes('|')) {
            const parts = timestamp.split('|');
            const yearMonth = parts[0];
            const dayType = parts[1];
            const timePart = formatTime(timestamp);
            return `${yearMonth} ${dayType} ${timePart}`;
        }

        // 传统格式
        const datePart = timestamp.split('T')[0];
        const timePart = formatTime(timestamp);
        return `${datePart} ${timePart}`;
    }

    /**
     * 获取 DOM 元素
     * @param {string} selector - CSS 选择器
     * @returns {Element|null} DOM 元素
     */
    function $(selector) {
        return document.querySelector(selector);
    }

    /**
     * 获取所有匹配的 DOM 元素
     * @param {string} selector - CSS 选择器
     * @returns {NodeList} DOM 元素列表
     */
    function $$(selector) {
        return document.querySelectorAll(selector);
    }

    /**
     * 添加事件监听器
     * @param {Element} element - DOM 元素
     * @param {string} event - 事件名称
     * @param {Function} handler - 事件处理函数
     * @param {boolean} passive - 是否使用被动模式
     */
    function on(element, event, handler, passive = false) {
        if (element) {
            element.addEventListener(event, handler, { passive });
        }
    }

    /**
     * 移除事件监听器
     * @param {Element} element - DOM 元素
     * @param {string} event - 事件名称
     * @param {Function} handler - 事件处理函数
     */
    function off(element, event, handler) {
        if (element) {
            element.removeEventListener(event, handler);
        }
    }

    /**
     * 显示元素
     * @param {Element} element - DOM 元素
     */
    function show(element) {
        if (element) {
            element.classList.remove('hidden');
        }
    }

    /**
     * 隐藏元素
     * @param {Element} element - DOM 元素
     */
    function hide(element) {
        if (element) {
            element.classList.add('hidden');
        }
    }

    /**
     * 切换元素显示状态
     * @param {Element} element - DOM 元素
     * @returns {boolean} 切换后的显示状态
     */
    function toggle(element) {
        if (element) {
            const isHidden = element.classList.toggle('hidden');
            return !isHidden;
        }
        return false;
    }

    /**
     * 设置元素文本内容
     * @param {Element|string} element - DOM 元素或选择器
     * @param {string} text - 文本内容
     */
    function setText(element, text) {
        const el = typeof element === 'string' ? $(element) : element;
        if (el) {
            el.textContent = text || '-';
        }
    }

    /**
     * 设置元素 HTML 内容
     * @param {Element|string} element - DOM 元素或选择器
     * @param {string} html - HTML 内容
     */
    function setHTML(element, html) {
        const el = typeof element === 'string' ? $(element) : element;
        if (el) {
            el.innerHTML = html;
        }
    }

    /**
     * 防抖函数
     * @param {Function} func - 要防抖的函数
     * @param {number} wait - 等待时间 (ms)
     * @returns {Function} 防抖后的函数
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 节流函数
     * @param {Function} func - 要节流的函数
     * @param {number} limit - 时间限制 (ms)
     * @returns {Function} 节流后的函数
     */
    function throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 深度克隆对象
     * @param {Object} obj - 要克隆的对象
     * @returns {Object} 克隆后的对象
     */
    function deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    }

    /**
     * 从对象数组中查找匹配项
     * @param {Array} array - 对象数组
     * @param {string} key - 要匹配的键
     * @param {*} value - 要匹配的值
     * @returns {*} 找到的项或 undefined
     */
    function findByKey(array, key, value) {
        return array.find(item => item[key] === value);
    }

    /**
     * 按键分组对象数组
     * @param {Array} array - 对象数组
     * @param {string} key - 分组键
     * @returns {Object} 分组后的对象
     */
    function groupBy(array, key) {
        return array.reduce((groups, item) => {
            const value = item[key];
            groups[value] = groups[value] || [];
            groups[value].push(item);
            return groups;
        }, {});
    }

    /**
     * 加载脚本
     * @param {string} src - 脚本 URL
     * @returns {Promise} Promise 对象
     */
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * 加载 JSON 数据
     * @param {string} url - JSON 文件 URL
     * @returns {Promise} Promise 对象
     */
    async function loadJSON(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to load ${url}: ${response.status}`);
        }
        return response.json();
    }

    /**
     * 加载 JS 常量文件
     * @param {string} url - JS 文件 URL
     * @returns {Promise} Promise 对象
     */
    async function loadJSConstant(url) {
        try {
            // 使用 fetch 替代动态 script 标签加载（兼容 file:// 协议）
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to load ${url}: ${response.status}`);
            }
            const text = await response.text();
            // 执行脚本内容
            eval(text);
            // 提取变量名
            const match = url.match(/([^\/]+)\.js$/);
            if (match) {
                const varName = match[1].replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
                // 尝试从各种可能的变量名获取数据
                const possibleNames = [
                    varName,
                    varName.replace(/([A-Z])/g, '_$1').toUpperCase(),
                    'POPULATION_HEATMAP',
                    'PASSENGER_FLOW',
                    'DATA'
                ];
                for (const name of possibleNames) {
                    if (window[name] !== undefined) {
                        console.log(`loadJSConstant: found ${name} in window`);
                        return window[name];
                    }
                }
            }
            console.warn('loadJSConstant: data not found in window for', url);
            return null;
        } catch (error) {
            console.error('loadJSConstant error:', error);
            throw error;
        }
    }

    /**
     * 获取颜色（带透明度）
     * @param {string} color - 颜色值
     * @param {number} alpha - 透明度 (0-1)
     * @returns {string} RGBA 颜色值
     */
    function withAlpha(color, alpha) {
        // 如果已经是 rgba 格式，直接返回
        if (color.startsWith('rgba')) return color;
        // 如果是 hex 格式，转换为 rgba
        if (color.startsWith('#')) {
            const hex = color.slice(1);
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return color;
    }

    /**
     * 颜色亮度判断（返回适合暗色还是亮色文字）
     * @param {string} color - 颜色值
     * @returns {string} 'light' 或 'dark'
     */
    function getTextColorForBackground(color) {
        if (color.startsWith('#')) {
            const hex = color.slice(1);
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            return luminance > 0.5 ? 'dark' : 'light';
        }
        return 'dark';
    }

    // 导出公共 API
    return {
        formatNumber,
        formatFlow,
        formatPercent,
        formatTime,
        formatDateTime,
        $,
        $$,
        on,
        off,
        show,
        hide,
        toggle,
        setText,
        setHTML,
        debounce,
        throttle,
        deepClone,
        findByKey,
        groupBy,
        loadScript,
        loadJSON,
        loadJSConstant,
        withAlpha,
        getTextColorForBackground
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Helpers;
}
