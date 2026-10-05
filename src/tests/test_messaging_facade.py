# SPDX-License-Identifier: Apache-2.0
"""私域 messaging facade / 多通道防腐单测。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch


class MessagingFacadeTests(unittest.TestCase):
    def tearDown(self):
        from infra.private_channel import clear_vendor_cache, configure_vendor
        from messaging import reset_channel_cache

        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        os.environ.pop("PRIVATE_CHANNEL_FALLBACK", None)
        os.environ.pop("PRIVATE_CHANNEL_PACKS", None)
        clear_vendor_cache()
        configure_vendor("wecom")
        reset_channel_cache()

    def test_identity_source_follows_vendor(self):
        from extensions.messaging.facade import identity_source, vendor_label
        from infra.private_channel import clear_vendor_cache, configure_vendor
        from messaging import reset_channel_cache

        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        clear_vendor_cache()
        reset_channel_cache()
        configure_vendor("line")
        self.assertEqual(identity_source(), "line")
        self.assertEqual(vendor_label(), "LINE")

    def test_line_channel_demo_send(self):
        from messaging.line import LineChannel

        ch = LineChannel()
        r = ch.send_text(hotel_id=1, content="hi")
        self.assertTrue(r["ok"])
        self.assertTrue(r.get("demo"))
        self.assertEqual(r["vendor"], "line")

    def test_whatsapp_channel_demo_send(self):
        from messaging.whatsapp import WhatsappChannel

        ch = WhatsappChannel()
        r = ch.send_text(hotel_id=1, content="hi")
        self.assertTrue(r["ok"])
        self.assertTrue(r.get("demo"))
        self.assertEqual(r["vendor"], "whatsapp")

    def test_channel_status_line_env_override(self):
        """用环境变量强制 line，避免缓存/酒店组装干扰。"""
        os.environ["PRIVATE_CHANNEL_VENDOR"] = "line"
        os.environ["PRIVATE_CHANNEL_FALLBACK"] = "sms,email"
        from extensions.messaging.facade import channel_status
        from infra.private_channel import clear_vendor_cache
        from messaging import reset_channel_cache

        clear_vendor_cache()
        reset_channel_cache()
        with patch(
            "infra.private_channel.load_private_channel_config",
            return_value={"vendor": "line", "line": {}, "webhook": {}, "fallback": ["sms", "email"]},
        ):
            st = channel_status(MagicMock())
        self.assertEqual(st["vendor"], "line")
        self.assertTrue(st["connected"])
        self.assertEqual(st["config_path"], "/a-ai-core/private-channel")
        self.assertEqual(st["label"], "LINE")
        self.assertEqual(st["region_profile"], "intl")
        self.assertIn("private_ops_core", st["packs"])
        self.assertNotIn("wecom_deep", st["packs"])
        self.assertTrue(st["capabilities"]["fallback_sms"])
        self.assertFalse(st["capabilities"]["care_sidebar"])

    def test_channel_status_whatsapp_capabilities(self):
        os.environ["PRIVATE_CHANNEL_VENDOR"] = "whatsapp"
        os.environ["PRIVATE_CHANNEL_FALLBACK"] = "sms,email"
        from extensions.messaging.facade import channel_status
        from infra.private_channel import clear_vendor_cache
        from messaging import reset_channel_cache

        clear_vendor_cache()
        reset_channel_cache()
        with patch(
            "infra.private_channel.load_private_channel_config",
            return_value={"vendor": "whatsapp", "whatsapp": {}, "fallback": ["sms", "email"]},
        ):
            st = channel_status(MagicMock())
        self.assertEqual(st["vendor"], "whatsapp")
        self.assertEqual(st["label"], "WhatsApp")
        self.assertTrue(st["capabilities"]["bind_ticket"])
        self.assertTrue(st["capabilities"]["private_ops_core"])

    def test_messaging_spec_dict(self):
        from infra.hotel_config import messaging_spec

        spec = messaging_spec(
            {
                "vendors": {
                    "messaging": {
                        "primary": "whatsapp",
                        "fallback": ["sms", "email"],
                        "packs": ["private_ops_core"],
                    }
                }
            }
        )
        self.assertEqual(spec["primary"], "whatsapp")
        self.assertEqual(spec["fallback"], ["sms", "email"])

    def test_private_channel_menu_not_hidden_intl(self):
        from infra.hotel_config import hide_menus_from_profile

        hide = hide_menus_from_profile({"system": {"private_channel": True, "wecom": False, "llm": True}})
        self.assertNotIn("menu.system.wecom", hide)


if __name__ == "__main__":
    unittest.main()
