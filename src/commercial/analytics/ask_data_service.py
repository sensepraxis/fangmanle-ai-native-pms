# SPDX-License-Identifier: BUSL-1.1
"""智能问数 · LLM 经营诊断（营收预测页子能力）。

架构：预聚合 business_snapshot + 规则 anomalies + 受限 Taxonomy JSON。
本页只产出建议并跳转价格助手，绝不落库改价。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from analytics.ask_snapshot import (
    _channel_bucket,
    _mix_from_orders,
    _nights_in_window,
    _pct01,
    _rule_anomalies,
    _rule_anomaly_items,
    _segment_bucket,
    build_business_snapshot,
    candidates_from_snapshot,
    snapshot_from_board,
)
from infra.i18n import t
from models import AiDiagnosisResult

DIMENSIONS = [
    "远期预订进度偏慢",
    "平日入住率低",
    "周末价差不足",
    "渠道结构失衡(OTA占比过高)",
    "会员复购占比低",
    "商务客流失",
    "价格低于竞品",
    "价格高于竞品致流失",
    "长住连住未渗透",
    "节假日未做收益管理",
]

ACTIONS = [
    "开放远期预付价",
    "放开OTA日历房",
    "推出连住/套餐",
    "调整平日周末价差",
    "会员专属价",
    "暂不动作",
]

ASK_DATA_SYSTEM = """你是一名资深酒店收益管理（Revenue Management）诊断师，服务于一家以散客为主的单体/小型连锁酒店（约120间房）。
任务：基于后端已聚合好的「经营数据快照」，找出最能提升营收的经营短板，并给出可映射到「价格助手」调价动作的建议。

硬规则（必须严格遵守）：
1. 只依据「经营数据快照」字段判断，禁止编造快照中不存在的数字或字段；无证据写 "unknown"。
2. 每条结论必须带 evidence：引用快照字段名+数值，一句话。
3. 输出必须是纯 JSON，不要 Markdown 代码块标记、不要任何解释文字、不要输出思考过程。
4. 最多返回 3 条，按 revenue_impact（预估可提升营收）从大到小排序。
5. suggested_action 只能从列表选：["开放远期预付价","放开OTA日历房","推出连住/套餐","调整平日周末价差","会员专属价","暂不动作"]。
6. dimension 只能从列表选：["远期预订进度偏慢","平日入住率低","周末价差不足","渠道结构失衡(OTA占比过高)","会员复购占比低","商务客流失","价格低于竞品","价格高于竞品致流失","长住连住未渗透","节假日未做收益管理"]。
7. 若 anomalies 为空或数据健康，返回 {"issues":[]}。
8. 不确定时 confidence 标 "低"，不得硬编高置信度。

输出 JSON 结构：
{"issues":[{"dimension":"维度(列表选)","severity":"高|中|低","evidence":"快照字段+数值","revenue_impact":"元/天或unknown","suggested_action":"动作(列表选)","confidence":"高|中|低"}]}
"""

ASK_DATA_USER_FEWSHOT = """【经营数据快照】
{{business_snapshot_json}}

【示例】
输入：{"pickup":{"w7":{"booked":540,"expected":720,"gap":180}},"segment_mix":{"business_pct":0.22,"business_yoy":0.31},"anomalies":["pickup.w7 缺口25%","segment_mix.business 低于同期9pt"]}
输出：{"issues":[{"dimension":"远期预订进度偏慢","severity":"高","evidence":"pickup.w7 已订540/应有720，缺口180间夜(25%)","revenue_impact":"约6000元/天(国庆窗口)","suggested_action":"开放远期预付价","confidence":"高"},{"dimension":"商务客流失","severity":"中","evidence":"segment_mix.business_pct 22% 低于同期31%","revenue_impact":"约 ADR+18元/间","suggested_action":"推出连住/套餐","confidence":"中"}]}

现在请基于上方【经营数据快照】输出 JSON。
"""

# 智能问数专用 LLM 参数（§5）
# think 开启：流式拆 thinking / content；解析 JSON 只用 content（空则兜底 thinking）
ASK_LLM_OPTS = {
    "temperature": 0.2,
    "top_p": 0.85,
    # 思考 + 正文需要更大预算，避免 content 被 thinking 挤空
    "max_tokens": 4096,
    "think": True,
}


def _strip_think(text: str) -> str:
    if not text:
        return ""
    raw = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
    raw = re.sub(r"<thinking>[\s\S]*?</thinking>", "", raw, flags=re.I)
    # qwen3 偶发带自定义 think 标记
    raw = re.sub(r"</?think[^>]*>", "", raw, flags=re.I)
    return raw.strip()


def _extract_issues_json(text: str) -> dict[str, Any]:
    raw = _strip_think(text)
    if not raw:
        raise ValueError(t("模型返回为空"))
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw = p
                break
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(t("未找到 JSON"))
    obj = json.loads(raw[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError(t("JSON 根节点非对象"))
    return obj


def _severity_rank(s: str) -> int:
    return {"高": 0, "中": 1, "低": 2}.get(s, 9)


def _normalize_issues(raw: dict[str, Any]) -> list[dict]:
    items = raw.get("issues") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        raise ValueError("issues 不是数组")
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dim = str(it.get("dimension") or "").strip()
        act = str(it.get("suggested_action") or "").strip()
        if dim not in DIMENSIONS or act not in ACTIONS:
            continue  # §5 列表校验：越界丢弃
        sev = str(it.get("severity") or "中").strip()
        if sev not in ("高", "中", "低"):
            sev = "中"
        conf = str(it.get("confidence") or "低").strip()
        if conf not in ("高", "中", "低"):
            conf = "低"
        evidence = str(it.get("evidence") or "unknown").strip()[:160]
        impact = str(it.get("revenue_impact") or "unknown").strip()[:80]
        out.append(
            {
                "dimension": dim,
                "severity": sev,
                "evidence": evidence,
                "revenue_impact": impact,
                "suggested_action": act,
                "confidence": conf,
                # 卡片兼容字段
                "id": f"issue-{len(out) + 1}-{abs(hash(dim + evidence)) % 10000}",
                "reco_title": dim,
                "trigger": evidence,
                "reco_detail": f"建议动作：{act}。依据：{evidence}",
                "est_impact": impact if impact != "unknown" else "",
                "pricing_path": f"/pricing?action={act}",
                "ai_generated": True,
            }
        )
    out.sort(key=lambda x: _severity_rank(x["severity"]))
    return out[:3]


def _build_user_prompt(snapshot: dict[str, Any]) -> str:
    # 喂给模型的快照去掉 meta 噪声（保留契约字段）
    feed = {
        "hotel": snapshot.get("hotel"),
        "kpi": snapshot.get("kpi"),
        "pickup": snapshot.get("pickup"),
        "channel_mix": snapshot.get("channel_mix"),
        "segment_mix": snapshot.get("segment_mix"),
        "price_position": {"adr_index_vs_comp": (snapshot.get("price_position") or {}).get("adr_index_vs_comp")},
        "anomalies": snapshot.get("anomalies") or [],
    }
    return ASK_DATA_USER_FEWSHOT.replace(
        "{{business_snapshot_json}}",
        json.dumps(feed, ensure_ascii=False, indent=2),
    )


def _persist_diagnosis(
    db: Session,
    hotel_id: int,
    snapshot: dict[str, Any],
    issues: list[dict],
    *,
    model_name: str,
    status: str = "done",
) -> None:
    try:
        row = AiDiagnosisResult(
            hotel_id=hotel_id,
            generated_at=datetime.now(),
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            model_name=model_name or "",
            issues_json=json.dumps(issues, ensure_ascii=False),
            status=status,
            created_by="ai_agent",
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()


def _finalize(
    issues: list[dict],
    *,
    source: str,
    snapshot: dict[str, Any],
    model_name: str,
    error: str | None = None,
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    for it in issues:
        it["ai_source"] = source
        it["generated_at"] = generated_at
        it["created_by"] = "ai_agent" if source == "llm" else "system"
        it["status"] = "open"
    out = {
        "issues": issues,
        "findings": issues,  # 兼容旧前端字段名
        "ai_source": source,
        "generated_at": generated_at,
        "model_name": model_name,
        "model": model_name,
        "anomaly_count": len(snapshot.get("anomalies") or []),
        "snapshot": {
            "hotel": snapshot.get("hotel"),
            "anomalies": snapshot.get("anomalies") or [],
        },
    }
    if identity:
        out.update(identity)
    if error and source != "llm":
        # error 可能已是本地化串；再包一层警告模板并跟 Locale
        detail = t(str(error)[:120]) if error else ""
        out["ai_warning"] = t("未能调用大模型，未生成 AI 建议。{error}", error=detail)
    return out


def generate_ask_data(
    db: Session,
    hotel_id: int,
    *,
    growth_factor: float = 1.0,
) -> dict[str, Any]:
    snapshot = build_business_snapshot(db, hotel_id, growth_factor=growth_factor)
    user = _build_user_prompt(snapshot)
    model_name = ""
    identity: dict[str, Any] = {}
    try:
        from commercial.ai_core.llm_service import chat as llm_chat
        from commercial.ai_core.llm_service import llm_identity, load_llm_config
        from extensions.llm.facade import resolve_model_name

        cfg = load_llm_config(db)
        model_name = resolve_model_name(cfg)
        identity = llm_identity(cfg)
        if not cfg.get("enabled", True):
            raise RuntimeError(t("LLM 模块已禁用"))
        # anomalies 为空：仍调用模型，但提示应返回空；也可直接短路
        resp = llm_chat(
            db,
            [{"role": "user", "content": user}],
            ASK_DATA_SYSTEM,
            overrides=ASK_LLM_OPTS,
        )
        text = str((resp or {}).get("content") or "")
        parsed = _extract_issues_json(text)
        issues = _normalize_issues(parsed)
        identity = llm_identity(cfg, resp if isinstance(resp, dict) else None)
        model_name = str(identity.get("model") or model_name)
        _persist_diagnosis(db, hotel_id, snapshot, issues, model_name=model_name, status="done")
        return _finalize(issues, source="llm", snapshot=snapshot, model_name=model_name, identity=identity)
    except Exception as e:  # noqa: BLE001
        error = str(getattr(e, "detail", None) or e)
        # 降级：暂无可用建议（不展示错乱文本）；若有 anomalies 可给空 issues
        issues: list[dict] = []
        _persist_diagnosis(db, hotel_id, snapshot, issues, model_name=model_name, status="failed")
        return _finalize(
            issues,
            source="unavailable",
            snapshot=snapshot,
            model_name="",
            error=error,
            identity={},
        )


def stream_ask_data(
    db: Session,
    hotel_id: int,
    *,
    growth_factor: float = 1.0,
) -> Iterator[dict[str, Any]]:
    snapshot = build_business_snapshot(db, hotel_id, growth_factor=growth_factor)
    yield {
        "type": "meta",
        "data": {
            "anomaly_count": len(snapshot.get("anomalies") or []),
            "anomalies": snapshot.get("anomalies") or [],
            "hotel": snapshot.get("hotel"),
            "as_of": (snapshot.get("hotel") or {}).get("date"),
        },
    }
    user = _build_user_prompt(snapshot)
    model_name = ""
    identity: dict[str, Any] = {}
    try:
        from commercial.ai_core.llm_service import chat_stream_parts, llm_identity, load_llm_config
        from extensions.llm.facade import resolve_model_name

        cfg = load_llm_config(db)
        model_name = resolve_model_name(cfg)
        identity = llm_identity(cfg)
        if not cfg.get("enabled", True):
            raise RuntimeError(t("LLM 模块已禁用"))
        thinking_full = ""
        content_full = ""
        for kind, chunk in chat_stream_parts(
            db,
            [{"role": "user", "content": user}],
            ASK_DATA_SYSTEM,
            overrides=ASK_LLM_OPTS,
        ):
            if not chunk:
                continue
            if kind == "thinking":
                thinking_full += chunk
                yield {"type": "thinking", "content": chunk}
            else:
                content_full += chunk
                yield {"type": "token", "content": chunk}
        # 解析：优先正文；正文空则从思考里抠 JSON
        parse_text = content_full.strip() or thinking_full
        parsed = _extract_issues_json(parse_text)
        issues = _normalize_issues(parsed)
        identity = llm_identity(cfg, {"model": model_name})
        _persist_diagnosis(db, hotel_id, snapshot, issues, model_name=model_name, status="done")
        yield {
            "type": "done",
            "data": _finalize(issues, source="llm", snapshot=snapshot, model_name=model_name, identity=identity),
        }
    except Exception as e:  # noqa: BLE001
        error = str(getattr(e, "detail", None) or e)
        issues: list[dict] = []
        tip = '{"issues":[]}'
        yield {"type": "token", "content": tip}
        _persist_diagnosis(db, hotel_id, snapshot, issues, model_name=model_name, status="failed")
        yield {
            "type": "done",
            "data": _finalize(
                issues,
                source="unavailable",
                snapshot=snapshot,
                model_name="",
                error=error,
                identity={},
            ),
        }
