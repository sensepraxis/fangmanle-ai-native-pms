# SPDX-License-Identifier: BUSL-1.1
"""资产画像 AI 建议：结合台账数据生成下一步行动。"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from commercial.ai_core.llm_service import chat as llm_chat
from commercial.ai_core.llm_service import chat_stream, llm_identity, load_llm_config
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.branding import brand_text
from infra.i18n import get_locale
from infra.i18n import t as _t
from models import Asset, AssetAlert, AssetMaintenance

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _wants_english() -> bool:
    return get_locale().startswith("en")


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _asset_system_prompt() -> str:
    if _wants_english():
        return brand_text(
            """You are a senior hotel engineering / FMS advisor for {APP_NAME} PMS.
Based ONLY on the provided asset ledger, finance metrics, alerts and work orders, output a concrete next-action brief.

Rules:
1. Data-driven — do not invent sensor readings or work-order IDs.
2. Cost-aware — weigh repair-to-original ratio, residual %, and replace index.
3. Ops-first — protect sellable rooms and guest experience.
4. Actionable — each step must name owner, action, and due date.

Decision hints:
- health < 55 or high alert → Corrective repair
- replace index ≥ 75 or residual < 30% with high repair ratio → Replace/retire review
- stable but PM due soon → Preventive maintenance
- otherwise → Keep monitoring

OUTPUT FORMAT (exact English section tags, entire body in English, no Chinese characters):
[Action] <Corrective repair|Preventive maintenance|Replace/retire review|Keep monitoring> · Confidence <60-98>% · priority <high|medium|low>

[Conclusion]
(one sentence ≤ 40 words)

[Next steps]
1. (owner + action + due)
2. (optional)
3. (optional)

[Risk & basis]
(1-2 sentences citing health, repair %, alerts or WOs)

No JSON, no markdown headings, no Chinese."""
        )
    return brand_text(
        """你是一名具有酒店工程与设施管理（FMS/CMMS）背景的高级设备运维顾问，服务于{APP_NAME}酒店 PMS。
请基于系统提供的资产台账、财务指标、告警与工单数据，输出可落地的「下一步行动建议」。

## 分析原则
1. 数据驱动：仅依据提供的数据推理，不得编造传感器读数、工单号或未给出的历史记录。
2. 成本意识：结合维修成本占原值比例、残值率、修换指数评估「继续维修 vs 更换」的经济性。
3. 运营优先：优先保障客房可售与宾客体验，明确是否影响运营连续性。
4. 可执行性：每条建议须明确责任方（工程部/采购/外包）、具体动作、建议完成时限。

## 判定维度参考
- 健康分 < 55 或存在高危告警 → 倾向「纠正性维修」
- 修换指数 ≥ 75 或残值率 < 30% 且维修占比偏高 → 倾向「更换报废评估」
- 无异常且临近维保日期 → 倾向「预防性维保」
- 指标平稳、无开放告警 → 倾向「持续监测」

## 输出格式（严格按此结构）
【行动判定】<纠正性维修|预防性维保|更换报废评估|持续监测> · 置信度 <60-98>% · 优先级 <高|中|低>

【结论】
（1 句话概括核心判断，≤40 字）

【执行建议】
1. （责任方 + 动作 + 时限）
2. （可选第 2 条）
3. （可选第 3 条）

【风险与依据】
（1-2 句说明关键数据依据）

用户可见文案必须全中文。不要输出 JSON、markdown 标题或额外说明。"""
    )


def _build_user_prompt(ctx: dict) -> str:
    if _wants_english():
        return (
            "Produce the next-action brief in English only (no Chinese characters).\n"
            "Use section tags [Action] [Conclusion] [Next steps] [Risk & basis].\n\n"
            f"[Asset ledger]\n{json.dumps(ctx['asset'], ensure_ascii=False, indent=2)}\n\n"
            f"[Analytics]\n{json.dumps(ctx['analytics'], ensure_ascii=False, indent=2)}\n\n"
            f"[Open alerts]\n{json.dumps(ctx['alerts'], ensure_ascii=False, indent=2)}\n\n"
            f"[Recent work orders]\n{json.dumps(ctx['work_orders'], ensure_ascii=False, indent=2)}\n"
        )
    return f"""请根据以下设备资产数据，按系统提示的格式输出「下一步行动建议」。
用户可见文案必须全中文。

【资产台账】
{json.dumps(ctx["asset"], ensure_ascii=False, indent=2)}

【分析指标】
{json.dumps(ctx["analytics"], ensure_ascii=False, indent=2)}

【开放告警】
{json.dumps(ctx["alerts"], ensure_ascii=False, indent=2)}

【关联工单（近期）】
{json.dumps(ctx["work_orders"], ensure_ascii=False, indent=2)}

请综合健康分、维修成本占比、修换指数、开放/逾期工单、下次维保日期与告警信息，给出最优下一步行动。"""


def _ensure_locale_text(parsed: dict, ctx: dict) -> dict:
    """EN 下若模型仍混入中文，改用已翻译的规则兜底文案。"""
    text = str(parsed.get("text") or "")
    if _wants_english() and _has_cjk(text):
        fb = _rule_fallback(ctx)
        fb["source"] = "unavailable"
        fb["llm_error"] = _t("模型返回含中文，未当作 AI 结论")
        fb["text"] = ""
        return fb
    return parsed


def _asset_context(asset: Asset, maint: list, alerts: list) -> dict:
    pv = float(asset.purchase_value or 0)
    cv = float(asset.current_value if asset.current_value is not None else pv)
    rc = float(asset.repair_cost_total or 0)
    health = int(asset.health_score or 0)
    ratio = round(100 * rc / pv, 1) if pv > 0 else 0
    years = None
    if asset.purchase_date:
        years = max(0, round((date.today() - asset.purchase_date).days / 365.25))
    residual = round(100 * cv / pv, 1) if pv > 0 else 0

    replace_index = min(
        99,
        round(
            ratio * 0.5
            + max(0, 70 - health) * 0.4
            + (12 if years is not None and years >= 8 else 0)
            + (10 if residual < 30 else 0)
        ),
    )

    open_wo = [m for m in maint if (m.status or "scheduled") != "done"]
    overdue_wo = [m for m in open_wo if m.status == "overdue"]

    return {
        "asset": {
            "id": asset.id,
            "name": asset.name,
            "asset_no": asset.asset_no or asset.sn,
            "category": asset.category,
            "brand_model": asset.brand_model,
            "location": asset.location,
            "room_no": asset.room_no,
            "status": asset.status,
            "health_score": health,
            "insight": asset.insight,
            "purchase_date": str(asset.purchase_date) if asset.purchase_date else None,
            "purchase_value": pv,
            "current_value": cv,
            "repair_cost_total": rc,
            "repair_to_purchase_pct": ratio,
            "residual_pct": residual,
            "service_years": years,
            "next_maintain_date": str(asset.next_maintain_date) if asset.next_maintain_date else None,
            "warranty_until": str(asset.warranty_until) if asset.warranty_until else None,
            "runtime_hours": asset.runtime_hours,
            "avg_power_w": float(asset.avg_power_w) if asset.avg_power_w is not None else None,
            "supplier": asset.supplier,
            "dept": asset.dept,
        },
        "analytics": {
            "replace_index": replace_index,
            "open_work_orders": len(open_wo),
            "overdue_work_orders": len(overdue_wo),
        },
        "alerts": [
            {
                "severity": al.severity,
                "message": al.message,
                "alert_type": al.alert_type,
            }
            for al in alerts[:5]
        ],
        "work_orders": [
            {
                "task_type": m.task_type,
                "status": m.status,
                "due_date": str(m.due_date) if m.due_date else None,
                "owner": m.owner,
                "note": m.note,
            }
            for m in maint[:6]
        ],
    }


def load_asset_action_context(db: Session, hotel_id: int, asset_id: int) -> dict:
    asset = db.query(Asset).filter_by(id=asset_id, hotel_id=hotel_id).first()
    if not asset:
        raise NotFoundError("asset not found")

    maint = (
        db.query(AssetMaintenance)
        .filter_by(hotel_id=hotel_id, asset_id=asset_id)
        .order_by(AssetMaintenance.due_date.desc())
        .limit(8)
        .all()
    )
    alerts = (
        db.query(AssetAlert)
        .filter_by(hotel_id=hotel_id, asset_id=asset_id, status="open")
        .order_by(AssetAlert.id.desc())
        .limit(5)
        .all()
    )
    return _asset_context(asset, maint, alerts)


def _parse_narrative_response(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError(_t("模型返回内容为空"))

    head = raw[:160]
    action_map = [
        ("纠正性维修", "repair"),
        ("故障维修", "repair"),
        ("Corrective repair", "repair"),
        ("更换报废评估", "replace"),
        ("更换报废", "replace"),
        ("报废评估", "replace"),
        ("Replacement", "replace"),
        ("预防性维保", "maintain"),
        ("计划维保", "maintain"),
        ("Preventive", "maintain"),
        ("持续监测", "monitor"),
        ("Monitor", "monitor"),
    ]
    action_type = "monitor"
    for label, code in action_map:
        if label in head:
            action_type = code
            break

    conf_m = re.search(r"(?:置信度|Confidence)\s*(\d+)", head, re.I)
    conf = int(conf_m.group(1)) if conf_m else 85
    conf = max(60, min(98, conf))

    urgency = "medium"
    if re.search(r"优先级\s*高|·\s*高\b|priority\s*[:=]?\s*high", head, re.I):
        urgency = "high"
    elif re.search(r"优先级\s*低|·\s*低\b|priority\s*[:=]?\s*low", head, re.I):
        urgency = "low"

    summary_m = re.search(
        r"(?:【结论】|\[Conclusion\])\s*(.+?)(?=\n\n|【执行|【风险|\[Next|\[Risk|$)",
        raw,
        re.S | re.I,
    )
    summary = summary_m.group(1).strip().replace("\n", " ") if summary_m else ""

    return {
        "conf": conf,
        "text": raw,
        "summary": summary,
        "detail": raw,
        "action_type": action_type,
        "urgency": urgency,
    }


def _rule_fallback(ctx: dict) -> dict:
    a = ctx["asset"]
    name = a.get("name") or _t("该设备")
    # EN：台账名常为中文种子，结论里改用编号/房号，避免正文再混中文
    if _wants_english() and _has_cjk(str(name)):
        name = a.get("asset_no") or (f"Room {a['room_no']}" if a.get("room_no") else _t("该设备"))
    loc = _t("{n} 房", n=a["room_no"]) if a.get("room_no") else (a.get("location") or "—")
    ri = ctx["analytics"]["replace_index"]
    health = a.get("health_score") or 0
    ratio = a.get("repair_to_purchase_pct") or 0
    rc = a.get("repair_cost_total") or 0
    alert_msg = ctx["alerts"][0]["message"] if ctx["alerts"] else None
    conf = min(96, max(78, 82 + health // 8))

    if ri >= 75:
        text = _t(
            "【行动判定】更换报废评估 · 置信度 {conf}% · 优先级 高\n\n"
            "【结论】\n{name} 修换指数 {ri}，继续维修经济性不足。\n\n"
            "【执行建议】\n"
            "1. 采购部在 7 个工作日内完成同品类设备选型与报价比价\n"
            "2. 工程部评估拆除安装窗口，优先选择低入住率时段施工\n\n"
            "【风险与依据】\n"
            "累计维修 ¥{rc}，占原值 {ratio}%，健康分 {health}。",
            conf=conf,
            name=name,
            ri=ri,
            loc=loc,
            rc=f"{rc:,.0f}",
            ratio=ratio,
            health=health,
        )
        return {
            "conf": conf,
            "text": text,
            "action_type": "replace",
            "urgency": "high",
            "summary": _t("建议更换或报废"),
            "detail": text,
        }
    if a.get("status") == "abnormal" or health < 55 or any(al.get("severity") == "high" for al in ctx["alerts"]):
        text = _t(
            "【行动判定】纠正性维修 · 置信度 {conf}% · 优先级 高\n\n"
            "【结论】\n{name} 状态异常，需立即处置。\n\n"
            "【执行建议】\n"
            "1. 工程部 24 小时内到场排查并生成维修工单\n"
            "2. 优先处理：{issue}\n\n"
            "【风险与依据】\n"
            "健康分 {health}，存在开放高危告警或异常状态。",
            conf=conf,
            name=name,
            issue=_t(alert_msg or "设备异常"),
            health=health,
        )
        return {
            "conf": conf,
            "text": text,
            "action_type": "repair",
            "urgency": "high",
            "summary": _t("建议立即维修"),
            "detail": text,
        }
    nm = a.get("next_maintain_date") or _t("下月")
    text = _t(
        "【行动判定】预防性维保 · 置信度 {conf}% · 优先级 中\n\n"
        "【结论】\n{name} 运行平稳，按计划开展预防性维保。\n\n"
        "【执行建议】\n"
        "1. 工程维保部在 {date} 前完成计划性检测与保养\n"
        "2. 维护后更新设备健康评分并归档记录\n\n"
        "【风险与依据】\n"
        "健康分 {health}，无高危告警，开放工单 {n} 条。",
        conf=conf,
        name=name,
        date=nm,
        health=health,
        n=ctx["analytics"]["open_work_orders"],
    )
    return {
        "conf": conf,
        "text": text,
        "action_type": "maintain",
        "urgency": "medium",
        "summary": _t("按计划预防维保"),
        "detail": text,
    }


def _finalize_llm_result(parsed: dict, cfg: dict, res: dict | None = None) -> dict:
    parsed["source"] = "llm"
    parsed.update(llm_identity(cfg, res))
    return parsed


def generate_asset_next_action(db: Session, hotel_id: int, asset_id: int) -> dict:
    ctx = load_asset_action_context(db, hotel_id, asset_id)
    cfg = load_llm_config(db)

    try:
        res = llm_chat(
            db,
            [{"role": "user", "content": _build_user_prompt(ctx)}],
            extra_system=_asset_system_prompt(),
        )
        parsed = _parse_narrative_response(res.get("content") or "")
        ensured = _ensure_locale_text(parsed, ctx)
        if ensured.get("source") in ("fallback", "unavailable"):
            return {"source": "unavailable", "text": "", "llm_error": ensured.get("llm_error") or ""}
        return _finalize_llm_result(ensured, cfg, res)
    except HTTPException as e:
        return {"source": "unavailable", "text": "", "llm_error": str(e.detail) if hasattr(e, "detail") else str(e)}
    except Exception as e:
        return {"source": "unavailable", "text": "", "llm_error": str(e)[:200]}


def stream_asset_next_action(db: Session, hotel_id: int, asset_id: int) -> Iterator[dict]:
    """SSE 事件：token / done / error。"""
    ctx = load_asset_action_context(db, hotel_id, asset_id)
    cfg = load_llm_config(db)
    stream_tokens = not _wants_english()

    try:
        full = ""
        for chunk in chat_stream(
            db,
            [{"role": "user", "content": _build_user_prompt(ctx)}],
            extra_system=_asset_system_prompt(),
        ):
            full += chunk
            # EN：不推流式中文碎片，避免过程中出现中文；仅最终 done 交付
            if stream_tokens:
                yield {"type": "token", "content": chunk}

        parsed = _parse_narrative_response(full)
        ensured = _ensure_locale_text(parsed, ctx)
        if ensured.get("source") in ("fallback", "unavailable"):
            yield {
                "type": "done",
                "data": {"source": "unavailable", "text": "", "llm_error": ensured.get("llm_error") or ""},
            }
        else:
            yield {"type": "done", "data": _finalize_llm_result(ensured, cfg)}
    except HTTPException as e:
        yield {
            "type": "done",
            "data": {
                "source": "unavailable",
                "text": "",
                "llm_error": str(e.detail) if hasattr(e, "detail") else str(e),
            },
        }
    except Exception as e:
        yield {"type": "done", "data": {"source": "unavailable", "text": "", "llm_error": str(e)[:200]}}
