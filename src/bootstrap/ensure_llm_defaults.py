# SPDX-License-Identifier: Apache-2.0
"""系统 LLM 配置表与默认种子。

LLM 设置 key 与默认配置在 `commercial.ai_core.llm_defaults`；本文件保留 schema 保活。
未启用商业包时只建表、不灌默认对话配置。
"""

import json

from models import AppSetting


def ensure_llm_schema(engine):
    from models import AppSetting

    AppSetting.__table__.create(bind=engine, checkfirst=True)


def ensure_llm_defaults(db):
    from infra.commercial_pack import load_module

    mod = load_module("commercial.ai_core.llm_defaults")
    if mod is None:
        return
    cfg = mod.build_default_llm_config()
    row = db.query(AppSetting).filter_by(key=mod.LLM_SETTING_KEY).first()
    if not row:
        db.add(AppSetting(key=mod.LLM_SETTING_KEY, value_json=json.dumps(cfg, ensure_ascii=False)))
        db.commit()
        return
    if not row.value_json:
        row.value_json = json.dumps(cfg, ensure_ascii=False)
        db.commit()
