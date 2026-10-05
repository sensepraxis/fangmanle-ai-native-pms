# SPDX-License-Identifier: Apache-2.0
"""客人券包 Wallet：grant_id 引用 + source 归一 + 多渠道数据。

source 归一 helper 已抽到 `mkt.wallet_norm`；本文件保留 schema 保活、回填与种子函数。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from infra.branding import LEGACY_WALLET_SOURCES, NATIVE_WALLET_SOURCE
from mkt.wallet_norm import WALLET_SOURCE_LABEL, normalize_wallet_source
from models import Guest, GuestCoupon, MktCouponGrant


def _add_col_if_missing(conn, insp, table: str, col: str, ddl: str) -> None:
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def migrate_wallet_source_brand_neutral(engine) -> int:
    """把历史品牌绑定的钱包源码迁到产品中立码 ``native_mkt``。

    SQL 对 PostgreSQL / SQLite 通用（标准 UPDATE … WHERE），无方言分支。
    返回受影响行数（尽力估算；部分驱动不返回 rowcount 时为 -1）。
    """
    insp = inspect(engine)
    if not insp.has_table("guest_coupons"):
        return 0
    total = 0
    with engine.begin() as conn:
        for old in sorted(LEGACY_WALLET_SOURCES):
            res = conn.execute(
                text("UPDATE guest_coupons SET source = :new WHERE source = :old"),
                {"new": NATIVE_WALLET_SOURCE, "old": old},
            )
            try:
                total += int(res.rowcount or 0)
            except Exception:
                total = -1
    return total


def ensure_coupon_wallet_schema(engine) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        insp_conn = inspect(conn)
        _add_col_if_missing(conn, insp, "guest_coupons", "grant_id", "grant_id INTEGER")
        # 去掉历史遗留的 (guest_id, source, coupon_type) 唯一约束，允许同一来源多张券。
        # PostgreSQL 下直接幂等删除同名唯一索引 / 唯一约束即可，不再依赖 SQLite 的
        # sqlite_master 自省与「整表重建」逻辑（PRAGMA / INSERT OR IGNORE / RENAME 均为 SQLite 专有）。
        if insp_conn.has_table("guest_coupons"):
            for name in (
                "uq_guest_coupon_source_type",
                "ix_guest_coupons_guest_id_source_coupon_type",
            ):
                try:
                    conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
                except Exception:
                    pass
            try:
                conn.execute(text("ALTER TABLE guest_coupons DROP CONSTRAINT IF EXISTS uq_guest_coupon_source_type"))
            except Exception:
                pass
    # 数据迁移：fangmanle_mkt → native_mkt（PG / SQLite 同一条 SQL）
    migrate_wallet_source_brand_neutral(engine)


def backfill_coupon_wallet(db: Session, hotel_id: int = 1) -> dict:
    """把已有 GuestCoupon 挂上 grant_id，并归一 source。

    为避开旧唯一约束冲突：先尽量用「mkt_g{{grant_id}}」这类已唯一的 source，
    表重建后才统一写成 fangmanle_mkt。
    """
    linked = 0
    normalized = 0
    rows = db.query(GuestCoupon).filter_by(hotel_id=hotel_id).all()
    for r in rows:
        grant = None
        if getattr(r, "grant_id", None):
            grant = db.get(MktCouponGrant, r.grant_id)
        if not grant and r.code:
            grant = db.query(MktCouponGrant).filter_by(code=r.code).first()
        if not grant and str(r.source or "").startswith("mkt_g"):
            try:
                gid = int(str(r.source).replace("mkt_g", ""))
                grant = db.get(MktCouponGrant, gid)
            except Exception:
                grant = None

        if grant:
            r.grant_id = grant.id
            # 每张券独立 source，避免 UNIQUE(guest_id,source,coupon_type) 冲突
            new_src = f"mkt_g{grant.id}"
            if r.source != new_src and r.source != NATIVE_WALLET_SOURCE and r.source not in LEGACY_WALLET_SOURCES:
                r.source = new_src
                normalized += 1
            elif r.source == NATIVE_WALLET_SOURCE or r.source in LEGACY_WALLET_SOURCES:
                # 若已有多张本店券会撞约束，改回按 grant 区分
                clash = (
                    db.query(GuestCoupon)
                    .filter(
                        GuestCoupon.guest_id == r.guest_id,
                        GuestCoupon.source.in_([NATIVE_WALLET_SOURCE, *LEGACY_WALLET_SOURCES]),
                        GuestCoupon.coupon_type == r.coupon_type,
                        GuestCoupon.id != r.id,
                    )
                    .first()
                )
                if clash:
                    r.source = new_src
                    normalized += 1
            linked += 1
            from mkt.mkt_coupon_engine import normalize_instance_status

            if normalize_instance_status(grant.status) == "USED" and r.redeem_status != "redeemed":
                r.redeem_status = "redeemed"
                r.status = "used"
                r.used_at = grant.used_at or r.used_at or datetime.now()
        else:
            ns = normalize_wallet_source(r.source)
            # wecom_scan → wecom 可能撞约束，仅当不冲突时改
            if ns != r.source:
                clash = (
                    db.query(GuestCoupon)
                    .filter(
                        GuestCoupon.guest_id == r.guest_id,
                        GuestCoupon.source == ns,
                        GuestCoupon.coupon_type == r.coupon_type,
                        GuestCoupon.id != r.id,
                    )
                    .first()
                )
                if not clash:
                    r.source = ns
                    normalized += 1

    db.commit()
    # 表已无旧约束时，再把 mkt_g* 归一为 native_mkt（产品中立码）
    try:
        for r in db.query(GuestCoupon).filter(GuestCoupon.source.like("mkt_g%")).all():
            r.source = NATIVE_WALLET_SOURCE
        db.commit()
    except Exception:
        db.rollback()

    return {"normalized": normalized, "linked_grant": linked, "total": len(rows)}


def seed_multichannel_wallet_demo(db: Session, hotel_id: int = 1) -> dict:
    """给董文(#228)补美团/抖音券，便于 360 看到多渠道券包。"""
    guest = db.get(Guest, 228)
    if not guest:
        guest = db.query(Guest).filter_by(name="董文").first()
    if not guest:
        return {"ok": False, "reason": "guest_228_missing"}

    now = datetime.now()
    created = 0
    demos = [
        {
            "code": "MT-DEMO-228-Y100",
            "name": "美团·到店立减¥100",
            "source": "meituan",
            "channel": "美团",
            "coupon_type": "reduction",
            "discount_rate": 1.0,
            "note": "：外渠道券，仅券包展示；核销走美团（demo 标记不可在本店直接核）",
            "can_local": False,
        },
        {
            "code": "DY-DEMO-228-BF",
            "name": "抖音·免费双早券",
            "source": "douyin",
            "channel": "抖音",
            "coupon_type": "benefit",
            "discount_rate": 1.0,
            "note": "：内容平台团购权益",
            "can_local": False,
        },
    ]
    for d in demos:
        if db.query(GuestCoupon).filter_by(code=d["code"]).first():
            continue
        db.add(
            GuestCoupon(
                hotel_id=hotel_id,
                guest_id=guest.id,
                grant_id=None,
                code=d["code"],
                name=d["name"],
                recipient_name=guest.name,
                channel=d["channel"],
                coupon_type=d["coupon_type"],
                discount_rate=d["discount_rate"],
                source=d["source"],
                status="active",
                redeem_status="unused",
                valid_from=now - timedelta(days=3),
                valid_until=now + timedelta(days=60),
                note=d["note"],
            )
        )
        created += 1

    # 确保本店发放的投影都挂上 grant_id
    for g in db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, guest_id=guest.id).all():
        gc = db.query(GuestCoupon).filter_by(code=g.code).first()
        if gc and not gc.grant_id:
            gc.grant_id = g.id
            gc.source = NATIVE_WALLET_SOURCE

    db.commit()
    return {"ok": True, "guest_id": guest.id, "created": created}


def ensure_coupon_wallet(engine, db: Session, hotel_id: int = 1) -> dict:
    ensure_coupon_wallet_schema(engine)
    bf = backfill_coupon_wallet(db, hotel_id=hotel_id)
    seed = seed_multichannel_wallet_demo(db, hotel_id=hotel_id)
    return {"backfill": bf, "seed": seed}
