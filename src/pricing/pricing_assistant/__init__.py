# SPDX-License-Identifier: Apache-2.0
"""pricing.pricing_assistant 子包 — 保留外部 import 兼容。

原 pricing/pricing_assistant_service.py（3232 行 / 71 函数）按业务子域拆为：
  - booking_pace_service
  - channel_matrix_service
  - competitor_service
  - config_service
  - event_service
  - recommendation_service
  - view_service
  - _common                  : 共享私有 helper

外部 `from pricing.pricing_assistant import xxx` 走这里 re-export，零改动。
"""

from __future__ import annotations

from pricing.pricing_assistant import (
    _common,  # noqa: F401
    booking_pace_service,  # noqa: F401
    channel_matrix_service,  # noqa: F401
    competitor_service,  # noqa: F401
    config_service,  # noqa: F401
    event_service,  # noqa: F401
    recommendation_service,  # noqa: F401
    view_service,  # noqa: F401
)

# ---- 私有 helper re-export ----
from pricing.pricing_assistant._common import _json_dumps, _json_loads, _money, _sid
from pricing.pricing_assistant.booking_pace_service import (
    _booked_for_date,
    _orders_on_stay,
    _ota_min_for_date,
    _pct_delta,
    _rooms_count,
    _self_adr_for_date,
    get_pace,
    list_data_sources,
)

# ---- 公共 API re-export ----
from pricing.pricing_assistant.channel_matrix_service import (
    _base_from_guest,
    _est_n,
    _guest_price_from_base,
    _round_to,
    build_channel_matrix,
)
from pricing.pricing_assistant.competitor_service import (
    add_competitor,
    add_room_map,
    deactivate_competitor,
    import_competitor_rates_csv,
    list_competitor_rates,
    list_competitor_sets,
    list_room_maps,
    upsert_competitor_rate,
)
from pricing.pricing_assistant.config_service import (
    _commission_channels_for_ui,
    _commission_dict,
    _commission_rate,
    _resolve_rate,
    get_config_dict,
    get_or_create_config,
    sync_commission_from_channels,
    update_config,
)
from pricing.pricing_assistant.event_service import (
    _event_to_dict,
    _holiday_day_shape,
    _holiday_length_pct,
    _infer_heat_score,
    _intensity_heat_preset,
    _parse_event_dt,
    _resolve_event_geo,
    _self_location,
    create_event,
    deactivate_event,
    delete_event,
    get_event_uplift,
    list_events,
    update_event,
)
from pricing.pricing_assistant.recommendation_service import (
    _comp_median_guest,
    _comp_rates_stale_vs_recos,
    _dense_direct_coverage_ok,
    _horizon_label,
    _mark_reco_gen_at,
    _reco_to_calendar_dict,
    _reco_to_dict,
    batch_decide,
    build_explain_json,
    compute_tightness,
    decide_recommendation,
    ensure_recommendations_fresh,
    generate_recommendations,
    get_recommendation,
    list_recommendations,
    optimize_price,
)
from pricing.pricing_assistant.view_service import (
    build_calendar,
    build_compare,
    build_overview,
    build_trend,
    list_alerts,
    run_simulate,
)

__all__ = [
    "_base_from_guest",
    "_booked_for_date",
    "_commission_channels_for_ui",
    "_commission_dict",
    "_commission_rate",
    "_comp_median_guest",
    "_comp_rates_stale_vs_recos",
    "_dense_direct_coverage_ok",
    "_est_n",
    "_event_to_dict",
    "_guest_price_from_base",
    "_holiday_day_shape",
    "_holiday_length_pct",
    "_horizon_label",
    "_infer_heat_score",
    "_intensity_heat_preset",
    "_mark_reco_gen_at",
    "_orders_on_stay",
    "_ota_min_for_date",
    "_parse_event_dt",
    "_pct_delta",
    "_reco_to_calendar_dict",
    "_reco_to_dict",
    "_resolve_event_geo",
    "_resolve_rate",
    "_rooms_count",
    "_round_to",
    "_self_adr_for_date",
    "_self_location",
    "add_competitor",
    "add_room_map",
    "batch_decide",
    "build_calendar",
    "build_channel_matrix",
    "build_compare",
    "build_explain_json",
    "build_overview",
    "build_trend",
    "compute_tightness",
    "create_event",
    "deactivate_competitor",
    "deactivate_event",
    "decide_recommendation",
    "delete_event",
    "ensure_recommendations_fresh",
    "generate_recommendations",
    "get_config_dict",
    "get_event_uplift",
    "get_or_create_config",
    "get_pace",
    "get_recommendation",
    "import_competitor_rates_csv",
    "list_alerts",
    "list_competitor_rates",
    "list_competitor_sets",
    "list_data_sources",
    "list_events",
    "list_recommendations",
    "list_room_maps",
    "optimize_price",
    "run_simulate",
    "sync_commission_from_channels",
    "update_config",
    "update_event",
    "upsert_competitor_rate",
    "_json_dumps",
    "_json_loads",
    "_money",
    "_sid",
]
