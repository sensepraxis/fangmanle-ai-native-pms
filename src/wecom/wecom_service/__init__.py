# SPDX-License-Identifier: Apache-2.0
"""wecom.wecom_service 子包 — 保留外部 import 兼容。

原 wecom/wecom_service.py（2764 行 / 56 函数）按业务子域拆为：
  - bind_service
  - callback_service
  - care_service
  - config_service
  - contact_service
  - message_service
  - phone_conflict_service
  - portal_service
  - sidebar_service
  - task_query_service
  - _common                  : 共享私有 helper

外部 `from wecom.wecom_service import xxx` 走这里 re-export，零改动。
"""

from __future__ import annotations

from wecom.wecom_service import (
    _common,  # noqa: F401
    bind_service,  # noqa: F401
    callback_service,  # noqa: F401
    care_service,  # noqa: F401
    config_service,  # noqa: F401
    contact_service,  # noqa: F401
    message_service,  # noqa: F401
    phone_conflict_service,  # noqa: F401
    portal_service,  # noqa: F401
    sidebar_service,  # noqa: F401
    task_query_service,  # noqa: F401
)

# ---- 私有 helper re-export ----
from wecom.wecom_service._common import _care_salutation, _http_json

# ---- 模块级常量 re-export（QYAPI 是企业微信 API base URL，被外部代码直接 import）----
from wecom.wecom_service.bind_service import (
    QYAPI,
    _expire_bind_tickets_for_external,
    _welcome_payload,
    create_bind_ticket,
    get_bind_ticket_public,
    handle_friend_added,
    issue_session_for_ticket,
    issue_wecom_room_coupon,
    list_bind_tickets,
    send_welcome_with_bind_link,
    simulate_friend_scan,
    submit_bind_phone,
)
from wecom.wecom_service.callback_service import (
    _mark_callback_archived,
    _spawn_callback_processor,
    drain_pending_wecom_callbacks,
    enqueue_wecom_callback,
    list_callback_inbox,
    process_wecom_callback_event,
)
from wecom.wecom_service.care_service import (
    _birthday_window_label,
    _build_care_template,
    _order_brief,
    _vip_label,
    build_guest_care_profile,
    build_profile_summary,
    draft_wecom_care_message,
    format_profile_for_prompt,
)
from wecom.wecom_service.config_service import (
    get_access_token,
    load_wecom_config,
    mask_wecom_config,
    save_wecom_config,
    test_wecom_connection,
)
from wecom.wecom_service.contact_service import (
    _bind_wecom_identity,
    _find_guest_by_phone,
    get_external_contact,
    list_external_userids,
    sync_external_contacts,
)
from wecom.wecom_service.message_service import _send_agent_text_message, send_care_direct_message, send_single_message
from wecom.wecom_service.phone_conflict_service import (
    dismiss_phone_conflict,
    list_phone_conflicts,
    resolve_phone_conflict,
)

# ---- 公共 API re-export ----
from wecom.wecom_service.portal_service import (
    _bind_url,
    _portal_url,
    _resolve_member_landing_page_key,
    _resolve_returning_landing_page_key,
    _resolve_welcome_landing_page_key,
    _returning_url,
    _vip_benefits,
    get_guest_portal,
    guest_wecom_summary,
)
from wecom.wecom_service.sidebar_service import log_sidebar_care_sent, sidebar_guest_by_external_userid
from wecom.wecom_service.task_query_service import list_msg_tasks, query_groupmsg_result

__all__ = [
    "_bind_url",
    "_bind_wecom_identity",
    "_birthday_window_label",
    "_build_care_template",
    "_expire_bind_tickets_for_external",
    "_find_guest_by_phone",
    "_mark_callback_archived",
    "_order_brief",
    "_portal_url",
    "_resolve_member_landing_page_key",
    "_resolve_returning_landing_page_key",
    "_resolve_welcome_landing_page_key",
    "_returning_url",
    "_send_agent_text_message",
    "_spawn_callback_processor",
    "_vip_benefits",
    "_vip_label",
    "_welcome_payload",
    "build_guest_care_profile",
    "build_profile_summary",
    "create_bind_ticket",
    "dismiss_phone_conflict",
    "draft_wecom_care_message",
    "drain_pending_wecom_callbacks",
    "enqueue_wecom_callback",
    "format_profile_for_prompt",
    "get_access_token",
    "get_bind_ticket_public",
    "get_external_contact",
    "get_guest_portal",
    "guest_wecom_summary",
    "handle_friend_added",
    "issue_session_for_ticket",
    "issue_wecom_room_coupon",
    "list_bind_tickets",
    "list_callback_inbox",
    "list_external_userids",
    "list_msg_tasks",
    "list_phone_conflicts",
    "load_wecom_config",
    "log_sidebar_care_sent",
    "mask_wecom_config",
    "process_wecom_callback_event",
    "query_groupmsg_result",
    "resolve_phone_conflict",
    "save_wecom_config",
    "send_care_direct_message",
    "send_single_message",
    "send_welcome_with_bind_link",
    "sidebar_guest_by_external_userid",
    "simulate_friend_scan",
    "submit_bind_phone",
    "sync_external_contacts",
    "test_wecom_connection",
    "_care_salutation",
    "_http_json",
]


# 订单状态 -> 中文（H5 端展示用）。
# 之前在旧 wecom_service.py 单体里定义；拆分后迁移至此，确保向后兼容。
ORDER_ST_CN_H5: dict[str, str] = {
    "pending": "待入住",
    "confirmed": "已确认",
    "checked_in": "在住",
    "checked_out": "已离店",
    "cancelled": "已取消",
    "no_show": "未到",
    "in_house": "在住",
    "reserved": "已预订",
}
