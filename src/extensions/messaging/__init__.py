# SPDX-License-Identifier: Apache-2.0
"""私域 Messaging Extension：Port = PrivateChannel；实现 = wecom / line / whatsapp / webhook (+ sms/email 兜底)。"""

from __future__ import annotations

from extensions.messaging.facade import (
    channel_status,
    guest_channel_reachable,
    identity_source,
    private_guest_ids,
    send_text,
    vendor_label,
)
from extensions.messaging.port import PrivateChannel
from messaging import current_vendor, get_channel

__all__ = [
    "PrivateChannel",
    "get_channel",
    "current_vendor",
    "channel_status",
    "guest_channel_reachable",
    "identity_source",
    "private_guest_ids",
    "send_text",
    "vendor_label",
]
