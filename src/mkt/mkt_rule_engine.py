# SPDX-License-Identifier: Apache-2.0
"""发券规则引擎：条件树求值 + 字段目录。

硬约束：所有规则最终都必须命中「H5 扫过码 / 企微建联」客人（h5_scanned=true）。
即使配置里漏写，求值器也会强制门禁。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import (
    Guest,
    GuestCoupon,
    GuestIdentity,
    MktCouponGrant,
    MktGuestWallet,
    Order,
    PmsCheckin,
    WecomBindTicket,
)

# ---------- 字段目录（产品可选条件）----------

FIELD_CATALOG = [
    {
        "key": "h5_scanned",
        "label": "曾在 H5/企微扫码建联",
        "type": "bool",
        "required": True,
        "ops": ["eq"],
        "hint": "硬约束：必须为是。含企微好友身份、H5 绑定票据、私域钱包或落地页领券。",
    },
    {
        "key": "wecom_bound",
        "label": "已绑定企微好友",
        "type": "bool",
        "required": False,
        "ops": ["eq"],
        "hint": "GuestIdentity.source=wecom",
    },
    {
        "key": "reg_days",
        "label": "注册天数",
        "type": "number",
        "required": False,
        "ops": ["eq", "gte", "lte", "gt", "lt"],
        "hint": "今天 − 客人档案创建日",
    },
    {
        "key": "days_since_checkout",
        "label": "距最近退房天数",
        "type": "number",
        "required": False,
        "ops": ["eq", "gte", "lte", "gt", "lt"],
        "hint": "优先实际退房日，否则订单离店日；无退房记录为 null",
    },
    {
        "key": "member_level",
        "label": "私域会员等级",
        "type": "enum",
        "required": False,
        "ops": ["eq", "in", "not_in"],
        "enum": ["silver", "gold", "platinum", "diamond"],
        "hint": "mkt_guest_wallets.level_code",
    },
    {
        "key": "has_private_wallet",
        "label": "已有私域会员钱包",
        "type": "bool",
        "required": False,
        "ops": ["eq"],
    },
]

OPS = ("eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in")

H5_GATE = {"field": "h5_scanned", "op": "eq", "value": True}


def list_field_catalog() -> list[dict]:
    return FIELD_CATALOG


# ---------- H5 扫码建联判定（权威）----------


def is_channel_bound(db: Session, hotel_id: int, guest_id: int) -> bool:
    """是否曾在私域通道（H5/IM）建联。

    命中任一即可：
    1. 当前 messaging vendor 的 GuestIdentity（及历史 wecom）
    2. 本店绑定票据 WecomBindTicket(status=bound, guest_id=)
    3. 本店私域钱包 MktGuestWallet
    4. 本店落地页渠道发券记录
    """
    from extensions.messaging.facade import identity_sources_for_reachability

    sources = identity_sources_for_reachability()
    if (
        db.query(GuestIdentity.id)
        .filter(GuestIdentity.guest_id == guest_id, GuestIdentity.source.in_(list(sources)))
        .first()
    ):
        return True
    if db.query(WecomBindTicket.id).filter_by(hotel_id=hotel_id, guest_id=guest_id, status="bound").first():
        return True
    if db.query(MktGuestWallet.id).filter_by(hotel_id=hotel_id, guest_id=guest_id).first():
        return True
    if (
        db.query(MktCouponGrant.id)
        .filter_by(hotel_id=hotel_id, guest_id=guest_id, grant_channel="landing_page")
        .first()
    ):
        return True
    if (
        db.query(GuestCoupon.id)
        .filter(
            GuestCoupon.hotel_id == hotel_id,
            GuestCoupon.guest_id == guest_id,
            GuestCoupon.channel.in_(("企业微信", "landing_page", "私域", "LINE", "WhatsApp")),
        )
        .first()
    ):
        return True
    return False


def is_h5_scanned(db: Session, hotel_id: int, guest_id: int) -> bool:
    """兼容旧名 → ``is_channel_bound``。"""
    return is_channel_bound(db, hotel_id, guest_id)


def _reg_days(guest: Guest, today: date) -> Optional[int]:
    if not guest.created_at:
        return None
    d = guest.created_at.date() if isinstance(guest.created_at, datetime) else guest.created_at
    return (today - d).days


def _days_since_checkout(db: Session, hotel_id: int, guest_id: int, today: date) -> Optional[int]:
    latest: Optional[date] = None
    ci = (
        db.query(PmsCheckin)
        .filter(
            PmsCheckin.hotel_id == hotel_id,
            PmsCheckin.guest_id == guest_id,
            PmsCheckin.actual_checkout_at.isnot(None),
        )
        .order_by(PmsCheckin.actual_checkout_at.desc())
        .first()
    )
    if ci and ci.actual_checkout_at:
        latest = ci.actual_checkout_at.date()
    od = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.guest_id == guest_id,
            Order.status == "checked_out",
        )
        .order_by(Order.check_out.desc())
        .first()
    )
    if od and od.check_out:
        d = od.check_out if isinstance(od.check_out, date) else od.check_out
        if latest is None or d > latest:
            latest = d
    # 也查 order 关联的 checkin（guest 在 checkin 上）
    if latest is None:
        for row in (
            db.query(PmsCheckin)
            .filter(PmsCheckin.hotel_id == hotel_id, PmsCheckin.actual_checkout_at.isnot(None))
            .order_by(PmsCheckin.actual_checkout_at.desc())
            .limit(50)
            .all()
        ):
            if row.guest_id == guest_id and row.actual_checkout_at:
                latest = row.actual_checkout_at.date()
                break
            if row.order_id:
                o = db.get(Order, row.order_id)
                if o and o.guest_id == guest_id and row.actual_checkout_at:
                    latest = row.actual_checkout_at.date()
                    break
    if not latest:
        return None
    return (today - latest).days


def build_guest_context(
    db: Session,
    hotel_id: int,
    guest: Guest,
    *,
    today: Optional[date] = None,
) -> dict[str, Any]:
    today = today or date.today()
    gid = guest.id
    from extensions.messaging.facade import identity_source

    src = identity_source()
    bound = bool(db.query(GuestIdentity.id).filter_by(guest_id=gid, source=src).first())
    if not bound and src != "wecom":
        bound = bool(db.query(GuestIdentity.id).filter_by(guest_id=gid, source="wecom").first())
    wallet = db.query(MktGuestWallet).filter_by(hotel_id=hotel_id, guest_id=gid).first()
    h5 = is_channel_bound(db, hotel_id, gid)
    return {
        "guest_id": gid,
        "h5_scanned": h5,
        "wecom_bound": bound,
        "reg_days": _reg_days(guest, today),
        "days_since_checkout": _days_since_checkout(db, hotel_id, gid, today),
        "member_level": (wallet.level_code if wallet else None),
        "has_private_wallet": bool(wallet),
        "name": guest.name,
    }


# ---------- 条件树 ----------


def _atom(node: dict) -> bool:
    return isinstance(node, dict) and "field" in node and "op" in node


def ensure_h5_gate(condition: Optional[dict]) -> dict:
    """强制把 h5_scanned=true 注入到 all 根条件（不可去掉）。"""
    gate = dict(H5_GATE)
    if not condition:
        return {"all": [gate]}
    if not isinstance(condition, dict):
        return {"all": [gate]}

    def _strip_h5(node: Any) -> Any:
        if _atom(node):
            if node.get("field") == "h5_scanned":
                return None
            return node
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k in ("all", "any") and isinstance(v, list):
                    kids = []
                    for c in v:
                        sc = _strip_h5(c)
                        if sc is not None:
                            kids.append(sc)
                    out[k] = kids
                else:
                    out[k] = v
            return out
        return node

    cleaned = _strip_h5(condition) or {}
    if "all" in cleaned and isinstance(cleaned["all"], list):
        return {"all": [gate] + list(cleaned["all"])}
    if "any" in cleaned:
        # (h5) AND (原 any ...)
        return {"all": [gate, cleaned]}
    if _atom(cleaned):
        return {"all": [gate, cleaned]}
    return {"all": [gate]}


def condition_to_text(condition: Optional[dict]) -> str:
    """人读文案：不展示硬门禁 h5_scanned（产品侧默认成立）。"""
    condition = ensure_h5_gate(condition)

    def _atom_text(n: dict) -> Optional[str]:
        if not _atom(n):
            return None
        # 硬门禁不在列表里啰嗦展示
        if n.get("field") == "h5_scanned":
            return None
        lab = next((f["label"] for f in FIELD_CATALOG if f["key"] == n["field"]), n["field"])
        op = n.get("op") or "eq"
        val = n.get("value")
        if n["field"] == "member_level":
            level_cn = {
                "silver": "银卡",
                "gold": "金卡",
                "platinum": "铂金",
                "diamond": "钻石",
            }
            if isinstance(val, list):
                val = "、".join(level_cn.get(str(v), str(v)) for v in val)
            else:
                val = level_cn.get(str(val), val)
        if isinstance(val, bool):
            val = "是" if val else "否"
        op_cn = {
            "eq": "等于",
            "ne": "不等于",
            "gt": "大于",
            "gte": "大于等于",
            "lt": "小于",
            "lte": "小于等于",
            "in": "属于",
            "not_in": "不属于",
        }.get(op, op)
        return f"{lab}{op_cn}{val}"

    def _one(n: Any) -> str:
        if not isinstance(n, dict):
            return str(n)
        if "all" in n:
            parts = [t for t in (_one(x) for x in n["all"]) if t]
            return "，且 ".join(parts) if parts else "已加企微的客人"
        if "any" in n:
            parts = [t for t in (_one(x) for x in n["any"]) if t]
            return "(" + " 或 ".join(parts) + ")" if parts else ""
        t = _atom_text(n)
        return t or ""

    text = _one(condition).strip()
    return text or "已加企微的客人"


def _cmp(left: Any, op: str, right: Any) -> bool:
    if op not in OPS:
        return False
    if left is None and op not in ("eq", "ne"):
        return False
    if op == "eq":
        if isinstance(right, bool) or isinstance(left, bool):
            return bool(left) is bool(right) if right is not None else left is None
        return left == right
    if op == "ne":
        return left != right
    if op == "in":
        return left in (right or [])
    if op == "not_in":
        return left not in (right or [])
    try:
        lf, rf = float(left), float(right)
    except (TypeError, ValueError):
        return False
    if op == "gt":
        return lf > rf
    if op == "gte":
        return lf >= rf
    if op == "lt":
        return lf < rf
    if op == "lte":
        return lf <= rf
    return False


def eval_condition(condition: Optional[dict], ctx: dict) -> tuple[bool, list[str]]:
    """返回 (是否命中, 失败原因列表)。始终先过 H5 门禁。"""
    reasons: list[str] = []
    # 硬门禁
    if not ctx.get("h5_scanned"):
        return False, ["未在 H5/企微扫码建联（h5_scanned=false）"]

    tree = ensure_h5_gate(condition)

    def _eval(node: Any) -> bool:
        if not isinstance(node, dict):
            reasons.append("无效条件节点")
            return False
        if "all" in node:
            ok = True
            for c in node["all"] or []:
                if not _eval(c):
                    ok = False
            return ok
        if "any" in node:
            kids = node["any"] or []
            if not kids:
                return True
            for c in kids:
                if _eval(c):
                    return True
            reasons.append("或条件均未命中")
            return False
        if _atom(node):
            field = node["field"]
            op = node.get("op") or "eq"
            want = node.get("value")
            got = ctx.get(field)
            hit = _cmp(got, op, want)
            if not hit:
                reasons.append(f"{field} 实际={got} 不满足 {op} {want}")
            return hit
        reasons.append("未知条件结构")
        return False

    return _eval(tree), reasons


def legacy_to_condition(event_type: str, params: dict) -> dict:
    """旧事件枚举 → 条件树。"""
    et = (event_type or "").upper()
    params = params or {}
    extra: list[dict] = []
    if et == "REG_DAYS":
        n = int(params.get("reg_days") or 0)
        if n > 0:
            extra.append({"field": "reg_days", "op": "eq", "value": n})
    elif et == "CHECKOUT_DAYS":
        n = int(params.get("days_after_checkout") or 0)
        if n > 0:
            extra.append({"field": "days_since_checkout", "op": "eq", "value": n})
    elif et == "NEW_WECHAT_MEMBER":
        extra.append({"field": "wecom_bound", "op": "eq", "value": True})
    # 已有 condition 则合并
    if params.get("condition"):
        return ensure_h5_gate(params["condition"])
    return ensure_h5_gate({"all": extra} if extra else {"all": []})


def match_guests(
    db: Session,
    hotel_id: int,
    condition: dict,
    *,
    today: Optional[date] = None,
    limit_scan: int = 800,
    sample: int = 20,
) -> dict:
    """对门店相关客人求值，返回命中集合（仅 h5_scanned 会通过门禁）。"""
    from bootstrap.ensure_member_crm import _hotel_guest_ids

    today = today or date.today()
    condition = ensure_h5_gate(condition)
    gids = _hotel_guest_ids(db, hotel_id)[:limit_scan]
    # 补：有绑定票据/企微身份但可能不在 hotel guest 列表的，仍以 hotel list 为主
    matched: list[dict] = []
    scanned = 0
    for gid in gids:
        g = db.get(Guest, gid)
        if not g:
            continue
        scanned += 1
        ctx = build_guest_context(db, hotel_id, g, today=today)
        ok, _ = eval_condition(condition, ctx)
        if ok:
            matched.append(
                {
                    "guest_id": g.id,
                    "name": g.name,
                    "reg_days": ctx.get("reg_days"),
                    "days_since_checkout": ctx.get("days_since_checkout"),
                    "member_level": ctx.get("member_level"),
                    "wecom_bound": ctx.get("wecom_bound"),
                    "h5_scanned": True,
                }
            )
    return {
        "scanned": scanned,
        "matched": len(matched),
        "samples": matched[:sample],
        "guest_ids": [m["guest_id"] for m in matched],
        "condition_text": condition_to_text(condition),
    }
