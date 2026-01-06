/**
 * 新加坡公共交通客流数据
 * Singapore Transit Passenger Flow Data
 *
 * 数据格式：每小时客流数据
 */

window.PASSENGER_FLOW = {
    "ir_kind": "passenger_flow",
    "data": {
        // ==========================================
        // 6:00 AM - 早高峰开始
        // ==========================================
        "2024-01-01T06:00:00": {
            "timestamp": "2024-01-01T06:00:00",
            "data": [
                // MRT Lines
                { "route_id": "NS_LINE", "type": "mrt", "flow": 4200, "capacity": 12000, "utilization": 0.35 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 3800, "capacity": 12000, "utilization": 0.32 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 2100, "capacity": 10000, "utilization": 0.21 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 1800, "capacity": 10000, "utilization": 0.18 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 1500, "capacity": 10000, "utilization": 0.15 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 800, "capacity": 10000, "utilization": 0.08 },
                // LRT Lines
                { "route_id": "BP_LRT", "type": "lrt", "flow": 450, "capacity": 3500, "utilization": 0.13 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 380, "capacity": 3500, "utilization": 0.11 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 320, "capacity": 3500, "utilization": 0.09 },
                // Bus Routes (sample)
                { "route_id": "BUS_96", "type": "bus", "flow": 180, "capacity": 800, "utilization": 0.23 },
                { "route_id": "BUS_97", "type": "bus", "flow": 150, "capacity": 800, "utilization": 0.19 },
                { "route_id": "BUS_106", "type": "bus", "flow": 200, "capacity": 800, "utilization": 0.25 },
                { "route_id": "BUS_161", "type": "bus", "flow": 165, "capacity": 800, "utilization": 0.21 },
                { "route_id": "BUS_188", "type": "bus", "flow": 190, "capacity": 800, "utilization": 0.24 }
            ],
            "total_flow": 17130
        },

        // ==========================================
        // 7:00 AM - 早高峰
        // ==========================================
        "2024-01-01T07:00:00": {
            "timestamp": "2024-01-01T07:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 8500, "capacity": 12000, "utilization": 0.71 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 8200, "capacity": 12000, "utilization": 0.68 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 4500, "capacity": 10000, "utilization": 0.45 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 3800, "capacity": 10000, "utilization": 0.38 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 3200, "capacity": 10000, "utilization": 0.32 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1800, "capacity": 10000, "utilization": 0.18 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1200, "capacity": 3500, "utilization": 0.34 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 980, "capacity": 3500, "utilization": 0.28 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 850, "capacity": 3500, "utilization": 0.24 },
                { "route_id": "BUS_96", "type": "bus", "flow": 450, "capacity": 800, "utilization": 0.56 },
                { "route_id": "BUS_97", "type": "bus", "flow": 380, "capacity": 800, "utilization": 0.48 },
                { "route_id": "BUS_106", "type": "bus", "flow": 520, "capacity": 800, "utilization": 0.65 },
                { "route_id": "BUS_161", "type": "bus", "flow": 420, "capacity": 800, "utilization": 0.53 },
                { "route_id": "BUS_188", "type": "bus", "flow": 480, "capacity": 800, "utilization": 0.60 }
            ],
            "total_flow": 40280
        },

        // ==========================================
        // 8:00 AM - 早高峰高峰
        // ==========================================
        "2024-01-01T08:00:00": {
            "timestamp": "2024-01-01T08:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 11200, "capacity": 12000, "utilization": 0.93 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 10800, "capacity": 12000, "utilization": 0.90 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 5800, "capacity": 10000, "utilization": 0.58 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 4800, "capacity": 10000, "utilization": 0.48 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 4100, "capacity": 10000, "utilization": 0.41 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 2500, "capacity": 10000, "utilization": 0.25 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1800, "capacity": 3500, "utilization": 0.51 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 1500, "capacity": 3500, "utilization": 0.43 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 1300, "capacity": 3500, "utilization": 0.37 },
                { "route_id": "BUS_96", "type": "bus", "flow": 680, "capacity": 800, "utilization": 0.85 },
                { "route_id": "BUS_97", "type": "bus", "flow": 590, "capacity": 800, "utilization": 0.74 },
                { "route_id": "BUS_106", "type": "bus", "flow": 720, "capacity": 800, "utilization": 0.90 },
                { "route_id": "BUS_161", "type": "bus", "flow": 650, "capacity": 800, "utilization": 0.81 },
                { "route_id": "BUS_188", "type": "bus", "flow": 700, "capacity": 800, "utilization": 0.88 }
            ],
            "total_flow": 53140
        },

        // ==========================================
        // 9:00 AM - 早高峰结束
        // ==========================================
        "2024-01-01T09:00:00": {
            "timestamp": "2024-01-01T09:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 7800, "capacity": 12000, "utilization": 0.65 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 7200, "capacity": 12000, "utilization": 0.60 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 3800, "capacity": 10000, "utilization": 0.38 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 3200, "capacity": 10000, "utilization": 0.32 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 2800, "capacity": 10000, "utilization": 0.28 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1600, "capacity": 10000, "utilization": 0.16 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1400, "capacity": 3500, "utilization": 0.40 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 1100, "capacity": 3500, "utilization": 0.31 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 950, "capacity": 3500, "utilization": 0.27 },
                { "route_id": "BUS_96", "type": "bus", "flow": 520, "capacity": 800, "utilization": 0.65 },
                { "route_id": "BUS_97", "type": "bus", "flow": 450, "capacity": 800, "utilization": 0.56 },
                { "route_id": "BUS_106", "type": "bus", "flow": 580, "capacity": 800, "utilization": 0.73 },
                { "route_id": "BUS_161", "type": "bus", "flow": 490, "capacity": 800, "utilization": 0.61 },
                { "route_id": "BUS_188", "type": "bus", "flow": 540, "capacity": 800, "utilization": 0.68 }
            ],
            "total_flow": 35930
        },

        // ==========================================
        // 10:00 AM - 平峰时段
        // ==========================================
        "2024-01-01T10:00:00": {
            "timestamp": "2024-01-01T10:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 4500, "capacity": 12000, "utilization": 0.38 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 4200, "capacity": 12000, "utilization": 0.35 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 2500, "capacity": 10000, "utilization": 0.25 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 2200, "capacity": 10000, "utilization": 0.22 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 1800, "capacity": 10000, "utilization": 0.18 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1000, "capacity": 10000, "utilization": 0.10 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 800, "capacity": 3500, "utilization": 0.23 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 650, "capacity": 3500, "utilization": 0.19 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 580, "capacity": 3500, "utilization": 0.17 },
                { "route_id": "BUS_96", "type": "bus", "flow": 280, "capacity": 800, "utilization": 0.35 },
                { "route_id": "BUS_97", "type": "bus", "flow": 240, "capacity": 800, "utilization": 0.30 },
                { "route_id": "BUS_106", "type": "bus", "flow": 320, "capacity": 800, "utilization": 0.40 },
                { "route_id": "BUS_161", "type": "bus", "flow": 260, "capacity": 800, "utilization": 0.33 },
                { "route_id": "BUS_188", "type": "bus", "flow": 300, "capacity": 800, "utilization": 0.38 }
            ],
            "total_flow": 22630
        },

        // ==========================================
        // 12:00 PM - 午间平峰
        // ==========================================
        "2024-01-01T12:00:00": {
            "timestamp": "2024-01-01T12:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 5200, "capacity": 12000, "utilization": 0.43 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 4800, "capacity": 12000, "utilization": 0.40 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 2800, "capacity": 10000, "utilization": 0.28 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 2500, "capacity": 10000, "utilization": 0.25 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 2100, "capacity": 10000, "utilization": 0.21 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1200, "capacity": 10000, "utilization": 0.12 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 750, "capacity": 3500, "utilization": 0.21 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 620, "capacity": 3500, "utilization": 0.18 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 550, "capacity": 3500, "utilization": 0.16 },
                { "route_id": "BUS_96", "type": "bus", "flow": 320, "capacity": 800, "utilization": 0.40 },
                { "route_id": "BUS_97", "type": "bus", "flow": 280, "capacity": 800, "utilization": 0.35 },
                { "route_id": "BUS_106", "type": "bus", "flow": 360, "capacity": 800, "utilization": 0.45 },
                { "route_id": "BUS_161", "type": "bus", "flow": 300, "capacity": 800, "utilization": 0.38 },
                { "route_id": "BUS_188", "type": "bus", "flow": 340, "capacity": 800, "utilization": 0.43 }
            ],
            "total_flow": 26120
        },

        // ==========================================
        // 2:00 PM - 下午平峰
        // ==========================================
        "2024-01-01T14:00:00": {
            "timestamp": "2024-01-01T14:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 4800, "capacity": 12000, "utilization": 0.40 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 4400, "capacity": 12000, "utilization": 0.37 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 2600, "capacity": 10000, "utilization": 0.26 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 2300, "capacity": 10000, "utilization": 0.23 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 1900, "capacity": 10000, "utilization": 0.19 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1100, "capacity": 10000, "utilization": 0.11 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 700, "capacity": 3500, "utilization": 0.20 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 580, "capacity": 3500, "utilization": 0.17 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 520, "capacity": 3500, "utilization": 0.15 },
                { "route_id": "BUS_96", "type": "bus", "flow": 290, "capacity": 800, "utilization": 0.36 },
                { "route_id": "BUS_97", "type": "bus", "flow": 250, "capacity": 800, "utilization": 0.31 },
                { "route_id": "BUS_106", "type": "bus", "flow": 330, "capacity": 800, "utilization": 0.41 },
                { "route_id": "BUS_161", "type": "bus", "flow": 270, "capacity": 800, "utilization": 0.34 },
                { "route_id": "BUS_188", "type": "bus", "flow": 310, "capacity": 800, "utilization": 0.39 }
            ],
            "total_flow": 24050
        },

        // ==========================================
        // 5:00 PM - 晚高峰开始
        // ==========================================
        "2024-01-01T17:00:00": {
            "timestamp": "2024-01-01T17:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 9500, "capacity": 12000, "utilization": 0.79 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 9200, "capacity": 12000, "utilization": 0.77 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 5200, "capacity": 10000, "utilization": 0.52 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 4200, "capacity": 10000, "utilization": 0.42 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 3600, "capacity": 10000, "utilization": 0.36 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 2200, "capacity": 10000, "utilization": 0.22 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1600, "capacity": 3500, "utilization": 0.46 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 1350, "capacity": 3500, "utilization": 0.39 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 1180, "capacity": 3500, "utilization": 0.34 },
                { "route_id": "BUS_96", "type": "bus", "flow": 620, "capacity": 800, "utilization": 0.78 },
                { "route_id": "BUS_97", "type": "bus", "flow": 540, "capacity": 800, "utilization": 0.68 },
                { "route_id": "BUS_106", "type": "bus", "flow": 680, "capacity": 800, "utilization": 0.85 },
                { "route_id": "BUS_161", "type": "bus", "flow": 580, "capacity": 800, "utilization": 0.73 },
                { "route_id": "BUS_188", "type": "bus", "flow": 640, "capacity": 800, "utilization": 0.80 }
            ],
            "total_flow": 48190
        },

        // ==========================================
        // 6:00 PM - 晚高峰高峰
        // ==========================================
        "2024-01-01T18:00:00": {
            "timestamp": "2024-01-01T18:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 10800, "capacity": 12000, "utilization": 0.90 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 10400, "capacity": 12000, "utilization": 0.87 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 6200, "capacity": 10000, "utilization": 0.62 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 5100, "capacity": 10000, "utilization": 0.51 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 4300, "capacity": 10000, "utilization": 0.43 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 2800, "capacity": 10000, "utilization": 0.28 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1950, "capacity": 3500, "utilization": 0.56 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 1620, "capacity": 3500, "utilization": 0.46 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 1420, "capacity": 3500, "utilization": 0.41 },
                { "route_id": "BUS_96", "type": "bus", "flow": 720, "capacity": 800, "utilization": 0.90 },
                { "route_id": "BUS_97", "type": "bus", "flow": 640, "capacity": 800, "utilization": 0.80 },
                { "route_id": "BUS_106", "type": "bus", "flow": 760, "capacity": 800, "utilization": 0.95 },
                { "route_id": "BUS_161", "type": "bus", "flow": 690, "capacity": 800, "utilization": 0.86 },
                { "route_id": "BUS_188", "type": "bus", "flow": 740, "capacity": 800, "utilization": 0.93 }
            ],
            "total_flow": 56140
        },

        // ==========================================
        // 7:00 PM - 晚高峰结束
        // ==========================================
        "2024-01-01T19:00:00": {
            "timestamp": "2024-01-01T19:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 7200, "capacity": 12000, "utilization": 0.60 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 6800, "capacity": 12000, "utilization": 0.57 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 3800, "capacity": 10000, "utilization": 0.38 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 3200, "capacity": 10000, "utilization": 0.32 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 2700, "capacity": 10000, "utilization": 0.27 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 1600, "capacity": 10000, "utilization": 0.16 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 1300, "capacity": 3500, "utilization": 0.37 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 1050, "capacity": 3500, "utilization": 0.30 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 920, "capacity": 3500, "utilization": 0.26 },
                { "route_id": "BUS_96", "type": "bus", "flow": 480, "capacity": 800, "utilization": 0.60 },
                { "route_id": "BUS_97", "type": "bus", "flow": 420, "capacity": 800, "utilization": 0.53 },
                { "route_id": "BUS_106", "type": "bus", "flow": 540, "capacity": 800, "utilization": 0.68 },
                { "route_id": "BUS_161", "type": "bus", "flow": 450, "capacity": 800, "utilization": 0.56 },
                { "route_id": "BUS_188", "type": "bus", "flow": 500, "capacity": 800, "utilization": 0.63 }
            ],
            "total_flow": 36160
        },

        // ==========================================
        // 9:00 PM - 晚间平峰
        // ==========================================
        "2024-01-01T21:00:00": {
            "timestamp": "2024-01-01T21:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 3800, "capacity": 12000, "utilization": 0.32 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 3500, "capacity": 12000, "utilization": 0.29 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 2000, "capacity": 10000, "utilization": 0.20 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 1800, "capacity": 10000, "utilization": 0.18 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 1500, "capacity": 10000, "utilization": 0.15 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 850, "capacity": 10000, "utilization": 0.09 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 650, "capacity": 3500, "utilization": 0.19 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 520, "capacity": 3500, "utilization": 0.15 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 460, "capacity": 3500, "utilization": 0.13 },
                { "route_id": "BUS_96", "type": "bus", "flow": 220, "capacity": 800, "utilization": 0.28 },
                { "route_id": "BUS_97", "type": "bus", "flow": 180, "capacity": 800, "utilization": 0.23 },
                { "route_id": "BUS_106", "type": "bus", "flow": 250, "capacity": 800, "utilization": 0.31 },
                { "route_id": "BUS_161", "type": "bus", "flow": 200, "capacity": 800, "utilization": 0.25 },
                { "route_id": "BUS_188", "type": "bus", "flow": 230, "capacity": 800, "utilization": 0.29 }
            ],
            "total_flow": 18160
        },

        // ==========================================
        // 11:00 PM - 夜间时段
        // ==========================================
        "2024-01-01T23:00:00": {
            "timestamp": "2024-01-01T23:00:00",
            "data": [
                { "route_id": "NS_LINE", "type": "mrt", "flow": 1800, "capacity": 12000, "utilization": 0.15 },
                { "route_id": "EW_LINE", "type": "mrt", "flow": 1600, "capacity": 12000, "utilization": 0.13 },
                { "route_id": "NE_LINE", "type": "mrt", "flow": 900, "capacity": 10000, "utilization": 0.09 },
                { "route_id": "CC_LINE", "type": "mrt", "flow": 800, "capacity": 10000, "utilization": 0.08 },
                { "route_id": "DT_LINE", "type": "mrt", "flow": 650, "capacity": 10000, "utilization": 0.07 },
                { "route_id": "TE_LINE", "type": "mrt", "flow": 380, "capacity": 10000, "utilization": 0.04 },
                { "route_id": "BP_LRT", "type": "lrt", "flow": 280, "capacity": 3500, "utilization": 0.08 },
                { "route_id": "SK_LRT", "type": "lrt", "flow": 220, "capacity": 3500, "utilization": 0.06 },
                { "route_id": "PG_LRT", "type": "lrt", "flow": 190, "capacity": 3500, "utilization": 0.05 },
                { "route_id": "BUS_96", "type": "bus", "flow": 80, "capacity": 800, "utilization": 0.10 },
                { "route_id": "BUS_97", "type": "bus", "flow": 65, "capacity": 800, "utilization": 0.08 },
                { "route_id": "BUS_106", "type": "bus", "flow": 90, "capacity": 800, "utilization": 0.11 },
                { "route_id": "BUS_161", "type": "bus", "flow": 70, "capacity": 800, "utilization": 0.09 },
                { "route_id": "BUS_188", "type": "bus", "flow": 85, "capacity": 800, "utilization": 0.11 }
            ],
            "total_flow": 8210
        }
    }
};

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.PASSENGER_FLOW;
}
