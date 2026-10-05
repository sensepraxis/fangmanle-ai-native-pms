# SPDX-License-Identifier: Apache-2.0
"""mkt.auto_rules subdomain routes."""

from __future__ import annotations

from routers.mkt._common import APIRouter, Depends, HTTPException, Session, get_db, hotel_scope, ok

router = APIRouter(tags=["mkt"])


@router.get("/mkt/auto-grant/fields")
def mkt_auto_grant_fields():
    from application.mkt import list_auto_grant_fields

    return ok(list_auto_grant_fields())


@router.post("/mkt/auto-grant/preview")
def mkt_auto_grant_preview(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import preview_auto_grant_audience

    return ok(preview_auto_grant_audience(db, hotel_id, payload or {}))


@router.get("/mkt/auto-grant/templates")
def mkt_auto_grant_templates():
    from application.mkt import list_auto_grant_templates

    return ok(list_auto_grant_templates())


@router.get("/mkt/auto-grant/rules")
def mkt_auto_grant_list(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_auto_grant_rules

    return ok(list_auto_grant_rules(db, hotel_id))


@router.post("/mkt/auto-grant/rules")
def mkt_auto_grant_upsert(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_auto_grant_rule

    return ok(upsert_auto_grant_rule(db, hotel_id, payload or {}))


@router.patch("/mkt/auto-grant/rules/{rule_id}/enabled")
def mkt_auto_grant_enabled(
    rule_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import set_auto_grant_rule_enabled

    return ok(set_auto_grant_rule_enabled(db, hotel_id, rule_id, bool((payload or {}).get("is_enabled"))))


@router.delete("/mkt/auto-grant/rules/{rule_id}")
def mkt_auto_grant_del(rule_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_auto_grant_rule

    return ok(delete_auto_grant_rule(db, hotel_id, rule_id))


@router.post("/mkt/auto-grant/rules/scan")
def mkt_auto_grant_scan(payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """立即执行日扫（REG_DAYS / CHECKOUT_DAYS）。payload.rule_id 可选。"""
    from datetime import date as date_cls

    from application.mkt import run_auto_grant_scan

    payload = payload or {}
    today = None
    if payload.get("today"):
        try:
            today = date_cls.fromisoformat(str(payload["today"])[:10])
        except Exception:
            today = None
    return ok(
        run_auto_grant_scan(
            db,
            hotel_id,
            rule_id=int(payload["rule_id"]) if payload.get("rule_id") else None,
            today=today,
        )
    )


@router.post("/mkt/auto-grant/rules/{rule_id}/try")
def mkt_auto_grant_try(
    rule_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import try_auto_grant_for_guest

    gid = int((payload or {}).get("guest_id") or (payload or {}).get("customer_id") or 0)
    if not gid:
        raise HTTPException(400, "请指定 guest_id")
    return ok(try_auto_grant_for_guest(db, hotel_id, rule_id, gid))


# ---------- 自动发券规则四表（权威稿）----------


@router.get("/mkt/auto-rules/kpi")
def mkt_auto_rules_kpi(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import kpi_summary

    return ok(kpi_summary(db, hotel_id))


@router.get("/mkt/auto-rules/fields")
def mkt_auto_rules_fields():
    from application.mkt import list_auto_rules_fields

    return ok(list_auto_rules_fields())


@router.get("/mkt/auto-rules/events")
def mkt_auto_rules_events():
    from application.mkt import list_event_types

    return ok(list_event_types())


@router.get("/mkt/auto-rules")
def mkt_auto_rules_list(
    status: str = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import list_auto_rules

    return ok(list_auto_rules(db, hotel_id, status=status))


@router.post("/mkt/auto-rules")
def mkt_auto_rules_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_auto_rule

    body = dict(payload or {})
    body.pop("id", None)
    return ok(upsert_auto_rule(db, hotel_id, body))


@router.get("/mkt/auto-rules/{rule_id}")
def mkt_auto_rules_get(rule_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import get_auto_rule

    return ok(get_auto_rule(db, hotel_id, rule_id))


@router.put("/mkt/auto-rules/{rule_id}")
def mkt_auto_rules_put(
    rule_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import upsert_auto_rule

    body = dict(payload or {})
    body["id"] = rule_id
    return ok(upsert_auto_rule(db, hotel_id, body))


@router.post("/mkt/auto-rules/{rule_id}/enable")
def mkt_auto_rules_enable(rule_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import set_status

    return ok(set_status(db, hotel_id, rule_id, "active"))


@router.post("/mkt/auto-rules/{rule_id}/pause")
def mkt_auto_rules_pause(rule_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import set_status

    return ok(set_status(db, hotel_id, rule_id, "paused"))


@router.delete("/mkt/auto-rules/{rule_id}")
def mkt_auto_rules_delete(rule_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import delete_auto_rule

    return ok(delete_auto_rule(db, hotel_id, rule_id))


@router.post("/mkt/auto-rules/preview")
def mkt_auto_rules_preview_draft(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """草稿态实时预览（无 rule id）。"""
    from application.mkt import preview_estimate

    return ok(preview_estimate(db, hotel_id, payload or {}))


@router.post("/mkt/auto-rules/{rule_id}/preview")
def mkt_auto_rules_preview(
    rule_id: int, payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)
):
    from application.mkt import preview_estimate

    body = dict(payload or {})
    body["rule_id"] = rule_id
    return ok(preview_estimate(db, hotel_id, body))


@router.post("/mkt/auto-rules/{rule_id}/dry-run")
def mkt_auto_rules_dry_run(
    rule_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import dry_run

    body = payload or {}
    ids = body.get("customer_ids") or body.get("oneids") or []
    if not ids and body.get("customer_id"):
        ids = [body["customer_id"]]
    if not ids and body.get("guest_id"):
        ids = [body["guest_id"]]
    return ok(dry_run(db, hotel_id, rule_id, ids))


@router.get("/mkt/auto-rules/{rule_id}/triggers")
def mkt_auto_rules_triggers(
    rule_id: int,
    matched: int = None,
    limit: int = 50,
    offset: int = 0,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import list_triggers

    return ok(list_triggers(db, hotel_id, rule_id, matched=matched, limit=limit, offset=offset))


@router.post("/mkt/auto-rules/scan")
def mkt_auto_rules_scan(payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import run_auto_rules_scan

    payload = payload or {}
    return ok(
        run_auto_rules_scan(
            db,
            hotel_id,
            rule_id=int(payload["rule_id"]) if payload.get("rule_id") else None,
        )
    )
