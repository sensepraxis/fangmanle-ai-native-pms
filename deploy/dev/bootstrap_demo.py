# SPDX-License-Identifier: Apache-2.0
"""Bootstrap full demo DB for 8081 startup (CN / EN seed packs).

Env vars (set by deploy/dev/start.bat / start.sh):
    DATABASE_URL         e.g. sqlite:///C:\\tmp\\fml_demo_8081_zh.db
    SEED_LOCALE          zh-CN | en
    FML_DEFAULT_LOCALE   aligned with SEED_LOCALE (default UI language)
    SRC_DIR              repo src/ (optional; derived from this file by default)

Skips PG-only ensure_*_schema(engine); runs ORM seed + seed_*_demo only.
Matches legacy C:\\tmp\\bootstrap_admin.py behavior with bilingual seeds.
"""
from __future__ import annotations

import os
import os.path as op
import sys


def _repo_src() -> str:
    env = os.environ.get("SRC_DIR")
    if env:
        return env
    here = op.dirname(op.abspath(__file__))
    return op.normpath(op.join(here, "..", "..", "src"))


SRC_DIR = _repo_src()
sys.path.insert(0, SRC_DIR)

# Locale must be set before importing seed modules
SEED_LOCALE = os.environ.get("SEED_LOCALE") or os.environ.get("FML_DEFAULT_LOCALE") or "zh-CN"
os.environ["SEED_LOCALE"] = SEED_LOCALE
os.environ.setdefault("FML_DEFAULT_LOCALE", SEED_LOCALE)

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    # Fallback DB path by locale
    suffix = "en" if str(SEED_LOCALE).lower().startswith("en") else "zh"
    db_path = rf"C:\tmp\fml_demo_8081_{suffix}.db"
    DB_URL = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = DB_URL

# Parse sqlite URL path so we can delete the old DB file
DB_PATH = DB_URL.replace("sqlite:///", "").replace("sqlite://", "")

print("============================================")
print(f"Bootstrap demo · SEED_LOCALE={SEED_LOCALE}")
print(f"DB: {DB_PATH}")
print("============================================")

from database import SessionLocal, engine  # noqa: E402
from models import Base  # noqa: E402

# 1) Delete old DB (clean seed every start)
deleted_files = False
for ext in ["", "-wal", "-shm"]:
    p = DB_PATH + ext
    if op.exists(p):
        try:
            os.remove(p)
            deleted_files = True
        except OSError as exc:
            print(f"[1/2] skip delete {p}: {exc}")
            break
if deleted_files:
    print(f"[1/2] DB clean: {DB_PATH}")

Base.metadata.create_all(engine)
print("[1/2] tables created")

# Clear pack cache so SEED_LOCALE takes effect
from seed.locale_pack import clear_pack_cache, get_seed_locale  # noqa: E402

clear_pack_cache()
print(f"[1/2] seed locale resolved: {get_seed_locale()}")

# Align seed _t()/build_face_text with SEED_LOCALE (otherwise defaults to zh)
from infra.i18n import set_locale  # noqa: E402

set_locale(get_seed_locale())

from seed import seed  # noqa: E402

print("[1/2] seeding core demo data...")
seed(reset=True)

print("[1/2] enriching domain demos...")
_db = SessionLocal()
try:
    from bootstrap.ensure_rbac import bootstrap_rbac_all
    from bootstrap.migrations.alter_to_single_hotel import ensure_local_users
    from finance.ota_commission_service import ensure_ota_commission_seed
    from bootstrap.ensure_room_types import backfill_room_types

    rbac_info = bootstrap_rbac_all(engine, _db, reset_matrix=False)
    print(
        f'  RBAC: roles {",".join(rbac_info.get("roles") or [])} · '
        f'users {rbac_info.get("users", 0)}'
    )
    ensure_local_users(_db)
    ota_seed = ensure_ota_commission_seed(_db)
    print(f'  OTA commission: +{ota_seed.get("created", 0)} / upd {ota_seed.get("updated", 0)}')
    backfill_room_types(_db)

    from bootstrap.ensure_room_maintenance import seed_room_maintenance_demo
    from bootstrap.ensure_order_channels import ensure_order_channels
    from bootstrap.ensure_corp_agreements import ensure_corp_agreements

    rmaint = seed_room_maintenance_demo(_db, hotel_id=1)
    print(
        f'  Room maint: rooms {rmaint["rooms"]} · assets {rmaint["assets"]} · '
        f'maint +{rmaint["maintenance"]} · alerts +{rmaint["alerts"]}'
    )
    ensure_order_channels(_db)
    ensure_corp_agreements(_db)

    from bootstrap.ensure_ar_ap import bootstrap_ar_ap

    try:
        arap = bootstrap_ar_ap(_db, hotel_id=1)
        print(
            f'  AR/AP: pay-norm {arap.get("orders_payment_normalized", 0)} · '
            f'AR +{arap.get("ar_synced", 0)}'
        )
    except Exception as exc:
        print(f"  AR/AP skipped: {type(exc).__name__}: {str(exc)[:80]}")

    try:
        from bootstrap.migrations.alter_pms_core_plaintext import backfill_pms_core

        pms = backfill_pms_core(_db)
        print(
            f'  PMS core: orders {pms["orders_updated"]} · '
            f'checkins {pms["checkins_created"]}'
        )
    except Exception as exc:
        print(f"  PMS core skipped: {type(exc).__name__}: {str(exc)[:80]}")

    try:
        from bootstrap.seed_compact_floors import ensure_compact_demo_floors
        from seed import enrich_housekeeping_demo
        from models import Hotel as _Hotel

        compact = ensure_compact_demo_floors(_db, hotel_id=1, max_floors=2)
        if not compact.get("skipped"):
            hotels = _db.query(_Hotel).all()
            enrich_housekeeping_demo(_db, hotels)
            print(f'  Floors compact: left {compact.get("rooms_left")}')
    except Exception as exc:
        print(f"  Floors skipped: {type(exc).__name__}: {str(exc)[:80]}")

    from bootstrap.ensure_order_attribution import ensure_order_attribution
    from bootstrap.ensure_acquisition import ensure_acquisition_seed
    from bootstrap.ensure_webhook import ensure_webhook_bindings_seed
    from bootstrap.ensure_wecom import ensure_wecom_defaults
    from infra.map_config import ensure_map_defaults

    atr = ensure_order_attribution(_db)
    print(f'  Attribution: campaigns +{atr["campaigns_added"]}')
    acq = ensure_acquisition_seed(_db)
    print(f'  Acquisition: contents +{acq["contents_added"]} · leads +{acq["leads_added"]}')
    wh = ensure_webhook_bindings_seed(_db)
    print(f'  Webhook: +{wh["bindings_added"]}')
    ensure_wecom_defaults(_db)
    ensure_map_defaults(_db)

    from bootstrap.ensure_mkt import seed_mkt_demo
    from bootstrap.ensure_mkt_auto_rules import seed_auto_rules_demo
    from bootstrap.ensure_mkt_member_v2 import seed_member_system
    from bootstrap.ensure_coupon_wallet import ensure_coupon_wallet

    mkt = seed_mkt_demo(_db, hotel_id=1)
    ar = seed_auto_rules_demo(_db, hotel_id=1)
    ms = seed_member_system(_db, hotel_id=1)
    _db.commit()
    print(
        f'  Mkt: templates +{mkt["templates"]} · coupons +{mkt["coupons"]} · '
        f'auto_rules +{ar.get("auto_rules", 0)} · member levels +{ms.get("levels", 0)}'
    )
    cw = ensure_coupon_wallet(engine, _db, hotel_id=1)
    print(f'  Coupon wallet: seed +{cw["seed"].get("created", 0)}')

    from bootstrap.ensure_crm_extended import ensure_crm_extended
    from bootstrap.ensure_nl_segment import seed_nl_cancel_demo
    from bootstrap.ensure_order_arrival import seed_arrival_calendar_demo
    from bootstrap.ensure_deposits import seed_deposits_demo
    from bootstrap.ensure_refund_adjust import seed_refund_adjust_demo, seed_refund_cases_demo
    from bootstrap.ensure_oneid_audit import ensure_oneid_audit_realism
    from bootstrap.ensure_pricing_assistant import seed_pricing_assistant_demo

    ensure_crm_extended(_db)
    nl = seed_nl_cancel_demo(_db)
    print(f'  NL segments: cancel +{nl["cancel_orders_added"]}')
    arr = seed_arrival_calendar_demo(_db)
    print(f'  Arrival calendar: +{arr["orders_added"]}')
    dep = seed_deposits_demo(_db, hotel_id=1)
    if not dep.get("skipped"):
        print(f'  Deposits: +{dep.get("added", 0)}')
    ra = seed_refund_adjust_demo(_db, hotel_id=1)
    if not ra.get("skipped"):
        print(f'  Refund/adjust: +{ra.get("added", 0)}')
    seed_refund_cases_demo(_db, hotel_id=1)
    oid = ensure_oneid_audit_realism(_db, force_rebuild_events=True)
    print(f'  OneID: guests {oid["guests"]}')
    pa = seed_pricing_assistant_demo(_db, hotel_id=1)
    if pa.get("skipped"):
        print(f'  Pricing assistant: ready ({pa.get("reason", "skip")})')
    else:
        print(
            f'  Pricing assistant: types {pa.get("room_types", 0)} · '
            f'comps {pa.get("competitors", 0)} · reco +{pa.get("recommendations", 0)}'
        )

    print("[2/2] admin ready · DB ready for uvicorn")
finally:
    _db.close()

print(f"[2/2] SEED_LOCALE={SEED_LOCALE} · open http://127.0.0.1:{os.environ.get('FML_PORT') or '8081'}/")
