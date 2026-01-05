/**
 * 播放控制器
 * Singapore Transit Visualization System
 */

const Player = (function() {
    'use strict';

    // 时间戳列表
    let timestamps = [];

    // 当前时间索引
    let currentIndex = 0;

    // 播放状态
    let isPlaying = false;

    // 播放定时器
    let timer = null;

    // 播放速度（倍数）
    let speed = CONFIG.timeline.defaultSpeed;

    // 播放间隔（ms）
    let interval = CONFIG.timeline.playInterval;

    // 循环播放
    let loop = true;

    // 回调函数
    let callbacks = {
        onTimeUpdate: null,
        onPlayChange: null
    };

    /**
     * 初始化播放器
     * @param {string[]} timeStamps - 时间戳列表
     * @param {Object} options - 选项
     */
    function init(timeStamps, options = {}) {
        timestamps = timeStamps || [];
        callbacks = { ...callbacks, ...options };

        if (timestamps.length > 0) {
            currentIndex = 0;
        }
    }

    /**
     * 开始播放
     */
    function play() {
        if (isPlaying) return;

        if (timestamps.length === 0) {
            console.warn('No timestamps to play');
            return;
        }

        isPlaying = true;

        // 更新 UI
        updatePlayButton(true);
        Timeline.setPlaying(true);

        // 触发回调
        if (callbacks.onPlayChange) {
            callbacks.onPlayChange(true);
        }

        // 启动定时器
        scheduleNext();
    }

    /**
     * 暂停播放
     */
    function pause() {
        if (!isPlaying) return;

        isPlaying = false;

        // 清除定时器
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }

        // 更新 UI
        updatePlayButton(false);
        Timeline.setPlaying(false);

        // 触发回调
        if (callbacks.onPlayChange) {
            callbacks.onPlayChange(false);
        }
    }

    /**
     * 停止播放
     */
    function stop() {
        pause();

        // 重置到起始位置
        if (timestamps.length > 0) {
            currentIndex = 0;
            const timestamp = timestamps[currentIndex];

            // 更新显示
            Timeline.setCurrentTime(timestamp);

            // 触发回调
            if (callbacks.onTimeUpdate) {
                callbacks.onTimeUpdate(timestamp);
            }
        }
    }

    /**
     * 跳到下一帧
     */
    function next() {
        if (timestamps.length === 0) return -1;

        currentIndex++;

        // 检查是否到达末尾
        if (currentIndex >= timestamps.length) {
            if (loop) {
                currentIndex = 0;
            } else {
                currentIndex = timestamps.length - 1;
                pause();
                return currentIndex;
            }
        }

        const timestamp = timestamps[currentIndex];

        // 更新显示
        Timeline.setCurrentTime(timestamp);

        // 触发回调
        if (callbacks.onTimeUpdate) {
            callbacks.onTimeUpdate(timestamp);
        }

        return currentIndex;
    }

    /**
     * 跳到上一帧
     */
    function prev() {
        if (timestamps.length === 0) return -1;

        currentIndex--;

        // 检查是否到达开头
        if (currentIndex < 0) {
            if (loop) {
                currentIndex = timestamps.length - 1;
            } else {
                currentIndex = 0;
                return currentIndex;
            }
        }

        const timestamp = timestamps[currentIndex];

        // 更新显示
        Timeline.setCurrentTime(timestamp);

        // 触发回调
        if (callbacks.onTimeUpdate) {
            callbacks.onTimeUpdate(timestamp);
        }

        return currentIndex;
    }

    /**
     * 跳转到指定时间
     * @param {string} timestamp - 时间戳
     */
    function jumpTo(timestamp) {
        const index = timestamps.indexOf(timestamp);
        if (index >= 0) {
            currentIndex = index;
            Timeline.setCurrentTime(timestamp);

            if (callbacks.onTimeUpdate) {
                callbacks.onTimeUpdate(timestamp);
            }
        }
    }

    /**
     * 调度下一帧
     */
    function scheduleNext() {
        if (!isPlaying) return;

        // 计算实际间隔（考虑速度）
        const actualInterval = interval / speed;

        timer = setTimeout(() => {
            const nextIndex = next();

            // 检查是否播放完毕（非循环模式）
            if (!isPlaying && nextIndex >= timestamps.length - 1 && !loop) {
                stop();
                return;
            }

            // 继续播放
            if (isPlaying) {
                scheduleNext();
            }
        }, actualInterval);
    }

    /**
     * 设置播放速度
     * @param {number} value - 速度倍数
     */
    function setSpeed(value) {
        speed = Math.max(0.25, Math.min(8, value));

        // 如果正在播放，重新调度
        if (isPlaying) {
            clearTimeout(timer);
            scheduleNext();
        }
    }

    /**
     * 设置播放间隔
     * @param {number} ms - 毫秒
     */
    function setInterval(ms) {
        interval = Math.max(100, Math.min(5000, ms));

        // 如果正在播放，重新调度
        if (isPlaying) {
            clearTimeout(timer);
            scheduleNext();
        }
    }

    /**
     * 设置循环模式
     * @param {boolean} value - 是否循环
     */
    function setLoop(value) {
        loop = value;
    }

    /**
     * 获取播放状态
     * @returns {Object} 状态对象
     */
    function getState() {
        return {
            isPlaying,
            currentIndex,
            currentTime: timestamps[currentIndex] || null,
            speed,
            interval,
            loop,
            total: timestamps.length
        };
    }

    /**
     * 获取当前时间
     * @returns {string} 当前时间戳
     */
    function getCurrentTime() {
        if (timestamps[currentIndex]) {
            return timestamps[currentIndex];
        }
        return null;
    }

    /**
     * 获取当前索引
     * @returns {number} 当前索引
     */
    function getCurrentIndex() {
        return currentIndex;
    }

    /**
     * 获取总帧数
     * @returns {number} 总帧数
     */
    function getTotalFrames() {
        return timestamps.length;
    }

    /**
     * 更新播放按钮状态
     * @param {boolean} playing - 是否正在播放
     */
    function updatePlayButton(playing) {
        const playBtn = Helpers.$('#play-btn');
        const playIcon = Helpers.$('#play-icon');

        if (playBtn) {
            if (playing) {
                playBtn.classList.add('active');
            } else {
                playBtn.classList.remove('active');
            }
        }

        if (playIcon) {
            playIcon.textContent = playing ? '⏸' : '▶';
        }
    }

    /**
     * 跳到第一个时间点
     */
    function first() {
        if (timestamps.length > 0) {
            jumpTo(timestamps[0]);
        }
    }

    /**
     * 跳到最后一个时间点
     */
    function last() {
        if (timestamps.length > 0) {
            jumpTo(timestamps[timestamps.length - 1]);
        }
    }

    /**
     * 设置时间戳列表
     * @param {string[]} timeStamps - 时间戳列表
     */
    function setTimestamps(timeStamps) {
        timestamps = timeStamps || [];
        currentIndex = 0;
    }

    /**
     * 销毁播放器
     */
    function destroy() {
        pause();
        timestamps = [];
        currentIndex = 0;
        callbacks = {
            onTimeUpdate: null,
            onPlayChange: null
        };
    }

    // 导出公共 API
    return {
        init,
        play,
        pause,
        stop,
        next,
        prev,
        jumpTo,
        setSpeed,
        setInterval,
        setLoop,
        getState,
        getCurrentTime,
        getCurrentIndex,
        getTotalFrames,
        first,
        last,
        setTimestamps,
        destroy
    };
})();

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Player;
}
