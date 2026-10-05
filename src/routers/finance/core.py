# SPDX-License-Identifier: Apache-2.0
"""finance.core subdomain routes."""

from __future__ import annotations

from routers.finance._common import APIRouter, AppContext, Depends, Session, get_current_user, get_db, hotel_scope, ok

router = APIRouter(tags=["finance"])


@router.get("/agreements/board")
def agreements_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """协议客工作台。"""
    from application.finance import build_agreements_board

    return ok(build_agreements_board(db, hotel_id))


@router.get("/ar/board")
def ar_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """协议 AR 应收看板。"""
    from application.finance import build_ar_board

    return ok(build_ar_board(db, hotel_id))


@router.post("/ar/{ledger_id}/settle")
def ar_settle(
    ledger_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    """对公回款核销：人工录入打款单号 + 金额。"""
    from application.finance import settle_ar_ledger

    return ok(
        settle_ar_ledger(
            db,
            ledger_id,
            hotel_id=ctx.hotel_id,
            amount=payload.get("amount") or 0,
            ref_no=payload.get("ref_no") or payload.get("bank_ref"),
            note=payload.get("note") or "对公回款核销",
            operator_id=getattr(ctx, "user_id", None),
        )
    )


# ---------- 押金管理 ----------
@router.get("/finance/flow-summary")
def finance_flow_summary(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """动线总览：最近夜审 + 异常/对账/报税/利润计数。"""
    from application.finance import finance_flow_summary as finance_flow_summary_q

    return ok(finance_flow_summary_q(db, hotel_id))


@router.get("/finance/payments-shift")
def payments_shift(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """当班收款汇总（payments），供交接班结算单 / 换班工作台。"""
    from application.finance import build_payments_shift

    return ok(build_payments_shift(db, hotel_id))


@router.get("/finance/ledger")
def list_ledger(hotel_id: int = Depends(hotel_scope), limit: int = 40, db: Session = Depends(get_db)):
    """账务流水（ledger_entries），供常住账务页。"""
    from application.finance import list_ledger as list_ledger_q

    return ok(list_ledger_q(db, hotel_id, limit=limit))


@router.get("/finance/board")
def finance_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """⑨ 动线聚合看板：支付方式/房型收益/渠道归因/物资/在住账单等。"""
    from application.finance import build_finance_board

    return ok(build_finance_board(db, hotel_id))


@router.get("/risk/board")
def risk_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """经营风控聚合看板。"""
    from application.finance import build_risk_board

    return ok(build_risk_board(db, hotel_id))


@router.get("/risk-alerts")
def list_risk_alerts(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_risk_alerts as list_risk_alerts_q

    return ok(list_risk_alerts_q(db, hotel_id))
