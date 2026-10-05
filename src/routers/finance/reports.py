# SPDX-License-Identifier: Apache-2.0
"""finance.reports subdomain routes."""

from __future__ import annotations

from models import FinanceReport
from routers.finance._common import (
    APIRouter,
    AppContext,
    Depends,
    FileResponse,
    HTTPException,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
    row_to_dict,
)

router = APIRouter(tags=["finance"])


@router.get("/finance/reports")
def list_finance_reports(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    rows = db.query(FinanceReport).filter_by(hotel_id=hotel_id).order_by(FinanceReport.id.desc()).limit(40).all()
    return ok([row_to_dict(r) for r in rows])


@router.get("/finance/reports/center")
def finance_reports_center(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    period: str = "month",
    start: str | None = None,
    end: str | None = None,
    compare: str = "yoy",
):
    from application.finance import build_center

    return ok(build_center(db, hotel_id, period=period, start=start, end=end, compare=compare))


@router.get("/finance/reports/{code}")
def finance_report_detail(
    code: str,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    period: str = "month",
    start: str | None = None,
    end: str | None = None,
    compare: str = "yoy",
):
    from application.finance import build_report

    return ok(build_report(db, hotel_id, code, period=period, start=start, end=end, compare=compare))


@router.get("/finance/reports/{code}/exports")
def finance_report_exports(
    code: str,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import list_exports

    return ok(list_exports(db, hotel_id, code=code))


@router.post("/finance/reports/{code}/export")
def finance_report_export(
    code: str,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import create_export

    fmt = (payload or {}).get("format") or "xlsx"
    period = (payload or {}).get("period") or "month"
    start = (payload or {}).get("start")
    end = (payload or {}).get("end")
    compare = (payload or {}).get("compare") or "yoy"
    operator = getattr(ctx, "username", None) or getattr(ctx, "name", None) or "店长"
    return ok(
        create_export(
            db,
            hotel_id,
            code,
            fmt,
            period=period,
            start=start,
            end=end,
            compare=compare,
            operator=str(operator),
        )
    )


@router.get("/finance/reports/exports/{export_id}/download")
def finance_report_export_download(
    export_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from fastapi.responses import FileResponse

    from application.finance import get_export_file

    try:
        path, name, mime = get_export_file(db, hotel_id, export_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return FileResponse(path, media_type=mime, filename=name)


@router.post("/finance/reports/{code}/ai-interpret")
def finance_report_ai_interpret(
    code: str,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """报告特化 AI 解读：双层提示词 + 4 段 JSON + 落库（不自动执行 actions）。"""
    from application.finance import interpret_report

    period = (payload or {}).get("period") or "month"
    start = (payload or {}).get("start")
    end = (payload or {}).get("end")
    compare = (payload or {}).get("compare") or "yoy"
    operator = getattr(ctx, "username", None) or getattr(ctx, "name", None) or "ai_agent"
    try:
        return ok(
            interpret_report(
                db,
                hotel_id,
                code,
                period=period,
                start=start,
                end=end,
                compare=compare,
                operator=str(operator),
            )
        )
    except Exception as e:
        raise HTTPException(503, f"AI 解读失败：{e}") from e


@router.get("/finance/reports/ai-interpret/{interpretation_id}")
def finance_report_ai_interpret_get(
    interpretation_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import get_interpretation

    try:
        return ok(get_interpretation(db, hotel_id, interpretation_id))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/finance/reports/ai-interpret/{interpretation_id}/actions/{action_index}/decide")
def finance_report_ai_action_decide(
    interpretation_id: int,
    action_index: int,
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """Harness 确认闸：confirmed | dismissed。"""
    from application.finance import decide_action

    decision = (payload or {}).get("decision") or "dismissed"
    remark = (payload or {}).get("remark") or ""
    operator = getattr(ctx, "username", None) or getattr(ctx, "name", None) or "店长"
    try:
        return ok(
            decide_action(
                db,
                hotel_id,
                interpretation_id,
                action_index,
                decision,
                operator=str(operator),
                remark=str(remark),
            )
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
