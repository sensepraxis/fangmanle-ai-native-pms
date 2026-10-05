# SPDX-License-Identifier: Apache-2.0
"""mkt.member subdomain routes."""

from __future__ import annotations

from routers.mkt._common import APIRouter, Depends, Optional, Query, Session, get_db, hotel_scope, ok

router = APIRouter(tags=["mkt"])


@router.get("/mkt/customers")
def mkt_customers(
    hotel_id: int = Depends(hotel_scope),
    tag: Optional[str] = Query(None),
    h5_only: int = Query(0),
    db: Session = Depends(get_db),
):
    from application.mkt import list_mkt_customers

    return ok(list_mkt_customers(db, hotel_id, tag=tag, h5_only=bool(h5_only)))


@router.get("/mkt/customers/{guest_id}")
def mkt_customer_detail(guest_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import get_mkt_customer

    return ok(get_mkt_customer(db, hotel_id, guest_id))


@router.patch("/mkt/customers/{guest_id}/note")
def mkt_customer_note(
    guest_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import add_customer_note

    return ok(add_customer_note(db, hotel_id, guest_id, payload or {}))


@router.get("/mkt/settings")
def mkt_settings_get(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import get_mkt_settings

    return ok(get_mkt_settings(db, hotel_id))


@router.put("/mkt/settings")
def mkt_settings_put(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import save_mkt_settings

    return ok(save_mkt_settings(db, hotel_id, payload or {}))


@router.get("/mkt/members")
def mkt_members_bundle(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import member_system_bundle

    return ok(member_system_bundle(db, hotel_id))


@router.post("/mkt/members/levels")
def mkt_member_level_upsert(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_level

    return ok(upsert_level(db, hotel_id, payload or {}))


@router.delete("/mkt/members/levels/{level_id}")
def mkt_member_level_del(level_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_level

    return ok(delete_level(db, hotel_id, level_id))


@router.post("/mkt/members/plans")
def mkt_stored_plan_upsert(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_recharge_tier

    return ok(upsert_recharge_tier(db, hotel_id, payload or {}))


@router.delete("/mkt/members/plans/{plan_id}")
def mkt_stored_plan_del(plan_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_recharge_tier

    return ok(delete_recharge_tier(db, hotel_id, plan_id))


# ---------- 会员体系权威 API（/api/mkt/member/...）----------


@router.get("/mkt/member/levels")
def mkt_member_levels(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_levels

    return ok(list_levels(db, hotel_id))


@router.put("/mkt/member/levels/{code}")
def mkt_member_level_put(code: str, payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_level

    body = dict(payload or {})
    body["level_code"] = code
    return ok(upsert_level(db, hotel_id, body))


@router.get("/mkt/member/benefits")
def mkt_member_benefits(
    level_code: str | None = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import get_benefits

    return ok(get_benefits(db, hotel_id, level_code))


@router.put("/mkt/member/benefits")
def mkt_member_benefits_put(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import put_benefits

    return ok(put_benefits(db, hotel_id, payload or {}))


@router.get("/mkt/member/level-rule")
def mkt_member_level_rule(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import get_level_rule

    return ok(get_level_rule(db, hotel_id))


@router.put("/mkt/member/level-rule")
def mkt_member_level_rule_put(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import save_level_rule

    return ok(save_level_rule(db, hotel_id, payload or {}))


@router.get("/mkt/member/recharge-tiers")
def mkt_member_recharge_tiers(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_recharge_tiers

    return ok(list_recharge_tiers(db, hotel_id))


@router.put("/mkt/member/recharge-tiers/{tier_id}")
def mkt_member_recharge_tier_put(
    tier_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import upsert_recharge_tier

    body = dict(payload or {})
    body["id"] = tier_id
    return ok(upsert_recharge_tier(db, hotel_id, body))


@router.post("/mkt/member/recharge-tiers")
def mkt_member_recharge_tier_post(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_recharge_tier

    return ok(upsert_recharge_tier(db, hotel_id, payload or {}))


@router.delete("/mkt/member/recharge-tiers/{tier_id}")
def mkt_member_recharge_tier_del(tier_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_recharge_tier

    return ok(delete_recharge_tier(db, hotel_id, tier_id))


@router.get("/mkt/member/point-rule")
def mkt_member_point_rule(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import get_point_rule

    return ok(get_point_rule(db, hotel_id))


@router.put("/mkt/member/point-rule")
def mkt_member_point_rule_put(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import save_point_rule

    return ok(save_point_rule(db, hotel_id, payload or {}))


@router.post("/mkt/member/point/preview")
def mkt_member_point_preview(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import preview_points

    return ok(preview_points(db, hotel_id, payload or {}))


@router.get("/mkt/automations")
def mkt_automations_list(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_automations

    return ok(list_automations(db, hotel_id))


@router.post("/mkt/automations")
def mkt_automations_upsert(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_automation

    return ok(upsert_automation(db, hotel_id, payload or {}))


@router.patch("/mkt/automations/{auto_id}/enabled")
def mkt_automations_enabled(
    auto_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import set_automation_enabled

    return ok(set_automation_enabled(db, hotel_id, auto_id, bool((payload or {}).get("is_enabled"))))


@router.post("/mkt/automations/{auto_id}/preview")
def mkt_automations_preview(auto_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import preview_automation

    return ok(preview_automation(db, hotel_id, auto_id))


@router.delete("/mkt/automations/{auto_id}")
def mkt_automations_del(auto_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_automation

    return ok(delete_automation(db, hotel_id, auto_id))
