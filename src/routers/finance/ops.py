# SPDX-License-Identifier: Apache-2.0
"""finance.ops subdomain routes."""

from __future__ import annotations

from routers.finance._common import (
    APIRouter,
    AppContext,
    BaseModel,
    Depends,
    HTTPException,
    Optional,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["finance"])


@router.get("/finance/audit-exceptions")
def list_audit_exceptions(
    hotel_id: int = Depends(hotel_scope), biz_date: Optional[str] = None, db: Session = Depends(get_db)
):
    from application.finance import list_audit_exceptions as list_audit_exceptions_q
    from domain import ValidationError

    try:
        return ok(list_audit_exceptions_q(db, hotel_id, biz_date=biz_date))
    except ValidationError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/finance/audit-exceptions/{eid}/fix")
def fix_audit_exception(eid: int, db: Session = Depends(get_db)):
    from application.finance import fix_audit_exception as fix_audit_exception_uc

    return ok(fix_audit_exception_uc(db, eid))


@router.get("/finance/recon-batches")
def list_recon_batches(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_recon_batches_enriched

    return ok(list_recon_batches_enriched(db, hotel_id))


@router.post("/finance/recon-batches/sync")
def sync_recon_batches(
    hotel_id: int = Depends(hotel_scope),
    days: int = 14,
    db: Session = Depends(get_db),
):
    """强制同步：按库内订单与收款重建对账批次。"""
    from application.finance import rebuild_recon_from_orders
    from seed import TODAY as SEED_TODAY

    as_of = SEED_TODAY if SEED_TODAY else None
    result = rebuild_recon_from_orders(db, hotel_id, days=days, as_of=as_of)
    return ok(result)


@router.get("/finance/recon-batches/{bid}")
def recon_batch_detail(bid: int, db: Session = Depends(get_db)):
    from application.finance import batch_detail_enriched

    data = batch_detail_enriched(db, bid)
    if not data:
        raise HTTPException(404, "batch not found")
    return ok(data)


@router.post("/finance/recon-batches/{bid}/ai-explain")
def recon_batch_ai_explain(bid: int, db: Session = Depends(get_db)):
    """点击触发：基于库内订单明细调用 LLM，先陈述事实再归因。"""
    from application.finance import explain_recon_batch

    try:
        return ok(explain_recon_batch(db, bid))
    except ValueError:
        raise HTTPException(404, "batch not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"AI 差异解释失败：{e}") from e


@router.get("/finance/recon-conflicts")
def list_recon_conflicts(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """冲突明细（供审计冲突下钻页）。"""
    from application.finance import list_recon_conflicts as list_recon_conflicts_q

    return ok(list_recon_conflicts_q(db, hotel_id))


@router.get("/finance/tax-filings")
def list_tax_filings(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_tax_filings as list_tax_filings_q

    return ok(list_tax_filings_q(db, hotel_id))


@router.get("/finance/invoices/workspace")
def invoice_workspace(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """发票管理中心：KPI + 待开/已开/红冲/失败列表（库内订单+发票聚合）。"""
    from application.finance import list_invoice_workspace

    return ok(list_invoice_workspace(db, hotel_id))


@router.get("/finance/ar-ap/workspace")
def ar_ap_workspace(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """应收应付中心：KPI + 应收/应付/账龄/授信（与订单、协议 AR、OTA 对账同源）。"""
    from application.finance import list_workspace

    return ok(list_workspace(db, hotel_id))


@router.post("/finance/ar-ap/check-credit")
def ar_ap_check_credit(payload: dict = {}, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import check_credit

    corp_id = int(payload.get("corp_id") or 0)
    amount = float(payload.get("amount") or 0)
    if not corp_id:
        raise HTTPException(400, "请选择协议单位")
    return ok(check_credit(db, hotel_id, corp_id, amount))


@router.post("/finance/ar-ap/charge")
def ar_ap_charge(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """企业挂账：授信校验 + 生成 AR 单据。"""
    from application.finance import create_corp_charge

    corp_id = int(payload.get("corp_id") or 0)
    amount = float(payload.get("amount") or 0)
    note = str(payload.get("note") or "")
    operator = str(getattr(ctx, "username", None) or getattr(ctx, "user_id", None) or "财务")
    if not corp_id or amount <= 0:
        raise HTTPException(400, "协议单位与挂账金额必填")
    return ok(create_corp_charge(db, hotel_id, corp_id, amount, operator, note))


@router.post("/finance/ar-ap/ar/{ar_id}/receipt")
def ar_ap_receipt(
    ar_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import apply_receipt

    amount = float(payload.get("amount") or 0)
    channel = str(payload.get("channel") or "对公转账")
    ref_no = str(payload.get("ref_no") or "")
    operator = str(getattr(ctx, "username", None) or getattr(ctx, "user_id", None) or "财务")
    return ok(apply_receipt(db, hotel_id, ar_id, amount, channel, operator, ref_no))


@router.post("/finance/ar-ap/ap/{ap_id}/payment")
def ar_ap_payment(
    ap_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import apply_payment

    amount = float(payload.get("amount") or 0)
    channel = str(payload.get("channel") or "对公转账")
    ref_no = str(payload.get("ref_no") or "")
    operator = str(getattr(ctx, "username", None) or getattr(ctx, "user_id", None) or "财务")
    return ok(apply_payment(db, hotel_id, ap_id, amount, channel, operator, ref_no))


@router.post("/finance/ar-ap/ar/{ar_id}/write-off")
def ar_ap_write_off(
    ar_id: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import write_off_ar

    reason = str(payload.get("reason") or "")
    approver = str(payload.get("approver") or "")
    operator = str(getattr(ctx, "username", None) or getattr(ctx, "user_id", None) or "财务")
    return ok(write_off_ar(db, hotel_id, ar_id, reason, approver, operator))


@router.post("/finance/ar-ap/todos/{todo_id}/dismiss")
def ar_ap_dismiss_todo(
    todo_id: str,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """标记催收/授信待办已跟进（不自动核销回款）。"""
    from application.finance import dismiss_ar_ap_todo

    operator = str(getattr(ctx, "username", None) or getattr(ctx, "user_id", None) or "财务")
    note = str(payload.get("note") or "")
    return ok(dismiss_ar_ap_todo(db, hotel_id, todo_id, operator, note))


@router.post("/finance/ai-plan/generate")
def finance_ai_plan_generate(
    payload: dict = {},
    db: Session = Depends(get_db),
    hotel_id: int = Depends(hotel_scope),
):
    """财务 AI Harness：生成可确认操作单（押金/退改/夜审/对账/发票）。"""
    from application.finance import generate_plan

    scene = str(payload.get("scene") or "recon")
    return ok(generate_plan(db, hotel_id, scene))


@router.post("/finance/ai-plan/confirm")
def finance_ai_plan_confirm(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
    hotel_id: int = Depends(hotel_scope),
):
    """确认执行勾选操作单并写库（资金/日切类不会自动完成）。"""
    from application.finance import confirm_plan

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else payload
    operator = str(getattr(ctx, "user_id", None) or getattr(ctx, "username", None) or "财务AI")
    return ok(confirm_plan(db, hotel_id, plan=plan, operator=operator))


class InvoiceIssuePayload(BaseModel):
    order_id: int


@router.post("/finance/invoices/issue")
def invoice_issue(payload: InvoiceIssuePayload, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import issue_invoice

    return ok(issue_invoice(db, hotel_id, payload.order_id))


class InvoiceRedPayload(BaseModel):
    reason: str


@router.post("/finance/invoices/{invoice_id}/red-flush")
def invoice_red_flush(
    invoice_id: int,
    payload: InvoiceRedPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """红冲：必须人工确认并填写原因，不自动执行。"""
    from application.finance import red_flush_invoice

    return ok(red_flush_invoice(db, hotel_id, invoice_id, payload.reason))


@router.get("/finance/profit-insights")
def list_profit_insights(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_profit_insights as list_profit_insights_q

    return ok(list_profit_insights_q(db, hotel_id))


@router.get("/finance/revenue-anomalies")
def list_revenue_anomalies(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_revenue_anomalies as list_revenue_anomalies_q

    return ok(list_revenue_anomalies_q(db, hotel_id))
