# SPDX-License-Identifier: Apache-2.0
"""finance.reports 子包 — 财务报表中心按职责拆分。

原 finance/finance_reports_service.py 按 strangler 拆为：
  - period   : 期间解析 / 金额 / 同比环比
  - metrics  : 营收与 KPI 聚合
  - builders : 报表中心与各报表正文
  - export   : 导出列表 / 生成 / 下载

外部可 `from finance.reports import build_report`；
兼容层仍经 `finance.finance_reports_service` re-export。
"""

from __future__ import annotations

from finance.reports.builders import (
    CATALOG,
    DEFAULT_FORMAT,
    METHOD_CN,
    REPORT_META,
    SOURCE_CN,
    _ar_aging_rows,
    _build_manager_flash,
    _build_p_l,
    _build_trial_balance,
    _channel_rows,
    _empty_note,
    _income_rows,
    _kpi_metric_rows,
    _nav_with_badges,
    _payment_rows,
    _room_status_stats,
    _room_type_rows,
    _section_stats,
    _section_table,
    build_center,
    build_report,
)
from finance.reports.export import (
    EXPORT_DIR,
    _flatten_rows,
    _write_export_file,
    create_export,
    get_export_file,
    list_exports,
)
from finance.reports.metrics import (
    REV_STATUSES,
    _order_nights,
    _order_other_amount,
    _order_room_amount,
    _orders_in_period,
    _orders_overlapping,
    _overlap_room_nights,
    _room_count,
    _sum_night_audit_nights,
    _sum_night_audit_rev,
    _sum_orders_other,
    _sum_orders_other_rev,
    _sum_orders_rev,
    _sum_orders_room_rev,
    _sum_payments,
    _tax_rate,
    build_kpis,
    period_ops_kpis,
    period_revenue,
    period_room_revenue,
)
from finance.reports.period import (
    _as_date,
    _compare_range,
    _delta_pct,
    _dt_range,
    _mom_range,
    _money,
    _parse_date,
    _pct,
    _yoy_range,
    resolve_period,
)

__all__ = [
    # constants
    "CATALOG",
    "DEFAULT_FORMAT",
    "EXPORT_DIR",
    "METHOD_CN",
    "REPORT_META",
    "REV_STATUSES",
    "SOURCE_CN",
    # period
    "resolve_period",
    "_parse_date",
    "_as_date",
    "_dt_range",
    "_money",
    "_pct",
    "_yoy_range",
    "_mom_range",
    "_compare_range",
    "_delta_pct",
    # metrics
    "period_revenue",
    "period_room_revenue",
    "period_ops_kpis",
    "build_kpis",
    "_sum_payments",
    "_orders_in_period",
    "_orders_overlapping",
    "_overlap_room_nights",
    "_sum_orders_rev",
    "_sum_orders_other",
    "_sum_night_audit_rev",
    "_sum_night_audit_nights",
    "_room_count",
    "_order_nights",
    "_order_room_amount",
    "_order_other_amount",
    "_sum_orders_room_rev",
    "_sum_orders_other_rev",
    "_tax_rate",
    # builders
    "build_center",
    "build_report",
    "_section_table",
    "_section_stats",
    "_empty_note",
    "_nav_with_badges",
    "_payment_rows",
    "_room_status_stats",
    "_kpi_metric_rows",
    "_income_rows",
    "_room_type_rows",
    "_build_manager_flash",
    "_build_trial_balance",
    "_build_p_l",
    "_channel_rows",
    "_ar_aging_rows",
    # export
    "list_exports",
    "create_export",
    "get_export_file",
    "_flatten_rows",
    "_write_export_file",
]
