# SPDX-License-Identifier: Apache-2.0
"""Extensions 组装：map / llm / messaging / tax（由酒店 YAML 驱动）。"""

from __future__ import annotations

import os
import unittest


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


class ExtensionsAssembleTests(unittest.TestCase):
    def tearDown(self):
        _restore()

    def test_sg_activates_google_line_and_llm_catalog(self):
        os.environ["FML_HOTEL_FILE"] = "demo-sg"
        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        from extensions import ensure_extensions
        from extensions.llm import active_llm_default, list_llm_providers
        from infra.hotel import ensure_hotel, reset_hotel
        from infra.map_provider import get_map_provider
        from messaging import get_channel

        reset_hotel()
        self.assertEqual(ensure_hotel(), "demo-sg")
        ext = ensure_extensions()
        self.assertEqual(ext["map"], "google")
        self.assertEqual(ext["messaging"], "line")
        self.assertEqual(ext["tax"], "gst")
        self.assertEqual(get_map_provider().name, "google")
        self.assertEqual(get_channel().vendor, "line")
        ids = [p["id"] for p in list_llm_providers()]
        self.assertIn("ollama", ids)
        self.assertIn("deepseek", ids)
        self.assertEqual(active_llm_default(), "openai_compatible")

    def test_cn_map_allows_tianditu_family(self):
        from extensions import ensure_extensions
        from extensions.map.engine import list_provider_ids
        from infra.hotel import ensure_hotel, reset_hotel
        from infra.hotel_config import repo_root

        os.environ["FML_HOTEL_FILE"] = str(repo_root() / "config" / "hotels" / "demo-cn.yaml")
        reset_hotel()
        self.assertEqual(ensure_hotel(), "demo-cn")
        ext = ensure_extensions()
        self.assertEqual(ext["map"], "tianditu")
        self.assertEqual(ext["messaging"], "wecom")
        self.assertEqual(ext["tax"], "fapiao")
        for name in ("tianditu", "gaode", "baidu", "google", "noop"):
            self.assertIn(name, list_provider_ids())

    def test_imap_yaml_catalog_loads_classes(self):
        from extensions.map.engine import get_map, load_catalog, reset_engine

        reset_engine()
        cat = load_catalog(force=True)
        self.assertIn("tianditu", cat["providers"])
        self.assertEqual(
            cat["providers"]["tianditu"]["class"],
            "extensions.map.impl.tianditu.TiandituMap",
        )
        m = get_map("tianditu")
        self.assertEqual(m.name, "tianditu")
        g = get_map("amap")
        self.assertEqual(g.name, "gaode")

    def test_map_config_keeps_google_and_baidu(self):
        from infra.map_config import load_map_config, map_providers_ui

        ids = [p["id"] for p in map_providers_ui()]
        for name in ("tianditu", "gaode", "baidu", "google", "noop"):
            self.assertIn(name, ids)
        os.environ["MAP_PROVIDER"] = "google"
        try:
            cfg = load_map_config(None)
            self.assertEqual(cfg["provider"], "google")
        finally:
            os.environ.pop("MAP_PROVIDER", None)
        os.environ["MAP_PROVIDER"] = "baidu"
        try:
            cfg = load_map_config(None)
            self.assertEqual(cfg["provider"], "baidu")
        finally:
            os.environ.pop("MAP_PROVIDER", None)

    def test_tile_proxy_is_per_provider_not_tianditu_only(self):
        from unittest.mock import MagicMock, patch

        from extensions.map.engine import get_map, reset_engine
        from extensions.map.facade import proxy_map_tile

        reset_engine()
        self.assertTrue(callable(getattr(get_map("tianditu"), "fetch_tile", None)))
        self.assertIsNone(get_map("noop").fetch_tile("vec_w", 10, 1, 1))
        self.assertIsNone(get_map("baidu").fetch_tile("road", 10, 1, 1))

        gd = get_map("gaode")
        self.assertIn("road", (gd.render_config().get("tile_layers") or []))
        with patch("extensions.map.tile_http.fetch_bytes", return_value=(b"PNG", "image/png")) as http:
            body, ctype = gd.fetch_tile("road", 10, 512, 512, referer="http://localhost/")
            self.assertEqual((body, ctype), (b"PNG", "image/png"))
            self.assertIn("autonavi.com", http.call_args.args[0])

        # facade 只调当前 IMap，不写死天地图
        mock_map = MagicMock()
        mock_map.name = "google"
        mock_map.fetch_tile.return_value = (b"G", "image/png")
        with patch("extensions.map.facade.get_imap", return_value=mock_map):
            body, ctype = proxy_map_tile("m", 5, 1, 2, referer="http://x/")
            self.assertEqual(body, b"G")
            mock_map.fetch_tile.assert_called_once_with("m", 5, 1, 2, referer="http://x/")


if __name__ == "__main__":
    unittest.main()
