#!/usr/bin/env python3
"""
站点代码到线路的映射
PT_CODE to Route ID Mapping for Singapore Public Transit
"""

# 站点代码到线路的映射
PT_CODE_TO_ROUTE = {
    # =====================================
    # North-South Line (NS) - 红线
    # =====================================
    "NS1": "NS_LINE", "NS2": "NS_LINE", "NS3": "NS_LINE", "NS4": "NS_LINE",
    "NS5": "NS_LINE", "NS6": "NS_LINE", "NS7": "NS_LINE", "NS8": "NS_LINE",
    "NS9": "NS_LINE", "NS10": "NS_LINE", "NS11": "NS_LINE", "NS12": "NS_LINE",
    "NS13": "NS_LINE", "NS14": "NS_LINE", "NS15": "NS_LINE", "NS16": "NS_LINE",
    "NS17": "NS_LINE", "NS18": "NS_LINE", "NS19": "NS_LINE", "NS20": "NS_LINE",
    "NS21": "NS_LINE", "NS22": "NS_LINE", "NS23": "NS_LINE", "NS24": "NS_LINE",
    "NS25": "NS_LINE", "NS26": "NS_LINE", "NS27": "NS_LINE", "NS28": "NS_LINE",

    # =====================================
    # East-West Line (EW) - 绿线
    # =====================================
    "EW1": "EW_LINE", "EW2": "EW_LINE", "EW3": "EW_LINE", "EW4": "EW_LINE",
    "EW5": "EW_LINE", "EW6": "EW_LINE", "EW7": "EW_LINE", "EW8": "EW_LINE",
    "EW9": "EW_LINE", "EW10": "EW_LINE", "EW11": "EW_LINE", "EW12": "EW_LINE",
    "EW13": "EW_LINE", "EW14": "EW_LINE", "EW15": "EW_LINE", "EW16": "EW_LINE",
    "EW17": "EW_LINE", "EW18": "EW_LINE", "EW19": "EW_LINE", "EW20": "EW_LINE",
    "EW21": "EW_LINE", "EW22": "EW_LINE", "EW23": "EW_LINE", "EW24": "EW_LINE",
    "EW25": "EW_LINE", "EW26": "EW_LINE", "EW27": "EW_LINE", "EW28": "EW_LINE",
    "EW29": "EW_LINE", "EW30": "EW_LINE", "EW31": "EW_LINE", "EW32": "EW_LINE",
    "EW33": "EW_LINE", "EW34": "EW_LINE",

    # =====================================
    # North-East Line (NE) - 紫线
    # =====================================
    "NE1": "NE_LINE", "NE2": "NE_LINE", "NE3": "NE_LINE", "NE4": "NE_LINE",
    "NE5": "NE_LINE", "NE6": "NE_LINE", "NE7": "NE_LINE", "NE8": "NE_LINE",
    "NE9": "NE_LINE", "NE10": "NE_LINE", "NE11": "NE_LINE", "NE12": "NE_LINE",
    "NE13": "NE_LINE", "NE14": "NE_LINE", "NE15": "NE_LINE", "NE16": "NE_LINE",
    "NE17": "NE_LINE",

    # =====================================
    # Circle Line (CC) - 橙线
    # =====================================
    "CC1": "CC_LINE", "CC2": "CC_LINE", "CC3": "CC_LINE", "CC4": "CC_LINE",
    "CC5": "CC_LINE", "CC6": "CC_LINE", "CC7": "CC_LINE", "CC8": "CC_LINE",
    "CC9": "CC_LINE", "CC10": "CC_LINE", "CC11": "CC_LINE", "CC12": "CC_LINE",
    "CC13": "CC_LINE", "CC14": "CC_LINE", "CC15": "CC_LINE", "CC16": "CC_LINE",
    "CC17": "CC_LINE", "CC18": "CC_LINE", "CC19": "CC_LINE", "CC20": "CC_LINE",
    "CC21": "CC_LINE", "CC22": "CC_LINE", "CC23": "CC_LINE", "CC24": "CC_LINE",
    "CC25": "CC_LINE", "CC26": "CC_LINE", "CC27": "CC_LINE", "CC28": "CC_LINE",
    "CC29": "CC_LINE", "CC30": "CC_LINE", "CC31": "CC_LINE", "CC32": "CC_LINE",
    "CC33": "CC_LINE", "CC34": "CC_LINE",

    # =====================================
    # Downtown Line (DT) - 蓝线
    # =====================================
    "DT1": "DT_LINE", "DT2": "DT_LINE", "DT3": "DT_LINE", "DT4": "DT_LINE",
    "DT5": "DT_LINE", "DT6": "DT_LINE", "DT7": "DT_LINE", "DT8": "DT_LINE",
    "DT9": "DT_LINE", "DT10": "DT_LINE", "DT11": "DT_LINE", "DT12": "DT_LINE",
    "DT13": "DT_LINE", "DT14": "DT_LINE", "DT15": "DT_LINE", "DT16": "DT_LINE",
    "DT17": "DT_LINE", "DT18": "DT_LINE", "DT19": "DT_LINE", "DT20": "DT_LINE",
    "DT21": "DT_LINE", "DT22": "DT_LINE", "DT23": "DT_LINE", "DT24": "DT_LINE",
    "DT25": "DT_LINE", "DT26": "DT_LINE", "DT27": "DT_LINE", "DT28": "DT_LINE",
    "DT29": "DT_LINE", "DT30": "DT_LINE", "DT31": "DT_LINE", "DT32": "DT_LINE",
    "DT33": "DT_LINE", "DT34": "DT_LINE", "DT35": "DT_LINE", "DT36": "DT_LINE",
    "DT37": "DT_LINE", "DT38": "DT_LINE", "DT39": "DT_LINE", "DT40": "DT_LINE",
    "DT41": "DT_LINE", "DT42": "DT_LINE", "DT43": "DT_LINE",

    # =====================================
    # Thomson-East Coast Line (TE) - 棕线
    # =====================================
    "TE1": "TE_LINE", "TE2": "TE_LINE", "TE3": "TE_LINE", "TE4": "TE_LINE",
    "TE5": "TE_LINE", "TE6": "TE_LINE", "TE7": "TE_LINE", "TE8": "TE_LINE",
    "TE9": "TE_LINE", "TE10": "TE_LINE", "TE11": "TE_LINE", "TE12": "TE_LINE",
    "TE13": "TE_LINE", "TE14": "TE_LINE", "TE15": "TE_LINE", "TE16": "TE_LINE",
    "TE17": "TE_LINE", "TE18": "TE_LINE", "TE19": "TE_LINE", "TE20": "TE_LINE",
    "TE21": "TE_LINE", "TE22": "TE_LINE", "TE23": "TE_LINE", "TE24": "TE_LINE",
    "TE25": "TE_LINE", "TE26": "TE_LINE", "TE27": "TE_LINE", "TE28": "TE_LINE",
    "TE29": "TE_LINE", "TE30": "TE_LINE", "TE31": "TE_LINE", "TE32": "TE_LINE",
    "TE33": "TE_LINE", "TE34": "TE_LINE", "TE35": "TE_LINE",

    # =====================================
    # Bukit Panjang LRT (BP)
    # =====================================
    "BP1": "BP_LRT", "BP2": "BP_LRT", "BP3": "BP_LRT", "BP4": "BP_LRT",
    "BP5": "BP_LRT", "BP6": "BP_LRT", "BP7": "BP_LRT", "BP8": "BP_LRT",
    "BP9": "BP_LRT", "BP10": "BP_LRT", "BP11": "BP_LRT", "BP12": "BP_LRT",
    "BP13": "BP_LRT", "BP14": "BP_LRT",

    # =====================================
    # Sengkang LRT (ST)
    # =====================================
    "ST1": "ST_LRT", "ST2": "ST_LRT", "ST3": "ST_LRT", "ST4": "ST_LRT",
    "ST5": "ST_LRT", "ST6": "ST_LRT", "ST7": "ST_LRT", "ST8": "ST_LRT",
    "ST9": "ST_LRT", "ST10": "ST_LRT", "ST11": "ST_LRT", "ST12": "ST_LRT",

    # =====================================
    # Punggol LRT (PE)
    # =====================================
    "PE1": "PE_LRT", "PE2": "PE_LRT", "PE3": "PE_LRT", "PE4": "PE_LRT",
    "PE5": "PE_LRT", "PE6": "PE_LRT", "PE7": "PE_LRT", "PE8": "PE_LRT",
    "PE9": "PE_LRT", "PE10": "PE_LRT",

    # =====================================
    # Choa Chu Kang LRT (SW) - Sentosa Express
    # =====================================
    "SW1": "SW_LRT", "SW2": "SW_LRT", "SW3": "SW_LRT", "SW4": "SW_LRT",
    "SW5": "SW_LRT", "SW6": "SW_LRT", "SW7": "SW_LRT", "SW8": "SW_LRT",

    # =====================================
    # East Loop LRT (SE)
    # =====================================
    "SE1": "SE_LRT", "SE2": "SE_LRT", "SE3": "SE_LRT", "SE4": "SE_LRT",
    "SE5": "SE_LRT", "SE6": "SE_LRT", "SE7": "SE_LRT",

    # =====================================
    # West Loop LRT (PW)
    # =====================================
    "PW1": "PW_LRT", "PW2": "PW_LRT", "PW3": "PW_LRT", "PW4": "PW_LRT",
    "PW5": "PW_LRT", "PW6": "PW_LRT", "PW7": "PW_LRT", "PW8": "PW_LRT",

    # =====================================
    # Sengkang LRT East (SK)
    # =====================================
    "SK1": "SK_LRT", "SK2": "SK_LRT", "SK3": "SK_LRT", "SK4": "SK_LRT",
    "SK5": "SK_LRT", "SK6": "SK_LRT", "SK7": "SK_LRT", "SK8": "SK_LRT",

    # =====================================
    # Punggol LRT West (PG)
    # =====================================
    "PG1": "PG_LRT", "PG2": "PG_LRT", "PG3": "PG_LRT", "PG4": "PG_LRT",
    "PG5": "PG_LRT", "PG6": "PG_LRT", "PG7": "PG_LRT", "PG8": "PG_LRT",
}


def get_route_for_pt_code(pt_code):
    """根据站点代码获取线路ID"""
    return PT_CODE_TO_ROUTE.get(pt_code.upper(), None)


def get_type_for_route(route_id):
    """根据线路ID获取类型"""
    if route_id.endswith('_LRT'):
        return 'lrt'
    return 'mrt'


if __name__ == "__main__":
    # Test
    print("Testing PT_CODE to ROUTE mapping...")
    test_codes = ["NS1", "EW25", "NE9", "CC4", "DT35", "TE14", "BP5", "SE3", "PE1", "PW4"]
    for code in test_codes:
        route = get_route_for_pt_code(code)
        print(f"  {code} -> {route}")
    print("Done.")
