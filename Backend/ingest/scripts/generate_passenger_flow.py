#!/usr/bin/env python3
"""
生成新加坡公共交通客流数据前端文件
Convert LTA passenger flow data to frontend format
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 添加路径以便导入 pt_code_to_route
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIMIZER_DIR = os.path.join(SCRIPT_DIR, '..', 'transform', 'optimizer', 'passenger_flow')
sys.path.insert(0, OPTIMIZER_DIR)

from pt_code_to_route import get_route_for_pt_code, get_type_for_route


# 线路容量配置（估算值）
ROUTE_CAPACITY = {
    'NS_LINE': 28000,   # 6辆编组，每辆约500人
    'EW_LINE': 28000,
    'NE_LINE': 19000,   # 4辆编组
    'CC_LINE': 19000,
    'DT_LINE': 19000,
    'TE_LINE': 19000,
    'BP_LRT': 6000,     # 单车厢
    'ST_LRT': 6000,
    'PE_LRT': 6000,
    'SW_LRT': 6000,
    'SE_LRT': 6000,
    'PW_LRT': 6000,
    'SK_LRT': 6000,
    'PG_LRT': 6000,
}

# 日期类型映射
DAY_TYPE_MAP = {
    'WEEKDAY': 'weekday',
    'WEEKENDS/HOLIDAY': 'weekend',
}


def load_raw_data(train_path, bus_path):
    """加载原始客流数据"""
    data = {
        'mrt': [],
        'lrt': [],
        'bus': []
    }

    # 加载 train 数据
    if os.path.exists(train_path):
        with open(train_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            payload = raw.get('payload', raw)

            # 提取 mrt 和 lrt 数据
            if 'mrt' in payload:
                data['mrt'].extend(payload['mrt'])
            if 'lrt' in payload:
                data['lrt'].extend(payload['lrt'])

    # 加载 bus 数据
    if os.path.exists(bus_path):
        with open(bus_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            payload = raw.get('payload', raw)
            if 'bus' in payload:
                data['bus'].extend(payload['bus'])

    return data


def aggregate_by_route(raw_data):
    """将站点级数据聚合到线路级"""
    # 按 线路-小时-日期类型 聚合
    aggregated = defaultdict(lambda: {
        'tap_in': 0,
        'tap_out': 0,
        'count': 0
    })

    for mode, records in raw_data.items():
        for record in records:
            pt_code = record.get('PT_CODE', '')
            route_id = get_route_for_pt_code(pt_code)

            if not route_id:
                continue

            hour = int(record.get('TIME_PER_HOUR', record.get('_hour', 0)))
            day_type = record.get('DAY_TYPE', 'WEEKDAY')

            try:
                tap_in = int(record.get('TOTAL_TAP_IN_VOLUME', '0'))
                tap_out = int(record.get('TOTAL_TAP_OUT_VOLUME', '0'))
            except (ValueError, TypeError):
                continue

            key = f"{route_id}|{hour}|{day_type}"
            aggregated[key]['tap_in'] += tap_in
            aggregated[key]['tap_out'] += tap_out
            aggregated[key]['count'] += 1

    return aggregated


def generate_hourly_data(aggregated, base_date='2024-01-01'):
    """生成每小时数据"""
    hourly_data = {}

    # 获取所有唯一的 (hour, day_type) 组合
    hour_day_combos = set()
    for key in aggregated.keys():
        parts = key.split('|')
        if len(parts) == 3:
            hour_day_combos.add((int(parts[1]), parts[2]))

    for hour, day_type in sorted(hour_day_combos):
        # 创建时间戳
        timestamp = f"{base_date}T{hour:02d}:00:00"
        day_type_key = DAY_TYPE_MAP.get(day_type, 'weekday')

        # 收集该小时所有线路的数据
        route_flows = []
        total_flow = 0

        for key, values in aggregated.items():
            parts = key.split('|')
            if len(parts) == 3 and int(parts[1]) == hour and parts[2] == day_type:
                route_id = parts[0]
                route_type = get_type_for_route(route_id)
                capacity = ROUTE_CAPACITY.get(route_id, 10000)

                # 使用进站+出站客流，取平均值作为线路客流
                flow = (values['tap_in'] + values['tap_out']) // max(values['count'], 1)
                utilization = min(flow / capacity, 1.0)

                route_flows.append({
                    'route_id': route_id,
                    'type': route_type,
                    'flow': flow,
                    'capacity': capacity,
                    'utilization': round(utilization, 2)
                })
                total_flow += flow

        # 按客流量排序
        route_flows.sort(key=lambda x: x['flow'], reverse=True)

        if route_flows:
            hourly_data[f"{timestamp}|{day_type_key}"] = {
                'timestamp': timestamp,
                'day_type': day_type_key,
                'data': route_flows,
                'total_flow': total_flow
            }

    return hourly_data


def convert_to_frontend_format(hourly_data):
    """转换为前端期望的格式"""
    result = {
        'ir_kind': 'passenger_flow',
        'data': {}
    }

    for key, value in sorted(hourly_data.items()):
        timestamp = value['timestamp']
        result['data'][timestamp] = {
            'timestamp': timestamp,
            'day_type': value['day_type'],
            'data': value['data'],
            'total_flow': value['total_flow']
        }

    return result


def write_js_file(data, output_path):
    """写入前端JS文件"""
    js_content = f'''/**
 * 新加坡公共交通客流数据
 * Singapore Transit Passenger Flow Data
 *
 * 数据来源: LTA DataMall - Public Transport Passenger Volume
 * 数据处理: 从站点级数据聚合到线路级
 */

window.PASSENGER_FLOW = {json.dumps(data, indent=4, ensure_ascii=False)};

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = window.PASSENGER_FLOW;
}}
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"Generated: {output_path}")


def main():
    # 路径配置
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # 查找最新的 passenger_flow 数据目录
    preprocessed_dir = os.path.join(base_dir, 'Backend', 'data', 'preprocessed')

    train_path = None
    bus_path = None

    # 查找 train 数据
    for item in os.listdir(preprocessed_dir):
        if 'passenger_flow' in item.lower() and os.path.isdir(os.path.join(preprocessed_dir, item)):
            json_path = os.path.join(preprocessed_dir, item, 'artifacts', 'jsonfile', 'passenger_flow_train.json')
            if os.path.exists(json_path):
                train_path = json_path
                print(f"Found train data: {train_path}")

            bus_json_path = os.path.join(preprocessed_dir, item, 'artifacts', 'jsonfile', 'passenger_flow_bus.json')
            if os.path.exists(bus_json_path):
                bus_path = bus_json_path
                print(f"Found bus data: {bus_path}")

    if not train_path:
        print("Error: Could not find passenger flow train data")
        return 1

    output_path = os.path.join(base_dir, 'Frontend', 'data', 'passenger_flow.js')

    print("Loading raw data...")
    raw_data = load_raw_data(train_path, bus_path)
    print(f"  MRT records: {len(raw_data['mrt'])}")
    print(f"  LRT records: {len(raw_data['lrt'])}")
    print(f"  Bus records: {len(raw_data['bus'])}")

    print("Aggregating by route...")
    aggregated = aggregate_by_route(raw_data)
    print(f"  Aggregated entries: {len(aggregated)}")

    print("Generating hourly data...")
    hourly_data = generate_hourly_data(aggregated)
    print(f"  Hourly entries: {len(hourly_data)}")

    print("Converting to frontend format...")
    frontend_data = convert_to_frontend_format(hourly_data)
    print(f"  Timestamps: {len(frontend_data['data'])}")

    print("Writing output file...")
    write_js_file(frontend_data, output_path)

    # 统计信息
    all_flows = []
    for entry in frontend_data['data'].values():
        for route in entry['data']:
            all_flows.append(route['flow'])

    if all_flows:
        print(f"\nStatistics:")
        print(f"  Total routes: {len(set(r['route_id'] for e in frontend_data['data'].values() for r in e['data']))}")
        print(f"  Flow range: {min(all_flows):,} - {max(all_flows):,}")
        print(f"  Average flow: {sum(all_flows)/len(all_flows):,.0f}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
