/**
 * @file layers.js
 * @brief 图层管理器（数据中心建模版）/ Layer manager (data-centric modeling).
 *
 * 设计要点（中文）：
 * - 以 RouteState 为真相源（single source of truth），将「静态 routes」+「动态 flow」+「UI 状态」统一建模。
 * - 样式由投影函数（projection）计算得到；任何时刻都能从状态推导出确定的渲染结果。
 *
 * Design notes (EN):
 * - Use RouteState as the single source of truth, modeling static routes + dynamic flow + UI state.
 * - Styles are computed by projection; rendering is a deterministic function of state.
 */

const LayerManager = (function () {
    "use strict";

    // -----------------------------
    // Internal state / 内部状态
    // -----------------------------

    /** @type {L.LayerGroup|null} */
    let routeLayerGroup = null;

    /** @type {L.LayerGroup|null} */
    let stationLayerGroup = null;

    /** @type {boolean} */
    let initialized = false;

    /**
     * @typedef {Object} RouteUIState
     * @property {boolean} selected - 是否被选中 / Selected.
     * @property {boolean} hovered  - 是否悬浮 / Hovered.
     */

    /**
     * @typedef {Object} RouteFlowState
     * @property {number|null} flow - 客流 / Flow.
     * @property {string|null} type - 类型 / Type.
     * @property {number|null} capacity - 容量 / Capacity.
     * @property {number|null} utilization - 利用率 / Utilization.
     */

    /**
     * @typedef {Object} RouteStyleState
     * @property {string} color - 颜色 / Color.
     * @property {number} weight - 线宽 / Stroke weight.
     * @property {number} opacity - 不透明度 / Opacity.
     */

    /**
     * @typedef {Object} RouteState
     * @property {string} id - 线路主键 / Route id.
     * @property {Object} info - 静态信息 / Static route info.
     * @property {L.GeoJSON} layer - Leaflet layer.
     * @property {RouteUIState} ui - UI state.
     * @property {RouteFlowState} flow - Latest flow state.
     * @property {RouteStyleState|null} lastStyle - Last applied style (for diff).
     */

    /** @type {Map<string, RouteState>} */
    const routesById = new Map();

    /** @type {Map<string, string>} */
    const idByName = new Map();

    /** @type {string|null} */
    let selectedRouteId = null;

    // -----------------------------
    // Init / 初始化
    // -----------------------------

    /**
     * @brief 初始化图层管理器（幂等）/ Initialize layer manager (idempotent).
     * @note
     * 中文：禁止重复 init，避免图层组/引用漂移。
     * EN: Must be idempotent to prevent layer-group/reference drift.
     */
    function init() {
        if (initialized) return;
        initialized = true;

        routeLayerGroup = L.layerGroup().addTo(MapManager.getMap());
        stationLayerGroup = L.layerGroup().addTo(MapManager.getMap());

        bindRouteClickEvents();
    }

    function bindRouteClickEvents() {
        MapManager.on("click", function () {
            clearSelection();
        });
    }

    // -----------------------------
    // Data-centric projection / 数据投影：State -> Style
    // -----------------------------

    /**
     * @brief 解析外部 flow item 到 routeId / Resolve an external flow item to routeId.
     * @param {Object} item - 外部 flow item / External flow item.
     * @return {string|null} routeId - 匹配到的 routeId / Resolved routeId.
     */
    function resolveRouteId(item) {
        if (!item) return null;

        // 1) Primary key: route_id
        if (item.route_id && routesById.has(item.route_id)) return item.route_id;

        // 2) Common alternates: name / route_name
        const name = item.route_name || item.name || null;
        if (name && idByName.has(name)) return idByName.get(name);

        return null;
    }

    /**
     * @brief 决定一条线路的颜色 / Decide route color.
     * @param {RouteState} rs - RouteState.
     * @return {string} color - CSS color string.
     */
    function decideColor(rs) {
        const infoType = (rs.info?.type || "mrt").toLowerCase();
        const flowType = (rs.flow?.type || infoType || "mrt").toLowerCase();

        // 1) Dynamic flow color
        if (rs.flow && rs.flow.flow !== null && rs.flow.flow !== undefined) {
            if (window.ColorScale && typeof ColorScale.getColor === "function") {
                const c = ColorScale.getColor(rs.flow.flow, flowType);
                if (c) return c;
            }
        }

        // 2) Static route color (your data: colour)
        if (rs.info?.colour) return rs.info.colour;
        if (rs.info?.color) return rs.info.color;

        // 3) Optional type defaults
        if (infoType === "bus") return "#f39c12";
        if (infoType === "lrt") return "#2ecc71";
        if (infoType === "mrt") return "#3498db";

        // 4) Fallback gray
        return "#cccccc";
    }

    /**
     * @brief 由 RouteState 投影得到 StyleState / Project style from RouteState.
     * @param {RouteState} rs - RouteState.
     * @return {RouteStyleState} style - Projected style.
     */
    function projectStyle(rs) {
        const baseOpacity = rs.ui.selected ? 1.0 : 0.8;
        const opacity = rs.ui.selected ? 1.0 : (rs.ui.hovered ? 1.0 : baseOpacity);
        const weight = rs.ui.selected ? 6 : (rs.ui.hovered ? 6 : 4);

        return {
            color: decideColor(rs),
            weight,
            opacity,
        };
    }

    /**
     * @brief 将投影样式应用到 Leaflet layer（带 diff）/ Apply projected style with diff.
     * @param {RouteState} rs - RouteState.
     */
    function applyProjection(rs) {
        const next = projectStyle(rs);
        const prev = rs.lastStyle;

        // Cheap diff to avoid redundant setStyle
        if (
            prev &&
            prev.color === next.color &&
            prev.weight === next.weight &&
            prev.opacity === next.opacity
        ) {
            return;
        }

        rs.layer.eachLayer(function (layer) {
            if (layer.setStyle) layer.setStyle(next);
        });

        rs.lastStyle = next;
    }

    /**
     * @brief 批量重投影所有线路 / Re-project all routes.
     */
    function invalidateAll() {
        routesById.forEach((rs) => applyProjection(rs));
    }

    // -----------------------------
    // Public API / 对外 API（保持兼容）
    // -----------------------------

    /**
     * @brief 添加线路图层 / Add a route layer.
     * @param {string} routeId - 线路主键 / Route id.
     * @param {Object} routeInfo - 静态线路信息 / Static route info.
     * @param {Object} geojson - GeoJSON 数据 / GeoJSON.
     * @returns {L.GeoJSON|null} layer - Leaflet GeoJSON layer.
     */
    function addRoute(routeId, routeInfo, geojson) {
        if (!routeLayerGroup || !geojson) {
            console.warn("LayerManager.addRoute: missing routeLayerGroup or geojson");
            return null;
        }

        // Create layer
        const layer = L.geoJSON(geojson, {
            // IMPORTANT: do NOT hardcode gray here; style is projected from RouteState.
            style: () => ({
                color: "#cccccc", // temporary until first projection
                weight: 4,
                opacity: 0.8,
            }),
            onEachFeature: (feature, leafLayer) => {
                leafLayer.on("click", function (e) {
                    L.DomEvent.stopPropagation(e);
                    selectRoute(routeId);
                    if (window.App) App.showRouteDetail(routeId);
                });

                leafLayer.on("mouseover", function () {
                    const rs = routesById.get(routeId);
                    if (!rs) return;
                    if (!rs.ui.selected) {
                        rs.ui.hovered = true;
                        applyProjection(rs);
                    }
                });

                leafLayer.on("mouseout", function () {
                    const rs = routesById.get(routeId);
                    if (!rs) return;
                    if (!rs.ui.selected) {
                        rs.ui.hovered = false;
                        applyProjection(rs);
                    }
                });
            },
        });

        // Build RouteState
        /** @type {RouteState} */
        const rs = {
            id: routeId,
            info: routeInfo || {},
            layer,
            ui: { selected: false, hovered: false },
            flow: { flow: null, type: null, capacity: null, utilization: null },
            lastStyle: null,
        };

        routesById.set(routeId, rs);
        if (rs.info?.name) idByName.set(rs.info.name, routeId);

        layer.addTo(routeLayerGroup);

        // First projection (static colour already available)
        applyProjection(rs);

        return layer;
    }

    /**
     * @brief 吸收客流快照并刷新渲染 / Ingest flow snapshot and refresh rendering.
     * @param {Array<Object>} flowData - 客流数组 / Flow items.
     */
    function updateRouteColors(flowData) {
        if (!flowData) {
            // Even if flowData is missing, we still want a stable projection (static colour).
            invalidateAll();
            return;
        }

        // 1) ingest to state
        for (const item of flowData) {
            const rid = resolveRouteId(item);
            if (!rid) continue;

            const rs = routesById.get(rid);
            if (!rs) continue;

            rs.flow = {
                flow: item.flow ?? null,
                type: item.type ?? rs.info?.type ?? null,
                capacity: item.capacity ?? null,
                utilization: item.utilization ?? null,
            };
        }

        // 2) project all (can be optimized later to only affected routeIds)
        invalidateAll();
    }

    /**
     * @brief 选中线路 / Select a route.
     * @param {string} routeId - route id.
     */
    function selectRoute(routeId) {
        clearSelection();
        selectedRouteId = routeId;

        const rs = routesById.get(routeId);
        if (rs) {
            rs.ui.selected = true;
            rs.ui.hovered = false;
            applyProjection(rs);
            rs.layer.bringToFront();
        }

        // de-emphasize others (data-driven opacity)
        routesById.forEach((r, id) => {
            if (id !== routeId) {
                r.ui.selected = false;
                r.ui.hovered = false;
                // selection effect: reduce opacity, but keep color
                r.lastStyle = null; // force apply
                r.layer.eachLayer((layer) => {
                    if (layer.setStyle) layer.setStyle({ opacity: 0.3 });
                });
            }
        });
    }

    /**
     * @brief 清除选中状态 / Clear selection.
     */
    function clearSelection() {
        if (selectedRouteId) {
            const rs = routesById.get(selectedRouteId);
            if (rs) {
                rs.ui.selected = false;
                rs.ui.hovered = false;
                rs.lastStyle = null;
                applyProjection(rs);
            }
            selectedRouteId = null;
        }

        // restore others
        invalidateAll();
    }

    // ---- keep rest of API (stations, toggle, etc.) as-is or minimally adapted ----

    function addStations(stations) {
        if (!stationLayerGroup || !stations) return [];
        const markers = [];
        stations.forEach((station) => {
            if (station.position) {
                const marker = L.circleMarker(station.position, {
                    radius: 5,
                    fillColor: "#666",
                    color: "#fff",
                    weight: 1,
                    fillOpacity: 0.8,
                });
                marker.bindPopup(
                    `<strong>${station.name}</strong><br><small>${station.id || ""}</small>`
                );
                marker.addTo(stationLayerGroup);
                markers.push(marker);
            }
        });
        return markers;
    }

    function addBusStops(busStops) {
        if (!stationLayerGroup || !busStops) return [];
        const markers = [];
        busStops.forEach((stop) => {
            if (stop.Latitude && stop.Longitude) {
                const position = [stop.Latitude, stop.Longitude];
                const marker = L.circleMarker(position, {
                    radius: 4,
                    fillColor: "#f39c12",
                    color: "#fff",
                    weight: 1,
                    fillOpacity: 0.7,
                });
                marker.bindPopup(
                    `<strong>${stop.Description || stop.BusStopCode}</strong><br>
           <small>站点编号: ${stop.BusStopCode}</small><br>
           <small>道路: ${stop.RoadName || "-"}</small>`
                );
                marker.addTo(stationLayerGroup);
                markers.push(marker);
            }
        });
        return markers;
    }

    function toggleLayer(type, visible) {
        routesById.forEach((rs) => {
            const routeType = (rs.info?.type || "mrt").toLowerCase();
            if (routeType !== type) return;
            if (visible) routeLayerGroup.addLayer(rs.layer);
            else routeLayerGroup.removeLayer(rs.layer);
        });
    }

    function getRouteInfo(routeId) {
        const rs = routesById.get(routeId);
        return rs ? rs.info : null;
    }

    function getAllRoutes() {
        const obj = {};
        routesById.forEach((rs, id) => (obj[id] = rs.info));
        return obj;
    }

    function clearRoutes() {
        if (routeLayerGroup) routeLayerGroup.clearLayers();
        routesById.clear();
        idByName.clear();
        selectedRouteId = null;
    }

    function clearStations() {
        if (stationLayerGroup) stationLayerGroup.clearLayers();
    }

    function getRouteLayer(routeId) {
        const rs = routesById.get(routeId);
        return rs ? rs.layer : null;
    }

    function fitToRoute(routeId) {
        const rs = routesById.get(routeId);
        if (!rs || !rs.layer) return;
        const map = MapManager.getMap();
        if (!map) return;
        map.fitBounds(rs.layer.getBounds(), { padding: [50, 50] });
    }

    return {
        init,
        addRoute,
        addStations,
        addBusStops,
        updateRouteColors, // keep name for compatibility
        selectRoute,
        clearSelection,
        highlightRoute: selectRoute,
        toggleLayer,
        getRouteInfo,
        getAllRoutes,
        clearRoutes,
        clearStations,
        getRouteLayer,
        fitToRoute,
    };
})();

window.LayerManager = LayerManager;

if (typeof module !== "undefined" && module.exports) {
    module.exports = LayerManager;
}
