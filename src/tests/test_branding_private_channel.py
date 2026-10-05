# SPDX-License-Identifier: Apache-2.0
"""白标 branding + 私域通道 vendor 可配置性单测。"""

from __future__ import annotations

import os
import unittest


class BrandingTests(unittest.TestCase):
    def tearDown(self):
        from infra.branding import clear_branding_cache

        clear_branding_cache()
        os.environ.pop("FML_APP_NAME", None)

    def test_default_app_name(self):
        from infra.branding import NATIVE_WALLET_SOURCE, app_name, product_title

        self.assertEqual(app_name(), "房满乐")
        self.assertIn("PMS", product_title())
        self.assertEqual(NATIVE_WALLET_SOURCE, "native_mkt")

    def test_env_override(self):
        os.environ["FML_APP_NAME"] = "星宿酒店"
        from infra.branding import app_name, brand_text, clear_branding_cache

        clear_branding_cache()
        self.assertEqual(app_name(), "星宿酒店")
        self.assertIn("星宿酒店", brand_text("你好{APP_NAME}"))

    def test_wallet_norm_accepts_legacy(self):
        from mkt.wallet_norm import NATIVE_WALLET_SOURCE, normalize_wallet_source

        self.assertEqual(normalize_wallet_source("fangmanle_mkt"), NATIVE_WALLET_SOURCE)
        self.assertEqual(normalize_wallet_source("mkt_g12"), NATIVE_WALLET_SOURCE)
        self.assertEqual(normalize_wallet_source(NATIVE_WALLET_SOURCE), NATIVE_WALLET_SOURCE)


class CommercialCapabilityTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("FML_COMMERCIAL", None)
        from infra.branding import clear_branding_cache
        from infra.commercial_pack import reset_commercial_cache
        from infra.hotel import reset_hotel

        reset_commercial_cache()
        clear_branding_cache()
        reset_hotel()

    def test_branding_exposes_commercial_flag(self):
        from infra.branding import branding_public_dict
        from infra.commercial_pack import commercial_enabled

        d = branding_public_dict()
        self.assertIn("commercial_enabled", d)
        self.assertEqual(d["commercial_enabled"], commercial_enabled())

    def test_flag_off_hides_ai_menus(self):
        os.environ["FML_COMMERCIAL"] = "0"
        from infra.commercial_pack import reset_commercial_cache
        from infra.hotel import public_hotel_dict, reset_hotel

        reset_commercial_cache()
        reset_hotel()
        pub = public_hotel_dict()
        self.assertFalse(pub["commercial_enabled"])
        self.assertIn("menu.analytics.ai", pub["menus_hidden"])
        self.assertIn("menu.system.llm", pub["menus_hidden"])


class PrivateChannelVendorTests(unittest.TestCase):
    def tearDown(self):
        from infra.private_channel import clear_vendor_cache, configure_vendor
        from messaging import reset_channel_cache

        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        clear_vendor_cache()
        configure_vendor("wecom")
        reset_channel_cache()

    def test_env_vendor_override(self):
        os.environ["PRIVATE_CHANNEL_VENDOR"] = "webhook"
        from infra.private_channel import clear_vendor_cache, resolve_vendor
        from messaging import get_channel, reset_channel_cache

        clear_vendor_cache()
        reset_channel_cache()
        self.assertEqual(resolve_vendor(), "webhook")
        self.assertEqual(get_channel().vendor, "webhook")

    def test_configure_vendor_cache(self):
        from infra.private_channel import clear_vendor_cache, configure_vendor, resolve_vendor
        from messaging import get_channel, reset_channel_cache

        clear_vendor_cache()
        reset_channel_cache()
        configure_vendor("wecom")
        self.assertEqual(resolve_vendor(), "wecom")
        self.assertEqual(get_channel().vendor, "wecom")


if __name__ == "__main__":
    unittest.main()
