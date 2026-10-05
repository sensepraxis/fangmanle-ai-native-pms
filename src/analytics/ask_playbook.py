# SPDX-License-Identifier: Apache-2.0
"""AI 问数 · 追问 playbook（运营预注册，模型只挑选组织白话）。"""

from __future__ import annotations

from typing import Any

# tip_id → 条目；key = f"{trigger_intent}.{order}"
PLAYBOOK: dict[str, list[dict[str, Any]]] = {
    "ota_share_ratio": [
        {
            "id": "ota_share_ratio.1",
            "name": "官微直订权益升级",
            "desc": "会员折扣与延迟退房等直订权益，拉动官网/企微占比",
            "expected_impact": "预计直订拉新约 8%",
        },
        {
            "id": "ota_share_ratio.2",
            "name": "企业协议客定向拉新",
            "desc": "面向 HR / 商会推进协议签约",
            "expected_impact": "预计约 +12 单/月",
        },
        {
            "id": "ota_share_ratio.3",
            "name": "OTA 返佣谈判",
            "desc": "与主要 OTA 协商佣金结构",
            "expected_impact": "佣金率每降 1pt，按量测算月节省可观",
        },
    ],
    "business_churn": [
        {
            "id": "business_churn.1",
            "name": "重启企业协议拜访",
            "desc": "对高频协议客户做季度回访",
            "expected_impact": "预计挽回若干协议客户",
        },
        {
            "id": "business_churn.2",
            "name": "工作日商务套餐",
            "desc": "住宿 + 早餐 + 发票组合",
            "expected_impact": "预计商务单量提升",
        },
        {
            "id": "business_churn.3",
            "name": "协议客经理积分",
            "desc": "企业管理员积分，刺激主动带新",
            "expected_impact": "提升转介绍意愿",
        },
    ],
    "member_repurchase": [
        {
            "id": "member_repurchase.1",
            "name": "企微沉睡召回",
            "desc": "对近期未消费会员发放唤醒券",
            "expected_impact": "预计回流约一成沉睡会员",
        },
        {
            "id": "member_repurchase.2",
            "name": "会员专属价",
            "desc": "仅会员可见价，降低佣金侵蚀",
            "expected_impact": "提升会员间夜占比",
        },
        {
            "id": "member_repurchase.3",
            "name": "生日/升房权益",
            "desc": "情感连接型权益，促进复购",
            "expected_impact": "预计复购率小幅提升",
        },
    ],
    "channel_profit_loss": [
        {
            "id": "channel_profit_loss.1",
            "name": "亏钱渠道控量",
            "desc": "对净收益为负的渠道暂停高成本活动并观察",
            "expected_impact": "控制亏损敞口",
        },
        {
            "id": "channel_profit_loss.2",
            "name": "返佣谈判",
            "desc": "与高佣金渠道协商费率",
            "expected_impact": "降低获客成本",
        },
        {
            "id": "channel_profit_loss.3",
            "name": "替代渠道测试",
            "desc": "加投直订/其他渠道对比净收益",
            "expected_impact": "优化渠道结构",
        },
    ],
    "review_topics": [
        {
            "id": "review_topics.1",
            "name": "高峰人力调度",
            "desc": "退房高峰增援前台，缩短等待",
            "expected_impact": "降低排队类投诉",
        },
        {
            "id": "review_topics.2",
            "name": "工程介入",
            "desc": "噪音/空调等硬件问题批次整改",
            "expected_impact": "2 周内闭环高频硬件投诉",
        },
        {
            "id": "review_topics.3",
            "name": "餐饮改善",
            "desc": "菜单更新与客评反馈闭环",
            "expected_impact": "降低餐饮相关差评",
        },
    ],
    "revpar_trend": [
        {
            "id": "revpar_trend.1",
            "name": "平日补量",
            "desc": "针对低入住平日推出连住/商务套餐",
            "expected_impact": "抬升 OCC，拉动 RevPAR",
        },
        {
            "id": "revpar_trend.2",
            "name": "周末价差复核",
            "desc": "核对周末与平日价差是否到位",
            "expected_impact": "改善收益结构",
        },
    ],
    "occupancy_compare_mom": [
        {
            "id": "occupancy_compare_mom.1",
            "name": "平日补量活动",
            "desc": "针对环比下滑的平日窗口释放连住/商务套餐",
            "expected_impact": "预计抬升周中 OCC",
        },
        {
            "id": "occupancy_compare_mom.2",
            "name": "临期渠道补量",
            "desc": "对缺口日期适度加投直订曝光（到价格助手确认）",
            "expected_impact": "缩小短期入住落差",
        },
        {
            "id": "occupancy_compare_mom.3",
            "name": "企微沉睡召回",
            "desc": "对近 30 天未到店会员发唤醒券",
            "expected_impact": "预计回流部分间夜",
        },
    ],
    "direct_book_rate": [
        {
            "id": "direct_book_rate.1",
            "name": "直订权益曝光",
            "desc": "在企微/到店强化直订权益说明",
            "expected_impact": "提升直订转化",
        },
    ],
    "segment_mix": [
        {
            "id": "segment_mix.1",
            "name": "弱势客群定向活动",
            "desc": "对占比下滑客群做专题促销或协议",
            "expected_impact": "平衡客群结构",
        },
    ],
    "weekday_occ": [
        {
            "id": "weekday_occ.1",
            "name": "平日商务套餐",
            "desc": "工作日连住优惠",
            "expected_impact": "抬升周中 OCC",
        },
    ],
    "pickup_gap": [
        {
            "id": "pickup_gap.1",
            "name": "临期补量",
            "desc": "对缺口窗口释放连住/预付产品（到价格助手确认）",
            "expected_impact": "缩小预订缺口",
        },
    ],
    "nps_trend": [
        {
            "id": "nps_trend.1",
            "name": "差评主题闭环",
            "desc": "按本月差评主题排优先级整改",
            "expected_impact": "改善均分与 NPS",
        },
    ],
}

FOLLOWUP_KEYWORDS = {
    "followup_optimize": [
        "提升",
        "优化",
        "怎么办",
        "怎么解决",
        "如何降低",
        "怎么降低",
        "该怎么办",
        "怎么改",
        "怎么弄",
        "有没有办法",
        "怎么提升",
        "如何提升",
        "怎么优化",
        "能提升吗",
        "能改善吗",
        "如何改善",
        "怎么改善",
        "对策",
        "建议",
    ],
    "followup_impact": [
        "影响",
        "后果",
        "会不会更糟",
        "好不好",
        "会怎样",
        "会带来",
        "好不",
        "有没有风险",
        "会不会",
        "趋势",
    ],
    "followup_diagnose": [
        "为什么",
        "什么原因",
        "怎么导致",
        "原因",
        "为何",
        "怎么造成",
        "为啥",
    ],
    "followup_compare": [
        "对比",
        "哪个更",
        "和去年",
        "同比",
        "环比",
        "比起",
        "相比",
        "哪个糟",
    ],
}

PRONOUN_MARKERS = [
    "这样",
    "那样",
    "这个",
    "那个",
    "它",
    "这事",
    "这情况",
    "刚才",
    "上面",
    "那段",
    "这个数",
    "那块",
    "这种情况",
    "这个结果",
    "这个问题",
]


def _localize_tip(tip: dict[str, Any]) -> dict[str, Any]:
    from infra.i18n import t as _t

    out = dict(tip)
    for key in ("name", "desc", "expected_impact"):
        if out.get(key):
            out[key] = _t(str(out[key]))
    return out


def tips_for(trigger_intent_id: str) -> list[dict[str, Any]]:
    return [_localize_tip(x) for x in list(PLAYBOOK.get(trigger_intent_id) or [])[:3]]


def filter_playbook_ids(trigger_intent_id: str, claimed: list[str] | None) -> list[dict[str, Any]]:
    """只保留 playbook 表内存在的 tip；丢弃模型瞎编的条目。"""
    allowed = {tip["id"]: tip for tip in tips_for(trigger_intent_id)}
    if not claimed:
        return list(allowed.values())[:3]
    out = []
    for cid in claimed:
        if cid in allowed:
            out.append(allowed[cid])
    return out or list(allowed.values())[:3]
