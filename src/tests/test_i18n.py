# SPDX-License-Identifier: Apache-2.0
"""i18n smoke：locale 切换 + 押金标签 + 异常文案。"""

from __future__ import annotations

import unittest

import pytest

from infra.i18n import clear_locale, reload_catalogs, set_locale, t


class I18nCoreTests(unittest.TestCase):
    def setUp(self):
        reload_catalogs()
        clear_locale()

    def tearDown(self):
        clear_locale()

    def test_nav_stable_key(self):
        set_locale("zh-CN")
        self.assertEqual(t("nav.overview"), "经营总览")
        set_locale("en")
        self.assertEqual(t("nav.overview"), "Overview")

    def test_chinese_msgid_phrase(self):
        set_locale("en")
        self.assertEqual(t("退出登录"), "Log out")
        set_locale("zh-CN")
        self.assertEqual(t("退出登录"), "退出登录")

    def test_deposit_labels_follow_locale(self):
        from finance.deposit_status import FORMS, STATUS_LABEL

        set_locale("en")
        self.assertIn("WeChat", FORMS["WECHAT_DEPOSIT"])
        self.assertEqual(STATUS_LABEL["FROZEN"], "On hold")
        set_locale("zh-CN")
        self.assertEqual(STATUS_LABEL["FROZEN"], "在押")

    def test_param_interpolation(self):
        set_locale("en")
        msg = t("状态 {status} 不允许事件 {event}", status="FROZEN", event="FOO")
        self.assertIn("FROZEN", msg)
        self.assertIn("FOO", msg)


@pytest.mark.commercial
class AiPromptPackTests(unittest.TestCase):
    def test_scene_prompt_switches_locale(self):
        from commercial.ai_core.prompt_packs import get_scene_prompt, language_instruction, reload_prompt_packs
        from infra.i18n import set_locale

        reload_prompt_packs()
        set_locale("zh-CN")
        zh = get_scene_prompt("finance", "deposit")
        self.assertIn("押金", zh)
        self.assertIn("中文", language_instruction())
        set_locale("en")
        en = get_scene_prompt("finance", "deposit")
        self.assertIn("deposit", en.lower())
        self.assertIn("English", language_instruction())

    def test_mkt_prompt_pack_locale(self):
        from commercial.ai_core.prompt_packs import get_scene_prompt, reload_prompt_packs
        from infra.i18n import set_locale

        reload_prompt_packs()
        set_locale("zh-CN")
        zh = get_scene_prompt("mkt", "diagnosis")
        set_locale("en")
        en = get_scene_prompt("mkt", "diagnosis")
        self.assertTrue(zh.strip() and en.strip())
        self.assertNotEqual(zh, en)
        self.assertIn("私域", zh)
        self.assertIn("private", en.lower())

    def test_ask_occupancy_template_en(self):
        from commercial.analytics.ai_ask_answer_templates import get_answer_template
        from infra.i18n import set_locale

        set_locale("en")
        fn = get_answer_template("occupancy_compare_mom")
        summary, _ = fn(
            {"metrics": {"occ_pct": 80, "occ_pct_base": 70, "delta_pt": 10, "baseline": "prior"}, "rows": []},
            {},
        )
        self.assertIn("Occupancy", summary)
        set_locale("zh-CN")


class DocIdentityTests(unittest.TestCase):
    def setUp(self):
        reload_catalogs()
        clear_locale()

    def tearDown(self):
        clear_locale()

    def test_encode_tokens_are_stable(self):
        from finance.doc_identity import (
            encode_commission_doc,
            encode_corp_doc,
            encode_note_doc,
            encode_order_doc,
            encode_ota_doc,
        )

        self.assertEqual(encode_order_doc("ORD-1"), "order:ORD-1")
        self.assertEqual(encode_corp_doc(), "corp")
        self.assertEqual(encode_note_doc("企业挂账"), "corp")
        self.assertEqual(encode_note_doc("手工备注"), "note:手工备注")
        self.assertEqual(encode_ota_doc("2026-10", "ctrip", 3), "ota:2026-10:ctrip:3")
        self.assertEqual(encode_commission_doc("2026-10"), "commission:2026-10")

    def test_present_doc_label_follows_locale(self):
        from finance.doc_identity import present_doc_label

        set_locale("en")
        self.assertEqual(present_doc_label("order:ORD-9"), "On account · order ORD-9")
        self.assertEqual(present_doc_label("corp"), "Corporate AR")
        self.assertEqual(
            present_doc_label("ota:2026-10:ctrip:3", channel_name="Ctrip"),
            "10 · Ctrip · 3 orders",
        )
        self.assertEqual(present_doc_label("commission:2026-10"), "10 commission")
        self.assertEqual(present_doc_label("挂账 · 订单 LEGACY"), "On account · order LEGACY")

        set_locale("zh-CN")
        self.assertEqual(present_doc_label("order:ORD-9"), "挂账 · 订单 ORD-9")
        self.assertEqual(present_doc_label("corp"), "企业挂账")

    def test_party_name_is_identity(self):
        from finance.doc_identity import present_party_name

        set_locale("en")
        self.assertEqual(present_party_name("工商银行分行差旅"), "工商银行分行差旅")
        self.assertEqual(present_party_name("协议客户"), "Corporate guest")
        set_locale("zh-CN")
        self.assertEqual(present_party_name("协议客户"), "协议客户")

    def test_diff_type_code_stable_label_follows_locale(self):
        from finance.doc_identity import present_diff_type_label

        set_locale("en")
        self.assertEqual(present_diff_type_label("long"), "Overage")
        self.assertEqual(present_diff_type_label("short"), "Shortage")
        self.assertEqual(present_diff_type_label("flat"), "Balanced")
        set_locale("zh-CN")
        self.assertEqual(present_diff_type_label("long"), "长款")
        self.assertEqual(present_diff_type_label("short"), "短款")
        self.assertEqual(present_diff_type_label("flat"), "对平")


class CatalogSourceTests(unittest.TestCase):
    def setUp(self):
        reload_catalogs()
        clear_locale()

    def tearDown(self):
        clear_locale()

    def test_backend_loads_repo_locales(self):
        from infra.i18n import _find_locales_dir

        loc = _find_locales_dir()
        self.assertEqual(loc.name, "locales")
        self.assertTrue((loc / "en.json").is_file())
        self.assertNotIn("src", loc.parts[-2:])

    def test_finance_glossary_stable_keys(self):
        set_locale("en")
        self.assertEqual(t("finance.shift.overage"), "Overage")
        self.assertEqual(t("finance.shift.shortage"), "Shortage")
        self.assertEqual(t("finance.shift.balanced"), "Balanced")
        self.assertEqual(t("finance.ar.doc_corp"), "Corporate AR")
        self.assertEqual(
            t("finance.ar.doc_order", order_no="ORD-1"),
            "On account · order ORD-1",
        )
        set_locale("zh-CN")
        self.assertEqual(t("finance.shift.overage"), "长款")
        self.assertEqual(t("finance.ar.doc_corp"), "企业挂账")


if __name__ == "__main__":
    unittest.main()
