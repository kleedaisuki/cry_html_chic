/**
 * 新加坡公共交通线路数据
 * Singapore Transit Routes Data
 */

window.ROUTES = {
    // ==========================================
    // MRT 地铁线路 (Mass Rapid Transit)
    // ==========================================

    // North-South Line (NSL) - 南北线
    "NS_LINE": {
        "name": "南北线 (North-South Line)",
        "type": "mrt",
        "color": "#e41a1c",
        "description": "连接新加坡北部和南部的主要干线",
        "coordinates": [
            [103.7643, 1.3329],   // Jurong East
            [103.7618, 1.3389],   // Bukit Batok
            [103.7639, 1.3440],   // Bukit Gombak
            [103.7719, 1.3525],   // Choa Chu Kang
            [103.7780, 1.3614],   // Yew Tee
            [103.7867, 1.3770],   // Kranji
            [103.7910, 1.3851],   // Marsiling
            [103.7969, 1.3952],   // Woodlands
            [103.8010, 1.4032],   // Admiralty
            [103.8038, 1.4169],   // Sembawang
            [103.8086, 1.4291],   // Canberra
            [103.8198, 1.4432],   // Yishun
            [103.8351, 1.4505],   // Khatib
            [103.8370, 1.4615],   // Ang Mo Kio
            [103.8451, 1.4697],   // Bishan
            [103.8357, 1.4780],   // Braddell
            [103.8564, 1.4855],   // Toa Payoh
            [103.8639, 1.4931],   // Novena
            [103.8442, 1.5000],   // Newton
            [103.8278, 1.5019],   // Orchard
            [103.8236, 1.5052],   // Somerset
            [103.8195, 1.5086],   // Dhoby Ghaut
            [103.8139, 1.5189],   // City Hall
            [103.8077, 1.5299],   // Raffles Place
            [103.8037, 1.5423],   // Marina Bay
            [103.8092, 1.5501]    // Marina South Pier
        ],
        "stations": [
            {"id": "NS1", "name": "Jurong East", "position": [103.7643, 1.3329]},
            {"id": "NS2", "name": "Bukit Batok", "position": [103.7618, 1.3389]},
            {"id": "NS3", "name": "Bukit Gombak", "position": [103.7639, 1.3440]},
            {"id": "NS4", "name": "Choa Chu Kang", "position": [103.7719, 1.3525]},
            {"id": "NS5", "name": "Yew Tee", "position": [103.7780, 1.3614]},
            {"id": "NS6", "name": "Kranji", "position": [103.7867, 1.3770]},
            {"id": "NS7", "name": "Marsiling", "position": [103.7910, 1.3851]},
            {"id": "NS8", "name": "Woodlands", "position": [103.7969, 1.3952]},
            {"id": "NS9", "name": "Admiralty", "position": [103.8010, 1.4032]},
            {"id": "NS10", "name": "Sembawang", "position": [103.8038, 1.4169]},
            {"id": "NS11", "name": "Canberra", "position": [103.8086, 1.4291]},
            {"id": "NS12", "name": "Yishun", "position": [103.8198, 1.4432]},
            {"id": "NS13", "name": "Khatib", "position": [103.8351, 1.4505]},
            {"id": "NS14", "name": "Ang Mo Kio", "position": [103.8370, 1.4615]},
            {"id": "NS15", "name": "Bishan", "position": [103.8451, 1.4697]},
            {"id": "NS16", "name": "Braddell", "position": [103.8357, 1.4780]},
            {"id": "NS17", "name": "Toa Payoh", "position": [103.8564, 1.4855]},
            {"id": "NS18", "name": "Novena", "position": [103.8639, 1.4931]},
            {"id": "NS19", "name": "Newton", "position": [103.8442, 1.5000]},
            {"id": "NS20", "name": "Orchard", "position": [103.8278, 1.5019]},
            {"id": "NS21", "name": "Somerset", "position": [103.8236, 1.5052]},
            {"id": "NS22", "name": "Dhoby Ghaut", "position": [103.8195, 1.5086]},
            {"id": "NS23", "name": "City Hall", "position": [103.8139, 1.5189]},
            {"id": "NS24", "name": "Raffles Place", "position": [103.8077, 1.5299]},
            {"id": "NS25", "name": "Marina Bay", "position": [103.8037, 1.5423]},
            {"id": "NS26", "name": "Marina South Pier", "position": [103.8092, 1.5501]}
        ]
    },

    // East-West Line (EWL) - 东西线
    "EW_LINE": {
        "name": "东西线 (East-West Line)",
        "type": "mrt",
        "color": "#008000",
        "description": "连接新加坡东部和西部的主要干线",
        "coordinates": [
            [103.6394, 1.3189],   // Pasir Ris
            [103.6490, 1.3216],   // Tampines
            [103.6574, 1.3278],   // Tampines West
            [103.6630, 1.3340],   // Tampines East
            [103.6690, 1.3418],   // Bedok
            [103.6795, 1.3518],   // Bedok Reservoir
            [103.6870, 1.3589],   // Tampines Hill
            [103.7018, 1.3679],   // Kaki Bukit
            [103.7099, 1.3735],   // Bedok North
            [103.7175, 1.3791],   // Bedok South
            [103.7296, 1.3880],   // Tanah Merah
            [103.7395, 1.3962],   // Kembangan
            [103.7540, 1.4045],   // Eunos
            [103.7665, 1.4105],   // Paya Lebar
            [103.7775, 1.4170],   // Aljunied
            [103.7873, 1.4230],   // Kallang
            [103.7965, 1.4300],   // Lavender
            [103.8025, 1.4380],   // Bugis
            [103.8070, 1.4448],   // City Hall
            [103.8077, 1.4548],   // Raffles Place
            [103.8105, 1.4650],   // Outram Park
            [103.8190, 1.4750],   // Tiong Bahru
            [103.8230, 1.4850],   // Redhill
            [103.8290, 1.4950],   // Queenstown
            [103.8330, 1.5050],   // Commonwealth
            [103.8350, 1.5150],   // Buona Vista
            [103.8410, 1.5250],   // Dover
            [103.8470, 1.5350],   // Clementi
            [103.8550, 1.5450],   // Jurong East
            [103.8670, 1.5550],   // Chinese Garden
            [103.8750, 1.5620],   // Lakeside
            [103.8840, 1.5700],   // Boon Lay
            [103.8940, 1.5750],   // Pioneer
            [103.9020, 1.5800]    // Joo Koon
        ],
        "stations": [
            {"id": "EW1", "name": "Pasir Ris", "position": [103.6394, 1.3189]},
            {"id": "EW2", "name": "Tampines", "position": [103.6490, 1.3216]},
            {"id": "EW3", "name": "Tampines West", "position": [103.6574, 1.3278]},
            {"id": "EW4", "name": "Tampines East", "position": [103.6630, 1.3340]},
            {"id": "EW5", "name": "Bedok", "position": [103.6690, 1.3418]},
            {"id": "EW6", "name": "Bedok Reservoir", "position": [103.6795, 1.3518]},
            {"id": "EW7", "name": "Kaki Bukit", "position": [103.7018, 1.3679]},
            {"id": "EW8", "name": "Kembangan", "position": [103.7395, 1.3962]},
            {"id": "EW9", "name": "Eunos", "position": [103.7540, 1.4045]},
            {"id": "EW10", "name": "Paya Lebar", "position": [103.7665, 1.4105]},
            {"id": "EW11", "name": "Aljunied", "position": [103.7775, 1.4170]},
            {"id": "EW12", "name": "Kallang", "position": [103.7873, 1.4230]},
            {"id": "EW13", "name": "Lavender", "position": [103.7965, 1.4300]},
            {"id": "EW14", "name": "Bugis", "position": [103.8025, 1.4380]},
            {"id": "EW15", "name": "City Hall", "position": [103.8070, 1.4448]},
            {"id": "EW16", "name": "Raffles Place", "position": [103.8077, 1.4548]},
            {"id": "EW17", "name": "Outram Park", "position": [103.8105, 1.4650]},
            {"id": "EW18", "name": "Tiong Bahru", "position": [103.8190, 1.4750]},
            {"id": "EW19", "name": "Redhill", "position": [103.8230, 1.4850]},
            {"id": "EW20", "name": "Queenstown", "position": [103.8290, 1.4950]},
            {"id": "EW21", "name": "Commonwealth", "position": [103.8330, 1.5050]},
            {"id": "EW22", "name": "Buona Vista", "position": [103.8350, 1.5150]},
            {"id": "EW23", "name": "Clementi", "position": [103.8470, 1.5350]},
            {"id": "EW24", "name": "Jurong East", "position": [103.8550, 1.5450]},
            {"id": "EW25", "name": "Chinese Garden", "position": [103.8670, 1.5550]},
            {"id": "EW26", "name": "Lakeside", "position": [103.8750, 1.5620]},
            {"id": "EW27", "name": "Boon Lay", "position": [103.8840, 1.5700]}
        ]
    },

    // North-East Line (NEL) - 东北线
    "NE_LINE": {
        "name": "东北线 (North-East Line)",
        "type": "mrt",
        "color": "#800080",
        "description": "连接东北部地区和市中心的无人驾驶地铁线",
        "coordinates": [
            [103.8910, 1.4081],   // HarbourFront
            [103.8832, 1.4172],   // Outram Park
            [103.8735, 1.4257],   // Chinatown
            [103.8639, 1.4325],   // Clarke Quay
            [103.8541, 1.4393],   // Little India
            [103.8436, 1.4468],   // Farrer Park
            [103.8332, 1.4538],   // Boon Keng
            [103.8229, 1.4608],   // Potong Pasir
            [103.8125, 1.4678],   // Woodleigh
            [103.8021, 1.4748],   // Serangoon
            [103.7917, 1.4818],   // Kovan
            [103.7813, 1.4888],   // Hougang
            [103.7709, 1.4958],   // Buangkok
            [103.7605, 1.5028],   // Sengkang
            [103.7501, 1.5098]    // Punggol
        ],
        "stations": [
            {"id": "NE1", "name": "HarbourFront", "position": [103.8910, 1.4081]},
            {"id": "NE2", "name": "Outram Park", "position": [103.8832, 1.4172]},
            {"id": "NE3", "name": "Chinatown", "position": [103.8735, 1.4257]},
            {"id": "NE4", "name": "Clarke Quay", "position": [103.8639, 1.4325]},
            {"id": "NE5", "name": "Little India", "position": [103.8541, 1.4393]},
            {"id": "NE6", "name": "Farrer Park", "position": [103.8436, 1.4468]},
            {"id": "NE7", "name": "Serangoon", "position": [103.8021, 1.4748]},
            {"id": "NE12", "name": "Kovan", "position": [103.7917, 1.4818]},
            {"id": "NE13", "name": "Hougang", "position": [103.7813, 1.4888]},
            {"id": "NE16", "name": "Sengkang", "position": [103.7605, 1.5028]},
            {"id": "NE17", "name": "Punggol", "position": [103.7501, 1.5098]}
        ]
    },

    // Circle Line (CCL) - 环线
    "CC_LINE": {
        "name": "环线 (Circle Line)",
        "type": "mrt",
        "color": "#FFA500",
        "description": "环绕新加坡市中心的环状地铁线",
        "coordinates": [
            [103.8236, 1.5052],   // Dhoby Ghaut
            [103.8321, 1.5110],   // Bras Basah
            [103.8406, 1.5169],   // Esplanade
            [103.8491, 1.5228],   // Promenade
            [103.8576, 1.5287],   // Nicoll Highway
            [103.8661, 1.5346],   // Stadium
            [103.8746, 1.5405],   // Mountbatten
            [103.8831, 1.5464],   // Dakota
            [103.8916, 1.5523],   // Paya Lebar
            [103.9001, 1.5582],   // MacPherson
            [103.9086, 1.5641],   // Ubi
            [103.9171, 1.5700],   // Kaki Bukit
            [103.9256, 1.5759],   // Bedok North
            [103.9341, 1.5818],   // Bedok Reservoir
            [103.9426, 1.5877],   // Tampines West
            [103.9511, 1.5936],   // Tampines
            [103.9596, 1.5995],   // Tampines East
            [103.9681, 1.6054],   // Upper Changi
            [103.9766, 1.6113],   // Expo
            [103.9851, 1.6172],   // Changi Airport
            [103.9936, 1.6231],   // Marina Bay
            [103.9821, 1.6172],   // Bayfront
            [103.9706, 1.6113],   // Promenade
            [103.9591, 1.6054],   // Bencoolen
            [103.9476, 1.5995],   // Jalan Besar
            [103.9361, 1.5936],   // Farrer Park
            [103.9246, 1.5877],   // Boon Keng
            [103.9131, 1.5818],   // Potong Pasir
            [103.9016, 1.5759],   // Woodleigh
            [103.8901, 1.5700],   // Serangoon
            [103.8786, 1.5641],   // Bidadari
            [103.8671, 1.5582],   // Aljunied
            [103.8556, 1.5523],   // Paya Lebar
            [103.8441, 1.5464],   // Dakota
            [103.8326, 1.5405],   // Mountbatten
            [103.8211, 1.5346],   // Stadium
            [103.8096, 1.5287],   // Nicoll Highway
            [103.7981, 1.5228],   // Esplanade
            [103.7866, 1.5169],   // Bras Basah
            [103.7751, 1.5110],   // Dhoby Ghaut
        ],
        "stations": [
            {"id": "CC1", "name": "Dhoby Ghaut", "position": [103.8236, 1.5052]},
            {"id": "CC2", "name": "Bras Basah", "position": [103.8321, 1.5110]},
            {"id": "CC3", "name": "Esplanade", "position": [103.8406, 1.5169]},
            {"id": "CC4", "name": "Promenade", "position": [103.8491, 1.5228]},
            {"id": "CC5", "name": "Nicoll Highway", "position": [103.8576, 1.5287]},
            {"id": "CC6", "name": "Stadium", "position": [103.8661, 1.5346]},
            {"id": "CC9", "name": "Paya Lebar", "position": [103.8916, 1.5523]},
            {"id": "CC10", "name": "MacPherson", "position": [103.9001, 1.5582]},
            {"id": "CC15", "name": "Serangoon", "position": [103.8901, 1.5700]},
            {"id": "CC26", "name": "Promenade", "position": [103.9706, 1.6113]},
            {"id": "CC27", "name": "Marina Bay", "position": [103.9936, 1.6231]}
        ]
    },

    // Downtown Line (DTL) - 滨海市区线
    "DT_LINE": {
        "name": "滨海市区线 (Downtown Line)",
        "type": "mrt",
        "color": "#0055A4",
        "description": "连接新加坡西北部到市中心的地铁线",
        "coordinates": [
            [103.6978, 1.3778],   // Bukit Panjang
            [103.7120, 1.3830],   // Cashew
            [103.7262, 1.3882],   // Hillview
            [103.7404, 1.3934],   // Beauty World
            [103.7546, 1.3986],   // King Albert Park
            [103.7688, 1.4038],   // Sixth Avenue
            [103.7830, 1.4090],   // Tan Kah Kee
            [103.7972, 1.4142],   // Botanic Gardens
            [103.8114, 1.4194],   // Stevens
            [103.8256, 1.4246],   // Newton
            [103.8398, 1.4298],   // Little India
            [103.8540, 1.4350],   // Rochor
            [103.8682, 1.4402],   // Bugis
            [103.8824, 1.4454],   // Promenade
            [103.8966, 1.4506],   // Bayfront
            [103.9108, 1.4558],   // Downtown
            [103.9250, 1.4610],   // Telok Ayer
            [103.9392, 1.4662],   // Chinatown
            [103.9534, 1.4714],   // Fort Canning
            [103.9676, 1.4766],   // Bencoolen
            [103.9818, 1.4818],   // Jalan Besar
            [103.9960, 1.4870],   // Bendemeer
            [104.0102, 1.4922],   // Geylang Bahru
            [104.0244, 1.4974],   // Mattar
            [104.0386, 1.5026],   // MacPherson
            [104.0528, 1.5078],   // Ubi
            [104.0670, 1.5130]    // Kaki Bukit
        ],
        "stations": [
            {"id": "DT1", "name": "Bukit Panjang", "position": [103.6978, 1.3778]},
            {"id": "DT2", "name": "Cashew", "position": [103.7120, 1.3830]},
            {"id": "DT3", "name": "Hillview", "position": [103.7262, 1.3882]},
            {"id": "DT5", "name": "Botanic Gardens", "position": [103.7972, 1.4142]},
            {"id": "DT7", "name": "Stevens", "position": [103.8114, 1.4194]},
            {"id": "DT9", "name": "Newton", "position": [103.8256, 1.4246]},
            {"id": "DT11", "name": "Little India", "position": [103.8398, 1.4298]},
            {"id": "DT13", "name": "Rochor", "position": [103.8540, 1.4350]},
            {"id": "DT14", "name": "Bugis", "position": [103.8682, 1.4402]},
            {"id": "DT15", "name": "Promenade", "position": [103.8824, 1.4454]},
            {"id": "DT16", "name": "Bayfront", "position": [103.8966, 1.4506]},
            {"id": "DT17", "name": "Downtown", "position": [103.9108, 1.4558]},
            {"id": "DT18", "name": "Telok Ayer", "position": [103.9250, 1.4610]},
            {"id": "DT19", "name": "Chinatown", "position": [103.9392, 1.4662]}
        ]
    },

    // Thomson-East Coast Line (TEL) - 汤申-东海岸线
    "TE_LINE": {
        "name": "汤申-东海岸线 (Thomson-East Coast Line)",
        "type": "mrt",
        "color": "#D9EAD3",
        "description": "新加坡最新的地铁线，连接北部和东部",
        "coordinates": [
            [103.7751, 1.4530],   // Woodlands North
            [103.7865, 1.4440],   // Woodlands
            [103.7979, 1.4350],   // Woodlands South
            [103.8093, 1.4260],   // Springleaf
            [103.8207, 1.4170],   // Lentor
            [103.8321, 1.4080],   // Mayflower
            [103.8435, 1.3990],   // Ang Mo Kio
            [103.8549, 1.3900],   // Bright Hill
            [103.8663, 1.3810],   // Upper Thomson
            [103.8777, 1.3720],   // Mount Pleasant
            [103.8891, 1.3630],   // Stevens
            [103.9005, 1.3540],   // Napier
            [103.9119, 1.3450],   // Orchard Boulevard
            [103.9233, 1.3360],   // Orchard
            [103.9347, 1.3270],   // Great World
            [103.9461, 1.3180],   // Havelock
            [103.9575, 1.3090],   // Outram Park
            [103.9689, 1.3000],   // Maxwell
            [103.9803, 1.2910],   // Tanjong Pagar
            [103.9917, 1.2820],   // Marina Bay
            [104.0031, 1.2730],   // Marina South
            [104.0145, 1.2640],   // Gardens by the Bay
            [104.0259, 1.2550],   // Bedok South
            [104.0373, 1.2460],   // Bedok
            [104.0487, 1.2370],   // Tampines North
            [104.0601, 1.2280]    // Upper Changi
        ],
        "stations": [
            {"id": "TE1", "name": "Woodlands North", "position": [103.7751, 1.4530]},
            {"id": "TE2", "name": "Woodlands", "position": [103.7865, 1.4440]},
            {"id": "TE3", "name": "Woodlands South", "position": [103.7979, 1.4350]},
            {"id": "TE4", "name": "Springleaf", "position": [103.8093, 1.4260]},
            {"id": "TE5", "name": "Lentor", "position": [103.8207, 1.4170]},
            {"id": "TE6", "name": "Mayflower", "position": [103.8321, 1.4080]},
            {"id": "TE7", "name": "Bright Hill", "position": [103.8549, 1.3900]},
            {"id": "TE8", "name": "Upper Thomson", "position": [103.8663, 1.3810]},
            {"id": "TE14", "name": "Orchard", "position": [103.9233, 1.3360]},
            {"id": "TE17", "name": "Outram Park", "position": [103.9575, 1.3090]},
            {"id": "TE20", "name": "Marina Bay", "position": [103.9917, 1.2820]}
        ]
    },

    // ==========================================
    // LRT 轻轨线路 (Light Rail Transit)
    // ==========================================

    // Bukit Panjang LRT - 武吉班让轻轨
    "BP_LRT": {
        "name": "武吉班让轻轨 (Bukit Panjang LRT)",
        "type": "lrt",
        "color": "#006400",
        "description": "服务于武吉班让新镇的内环轻轨系统",
        "coordinates": [
            [103.7719, 1.3774],   // Choa Chu Kang
            [103.7719, 1.3824],   // South View
            [103.7719, 1.3874],   // Keat Hong
            [103.7719, 1.3924],   // Teck Whye
            [103.7669, 1.3974],   // Phoenix
            [103.7619, 1.4024],   // Bukit Panjang
            [103.7569, 1.3974],   // Fajar
            [103.7519, 1.3924],   // Gangsa
            [103.7469, 1.3874],   // Jelebu
            [103.7419, 1.3824],   // Bangkit
            [103.7369, 1.3774],   // Pending
            [103.7319, 1.3724],   // Petir
            [103.7269, 1.3674],   // Senja
            [103.7219, 1.3624]    // Ten Mile Junction
        ],
        "stations": [
            {"id": "BP1", "name": "Choa Chu Kang", "position": [103.7719, 1.3774]},
            {"id": "BP2", "name": "South View", "position": [103.7719, 1.3824]},
            {"id": "BP3", "name": "Keat Hong", "position": [103.7719, 1.3874]},
            {"id": "BP4", "name": "Teck Whye", "position": [103.7719, 1.3924]},
            {"id": "BP5", "name": "Phoenix", "position": [103.7669, 1.3974]},
            {"id": "BP6", "name": "Bukit Panjang", "position": [103.7619, 1.4024]},
            {"id": "BP7", "name": "Fajar", "position": [103.7569, 1.3974]},
            {"id": "BP8", "name": "Gangsa", "position": [103.7519, 1.3924]},
            {"id": "BP9", "name": "Jelebu", "position": [103.7469, 1.3874]},
            {"id": "BP10", "name": "Bangkit", "position": [103.7419, 1.3824]}
        ]
    },

    // Sengkang LRT - 盛港轻轨
    "SK_LRT": {
        "name": "盛港轻轨 (Sengkang LRT)",
        "type": "lrt",
        "color": "#006400",
        "description": "服务于盛港新镇的轻轨系统",
        "coordinates": [
            [103.8915, 1.4500],   // Sengkang
            [103.8915, 1.4550],   // Compassvale
            [103.8915, 1.4600],   // Rumbia
            [103.8865, 1.4650],   // Bakau
            [103.8815, 1.4700],   // Kangkar
            [103.8765, 1.4750],   // Ranggung
            [103.8715, 1.4800],   // Chengkam
            [103.8665, 1.4850],   // Samudera
            [103.8615, 1.4900]    // Passir Ris (via East Loop)
        ],
        "stations": [
            {"id": "SK1", "name": "Sengkang", "position": [103.8915, 1.4500]},
            {"id": "SK2", "name": "Compassvale", "position": [103.8915, 1.4550]},
            {"id": "SK3", "name": "Rumbia", "position": [103.8915, 1.4600]},
            {"id": "SK4", "name": "Bakau", "position": [103.8865, 1.4650]},
            {"id": "SK5", "name": "Kangkar", "position": [103.8815, 1.4700]},
            {"id": "SK6", "name": "Ranggung", "position": [103.8765, 1.4750]}
        ]
    },

    // Punggol LRT - 榜鹅轻轨
    "PG_LRT": {
        "name": "榜鹅轻轨 (Punggol LRT)",
        "type": "lrt",
        "color": "#006400",
        "description": "服务于榜鹅新镇的轻轨系统",
        "coordinates": [
            [103.9020, 1.4041],   // Punggol
            [103.9020, 1.4091],   // Cove
            [103.9020, 1.4141],   // Meridian
            [103.9020, 1.4191],   // Coral Edge
            [103.9020, 1.4241],   // Riverview
            [103.8970, 1.4291],   // Sam Kee
            [103.8920, 1.4341],   // Tiong Bahru
            [103.8870, 1.4391],   // Punggol Point
            [103.8820, 1.4441],   // Samudera
            [103.8770, 1.4491],   // Nibong
            [103.8720, 1.4541],   // Sumang
            [103.8670, 1.4591],   // Soo Teck
            [103.9070, 1.4041],   // Waterbay (East Loop)
            [103.9120, 1.4091],   // Compassvale (East Loop)
            [103.9170, 1.4141],   // Kepong (East Loop)
            [103.9220, 1.4191],   // Chengsan (East Loop)
            [103.9270, 1.4241],   // Sengkang (East Loop)
        ],
        "stations": [
            {"id": "PG1", "name": "Punggol", "position": [103.9020, 1.4041]},
            {"id": "PG2", "name": "Cove", "position": [103.9020, 1.4091]},
            {"id": "PG3", "name": "Meridian", "position": [103.9020, 1.4141]},
            {"id": "PG4", "name": "Coral Edge", "position": [103.9020, 1.4191]},
            {"id": "PG5", "name": "Riverview", "position": [103.9020, 1.4241]},
            {"id": "PG6", "name": "Sam Kee", "position": [103.8970, 1.4291]},
            {"id": "PG7", "name": "Tiong Bahru", "position": [103.8920, 1.4341]},
            {"id": "PG8", "name": "Punggol Point", "position": [103.8870, 1.4391]},
            {"id": "PG9", "name": "Samudera", "position": [103.8820, 1.4441]}
        ]
    }
};

// 导出（用于模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.ROUTES;
}
