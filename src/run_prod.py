# SPDX-License-Identifier: Apache-2.0
"""Production start: ensure schema -> FastAPI (no demo seed).

Usage:
  DATABASE_URL=postgresql+psycopg://... python run_prod.py --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _wait_for_db(engine, timeout: int = 60) -> None:
    """Wait until the database accepts connections (pms may start before db)."""
    import time

    from sqlalchemy import text

    deadline = time.time() + timeout
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[run_prod] database reachable", flush=True)
            return
        except Exception as e:  # noqa: BLE001
            if time.time() >= deadline:
                raise RuntimeError(f"[run_prod] database not ready after {timeout}s: {e}") from e
            msg = str(e).replace("\n", " ")
            print(f"[run_prod] waiting for db... {msg[:120]}", flush=True)
            time.sleep(2)


def _ensure_schema() -> None:
    import concurrent.futures

    from database import engine
    from models import Base

    _wait_for_db(engine)

    # Structural migrations only; demo rows come from deploy/dev or 03_demo SQL
    from bootstrap.ensure_acquisition import ensure_acquisition_schema
    from bootstrap.ensure_acquisition_fields import ensure_acquisition_fields
    from bootstrap.ensure_ai_ask import ensure_ai_ask_schema
    from bootstrap.ensure_ar_ap import ensure_ar_ap_schema
    from bootstrap.ensure_assets import ensure_asset_schema
    from bootstrap.ensure_corp_agreements import ensure_corp_agreement_schema
    from bootstrap.ensure_coupon_wallet import ensure_coupon_wallet_schema
    from bootstrap.ensure_crm_extended import ensure_crm_tasks_schema
    from bootstrap.ensure_deposits import ensure_deposits_schema
    from bootstrap.ensure_group_orders import ensure_group_orders_schema
    from bootstrap.ensure_guest_aliases import ensure_guest_aliases_schema
    from bootstrap.ensure_llm_defaults import ensure_llm_schema
    from bootstrap.ensure_oneid_audit import ensure_oneid_audit_schema
    from bootstrap.ensure_order_arrival import ensure_order_arrival_schema
    from bootstrap.ensure_order_refactor import ensure_order_refactor_schema
    from bootstrap.ensure_room_inventory import ensure_room_inventory_schema
    from bootstrap.ensure_room_types import ensure_room_types_schema
    from bootstrap.ensure_service_requests import ensure_service_request_schema
    from bootstrap.ensure_supplies import ensure_supplies_schema
    from bootstrap.ensure_webhook import ensure_webhook_schema
    from bootstrap.ensure_wecom import ensure_wecom_schema
    from bootstrap.migrations.alter_pms_core_plaintext import ensure_pms_core_schema
    from bootstrap.migrations.alter_room_hk_columns import ensure_room_hk_schema
    from bootstrap.migrations.alter_to_single_hotel import ensure_single_hotel_schema
    from hk.staffing_service import ensure_staffing_schema

    # Step-by-step migrations with progress; >120s per step is treated as stuck
    steps = [
        ("create_all(base)", lambda e: Base.metadata.create_all(e)),
        ("single_hotel", ensure_single_hotel_schema),
        ("asset", ensure_asset_schema),
        ("supplies", ensure_supplies_schema),
        ("service_request", ensure_service_request_schema),
        ("room_inventory", ensure_room_inventory_schema),
        ("room_types", ensure_room_types_schema),
        ("corp_agreement", ensure_corp_agreement_schema),
        ("acquisition", ensure_acquisition_schema),
        ("webhook", ensure_webhook_schema),
        ("llm", ensure_llm_schema),
        ("ai_ask", ensure_ai_ask_schema),
        ("wecom", ensure_wecom_schema),
        ("crm_tasks", ensure_crm_tasks_schema),
        ("acquisition_fields", ensure_acquisition_fields),
        ("order_arrival", ensure_order_arrival_schema),
        ("order_refactor", ensure_order_refactor_schema),
        ("room_hk", ensure_room_hk_schema),
        ("pms_core", ensure_pms_core_schema),
        ("group_orders", ensure_group_orders_schema),
        ("oneid_audit", ensure_oneid_audit_schema),
        ("guest_aliases", ensure_guest_aliases_schema),
        ("deposits", ensure_deposits_schema),
        ("ar_ap", ensure_ar_ap_schema),
        ("staffing", ensure_staffing_schema),
        ("coupon_wallet", ensure_coupon_wallet_schema),
    ]

    def _run(name, fn):
        print(f"[schema] -> {name}", flush=True)
        fn(engine)
        print(f"[schema] OK {name}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        for name, fn in steps:
            fut = ex.submit(_run, name, fn)
            try:
                fut.result(timeout=120)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(
                    f"[schema] stuck: step '{name}' did not return within 120s; check DB locks/connections and retry."
                )

    # Optional non-core tables: skip on failure
    try:
        from finance.ota_commission_service import ensure_ota_commission_schema

        ensure_ota_commission_schema(engine)
        print("[schema] OK ota_commission", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[run_prod] ota_commission schema skip: {e}", flush=True)
    try:
        from infra.rbac_service import ensure_rbac_schema

        ensure_rbac_schema(engine)
        print("[schema] OK rbac", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[run_prod] rbac schema skip: {e}", flush=True)


def _log_hotel_config() -> None:
    """Ensure hotel YAML is resolved; load_hotel_doc logs absolute path (English)."""
    try:
        from infra.hotel_config import load_hotel_doc

        load_hotel_doc()
    except Exception as e:  # noqa: BLE001
        print(f"[run_prod] Hotel config resolve failed: {e}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="PMS production start (brand via FML_APP_NAME)")
    ap.add_argument("--host", default=os.environ.get("FML_HOST", "0.0.0.0"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("FML_PORT", "8000")))
    ap.add_argument("--skip-schema", action="store_true", help="Skip schema ensure on startup")
    args = ap.parse_args()

    _log_hotel_config()

    if not args.skip_schema:
        print("[run_prod] ensuring schema …")
        _ensure_schema()
        print("[run_prod] schema ready")

    import uvicorn

    uvicorn.run("api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
