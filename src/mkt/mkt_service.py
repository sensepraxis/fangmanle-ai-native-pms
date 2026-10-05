# SPDX-License-Identifier: Apache-2.0
"""营销获客服务：薄重导出（Strangler 拆分后的兼容入口）。

实现已迁至同目录各 *_service / facade 模块；本文件保持
`from mkt.mkt_service import X` 与 application/mkt.py 可用。
"""

from __future__ import annotations

# Shared helpers / constants re-exported for callers that imported them from here
from mkt._mkt_utils import _dt, _jdumps, _jloads
from mkt.campaign_service import (
    CAMPAIGN_STATUSES,
    CAMPAIGN_TEMPLATES,
    CAMPAIGN_TRANSITIONS,
    approve_campaign,
    campaign_to_dict,
    create_campaign,
    list_campaign_templates,
    list_campaigns,
    patch_campaign_status,
    reject_campaign,
)
from mkt.coupon_batch_service import (
    COUPON_STATUSES,
    COUPON_TEMPLATES,
    COUPON_TYPES,
    COUPON_TYPES_LEGACY,
    _coupon_label,
    _next_coupon_batch_no,
    coupon_to_dict,
    create_coupon,
    list_coupon_templates,
    list_coupons,
    update_coupon_batch,
    update_coupon_status,
)
from mkt.grant_service import (
    CHANNEL_CN,
    _ensure_guest_coupon_from_mkt,
    _guest_h5_ready,  # compat
    bind_coupon_to_claim_landing,
    grant_coupon,
    grant_from_landing,
    guest_channel_reachable,
    guest_in_wecom_private,  # compat
    guest_private_bound,
    list_claim_landing_options,
    list_coupon_guest_ownership,
    list_grant_segments,
    list_grants,
    mkt_grant_to_public_coupon,
    preview_grant_audience,
    public_claim_without_token,
    resolve_grant_segment_guest_ids,
    resolve_landing_coupon,
    verify_coupon,
)
from mkt.landing_service import (
    ALL_BLOCK_TYPES,
    CLAIM_BLOCK_TYPES,
    MEMBER_BLOCK_TYPES,
    PAGE_ROLES,
    RETURNING_BLOCK_TYPES,
    _allowed_blocks_for_role,
    _esc,
    _has_unpublished_changes,
    _live_blocks,
    _live_coupon_id,
    _live_title,
    _norm_json_text,
    _sync_published_snapshot,
    create_landing_page,
    get_landing_page,
    get_published_landing,
    landing_to_dict,
    list_landing_pages,
    list_landing_templates,
    preview_landing_html,
    publish_landing_page,
    render_landing_html,
    unpublish_landing_page,
    update_landing_page,
)
from mkt.mkt_automation_service import (
    ACTION_TYPES,
    TRIGGER_TYPES,
    delete_automation,
    list_automations,
    preview_automation,
    set_automation_enabled,
    upsert_automation,
)
from mkt.mkt_customer_service import (
    add_customer_note,
    get_mkt_customer,
    list_mkt_customers,
)
from mkt.mkt_dashboard_service import (
    _recent_timeline,
    _wecom_mirror,
    mkt_dashboard,
)
from mkt.mkt_membership_facade import (
    _map_vip_to_h5_level,
    _normalize_benefits,
    delete_member_level,
    delete_stored_plan,
    ensure_mkt_guest_wallet,
    get_guest_h5_membership,
    list_member_levels,
    list_stored_plans,
    member_bundle,
    upsert_member_level,
    upsert_stored_plan,
)
from mkt.mkt_settings_service import (
    _entry_ids,
    get_mkt_settings,
    save_mkt_settings,
)

__all__ = [
    # utils
    "_jloads",
    "_jdumps",
    "_dt",
    # coupons
    "COUPON_TYPES",
    "COUPON_TYPES_LEGACY",
    "COUPON_STATUSES",
    "COUPON_TEMPLATES",
    "_coupon_label",
    "_next_coupon_batch_no",
    "coupon_to_dict",
    "list_coupons",
    "create_coupon",
    "update_coupon_batch",
    "update_coupon_status",
    "list_coupon_templates",
    # campaigns
    "CAMPAIGN_STATUSES",
    "CAMPAIGN_TRANSITIONS",
    "CAMPAIGN_TEMPLATES",
    "campaign_to_dict",
    "list_campaign_templates",
    "list_campaigns",
    "create_campaign",
    "patch_campaign_status",
    "approve_campaign",
    "reject_campaign",
    # dashboard
    "mkt_dashboard",
    "_recent_timeline",
    "_wecom_mirror",
    # settings
    "_entry_ids",
    "get_mkt_settings",
    "save_mkt_settings",
    # landing
    "PAGE_ROLES",
    "CLAIM_BLOCK_TYPES",
    "MEMBER_BLOCK_TYPES",
    "RETURNING_BLOCK_TYPES",
    "ALL_BLOCK_TYPES",
    "_allowed_blocks_for_role",
    "landing_to_dict",
    "_norm_json_text",
    "_has_unpublished_changes",
    "_live_blocks",
    "_live_title",
    "_live_coupon_id",
    "_sync_published_snapshot",
    "list_landing_templates",
    "list_landing_pages",
    "create_landing_page",
    "update_landing_page",
    "publish_landing_page",
    "unpublish_landing_page",
    "get_landing_page",
    "preview_landing_html",
    "get_published_landing",
    "render_landing_html",
    "_esc",
    # grants
    "CHANNEL_CN",
    "guest_channel_reachable",
    "guest_private_bound",
    "guest_in_wecom_private",  # compat
    "_guest_h5_ready",  # compat
    "list_grant_segments",
    "resolve_grant_segment_guest_ids",
    "preview_grant_audience",
    "list_claim_landing_options",
    "bind_coupon_to_claim_landing",
    "list_grants",
    "grant_coupon",
    "list_coupon_guest_ownership",
    "verify_coupon",
    "resolve_landing_coupon",
    "grant_from_landing",
    "_ensure_guest_coupon_from_mkt",
    "mkt_grant_to_public_coupon",
    "public_claim_without_token",
    # customers
    "list_mkt_customers",
    "get_mkt_customer",
    "add_customer_note",
    # automation
    "TRIGGER_TYPES",
    "ACTION_TYPES",
    "list_automations",
    "upsert_automation",
    "set_automation_enabled",
    "delete_automation",
    "preview_automation",
    # membership
    "list_member_levels",
    "upsert_member_level",
    "delete_member_level",
    "list_stored_plans",
    "upsert_stored_plan",
    "delete_stored_plan",
    "member_bundle",
    "_normalize_benefits",
    "_map_vip_to_h5_level",
    "ensure_mkt_guest_wallet",
    "get_guest_h5_membership",
]
