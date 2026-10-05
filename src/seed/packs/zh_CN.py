# SPDX-License-Identifier: Apache-2.0
"""中文种子常量（默认 demo）。"""

from __future__ import annotations

SURNAMES = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林郑谢罗梁宋唐许韩冯邓曹彭曾")
GIVEN = [
    "伟",
    "芳",
    "娜",
    "敏",
    "静",
    "丽",
    "强",
    "磊",
    "军",
    "洋",
    "勇",
    "艳",
    "杰",
    "娟",
    "涛",
    "明",
    "超",
    "霞",
    "平",
    "刚",
    "婷",
    "宇",
    "浩",
    "雪",
    "琳",
]
CITIES = ["北京", "上海", "广州", "深圳", "杭州"]

HOTELS = [("LOCAL", "房满乐", "本地", "请在本店设置中填写地址", 4)]
LOCAL_USERS = [
    ("admin", "admin123", "admin", "系统管理员"),
    ("gm", "gm123", "gm", "店长"),
    ("revenue", "rm123", "rm", "收益经理"),
    ("front", "front123", "fd", "前台"),
]
ROLES = [
    ("admin", "系统管理员", "全权限"),
    ("gm", "店长", "单店经营"),
    ("rm", "收益经理", "定价收益"),
    ("fd", "前台", "接待收银"),
]

ROOM_TYPE_TPL = [
    ("std-twin", "经济标间", "双床", 2, 199, False),
    ("deluxe-king", "豪华大床房", "大床", 2, 480, True),
    ("premier-king", "尊享大床房", "大床", 2, 520, True),
    ("biz-twin", "商务双床房", "双床", 2, 420, True),
    ("family", "家庭亲子房", "一大一小", 3, 680, True),
    ("exec-suite", "行政套房", "大床", 2, 880, True),
]

CHANNELS = [
    ("ctrip", "携程", "booking", 0.12),
    ("meituan", "美团酒店", "booking", 0.1),
    ("fliggy", "飞猪", "booking", 0.11),
    ("douyin", "抖音团购", "voucher", 0.08),
    ("meituan_voucher", "美团团购", "voucher", 0.1),
    ("xiaohongshu", "小红书", "xiaohongshu", 0.06),
    ("direct", "散客直订", "direct", 0.0),
    ("map_baidu", "百度地图", "map", 0.06),
    ("map_amap", "高德地图", "map", 0.06),
    ("geo_doubao", "GEO·豆包", "geo", 0.05),
    ("longstay", "常住客", "longstay", 0.04),
    ("agreement", "协议客户", "agreement", 0.05),
    ("wechat", "企微私域", "wechat", 0.03),
]

TAGS = [
    ("high_value", "高价值客户", "价值", "年消费 ≥ ¥50,000 或 LTV ≥ ¥8,000"),
    ("price_sensitive", "价格敏感", "行为", "促销转化率高 · 均价低于门市价 15%"),
    ("family", "亲子家庭", "画像", "历史携儿童订单 ≥ 2"),
    ("business", "商务常旅客", "画像", "工作日入住占比 > 70%"),
    ("complaint_risk", "投诉风险", "风险", "模型：Complaint_v2（置信度 > 80%）"),
    ("douyin_fan", "抖音粉丝", "渠道", "抖音渠道订单 ≥ 1 或私域互动 ≥ 3"),
    ("xhs_fan", "小红书种草", "渠道", "小红书来源订单 ≥ 1"),
    ("repeat", "复购客", "忠诚度", "180 天内订单 ≥ 5"),
    ("vip", "VIP", "忠诚度", "会员等级 ∈ {金卡, 白金} 或累计间夜 ≥ 20"),
]

SUPPLY_CATS = [("易耗品", None), ("布草", None), ("清洁用品", None), ("客用品", None)]
SUPPLIES = [
    ("易耗品", "牙具套装", "套", 200, 60),
    ("易耗品", "洗发水", "瓶", 300, 80),
    ("易耗品", "拖鞋", "双", 250, 70),
    ("布草", "床单", "条", 120, 40),
    ("布草", "浴巾", "条", 150, 50),
    ("清洁用品", "吸尘袋", "个", 80, 20),
    ("客用品", "矿泉水", "瓶", 500, 150),
    ("客用品", "茶包", "盒", 180, 50),
]

ASSET_TPL = ["中央空调", "电梯", "智能电视", "床垫", "热水系统", "门禁系统", "新风系统", "消防主机"]
ASSET_FLOW_TPL = [
    (
        "大金中央空调",
        "暖通",
        "402",
        "4F",
        "DK-AC-402-01",
        "FTXG50JV2W",
        4500,
        72,
        "预计 3 天后需清洗滤网",
        "maintenance",
    ),
    (
        "TOTO 智能马桶",
        "客房设备",
        "305",
        "3F",
        "TT-305-A2",
        "CES9788",
        6800,
        45,
        "水压异常波动，建议检查水阀",
        "abnormal",
    ),
    (
        "索尼 65寸 智能电视",
        "客房设备",
        "302",
        "3F",
        "SNY-8839-2A",
        "XR-65X90J",
        6500,
        88,
        "功耗稳定，背光模组健康",
        "active",
    ),
    ("戴森吹风机 HD15", "客房设备", "410", "4F", "DYN-4471-9F", "HD15", 3200, 62, "蓝牙标签偶发断开", "active"),
    ("美的中央空调", "暖通", "", "大堂", "MTC-2207-B3", "MDV-D280", 28000, 88, "下月常规保养", "active"),
    ("智能门锁", "弱电", "510", "5F", "LK-510-09", "Yale-YDM7116", 1800, 55, "剩余电量低于 15%", "maintenance"),
    ("大堂香氛机", "公区", "", "1F大堂", "AR-LOBBY-01", "AromaPro", 4200, 70, "溶液预计明晚耗尽", "active"),
    ("客梯 A", "电梯", "", "大堂", "EL-A-01", "OTIS-Gen2", 150000, 78, "本周例行检修窗口", "maintenance"),
    ("热泵热水系统", "暖通", "", "B1设备间", "HP-B1-01", "Gree-GHP", 210000, 91, "运行正常", "active"),
    ("新风系统", "暖通", "", "管井", "FAU-03", "Holtop-X", 96000, 85, "滤网寿命约剩 40%", "active"),
    ("丝涟床垫", "客房设备", "302", "3F", "SL-302-M1", "Sealy-Posture", 8800, 68, "高入住房，临近更换周期", "active"),
    ("监控系统 NVR", "弱电", "", "消防控制室", "NVR-01", "Hikvision-DS", 58000, 93, "磁盘余量充足", "active"),
]

HK_NAMES = [
    ("hk-a", "王阿姨"),
    ("hk-b", "李姐"),
    ("hk-c", "张师傅"),
    ("hk-d", "赵保洁"),
    ("hk-e", "陈大姐"),
]
HK_ROLE_NAME = "客房"

RATE_STRATEGY_NAME = "默认收益护栏"
AMENITY_BF = "含早"
AMENITY_EXTRA_BED = "可加床"
AMENITY_LIVING = "会客厅"
AMENITY_TUB = "浴缸"
AMENITY_SHOWER = "淋浴"

PRICING_EVENTS = [
    # type, name, start_offset_days, end_offset_days, dist, intensity(code), heat, uplift_max
    ("holiday", "中秋节", 20, 21, None, "中", None, 1.0),
    ("holiday", "国庆黄金周", 28, 34, None, "强", None, 1.0),
    ("concert", "周杰伦上海演唱会", 2, 3, 3.2, "爆", 95, 1.0),
    ("exhibition", "酒店用品展", 10, 12, 4.5, "中", 60, 1.0),
]
