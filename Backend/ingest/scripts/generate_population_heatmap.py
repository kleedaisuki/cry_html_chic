#!/usr/bin/env python3
"""
生成新加坡人口热力图数据文件
"""

import json

# 新加坡55个规划区域中心坐标
SG_PLANNING_AREA_COORDS = {
    "ang mo kio": (1.3691, 103.8454),
    "bedok": (1.3236, 103.9273),
    "bishan": (1.3526, 103.8352),
    "bukit batok": (1.3590, 103.7637),
    "bukit merah": (1.2819, 103.8239),
    "bukit panjang": (1.3774, 103.7719),
    "bukit timah": (1.3294, 103.8021),
    "central water catch": (1.3403, 103.7880),
    "changi": (1.3380, 103.9871),
    "changi bay": (1.3362, 104.0037),
    "choa chu kang": (1.3840, 103.7470),
    "clementi": (1.3162, 103.7649),
    "downtown core": (1.2789, 103.8536),
    "geylang": (1.3201, 103.8918),
    "hougang": (1.3612, 103.8863),
    "jurong east": (1.3329, 103.7436),
    "jurong west": (1.3404, 103.7090),
    "kallang": (1.3100, 103.8651),
    "lim chu kang": (1.4305, 103.7174),
    "mandai": (1.4131, 103.8180),
    "marina south": (1.2705, 103.8638),
    "marine parade": (1.3020, 103.9072),
    "museum": (1.2998, 103.8354),
    "newton": (1.3294, 103.8354),
    "north-eastern islands": (1.2915, 103.8495),
    "orchard": (1.3045, 103.8328),
    "outram": (1.2889, 103.8376),
    "pasir ris": (1.3721, 103.9474),
    "paya lebar": (1.3570, 103.9153),
    "pioneer": (1.3254, 103.6782),
    "queenstown": (1.2942, 103.7861),
    "river valley": (1.2892, 103.8458),
    "rochor": (1.3045, 103.8558),
    "seletar": (1.4040, 103.8674),
    "sembawang": (1.4491, 103.8185),
    "sengkang": (1.3868, 103.8914),
    "serangoon": (1.3554, 103.8679),
    "southern islands": (1.2167, 103.8333),
    "straits view": (1.2645, 103.8558),
    "sungei kadut": (1.4230, 103.7645),
    "tampines": (1.3496, 103.9568),
    "tengah": (1.3920, 103.7360),
    "toa payoh": (1.3343, 103.8563),
    "tuas": (1.3060, 103.6350),
    "western islands": (1.2500, 103.8000),
    "western water catch": (1.3333, 103.7167),
    "woodlands": (1.4382, 103.7890),
    "yishun": (1.4304, 103.8354),
}

def normalize_name(name):
    """规范化区域名称"""
    name = name.strip().lower()
    # 移除常见后缀
    for suffix in [" - total", " town centre", " planning area"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name

def process_data(input_file, output_file):
    """处理数据并生成热力图文件"""
    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data.get('data', {}).get('result', {}).get('records', [])

    points = []
    vmin = None
    vmax = None
    vsum = 0.0
    skipped = 0

    SKIP_NAMES = {"total", "total resident", "total population"}

    for record in records:
        name_raw = record.get('Number', '')
        if not name_raw:
            continue

        name_norm = normalize_name(name_raw)

        # 跳过汇总行
        if name_norm in SKIP_NAMES:
            skipped += 1
            continue

        # 获取人口值
        try:
            value = int(record.get('Total_Total', '0').replace(',', ''))
        except (ValueError, TypeError):
            continue

        if value <= 0:
            continue

        # 查找坐标
        coords = SG_PLANNING_AREA_COORDS.get(name_norm)
        if coords is None:
            # 尝试模糊匹配
            coords = fuzzy_match(name_norm)
            if coords is None:
                skipped += 1
                continue

        lat, lon = coords
        points.append({
            "name": name_raw,
            "value": value,
            "lat": lat,
            "lon": lon
        })

        vmin = value if vmin is None else min(vmin, value)
        vmax = value if vmax is None else max(vmax, value)
        vsum += value

    # 生成输出
    output = {
        "ir_kind": "population_heatmap",
        "data": {
            "points": points,
            "stats": {
                "count": len(points),
                "min": vmin if vmin is not None else 0,
                "max": vmax if vmax is not None else 0,
                "sum": vsum,
                "skipped": skipped
            }
        }
    }

    # 写入 JS 文件
    js_content = f"""/**
 * 新加坡人口热力图数据
 * Singapore Population Heatmap Data
 *
 * 数据来源: data.gov.sg 人口普查 2020
 */

window.POPULATION_HEATMAP = {json.dumps(output, indent=4, ensure_ascii=False)};

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = window.POPULATION_HEATMAP;
}}
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"生成人口热力图数据: {len(points)} 个点")
    print(f"人口范围: {vmin:,} - {vmax:,}")
    print(f"总人口: {vsum:,.0f}")
    print(f"跳过: {skipped} 条记录")
    print(f"输出文件: {output_file}")

def fuzzy_match(name):
    """模糊匹配区域名称"""
    for key in SG_PLANNING_AREA_COORDS:
        if key in name or name in key:
            return SG_PLANNING_AREA_COORDS[key]
    return None

if __name__ == "__main__":
    input_file = "Backend/data/preprocessed/2026-01-07T001257Z-sg_heatmap-5836053c68fd5c40e01f7399ad34cbb8f04b842780ce3a60828d89c01afd62ca/artifacts/jsonfile/json_payload.json"
    output_file = "Frontend/data/population_heatmap.js"
    process_data(input_file, output_file)
