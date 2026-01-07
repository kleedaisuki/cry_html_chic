/**
 * @file heatmapRenderer.js
 * @brief 人口热力图渲染器 / Population heatmap renderer.
 *
 * @details
 * 保留既有 HeatmapRenderer API，不改调用方（We don't break userspace!）。
 * Keep the public HeatmapRenderer API unchanged.
 *
 * 渲染实现采用主流热力图管线（common heatmap pipeline）：
 * 1) 将点渲染到“alpha 画布”（shadow canvas）上做强度叠加。
 *    Accumulate intensity into an alpha-only shadow canvas.
 * 2) 对 alpha 像素做调色板映射（palette mapping），输出到可见画布。
 *    Colorize the alpha pixels using a precomputed palette.
 *
 * @note
 * - 数据点格式：[{ lat, lon, value, name? }, ...]
 *   Data point format: [{lat, lon, value, name?}, ...]
 * - 仅依赖 Leaflet (L) 与 MapManager.getMap()。
 *   Depends only on Leaflet (L) and MapManager.getMap().
 */

/* global L, MapManager */

const HeatmapRenderer = (function () {
    'use strict';

    // -----------------------------
    // 内部状态 / Internal state
    // -----------------------------
    let overlay = null;          // Leaflet layer instance
    let enabled = true;
    let heatmapData = [];
    let mapInstance = null;

    // -----------------------------
    // 配置 / Config
    // -----------------------------
    const CONFIG = {
        /**
         * @brief 基础半径（CSS 像素）/ Base radius in CSS pixels.
         */
        radius: 35,

        /**
         * @brief 强度曲线（Gamma）/ Intensity gamma curve.
         * @note
         * - < 1：增强弱信号（更“糊”更显眼） / boosts weak signals
         * - > 1：压制弱信号（更“尖”更集中） / suppresses weak signals
         */
        gamma: 0.85,

        /**
         * @brief 叠加上限透明度 / Max opacity applied when drawing blobs.
         */
        maxOpacity: 0.80,

        /**
         * @brief 颜色渐变（0~1）/ Color gradient stops (0~1).
         * @note
         * - 透明度这里作为“调色板 alpha 上限”，最终会再乘 shadow alpha。
         * - Alpha here is the palette alpha cap; final alpha is paletteAlpha * shadowAlpha.
         */
        gradient: [
            { pos: 0.0, color: 'rgba(0, 0, 255, 0.0)' },
            { pos: 0.2, color: 'rgba(0, 255, 255, 0.30)' },
            { pos: 0.4, color: 'rgba(0, 255, 0, 0.40)' },
            { pos: 0.6, color: 'rgba(255, 255, 0, 0.55)' },
            { pos: 0.8, color: 'rgba(255, 127, 0, 0.65)' },
            { pos: 1.0, color: 'rgba(255, 0, 0, 0.75)' }
        ],

        /**
         * @brief z-index：在底图之上、线路之下 / z-index: above basemap, below routes.
         */
        zIndex: 400
    };

    // -----------------------------
    // 小工具 / Utilities
    // -----------------------------

    /**
     * @brief 夹紧数值 / Clamp a number.
     * @param {number} x 数值 / value
     * @param {number} lo 下界 / lower bound
     * @param {number} hi 上界 / upper bound
     * @returns {number} 夹紧后的数值 / clamped value
     */
    function clamp(x, lo, hi) {
        return Math.max(lo, Math.min(hi, x));
    }

    /**
     * @brief 将 rgba()/rgb()/hex 解析为 RGBA / Parse rgba()/rgb()/hex to RGBA.
     * @param {string} s 颜色字符串 / color string
     * @returns {{r:number,g:number,b:number,a:number}} RGBA / RGBA
     */
    function parseColor(s) {
        if (!s || typeof s !== 'string') return { r: 0, g: 0, b: 0, a: 1 };

        const str = s.trim();

        // rgba(r,g,b,a)
        let m = str.match(/^rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)$/i);
        if (m) {
            return {
                r: clamp(parseFloat(m[1]), 0, 255),
                g: clamp(parseFloat(m[2]), 0, 255),
                b: clamp(parseFloat(m[3]), 0, 255),
                a: clamp(parseFloat(m[4]), 0, 1)
            };
        }

        // rgb(r,g,b)
        m = str.match(/^rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)$/i);
        if (m) {
            return {
                r: clamp(parseFloat(m[1]), 0, 255),
                g: clamp(parseFloat(m[2]), 0, 255),
                b: clamp(parseFloat(m[3]), 0, 255),
                a: 1
            };
        }

        // #RRGGBB / #RGB
        m = str.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
        if (m) {
            const hex = m[1];
            if (hex.length === 3) {
                const r = parseInt(hex[0] + hex[0], 16);
                const g = parseInt(hex[1] + hex[1], 16);
                const b = parseInt(hex[2] + hex[2], 16);
                return { r, g, b, a: 1 };
            }
            const r = parseInt(hex.slice(0, 2), 16);
            const g = parseInt(hex.slice(2, 4), 16);
            const b = parseInt(hex.slice(4, 6), 16);
            return { r, g, b, a: 1 };
        }

        // fallback：让浏览器解析 / let browser parse it
        const tmp = document.createElement('div');
        tmp.style.color = str;
        document.body.appendChild(tmp);
        const cs = getComputedStyle(tmp).color;
        document.body.removeChild(tmp);

        return parseColor(cs);
    }

    /**
     * @brief 生成 256 色调色板 / Build a 256-entry palette from gradient stops.
     * @param {{pos:number,color:string}[]} stops 渐变点 / gradient stops
     * @returns {Uint8ClampedArray} 长度 256*4 的 RGBA 数组 / RGBA array length 256*4
     */
    function buildPalette(stops) {
        const sorted = (stops || []).slice().sort((a, b) => (a.pos || 0) - (b.pos || 0));
        const palette = new Uint8ClampedArray(256 * 4);

        if (sorted.length === 0) {
            for (let i = 0; i < 256; i++) {
                palette[i * 4 + 0] = 0;
                palette[i * 4 + 1] = 0;
                palette[i * 4 + 2] = 0;
                palette[i * 4 + 3] = 0;
            }
            return palette;
        }

        const parsed = sorted.map(s => ({ pos: clamp(s.pos ?? 0, 0, 1), rgba: parseColor(s.color) }));

        for (let i = 0; i < 256; i++) {
            const t = i / 255;

            let j = 0;
            while (j + 1 < parsed.length && t > parsed[j + 1].pos) j++;

            const left = parsed[j];
            const right = parsed[Math.min(j + 1, parsed.length - 1)];

            if (right.pos === left.pos) {
                palette[i * 4 + 0] = Math.round(left.rgba.r);
                palette[i * 4 + 1] = Math.round(left.rgba.g);
                palette[i * 4 + 2] = Math.round(left.rgba.b);
                palette[i * 4 + 3] = Math.round(clamp(left.rgba.a, 0, 1) * 255);
                continue;
            }

            const u = clamp((t - left.pos) / (right.pos - left.pos), 0, 1);

            const r = left.rgba.r + (right.rgba.r - left.rgba.r) * u;
            const g = left.rgba.g + (right.rgba.g - left.rgba.g) * u;
            const b = left.rgba.b + (right.rgba.b - left.rgba.b) * u;
            const a = left.rgba.a + (right.rgba.a - left.rgba.a) * u;

            palette[i * 4 + 0] = Math.round(r);
            palette[i * 4 + 1] = Math.round(g);
            palette[i * 4 + 2] = Math.round(b);
            palette[i * 4 + 3] = Math.round(clamp(a, 0, 1) * 255);
        }

        return palette;
    }

    /**
     * @brief 创建“点模板”（模糊圆）/ Build a blurred circle stamp.
     * @param {number} radiusPx 半径（device 像素）/ radius in device pixels
     * @returns {HTMLCanvasElement} stamp canvas
     */
    function buildCircleStamp(radiusPx) {
        const r = Math.max(1, Math.floor(radiusPx));
        const d = r * 2;

        const c = document.createElement('canvas');
        c.width = d;
        c.height = d;

        const ctx = c.getContext('2d');
        ctx.clearRect(0, 0, d, d);

        const g = ctx.createRadialGradient(r, r, 0, r, r, r);
        g.addColorStop(0, 'rgba(0,0,0,1)');
        g.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(r, r, r, 0, Math.PI * 2);
        ctx.fill();

        return c;
    }

    // -----------------------------
    // Leaflet Layer: HeatmapCanvas
    // -----------------------------
    const HeatmapCanvas = L.Layer.extend({
        _heatmapData: [],
        _enabled: true,
        _palette: null,
        _circleStamp: null,
        _lastSizeKey: null,
        _raf: 0,

        initialize: function (options) {
            L.setOptions(this, options);
            this._palette = buildPalette(CONFIG.gradient);
        },

        onAdd: function (map) {
            this._map = map;

            this._container = L.DomUtil.create('div', 'leaflet-heatmap-layer');
            this._container.style.position = 'absolute';
            this._container.style.top = '0';
            this._container.style.left = '0';
            this._container.style.width = '100%';
            this._container.style.height = '100%';
            this._container.style.pointerEvents = 'none';
            this._container.style.zIndex = String(CONFIG.zIndex);

            this._canvas = L.DomUtil.create('canvas', '');
            this._canvas.style.width = '100%';
            this._canvas.style.height = '100%';
            this._container.appendChild(this._canvas);

            // shadow canvas：不进 DOM，用于 alpha 累积
            this._shadowCanvas = document.createElement('canvas');

            map.getPanes().overlayPane.appendChild(this._container);

            map.on('moveend', this._scheduleDraw, this);
            map.on('zoomend', this._scheduleDraw, this);
            map.on('resize', this._scheduleDraw, this);

            this._scheduleDraw();
        },

        onRemove: function (map) {
            if (this._raf) {
                L.Util.cancelAnimFrame(this._raf);
                this._raf = 0;
            }

            map.getPanes().overlayPane.removeChild(this._container);

            map.off('moveend', this._scheduleDraw, this);
            map.off('zoomend', this._scheduleDraw, this);
            map.off('resize', this._scheduleDraw, this);

            this._map = null;
            this._container = null;
            this._canvas = null;
            this._shadowCanvas = null;
        },

        setData: function (data) {
            this._heatmapData = Array.isArray(data) ? data : [];
            this._scheduleDraw();
        },

        setEnabled: function (enabled) {
            this._enabled = !!enabled;
            this._scheduleDraw();
        },

        _scheduleDraw: function () {
            if (!this._map || !this._canvas) return;
            if (this._raf) return;
            this._raf = L.Util.requestAnimFrame(this._draw, this);
        },

        _draw: function () {
            this._raf = 0;

            const map = this._map;
            const canvas = this._canvas;
            const shadow = this._shadowCanvas;
            if (!map || !canvas || !shadow) return;

            const size = map.getSize();                 // CSS px
            const pixelRatio = window.devicePixelRatio || 1;

            const sizeKey = `${size.x}x${size.y}@${pixelRatio}`;
            if (this._lastSizeKey !== sizeKey) {
                this._lastSizeKey = sizeKey;

                const w = Math.max(1, Math.floor(size.x * pixelRatio));
                const h = Math.max(1, Math.floor(size.y * pixelRatio));

                canvas.width = w;
                canvas.height = h;
                canvas.style.width = `${size.x}px`;
                canvas.style.height = `${size.y}px`;

                shadow.width = w;
                shadow.height = h;

                this._circleStamp = buildCircleStamp(CONFIG.radius * pixelRatio);
            }

            const ctx = canvas.getContext('2d');
            const sctx = shadow.getContext('2d');

            // reset transform（关键：避免 scale 累积）
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            sctx.setTransform(1, 0, 0, 1, 0, 0);

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            sctx.clearRect(0, 0, shadow.width, shadow.height);

            if (!this._enabled) return;

            const data = this._heatmapData;
            if (!data || data.length === 0) return;

            // maxValue for normalization
            let maxValue = 1;
            for (let i = 0; i < data.length; i++) {
                const v = Number(data[i]?.value ?? 0);
                if (Number.isFinite(v) && v > maxValue) maxValue = v;
            }

            // alpha accumulate
            const stamp = this._circleStamp;
            const stampRadius = stamp.width / 2;

            for (let i = 0; i < data.length; i++) {
                const p = data[i];
                const lat = Number(p?.lat);
                const lon = Number(p?.lon);
                const v = Number(p?.value ?? 0);

                if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
                if (!Number.isFinite(v) || v <= 0) continue;

                const t = clamp(v / maxValue, 0, 1);
                const intensity = Math.pow(t, CONFIG.gamma);

                const pt = map.latLngToContainerPoint([lat, lon]); // CSS px
                const x = pt.x * pixelRatio;                      // device px
                const y = pt.y * pixelRatio;

                sctx.globalAlpha = clamp(intensity * CONFIG.maxOpacity, 0, 1);
                sctx.drawImage(stamp, x - stampRadius, y - stampRadius);
            }

            // colorize
            const img = sctx.getImageData(0, 0, shadow.width, shadow.height);
            const pix = img.data;
            const pal = this._palette;

            for (let i = 0; i < pix.length; i += 4) {
                const a = pix[i + 3]; // 0..255
                if (a === 0) continue;

                const idx = a * 4;
                pix[i + 0] = pal[idx + 0];
                pix[i + 1] = pal[idx + 1];
                pix[i + 2] = pal[idx + 2];

                const pa = pal[idx + 3];
                pix[i + 3] = Math.round((pa * a) / 255);
            }

            ctx.putImageData(img, 0, 0);
        }
    });

    // -----------------------------
    // Public API (unchanged)
    // -----------------------------

    /**
     * @brief 初始化渲染器 / Initialize renderer.
     * @returns {void}
     */
    function init() {
        if (overlay) return;

        const map = MapManager?.getMap?.();
        if (!map) {
            console.warn('HeatmapRenderer: Map not available');
            return;
        }

        mapInstance = map;
        enabled = true;

        overlay = new HeatmapCanvas();
        overlay.addTo(map);

        overlay.setEnabled(enabled);
        overlay.setData(heatmapData);
    }

    /**
     * @brief 渲染热力图数据 / Render heatmap data.
     * @param {Array} data 热力图数据点 / heatmap points
     * @returns {void}
     */
    function render(data) {
        if (!Array.isArray(data)) {
            heatmapData = [];
            if (overlay) overlay.setData([]);
            return;
        }
        heatmapData = data;
        if (overlay) overlay.setData(heatmapData);
    }

    /**
     * @brief 设置启用状态 / Set enabled state.
     * @param {boolean} val 是否启用 / enabled
     * @returns {void}
     */
    function setEnabled(val) {
        enabled = !!val;
        if (overlay) overlay.setEnabled(enabled);
    }

    /**
     * @brief 获取启用状态 / Get enabled state.
     * @returns {boolean} enabled
     */
    function getEnabled() {
        return enabled;
    }

    /**
     * @brief 获取当前数据 / Get current data.
     * @returns {Array} shallow copied data
     */
    function getData() {
        return heatmapData.slice();
    }

    /**
     * @brief 清除热力图 / Clear heatmap.
     * @returns {void}
     */
    function clear() {
        heatmapData = [];
        if (overlay) overlay.setData([]);
    }

    /**
     * @brief 销毁渲染器 / Destroy renderer.
     * @returns {void}
     */
    function destroy() {
        if (overlay && mapInstance) {
            mapInstance.removeLayer(overlay);
        }
        overlay = null;
        mapInstance = null;
        heatmapData = [];
        enabled = false;
    }

    return {
        init,
        render,
        setEnabled,
        getEnabled,
        getData,
        clear,
        destroy
    };
})();

// CommonJS export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeatmapRenderer;
}

// Global attach
window.HeatmapRenderer = HeatmapRenderer;
