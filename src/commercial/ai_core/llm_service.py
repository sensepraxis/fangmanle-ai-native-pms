# SPDX-License-Identifier: BUSL-1.1
"""可插拔 LLM 服务：Ollama / 百炼 / 硅基流动 / DeepSeek / OpenAI 兼容接口。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any, Iterator

from sqlalchemy.orm import Session

from commercial.ai_core.llm_defaults import DEFAULT_LLM_CONFIG, LLM_SETTING_KEY, build_default_llm_config
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from extensions.llm.catalog import LLM_PROVIDER_CATALOG, catalog_ids, catalog_meta
from infra.i18n import t
from models import AppSetting

# 兼容旧引用：目录以 extensions.llm 为源
LLM_PROVIDERS = list(LLM_PROVIDER_CATALOG)

_PROVIDER_IDS = set(catalog_ids())
_PROFILE_FIELDS = ("base_url", "model", "api_key")


def localized_llm_providers() -> list[dict]:
    """按请求 locale 翻译 label / hint；目录来自 extensions.llm。"""
    from extensions.llm import list_llm_providers

    return list_llm_providers()


def resolve_system_prompt_for_locale(prompt: str | None) -> str:
    """若仍是包装默认提示词，则按当前 locale 换成对应包；自定义文案不动。"""
    from commercial.ai_core.prompt_packs import get_default_system_prompt
    from infra.branding import app_name, app_name_en, app_slug

    def _brand_norm(s: str) -> str:
        out = str(s or "").strip()
        for b in (
            app_name(),
            app_name_en(),
            app_slug(),
            "房满乐",
            "Fangmanle",
            "fangmanle",
        ):
            if b:
                out = out.replace(b, "{APP_NAME}")
        return out

    p = str(prompt or "").strip()
    zh = get_default_system_prompt("zh-CN").strip()
    en = get_default_system_prompt("en").strip()
    if not p or _brand_norm(p) in (_brand_norm(zh), _brand_norm(en)):
        return get_default_system_prompt()
    return str(prompt or "")


def _provider_meta(provider_id: str) -> dict:
    return catalog_meta(provider_id)


def _provider_kind(provider_id: str) -> str:
    return str(_provider_meta(provider_id).get("kind") or "openai_compatible")


def _default_provider_id() -> str:
    from extensions.llm.facade import fallback_provider_id

    return fallback_provider_id()


def _default_profile(provider_id: str) -> dict:
    meta = _provider_meta(provider_id)
    return {
        "base_url": str(meta.get("default_base_url") or "").rstrip("/"),
        "model": str(meta.get("default_model") or "").strip(),
        "api_key": "",
    }


def _normalize_profile(raw: Any, provider_id: str) -> dict:
    base = _default_profile(provider_id)
    if isinstance(raw, dict):
        for k in _PROFILE_FIELDS:
            if raw.get(k) is not None:
                base[k] = raw[k]
    base["base_url"] = str(base.get("base_url") or "").rstrip("/")
    base["model"] = str(base.get("model") or "").strip()
    base["api_key"] = str(base.get("api_key") or "")
    return base


def _ensure_profiles(data: dict) -> dict[str, dict]:
    profiles_in = data.get("profiles") if isinstance(data.get("profiles"), dict) else {}
    profiles: dict[str, dict] = {}
    for p in LLM_PROVIDERS:
        pid = p["id"]
        profiles[pid] = _normalize_profile(profiles_in.get(pid), pid)

    # 旧版扁平配置迁移：仅当尚未存过 profiles 时写入当前 provider
    if not profiles_in:
        provider = str(data.get("provider") or _default_provider_id())
        if provider not in _PROVIDER_IDS:
            provider = _default_provider_id()
        flat = {k: data.get(k) for k in _PROFILE_FIELDS}
        if any(v not in (None, "") for v in flat.values()):
            merged = {**profiles[provider], **{k: v for k, v in flat.items() if v not in (None, "")}}
            profiles[provider] = _normalize_profile(merged, provider)
    return profiles


def _apply_active_profile(cfg: dict) -> dict:
    """把当前活跃 provider 的 profile 展平到顶层，供 chat() 使用。"""
    out = deepcopy(cfg)
    provider = str(out.get("provider") or _default_provider_id())
    if provider not in _PROVIDER_IDS:
        provider = _default_provider_id()
        out["provider"] = provider
    profiles = out.get("profiles") if isinstance(out.get("profiles"), dict) else {}
    prof = _normalize_profile(profiles.get(provider), provider)
    out["base_url"] = prof["base_url"]
    out["model"] = prof["model"]
    out["api_key"] = prof["api_key"]
    return out


def _http_json(
    method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 120
) -> Any:
    body = None
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise BusinessError(f"LLM 上游 HTTP {e.code}: {detail[:400]}") from e
    except urllib.error.URLError as e:
        raise BusinessError(f"无法连接 LLM 服务：{e.reason}") from e
    except TimeoutError as e:
        raise BusinessError("LLM 请求超时") from e


def load_llm_config(db: Session) -> dict:
    fallback = build_default_llm_config()
    row = db.query(AppSetting).filter_by(key=LLM_SETTING_KEY).first()
    if not row or not row.value_json:
        data: dict = deepcopy(fallback)
    else:
        try:
            data = json.loads(row.value_json)
        except json.JSONDecodeError:
            data = deepcopy(fallback)
    merged = deepcopy(fallback)
    merged.update({k: v for k, v in data.items() if v is not None and k != "profiles"})
    merged["profiles"] = _ensure_profiles(data if isinstance(data, dict) else {})
    if merged.get("provider") not in _PROVIDER_IDS:
        merged["provider"] = _default_provider_id()
    return _apply_active_profile(merged)


def save_llm_config(db: Session, payload: dict) -> dict:
    current = load_llm_config(db)
    # 先还原为带完整 profiles 的结构（load 已展平）
    profiles = current.get("profiles") if isinstance(current.get("profiles"), dict) else _ensure_profiles(current)
    profiles = {pid: _normalize_profile(profiles.get(pid), pid) for pid in _PROVIDER_IDS}

    # 全局字段
    for k in ("enabled", "temperature", "max_tokens", "timeout_sec", "system_prompt", "provider"):
        if k in payload and payload[k] is not None:
            current[k] = payload[k]

    if current.get("provider") not in _PROVIDER_IDS:
        raise ValidationError("不支持的 LLM provider")

    # 批量写 profiles
    if isinstance(payload.get("profiles"), dict):
        for pid, raw in payload["profiles"].items():
            if pid not in _PROVIDER_IDS or not isinstance(raw, dict):
                continue
            prev = profiles[pid]
            nxt = dict(prev)
            for k in ("base_url", "model"):
                if k in raw and raw[k] is not None:
                    nxt[k] = raw[k]
            if "api_key" in raw:
                key = str(raw.get("api_key") or "")
                if key and "****" not in key:
                    nxt["api_key"] = key
            profiles[pid] = _normalize_profile(nxt, pid)

    # 兼容：扁平字段写入当前活跃 profile
    active = str(current.get("provider") or _default_provider_id())
    flat_update = dict(profiles[active])
    for k in ("base_url", "model"):
        if k in payload and payload[k] is not None:
            flat_update[k] = payload[k]
    if "api_key" in payload:
        key = str(payload.get("api_key") or "")
        if key and "****" not in key:
            flat_update["api_key"] = key
    profiles[active] = _normalize_profile(flat_update, active)

    current["profiles"] = profiles
    current["temperature"] = max(0.0, min(2.0, float(current.get("temperature") or 0.7)))
    current["max_tokens"] = max(128, min(8192, int(current.get("max_tokens") or 2048)))
    current["timeout_sec"] = max(10, min(300, int(current.get("timeout_sec") or 120)))

    active_prof = profiles[active]
    if not active_prof.get("model"):
        raise ValidationError("model 不能为空")
    if _provider_meta(active).get("needs_api_key") and not active_prof.get("api_key"):
        # 允许先保存空 key（便于填地址），调用时再报错
        pass

    # 顶层同步活跃 profile，便于旧代码读取
    current["base_url"] = active_prof["base_url"]
    current["model"] = active_prof["model"]
    current["api_key"] = active_prof["api_key"]

    row = db.query(AppSetting).filter_by(key=LLM_SETTING_KEY).first()
    if not row:
        row = AppSetting(key=LLM_SETTING_KEY)
        db.add(row)
    # 持久化时保留完整 profiles
    to_store = deepcopy(current)
    row.value_json = json.dumps(to_store, ensure_ascii=False)
    db.commit()
    return _apply_active_profile(to_store)


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return key[:4] + "****" + key[-4:] if len(key) > 8 else "****"


def mask_llm_config(cfg: dict) -> dict:
    out = deepcopy(cfg)
    key = str(out.get("api_key") or "")
    out["api_key"] = _mask_key(key)
    out["api_key_set"] = bool(key)
    profiles = out.get("profiles") if isinstance(out.get("profiles"), dict) else {}
    masked_profiles = {}
    profile_key_set = {}
    for pid, prof in profiles.items():
        p = dict(prof) if isinstance(prof, dict) else {}
        pk = str(p.get("api_key") or "")
        p["api_key"] = _mask_key(pk)
        p["api_key_set"] = bool(pk)
        masked_profiles[pid] = p
        profile_key_set[pid] = bool(pk)
    out["profiles"] = masked_profiles
    out["profile_api_key_set"] = profile_key_set
    # 配置页展示：默认包提示词随 X-Locale 切换；自定义不动
    out["system_prompt"] = resolve_system_prompt_for_locale(out.get("system_prompt"))
    return out


def _ollama_chat(cfg: dict, messages: list[dict]) -> str:
    url = f"{cfg['base_url']}/api/chat"
    model = str(cfg.get("model") or "")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": cfg.get("temperature", 0.7),
            "num_predict": cfg.get("max_tokens", 2048),
        },
    }
    if cfg.get("top_p") is not None:
        payload["options"]["top_p"] = float(cfg["top_p"])
    # Qwen3：默认关思考；调用方可 overrides.think=True 开启（智能问数）
    if model.lower().startswith("qwen3"):
        payload["think"] = bool(cfg.get("think", False))
    data = _http_json("POST", url, payload, timeout=int(cfg.get("timeout_sec") or 120))
    msg = data.get("message") or {}
    content = msg.get("content") or data.get("response")
    if not content:
        # 兼容：偶发只回 thinking，尝试从中取 JSON
        thinking = msg.get("thinking") or ""
        if thinking and ("{" in thinking):
            content = thinking
        else:
            raise BusinessError(t("Ollama 返回为空"))
    return str(content).strip()


def _ollama_chat_stream_parts(cfg: dict, messages: list[dict]) -> Iterator[tuple[str, str]]:
    """流式产出 (kind, text)，kind 为 thinking | content。"""
    url = f"{cfg['base_url']}/api/chat"
    model = str(cfg.get("model") or "")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": cfg.get("temperature", 0.7),
            "num_predict": cfg.get("max_tokens", 2048),
        },
    }
    if cfg.get("top_p") is not None:
        payload["options"]["top_p"] = float(cfg["top_p"])
    if model.lower().startswith("qwen3"):
        payload["think"] = bool(cfg.get("think", False))
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    timeout = int(cfg.get("timeout_sec") or 120)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                data = json.loads(line)
                msg = data.get("message") or {}
                thinking = msg.get("thinking") or ""
                content = msg.get("content") or ""
                if thinking:
                    yield ("thinking", str(thinking))
                if content:
                    yield ("content", str(content))
                if data.get("done"):
                    break
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise BusinessError(t("LLM 上游 HTTP {code}: {detail}", code=e.code, detail=detail[:400])) from e
    except urllib.error.URLError as e:
        raise BusinessError(t("无法连接 LLM 服务：{reason}", reason=e.reason)) from e
    except TimeoutError as e:
        raise BusinessError(t("LLM 请求超时")) from e


def _ollama_chat_stream(cfg: dict, messages: list[dict]) -> Iterator[str]:
    """兼容旧接口：优先流式 content；若全程无 content，则把 thinking 作为正文兜底。"""
    had_content = False
    thinking_parts: list[str] = []
    for kind, text in _ollama_chat_stream_parts(cfg, messages):
        if kind == "content" and text:
            had_content = True
            yield text
        elif kind == "thinking" and text:
            thinking_parts.append(text)
    if not had_content and thinking_parts:
        yield "".join(thinking_parts)


def _openai_compatible_chat_stream(cfg: dict, messages: list[dict]) -> Iterator[str]:
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature", 0.7),
        "max_tokens": cfg.get("max_tokens", 2048),
        "stream": True,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    timeout = int(cfg.get("timeout_sec") or 120)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                data = json.loads(chunk)
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {}).get("content") or ""
                if delta:
                    yield str(delta)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise BusinessError(f"LLM 上游 HTTP {e.code}: {detail[:400]}") from e
    except urllib.error.URLError as e:
        raise BusinessError(f"无法连接 LLM 服务：{e.reason}") from e
    except TimeoutError as e:
        raise BusinessError("LLM 请求超时") from e


def _build_messages(cfg: dict, user_messages: list[dict], extra_system: str | None = None) -> list[dict]:
    from commercial.ai_core.prompt_packs import language_instruction

    messages: list[dict] = []
    system_prompt = resolve_system_prompt_for_locale(cfg.get("system_prompt")).strip()
    if extra_system:
        system_prompt = f"{system_prompt}\n\n{extra_system}".strip()
    # 请求级 locale：强制输出语言（UI 顶栏 X-Locale）
    lang = language_instruction()
    if lang and lang not in system_prompt:
        system_prompt = f"{system_prompt}\n\n{lang}".strip() if system_prompt else lang
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for m in user_messages:
        role = m.get("role")
        content = str(m.get("content") or "").strip()
        if role in ("user", "assistant", "system") and content:
            messages.append({"role": role, "content": content})
    if not any(m["role"] == "user" for m in messages):
        raise ValidationError(t("messages 需包含至少一条 user 消息"))
    return messages


def _missing_api_key(provider: str) -> None:
    label = t(_provider_meta(provider).get("label") or provider)
    raise ValidationError(t("请先配置 {label} 的 API Key", label=label))


def _dispatch_chat(cfg: dict, messages: list[dict]) -> str:
    provider = cfg.get("provider") or _default_provider_id()
    kind = _provider_kind(provider)
    if kind == "ollama":
        return _ollama_chat(cfg, messages)
    if kind == "openai_compatible":
        if _provider_meta(provider).get("needs_api_key") and not cfg.get("api_key"):
            _missing_api_key(provider)
        return _openai_compatible_chat(cfg, messages)
    raise ValidationError(t("不支持的 provider"))


def _dispatch_chat_stream(cfg: dict, messages: list[dict]) -> Iterator[str]:
    provider = cfg.get("provider") or _default_provider_id()
    kind = _provider_kind(provider)
    if kind == "ollama":
        yield from _ollama_chat_stream(cfg, messages)
        return
    if kind == "openai_compatible":
        if _provider_meta(provider).get("needs_api_key") and not cfg.get("api_key"):
            _missing_api_key(provider)
        yield from _openai_compatible_chat_stream(cfg, messages)
        return
    raise ValidationError(t("不支持的 provider"))


def _dispatch_chat_stream_parts(cfg: dict, messages: list[dict]) -> Iterator[tuple[str, str]]:
    provider = cfg.get("provider") or _default_provider_id()
    kind = _provider_kind(provider)
    if kind == "ollama":
        yield from _ollama_chat_stream_parts(cfg, messages)
        return
    if kind == "openai_compatible":
        if _provider_meta(provider).get("needs_api_key") and not cfg.get("api_key"):
            _missing_api_key(provider)
        for text in _openai_compatible_chat_stream(cfg, messages):
            if text:
                yield ("content", text)
        return
    raise ValidationError(t("不支持的 provider"))


def chat_stream(
    db: Session,
    user_messages: list[dict],
    extra_system: str | None = None,
    overrides: dict | None = None,
) -> Iterator[str]:
    """流式输出 LLM 正文；若全程无 content，则把 thinking 作为兜底正文。"""
    had_content = False
    thinking_buf: list[str] = []
    for kind, text in chat_stream_parts(db, user_messages, extra_system, overrides):
        if not text:
            continue
        if kind == "thinking":
            thinking_buf.append(text)
            continue
        had_content = True
        yield text
    if not had_content and thinking_buf:
        yield "".join(thinking_buf)


def chat_stream_parts(
    db: Session,
    user_messages: list[dict],
    extra_system: str | None = None,
    overrides: dict | None = None,
) -> Iterator[tuple[str, str]]:
    """流式输出 (thinking|content, text)，供需要展示思考过程的场景。"""
    cfg = load_llm_config(db)
    if overrides:
        cfg = {**cfg, **overrides}
    if not cfg.get("enabled", True):
        raise BusinessError(t("LLM 模块已禁用，请在系统配置中启用"))

    messages = _build_messages(cfg, user_messages, extra_system)
    yield from _dispatch_chat_stream_parts(cfg, messages)


def _openai_compatible_chat(cfg: dict, messages: list[dict]) -> str:
    url = f"{cfg['base_url']}/chat/completions"
    headers = {}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature", 0.7),
        "max_tokens": cfg.get("max_tokens", 2048),
    }
    data = _http_json("POST", url, payload, headers=headers, timeout=int(cfg.get("timeout_sec") or 120))
    choices = data.get("choices") or []
    if not choices:
        raise BusinessError("模型接口返回为空（无 choices）")
    msg = choices[0].get("message") or {}
    # 部分推理模型可能把正文放在 reasoning_content，content 为空
    content = msg.get("content") or msg.get("reasoning_content") or ""
    if isinstance(content, list):
        # 少数兼容网关返回 content parts
        content = "".join(str(p.get("text") if isinstance(p, dict) else p) for p in content)
    content = str(content or "").strip()
    if not content:
        raise BusinessError("模型接口未返回可用正文（content 为空）")
    return content


def test_llm_connection(cfg: dict) -> dict:
    provider = cfg.get("provider") or _default_provider_id()
    kind = _provider_kind(provider)
    if kind == "ollama":
        url = f"{cfg['base_url']}/api/tags"
        data = _http_json("GET", url, timeout=min(30, int(cfg.get("timeout_sec") or 120)))
        models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
        model_ok = cfg["model"] in models
        reply = _ollama_chat(cfg, [{"role": "user", "content": "请回复：连接成功"}])
        return {
            "ok": True,
            "provider": provider,
            "model": cfg["model"],
            "models_available": models[:20],
            "model_registered": model_ok,
            "sample_reply": reply[:200],
        }
    if kind == "openai_compatible":
        if _provider_meta(provider).get("needs_api_key") and not cfg.get("api_key"):
            raise ValidationError(t("请先保存 API Key 后再测试连接"))
        reply = _openai_compatible_chat(cfg, [{"role": "user", "content": "请回复：连接成功"}])
        return {
            "ok": True,
            "provider": provider,
            "model": cfg["model"],
            "sample_reply": reply[:200],
        }
    raise ValidationError(t("不支持的 provider"))


def chat(
    db: Session,
    user_messages: list[dict],
    extra_system: str | None = None,
    overrides: dict | None = None,
) -> dict:
    cfg = load_llm_config(db)
    if overrides:
        cfg = {**cfg, **overrides}
    if not cfg.get("enabled", True):
        raise BusinessError("LLM 模块已禁用，请在系统配置中启用")

    messages = _build_messages(cfg, user_messages, extra_system)
    provider = cfg.get("provider") or _default_provider_id()
    content = _dispatch_chat(cfg, messages)

    return {
        "role": "assistant",
        "content": content,
        "model": cfg.get("model"),
        "provider": provider,
        "provider_label": provider_display(provider),
    }


def provider_display(provider_id: str | None) -> str:
    pid = str(provider_id or _default_provider_id())
    label = str(_provider_meta(pid).get("label") or pid)
    return t(label)


def llm_identity(cfg: dict, res: dict | None = None) -> dict:
    """解读结果附带的模型身份，便于前端展示当前实际调用的接入与模型。"""
    from extensions.llm.facade import resolve_model_name, resolve_provider_id

    provider = resolve_provider_id(cfg, res=res)
    model = resolve_model_name(cfg, res=res)
    return {
        "provider": provider,
        "provider_label": provider_display(provider),
        "model": model,
    }


def format_llm_fallback_note(cfg: dict | None, err: Any, *, max_err: int = 100) -> str:
    """LLM 失败时的用户可见附注：按当前系统配置的提供商/模型书写，禁止写死「本地」。

    例：DeepSeek · deepseek-v4-flash 暂不可用：…；硅基流动 · Qwen/Qwen3-8B 暂不可用：…
    """
    ident = llm_identity(cfg or {})
    parts = [p for p in (ident.get("provider_label"), ident.get("model")) if p]
    who = " · ".join(str(p) for p in parts) if parts else t("当前大模型")
    detail = getattr(err, "detail", None)
    text = str(detail if detail is not None else err).strip()[:max_err]
    return t("（{who}暂不可用：{text}；以上为规则化说明）", who=who, text=text)
