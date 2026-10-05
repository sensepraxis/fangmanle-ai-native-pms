# SPDX-License-Identifier: Apache-2.0
"""P0 扩展点接线：events.emit 导出 + messaging.get_channel 入口。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class EmitExportTests(unittest.TestCase):
    def test_emit_is_exported_from_events_package(self):
        from events import emit

        self.assertTrue(callable(emit))

    def test_emit_publishes_without_raising(self):
        from events import emit, unsubscribe
        from events.bus import EventBus

        seen = []

        def _handler(event, payload):
            seen.append((event, payload))

        EventBus.subscribe("test.p0.emit", _handler)
        try:
            emit("test.p0.emit", {"ok": True})
            self.assertEqual(seen, [("test.p0.emit", {"ok": True})])
        finally:
            unsubscribe("test.p0.emit", _handler)

    def test_emit_isolates_handler_errors(self):
        from events import emit, unsubscribe
        from events.bus import EventBus

        def _boom(event, payload):
            raise RuntimeError("handler broken")

        EventBus.subscribe("test.p0.emit.boom", _boom)
        try:
            # emit 自身不抛；业务链路不被埋点拖垮
            emit("test.p0.emit.boom", {"x": 1})
        finally:
            unsubscribe("test.p0.emit.boom", _boom)


class MessagingFactoryTests(unittest.TestCase):
    def tearDown(self):
        from messaging import reset_channel_cache

        reset_channel_cache()

    def test_get_channel_defaults_to_wecom(self):
        from messaging import current_vendor, get_channel

        self.assertEqual(current_vendor(), "wecom")
        ch = get_channel()
        self.assertEqual(ch.vendor, "wecom")

    def test_facade_send_text_delegates_to_channel(self):
        from messaging import reset_channel_cache, send_text

        reset_channel_cache()
        fake = MagicMock()
        fake.vendor = "wecom"
        fake.send_text.return_value = {"task_id": 1}

        with patch("messaging.factory.get_channel", return_value=fake):
            # messaging.send_text 内部再调 get_channel —— patch 模块级导入路径
            with patch("messaging.get_channel", return_value=fake):
                out = send_text(hotel_id=1, content="hi", guest_id=9, db=object())
        self.assertEqual(out, {"task_id": 1})
        fake.send_text.assert_called_once()
        kwargs = fake.send_text.call_args.kwargs
        self.assertEqual(kwargs["hotel_id"], 1)
        self.assertEqual(kwargs["guest_id"], 9)
        self.assertEqual(kwargs["content"], "hi")

    def test_application_send_and_sync_go_through_messaging(self):
        from application import wecom as app_wecom

        with patch("messaging.send_text", return_value={"ok": True}) as mock_send:
            out = app_wecom.send_single_message(object(), 1, 42, "hello")
        self.assertEqual(out, {"ok": True})
        mock_send.assert_called_once()

        with patch("messaging.sync_external_contacts", return_value={"synced": 3}) as mock_sync:
            out2 = app_wecom.sync_external_contacts(object(), 1)
        self.assertEqual(out2, {"synced": 3})
        mock_sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
