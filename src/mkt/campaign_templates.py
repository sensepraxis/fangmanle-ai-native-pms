# SPDX-License-Identifier: Apache-2.0
"""营销页面 / 活动模板常量。

从原 `bootstrap.ensure_mkt` 抽离；ensure_mkt_schema / seed_mkt_demo 仍在
`bootstrap.ensure_mkt` 里。
"""

from __future__ import annotations

BIND_TEMPLATE_BLOCKS = [
    {
        "id": "b1",
        "type": "banner",
        "props": {
            "badge": "专属管家 · 扫码礼遇",
            "title": "填写手机号 领取优惠券",
            "subtitle": "提交后开通专属管家档案，优惠券可在本店房费使用。",
            "bg": "#0f3d2e",
        },
    },
    {
        "id": "b2",
        "type": "coupon_card",
        "props": {"coupon_id": None, "bind_pool": True},
    },
    {
        "id": "b3",
        "type": "form_phone",
        "props": {"label": "手机号", "placeholder": "请输入预订/入住手机号", "required": True},
    },
    {
        "id": "b4",
        "type": "button",
        "props": {"text": "提交并领取优惠券", "action": "submit_bind"},
    },
    {
        "id": "b5",
        "type": "text",
        "props": {"text": "提交后将绑定专属管家档案（OneID）。每份企微身份仅可领取一次。优惠券仅限本店房费使用。"},
    },
]


MEMBER_CENTER_BLOCKS = [
    {
        "id": "mc1",
        "type": "banner",
        "props": {
            "badge": "专属会员中心",
            "title": "我的会员中心",
            "subtitle": "查看私域优惠券、订单与会员权益",
        },
    },
    {"id": "mc2", "type": "member_header", "props": {"show_stats": True}},
    {
        "id": "mc3",
        "type": "nav_tabs",
        "props": {
            "tabs": [
                {"key": "coupon", "label": "我的券"},
                {"key": "order", "label": "历史订单"},
                {"key": "benefit", "label": "权益中心"},
            ],
        },
    },
    {"id": "mc4", "type": "coupon_wallet", "props": {"tab": "coupon", "title": "私域优惠券"}},
    {"id": "mc5", "type": "order_list", "props": {"tab": "order", "title": "历史订单", "limit": 12}},
    {"id": "mc6", "type": "benefit_list", "props": {"tab": "benefit", "title": "权益中心"}},
    {
        "id": "mc7",
        "type": "text",
        "props": {"text": "本页由酒店装修发布。券仅限本店私域渠道发放，到店出示券码即可核销。"},
    },
]


# 老客扫码中间页（对标原 renderWallet 界面）
RETURNING_WELCOME_BLOCKS = [
    {
        "id": "rw1",
        "type": "banner",
        "props": {
            "badge": "欢迎回来",
            "title": "{guest_name}，您的私域礼遇",
            "subtitle": "欢迎回来！以下是您在本店私域领取的全部优惠券",
        },
    },
    {"id": "rw2", "type": "coupon_wallet", "props": {"title": "私域优惠券", "sum_style": "returning"}},
    {
        "id": "rw3",
        "type": "button",
        "props": {"text": "进入专属会员中心", "action": "go_portal"},
    },
]


SYSTEM_TEMPLATES = [
    {
        "template_key": "tpl_bind",
        "name": "单券领取（企微欢迎语）",
        "category": "bind",
        "blocks": BIND_TEMPLATE_BLOCKS,
    },
    {
        "template_key": "tpl_member_center",
        "name": "会员中心",
        "category": "member",
        "blocks": MEMBER_CENTER_BLOCKS,
    },
    {
        "template_key": "tpl_returning",
        "name": "老客回访（券包）",
        "category": "returning",
        "blocks": RETURNING_WELCOME_BLOCKS,
    },
    {
        "template_key": "tpl_pack",
        "name": "券包大礼包",
        "category": "pack",
        "blocks": [
            {
                "id": "p1",
                "type": "banner",
                "props": {"title": "新人礼包到账", "subtitle": "领完即可预订", "badge": "限时"},
            },
            {"id": "p2", "type": "coupon_card", "props": {"bind_pool": True}},
            {"id": "p3", "type": "form_phone", "props": {"label": "手机号", "placeholder": "11 位手机号"}},
            {"id": "p4", "type": "button", "props": {"text": "一键领取", "action": "submit_bind"}},
        ],
    },
    {
        "template_key": "tpl_festival",
        "name": "节日活动页",
        "category": "festival",
        "blocks": [
            {
                "id": "f1",
                "type": "banner",
                "props": {"title": "中秋连住特惠", "subtitle": "连住两晚更划算", "badge": "中秋"},
            },
            {"id": "f2", "type": "image", "props": {"src": "", "alt": "节日主视觉"}},
            {"id": "f3", "type": "coupon_card", "props": {"bind_pool": True}},
            {"id": "f4", "type": "form_phone", "props": {"label": "手机号"}},
            {"id": "f5", "type": "button", "props": {"text": "立即领取", "action": "submit_bind"}},
        ],
    },
    {
        "template_key": "tpl_member",
        "name": "会员专享领券",
        "category": "bind",
        "blocks": [
            {
                "id": "mm1",
                "type": "banner",
                "props": {"title": "会员专享折扣", "subtitle": "登录手机号核销身份", "badge": "会员"},
            },
            {"id": "mm2", "type": "coupon_card", "props": {"bind_pool": True}},
            {"id": "mm3", "type": "form_phone", "props": {"label": "会员手机号"}},
            {"id": "mm4", "type": "button", "props": {"text": "领取会员券", "action": "submit_bind"}},
            {"id": "mm5", "type": "cs", "props": {"text": "联系专属管家"}},
        ],
    },
]


CAMPAIGN_TEMPLATES = [
    {
        "id": "holiday",
        "name": "节假日活动",
        "type": "holiday",
        "ico": "🌕",
        "desc": "春节/国庆/中秋通用模板，预填 7 天周期与节假日客群。",
    },
    {
        "id": "seasonal",
        "name": "淡季促销",
        "type": "seasonal",
        "ico": "📉",
        "desc": "入住率低于 60% 自动推荐，固定折扣 + 全房型。",
    },
    {"id": "weekend", "name": "周末特惠", "type": "weekend", "ico": "🛏️", "desc": "周五-周日限时折扣，升房券绑定。"},
    {
        "id": "member_day",
        "name": "会员日",
        "type": "member",
        "ico": "👑",
        "desc": "每月固定日期会员专享，双倍积分 + 升房。",
    },
    {"id": "birthday", "name": "生日特惠", "type": "birthday", "ico": "🎂", "desc": "自动化触发，触发器：生日当天。"},
    {
        "id": "ota_compare",
        "name": "OTA 比价",
        "type": "ota_compare",
        "ico": "⚖️",
        "desc": "动态底价防 OTA 倒挂，不发券。",
    },
]
