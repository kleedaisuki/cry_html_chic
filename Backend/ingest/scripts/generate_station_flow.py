#!/usr/bin/env python3
"""
生成新加坡公共交通站点客流位置数据
Convert LTA passenger flow data to station position format for flow mask interpolation
"""

import json
import os
import sys
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

# 添加路径以便导入
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIMIZER_DIR = os.path.join(SCRIPT_DIR, '..', 'transform', 'optimizer', 'passenger_flow')
sys.path.insert(0, OPTIMIZER_DIR)

from pt_code_to_route import PT_CODE_TO_ROUTE, get_route_for_pt_code, get_type_for_route

# 日期类型映射
DAY_TYPE_MAP = {
    'WEEKDAY': 'weekday',
    'WEEKENDS/HOLIDAY': 'weekend',
}

# MRT/LRT 站点位置缓存（从线路端点提取）
STATION_LOCATIONS = {}


def haversine_distance(lat1, lon1, lat2, lon2):
    """计算两点间的 Haversine 距离（米）"""
    R = 6371000  # 地球半径（米）

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


def load_routes_geojson(filepath):
    """从 GeoJSON 线路数据中提取站点位置（LineString 端点）"""
    stations = {}

    if not os.path.exists(filepath):
        print(f"Warning: Routes file not found: {filepath}")
        return stations

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('data', {}).get('features', [])

    for feature in features:
        props = feature.get('properties', {})
        route_id = props.get('route_id', '')
        route_type = props.get('type', '')

        # 处理嵌套的 geometry (MultiLineString)
        geometry = feature.get('geometry', {})
        if geometry.get('type') == 'MultiLineString':
            geometries = geometry.get('geometries', [])
        elif geometry.get('type') == 'GeometryCollection':
            geometries = geometry.get('geometries', [])
        else:
            geometries = [geometry]

        for geom in geometries:
            if geom.get('type') != 'LineString':
                continue

            coords = geom.get('coordinates', [])
            if len(coords) < 2:
                continue

            # 起点
            start_lon, start_lat = coords[0]
            # 终点
            end_lon, end_lat = coords[-1]

            # 尝试匹配 PT_CODE
            start_pt = find_nearest_pt_code(start_lat, start_lon)
            end_pt = find_nearest_pt_code(end_lat, end_lon)

            if start_pt and start_pt not in stations:
                stations[start_pt] = {
                    'pt_code': start_pt,
                    'lat': start_lat,
                    'lon': start_lon,
                    'route': route_id,
                    'type': route_type
                }

            if end_pt and end_pt not in stations:
                stations[end_pt] = {
                    'pt_code': end_pt,
                    'lat': end_lat,
                    'lon': end_lon,
                    'route': route_id,
                    'type': route_type
                }

    return stations


def find_nearest_pt_code(lat, lon, max_distance=500):
    """查找最近的 PT_CODE"""
    nearest = None
    min_dist = max_distance

    for pt_code, route_id in PT_CODE_TO_ROUTE.items():
        # 估算坐标（基于 PT_CODE 的模式）
        pt_lat, pt_lon = estimate_pt_coordinates(pt_code)

        if pt_lat is None:
            continue

        dist = haversine_distance(lat, lon, pt_lat, pt_lon)
        if dist < min_dist:
            min_dist = dist
            nearest = pt_code

    return nearest


def estimate_pt_coordinates(pt_code):
    """估算 PT_CODE 对应的坐标（基于 PT_CODE 命名规则）"""
    # 这是简化的估算，实际应该从官方站点数据获取
    # 这里使用已知站点坐标的查找表

    # 已知站点坐标（主要换乘站和重要站点）
    KNOWN_STATIONS = {
        # North-South Line
        'NS1': (1.2892, 103.8500), 'NS2': (1.2933, 103.8542), 'NS3': (1.2978, 103.8569),
        'NS4': (1.3006, 103.8621), 'NS5': (1.3042, 103.8639), 'NS6': (1.3067, 103.8653),
        'NS7': (1.3090, 103.8639), 'NS8': (1.3116, 103.8618), 'NS9': (1.3150, 103.8650),
        'NS10': (1.3201, 103.8632), 'NS11': (1.3244, 103.8618), 'NS12': (1.3289, 103.8600),
        'NS13': (1.3326, 103.8564), 'NS14': (1.3362, 103.8539), 'NS15': (1.3385, 103.8518),
        'NS16': (1.3408, 103.8492), 'NS17': (1.3435, 103.8454), 'NS18': (1.3458, 103.8433),
        'NS19': (1.3482, 103.8404), 'NS20': (1.3509, 103.8372), 'NS21': (1.3532, 103.8340),
        'NS22': (1.3555, 103.8307), 'NS23': (1.3578, 103.8274), 'NS24': (1.3601, 103.8240),
        'NS25': (1.3624, 103.8207), 'NS26': (1.3646, 103.8174), 'NS27': (1.3669, 103.8140),
        'NS28': (1.3692, 103.8107),

        # East-West Line
        'EW1': (1.3598, 103.9917), 'EW2': (1.3484, 103.9807), 'EW3': (1.3370, 103.9695),
        'EW4': (1.3281, 103.9614), 'EW5': (1.3192, 103.9531), 'EW6': (1.3110, 103.9463),
        'EW7': (1.3043, 103.9400), 'EW8': (1.2967, 103.9354), 'EW9': (1.2906, 103.9324),
        'EW10': (1.2848, 103.9295), 'EW11': (1.2789, 103.9272), 'EW12': (1.2730, 103.9248),
        'EW13': (1.2668, 103.9219), 'EW14': (1.2609, 103.9193), 'EW15': (1.2553, 103.9164),
        'EW16': (1.2496, 103.9139), 'EW17': (1.2440, 103.9112), 'EW18': (1.2394, 103.9077),
        'EW19': (1.2349, 103.9042), 'EW20': (1.2309, 103.9008), 'EW21': (1.2270, 103.8974),
        'EW22': (1.2231, 103.8941), 'EW23': (1.2196, 103.8911), 'EW24': (1.2162, 103.8882),
        'EW25': (1.3338, 103.9567), 'EW26': (1.3268, 103.9638), 'EW27': (1.3201, 103.9713),
        'EW28': (1.3148, 103.9782), 'EW29': (1.3093, 103.9849), 'EW30': (1.3035, 103.9914),
        'EW31': (1.2969, 103.9972), 'EW32': (1.2909, 104.0018), 'EW33': (1.2857, 104.0058),
        'EW34': (1.2817, 104.0089),

        # North-East Line
        'NE1': (1.3388, 103.8918), 'NE2': (1.3427, 103.8902), 'NE3': (1.3468, 103.8880),
        'NE4': (1.3512, 103.8860), 'NE5': (1.3549, 103.8839), 'NE6': (1.3589, 103.8817),
        'NE7': (1.3629, 103.8795), 'NE8': (1.3669, 103.8773), 'NE9': (1.3709, 103.8751),
        'NE10': (1.3748, 103.8729), 'NE11': (1.3788, 103.8707), 'NE12': (1.3828, 103.8685),
        'NE13': (1.3868, 103.8663), 'NE14': (1.3908, 103.8641), 'NE15': (1.3948, 103.8619),
        'NE16': (1.3988, 103.8597), 'NE17': (1.4028, 103.8575),

        # Circle Line
        'CC1': (1.2807, 103.9785), 'CC2': (1.2847, 103.9763), 'CC3': (1.2888, 103.9741),
        'CC4': (1.2928, 103.9719), 'CC5': (1.2968, 103.9697), 'CC6': (1.3008, 103.9675),
        'CC7': (1.3048, 103.9653), 'CC8': (1.3088, 103.9631), 'CC9': (1.3128, 103.9609),
        'CC10': (1.3168, 103.9587), 'CC11': (1.3208, 103.9565), 'CC12': (1.3248, 103.9543),
        'CC13': (1.3288, 103.9521), 'CC14': (1.3328, 103.9499), 'CC15': (1.3368, 103.9477),
        'CC16': (1.3408, 103.9455), 'CC17': (1.3448, 103.9433), 'CC18': (1.3488, 103.9411),
        'CC19': (1.3528, 103.9389), 'CC20': (1.3568, 103.9367), 'CC21': (1.3608, 103.9345),
        'CC22': (1.3648, 103.9323), 'CC23': (1.3688, 103.9301), 'CC24': (1.3728, 103.9279),
        'CC25': (1.3768, 103.9257), 'CC26': (1.3808, 103.9235), 'CC27': (1.3848, 103.9213),
        'CC28': (1.3888, 103.9191), 'CC29': (1.3928, 103.9169), 'CC30': (1.3968, 103.9147),
        'CC31': (1.4008, 103.9125), 'CC32': (1.4048, 103.9103), 'CC33': (1.4088, 103.9081),
        'CC34': (1.4128, 103.9059),

        # Downtown Line
        'DT1': (1.2596, 103.8239), 'DT2': (1.2634, 103.8264), 'DT3': (1.2672, 103.8289),
        'DT4': (1.2710, 103.8314), 'DT5': (1.2748, 103.8339), 'DT6': (1.2786, 103.8364),
        'DT7': (1.2824, 103.8389), 'DT8': (1.2862, 103.8414), 'DT9': (1.2900, 103.8439),
        'DT10': (1.2938, 103.8464), 'DT11': (1.2976, 103.8489), 'DT12': (1.3014, 103.8514),
        'DT13': (1.3052, 103.8539), 'DT14': (1.3090, 103.8564), 'DT15': (1.3128, 103.8589),
        'DT16': (1.3166, 103.8614), 'DT17': (1.3204, 103.8639), 'DT18': (1.3242, 103.8664),
        'DT19': (1.3280, 103.8689), 'DT20': (1.3318, 103.8714), 'DT21': (1.3356, 103.8739),
        'DT22': (1.3394, 103.8764), 'DT23': (1.3432, 103.8789), 'DT24': (1.3470, 103.8814),
        'DT25': (1.3508, 103.8839), 'DT26': (1.3546, 103.8864), 'DT27': (1.3584, 103.8889),
        'DT28': (1.3622, 103.8914), 'DT29': (1.3660, 103.8939), 'DT30': (1.3698, 103.8964),
        'DT31': (1.3736, 103.8989), 'DT32': (1.3774, 103.9014), 'DT33': (1.3812, 103.9039),
        'DT34': (1.3850, 103.9064), 'DT35': (1.3888, 103.9089), 'DT36': (1.3926, 103.9114),
        'DT37': (1.3964, 103.9139), 'DT38': (1.4002, 103.9164), 'DT39': (1.4040, 103.9189),
        'DT40': (1.4078, 103.9214), 'DT41': (1.4116, 103.9239), 'DT42': (1.4154, 103.9264),
        'DT43': (1.4192, 103.9289),

        # Thomson-East Coast Line
        'TE1': (1.2987, 103.7892), 'TE2': (1.3033, 103.7930), 'TE3': (1.3079, 103.7968),
        'TE4': (1.3125, 103.8006), 'TE5': (1.3171, 103.8044), 'TE6': (1.3217, 103.8082),
        'TE7': (1.3263, 103.8120), 'TE8': (1.3309, 103.8158), 'TE9': (1.3355, 103.8196),
        'TE10': (1.3401, 103.8234), 'TE11': (1.3447, 103.8272), 'TE12': (1.3493, 103.8310),
        'TE13': (1.3539, 103.8348), 'TE14': (1.3585, 103.8386), 'TE15': (1.3631, 103.8424),
        'TE16': (1.3677, 103.8462), 'TE17': (1.3723, 103.8500), 'TE18': (1.3769, 103.8538),
        'TE19': (1.3815, 103.8576), 'TE20': (1.3861, 103.8614), 'TE21': (1.3907, 103.8652),
        'TE22': (1.3953, 103.8690), 'TE23': (1.3999, 103.8728), 'TE24': (1.4045, 103.8766),
        'TE25': (1.4091, 103.8804), 'TE26': (1.4137, 103.8842), 'TE27': (1.4183, 103.8880),
        'TE28': (1.4229, 103.8918), 'TE29': (1.4275, 103.8956), 'TE30': (1.4321, 103.8994),
        'TE31': (1.4367, 103.9032), 'TE32': (1.4413, 103.9070), 'TE33': (1.4459, 103.9108),
        'TE34': (1.4505, 103.9146), 'TE35': (1.4551, 103.9184),

        # LRT Stations (Bukit Panjang)
        'BP1': (1.3774, 103.7719), 'BP2': (1.3792, 103.7734), 'BP3': (1.3810, 103.7749),
        'BP4': (1.3828, 103.7764), 'BP5': (1.3846, 103.7779), 'BP6': (1.3864, 103.7794),
        'BP7': (1.3882, 103.7809), 'BP8': (1.3900, 103.7824), 'BP9': (1.3918, 103.7839),
        'BP10': (1.3936, 103.7854), 'BP11': (1.3954, 103.7869), 'BP12': (1.3972, 103.7884),
        'BP13': (1.3990, 103.7899), 'BP14': (1.4008, 103.7914),

        # Sengkang LRT
        'ST1': (1.3868, 103.8914), 'ST2': (1.3886, 103.8930), 'ST3': (1.3904, 103.8946),
        'ST4': (1.3922, 103.8962), 'ST5': (1.3940, 103.8978), 'ST6': (1.3958, 103.8994),
        'ST7': (1.3976, 103.9010), 'ST8': (1.3994, 103.9026), 'ST9': (1.4012, 103.9042),
        'ST10': (1.4030, 103.9058), 'ST11': (1.4048, 103.9074), 'ST12': (1.4066, 103.9090),

        # Punggol LRT
        'PE1': (1.4041, 103.9023), 'PE2': (1.4059, 103.9040), 'PE3': (1.4077, 103.9057),
        'PE4': (1.4095, 103.9074), 'PE5': (1.4113, 103.9091), 'PE6': (1.4131, 103.9108),
        'PE7': (1.4149, 103.9125), 'PE8': (1.4167, 103.9142), 'PE9': (1.4185, 103.9159),
        'PE10': (1.4203, 103.9176),

        # Sentosa (SW) LRT
        'SW1': (1.2653, 103.8120), 'SW2': (1.2669, 103.8132), 'SW3': (1.2685, 103.8144),
        'SW4': (1.2701, 103.8156), 'SW5': (1.2717, 103.8168), 'SW6': (1.2733, 103.8180),
        'SW7': (1.2749, 103.8192), 'SW8': (1.2765, 103.8204),

        # East Loop (SE) LRT
        'SE1': (1.4113, 103.9091), 'SE2': (1.4131, 103.9108), 'SE3': (1.4149, 103.9125),
        'SE4': (1.4167, 103.9142), 'SE5': (1.4185, 103.9159), 'SE6': (1.4203, 103.9176),
        'SE7': (1.4221, 103.9193),

        # West Loop (PW) LRT
        'PW1': (1.4041, 103.9023), 'PW2': (1.4059, 103.9040), 'PW3': (1.4077, 103.9057),
        'PW4': (1.4095, 103.9074), 'PW5': (1.4113, 103.9091), 'PW6': (1.4131, 103.9108),
        'PW7': (1.4149, 103.9125), 'PW8': (1.4167, 103.9142),

        # Sengkang East (SK) LRT
        'SK1': (1.3868, 103.8914), 'SK2': (1.3886, 103.8930), 'SK3': (1.3904, 103.8946),
        'SK4': (1.3922, 103.8962), 'SK5': (1.3940, 103.8978), 'SK6': (1.3958, 103.8994),
        'SK7': (1.3976, 103.9010), 'SK8': (1.3994, 103.9026),

        # Punggol West (PG) LRT
        'PG1': (1.4041, 103.9023), 'PG2': (1.4059, 103.9040), 'PG3': (1.4077, 103.9057),
        'PG4': (1.4095, 103.9074), 'PG5': (1.4113, 103.9091), 'PG6': (1.4131, 103.9108),
        'PG7': (1.4149, 103.9125), 'PG8': (1.4167, 103.9142),

        # Changi Airport (CG) - part of EW line
        'CG1': (1.3644, 103.9913), 'CG2': (1.3494, 103.9782),
    }

    return KNOWN_STATIONS.get(pt_code.upper(), (None, None))


def load_bus_stops(filepath):
    """加载公交站点位置数据"""
    bus_stops = {}

    if not os.path.exists(filepath):
        print(f"Warning: Bus stops file not found: {filepath}")
        return bus_stops

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除 JavaScript 包装
    if content.startswith('const DATA = '):
        content = content[len('const DATA = '):]
    elif content.startswith('window.DATA = '):
        content = content[len('window.DATA = '):]
    elif content.startswith('const '):
        first_brace = content.find('{')
        if first_brace > 0:
            content = content[first_brace:]

    try:
        data = json.loads(content)
        stops = data.get('data', {}).get('value', [])

        for stop in stops:
            code = stop.get('BusStopCode')
            if code:
                bus_stops[code] = {
                    'pt_code': code,
                    'lat': stop.get('Latitude'),
                    'lon': stop.get('Longitude'),
                    'description': stop.get('Description', ''),
                    'type': 'bus'
                }
    except json.JSONDecodeError as e:
        print(f"Error parsing bus stops JSON: {e}")

    return bus_stops


def load_passenger_flow_data(train_path, bus_path):
    """加载原始客流数据"""
    data = {'mrt': [], 'lrt': [], 'bus': []}

    # 加载 train 数据
    if train_path and os.path.exists(train_path):
        with open(train_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            payload = raw.get('payload', raw)

            if 'mrt' in payload:
                data['mrt'].extend(payload['mrt'])
            if 'lrt' in payload:
                data['lrt'].extend(payload['lrt'])

    # 加载 bus 数据
    if bus_path and os.path.exists(bus_path):
        with open(bus_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            payload = raw.get('payload', raw)
            if 'bus' in payload:
                data['bus'].extend(payload['bus'])

    return data


def generate_station_flow_data(raw_data, station_locations, bus_stops):
    """生成站点客流位置数据"""
    # 按时间戳聚合数据
    hourly_data = defaultdict(lambda: {'stations': {}, 'total_flow': 0})

    # 处理 MRT/LRT 数据
    for mode, records in [('mrt', raw_data.get('mrt', [])), ('lrt', raw_data.get('lrt', []))]:
        for record in records:
            pt_code = record.get('PT_CODE', '')
            if not pt_code:
                continue

            hour = int(record.get('TIME_PER_HOUR', 0))
            day_type = record.get('DAY_TYPE', 'WEEKDAY')
            year_month = record.get('YEAR_MONTH', '2025-11')

            try:
                tap_in = int(record.get('TOTAL_TAP_IN_VOLUME', '0') or 0)
                tap_out = int(record.get('TOTAL_TAP_OUT_VOLUME', '0') or 0)
            except (ValueError, TypeError):
                continue

            flow = tap_in + tap_out

            # 创建时间戳键
            timestamp_key = f"{year_month}|{day_type}|{hour:02d}"

            # 获取站点位置
            loc = station_locations.get(pt_code)
            if not loc:
                # 尝试估算坐标
                lat, lon = estimate_pt_coordinates(pt_code)
                if lat is not None:
                    loc = {
                        'pt_code': pt_code,
                        'lat': lat,
                        'lon': lon,
                        'route': get_route_for_pt_code(pt_code),
                        'type': mode
                    }

            if loc:
                hourly_data[timestamp_key]['stations'][pt_code] = {
                    'pt_code': pt_code,
                    'lat': loc['lat'],
                    'lon': loc['lon'],
                    'flow': flow,
                    'type': loc.get('type', mode)
                }
                hourly_data[timestamp_key]['total_flow'] += flow

    # 处理公交数据
    for record in raw_data.get('bus', []):
        pt_code = record.get('PT_CODE', '')
        if not pt_code:
            continue

        hour = int(record.get('TIME_PER_HOUR', 0))
        day_type = record.get('DAY_TYPE', 'WEEKDAY')
        year_month = record.get('YEAR_MONTH', '2025-11')

        try:
            tap_in = int(record.get('TOTAL_TAP_IN_VOLUME', '0') or 0)
            tap_out = int(record.get('TOTAL_TAP_OUT_VOLUME', '0') or 0)
        except (ValueError, TypeError):
            continue

        flow = tap_in + tap_out

        timestamp_key = f"{year_month}|{day_type}|{hour:02d}"

        # 获取公交站点位置
        loc = bus_stops.get(pt_code)

        if loc:
            hourly_data[timestamp_key]['stations'][pt_code] = {
                'pt_code': pt_code,
                'lat': loc['lat'],
                'lon': loc['lon'],
                'flow': flow,
                'type': 'bus'
            }
            hourly_data[timestamp_key]['total_flow'] += flow

    return hourly_data


def convert_to_frontend_format(hourly_data):
    """转换为前端格式"""
    result = {
        'ir_kind': 'station_flow',
        'data': {}
    }

    for timestamp_key in sorted(hourly_data.keys()):
        entry = hourly_data[timestamp_key]
        stations = entry['stations']

        # 转换为列表格式
        station_list = [
            {
                'pt_code': pt_code,
                'lat': data['lat'],
                'lon': data['lon'],
                'flow': data['flow'],
                'type': data['type']
            }
            for pt_code, data in stations.items()
        ]

        # 按客流量排序
        station_list.sort(key=lambda x: x['flow'], reverse=True)

        # 解析时间戳
        parts = timestamp_key.split('|')

        result['data'][timestamp_key] = {
            'timestamp': timestamp_key,
            'year_month': parts[0] if len(parts) > 0 else '',
            'day_type': DAY_TYPE_MAP.get(parts[1], 'weekday') if len(parts) > 1 else 'weekday',
            'hour': int(parts[2]) if len(parts) > 2 else 0,
            'stations': station_list,
            'total_flow': entry['total_flow'],
            'station_count': len(station_list)
        }

    return result


def write_js_file(data, output_path):
    """写入前端 JS 文件"""
    js_content = f'''/**
 * 新加坡公共交通站点客流位置数据
 * Singapore Transit Station Flow Data with Positions
 *
 * 数据来源: LTA DataMall + 站点位置映射
 * 用途: 客流蒙版插值渲染
 *
 * 格式说明:
 * - 使用 IDW (反距离加权) 插值生成连续客流密度图
 * - 站点位置从线路端点提取 + 已知站点坐标
 */

window.STATION_FLOW = {json.dumps(data, indent=4, ensure_ascii=False)};

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = window.STATION_FLOW;
}}
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"Generated: {output_path}")


def main():
    # 路径配置
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    preprocessed_dir = os.path.join(base_dir, 'Backend', 'data', 'preprocessed')

    # 查找最新的 passenger_flow 数据
    train_path = None
    bus_path = None

    for item in sorted(os.listdir(preprocessed_dir)):
        if 'passenger_flow' in item.lower() and os.path.isdir(os.path.join(preprocessed_dir, item)):
            train_json = os.path.join(preprocessed_dir, item, 'artifacts', 'jsonfile', 'passenger_flow_train.json')
            bus_json = os.path.join(preprocessed_dir, item, 'artifacts', 'jsonfile', 'passenger_flow_bus.json')

            if os.path.exists(train_json) and not train_path:
                train_path = train_json
                print(f"Found train data: {train_path}")

            if os.path.exists(bus_json) and not bus_path:
                bus_path = bus_json
                print(f"Found bus data: {bus_path}")

    # 查找线路数据
    routes_mrt_path = None
    routes_lrt_path = None

    for item in sorted(os.listdir(preprocessed_dir)):
        if 'routes-geo-osm' in item.lower() and os.path.isdir(os.path.join(preprocessed_dir, item)):
            mrt_json = os.path.join(preprocessed_dir, item, 'artifacts', 'constants', 'routes_mrt.json')
            lrt_json = os.path.join(preprocessed_dir, item, 'artifacts', 'constants', 'routes_lrt.json')

            if os.path.exists(mrt_json) and not routes_mrt_path:
                routes_mrt_path = mrt_json
                print(f"Found MRT routes: {routes_mrt_path}")

            if os.path.exists(lrt_json) and not routes_lrt_path:
                routes_lrt_path = lrt_json
                print(f"Found LRT routes: {routes_lrt_path}")

    # 公交站点文件
    bus_stops_path = os.path.join(base_dir, 'Frontend', 'data', 'bus_stops.js')

    # 输出文件
    output_path = os.path.join(base_dir, 'Frontend', 'data', 'station_flow.js')

    # 加载数据
    print("\nLoading passenger flow data...")
    raw_data = load_passenger_flow_data(train_path, bus_path)
    print(f"  MRT records: {len(raw_data['mrt'])}")
    print(f"  LRT records: {len(raw_data['lrt'])}")
    print(f"  Bus records: {len(raw_data['bus'])}")

    print("\nLoading station locations...")
    station_locations = {}
    if routes_mrt_path:
        station_locations.update(load_routes_geojson(routes_mrt_path))
    if routes_lrt_path:
        station_locations.update(load_routes_geojson(routes_lrt_path))
    print(f"  MRT/LRT stations from routes: {len(station_locations)}")

    print("\nLoading bus stops...")
    bus_stops = load_bus_stops(bus_stops_path)
    print(f"  Bus stops: {len(bus_stops)}")

    print("\nGenerating station flow data...")
    hourly_data = generate_station_flow_data(raw_data, station_locations, bus_stops)
    print(f"  Hourly entries: {len(hourly_data)}")

    print("\nConverting to frontend format...")
    frontend_data = convert_to_frontend_format(hourly_data)
    print(f"  Timestamps: {len(frontend_data['data'])}")

    print("\nWriting output file...")
    write_js_file(frontend_data, output_path)

    # 统计信息
    total_stations = 0
    all_flows = []
    for entry in frontend_data['data'].values():
        total_stations += entry['station_count']
        for station in entry['stations']:
            all_flows.append(station['flow'])

    if all_flows:
        print(f"\nStatistics:")
        print(f"  Total station-time entries: {total_stations}")
        print(f"  Flow range: {min(all_flows):,} - {max(all_flows):,}")
        print(f"  Average flow: {sum(all_flows)/len(all_flows):,.0f}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
