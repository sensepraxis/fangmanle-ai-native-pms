# SPDX-License-Identifier: Apache-2.0
"""问数意图目录（OpenCore 只读分析内核；模型只引用 intent_id，SQL 不进 prompt）。"""

from __future__ import annotations

from typing import Any

from infra.i18n import TranslatingMap

# 必填槽 / 查询键 / 例句 —— SQL 永不进 prompt
INTENT_CATALOG: dict[str, dict[str, Any]] = {
    "channel_profit_loss": {
        "intent_label": "哪些渠道在亏钱",
        "group_name": "A",
        "required_slots": ["period"],
        "query_ref": "q_channel_profit_loss",
        "semantic_template": "各渠道净收益（营收−佣金估算）哪些为负",
        "example_queries": ["哪些渠道亏", "渠道净收益", "哪个渠道在赔钱"],
        "keywords": ["渠道", "亏", "净收益", "赚", "赔", "亏钱"],
        "is_default": True,
        "default_question": "本月哪些渠道在亏钱？",
    },
    "ota_share_ratio": {
        "intent_label": "OTA 占比是否过高",
        "group_name": "A",
        "required_slots": ["period"],
        "query_ref": "q_ota_share_ratio",
        "semantic_template": "OTA 间夜占比相对 55% 警戒线",
        "example_queries": ["OTA 占比", "太依赖携程吗", "OTA 是不是太高"],
        "keywords": ["ota", "OTA", "占比", "携程", "美团", "飞猪", "依赖", "太高"],
        "is_default": True,
        "default_question": "OTA 占比是否过高？",
    },
    "direct_book_rate": {
        "intent_label": "直订率升了没",
        "group_name": "A",
        "required_slots": ["period"],
        "query_ref": "q_direct_book_rate",
        "semantic_template": "直订（官网/企微/小程序口径）占比变化",
        "example_queries": ["直订率", "官网占比", "直订升了吗"],
        "keywords": ["直订", "官网", "小程序", "企微"],
        "is_default": False,
    },
    "business_churn": {
        "intent_label": "商务客是不是在流失",
        "group_name": "B",
        "required_slots": ["period"],
        "query_ref": "q_business_churn",
        "semantic_template": "商务客占比同比变化",
        "example_queries": ["商务客少了", "公司客", "商务客流失"],
        "keywords": ["商务", "公司客", "商旅", "b2b", "B2B", "流失"],
        "is_default": True,
        "default_question": "商务客是不是在流失？",
    },
    "member_repurchase": {
        "intent_label": "会员复购有没有变差",
        "group_name": "B",
        "required_slots": ["period"],
        "query_ref": "q_member_repurchase",
        "semantic_template": "会员间夜占比环比变化（复购代理）",
        "example_queries": ["会员复购", "回头客", "会员变差"],
        "keywords": ["会员", "复购", "回头", "老客"],
        "is_default": True,
        "default_question": "会员复购有没有变差？",
    },
    "segment_mix": {
        "intent_label": "客群结构变化",
        "group_name": "B",
        "required_slots": ["period"],
        "query_ref": "q_segment_mix",
        "semantic_template": "各客群间夜占比",
        "example_queries": ["客群变了", "谁在订", "客群结构"],
        "keywords": ["客群", "结构", "谁在订", "休闲", "团队"],
        "is_default": False,
    },
    "revpar_trend": {
        "intent_label": "RevPAR 同比环比",
        "group_name": "C",
        "required_slots": ["period"],
        "query_ref": "q_revpar_trend",
        "semantic_template": "客房 ADR/OCC/RevPAR 与对比期",
        "example_queries": ["RevPAR 怎么样", "revpar", "每房收益"],
        "keywords": ["revpar", "RevPAR", "每房收益", "adr", "ADR", "出租率"],
        "is_default": False,
    },
    "weekday_occ": {
        "intent_label": "平日为何低入住",
        "group_name": "C",
        "required_slots": ["period"],
        "query_ref": "q_weekday_occ",
        "semantic_template": "平日 vs 周末间夜结构",
        "example_queries": ["周中没人", "平日入住", "周末"],
        "keywords": ["平日", "周中", "周末", "工作日"],
        "is_default": False,
    },
    "review_topics": {
        "intent_label": "客人在吐槽啥",
        "group_name": "D",
        "required_slots": ["period"],
        "query_ref": "q_review_topics",
        "semantic_template": "点评主题与均分",
        "example_queries": ["差评原因", "投诉", "客人在骂啥", "吐槽"],
        "keywords": ["吐槽", "差评", "投诉", "骂", "不满", "怨", "点评"],
        "is_default": False,
    },
    "nps_trend": {
        "intent_label": "NPS / 评分如何",
        "group_name": "D",
        "required_slots": ["period"],
        "query_ref": "q_nps_trend",
        "semantic_template": "点评均分与 NPS 代理",
        "example_queries": ["NPS", "点评分", "口碑"],
        "keywords": ["nps", "NPS", "评分", "口碑", "好评"],
        "is_default": False,
    },
    "pickup_gap": {
        "intent_label": "未来预订进度缺口",
        "group_name": "F",
        "required_slots": ["horizon"],
        "query_ref": "q_pickup_gap",
        "semantic_template": "未来 N 天已订相对基线缺口",
        "example_queries": ["下周满了吗", "预订进度", "pickup"],
        "keywords": ["预订", "进度", "满房", "缺口", "pickup", "下周", "未来"],
        "is_default": False,
    },
}

# 追问意图（仅在会话有上一轮结论时启用）
FOLLOWUP_INTENTS = {
    "followup_optimize": {
        "intent_label": "怎么优化/提升",
        "group_name": "FU",
        "required_slots": [],
        "query_ref": "q_followup_optimize",
        "semantic_template": "基于上一轮结论给出 playbook 优化建议",
        "example_queries": ["这样能提升吗", "怎么办", "怎么解决", "如何降低"],
        "is_default": False,
        "is_followup": True,
    },
    "followup_impact": {
        "intent_label": "会带来什么影响",
        "group_name": "FU",
        "required_slots": [],
        "query_ref": "q_followup_impact",
        "semantic_template": "基于上一轮结论推断趋势影响",
        "example_queries": ["影响什么", "会不会更糟", "好不好"],
        "is_default": False,
        "is_followup": True,
    },
    "followup_diagnose": {
        "intent_label": "为什么会这样",
        "group_name": "FU",
        "required_slots": [],
        "query_ref": "q_followup_diagnose",
        "semantic_template": "解释上一轮结论的驱动因子",
        "example_queries": ["为什么", "什么原因", "怎么导致的"],
        "is_default": False,
        "is_followup": True,
    },
    "followup_compare": {
        "intent_label": "对比一下",
        "group_name": "FU",
        "required_slots": [],
        "query_ref": "q_followup_compare",
        "semantic_template": "对比上一轮指标与对照期/对照实体",
        "example_queries": ["和去年比呢", "哪个更糟", "对比一下"],
        "is_default": False,
        "is_followup": True,
    },
}

ACTION_KEYWORDS = ["调低", "调高", "改价", "降价", "涨价", "关房", "改库存", "提价", "把价"]

SPECIAL_INTENTS = {
    "action_not_question": {
        "intent_label": "这是操作不是问数",
        "group_name": "X",
        "required_slots": [],
        "query_ref": None,
        "is_default": False,
    },
    "unknown": {
        "intent_label": "暂不支持的问题",
        "group_name": "X",
        "required_slots": [],
        "query_ref": None,
        "is_default": False,
    },
}

PERIOD_ALIASES = {
    "本周": "week",
    "这周": "week",
    "这一周": "week",
    "本月": "month",
    "这个月": "month",
    "这月": "month",
    "本季": "quarter",
    "这一季": "quarter",
    "季度": "quarter",
    "自定义": "custom",
}

PERIOD_LABELS = TranslatingMap({"week": "本周", "month": "本月", "quarter": "本季", "custom": "自定义"})


def default_presets() -> list[dict[str, str]]:
    out = []
    for iid, meta in INTENT_CATALOG.items():
        if meta.get("is_default") and meta.get("default_question"):
            out.append({"intent_id": iid, "question": meta["default_question"], "label": meta["intent_label"]})
    return out


def intent_list_for_prompt(*, include_followup: bool = False) -> str:
    lines = []
    for iid, meta in INTENT_CATALOG.items():
        slots = ",".join(meta.get("required_slots") or []) or "无"
        lines.append(f"- {iid}(必填:{slots}): {meta['intent_label']}")
    from analytics.ask_domain import COMPOSITE_INTENTS

    for iid, meta in COMPOSITE_INTENTS.items():
        if iid in INTENT_CATALOG:
            continue
        slots = ",".join(meta.get("required_slots") or []) or "无"
        lines.append(f"- {iid}(必填:{slots}): {meta['intent_label']}")
    if include_followup:
        lines.append("- 追问意图（仅对话历史非空时可用）：")
        for iid, meta in FOLLOWUP_INTENTS.items():
            slots = ",".join(meta.get("required_slots") or []) or "无"
            lines.append(f"  - {iid}(必填:{slots}): {meta['intent_label']}")
    return "\n".join(lines)


def all_intent_ids() -> set[str]:
    from analytics.ask_domain import COMPOSITE_INTENTS

    return (
        set(INTENT_CATALOG.keys())
        | set(FOLLOWUP_INTENTS.keys())
        | set(SPECIAL_INTENTS.keys())
        | set(COMPOSITE_INTENTS.keys())
    )


def is_followup_intent(intent_id: str | None) -> bool:
    return bool(intent_id) and intent_id in FOLLOWUP_INTENTS


def get_intent(intent_id: str) -> dict[str, Any] | None:
    if intent_id in INTENT_CATALOG:
        return {"intent_id": intent_id, **INTENT_CATALOG[intent_id]}
    if intent_id in FOLLOWUP_INTENTS:
        return {"intent_id": intent_id, **FOLLOWUP_INTENTS[intent_id]}
    from analytics.ask_domain import COMPOSITE_INTENTS

    if intent_id in COMPOSITE_INTENTS:
        return {"intent_id": intent_id, **COMPOSITE_INTENTS[intent_id]}
    if intent_id in SPECIAL_INTENTS:
        return {"intent_id": intent_id, **SPECIAL_INTENTS[intent_id]}
    return None


def register_intent(intent_id: str, meta: dict[str, Any], *, catalog: str = "main") -> None:
    """插件/测试可追加意图（默认写入 INTENT_CATALOG）。

    catalog: main | followup | special
    """
    target = {
        "main": INTENT_CATALOG,
        "followup": FOLLOWUP_INTENTS,
        "special": SPECIAL_INTENTS,
    }.get(catalog)
    if target is None:
        raise ValueError(f"unknown catalog: {catalog}")
    target[intent_id] = dict(meta)
