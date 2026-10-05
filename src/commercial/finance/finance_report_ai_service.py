# SPDX-License-Identifier: BUSL-1.1
"""财务报表 · AI 解读（报告特化提示词 + 4 段 JSON + Harness 确认闸）。"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.locale_llm import (
    compose_system,
    run_locale_llm_json,
)
from commercial.ai_core.locale_llm import (
    locale_text as _core_locale_text,
)
from commercial.ai_core.locale_llm import (
    wants_en as _wants_en,
)
from infra.branding import brand_text
from infra.i18n import t
from models import (
    AiActionConfirmation,
    AiReportInterpretation,
    NightAuditException,
    ProfitInsight,
)

PROMPT_VERSION = "report-ai-v3"
ACTION_KINDS = {
    "draft_reco",
    "draft_receivable",
    "mark_anomaly",
    "submit_close",
    "draft_close",
    "escalate",
    "export",
}
MODULE_SET = {"finance", "revenue", "marketing", "ops"}
SEVERITY_SET = {"info", "warn", "critical"}

# 快照 / 文案中的英文字段 → 中文（解读展示与喂给模型均用中文）
FIELD_CN: dict[str, str] = {
    "total_revenue": "总营收",
    "room_revenue": "客房收入",
    "rooms_revenue": "客房收入",
    "other_revenue": "其他收入",
    "revenue": "营收",
    "revenue_source": "营收口径",
    "occ_pct": "出租率",
    "occ_compare": "出租率对比",
    "occ_delta": "出租率变动",
    "adr": "平均房价",
    "adr_compare": "平均房价对比",
    "adr_delta": "平均房价变动",
    "revpar": "每房收益",
    "revpar_compare": "每房收益对比",
    "revpar_delta": "每房收益变动",
    "room_nights": "间夜数",
    "available": "可用房数",
    "occupied": "在住房数",
    "pending_arrival": "待抵房数",
    "cancelled": "取消数",
    "comps": "免费房数",
    "gop": "经营毛利",
    "gop_pct": "毛利率",
    "by_dept": "部门收入",
    "payments_by_method": "收银方式",
    "room_types": "房型明细",
    "mis_summary": "MIS摘要",
    "ar_aging": "应收账龄",
    "anomalies": "异常线索",
    "channels": "渠道明细",
    "series": "趋势序列",
    "items": "明细",
    "customers": "客户明细",
    "totals": "合计",
    "accounts": "科目",
    "debit_total": "借方合计",
    "credit_total": "贷方合计",
    "balanced": "是否平衡",
    "operating_inflow": "经营流入",
    "net_observable": "可观测净额",
    "ar_balance": "应收余额",
    "ap_balance": "应付余额",
    "ar_0_30": "应收0-30天",
    "net": "净额",
    "tax_rate": "税率",
    "taxable_sales": "应税销售额",
    "output_tax": "销项税额",
    "gross": "价税合计",
    "empty_reason": "空表原因",
    "exceptions": "异常列表",
    "note": "说明",
    "report_type": "报告类型",
    "report_code": "报告编码",
    "period": "期间",
    "currency": "币种",
    "tenant_id": "门店",
    "generated_at": "生成时间",
    "compare": "对比口径",
    "data": "数据",
    "avail": "可用",
    "name": "名称",
    "date": "日期",
    "dept": "部门",
    "metric": "指标",
    "today": "本期",
    "ly": "同期",
    "yoy": "同比",
    "channel": "渠道",
    "nights": "间夜",
    "commission": "佣金",
    "share": "占比",
    "title": "标题",
    "amount": "金额",
    "status": "状态",
    "severity": "严重度",
    "code": "编码",
    "biz_date": "营业日",
}


def _localize_field_key(key: str) -> str:
    k = str(key or "")
    if _wants_en():
        return k
    return FIELD_CN.get(k) or FIELD_CN.get(k.lower()) or k


def _localize_snapshot(obj: Any) -> Any:
    """把喂给模型的快照键名改为中文，降低原文抄字段名的概率。"""
    if isinstance(obj, dict):
        return {_localize_field_key(k): _localize_snapshot(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_localize_snapshot(x) for x in obj]
    return obj


def _localize_cn_text(text: Any) -> str:
    """文案后处理：中文 Locale 下把残留英文字段名换成中文。"""
    s = str(text or "")
    if not s or _wants_en():
        return s
    for en, cn in sorted(FIELD_CN.items(), key=lambda kv: -len(kv[0])):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", en):
            continue
        s = re.sub(rf"\b{re.escape(en)}\b", cn, s, flags=re.I)
    return s


def _locale_text(raw: Any, fallback: str, n: int = 160) -> str:
    return _core_locale_text(raw, fallback, n, polish=_localize_cn_text)


# code → 对外 report_type / 维度说明 / Layer B / 允许 actions
REPORT_PROFILES: dict[str, dict[str, Any]] = {
    "daily_operations": {
        "report_type": "每日运营",
        "dimensions": "出租率 / 平均房价 / 每房收益 / 入离 / 当日营收 / 房型运营",
        "layer_b": """【报告类型】每日运营报告
【专属字段集】（严禁超出；叙述时一律用中文指标名）
- 运营：出租率、平均房价、每房收益、间夜数、总营收
- 房态：可用房数、在住房数、待抵房数、取消数
- 房型：房型明细（名称、可用、出租率、平均房价、每房收益）
【允许的 actions】draft_reco, mark_anomaly, export
【禁区】不输出损益/资产负债表；不替人定价/结账""",
        "actions": ["draft_reco", "mark_anomaly", "export"],
    },
    "manager_flash": {
        "report_type": "经理快讯",
        "dimensions": "房收入 / 其他 / 可用房 / 已占房 / 取消 / 收银拆分",
        "layer_b": """【报告类型】经理快讯
【专属字段集】（叙述时一律用中文指标名，禁止写出英文蛇形字段名）
- 收入：总营收、客房收入、其他收入
- 房态：可用房数、在住房数、待抵房数、取消数、免费房数
- 收银：收银方式
【允许的 actions】draft_reco, mark_anomaly, export
【禁区】不输出完整 USALI 损益；不替人结账""",
        "actions": ["draft_reco", "mark_anomaly", "export"],
    },
    "mis": {
        "report_type": "MIS报告",
        "dimensions": "出租率 / 平均房价 / 每房收益 / 收入 / 毛利 / 应收 / 异常",
        "layer_b": """【报告类型】MIS 报告（月度经营汇总）
【专属字段集】（叙述时一律用中文指标名）
- 收入类：总营收、客房收入、其他收入
- 指标类：出租率、平均房价、每房收益、毛利率（未知则标未知）
- 异常类：异常线索
- 应收类：应收账龄
【允许的 actions】draft_reco, mark_anomaly, export
【禁区】不输出损益/资产负债表字段；不替人定价/结账/催收""",
        "actions": ["draft_reco", "mark_anomaly", "export"],
    },
    "revenue_summary": {
        "report_type": "收入汇总",
        "dimensions": "按部门收入结构",
        "layer_b": """【报告类型】收入汇总
【专属字段集】客房收入、其他收入、总营收、部门收入（叙述用中文）
【允许的 actions】export, escalate
【禁区】不输出出租率/平均房价；不替人改价""",
        "actions": ["export", "escalate"],
    },
    "channel_sales": {
        "report_type": "渠道销售",
        "dimensions": "OTA / 直销 / 会员 / 协议 + 佣金",
        "layer_b": """【报告类型】渠道销售分析
【专属字段集】渠道明细（渠道、营收、间夜、佣金、占比）
【允许的 actions】draft_reco, export, escalate
【禁区】不输出损益；不替人勾选渠道协议""",
        "actions": ["draft_reco", "export", "escalate"],
    },
    "adr_revpar_trend": {
        "report_type": "房价收益趋势",
        "dimensions": "时序 出租率 / 平均房价 / 每房收益 / 营收",
        "layer_b": """【报告类型】平均房价/每房收益趋势
【专属字段集】趋势序列（日期、出租率、平均房价、每房收益、营收）
【允许的 actions】draft_reco, export
【禁区】不输出资产负债表；不替人定价""",
        "actions": ["draft_reco", "export"],
    },
    "p_l": {
        "report_type": "损益表",
        "dimensions": "USALI 收入侧（成本未接入则标明）",
        "layer_b": """【报告类型】USALI 损益表
【专属字段集】客房收入、其他收入、总营收、经营毛利（可能为空）、说明
【允许的 actions】submit_close, mark_anomaly, escalate
【禁区】不输出平均房价/出租率/每房收益；不替人平账/结账""",
        "actions": ["submit_close", "mark_anomaly", "escalate"],
    },
    "balance_sheet": {
        "report_type": "资产负债表",
        "dimensions": "资产/负债/权益（若未接入则空）",
        "layer_b": """【报告类型】资产负债表
【专属字段集】明细 或 空表原因
【允许的 actions】export, escalate
【禁区】不输出平均房价/出租率；不替人调账""",
        "actions": ["export", "escalate"],
    },
    "cash_flow": {
        "report_type": "现金流量表",
        "dimensions": "可观测收款净额",
        "layer_b": """【报告类型】现金流量表（可观测收款）
【专属字段集】经营流入、可观测净额、说明
【允许的 actions】export, escalate
【禁区】不输出平均房价；不替人划款""",
        "actions": ["export", "escalate"],
    },
    "trial_balance": {
        "report_type": "试算平衡表",
        "dimensions": "借贷科目合计 / 是否平衡",
        "layer_b": """【报告类型】试算平衡表
【专属字段集】科目、借方合计、贷方合计、是否平衡
【允许的 actions】mark_anomaly, escalate, export
【禁区】不输出营销指标；不替人平账""",
        "actions": ["mark_anomaly", "escalate", "export"],
    },
    "ar_aging": {
        "report_type": "账龄分析",
        "dimensions": "客户 × 账龄桶",
        "layer_b": """【报告类型】账龄分析
【专属字段集】客户明细、合计
【允许的 actions】draft_receivable, escalate, export
【禁区】不输出收入指标；不替人发催收短信/核销""",
        "actions": ["draft_receivable", "escalate", "export"],
    },
    "ar_ap_summary": {
        "report_type": "应收应付汇总",
        "dimensions": "应收/应付余额与净额",
        "layer_b": """【报告类型】应收应付汇总
【专属字段集】应收余额、应付余额、净额
【允许的 actions】draft_receivable, escalate, export
【禁区】不输出出租率；不替人付款""",
        "actions": ["draft_receivable", "escalate", "export"],
    },
    "vat_summary": {
        "report_type": "增值税汇总",
        "dimensions": "开票税额 / 税率",
        "layer_b": """【报告类型】增值税汇总
【专属字段集】税率、应税销售额、销项税额、价税合计、空表原因?
【允许的 actions】export, escalate
【禁区】不替人申报/开发票""",
        "actions": ["export", "escalate"],
    },
    "tax_exempt": {
        "report_type": "免税收入",
        "dimensions": "免税收入明细",
        "layer_b": """【报告类型】免税收入
【专属字段集】明细、合计、空表原因?
【允许的 actions】export, escalate
【禁区】不替人申报""",
        "actions": ["export", "escalate"],
    },
    "night_daily": {
        "report_type": "夜审日报",
        "dimensions": "营业日营收 / 间夜 / 异常数",
        "layer_b": """【报告类型】夜审日报
【专属字段集】明细（营业日、营收、间夜、异常）
【允许的 actions】mark_anomaly, escalate, export
【禁区】不输出损益；不替人过账""",
        "actions": ["mark_anomaly", "escalate", "export"],
    },
    "night_exceptions": {
        "report_type": "夜审异常",
        "dimensions": "异常类型 × 严重度 × 状态",
        "layer_b": """【报告类型】夜审异常核查
【专属字段集】异常列表（营业日、编码、标题、严重度、状态）
【允许的 actions】mark_anomaly, escalate, draft_close
【禁区】不输出损益；不替人核销/调账""",
        "actions": ["mark_anomaly", "escalate", "draft_close"],
    },
}


def _layer_a(report_type: str, dimensions: str) -> str:
    if _wants_en():
        return (
            brand_text("""You are the "{APP_NAME} PMS finance report assistant". Interpret ONLY the currently selected financial report.

Hard rules:
1. Use only fields in this report. Type: {report_type}. Dimensions: {dimensions}.
2. If evidence is missing, write "unknown / insufficient data". Never invent numbers.
3. Do not price, check out, or change books — insight and draft suggestions only.
4. Output strict JSON. No Markdown, chatter, or think blocks.
5. Limits: insight ≤ 120 chars; max 3 findings (≤ 80 each); max 3 suggestions (≤ 100 each).
6. Anything that could affect revenue/compliance/AR must be an action with confirm_required.
7. **All user-visible strings MUST be English** (insight, findings.title/evidence, suggestions.title/rationale, actions.title). Use English metric names: occupancy, ADR, RevPAR, total revenue, occupied rooms, arrivals pending. severity/module/kind/required_role stay English enums.

JSON schema:
{{
  "insight": "string (English)",
  "findings": [{{"title":"string (English)","evidence":"string (English)","severity":"info|warn|critical"}}],
  "suggestions": [{{"title":"string (English)","rationale":"string (English)","module":"finance|revenue|marketing|ops"}}],
  "actions": [{{
    "kind":"draft_receivable|mark_anomaly|draft_reco|submit_close|draft_close|escalate|export",
    "title":"string (English)",
    "payload":{{}},
    "required_role":"manager|gm|finance|revenue",
    "confirm_required": true,
    "goto":"string"
  }}]
}}
""")
            .replace("{report_type}", str(report_type))
            .replace("{dimensions}", str(dimensions))
        )
    return (
        brand_text("""你是「{APP_NAME} PMS 财务解读助手」。你的任务是基于**当前选中的财务报告**给出忠实于该报告视图维度的解读。

【铁律】（违反任何一条即输出错误）
1. 只解读当前报告本身的字段，绝不引入无关指标。
   - 当前报告类型：{report_type}
   - 当前报告维度：{dimensions}
2. 无证据写"未知/数据不足以判断"。禁止臆造数字。
3. 财务场景不替人定价、不替人结账、不替人改数——只做解读+起草建议。
4. 输出严格 JSON，不得夹 Markdown/闲聊/think 块。
5. 字数上限：insight ≤ 120 字；findings 最多 3 条，每条 ≤ 80 字；suggestions 最多 3 条，每条 ≤ 100 字。
6. 任何可能影响营收/合规/应收的操作，必须以 action 形式给出，**绝不自动执行**。
7. **全文必须使用简体中文**。insight / findings.title / findings.evidence / suggestions.title / suggestions.rationale / actions.title 中：
   - 禁止出现英文蛇形字段名（如 total_revenue、occupied、pending_arrival、occ_pct）；
   - 请改用中文指标名：总营收、在住房数、待抵房数、可用房数、出租率、平均房价、每房收益、客房收入等；
   - severity / module / kind / required_role 仍用英文枚举值（供系统解析），不要把枚举值写进中文句子里。

【输出 JSON Schema】
{{
  "insight": "string（中文）",
  "findings": [{{"title":"string（中文）","evidence":"string（中文）","severity":"info|warn|critical"}}],
  "suggestions": [{{"title":"string（中文）","rationale":"string（中文）","module":"finance|revenue|marketing|ops"}}],
  "actions": [{{
    "kind":"draft_receivable|mark_anomaly|draft_reco|submit_close|draft_close|escalate|export",
    "title":"string（中文）",
    "payload":{{}},
    "required_role":"manager|gm|finance|revenue",
    "confirm_required": true,
    "goto":"string"
  }}]
}}
""")
        .replace("{report_type}", str(report_type))
        .replace("{dimensions}", str(dimensions))
    )


def _layer_b_text(profile: dict[str, Any]) -> str:
    if not _wants_en():
        return str(profile.get("layer_b") or "")
    actions = ", ".join(profile.get("actions") or [])
    return (
        f"[Report type] {t(str(profile.get('report_type') or ''))}\n"
        "Use only snapshot fields. Write every user-visible string in English. "
        "Metric names: occupancy, ADR, RevPAR, total revenue, room revenue, occupied rooms, "
        "available rooms, arrivals pending, cancellations, GOP, AR aging.\n"
        f"Allowed actions: {actions}."
    )


def _default_goto(kind: str, report_code: str) -> str:
    if kind == "draft_reco":
        return "/pricing?from=finance-report"
    if kind in ("draft_receivable",):
        return "/c9-finance/ar-ap"
    if kind in ("mark_anomaly", "draft_close") and report_code.startswith("night"):
        return "/c9-finance/night-audit"
    if kind == "export":
        return ""
    if kind == "escalate":
        return "/c9-finance/daily-operations"
    if kind == "submit_close":
        return "/c9-finance/daily-operations"
    return "/c9-finance/daily-operations"


def _normalize_result(raw: dict[str, Any], report_code: str, allowed_actions: list[str]) -> dict[str, Any]:
    insight = _locale_text(raw.get("insight"), "数据不足以形成一句话解读。", 160)
    findings = []
    for it in (raw.get("findings") or [])[:3]:
        if not isinstance(it, dict):
            continue
        sev = str(it.get("severity") or "info").lower()
        if sev not in SEVERITY_SET:
            sev = "info"
        findings.append(
            {
                "title": _locale_text(it.get("title"), "需关注的指标变动", 40),
                "evidence": _locale_text(it.get("evidence"), "详见本期报表数据", 100),
                "severity": sev,
            }
        )
    suggestions = []
    for it in (raw.get("suggestions") or [])[:3]:
        if not isinstance(it, dict):
            continue
        mod = str(it.get("module") or "finance").lower()
        if mod not in MODULE_SET:
            mod = "finance"
        suggestions.append(
            {
                "title": _locale_text(it.get("title"), "建议结合本期指标复核", 40),
                "rationale": _locale_text(it.get("rationale") or it.get("reason"), "详见本期报表数据", 120),
                "module": mod,
            }
        )
    actions = []
    for it in raw.get("actions") or []:
        if not isinstance(it, dict):
            continue
        kind = str(it.get("kind") or "").strip()
        if kind not in ACTION_KINDS or kind not in allowed_actions:
            continue
        payload = it.get("payload") if isinstance(it.get("payload"), dict) else {}
        role = str(it.get("required_role") or "manager")
        if role not in ("manager", "gm", "finance", "revenue"):
            role = "manager"
        confirm = bool(it.get("confirm_required", True))
        if kind != "export":
            confirm = True
        actions.append(
            {
                "kind": kind,
                "title": _locale_text(it.get("title") or kind, "请根据报表数据采取后续动作", 60),
                "payload": payload,
                "required_role": role,
                "confirm_required": confirm,
                "goto": str(it.get("goto") or _default_goto(kind, report_code)),
                "status": "pending",
            }
        )
    return {
        "insight": insight,
        "findings": findings,
        "suggestions": suggestions,
        "actions": actions,
    }


def _failed_result(msg: str = "解读失败") -> dict[str, Any]:
    return {"insight": t(msg), "findings": [], "suggestions": [], "actions": []}


def _hash_snapshot(obj: dict) -> str:
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _table_rows(report: dict, title_substr: str = "") -> list[dict]:
    out = []
    for sec in report.get("sections") or []:
        if sec.get("type") != "table":
            continue
        if title_substr and title_substr not in str(sec.get("title") or ""):
            continue
        for row in sec.get("rows") or []:
            if isinstance(row, dict):
                out.append({k: v for k, v in row.items() if not str(k).startswith("_")})
    return out


def _stats_map(report: dict) -> dict[str, Any]:
    m = {}
    for sec in report.get("sections") or []:
        if sec.get("type") != "stats":
            continue
        for it in sec.get("items") or []:
            lab = str(it.get("lab") or "")
            m[lab] = f"{it.get('v') or ''}{it.get('small') or ''}".strip()
    return m


def build_typed_snapshot(
    db: Session,
    hotel_id: int,
    code: str,
    report: dict,
    *,
    compare: str = "yoy",
) -> dict[str, Any]:
    """按报告类型裁剪字段，避免混入无关指标。"""
    profile = REPORT_PROFILES.get(code) or {
        "report_type": code,
        "dimensions": "通用",
        "layer_b": f"【报告类型】{code}\n仅解读快照中出现的字段。",
        "actions": ["export", "escalate"],
    }
    snap = report.get("snapshot") or {}
    period = report.get("period_label") or ""
    base = {
        "report_type": profile["report_type"],
        "report_code": code,
        "period": period,
        "currency": "CNY",
        "tenant_id": f"hotel_{hotel_id}",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "compare": report.get("compare_label") or compare,
    }

    if code in ("daily_operations", "manager_flash", "mis"):
        stats = _stats_map(report)
        rooms = snap.get("rooms") or {}
        data = {
            "total_revenue": snap.get("revenue"),
            "revenue_source": snap.get("revenue_source"),
            "available": rooms.get("total"),
            "occupied": rooms.get("occupied"),
            "pending_arrival": stats.get("已预订未到"),
            "cancelled": stats.get("取消 / 应到未到") or stats.get("取消"),
            "comps": stats.get("零房价单") or stats.get("免费房"),
        }
        # KPI 行
        for row in _table_rows(report, "关键指标"):
            metric = str(row.get("metric") or "")
            if "OCC" in metric:
                data["occ_pct"] = row.get("today")
                data["occ_compare"] = row.get("ly")
                data["occ_delta"] = row.get("yoy")
            elif "ADR" in metric:
                data["adr"] = row.get("today")
                data["adr_compare"] = row.get("ly")
                data["adr_delta"] = row.get("yoy")
            elif "RevPAR" in metric:
                data["revpar"] = row.get("today")
                data["revpar_compare"] = row.get("ly")
                data["revpar_delta"] = row.get("yoy")
            elif "GOP" in metric:
                data["gop_pct"] = row.get("today")
        # 收入拆分
        income = _table_rows(report, "收入")
        if income:
            data["by_dept"] = income
            for r in income:
                dept = str(r.get("dept") or "")
                if "客房" in dept:
                    data["room_revenue"] = r.get("revenue")
                elif "其他" in dept:
                    data["other_revenue"] = r.get("revenue")
        # 收银
        pays = _table_rows(report, "收银")
        if pays:
            data["payments_by_method"] = pays
        # 房型
        rts = _table_rows(report, "房型")
        if rts:
            data["room_types"] = rts
        # MIS 摘要
        if code == "mis":
            for sec in report.get("sections") or []:
                if sec.get("type") == "stats" and "MIS" in str(sec.get("title") or ""):
                    data["mis_summary"] = [{"lab": it.get("lab"), "v": it.get("v")} for it in (sec.get("items") or [])]
        # 异常线索 / 应收（仅 MIS 允许）
        if code == "mis":
            try:
                from finance.ar_ap_service import list_workspace

                ws = list_workspace(db, hotel_id)
                data["ar_aging"] = ws.get("aging") or {}
            except Exception:
                data["ar_aging"] = {}
            anoms = (
                db.query(ProfitInsight)
                .filter_by(hotel_id=hotel_id, status="open")
                .order_by(ProfitInsight.id.desc())
                .limit(5)
                .all()
            )
            data["anomalies"] = [
                {"id": f"pi-{a.id}", "title": a.title, "amount": float(a.impact_amount or 0)} for a in anoms
            ]
        base["data"] = data
        return base

    if code == "channel_sales":
        base["data"] = {"channels": snap.get("channels") or _table_rows(report), "total": snap.get("total")}
        return base

    if code == "adr_revpar_trend":
        series = []
        for r in _table_rows(report):
            series.append(
                {
                    "date": r.get("date"),
                    "occ_pct": r.get("occ"),
                    "adr": r.get("adr"),
                    "revpar": r.get("revpar"),
                    "revenue": r.get("revenue"),
                }
            )
        base["data"] = {"series": series}
        return base

    if code in ("revenue_summary", "p_l"):
        rows = _table_rows(report)
        base["data"] = {
            "items": rows,
            "total_revenue": snap.get("revenue"),
            "gop": snap.get("gop"),
            "note": "成本科目未接入时 gop 为 null",
        }
        return base

    if code == "trial_balance":
        base["data"] = {
            "accounts": _table_rows(report),
            "debit_total": snap.get("debit"),
            "credit_total": snap.get("credit"),
            "balanced": snap.get("balanced"),
        }
        return base

    if code == "balance_sheet":
        rows = _table_rows(report)
        base["data"] = {"items": rows, "empty_reason": None if rows else "总账未接入"}
        return base

    if code == "cash_flow":
        base["data"] = {
            "items": _table_rows(report),
            "operating_inflow": snap.get("net"),
            "net_observable": snap.get("net"),
            "note": "仅可观测收款",
        }
        return base

    if code == "ar_aging":
        rows = [r for r in _table_rows(report) if r.get("customer") != "合计"]
        base["data"] = {"customers": rows, "totals": snap.get("aging") or snap}
        return base

    if code == "ar_ap_summary":
        base["data"] = {
            "ar_balance": snap.get("ar"),
            "ap_balance": snap.get("ap"),
            "items": _table_rows(report),
            "net": (float(snap.get("ar") or 0) - float(snap.get("ap") or 0)),
        }
        return base

    if code == "vat_summary":
        rows = _table_rows(report)
        base["data"] = {
            "tax_rate": snap.get("rate"),
            "output_tax": snap.get("vat"),
            "gross": snap.get("gross"),
            "items": rows,
            "empty_reason": None if rows else "本期无开票记录",
        }
        return base

    if code == "tax_exempt":
        rows = _table_rows(report)
        base["data"] = {
            "items": rows,
            "total": snap.get("exempt") or 0,
            "empty_reason": None if rows else "无免税标记数据",
        }
        return base

    if code == "night_daily":
        base["data"] = {"rows": _table_rows(report)}
        return base

    if code == "night_exceptions":
        base["data"] = {"exceptions": _table_rows(report)}
        return base

    base["data"] = {
        "snapshot": snap,
        "sections_brief": [{"title": s.get("title"), "type": s.get("type")} for s in (report.get("sections") or [])],
    }
    return base


def interpret_report(
    db: Session,
    hotel_id: int,
    code: str,
    *,
    period: str = "month",
    start: Optional[str] = None,
    end: Optional[str] = None,
    compare: str = "yoy",
    operator: str = "ai_agent",
) -> dict[str, Any]:
    from commercial.ai_core.llm_service import llm_identity, load_llm_config
    from finance.finance_reports_service import build_report

    report = build_report(db, hotel_id, code, period=period, start=start, end=end, compare=compare)
    profile = REPORT_PROFILES.get(code) or {
        "report_type": code,
        "dimensions": "通用",
        "layer_b": f"【报告类型】{code}\n仅解读快照字段。",
        "actions": list(ACTION_KINDS),
    }
    typed = build_typed_snapshot(db, hotel_id, code, report, compare=compare)
    typed_for_llm = _localize_snapshot(typed)
    system = compose_system(
        _layer_a(t(str(profile["report_type"])), str(profile["dimensions"])),
        _layer_b_text(profile),
    )
    snap_blob = json.dumps(typed_for_llm, ensure_ascii=False, default=str)
    if _wants_en():
        user = "Output JSON only from this report snapshot. All narrative strings MUST be English:\n" + snap_blob
        retry_user = (
            "Previous output was truncated. Re-output COMPLETE JSON only "
            "(insight/findings/suggestions/actions); findings≤2, suggestions≤2, actions≤1; "
            "all narrative strings in English.\nSnapshot:\n" + snap_blob[:4000]
        )
    else:
        user = "请基于以下报告专属快照输出 JSON（不得夹杂其它文字；叙述指标必须用中文名）：\n" + snap_blob
        retry_user = (
            "上次输出被截断。请重新输出**完整** JSON，字段仅 insight/findings/suggestions/actions；"
            "findings≤2、suggestions≤2、actions≤1；字符串勿含未转义引号；指标名必须中文。\n快照：\n" + snap_blob[:4000]
        )

    cfg = load_llm_config(db)
    from extensions.llm.facade import resolve_model_name

    model_name = resolve_model_name(cfg)
    raw_text = ""
    status = "ready"
    allowed = profile.get("actions") or list(ACTION_KINDS)
    llm_opts = {"temperature": 0.2, "top_p": 0.85, "max_tokens": 2048, "think": False}
    call = run_locale_llm_json(
        db,
        system=system,
        user=user,
        retry_user=retry_user,
        overrides=llm_opts,
        retry_overrides={**llm_opts, "max_tokens": 1200},
    )
    raw_text = call.raw
    model_name = call.model or model_name
    if call.error and not call.parsed:
        status = "failed"
        result = _failed_result("解读失败，请稍后重试或缩短报告期间后再试。")
    else:
        try:
            parsed = call.parsed if call.parsed else {}
            if not parsed.get("insight") and not parsed.get("findings"):
                raise ValueError("empty")
            result = _normalize_result(parsed, code, allowed)
        except Exception:
            status = "failed"
            result = _failed_result("解读失败，请稍后重试或缩短报告期间后再试。")

    row = AiReportInterpretation(
        hotel_id=hotel_id,
        report_code=code,
        report_type=t(str(profile["report_type"])),
        period_start=date.fromisoformat(report["period_start"]) if report.get("period_start") else None,
        period_end=date.fromisoformat(report["period_end"]) if report.get("period_end") else None,
        period_label=report.get("period_label"),
        compare=compare,
        snapshot_hash=_hash_snapshot(typed),
        snapshot_json=json.dumps(typed, ensure_ascii=False, default=str),
        insight=result["insight"],
        findings_json=json.dumps(result["findings"], ensure_ascii=False),
        suggestions_json=json.dumps(result["suggestions"], ensure_ascii=False),
        actions_json=json.dumps(result["actions"], ensure_ascii=False),
        raw_response=raw_text[:8000],
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        status=status,
        created_by=operator or "ai_agent",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    data = _serialize_interpretation(row)
    data.update(llm_identity(cfg, {"model": model_name}))
    return data


def _serialize_interpretation(row: AiReportInterpretation) -> dict[str, Any]:
    def _loads(s: Optional[str], default):
        try:
            return json.loads(s or "") if s else default
        except Exception:
            return default

    actions = _loads(row.actions_json, [])
    # 合并已确认状态
    return {
        "id": row.id,
        "report_code": row.report_code,
        "report_type": t(str(row.report_type or "")),
        "period_label": row.period_label,
        "compare": row.compare,
        "insight": row.insight,
        "findings": _loads(row.findings_json, []),
        "suggestions": _loads(row.suggestions_json, []),
        "actions": actions,
        "status": row.status,
        "prompt_version": row.prompt_version,
        "created_at": row.created_at.isoformat(sep=" ", timespec="minutes") if row.created_at else None,
        "snapshot_hash": row.snapshot_hash,
        "model": row.model_name,
        "model_name": row.model_name,
    }


def get_interpretation(db: Session, hotel_id: int, interpretation_id: int) -> dict[str, Any]:
    row = db.get(AiReportInterpretation, interpretation_id)
    if not row or row.hotel_id != hotel_id:
        raise FileNotFoundError("解读记录不存在")
    data = _serialize_interpretation(row)
    try:
        from commercial.ai_core.llm_service import llm_identity, load_llm_config

        data.update(llm_identity(load_llm_config(db), {"model": row.model_name}))
    except Exception:
        pass
    confs = db.query(AiActionConfirmation).filter_by(hotel_id=hotel_id, interpretation_id=interpretation_id).all()
    by_idx = {c.action_index: c for c in confs}
    for i, act in enumerate(data["actions"]):
        c = by_idx.get(i)
        if c:
            act["status"] = c.decision
            act["decision_remark"] = c.decision_remark
            act["decided_by"] = c.decided_by
            act["decided_at"] = c.decided_at.isoformat(sep=" ", timespec="minutes") if c.decided_at else None
    return data


def decide_action(
    db: Session,
    hotel_id: int,
    interpretation_id: int,
    action_index: int,
    decision: str,
    *,
    operator: str = "店长",
    remark: str = "",
) -> dict[str, Any]:
    """人工确认闸：confirmed | dismissed。仅记录+有限副作用，永不静默改资金账。"""
    row = db.get(AiReportInterpretation, interpretation_id)
    if not row or row.hotel_id != hotel_id:
        raise FileNotFoundError("解读记录不存在")
    actions = json.loads(row.actions_json or "[]")
    if action_index < 0 or action_index >= len(actions):
        raise ValueError("action_index 越界")
    act = actions[action_index]
    kind = act.get("kind")
    if kind not in ACTION_KINDS:
        raise ValueError("非法 action kind")
    decision = "confirmed" if decision == "confirmed" else "dismissed"
    exec_result: dict[str, Any] = {"ok": True}

    if decision == "confirmed":
        payload = act.get("payload") or {}
        if kind == "export":
            from finance.finance_reports_service import create_export

            fmt = str(payload.get("format") or "xlsx")
            exp = create_export(
                db,
                hotel_id,
                row.report_code,
                fmt,
                period="custom" if row.period_start and row.period_end else "month",
                start=row.period_start.isoformat() if row.period_start else None,
                end=row.period_end.isoformat() if row.period_end else None,
                compare=row.compare or "yoy",
                operator=operator,
            )
            exec_result = {"ok": True, "export": exp, "goto": None}
        elif kind == "mark_anomaly":
            aid = str(payload.get("anomaly_id") or payload.get("id") or "")
            if aid.startswith("pi-"):
                try:
                    pid = int(aid.split("-", 1)[1])
                    ins = db.get(ProfitInsight, pid)
                    if ins and ins.hotel_id == hotel_id and ins.status == "open":
                        # 仅标记备注，不自动关闭
                        ins.recommendation = (ins.recommendation or "") + f"\n[AI标记]{remark or act.get('title')}"
                        db.commit()
                        exec_result = {"ok": True, "marked": aid}
                except Exception as e:
                    exec_result = {"ok": False, "error": str(e)}
            elif payload.get("exception_id"):
                try:
                    eid = int(payload["exception_id"])
                    ex = db.get(NightAuditException, eid)
                    if ex and ex.hotel_id == hotel_id:
                        # 不自动 fixed，只留备注到 detail
                        ex.detail = (ex.detail or "") + f"\n[AI标记]{remark or act.get('title')}"
                        db.commit()
                        exec_result = {"ok": True, "marked": eid}
                except Exception as e:
                    exec_result = {"ok": False, "error": str(e)}
            else:
                exec_result = {"ok": True, "note": "已记录标记意图（无具体异常 ID）"}
        elif kind == "draft_reco":
            exec_result = {"ok": True, "goto": act.get("goto") or "/pricing?from=finance-report", "draft_only": True}
        elif kind == "draft_receivable":
            exec_result = {"ok": True, "goto": act.get("goto") or "/c9-finance/ar-ap", "draft_only": True}
        elif kind in ("submit_close", "draft_close", "escalate"):
            exec_result = {
                "ok": True,
                "draft_only": True,
                "goto": act.get("goto") or _default_goto(kind, row.report_code),
                "note": "已记录起草意图，需在对应模块人工完成",
            }

    conf = AiActionConfirmation(
        hotel_id=hotel_id,
        interpretation_id=interpretation_id,
        action_index=action_index,
        action_kind=kind,
        action_payload=json.dumps(act.get("payload") or {}, ensure_ascii=False),
        decision=decision,
        decided_by=operator,
        decided_at=datetime.now(),
        decision_remark=remark or "",
        exec_result=json.dumps(exec_result, ensure_ascii=False, default=str),
    )
    db.add(conf)
    # 回写 actions 状态
    act["status"] = decision
    actions[action_index] = act
    row.actions_json = json.dumps(actions, ensure_ascii=False)
    db.commit()

    out = get_interpretation(db, hotel_id, interpretation_id)
    out["last_decision"] = {
        "action_index": action_index,
        "decision": decision,
        "exec_result": exec_result,
    }
    return out
