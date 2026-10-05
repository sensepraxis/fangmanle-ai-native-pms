# SPDX-License-Identifier: Apache-2.0
"""酒店 YAML 组装：demo-cn / demo-sg / aliases；Noop 税票与地图。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from domain import InvalidStateError


def _restore():
    os.environ.pop("FML_PACKS", None)
    os.environ.pop("FML_HOTEL", None)
    os.environ.pop("FML_DEPLOY_FILE", None)
    os.environ.pop("FML_HOTEL_FILE", None)
    os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
    from infra.hotel import reset_hotel
    from infra.private_channel import clear_vendor_cache
    from messaging import reset_channel_cache

    reset_hotel()
    clear_vendor_cache()
    reset_channel_cache()


_restore_cn = _restore


class NoopProvidersTests(unittest.TestCase):
    def test_noop_map_nearby_empty(self):
        from infra.maps.noop import NoopMapProvider

        p = NoopMapProvider()
        out = p.nearby_hotels(120.0, 30.0, 3000)
        self.assertEqual(out["hotels"], [])
        self.assertEqual(p.js_config()["engine"], "noop")

    def test_noop_tax_issue_not_supported(self):
        from finance.tax.noop import NoopTaxProvider

        p = NoopTaxProvider()
        self.assertFalse(p.enabled)
        with self.assertRaises(InvalidStateError):
            p.issue(None, 1, 1)

    def test_webhook_channel_vendor(self):
        from messaging.webhook import WebhookChannel

        ch = WebhookChannel()
        self.assertEqual(ch.vendor, "webhook")


class HotelAssembleTests(unittest.TestCase):
    def tearDown(self):
        _restore()

    def test_default_demo_cn(self):
        os.environ.pop("FML_PACKS", None)
        os.environ.pop("FML_HOTEL", None)
        from infra.hotel import ensure_hotel, parse_hotel, reset_hotel
        from infra.hotel_config import repo_root

        os.environ["FML_HOTEL_FILE"] = str(repo_root() / "config" / "hotels" / "demo-cn.yaml")
        reset_hotel()
        self.assertIn(parse_hotel(), ("demo-cn", "cn"))
        self.assertEqual(ensure_hotel(), "demo-cn")
        from finance.tax.registry import get_tax_provider
        from infra.map_provider import get_map_provider

        self.assertEqual(get_tax_provider().name, "fapiao")
        self.assertTrue(get_tax_provider().enabled)
        self.assertIn(get_map_provider().name, ("tianditu", "gaode", "amap", "noop"))

    def test_intl_noop_tax_map_and_whatsapp(self):
        os.environ["FML_HOTEL"] = "demo-intl"
        os.environ["FML_PACKS"] = "demo-intl"
        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        os.environ.pop("PRIVATE_CHANNEL_FALLBACK", None)
        from infra.hotel import ensure_hotel, public_hotel_dict, reset_hotel
        from infra.hotel_config import repo_root
        from infra.private_channel import clear_vendor_cache
        from messaging import get_channel, reset_channel_cache

        os.environ["FML_HOTEL_FILE"] = str(repo_root() / "config" / "hotels" / "demo-intl.yaml")
        reset_hotel()
        clear_vendor_cache()
        reset_channel_cache()
        self.assertEqual(ensure_hotel(), "demo-intl")
        from finance.tax.registry import get_tax_provider
        from infra.map_provider import geocode_address, get_map_provider

        self.assertEqual(get_map_provider().name, "noop")
        self.assertFalse(get_tax_provider().enabled)
        pub = public_hotel_dict()
        self.assertFalse(pub["tax_documents_enabled"])
        self.assertEqual(pub["private_channel_vendor"], "whatsapp")
        self.assertIn("sms", pub.get("private_channel_fallback") or [])
        self.assertIn("menu.finance.invoice", pub["menus_hidden"])
        self.assertEqual(get_channel().vendor, "whatsapp")
        with patch("infra.tianditu_service._http_get_json") as http:
            geo = geocode_address("somewhere")
            http.assert_not_called()
        self.assertEqual(geo.get("source"), "noop")

    def test_sg_alias_gst_and_line_messaging(self):
        os.environ["FML_PACKS"] = "sg"
        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        from extensions.messaging.facade import channel_status, identity_source
        from infra.hotel import ensure_hotel, hotel_channel_seeds, hotel_menus_hidden, reset_hotel
        from infra.private_channel import clear_vendor_cache
        from messaging import get_channel, reset_channel_cache

        os.environ["FML_HOTEL_FILE"] = "sg"
        reset_hotel()
        clear_vendor_cache()
        reset_channel_cache()
        self.assertEqual(ensure_hotel(), "demo-sg")
        from finance.tax.registry import get_tax_provider
        from infra.map_provider import get_map_provider

        tax = get_tax_provider()
        self.assertEqual(tax.name, "gst")
        self.assertTrue(tax.enabled)
        self.assertAlmostEqual(tax.tax_rate, 0.09)
        self.assertEqual(get_map_provider().name, "google")
        self.assertEqual(get_channel().vendor, "line")
        self.assertEqual(identity_source(), "line")
        # 海外酒店显示通用「私域通道」Tab（不再隐藏）
        self.assertNotIn("menu.system.wecom", hotel_menus_hidden())
        # LineChannel 最小可用：无密钥时 demo 发送不抛错
        r = get_channel().send_text(hotel_id=1, content="hello", guest_id=None)
        self.assertTrue(r.get("ok"))
        self.assertEqual(r.get("vendor"), "line")
        codes = [row[0] for row in hotel_channel_seeds()]
        self.assertIn("booking", codes)

    def test_abc_hotel_yaml(self):
        from infra.hotel import ensure_hotel, reset_hotel
        from infra.hotel_config import repo_root

        os.environ["FML_HOTEL_FILE"] = str(repo_root() / "config" / "hotels" / "abc-hotel.yaml")
        os.environ.pop("FML_PACKS", None)
        os.environ.pop("FML_HOTEL", None)
        reset_hotel()
        self.assertEqual(ensure_hotel(), "abc-hotel")
        from finance.tax.registry import get_tax_provider
        from infra.map_provider import get_map_provider

        self.assertEqual(get_tax_provider().name, "fapiao")
        self.assertEqual(get_map_provider().name, "tianditu")

    def test_hotels_dir_profiles(self):
        from infra.hotel_config import get_profile, list_profile_ids, repo_root, reset_hotel_config_cache

        reset_hotel_config_cache()
        os.environ["FML_HOTEL_FILE"] = str(repo_root() / "config" / "hotels" / "demo-cn.yaml")
        ids = list_profile_ids()
        self.assertIn("demo-cn", ids)
        self.assertIn("abc-hotel", ids)
        sg = get_profile("sg")
        self.assertEqual(sg.get("id") or sg.get("_id"), "demo-sg")
        self.assertNotIn("channels", sg)


if __name__ == "__main__":
    unittest.main()
