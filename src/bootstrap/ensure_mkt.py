# SPDX-License-Identifier: Apache-2.0
"""营销获客：建表 + 种子数据。

页面 / 活动模板常量已抽到 `mkt.campaign_templates`；本文件保留 schema 保活与
种子灌入函数。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from mkt.campaign_templates import (
    BIND_TEMPLATE_BLOCKS,
    CAMPAIGN_TEMPLATES,
    MEMBER_CENTER_BLOCKS,
    RETURNING_WELCOME_BLOCKS,
    SYSTEM_TEMPLATES,
)
from models import (
    Base,
    Guest,
    GuestIdentity,
    HotelMktSettings,
    MktAutomation,
    MktCampaign,
    MktCoupon,
    MktCouponGrant,
    MktCouponGrantLog,
    MktCouponRedeem,
    MktCouponTrigger,
    MktCustomerNote,
    MktGuestWallet,
    MktMemberLevel,
    MktStoredValuePlan,
    WxLandingPage,
    WxLandingTemplate,
)


def _add_col_if_missing(conn, insp, table: str, col: str, ddl: str) -> None:
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_mkt_schema(engine) -> None:
    Base.metadata.create_all(
        engine,
        tables=[
            MktCampaign.__table__,
            MktCoupon.__table__,
            MktCouponGrant.__table__,
            MktCouponTrigger.__table__,
            MktCouponGrantLog.__table__,
            MktCouponRedeem.__table__,
            WxLandingTemplate.__table__,
            WxLandingPage.__table__,
            MktCustomerNote.__table__,
            HotelMktSettings.__table__,
            MktMemberLevel.__table__,
            MktStoredValuePlan.__table__,
            MktGuestWallet.__table__,
            MktAutomation.__table__,
        ],
    )
    # 兜底：旧库缺列时补齐（PostgreSQL）
    insp = inspect(engine)
    with engine.begin() as conn:
        insp_conn = inspect(conn)
        # 批次扩展列（权威稿 §6）
        for col, ddl in [
            ("coupon_type", "coupon_type VARCHAR(16)"),
            ("reduce_amount", "reduce_amount NUMERIC(10,2)"),
            ("discount_rate", "discount_rate NUMERIC(5,3)"),
            ("max_discount", "max_discount NUMERIC(10,2)"),
            ("benefit_key", "benefit_key VARCHAR(32)"),
            ("benefit_value", "benefit_value VARCHAR(64)"),
            ("face_text", "face_text VARCHAR(128)"),
            ("scope_type", "scope_type VARCHAR(16) DEFAULT 'ALL'"),
            ("scope_rooms", "scope_rooms TEXT"),
            ("granted_qty", "granted_qty INTEGER DEFAULT 0"),
            ("validity_mode", "validity_mode VARCHAR(8) DEFAULT 'FIXED'"),
            ("validity_days", "validity_days INTEGER"),
            ("batch_valid_from", "batch_valid_from TIMESTAMP"),
            ("batch_valid_to", "batch_valid_to TIMESTAMP"),
            ("created_by", "created_by VARCHAR(32)"),
        ]:
            _add_col_if_missing(conn, insp, "mkt_coupons", col, ddl)

        # 触发表扩展
        for col, ddl in [
            ("name", "name VARCHAR(128)"),
            ("last_run_at", "last_run_at TIMESTAMP"),
            ("granted_total", "granted_total INTEGER DEFAULT 0"),
        ]:
            _add_col_if_missing(conn, insp, "mkt_coupon_triggers", col, ddl)

        # 实例扩展列
        for col, ddl in [
            ("coupon_type", "coupon_type VARCHAR(16)"),
            ("face_text", "face_text VARCHAR(128)"),
            ("valid_from", "valid_from TIMESTAMP"),
            ("valid_to", "valid_to TIMESTAMP"),
            ("grant_event", "grant_event VARCHAR(32)"),
            ("claim_at", "claim_at TIMESTAMP"),
            ("used_amount", "used_amount NUMERIC(10,2)"),
            ("redeemed_by", "redeemed_by VARCHAR(32)"),
        ]:
            _add_col_if_missing(conn, insp, "mkt_coupon_grants", col, ddl)

        # 回填批次有效期模板 & 类型
        if insp_conn.has_table("mkt_coupons"):
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET "
                    "batch_valid_from = COALESCE(batch_valid_from, valid_from), "
                    "batch_valid_to = COALESCE(batch_valid_to, valid_to), "
                    "validity_mode = COALESCE(validity_mode, 'FIXED') "
                    "WHERE batch_valid_from IS NULL OR batch_valid_to IS NULL OR validity_mode IS NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='DISCOUNT' WHERE type='discount' AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='CASH_ALL', threshold=0 WHERE type='reduction' AND COALESCE(threshold,0)=0 AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='CASH_ROOM' WHERE type='reduction' AND COALESCE(threshold,0)>0 AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='BENEFIT', benefit_key='FREE_NIGHT' WHERE type='night_up' AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='BENEFIT', benefit_key='ROOM_UPGRADE' WHERE type='room_up' AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET coupon_type='BENEFIT', benefit_key='CUSTOM' WHERE type='time_window' AND (coupon_type IS NULL OR coupon_type='')"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET discount_rate=face_value WHERE coupon_type='DISCOUNT' AND discount_rate IS NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE mkt_coupons SET reduce_amount=face_value WHERE coupon_type IN ('CASH_ROOM','CASH_ALL') AND reduce_amount IS NULL"
                )
            )

        if insp_conn.has_table("mkt_coupon_grants"):
            conn.execute(text("UPDATE mkt_coupon_grants SET status='AVAILABLE' WHERE status='unused'"))
            conn.execute(text("UPDATE mkt_coupon_grants SET status='USED' WHERE status='used'"))
            conn.execute(text("UPDATE mkt_coupon_grants SET status='EXPIRED' WHERE status='expired'"))
            conn.execute(text("UPDATE mkt_coupon_grants SET status='VOID' WHERE status='void'"))
            conn.execute(
                text(
                    "UPDATE mkt_coupon_grants SET "
                    "valid_from = COALESCE(valid_from, (SELECT valid_from FROM mkt_coupons WHERE mkt_coupons.id = mkt_coupon_grants.coupon_id)), "
                    "valid_to = COALESCE(valid_to, (SELECT valid_to FROM mkt_coupons WHERE mkt_coupons.id = mkt_coupon_grants.coupon_id)), "
                    "claim_at = COALESCE(claim_at, grant_at) "
                    "WHERE valid_from IS NULL OR valid_to IS NULL OR claim_at IS NULL"
                )
            )

        if insp_conn.has_table("wx_landing_pages"):
            cols = {c["name"] for c in insp_conn.get_columns("wx_landing_pages")}
            if "coupon_id" not in cols:
                conn.execute(text("ALTER TABLE wx_landing_pages ADD COLUMN coupon_id INTEGER"))
            if "page_role" not in cols:
                conn.execute(text("ALTER TABLE wx_landing_pages ADD COLUMN page_role VARCHAR(16) DEFAULT 'claim'"))
            if "published_blocks_json" not in cols:
                conn.execute(text("ALTER TABLE wx_landing_pages ADD COLUMN published_blocks_json TEXT"))
            if "published_title" not in cols:
                conn.execute(text("ALTER TABLE wx_landing_pages ADD COLUMN published_title VARCHAR(128)"))
            if "published_coupon_id" not in cols:
                conn.execute(text("ALTER TABLE wx_landing_pages ADD COLUMN published_coupon_id INTEGER"))
            conn.execute(
                text(
                    "UPDATE wx_landing_pages SET "
                    "published_blocks_json = COALESCE(published_blocks_json, blocks_json), "
                    "published_title = COALESCE(published_title, title), "
                    "published_coupon_id = COALESCE(published_coupon_id, coupon_id) "
                    "WHERE status = 'published'"
                )
            )
        if insp_conn.has_table("hotel_mkt_settings"):
            cols = {c["name"] for c in insp_conn.get_columns("hotel_mkt_settings")}
            if "points_json" not in cols:
                conn.execute(text("ALTER TABLE hotel_mkt_settings ADD COLUMN points_json TEXT"))
            if "member_landing_page_id" not in cols:
                conn.execute(text("ALTER TABLE hotel_mkt_settings ADD COLUMN member_landing_page_id INTEGER"))
            if "returning_landing_page_id" not in cols:
                conn.execute(text("ALTER TABLE hotel_mkt_settings ADD COLUMN returning_landing_page_id INTEGER"))


def _seed_localize_blocks(blocks: list) -> list:
    """落地页 block 内可见中文 → seed_text（EN 启动时用 en_strings 对照）。"""
    from seed.locale_pack import seed_text as st
    from seed.packs.en_strings import EN_STRINGS

    raw = json.loads(json.dumps(blocks, ensure_ascii=False))

    def _loc_str(s: str) -> str:
        if not s or not isinstance(s, str):
            return s
        en = EN_STRINGS.get(s)
        return st(s, en) if en else st(s)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if isinstance(v, str) and k in (
                    "badge",
                    "title",
                    "subtitle",
                    "label",
                    "placeholder",
                    "text",
                ):
                    node[k] = _loc_str(v)
                elif isinstance(v, list) and k == "tabs":
                    for tab in v:
                        if isinstance(tab, dict) and isinstance(tab.get("label"), str):
                            tab["label"] = _loc_str(tab["label"])
                else:
                    walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(raw)
    return raw


def seed_mkt_demo(db: Session, hotel_id: int = 1) -> dict:
    from seed.locale_pack import seed_text as st

    created = {
        "templates": 0,
        "coupons": 0,
        "pages": 0,
        "campaigns": 0,
        "levels": 0,
        "plans": 0,
        "automations": 0,
    }

    from seed.packs.en_strings import EN_STRINGS

    for t in SYSTEM_TEMPLATES:
        name_zh = t["name"]
        name_en = EN_STRINGS.get(name_zh)
        loc_name = st(name_zh, name_en) if name_en else st(name_zh)
        loc_blocks = _seed_localize_blocks(t["blocks"])
        row = db.query(WxLandingTemplate).filter_by(template_key=t["template_key"]).first()
        if not row:
            db.add(
                WxLandingTemplate(
                    template_key=t["template_key"],
                    name=loc_name,
                    category=t["category"],
                    blocks_json=json.dumps(loc_blocks, ensure_ascii=False),
                    is_system=True,
                )
            )
            created["templates"] += 1
        elif row.is_system:
            row.name = loc_name
            row.blocks_json = json.dumps(loc_blocks, ensure_ascii=False)

    now = datetime.now()
    coupons_spec = [
        # batch_no, name_zh, name_en, coupon_type, face/rate/amt, threshold, status, extra
        (
            "COUPON-DEMO-70",
            "企微好友专享 · 房费7折券",
            "WeCom friends · 30% off room",
            "DISCOUNT",
            0.70,
            0,
            "active",
            {"discount_rate": 0.70},
        ),
        (
            "COUPON-DEMO-50",
            "满减券 · 满300减50",
            "Spend ¥300 save ¥50",
            "CASH_ROOM",
            50,
            300,
            "active",
            {"reduce_amount": 50, "scope_type": "ROOM_SPECIFIED"},
        ),
        (
            "COUPON-DEMO-NIGHT",
            "连住送夜券",
            "Stay-N-get-1 night voucher",
            "BENEFIT",
            2,
            0,
            "draft",
            {"benefit_key": "FREE_NIGHT", "benefit_value": "2"},
        ),
        (
            "COUPON-DEMO-CASH50",
            "无门槛通用立减¥50",
            "¥50 off · no minimum",
            "CASH_ALL",
            50,
            0,
            "active",
            {"reduce_amount": 50, "scope_type": "ALL"},
        ),
        (
            "COUPON-DEMO-REG30",
            "注册满30天 · 立减¥10",
            "30-day member · ¥10 off",
            "CASH_ALL",
            10,
            0,
            "active",
            {"reduce_amount": 10, "scope_type": "ALL"},
        ),
        (
            "COUPON-DEMO-REG100",
            "注册满100天 · 立减¥20",
            "100-day member · ¥20 off",
            "CASH_ALL",
            20,
            0,
            "active",
            {"reduce_amount": 20, "scope_type": "ALL"},
        ),
        (
            "COUPON-DEMO-CO7",
            "退房后复购 · 满300减80",
            "7 days post-stay · ¥80 off ¥300+",
            "CASH_ROOM",
            80,
            300,
            "active",
            {"reduce_amount": 80, "scope_type": "ROOM_SPECIFIED"},
        ),
    ]
    coupon_ids = {}
    for batch, name_zh, name_en, typ, face, thr, status, extra in coupons_spec:
        name = st(name_zh, name_en)
        row = db.query(MktCoupon).filter_by(batch_no=batch).first()
        if not row:
            from mkt.mkt_coupon_engine import build_face_text

            face_text = build_face_text(
                typ,
                reduce_amount=extra.get("reduce_amount", face if typ.startswith("CASH") else None),
                threshold=thr,
                discount_rate=extra.get("discount_rate"),
                benefit_key=extra.get("benefit_key"),
                benefit_value=extra.get("benefit_value"),
            )
            row = MktCoupon(
                hotel_id=hotel_id,
                batch_no=batch,
                name=name,
                type=typ,
                coupon_type=typ,
                face_value=face,
                reduce_amount=extra.get("reduce_amount"),
                discount_rate=extra.get("discount_rate"),
                benefit_key=extra.get("benefit_key"),
                benefit_value=extra.get("benefit_value"),
                face_text=face_text,
                threshold=thr,
                scope_type=extra.get("scope_type") or ("ALL" if typ != "CASH_ROOM" else "ROOM_SPECIFIED"),
                total_qty=2000,
                granted_qty=0,
                per_user_qty=1,
                validity_mode="FIXED",
                batch_valid_from=now - timedelta(days=1),
                batch_valid_to=now + timedelta(days=365),
                valid_from=now - timedelta(days=1),
                valid_to=now + timedelta(days=365),
                scope_json=json.dumps({"channels": ["direct", "wecom"], "room_types": "all"}, ensure_ascii=False),
                status=status,
            )
            db.add(row)
            db.flush()
            created["coupons"] += 1
        else:
            is_demo_batch = (batch or "").startswith("COUPON-DEMO-")
            if is_demo_batch or (row.name or "") in (name_zh, name_en) or row.name != name:
                row.name = name
            # 旧种子升级字段
            if not getattr(row, "coupon_type", None):
                row.coupon_type = typ
                row.type = typ
            from mkt.mkt_coupon_engine import build_face_text

            if is_demo_batch or not getattr(row, "face_text", None):
                row.face_text = build_face_text(
                    typ,
                    reduce_amount=extra.get("reduce_amount", face if str(typ).startswith("CASH") else None),
                    threshold=thr,
                    discount_rate=extra.get("discount_rate"),
                    benefit_key=extra.get("benefit_key"),
                    benefit_value=extra.get("benefit_value"),
                )
            if not getattr(row, "batch_valid_from", None) and row.valid_from:
                row.batch_valid_from = row.valid_from
                row.batch_valid_to = row.valid_to
            if not getattr(row, "validity_mode", None):
                row.validity_mode = "FIXED"
        coupon_ids[batch] = row.id

    # 自动发券规则种子（规则引擎条件 + 强制 H5 扫码）
    from mkt.mkt_rule_engine import ensure_h5_gate

    rule_specs = [
        (
            "新客欢迎礼 · 房价7折",
            "New guest welcome · 30% off room",
            "NEW_WECHAT_MEMBER",
            "event:NEW_WECHAT_MEMBER",
            ensure_h5_gate({"all": [{"field": "wecom_bound", "op": "eq", "value": True}]}),
            "COUPON-DEMO-70",
        ),
        (
            "注册满30天 · 立减¥10",
            "30-day member · ¥10 off",
            "RULE_ENGINE",
            "daily",
            ensure_h5_gate({"all": [{"field": "reg_days", "op": "eq", "value": 30}]}),
            "COUPON-DEMO-REG30",
        ),
        (
            "注册满100天 · 立减¥20",
            "100-day member · ¥20 off",
            "RULE_ENGINE",
            "daily",
            ensure_h5_gate({"all": [{"field": "reg_days", "op": "eq", "value": 100}]}),
            "COUPON-DEMO-REG100",
        ),
        (
            "退房后7天 · 满减券",
            "7 days post-stay voucher",
            "RULE_ENGINE",
            "daily",
            ensure_h5_gate({"all": [{"field": "days_since_checkout", "op": "eq", "value": 7}]}),
            "COUPON-DEMO-CO7",
        ),
    ]
    created.setdefault("triggers", 0)
    for rname_zh, rname_en, etype, when, cond, bno in rule_specs:
        rname = st(rname_zh, rname_en)
        bid = coupon_ids.get(bno)
        if not bid:
            continue
        exist = (
            db.query(MktCouponTrigger)
            .filter_by(property_id=hotel_id, batch_id=bid)
            .filter(MktCouponTrigger.name == rname)
            .first()
        )
        if not exist:
            exist = db.query(MktCouponTrigger).filter_by(property_id=hotel_id, batch_id=bid, event_type=etype).first()
        payload_json = json.dumps({"when": when, "condition": cond}, ensure_ascii=False)
        if exist:
            exist.name = rname
            exist.event_type = etype
            exist.event_params = payload_json
            exist.is_enabled = 1
            continue
        db.add(
            MktCouponTrigger(
                property_id=hotel_id,
                batch_id=bid,
                name=rname,
                event_type=etype,
                event_params=payload_json,
                is_enabled=1,
                granted_total=0,
            )
        )
        created["triggers"] += 1

    bind_coupon_id = coupon_ids.get("COUPON-DEMO-70")
    page = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="bind").first()
    blocks = _seed_localize_blocks(BIND_TEMPLATE_BLOCKS)
    for b in blocks:
        if b.get("type") == "coupon_card":
            b["props"]["coupon_id"] = bind_coupon_id
    if not page:
        page = WxLandingPage(
            hotel_id=hotel_id,
            page_key="bind",
            title=st("企微扫码领券", "WeCom scan to claim"),
            template_id="tpl_bind",
            page_role="claim",
            blocks_json=json.dumps(blocks, ensure_ascii=False),
            coupon_id=bind_coupon_id,
            status="published",
            published_url=f"/wecom/landing/bind?hotel_id={hotel_id}",
            updated_by="seed",
        )
        db.add(page)
        created["pages"] += 1
    else:
        page.blocks_json = json.dumps(blocks, ensure_ascii=False)
        page.coupon_id = bind_coupon_id
        if not getattr(page, "page_role", None):
            page.page_role = "claim"
        if page.status != "published":
            page.status = "published"
            page.published_url = f"/wecom/landing/bind?hotel_id={hotel_id}"

    member_page = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="member").first()
    member_blocks = _seed_localize_blocks(MEMBER_CENTER_BLOCKS)
    if not member_page:
        member_page = WxLandingPage(
            hotel_id=hotel_id,
            page_key="member",
            title=st("企微会员中心", "WeCom member center"),
            template_id="tpl_member_center",
            page_role="member",
            blocks_json=json.dumps(member_blocks, ensure_ascii=False),
            coupon_id=None,
            status="published",
            published_url=f"/wecom/landing/member?hotel_id={hotel_id}",
            updated_by="seed",
        )
        db.add(member_page)
        db.flush()
        created["pages"] += 1
    else:
        member_page.page_role = "member"
        member_page.blocks_json = json.dumps(member_blocks, ensure_ascii=False)
        if member_page.status != "published":
            member_page.status = "published"
            member_page.published_url = f"/wecom/landing/member?hotel_id={hotel_id}"

    returning_page = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="returning").first()
    returning_blocks = _seed_localize_blocks(RETURNING_WELCOME_BLOCKS)
    if not returning_page:
        returning_page = WxLandingPage(
            hotel_id=hotel_id,
            page_key="returning",
            title=st("老客回访", "Returning guest welcome"),
            template_id="tpl_returning",
            page_role="returning",
            blocks_json=json.dumps(returning_blocks, ensure_ascii=False),
            coupon_id=None,
            status="published",
            published_url=f"/wecom/landing/returning?hotel_id={hotel_id}",
            updated_by="seed",
        )
        db.add(returning_page)
        db.flush()
        created["pages"] += 1
    else:
        returning_page.page_role = "returning"
        returning_page.blocks_json = json.dumps(returning_blocks, ensure_ascii=False)
        if returning_page.status != "published":
            returning_page.status = "published"
            returning_page.published_url = f"/wecom/landing/returning?hotel_id={hotel_id}"

    def _ensure_published_snapshot(p: WxLandingPage | None) -> None:
        if not p:
            return
        if not getattr(p, "published_blocks_json", None):
            p.published_blocks_json = p.blocks_json
        if not getattr(p, "published_title", None):
            p.published_title = p.title
        if getattr(p, "published_coupon_id", None) is None and p.coupon_id is not None:
            p.published_coupon_id = p.coupon_id
        # 种子页保持线上快照与草稿一致，避免环境草稿/线上脱节
        if (p.updated_by or "") == "seed" or p.page_key in ("bind", "member", "returning"):
            p.published_blocks_json = p.blocks_json
            p.published_title = p.title
            p.published_coupon_id = p.coupon_id

    _ensure_published_snapshot(page)
    _ensure_published_snapshot(member_page)
    _ensure_published_snapshot(returning_page)

    def _ensure_seed_campaign(
        *,
        name_zh: str,
        name_en: str,
        type_: str,
        status: str,
        template_id: str,
        start_at,
        end_at,
        config: dict,
        approved: bool = False,
    ) -> None:
        nonlocal created
        name = st(name_zh, name_en)
        row = db.query(MktCampaign).filter_by(hotel_id=hotel_id, template_id=template_id, created_by="seed").first()
        if not row:
            row = (
                db.query(MktCampaign)
                .filter(
                    MktCampaign.hotel_id == hotel_id,
                    MktCampaign.name.in_([name_zh, name_en, name]),
                )
                .first()
            )
        if not row:
            db.add(
                MktCampaign(
                    hotel_id=hotel_id,
                    name=name,
                    type=type_,
                    status=status,
                    start_at=start_at,
                    end_at=end_at,
                    template_id=template_id,
                    config_json=json.dumps(config, ensure_ascii=False),
                    created_by="seed",
                    approved_by="seed" if approved else None,
                )
            )
            created["campaigns"] += 1
            return
        # 已有种子行：按当前 SEED_LOCALE 对齐活动名（避免 EN 库残留中文名）
        if (row.created_by or "") == "seed" and row.name != name:
            row.name = name

    _ensure_seed_campaign(
        name_zh="国庆连住7折",
        name_en="National Day Stay 30% Off",
        type_="holiday",
        status="running",
        template_id="holiday",
        start_at=now - timedelta(days=2),
        end_at=now + timedelta(days=20),
        config={
            "coupon_ids": [bind_coupon_id],
            "landing_page_key": "bind",
            "channels": ["wecom", "landing_page"],
            "segment": "all",
        },
        approved=True,
    )
    _ensure_seed_campaign(
        name_zh="周末早鸟价",
        name_en="Weekend Early Bird",
        type_="weekend",
        status="draft",
        template_id="weekend",
        start_at=now + timedelta(days=7),
        end_at=now + timedelta(days=37),
        config={"coupon_ids": [], "channels": ["wecom"]},
    )

    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    default_points = {
        "spend_per_point": 1,  # 1 元 = 1 积分
        "checkin_bonus": 10,
        "review_bonus": 20,
        "birthday_multiplier": 2.0,
        "redeem_points_per_yuan": 100,  # 100 积分抵 1 元
        "expire_months": 12,
        "rule_note": st(
            "积分仅限本店企微 H5 私域使用，与 PMS 全局会员积分无关。",
            "Points for this property's WeCom H5 owned audience only; not global PMS member points.",
        ),
    }
    if not settings:
        settings = HotelMktSettings(
            hotel_id=hotel_id,
            default_receiver_userid="WangWeiWei",
            welcome_text="欢迎添加专属管家，点击卡片填写手机号领取房费优惠券。",
            welcome_landing_page_id=page.id if page.id else None,
            member_landing_page_id=member_page.id if member_page.id else None,
            returning_landing_page_id=returning_page.id if returning_page.id else None,
            points_json=json.dumps(default_points, ensure_ascii=False),
        )
        db.add(settings)
    else:
        if not getattr(settings, "points_json", None):
            settings.points_json = json.dumps(default_points, ensure_ascii=False)
        if not settings.welcome_landing_page_id and page and page.id:
            settings.welcome_landing_page_id = page.id
        if not getattr(settings, "member_landing_page_id", None) and member_page and member_page.id:
            settings.member_landing_page_id = member_page.id
        if not getattr(settings, "returning_landing_page_id", None) and returning_page and returning_page.id:
            settings.returning_landing_page_id = returning_page.id

    levels_spec = [
        ("silver", "银卡", "nights", 3, "nights", 1, 10, ["房费 98 折", "延迟退房 1h"]),
        ("gold", "金卡", "nights", 8, "nights", 3, 20, ["房费 95 折", "免费早餐", "延迟退房 2h"]),
        ("platinum", "白金卡", "amount", 20000, "amount", 8000, 30, ["房费 9 折", "升房券", "生日礼包"]),
        ("diamond", "钻石卡", "stored", 10000, "nights", 5, 40, ["房费 88 折", "专属管家", "免费升房"]),
    ]
    _level_name_en = {
        "银卡": "Silver",
        "金卡": "Gold",
        "白金卡": "Platinum",
        "钻石卡": "Diamond",
    }
    for code, name, ut, uv, rt, rv, sort, benefits in levels_spec:
        if db.query(MktMemberLevel).filter_by(hotel_id=hotel_id, level_code=code).first():
            continue
        db.add(
            MktMemberLevel(
                hotel_id=hotel_id,
                level_code=code,
                level_name=st(name, _level_name_en.get(name, name)),
                upgrade_type=ut,
                upgrade_value=uv,
                retention_type=rt,
                retention_value=rv,
                benefits_json=json.dumps(benefits, ensure_ascii=False),
                sort_order=sort,
                is_active=True,
            )
        )
        created["levels"] += 1

    plans_spec = [(1000, 100, "amount", 1), (3000, 400, "amount", 2), (5000, 800, "amount", 3)]
    for recharge, bonus, btype, sort in plans_spec:
        exists = db.query(MktStoredValuePlan).filter_by(hotel_id=hotel_id, recharge_amt=recharge).first()
        if exists:
            continue
        db.add(
            MktStoredValuePlan(
                hotel_id=hotel_id,
                recharge_amt=recharge,
                bonus_amt=bonus,
                bonus_type=btype,
                is_active=True,
                sort_order=sort,
            )
        )
        created["plans"] += 1

    autos = [
        (
            "生日关怀发券",
            "birthday",
            {"days_before": 0},
            "send_coupon",
            {"coupon_batch_hint": "COUPON-DEMO-70", "msg": "生日快乐，专属礼券已到账"},
            365,
        ),
        (
            "入住前 3 天提醒",
            "checkin_pre",
            {"days_before": 3},
            "send_msg",
            {"msg": "您的入住日临近，可提前选房型或联系专属管家"},
            14,
        ),
        (
            "退房后 7 天复购唤起",
            "stay_post",
            {"days_after": 7},
            "send_coupon",
            {"coupon_batch_hint": "COUPON-DEMO-50", "msg": "欢迎再次入住，送您一张满减券"},
            30,
        ),
    ]
    for name, ttype, tj, atype, aj, cap in autos:
        if db.query(MktAutomation).filter_by(hotel_id=hotel_id, name=name).first():
            continue
        db.add(
            MktAutomation(
                hotel_id=hotel_id,
                name=name,
                trigger_type=ttype,
                trigger_json=json.dumps(tj, ensure_ascii=False),
                action_type=atype,
                action_json=json.dumps(aj, ensure_ascii=False),
                frequency_cap_days=cap,
                is_enabled=True,
            )
        )
        created["automations"] += 1

    # 私域 H5 会员钱包：仅企微建联客；并清掉未建联脏钱包
    created.setdefault("wallets", 0)
    created.setdefault("wallets_purged", 0)

    wecom_gids = {int(r[0]) for r in db.query(GuestIdentity.guest_id).filter(GuestIdentity.source == "wecom").all()}
    # 清理：未建联却有钱包（与「非私域客户」口径冲突）
    for w in db.query(MktGuestWallet).filter_by(hotel_id=hotel_id).all():
        if int(w.guest_id) not in wecom_gids:
            db.delete(w)
            created["wallets_purged"] += 1

    vip_map = {"platinum": "platinum", "diamond": "diamond", "gold": "gold", "silver": "silver"}
    demo_specs = [
        ("gold", 2680, 9, 18600),
        ("silver", 860, 4, 4200),
        ("platinum", 5200, 14, 28600),
        ("gold", 1920, 7, 11200),
        ("diamond", 9800, 22, 52000),
        ("silver", 420, 2, 1800),
    ]
    wecom_guests = (
        db.query(Guest).filter(Guest.id.in_(wecom_gids) if wecom_gids else False).order_by(Guest.id.asc()).all()
        if wecom_gids
        else []
    )
    for i, g in enumerate(wecom_guests):
        if db.query(MktGuestWallet).filter_by(hotel_id=hotel_id, guest_id=g.id).first():
            continue
        code, pts, nights, spend = demo_specs[i % len(demo_specs)]
        gvip = (g.vip_level or "").strip().lower()
        if gvip in vip_map:
            code = vip_map[gvip]
        db.add(
            MktGuestWallet(
                hotel_id=hotel_id,
                guest_id=g.id,
                level_code=code,
                points_balance=pts,
                stored_balance=0,
                nights_ytd=nights,
                spend_ytd=spend,
            )
        )
        created["wallets"] += 1

    db.commit()
    return created
