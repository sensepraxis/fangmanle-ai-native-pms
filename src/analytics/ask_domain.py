# SPDX-License-Identifier: Apache-2.0
"""AI 问数 v1.2 · 业务术语词典 + 算子 + (metric × operator) 分解路由。

模型永不写 SQL；词典/算子由开发者预注册，运营可后续迁表维护。
"""

from __future__ import annotations

import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 算子目录（5 个核心）
# ---------------------------------------------------------------------------
OPERATOR_CATALOG: dict[str, dict[str, Any]] = {
    "op_get_value": {
        "label": "现在值是多少",
        "kws": ["多少", "是多少", "现在", "当前", "几", "什么水平", "到哪了"],
        "default_baseline": None,
    },
    "op_compare_baseline": {
        "label": "同比/环比/对比",
        "kws": [
            "相比",
            "对比",
            "比较",
            "比",
            "vs",
            "VS",
            "同比",
            "环比",
            "上月",
            "上个月",
            "去年",
            "同期",
            "更好",
            "更差",
            "升了",
            "降了",
            "如何",
        ],
        "default_baseline": "上月",
    },
    "op_trend": {
        "label": "趋势/走势",
        "kws": ["趋势", "走势", "变化", "波动", "走向", "近来", "这段时间"],
        "default_baseline": "同比",
    },
    "op_rank_top": {
        "label": "TopN/排名",
        "kws": ["哪几个", "哪些", "最多", "最少", "最糟", "最差", "最高", "最低", "排名", "top", "Top"],
        "default_baseline": None,
    },
    "op_breakdown": {
        "label": "拆解/明细",
        "kws": ["拆解", "明细", "看每个", "按渠道", "按房型", "分渠道", "分房型", "结构", "分群", "分布"],
        "default_baseline": None,
    },
}

# ---------------------------------------------------------------------------
# 业务术语小词典（≥20，含别名）
# ---------------------------------------------------------------------------
DOMAIN_GLOSSARY: list[dict[str, Any]] = [
    {
        "standard_term": "occupancy_rate",
        "aliases": [
            "入住率",
            "Occ%",
            "Occ％",
            "OCC%",
            "OCC％",
            "出租率",
            "住房率",
            "OCC",
            "Occ",
            "occ",
            "occupancy",
            "occupancy rate",
        ],
        "metric_id": "occupancy_rate",
        "unit": "%",
        "sample_query": "这个月入住率相比上个月如何？",
        "domain": "房间",
        "definition": "已售客房数 ÷ 可售客房数",
        "related_metrics": ["revpar", "adr"],
        "hot_score": 100,
    },
    {
        "standard_term": "adr",
        "aliases": ["平均房价", "均价", "ADR", "adr", "房价"],
        "metric_id": "adr",
        "unit": "元",
        "sample_query": "本月 ADR 同比怎样？",
        "domain": "房间",
        "definition": "客房收入 ÷ 已售客房数",
        "related_metrics": ["revpar", "occupancy_rate"],
        "hot_score": 95,
    },
    {
        "standard_term": "revpar",
        "aliases": ["RevPAR", "revpar", "每可用房收入", "每房收益"],
        "metric_id": "revpar",
        "unit": "元",
        "sample_query": "RevPAR 走势如何？",
        "domain": "房间",
        "definition": "OCC × ADR（或客房收入 ÷ 可售客房数）",
        "related_metrics": ["occupancy_rate", "adr"],
        "hot_score": 94,
    },
    {
        "standard_term": "ota_share",
        "aliases": [
            "OTA占比",
            "OTA 占比",
            "渠道依赖度",
            "OTA依赖",
            "OTA 依赖",
            "OTA share",
            "ota share",
            "OTA dependency",
        ],
        "metric_id": "ota_share",
        "unit": "%",
        "sample_query": "OTA 占比是否过高？",
        "domain": "渠道",
        "definition": "OTA 间夜 ÷ 总间夜",
        "related_metrics": ["direct_book_rate"],
        "hot_score": 92,
    },
    {
        "standard_term": "repurchase_rate",
        "aliases": [
            "复购率",
            "回头率",
            "老客占比",
            "会员复购",
            "复购",
            "member repurchase",
            "repurchase",
            "repeat purchase",
        ],
        "metric_id": "repurchase_rate",
        "unit": "%",
        "sample_query": "会员复购有没有变差？",
        "domain": "客户",
        "definition": "复购会员数 ÷ 总会员消费数（demo 用会员占比代理）",
        "related_metrics": ["member_pct"],
        "hot_score": 90,
    },
    {
        "standard_term": "nps",
        "aliases": ["NPS", "nps", "净推荐值", "点评分", "口碑分"],
        "metric_id": "nps",
        "unit": "分",
        "sample_query": "NPS 为啥降？",
        "domain": "口碑",
        "definition": "推荐者占比 − 贬损者占比（demo 用评分代理）",
        "related_metrics": ["review_topics"],
        "hot_score": 80,
    },
    {
        "standard_term": "rgi",
        "aliases": ["RGI", "rgi", "收益指数", "片区排名"],
        "metric_id": "rgi",
        "unit": "指数",
        "sample_query": "我在片区排第几？",
        "domain": "竞对",
        "definition": "本店 RevPAR ÷ 竞品集 RevPAR",
        "related_metrics": ["revpar"],
        "hot_score": 70,
    },
    {
        "standard_term": "direct_book_rate",
        "aliases": ["直订率", "官网占比", "直销占比", "直订"],
        "metric_id": "direct_book_rate",
        "unit": "%",
        "sample_query": "直订率升了没？",
        "domain": "渠道",
        "definition": "（官网+企微+小程序）间夜 ÷ 总间夜",
        "related_metrics": ["ota_share"],
        "hot_score": 85,
    },
    {
        "standard_term": "channel_profit",
        "aliases": [
            "渠道净收益",
            "渠道利润",
            "渠道亏钱",
            "渠道赚钱",
            "亏钱",
            "lost money",
            "losing money",
            "channel profit",
            "channel loss",
        ],
        "metric_id": "channel_profit",
        "unit": "元",
        "sample_query": "本月哪些渠道在亏钱？",
        "domain": "渠道",
        "definition": "渠道营收 − 佣金估算",
        "related_metrics": ["ota_share"],
        "hot_score": 88,
    },
    {
        "standard_term": "business_mix",
        "aliases": [
            "商务客占比",
            "商务客",
            "公司客",
            "商旅占比",
            "business travelers",
            "business traveler",
            "business mix",
            "corporate guests",
        ],
        "metric_id": "business_mix",
        "unit": "%",
        "sample_query": "商务客是不是在流失？",
        "domain": "客户",
        "definition": "商务客间夜 ÷ 总间夜",
        "related_metrics": ["segment_mix"],
        "hot_score": 87,
    },
    {
        "standard_term": "segment_mix",
        "aliases": ["客群结构", "客群占比", "谁在订"],
        "metric_id": "segment_mix",
        "unit": "%",
        "sample_query": "客群结构变了吗？",
        "domain": "客户",
        "definition": "各客群间夜占比",
        "related_metrics": ["business_mix"],
        "hot_score": 75,
    },
    {
        "standard_term": "weekday_occ",
        "aliases": ["平日入住", "周中入住", "工作日入住"],
        "metric_id": "weekday_occ",
        "unit": "%",
        "sample_query": "平日为何低入住？",
        "domain": "房间",
        "definition": "周一至周四间夜结构",
        "related_metrics": ["occupancy_rate"],
        "hot_score": 72,
    },
    {
        "standard_term": "los",
        "aliases": ["连住", "平均入住天数", "LOS", "住几晚"],
        "metric_id": "los",
        "unit": "晚",
        "sample_query": "平均住几天？",
        "domain": "房间",
        "definition": "平均连住晚数",
        "related_metrics": ["occupancy_rate"],
        "hot_score": 60,
    },
    {
        "standard_term": "review_topics",
        "aliases": ["差评原因", "投诉主题", "客人吐槽", "吐槽"],
        "metric_id": "review_topics",
        "unit": "单",
        "sample_query": "客人在吐槽啥？",
        "domain": "口碑",
        "definition": "差评关键词主题聚合",
        "related_metrics": ["nps"],
        "hot_score": 78,
    },
    {
        "standard_term": "pickup_gap",
        "aliases": ["预订缺口", "预订进度", "pickup", "Pickup"],
        "metric_id": "pickup_gap",
        "unit": "间夜",
        "sample_query": "下周满了吗？",
        "domain": "预测",
        "definition": "已订相对历史基线缺口",
        "related_metrics": ["occupancy_rate"],
        "hot_score": 74,
    },
    {
        "standard_term": "room_revenue",
        "aliases": ["客房收入", "房费收入", "房间营收"],
        "metric_id": "room_revenue",
        "unit": "元",
        "sample_query": "本月客房收入多少？",
        "domain": "财务",
        "definition": "总额 − other_amount（非房）",
        "related_metrics": ["revpar", "adr"],
        "hot_score": 82,
    },
    {
        "standard_term": "total_revenue",
        "aliases": ["总营收", "营业收入", "总收入"],
        "metric_id": "total_revenue",
        "unit": "元",
        "sample_query": "本月总营收多少？",
        "domain": "财务",
        "definition": "期间订单总额",
        "related_metrics": ["room_revenue"],
        "hot_score": 81,
    },
    {
        "standard_term": "commission_rate",
        "aliases": ["佣金率", "返佣", "渠道佣金"],
        "metric_id": "commission_rate",
        "unit": "%",
        "sample_query": "OTA 佣金率大概多少？",
        "domain": "渠道",
        "definition": "佣金 ÷ 渠道营收（demo 估算）",
        "related_metrics": ["channel_profit"],
        "hot_score": 65,
    },
    {
        "standard_term": "member_pct",
        "aliases": ["会员占比", "会员间夜", "会员客"],
        "metric_id": "member_pct",
        "unit": "%",
        "sample_query": "会员占比变了吗？",
        "domain": "客户",
        "definition": "会员间夜 ÷ 总间夜",
        "related_metrics": ["repurchase_rate"],
        "hot_score": 76,
    },
    {
        "standard_term": "compset_adr",
        "aliases": ["竞品房价", "对标房价", "片区均价"],
        "metric_id": "compset_adr",
        "unit": "元",
        "sample_query": "我的房价比竞品贵吗？",
        "domain": "竞对",
        "definition": "本店 ADR / 竞品集 ADR",
        "related_metrics": ["adr", "rgi"],
        "hot_score": 68,
    },
    {
        "standard_term": "reply_sla",
        "aliases": ["点评回复", "回复及时", "回复时长"],
        "metric_id": "reply_sla",
        "unit": "小时",
        "sample_query": "点评回复及时吗？",
        "domain": "口碑",
        "definition": "平均回复时长 vs SLA",
        "related_metrics": ["nps"],
        "hot_score": 62,
    },
    {
        "standard_term": "market_demand",
        "aliases": ["片区需求", "大环境", "行情", "市场需求"],
        "metric_id": "market_demand",
        "unit": "指数",
        "sample_query": "片区需求涨跌？",
        "domain": "竞对",
        "definition": "片区需求指数（demo）",
        "related_metrics": ["rgi"],
        "hot_score": 58,
    },
    # —— v1.3 客户域 ——
    {
        "standard_term": "cumulative_payment",
        "aliases": [
            "累计消费",
            "累计金额",
            "总消费",
            "LTV",
            "ltv",
            "消费总额",
            "消费最高",
            "total spend",
            "lifetime spend",
            "top spenders",
            "highest spend",
            "spend the most",
        ],
        "metric_id": "cumulative_payment",
        "unit": "元",
        "sample_query": "累计消费最高的前 5 个客人是谁？",
        "domain": "客户",
        "definition": "客户全生命周期实付总额（不受时间范围过滤）",
        "related_metrics": ["stay_count", "avg_order_value"],
        "hot_score": 96,
    },
    {
        "standard_term": "stay_count",
        "aliases": ["到店次数", "入住次数", "住店次数", "来住次数"],
        "metric_id": "stay_count",
        "unit": "次",
        "sample_query": "到店次数最多的客人有哪些？",
        "domain": "客户",
        "definition": "历史入住订单数（全生命周期）",
        "related_metrics": ["cumulative_payment"],
        "hot_score": 84,
    },
    {
        "standard_term": "avg_order_value",
        "aliases": ["客单价", "单次消费", "平均单间收入", "平均消费"],
        "metric_id": "avg_order_value",
        "unit": "元",
        "sample_query": "客单价分布如何？",
        "domain": "客户",
        "definition": "累计消费 ÷ 到店次数",
        "related_metrics": ["cumulative_payment", "stay_count"],
        "hot_score": 79,
    },
    {
        "standard_term": "last_stay_date",
        "aliases": ["最后入住", "上次来住", "多久没来", "沉睡天数", "沉睡客户", "沉睡"],
        "metric_id": "last_stay_date",
        "unit": "天",
        "sample_query": "沉睡客户有哪些？",
        "domain": "客户",
        "definition": "最近一笔离店日期距今天数",
        "related_metrics": ["stay_count"],
        "hot_score": 86,
    },
    {
        "standard_term": "guest_tag",
        "aliases": ["标签分群", "按标签", "客群标签", "客户标签", "分群客户"],
        "metric_id": "guest_tag",
        "unit": "人",
        "sample_query": "按标签分群的客户数？",
        "domain": "客户",
        "definition": "按标签统计客户人数",
        "related_metrics": ["segment_mix"],
        "hot_score": 77,
    },
]

# metric_id → 兼容旧 intent / 默认 query
METRIC_LEGACY_INTENT: dict[str, str] = {
    "ota_share": "ota_share_ratio",
    "repurchase_rate": "member_repurchase",
    "business_mix": "business_churn",
    "channel_profit": "channel_profit_loss",
    "direct_book_rate": "direct_book_rate",
    "segment_mix": "segment_mix",
    "weekday_occ": "weekday_occ",
    "review_topics": "review_topics",
    "nps": "nps_trend",
    "pickup_gap": "pickup_gap",
    "revpar": "revpar_trend",
}

# (metric_id, operator_id) → 组合意图（MVP；存量意图平迁 + 关键衍生）
COMPOSITE_INTENTS: dict[str, dict[str, Any]] = {
    # —— 入住率族 ——
    "occupancy_get_value": {
        "intent_label": "入住率现在多少",
        "group_name": "C",
        "metric_id": "occupancy_rate",
        "operator_id": "op_get_value",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_occupancy_kpi",
        "semantic_template": "本期入住率绝对值",
        "example_queries": ["入住率多少", "Occ% 是多少"],
        "keywords": [],
        "is_default": False,
    },
    "occupancy_compare_mom": {
        "intent_label": "入住率相比上月",
        "group_name": "C",
        "metric_id": "occupancy_rate",
        "operator_id": "op_compare_baseline",
        "applicable_dimensions": ["all"],
        "required_slots": ["period", "baseline"],
        "query_ref": "q_occupancy_kpi",
        "semantic_template": "入住率相对对比期（默认上月/环比）",
        "example_queries": ["这个月入住率相比上个月如何", "Occ% 同比", "出租率环比"],
        "keywords": [],
        "is_default": True,
        "default_question": "这个月入住率相比上个月如何？",
        "default_baseline": "环比",
    },
    "occupancy_trend": {
        "intent_label": "入住率走势",
        "group_name": "C",
        "metric_id": "occupancy_rate",
        "operator_id": "op_trend",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_occupancy_kpi",
        "semantic_template": "入住率趋势（对比期对照）",
        "example_queries": ["入住率走势", "OCC 变化"],
        "keywords": [],
        "is_default": False,
    },
    # —— ADR / RevPAR ——
    "adr_get_value": {
        "intent_label": "ADR 现在多少",
        "group_name": "C",
        "metric_id": "adr",
        "operator_id": "op_get_value",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_adr_kpi",
        "semantic_template": "本期 ADR",
        "example_queries": ["ADR 多少", "均价是多少"],
        "keywords": [],
        "is_default": False,
    },
    "adr_compare_mom": {
        "intent_label": "ADR 同比/环比",
        "group_name": "C",
        "metric_id": "adr",
        "operator_id": "op_compare_baseline",
        "applicable_dimensions": ["all"],
        "required_slots": ["period", "baseline"],
        "query_ref": "q_adr_kpi",
        "semantic_template": "ADR 相对对比期",
        "example_queries": ["ADR 同比", "均价相比上月"],
        "keywords": [],
        "is_default": False,
        "default_baseline": "同比",
    },
    "revpar_get_value": {
        "intent_label": "RevPAR 现在多少",
        "group_name": "C",
        "metric_id": "revpar",
        "operator_id": "op_get_value",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_revpar_kpi",
        "semantic_template": "本期 RevPAR",
        "example_queries": ["RevPAR 多少"],
        "keywords": [],
        "is_default": False,
    },
    "revpar_compare_mom": {
        "intent_label": "RevPAR 同比/环比",
        "group_name": "C",
        "metric_id": "revpar",
        "operator_id": "op_compare_baseline",
        "applicable_dimensions": ["all"],
        "required_slots": ["period", "baseline"],
        "query_ref": "q_revpar_kpi",
        "semantic_template": "RevPAR 相对对比期",
        "example_queries": ["RevPAR 同比", "每可用房收入相比上月"],
        "keywords": [],
        "is_default": False,
        "default_baseline": "同比",
    },
    "revpar_trend_all": {
        "intent_label": "RevPAR 走势",
        "group_name": "C",
        "metric_id": "revpar",
        "operator_id": "op_trend",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_revpar_trend",
        "semantic_template": "RevPAR/OCC/ADR 对照",
        "example_queries": ["RevPAR 走势", "每可用房收入变化"],
        "keywords": [],
        "is_default": False,
    },
    # —— OTA / 直订 组合 ——
    "ota_share_get_value": {
        "intent_label": "OTA 占比多少",
        "group_name": "A",
        "metric_id": "ota_share",
        "operator_id": "op_get_value",
        "applicable_dimensions": ["all"],
        "required_slots": ["period"],
        "query_ref": "q_ota_share_ratio",
        "semantic_template": "OTA 间夜占比",
        "example_queries": ["OTA 占比多少"],
        "keywords": [],
        "is_default": False,
    },
    "ota_share_compare_mom": {
        "intent_label": "OTA 占比同比环比",
        "group_name": "A",
        "metric_id": "ota_share",
        "operator_id": "op_compare_baseline",
        "applicable_dimensions": ["all"],
        "required_slots": ["period", "baseline"],
        "query_ref": "q_ota_share_ratio",
        "semantic_template": "OTA 占比相对警戒线与对比期",
        "example_queries": ["OTA 占比环比", "渠道依赖度同比"],
        "keywords": [],
        "is_default": False,
        "default_baseline": "环比",
    },
    "room_revenue_compare_mom": {
        "intent_label": "客房收入同比环比",
        "group_name": "C",
        "metric_id": "room_revenue",
        "operator_id": "op_compare_baseline",
        "applicable_dimensions": ["all"],
        "required_slots": ["period", "baseline"],
        "query_ref": "q_room_revenue_kpi",
        "semantic_template": "客房收入相对对比期",
        "example_queries": ["客房收入相比上月", "房费同比"],
        "keywords": [],
        "is_default": False,
        "default_baseline": "环比",
    },
    # —— v1.3 客户域 ——
    "guest_top_rank_cumulative_payment": {
        "intent_label": "累计消费 TopN 客户",
        "group_name": "G",
        "metric_id": "cumulative_payment",
        "operator_id": "op_rank_top",
        "applicable_dimensions": ["guest"],
        "required_slots": ["top_n"],
        "query_ref": "q_guest_top_cumulative",
        "semantic_template": "全生命周期累计消费最高的客户",
        "example_queries": ["累计消费最高的前 5 个客人是谁", "消费 Top5 客户", "LTV 最高客人"],
        "keywords": ["累计消费", "消费最高", "LTV"],
        "is_default": True,
        "default_question": "累计消费最高的前 5 个客人是谁？",
        "pii_level": "confirm",
        "ignore_period_filter": True,
    },
    "guest_top_rank_stay_count": {
        "intent_label": "到店次数 TopN 客户",
        "group_name": "G",
        "metric_id": "stay_count",
        "operator_id": "op_rank_top",
        "applicable_dimensions": ["guest"],
        "required_slots": ["top_n"],
        "query_ref": "q_guest_top_stay_count",
        "semantic_template": "到店次数最多的客户",
        "example_queries": ["到店次数最多的客人", "住店次数 Top5"],
        "keywords": ["到店次数", "入住次数"],
        "is_default": False,
        "pii_level": "confirm",
        "ignore_period_filter": True,
    },
    "guest_distribution_avg_order_value": {
        "intent_label": "客单价分布",
        "group_name": "G",
        "metric_id": "avg_order_value",
        "operator_id": "op_breakdown",
        "applicable_dimensions": ["guest"],
        "required_slots": [],
        "query_ref": "q_guest_aov_distribution",
        "semantic_template": "客单价分桶人数分布",
        "example_queries": ["客单价分布", "客单价结构"],
        "keywords": ["客单价"],
        "is_default": False,
        "pii_level": "none",
        "ignore_period_filter": True,
    },
    "guest_churn_warning_last_stay_date": {
        "intent_label": "沉睡客户告警",
        "group_name": "G",
        "metric_id": "last_stay_date",
        "operator_id": "op_rank_top",
        "applicable_dimensions": ["guest"],
        "required_slots": [],
        "query_ref": "q_guest_churn_warning",
        "semantic_template": "久未到店的沉睡客户清单（脱敏）",
        "example_queries": ["沉睡客户有哪些", "多久没来的客人"],
        "keywords": ["沉睡", "多久没来"],
        "is_default": False,
        "pii_level": "mask",
        "ignore_period_filter": True,
    },
    "guest_segment_count_by_tag": {
        "intent_label": "按标签分群客户数",
        "group_name": "G",
        "metric_id": "guest_tag",
        "operator_id": "op_breakdown",
        "applicable_dimensions": ["guest"],
        "required_slots": [],
        "query_ref": "q_guest_segment_by_tag",
        "semantic_template": "各标签下客户人数",
        "example_queries": ["按标签分群的客户数", "标签客户分布"],
        "keywords": ["标签分群", "按标签"],
        "is_default": False,
        "pii_level": "none",
        "ignore_period_filter": True,
    },
}


def glossary_active(*, limit: int = 30) -> list[dict[str, Any]]:
    rows = [g for g in DOMAIN_GLOSSARY if g.get("is_active", True)]
    rows.sort(key=lambda x: -int(x.get("hot_score") or 0))
    return rows[:limit]


def glossary_for_prompt(limit: int = 30) -> str:
    lines = []
    for g in glossary_active(limit=limit):
        aliases = ", ".join(g.get("aliases") or [])
        lines.append(f"- {g['standard_term']} {g.get('unit') or ''} = [{aliases}] → 口径：{g.get('definition') or ''}")
    return "\n".join(lines)


def _alias_hit(alias: str, text: str) -> bool:
    """别名匹配：长短语优先；短英文缩写用词边界。"""
    if not alias:
        return False
    if alias.isascii() and alias.isalpha() and len(alias) <= 4:
        return bool(re.search(rf"(?i)(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])", text))
    return alias in text or alias.lower() in text.lower()


def match_metric(q: str) -> Optional[dict[str, Any]]:
    """扫词典，优先最长别名命中。"""
    best = None
    best_len = -1
    for g in DOMAIN_GLOSSARY:
        for alias in g.get("aliases") or []:
            if _alias_hit(alias, q) and len(alias) > best_len:
                best = g
                best_len = len(alias)
    return best


def match_operator(q: str) -> Optional[str]:
    # 更具体算子优先：rank / breakdown / trend / compare / get_value
    order = ("op_rank_top", "op_breakdown", "op_trend", "op_compare_baseline", "op_get_value")
    for op_id in order:
        op = OPERATOR_CATALOG[op_id]
        if any(kw in q for kw in op["kws"]):
            return op_id
    return None


def infer_baseline_from_text(q: str, default: str = "环比") -> str:
    if any(k in q for k in ("同比", "去年", "同期", "去年同期")):
        return "同比"
    if any(k in q for k in ("环比", "上月", "上个月", "上个周", "上周")):
        return "环比"
    return default


def normalize(q: str) -> dict[str, Any]:
    """查询归一化：别名 → standard_term；识别 metric / operator。"""
    text = (q or "").strip()
    metric = match_metric(text)
    operator_id = match_operator(text)
    normalized = text
    metric_id = None
    if metric:
        metric_id = metric["metric_id"]
        # 按别名长度降序替换，避免短词抢先
        aliases = sorted(metric.get("aliases") or [], key=len, reverse=True)
        for alias in aliases:
            if not alias:
                continue
            if alias.isascii() and alias.isalpha() and len(alias) <= 4:
                normalized = re.sub(
                    rf"(?i)(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])",
                    metric["standard_term"],
                    normalized,
                )
            else:
                normalized = normalized.replace(alias, metric["standard_term"])
                # 大小写不敏感再扫一遍
                pattern = re.compile(re.escape(alias), re.IGNORECASE)
                normalized = pattern.sub(metric["standard_term"], normalized)
    return {
        "normalized": normalized,
        "metric_id": metric_id,
        "operator_id": operator_id,
        "standard_term": (metric or {}).get("standard_term"),
        "metric_label": None if not metric else (metric.get("aliases") or [metric_id])[0],
        "definition": (metric or {}).get("definition"),
        "unit": (metric or {}).get("unit"),
    }


def find_composite_intent(metric_id: str, operator_id: str) -> Optional[str]:
    for iid, meta in COMPOSITE_INTENTS.items():
        if meta.get("metric_id") == metric_id and meta.get("operator_id") == operator_id:
            return iid
    return None


def extract_top_n(q: str, default: int = 5) -> int:
    m = re.search(r"(?:前|top|Top)\s*(\d+)|(\d+)\s*个", q or "")
    if not m:
        return default
    n = int(m.group(1) or m.group(2) or default)
    return max(1, min(n, 20))


def decompose_route(q: str) -> dict[str, Any]:
    """0 候选兜底：normalize → (metric × operator) → intent_id。"""
    norm = normalize(q)
    text = q or ""
    metric_id = norm.get("metric_id")

    # 客户域特殊启发
    if any(k in text for k in ("沉睡", "多久没来")):
        metric_id = metric_id or "last_stay_date"
        norm["metric_id"] = metric_id
    if any(k in text for k in ("标签分群", "按标签", "客户标签")):
        metric_id = metric_id or "guest_tag"
        norm["metric_id"] = metric_id

    if not metric_id:
        return {
            **norm,
            "intent_id": None,
            "baseline": None,
            "top_n": None,
            "pipeline": _pipeline_payload(q, norm, None, None),
        }

    op = norm.get("operator_id")
    # 客户累计/到店默认走排名
    if metric_id in ("cumulative_payment", "stay_count") and not op:
        op = "op_rank_top"
    if metric_id in ("avg_order_value", "guest_tag") and not op:
        op = "op_breakdown"
    if metric_id == "last_stay_date" and not op:
        op = "op_rank_top"
    op = op or "op_compare_baseline"

    intent_id = find_composite_intent(metric_id, op)
    if not intent_id:
        for iid, meta in COMPOSITE_INTENTS.items():
            if meta.get("metric_id") == metric_id:
                intent_id = iid
                op = meta.get("operator_id") or op
                break
    if not intent_id:
        intent_id = METRIC_LEGACY_INTENT.get(metric_id)
        op = op or "op_get_value"

    baseline = None
    if op == "op_compare_baseline" or (intent_id and "compare" in (intent_id or "")):
        default_bl = "环比"
        if intent_id and intent_id in COMPOSITE_INTENTS:
            default_bl = COMPOSITE_INTENTS[intent_id].get("default_baseline") or default_bl
        baseline = infer_baseline_from_text(q, default_bl)

    top_n = None
    meta = COMPOSITE_INTENTS.get(intent_id or "") or {}
    if "top_n" in (meta.get("required_slots") or []) or (intent_id or "").startswith("guest_top_"):
        top_n = extract_top_n(text, 5)

    return {
        **norm,
        "operator_id": op,
        "intent_id": intent_id,
        "baseline": baseline,
        "top_n": top_n,
        "pii_level": meta.get("pii_level") or "none",
        "ignore_period_filter": bool(meta.get("ignore_period_filter")),
        "pipeline": _pipeline_payload(q, {**norm, "operator_id": op}, intent_id, baseline),
    }


def _pipeline_payload(
    raw: str,
    norm: dict,
    intent_id: Optional[str],
    baseline: Optional[str],
) -> list[dict[str, str]]:
    from infra.i18n import t

    meta = COMPOSITE_INTENTS.get(intent_id or "") or {}
    op_id = norm.get("operator_id") or "—"
    op_label = t(str((OPERATOR_CATALOG.get(op_id) or {}).get("label") or op_id))
    intent_label = t(str(meta.get("intent_label") or "")) if intent_id else ""
    # 展示层：原文跟 Locale（预设 msgid → 英文）；归一化优先 metric + 译文，避免残留中文
    disp_raw = t(str(raw or ""))
    st = norm.get("standard_term") or norm.get("metric_id")
    if disp_raw and disp_raw != str(raw or ""):
        disp_norm = f"{st} · {disp_raw}" if st else disp_raw
    else:
        disp_norm = str(norm.get("normalized") or raw or "")
    baseline_bit = ""
    if baseline:
        baseline_bit = t(" · baseline={b}", b=t(str(baseline)))
    return [
        {
            "step": "1",
            "title": t("查询归一化"),
            "detail": t("「{raw}」→ 「{normalized}」", raw=disp_raw, normalized=disp_norm),
        },
        {
            "step": "2",
            "title": t("指代消解"),
            "detail": t("原句不变（无代词）"),
        },
        {
            "step": "3",
            "title": t("意图分解"),
            "detail": t(
                "metric={metric} · operator={op}（{op_label}）{baseline}",
                metric=norm.get("metric_id") or "—",
                op=op_id,
                op_label=op_label,
                baseline=baseline_bit,
            ),
        },
        {
            "step": "4",
            "title": t("catalog 路由"),
            "detail": (
                t("命中 {intent_id} · {label}", intent_id=intent_id or "—", label=intent_label)
                if intent_id
                else t("未命中组合意图")
            ),
        },
    ]


def default_questions_dynamic() -> list[dict[str, str]]:
    """默认问题：存量默认 + 入住率 + 客户 Top（后续可按频次动态）。"""
    from analytics.ask_catalog import default_presets

    out = list(default_presets())
    for iid in ("occupancy_compare_mom", "guest_top_rank_cumulative_payment"):
        occ = COMPOSITE_INTENTS.get(iid) or {}
        if occ.get("default_question"):
            out.append(
                {
                    "intent_id": iid,
                    "question": occ["default_question"],
                    "label": occ["intent_label"],
                }
            )
    seen = set()
    uniq = []
    for p in out:
        k = p.get("question") or p.get("intent_id")
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    return uniq[:10]
