# SPDX-License-Identifier: Apache-2.0
"""货币展示由酒店 YAML 驱动，不写死 ¥。"""

from __future__ import annotations

import os
import unittest


class CurrencyTests(unittest.TestCase):
    def tearDown(self):
        from infra.hotel import reset_hotel
        from infra.private_channel import clear_vendor_cache
        from messaging import reset_channel_cache

        os.environ.pop("FML_HOTEL", None)
        os.environ.pop("FML_HOTEL_FILE", None)
        os.environ.pop("FML_PACKS", None)
        reset_hotel()
        clear_vendor_cache()
        reset_channel_cache()

    def test_sg_currency_symbol(self):
        os.environ["FML_HOTEL"] = "demo-sg"
        os.environ.pop("PRIVATE_CHANNEL_VENDOR", None)
        from infra.currency import currency_symbol, format_money, hotel_currency_code
        from infra.hotel import ensure_hotel, reset_hotel
        from infra.private_channel import clear_vendor_cache
        from messaging import reset_channel_cache

        reset_hotel()
        clear_vendor_cache()
        reset_channel_cache()
        ensure_hotel()
        self.assertEqual(hotel_currency_code(), "SGD")
        self.assertEqual(currency_symbol(), "S$")
        self.assertTrue(format_money(12.5).startswith("S$"))


if __name__ == "__main__":
    unittest.main()
