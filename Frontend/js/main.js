/**
 * 应用主入口
 * Singapore Transit Visualization System
 */

(function() {
    'use strict';

    // 应用状态
    const AppState = {
        currentTimestamp: null,
        isPlaying: false,
        activeLayers: {
            mrt: true,
            lrt: true,
            bus: true
        },
        selectedRoute: null
    };

    /**
     * 初始化应用
     */
    async function init() {
        console.log('Initializing Singapore Transit Visualization...');

        // 初始化主题
        initTheme();

        // 初始化 UI 组件
        initUI();

        // 初始化地图
        await initMap();

        // 加载数据
        const dataResult = await API.loadAll();

        if (dataResult.success) {
            // 初始化时间轴
            initTimeline(dataResult.timestamps);

            // 渲染初始数据
            if (dataResult.timestamps.length > 0) {
                // 设置第一个时间点
                const firstTimestamp = dataResult.timestamps[0];
                setCurrentTime(firstTimestamp);
            }
        } else {
            console.error('Failed to load data:', dataResult.error);
        }

        console.log('Application initialized successfully.');
    }

    /**
     * 初始化主题
     */
    function initTheme() {
        const themeToggle = Helpers.$('#theme-toggle');
        const themeStylesheet = Helpers.$('#theme-stylesheet');

        // 从本地存储恢复主题
        const savedTheme = localStorage.getItem(CONFIG.theme.storageKey) || CONFIG.theme.default;

        if (savedTheme === 'dark') {
            themeStylesheet.setAttribute('href', 'css/theme-dark.css');
        }

        // 主题切换事件
        Helpers.on(themeToggle, 'click', function() {
            const currentHref = themeStylesheet.getAttribute('href');
            const newTheme = currentHref.includes('light') ? 'dark' : 'light';
            const newHref = newTheme === 'dark' ? 'css/theme-dark.css' : 'css/theme-light.css';

            themeStylesheet.setAttribute('href', newHref);
            localStorage.setItem(CONFIG.theme.storageKey, newTheme);

            // 通知地图底图切换
            if (window.MapManager) {
                MapManager.setDarkMode(newTheme === 'dark');
            }
        });
    }

    /**
     * 初始化 UI 组件
     */
    function initUI() {
        // 侧边栏关闭按钮
        const sidebarClose = Helpers.$('#sidebar-close');
        const sidebar = Helpers.$('#sidebar');

        Helpers.on(sidebarClose, 'click', function() {
            Helpers.hide(sidebar);
            AppState.selectedRoute = null;
        });

        // 图层控制
        initLayerControls();

        // 时间轴控制
        initTimelineControls();
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

        // 恢复图层状态
        for (const [type, toggle] of Object.entries(toggles)) {
            if (toggle) {
                toggle.checked = AppState.activeLayers[type];

                // 监听变化
                Helpers.on(toggle, 'change', function() {
                    AppState.activeLayers[type] = this.checked;

                    // 通知图层管理器
                    if (window.LayerManager) {
                        LayerManager.toggleLayer(type, this.checked);
                    }

                    // 重新渲染客流
                    if (AppState.currentTimestamp) {
                        renderFlowData(AppState.currentTimestamp);
                    }
                });
            }
        }
    }

    /**
     * 初始化时间轴控制
     */
    function initTimelineControls() {
        const playBtn = Helpers.$('#play-btn');
        const stopBtn = Helpers.$('#stop-btn');
        const speedSelect = Helpers.$('#speed-select');

        // 播放/暂停
        Helpers.on(playBtn, 'click', function() {
            togglePlay();
        });

        // 停止
        Helpers.on(stopBtn, 'click', function() {
            stopPlay();
        });

        // 速度选择
        Helpers.on(speedSelect, 'change', function() {
            const speed = parseFloat(this.value);
            if (window.Player) {
                Player.setSpeed(speed);
            }
        });
    }

    /**
     * 初始化地图
     */
    async function initMap() {
        if (window.MapManager) {
            await MapManager.init(Helpers.$('#map-container'));
        }
    }

    /**
     * 初始化时间轴
     * @param {string[]} timestamps - 时间戳列表
     */
    function initTimeline(timestamps) {
        if (window.Timeline) {
            Timeline.init(Helpers.$('#timeline'), timestamps, {
                onTimeChange: setCurrentTime,
                onPlayChange: handlePlayChange
            });
        }

        // 初始化播放控制器
        if (window.Player) {
            Player.init(timestamps, {
                onTimeUpdate: (timestamp) => {
                    setCurrentTime(timestamp);
                    Timeline.setCurrentTime(timestamp);
                }
            });
        }
    }

    /**
     * 设置当前时间
     * @param {string} timestamp - 时间戳
     */
    function setCurrentTime(timestamp) {
        AppState.currentTimestamp = timestamp;

        // 更新时间显示
        const timeDisplay = Helpers.$('#current-time-display');
        if (timeDisplay) {
            timeDisplay.textContent = Helpers.formatTime(timestamp);
        }

        // 渲染客流数据
        renderFlowData(timestamp);
    }

    /**
     * 渲染客流数据
     * @param {string} timestamp - 时间戳
     */
    async function renderFlowData(timestamp) {
        // 获取活跃的图层类型
        const activeTypes = Object.entries(AppState.activeLayers)
            .filter(([_, enabled]) => enabled)
            .map(([type]) => type);

        // 获取客流数据
        const flows = await API.getFlowsAt(timestamp, activeTypes);

        // 渲染到地图
        if (window.FlowRenderer) {
            FlowRenderer.render(flows);
        }
    }

    /**
     * 切换播放状态
     */
    function togglePlay() {
        if (AppState.isPlaying) {
            pausePlay();
        } else {
            startPlay();
        }
    }

    /**
     * 开始播放
     */
    function startPlay() {
        AppState.isPlaying = true;

        const playBtn = Helpers.$('#play-btn');
        const playIcon = Helpers.$('#play-icon');

        if (playBtn) playBtn.classList.add('active');
        if (playIcon) playIcon.textContent = '⏸';

        if (window.Player) {
            Player.play();
        }
    }

    /**
     * 暂停播放
     */
    function pausePlay() {
        AppState.isPlaying = false;

        const playBtn = Helpers.$('#play-btn');
        const playIcon = Helpers.$('#play-icon');

        if (playBtn) playBtn.classList.remove('active');
        if (playIcon) playIcon.textContent = '▶';

        if (window.Player) {
            Player.pause();
        }
    }

    /**
     * 停止播放
     */
    function stopPlay() {
        pausePlay();

        // 重置到起始时间
        const timestamps = Timeline.getTimestamps();
        if (timestamps && timestamps.length > 0) {
            setCurrentTime(timestamps[0]);
            Timeline.setCurrentTime(timestamps[0]);
        }
    }

    /**
     * 处理播放状态变化
     * @param {boolean} isPlaying - 是否正在播放
     */
    function handlePlayChange(isPlaying) {
        if (isPlaying !== AppState.isPlaying) {
            AppState.isPlaying = isPlaying;
            // UI 会通过 Player 的事件更新
        }
    }

    /**
     * 显示线路详情
     * @param {string} routeId - 线路 ID
     */
    async function showRouteDetail(routeId) {
        AppState.selectedRoute = routeId;

        // 获取线路信息
        const routeInfo = await API.getRouteInfo(routeId);
        const flowItem = AppState.currentTimestamp
            ? await API.getFlowItem(AppState.currentTimestamp, routeId)
            : null;

        // 更新侧边栏
        updateSidebar(routeInfo, flowItem);

        // 显示侧边栏
        Helpers.show(Helpers.$('#sidebar'));

        // 高亮选中线路
        if (window.LayerManager) {
            LayerManager.highlightRoute(routeId);
        }
    }

    /**
     * 更新侧边栏内容
     * @param {Object} routeInfo - 线路信息
     * @param {Object} flowItem - 客流数据
     */
    function updateSidebar(routeInfo, flowItem) {
        if (!routeInfo) {
            Helpers.setText('#route-name', '未知线路');
            return;
        }

        // 基本信息
        Helpers.setText('#route-name', routeInfo.name || '未知线路');
        Helpers.setText('#route-type', CONFIG.transportTypes[routeInfo.type]?.name || routeInfo.type || '-');
        Helpers.setText('#route-start', routeInfo.startStation || '-');
        Helpers.setText('#route-end', routeInfo.endStation || '-');

        // 客流数据
        if (flowItem) {
            Helpers.setText('#current-flow-value', Helpers.formatFlow(flowItem.flow));
            Helpers.setText('#current-capacity', Helpers.formatFlow(flowItem.capacity));
            Helpers.setText('#current-utilization', Helpers.formatPercent(flowItem.utilization));
        } else {
            Helpers.setText('#current-flow-value', '-');
            Helpers.setText('#current-capacity', '-');
            Helpers.setText('#current-utilization', '-');
        }

        // 站点列表
        const stationsUl = Helpers.$('#stations-ul');
        if (stationsUl && routeInfo.stations) {
            const html = routeInfo.stations.map(s =>
                `<li>${s.name}</li>`
            ).join('');
            Helpers.setHTML(stationsUl, html);
        } else {
            Helpers.setHTML(stationsUl, '');
        }
    }

    /**
     * 当 DOM 加载完成后初始化
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 导出全局 API（供其他模块调用）
    window.App = {
        state: AppState,
        setCurrentTime,
        showRouteDetail,
        startPlay,
        pausePlay,
        stopPlay
    };

})();
