# SPDX-License-Identifier: Apache-2.0
"""报表导出：列表 / 生成 / 下载。"""

from __future__ import annotations

import csv
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from finance.reports.builders import build_report
from infra.i18n import t
from models import FinanceReportExport

# 保持与旧 finance_reports_service.py 相同目录：finance/data/report_exports
EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "report_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


_TEXT_KEYS = {
    "dept",
    "metric",
    "method",
    "item",
    "channel",
    "customer",
    "name",
    "title",
    "type",
    "note",
    "room_type",
    "yoy",
}


def _hdr(v: Any) -> str:
    s = "" if v is None else str(v)
    return t(s) if s else s


def _flatten_rows(report: dict) -> list[list[Any]]:
    out: list[list[Any]] = [[_hdr("报表"), _hdr(report.get("name"))], [_hdr("期间"), report.get("period_label")]]
    for sec in report.get("sections") or []:
        if sec.get("type") == "stats":
            out.append([])
            out.append([_hdr(sec.get("title"))])
            for it in sec.get("items") or []:
                out.append([_hdr(it.get("lab")), f"{it.get('v')}{it.get('small') or ''}"])
        elif sec.get("type") == "table":
            out.append([])
            out.append([_hdr(sec.get("title"))])
            cols = sec.get("columns") or []
            out.append([_hdr(c.get("label")) for c in cols])
            for row in sec.get("rows") or []:
                cells = []
                for c in cols:
                    key = c.get("key")
                    val = row.get(key)
                    if key in _TEXT_KEYS and val not in (None, ""):
                        cells.append(_hdr(val))
                    else:
                        cells.append(val)
                out.append(cells)
    return out


def _write_export_file(report: dict, fmt: str, token: str) -> tuple[Path, int, int]:
    rows = _flatten_rows(report)
    row_count = len(rows)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in report.get("code", "report"))
    if fmt == "csv":
        path = EXPORT_DIR / f"{safe}_{token}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow(r)
    elif fmt == "pdf":
        path = EXPORT_DIR / f"{safe}_{token}.pdf"
        content = "BT /F1 12 Tf 50 740 Td (Financial Report) Tj ET"
        raw = f"""%PDF-1.1
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj
4 0 obj<< /Length {len(content)} >>stream
{content}
endstream endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
trailer<< /Size 6 /Root 1 0 R >>
%%EOF
"""
        path.write_bytes(raw.encode("latin-1", errors="ignore"))
        path.with_suffix(".txt").write_text("\n".join("\t".join(str(c) for c in r) for r in rows), encoding="utf-8")
    else:
        path = EXPORT_DIR / f"{safe}_{token}.xlsx"

        def esc(x: Any) -> str:
            s = str(x if x is not None else "")
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        xml_rows = []
        for r in rows:
            cells = "".join(f'<Cell><Data ss:Type="String">{esc(c)}</Data></Cell>' for c in r)
            xml_rows.append(f"<Row>{cells}</Row>")
        xml = (
            '<?xml version="1.0"?>\n<?mso-application progid="Excel.Sheet"?>\n'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
            f'<Worksheet ss:Name="Report"><Table>{"".join(xml_rows)}</Table></Worksheet></Workbook>'
        )
        path.write_text(xml, encoding="utf-8")
    return path, path.stat().st_size, row_count


def list_exports(db: Session, hotel_id: int, code: Optional[str] = None, limit: int = 20) -> list[dict]:
    q = db.query(FinanceReportExport).filter_by(hotel_id=hotel_id)
    if code:
        q = q.filter_by(report_code=code)
    rows = q.order_by(FinanceReportExport.id.desc()).limit(limit).all()
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "report_code": r.report_code,
                "report_name": r.report_name,
                "format": r.format,
                "status": r.status,
                "file_name": r.file_name,
                "size_bytes": r.size_bytes,
                "row_count": r.row_count,
                "async_job": bool(r.async_job),
                "generated_at": r.generated_at.isoformat(sep=" ", timespec="minutes") if r.generated_at else None,
                "generated_by": t(r.generated_by or "系统"),
                "download_url": f"/api/finance/reports/exports/{r.id}/download",
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
        )
    return out


def create_export(
    db: Session,
    hotel_id: int,
    code: str,
    fmt: str,
    *,
    period: str = "month",
    start: Optional[str] = None,
    end: Optional[str] = None,
    compare: str = "yoy",
    operator: str = "店长",
) -> dict:
    fmt = (fmt or "xlsx").lower()
    if fmt not in ("xlsx", "pdf", "csv"):
        fmt = "xlsx"
    report = build_report(db, hotel_id, code, period=period, start=start, end=end, compare=compare)
    token = uuid.uuid4().hex[:10]
    path, size, row_count = _write_export_file(report, fmt, token)
    async_job = size > 10 * 1024 * 1024 or row_count > 10000
    now = datetime.now()
    exp = FinanceReportExport(
        hotel_id=hotel_id,
        report_code=code,
        report_name=report.get("name") or code,
        format=fmt,
        status="ready",
        file_name=path.name,
        file_path=str(path),
        size_bytes=size,
        row_count=row_count,
        async_job=async_job,
        period_start=date.fromisoformat(report["period_start"]),
        period_end=date.fromisoformat(report["period_end"]),
        generated_at=now,
        generated_by=operator,
        expires_at=now + timedelta(days=365 * 7),
        snapshot_json=json.dumps(report.get("snapshot") or {}, ensure_ascii=False),
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return list_exports(db, hotel_id, code=code, limit=1)[0]


def get_export_file(db: Session, hotel_id: int, export_id: int) -> tuple[Path, str, str]:
    row = db.get(FinanceReportExport, export_id)
    if not row or row.hotel_id != hotel_id:
        raise FileNotFoundError("导出记录不存在")
    path = Path(row.file_path or "")
    if not path.exists():
        raise FileNotFoundError("文件已过期或不存在")
    mime = {
        "xlsx": "application/vnd.ms-excel",
        "csv": "text/csv; charset=utf-8",
        "pdf": "application/pdf",
    }.get(row.format or "", "application/octet-stream")
    return path, row.file_name or path.name, mime
