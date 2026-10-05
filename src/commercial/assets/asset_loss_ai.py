# SPDX-License-Identifier: BUSL-1.1
"""报损分析页 —— 高频损坏 LLM 归因。"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from typing import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from commercial.ai_core.llm_service import chat as llm_chat
from commercial.ai_core.llm_service import chat_stream, llm_identity, load_llm_config
from infra.branding import brand_text
from infra.i18n import get_locale
from infra.i18n import t as _t
from models import AppSetting, Asset, AssetAlert, AssetMaintenance, DamageTicket

LINEN_RE = re.compile(r"布草|床单|浴巾|枕套|面巾")
SUPPLY_LINE = {"linen"}
CACHE_KEY_PREFIX = "loss_attr:"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _wants_english() -> bool:
    return str(get_locale() or "").lower().startswith("en")


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _is_linen_damage(d: dict) -> bool:
    blob = f"{d.get('asset_category') or ''} {d.get('item_name') or ''} {d.get('line') or ''}"
    return d.get("line") in SUPPLY_LINE or bool(LINEN_RE.search(blob))


def _is_equipment_asset(a: Asset) -> bool:
    cat = (a.category or "").strip()
    return bool(cat) and not re.search(r"布草|消耗|易耗|耗材|linen|amenity", cat, re.I)


def _period_bounds(period: str) -> tuple[date | None, date]:
    today = date.today()
    if period == "all":
        return None, today
    months = 6 if period == "6" else 12
    start = today - timedelta(days=int(months * 30.44))
    return start, today


def _in_period(raw: str | None, start: date | None, end: date) -> bool:
    if not start:
        return True
    if not raw:
        return False
    try:
        d = datetime.fromisoformat(str(raw).replace("Z", "+00:00")[:19]).date()
    except ValueError:
        try:
            d = date.fromisoformat(str(raw)[:10])
        except ValueError:
            return False
    return start <= d <= end


def _maint_date(m: AssetMaintenance) -> str | None:
    if m.completed_at:
        return str(m.completed_at)
    if m.due_date:
        return str(m.due_date)
    if m.created_at:
        return str(m.created_at)
    return None


def load_loss_attribution_context(db: Session, hotel_id: int, period: str = "12") -> dict:
    start, end = _period_bounds(period)
    period_label = {
        "6": _t("过去 6 个月"),
        "12": _t("过去 12 个月"),
        "all": _t("全部历史"),
    }.get(period, _t("过去 12 个月"))

    damages_raw = [
        row
        for row in (
            db.query(DamageTicket).filter_by(hotel_id=hotel_id).order_by(DamageTicket.id.desc()).limit(80).all()
        )
        if not _is_linen_damage({"line": row.line, "asset_category": row.asset_category, "item_name": row.item_name})
    ]
    damages = []
    for d in damages_raw:
        created = d.created_at.isoformat() if d.created_at else None
        if not _in_period(created, start, end):
            continue
        damages.append(
            {
                "id": d.id,
                "item_name": d.item_name,
                "asset_category": d.asset_category,
                "room_no": d.room_no,
                "severity": d.severity,
                "description": d.description,
                "note": d.note,
                "ai_suggestion": d.ai_suggestion,
                "ai_tags": d.ai_tags,
                "fee": float(d.fee or 0),
                "status": d.status,
                "created_at": created,
            }
        )

    assets = {a.id: a for a in db.query(Asset).filter_by(hotel_id=hotel_id).all() if _is_equipment_asset(a)}

    maintenance = []
    for m in (
        db.query(AssetMaintenance).filter_by(hotel_id=hotel_id).order_by(AssetMaintenance.id.desc()).limit(60).all()
    ):
        asset = assets.get(m.asset_id)
        if not asset:
            continue
        md = _maint_date(m)
        if not _in_period(md, start, end):
            continue
        maintenance.append(
            {
                "id": m.id,
                "asset_id": m.asset_id,
                "asset_name": asset.name,
                "asset_category": asset.category,
                "room_no": asset.room_no,
                "task_type": m.task_type,
                "status": m.status,
                "note": m.note,
                "cost": float(m.cost or 0),
                "due_date": str(m.due_date) if m.due_date else None,
                "owner": m.owner,
            }
        )

    alerts = []
    for a in (
        db.query(AssetAlert).filter_by(hotel_id=hotel_id, status="open").order_by(AssetAlert.id.desc()).limit(20).all()
    ):
        created = a.created_at.isoformat() if a.created_at else None
        if start and created and not _in_period(created, start, end):
            continue
        alerts.append(
            {
                "asset_id": a.asset_id,
                "asset_name": a.asset_name,
                "room_no": a.room_no,
                "floor": a.floor,
                "severity": a.severity,
                "alert_type": a.alert_type,
                "message": a.message,
                "created_at": created,
            }
        )

    return {
        "period": period,
        "period_label": period_label,
        "stats": {
            "damage_count": len(damages),
            "alert_count": len(alerts),
            "maintenance_count": len(maintenance),
            "damage_fee_total": round(sum(d["fee"] for d in damages), 2),
        },
        "damages": damages[:30],
        "alerts": alerts[:15],
        "maintenance": maintenance[:20],
    }


LOSS_ATTRIBUTION_SYSTEM_ZH = brand_text("""你是一名酒店设备设施运维分析顾问，服务于{APP_NAME} PMS。
请根据系统提供的报损单、开放告警与维保记录，归纳「高频损坏归因」结论。

## 分析原则
1. 仅依据输入数据归纳，不得编造未出现的设备、房号、金额或次数。
2. 「归因」指解释重复出现的损坏模式及其可能根因（老化、受潮、高使用强度、批次缺陷、水压异常等）。
3. 将相似报损/告警合并为同一主题；count 为合并后的记录条数之和。
4. 按发生频次与业务影响（severity、费用、是否影响入住）排序，最多输出 3 条。

## 输出格式（必须严格按顺序，分两段）

第一段 —— 分析过程（Markdown，供用户实时阅读）：
以标题「## 分析过程」开头，用 3～5 条 bullet 说明：
- 你如何聚类报损/告警（引用了哪些记录 ID 或物品名）
- 为何判定为高频或高影响
- 根因推断的依据（勿编造未给出的数据）

第二段 —— 归因结论（严格 JSON，用 ```json 代码块包裹，不要其他文字）：
每条 item 必须按下列字段结构化填写，禁止把多段内容挤进一个字符串：
```json
{
  "items": [
    {
      "title": "问题主题，≤16字",
      "count": 3,
      "count_label": "3 起",
      "priority": "high|mid|low",
      "root_cause": "根因一句话，≤36字",
      "mechanism": "故障机理，≤40字，如阀芯磨损、密封老化",
      "evidence": [
        "依据1：引用具体报损/告警/维保，≤50字",
        "依据2：说明为何判定高频或高影响"
      ],
      "data_refs": [
        {"type": "damage", "id": 7, "label": "报损#7 · 8201水龙头漏水"},
        {"type": "alert", "id": 10, "label": "告警#10 · TOTO马桶水压异常"}
      ],
      "action_hint": "建议措施，≤40字，可空",
      "related_items": ["物品或设备名"]
    }
  ]
}
```
字段要求：
- root_cause / mechanism / evidence / data_refs 各司其职，不要重复粘贴相同句子
- evidence 固定 2～3 条，每条独立一句
- data_refs 固定 1～4 条，必须为对象数组，含 type(damage/alert/maintenance)、id、label
- 不要使用 description 字段（已废弃）
- 用户可见字符串必须全中文""")

LOSS_ATTRIBUTION_SYSTEM_EN = brand_text("""You are a hotel facilities operations analyst for {APP_NAME} PMS.
From damage tickets, open alerts and maintenance records, produce high-frequency failure attribution.

Rules:
1. Use only provided data; do not invent assets, rooms, amounts or counts.
2. Attribution = repeating damage pattern + likely root cause (aging, moisture, heavy use, batch defect, water pressure, etc.).
3. Merge similar items; count is the merged record total.
4. Rank by frequency and business impact; output at most 3 items.

Output in two parts:

Part 1 — Process (Markdown for live reading):
Start with "## Analysis process", then 3–5 bullets on clustering, why high impact, and evidence basis.

Part 2 — Attribution JSON in a ```json fence only:
```json
{
  "items": [
    {
      "title": "theme ≤ 8 words",
      "count": 3,
      "count_label": "3 cases",
      "priority": "high|mid|low",
      "root_cause": "one sentence ≤ 20 words",
      "mechanism": "failure mechanism ≤ 24 words",
      "evidence": ["evidence 1", "evidence 2"],
      "data_refs": [
        {"type": "damage", "id": 7, "label": "Damage #7 · leak"},
        {"type": "alert", "id": 10, "label": "Alert #10 · water pressure"}
      ],
      "action_hint": "next step ≤ 24 words",
      "related_items": ["asset names"]
    }
  ]
}
```
All user-visible JSON strings MUST be English. No Chinese characters except unavoidable proper nouns.""")


def _system_prompt() -> str:
    return LOSS_ATTRIBUTION_SYSTEM_EN if _wants_english() else LOSS_ATTRIBUTION_SYSTEM_ZH


# 兼容旧引用
LOSS_ATTRIBUTION_SYSTEM = LOSS_ATTRIBUTION_SYSTEM_ZH


def _build_user_prompt(ctx: dict) -> str:
    if _wants_english():
        return (
            f"Attribute high-frequency equipment failures for period: {ctx['period_label']}.\n"
            "Respond in English only (no Chinese except proper nouns).\n\n"
            f"[Stats]\n{json.dumps(ctx['stats'], ensure_ascii=False, indent=2)}\n\n"
            f"[Damage tickets]\n{json.dumps(ctx['damages'], ensure_ascii=False, indent=2)}\n\n"
            f"[Open alerts]\n{json.dumps(ctx['alerts'], ensure_ascii=False, indent=2)}\n\n"
            f"[Maintenance]\n{json.dumps(ctx['maintenance'], ensure_ascii=False, indent=2)}\n\n"
            "Output ## Analysis process first, then a ```json attribution block."
        )
    return f"""请对以下设备设施报损与运维数据进行高频损坏归因分析（统计周期：{ctx["period_label"]}）。

【汇总】
{json.dumps(ctx["stats"], ensure_ascii=False, indent=2)}

【报损单】
{json.dumps(ctx["damages"], ensure_ascii=False, indent=2)}

【开放告警】
{json.dumps(ctx["alerts"], ensure_ascii=False, indent=2)}

【维保/维修记录】
{json.dumps(ctx["maintenance"], ensure_ascii=False, indent=2)}

请按系统提示先输出「## 分析过程」，再输出 ```json 归因结论。"""


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("模型返回为空")
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        return json.loads(fenced.group(1))
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        return json.loads(m.group(0))
    raise ValueError("未找到 JSON 归因结论")


def _extract_process(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    fenced = re.search(r"```json", raw, re.I)
    if fenced:
        head = raw[: fenced.start()].strip()
    else:
        m = re.search(r"\{\s*\"items\"\s*:", raw, re.S)
        head = raw[: m.start()].strip() if m else raw
    head = re.sub(r"^#+\s*分析过程\s*", "", head).strip()
    return head


def context_fingerprint(ctx: dict) -> str:
    """输入数据指纹：报损/告警/维保内容一致则哈希相同。"""
    payload = {
        "period": ctx.get("period"),
        "stats": ctx.get("stats"),
        "damages": ctx.get("damages"),
        "alerts": ctx.get("alerts"),
        "maintenance": ctx.get("maintenance"),
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _cache_setting_key(hotel_id: int, period: str, fingerprint: str) -> str:
    loc = "en" if _wants_english() else "zh"
    return f"{CACHE_KEY_PREFIX}{hotel_id}:{period}:{loc}:{fingerprint}"


def lookup_attribution_cache(db: Session, hotel_id: int, period: str, ctx: dict) -> dict | None:
    fp = context_fingerprint(ctx)
    row = db.query(AppSetting).filter_by(key=_cache_setting_key(hotel_id, period, fp)).first()
    if not row or not row.value_json:
        return None
    try:
        data = json.loads(row.value_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not data.get("items"):
        return None
    out = dict(data)
    out["source"] = "cache"
    out["from_cache"] = True
    out["fingerprint"] = fp
    cfg = load_llm_config(db)
    return _enrich_result(out, ctx, cfg)


def save_attribution_cache(db: Session, hotel_id: int, period: str, ctx: dict, result: dict) -> None:
    if result.get("source") != "llm" or not result.get("items"):
        return
    fp = context_fingerprint(ctx)
    key = _cache_setting_key(hotel_id, period, fp)
    payload = {
        "items": result.get("items"),
        "source": "llm",
        "model": result.get("model"),
        "provider": result.get("provider"),
        "provider_label": result.get("provider_label"),
        "narrative_html": result.get("narrative_html"),
        "actions": result.get("actions"),
        "fingerprint": fp,
        "cached_at": datetime.now().isoformat(timespec="seconds"),
    }
    row = db.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value_json = json.dumps(payload, ensure_ascii=False)
    else:
        db.add(AppSetting(key=key, value_json=json.dumps(payload, ensure_ascii=False)))
    loc = "en" if _wants_english() else "zh"
    prefix = f"{CACHE_KEY_PREFIX}{hotel_id}:{period}:{loc}:"
    for stale in db.query(AppSetting).filter(AppSetting.key.like(f"{prefix}%")).all():
        if stale.key != key:
            db.delete(stale)
    db.commit()


def _normalize_items(data: dict) -> list[dict]:
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("JSON 缺少 items 数组")
    out = []
    for it in items[:3]:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()
        if not title:
            continue
        count = int(it.get("count") or 1)
        count_label = str(it.get("count_label") or _t("{n} 起", n=count)).strip()
        root_cause = str(it.get("root_cause") or "").strip()
        mechanism = str(it.get("mechanism") or "").strip()
        evidence_raw = it.get("evidence") or it.get("evidence_points") or []
        if isinstance(evidence_raw, str):
            evidence_raw = [x.strip() for x in re.split(r"[\n;；]", evidence_raw) if x.strip()]
        evidence = [str(x).strip() for x in evidence_raw if str(x).strip()][:3]
        refs_raw = it.get("data_refs") or it.get("refs") or []
        data_refs = []
        for ref in refs_raw if isinstance(refs_raw, list) else [refs_raw]:
            if isinstance(ref, dict):
                label = str(ref.get("label") or "").strip()
                rid = int(ref.get("id") or 0)
                rtype = str(ref.get("type") or "").strip().lower()
                if not label and rid:
                    label = f"{rtype or '记录'}#{rid}"
                if label or rid:
                    data_refs.append({"type": rtype, "id": rid, "label": label})
                continue
            s = str(ref or "").strip()
            if not s:
                continue
            parsed = {"type": "", "id": 0, "label": s}
            for pat, rtype, prefix in (
                (r"报损#(\d+)", "damage", "报损"),
                (r"告警#(\d+)", "alert", "告警"),
                (r"(?:维保|维修)#(\d+)", "maintenance", "维保"),
            ):
                m = re.search(pat, s)
                if m:
                    parsed = {"type": rtype, "id": int(m.group(1)), "label": s}
                    break
            data_refs.append(parsed)
        data_refs = data_refs[:4]
        if not data_refs and it.get("related_items"):
            for name in it.get("related_items") or []:
                label = str(name).strip()
                if label:
                    data_refs.append({"type": "", "id": 0, "label": label})
            data_refs = data_refs[:4]
        action_hint = str(it.get("action_hint") or "").strip()
        legacy_desc = str(it.get("description") or "").strip()
        if not evidence and legacy_desc:
            evidence = [legacy_desc[:80]]
        priority = str(it.get("priority") or "mid").lower()
        if priority not in ("high", "mid", "low"):
            priority = "mid"
        out.append(
            {
                "title": title,
                "count": count_label,
                "root_cause": root_cause,
                "mechanism": mechanism,
                "evidence": evidence,
                "data_refs": data_refs,
                "action_hint": action_hint,
                "description": legacy_desc or (evidence[0] if evidence else root_cause),
                "priority": priority,
                "related_items": it.get("related_items") or [],
            }
        )
    if not out:
        raise ValueError("未解析到有效归因条目")
    return out


def _rule_fallback(ctx: dict) -> list[dict]:
    """关键词 + 物品名聚合的规则兜底。"""
    groups: dict[str, dict] = {}
    keyword_roots = [
        (r"漏水|渗水|水压|leak|seal|water", _t("水路密封件老化或水压波动")),
        (r"受潮|湿度|霉变|moisture|humidity", _t("仓储或环境湿度管控不足")),
        (r"撕裂|破损|开裂|crack|tear|break", _t("高使用强度导致材料疲劳")),
        (r"不通电|电路|功率|electric|power", _t("电气部件老化或异常用电")),
        (r"电量|电池|门锁|battery|lock", _t("电池寿命到期或批量更换滞后")),
    ]

    def bump(key: str, title: str, desc: str, fee: float = 0):
        g = groups.setdefault(key, {"title": title, "count": 0, "fee": 0.0, "descs": []})
        g["count"] += 1
        g["fee"] += fee
        if desc and desc not in g["descs"]:
            g["descs"].append(desc)

    for d in ctx.get("damages") or []:
        title = str(d.get("item_name") or _t("设备报损")).strip()
        if _wants_english() and _has_cjk(title):
            title = _t(title) if _t(title) != title else _t("设备报损")
        desc = str(d.get("description") or d.get("note") or "").strip()
        key = title.lower()
        bump(key, title, desc, float(d.get("fee") or 0))

    for a in ctx.get("alerts") or []:
        title = str(a.get("asset_name") or a.get("message") or _t("设备告警"))[:40]
        if _wants_english() and _has_cjk(title):
            title = _t(title) if _t(title) != title else _t("设备告警")
        desc = str(a.get("message") or "").strip()
        key = f"alert-{title.lower()}"
        bump(key, title, desc)

    ranked = sorted(groups.values(), key=lambda g: (-g["count"], -g["fee"]))
    items = []
    for g in ranked[:3]:
        blob = " ".join(g["descs"])
        root = _t("需结合现场复核确认")
        for pat, reason in keyword_roots:
            if re.search(pat, blob, re.I):
                root = reason
                break
        pri = "high" if g["count"] >= 2 or g["fee"] >= 500 else "mid"
        items.append(
            {
                "title": g["title"],
                "count": _t("{n} 起", n=g["count"]),
                "root_cause": root,
                "mechanism": _t("需结合现场复核确认机理"),
                "evidence": [d[:60] for d in g["descs"][:2]] or [_t("累计关联 {n} 条记录", n=g["count"])],
                "data_refs": [{"type": "", "id": 0, "label": g["title"]}],
                "action_hint": _t("建议安排现场核查并更新维保计划"),
                "description": (g["descs"][0] if g["descs"] else _t("累计费用约 ¥{n}", n=f"{g['fee']:,.0f}"))[:80],
                "priority": pri,
                "related_items": [g["title"]],
            }
        )
    return items


def _escape_html(s: str) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _format_loss_narrative_html(items: list[dict], stats: dict | None = None) -> str:
    """事实 / 建议双栏，对齐积分倍率等 AI 原生排版。"""
    facts: list[str] = []
    suggestions: list[str] = []
    st = stats or {}
    if st:
        facts.append(
            _t(
                "本期报损 <strong>{d}</strong> 条，开放告警 <strong>{a}</strong> 条，已完成维保 <strong>{m}</strong> 条",
                d=int(st.get("damage_count") or 0),
                a=int(st.get("alert_count") or 0),
                m=int(st.get("maintenance_count") or 0),
            )
        )
    for it in items[:3]:
        title = _escape_html(str(it.get("title") or "—"))
        count = _escape_html(str(it.get("count") or ""))
        root = _escape_html(str(it.get("root_cause") or ""))
        line = _t("「{title}」{count}", title=title, count=count)
        if root:
            sep = ": " if _wants_english() else "："
            line = f"{line}{sep}{root}"
        facts.append(line)
        hint = str(it.get("action_hint") or "").strip()
        if hint:
            suggestions.append(_escape_html(hint))
        else:
            suggestions.append(_t("针对「{title}」安排现场复核，并更新维保计划", title=title))
    if not suggestions:
        suggestions.append(_t("优先处理高优先归因项，并在低入住时段安排预防性维保。"))
    fact_lis = "".join(f"<li>{x}</li>" for x in facts if x)
    sug_lis = "".join(f"<li>{x}</li>" for x in suggestions if x)
    if not fact_lis and not sug_lis:
        return ""
    parts = ['<div class="ai-insight">']
    if fact_lis:
        parts.append(
            '<section class="ai-insight-sec fact">'
            f'<div class="ai-insight-h">{_escape_html(_t("事实"))}</div>'
            f"<ul>{fact_lis}</ul></section>"
        )
    if sug_lis:
        parts.append(
            '<section class="ai-insight-sec sug">'
            f'<div class="ai-insight-h">{_escape_html(_t("建议"))}</div>'
            f"<ul>{sug_lis}</ul></section>"
        )
    parts.append("</div>")
    return "".join(parts)


def _default_actions(items: list[dict]) -> list[dict]:
    acts: list[dict] = []
    high = next((i for i in items if str(i.get("priority") or "") == "high"), None)
    if high:
        theme = str(high.get("title") or _t("高优先项"))[:40]
        acts.append(
            {
                "id": "go_inventory",
                "action_type": "open_path",
                "action_label": _t("去资产清单"),
                "title": _t("评估「{title}」", title=theme),
                "body": str(high.get("action_hint") or _t("从资产清单核对健康分与维保履历。"))[:80],
                "path": "/c8-assets/inventory-2",
            }
        )
    acts.append(
        {
            "id": "go_tracking",
            "action_type": "open_path",
            "action_label": _t("维修追踪"),
            "title": _t("核对报损与告警"),
            "body": _t("到维修追踪查看本期报损单与开放告警，并安排维保窗口。"),
            "path": "/c8-assets/tracking",
        }
    )
    return acts[:4]


def _items_have_cjk(items: list[dict]) -> bool:
    for it in items:
        for key in ("title", "root_cause", "mechanism", "action_hint", "count"):
            if _has_cjk(str(it.get(key) or "")):
                return True
        for ev in it.get("evidence") or []:
            if _has_cjk(str(ev)):
                return True
    return False


def _enrich_result(out: dict, ctx: dict | None = None, cfg: dict | None = None) -> dict:
    items = out.get("items") if isinstance(out.get("items"), list) else []
    stats = (ctx or {}).get("stats") if isinstance(ctx, dict) else None
    # 始终按当前 Locale 重建叙事与动作（避免中文缓存串到 EN）
    out["narrative_html"] = _format_loss_narrative_html(items, stats)
    out["actions"] = _default_actions(items)
    out.pop("raw", None)
    out.pop("process", None)
    if cfg and not out.get("provider_label"):
        out.update(llm_identity(cfg, {"model": out.get("model"), "provider": out.get("provider")}))
    return out


def _finalize(
    items: list[dict],
    source: str,
    model: str | None = None,
    llm_error: str | None = None,
    process: str | None = None,
    raw: str | None = None,
    ctx: dict | None = None,
    cfg: dict | None = None,
    res: dict | None = None,
) -> dict:
    out = {"items": items, "source": source}
    if llm_error:
        out["llm_error"] = llm_error
    if process:
        out["process"] = process
    if raw:
        out["raw"] = raw
    if cfg:
        out.update(llm_identity(cfg, res or ({"model": model} if model else None)))
    elif model:
        out["model"] = model
    return _enrich_result(out, ctx, cfg)


def generate_loss_attribution(db: Session, hotel_id: int, period: str = "12", *, force: bool = False) -> dict:
    ctx = load_loss_attribution_context(db, hotel_id, period)
    cfg = load_llm_config(db)
    if not ctx["stats"]["damage_count"] and not ctx["stats"]["alert_count"]:
        return _finalize([], "empty", cfg.get("model"), ctx=ctx, cfg=cfg)

    if not force:
        cached = lookup_attribution_cache(db, hotel_id, period, ctx)
        if cached:
            return cached

    try:
        res = llm_chat(
            db,
            [{"role": "user", "content": _build_user_prompt(ctx)}],
            extra_system=_system_prompt(),
        )
        parsed = _normalize_items(_extract_json(res.get("content") or ""))
        if _wants_english() and _items_have_cjk(parsed):
            return _finalize(
                [],
                "unavailable",
                res.get("model"),
                _t("模型返回含中文，未当作 AI 结论"),
                ctx=ctx,
                cfg=cfg,
                res=res,
            )
        full = res.get("content") or ""
        result = _finalize(
            parsed,
            "llm",
            res.get("model"),
            process=_extract_process(full),
            raw=full,
            ctx=ctx,
            cfg=cfg,
            res=res,
        )
        save_attribution_cache(db, hotel_id, period, ctx, result)
        return result
    except HTTPException as e:
        err = str(e.detail) if hasattr(e, "detail") else str(e)
        return _finalize([], "unavailable", cfg.get("model"), err, ctx=ctx, cfg=cfg)
    except Exception as e:
        return _finalize([], "unavailable", cfg.get("model"), str(e)[:200], ctx=ctx, cfg=cfg)


def stream_loss_attribution(
    db: Session,
    hotel_id: int,
    period: str = "12",
    *,
    force: bool = False,
) -> Iterator[dict]:
    ctx = load_loss_attribution_context(db, hotel_id, period)
    cfg = load_llm_config(db)
    model = cfg.get("model")

    if not ctx["stats"]["damage_count"] and not ctx["stats"]["alert_count"]:
        yield {"type": "done", "data": _finalize([], "empty", model, ctx=ctx, cfg=cfg)}
        return

    if not force:
        cached = lookup_attribution_cache(db, hotel_id, period, ctx)
        if cached:
            yield {"type": "cached", "data": cached}
            yield {"type": "done", "data": cached}
            return

    try:
        full = ""
        # EN 下不流式中文 token，整段生成后再回写
        stream_tokens = not _wants_english()
        for chunk in chat_stream(
            db,
            [{"role": "user", "content": _build_user_prompt(ctx)}],
            extra_system=_system_prompt(),
        ):
            full += chunk
            if stream_tokens:
                yield {"type": "token", "content": chunk}

        parsed = _normalize_items(_extract_json(full))
        if _wants_english() and _items_have_cjk(parsed):
            yield {
                "type": "done",
                "data": _finalize(
                    [],
                    "unavailable",
                    model,
                    _t("模型返回含中文，未当作 AI 结论"),
                    ctx=ctx,
                    cfg=cfg,
                ),
            }
            return
        result = _finalize(
            parsed,
            "llm",
            model,
            process=_extract_process(full),
            raw=full,
            ctx=ctx,
            cfg=cfg,
        )
        save_attribution_cache(db, hotel_id, period, ctx, result)
        yield {"type": "done", "data": result}
    except HTTPException as e:
        err = str(e.detail) if hasattr(e, "detail") else str(e)
        yield {"type": "done", "data": _finalize([], "unavailable", model, err, ctx=ctx, cfg=cfg)}
    except Exception as e:
        yield {"type": "done", "data": _finalize([], "unavailable", cfg.get("model"), str(e)[:200], ctx=ctx, cfg=cfg)}
