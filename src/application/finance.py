# SPDX-License-Identifier: Apache-2.0
"""Facade module for finance domain.

生成器可产出上方透传包装；文末 ``# --- orchestrated ---`` 为手写编排，勿覆盖。

职责：
  - 调 service 函数 + 透传 BusinessError
  - 写路径编排入口（夜审等跨域流程）
"""

from __future__ import annotations

# 业务异常（透传用）
from domain import (  # noqa: F401
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from finance.ar_ap_service import (
    apply_payment as _apply_payment,
)
from finance.ar_ap_service import (
    apply_receipt as _apply_receipt,
)
from finance.ar_ap_service import (
    check_credit as _check_credit,
)
from finance.ar_ap_service import (
    create_corp_charge as _create_corp_charge,
)
from finance.ar_ap_service import (
    dismiss_ar_ap_todo as _dismiss_ar_ap_todo,
)
from finance.ar_ap_service import (
    list_workspace as _list_workspace,
)
from finance.ar_ap_service import (
    write_off_ar as _write_off_ar,
)
from finance.deposit_service import (
    board as _deposit_board,
)
from finance.deposit_service import (
    capture as _deposit_capture,
)
from finance.deposit_service import (
    collect as _deposit_collect,
)
from finance.deposit_service import (
    credit_preview as _credit_preview,
)
from finance.deposit_service import (
    dispute as _deposit_dispute,
)
from finance.deposit_service import (
    get_detail as _get_detail,
)
from finance.deposit_service import (
    list_collectable_orders as _list_collectable_orders,
)
from finance.deposit_service import (
    lookup_by_guest as _lookup_by_guest,
)
from finance.deposit_service import (
    lookup_by_phone as _lookup_by_phone,
)
from finance.deposit_service import (
    lookup_by_room as _lookup_by_room,
)
from finance.deposit_service import (
    reauthorize as _deposit_reauthorize,
)
from finance.deposit_service import (
    release as _deposit_release,
)
from infra.commercial_pack import bind as _cbind

_confirm_plan = _cbind("commercial.finance.finance_ai_harness", "confirm_plan")
_generate_plan = _cbind("commercial.finance.finance_ai_harness", "generate_plan")

from finance.finance_board_service import (
    build_agreements_board as _build_agreements_board,
)
from finance.finance_board_service import (
    build_ar_board as _build_ar_board,
)
from finance.finance_board_service import (
    build_finance_board as _build_finance_board,
)
from finance.finance_board_service import (
    build_payments_shift as _build_payments_shift,
)
from finance.finance_board_service import (
    build_risk_board as _build_risk_board,
)
from finance.finance_float_service import (
    approve_float_carry_finance as _approve_float_carry_finance,
)
from finance.finance_float_service import (
    approve_float_carry_manager as _approve_float_carry_manager,
)
from finance.finance_float_service import (
    get_float_carry_workspace as _get_float_carry_workspace,
)
from finance.finance_float_service import (
    reject_float_carry_change as _reject_float_carry_change,
)
from finance.finance_float_service import (
    submit_float_carry_change as _submit_float_carry_change,
)
from finance.finance_params_ext_service import (
    create_credit_customer as _create_credit_customer,
)
from finance.finance_params_ext_service import (
    get_acquiring_workspace as _get_acquiring_workspace,
)
from finance.finance_params_ext_service import (
    get_credit_workspace as _get_credit_workspace,
)
from finance.finance_params_ext_service import (
    get_tax_workspace as _get_tax_workspace,
)
from finance.finance_params_ext_service import (
    toggle_acquiring_channel as _toggle_acquiring_channel,
)
from finance.finance_params_ext_service import (
    update_acquiring_rate as _update_acquiring_rate,
)
from finance.finance_params_ext_service import (
    update_bad_debt_rate as _update_bad_debt_rate,
)
from finance.finance_params_ext_service import (
    update_credit_limit as _update_credit_limit,
)
from finance.finance_params_ext_service import (
    update_payment_term as _update_payment_term,
)
from finance.finance_params_ext_service import (
    update_tax_config as _update_tax_config,
)

_decide_action = _cbind("commercial.finance.finance_report_ai_service", "decide_action")
_get_interpretation = _cbind("commercial.finance.finance_report_ai_service", "get_interpretation")
_interpret_report = _cbind("commercial.finance.finance_report_ai_service", "interpret_report")

from finance.finance_reports_service import (
    build_center as _build_center,
)
from finance.finance_reports_service import (
    build_report as _build_report,
)
from finance.finance_reports_service import (
    create_export as _create_export,
)
from finance.finance_reports_service import (
    get_export_file as _get_export_file,
)
from finance.finance_reports_service import (
    list_exports as _list_exports,
)
from finance.invoice_service import (
    issue_invoice as _issue_invoice,
)
from finance.invoice_service import (
    list_invoice_workspace as _list_invoice_workspace,
)
from finance.invoice_service import (
    red_flush_invoice as _red_flush_invoice,
)
from finance.ota_commission_service import (
    can_edit_commission as _can_edit_commission,
)
from finance.ota_commission_service import (
    delete_commission_override as _delete_commission_override,
)
from finance.ota_commission_service import (
    list_channels_for_api as _list_channels_for_api,
)
from finance.ota_commission_service import (
    list_commission_overrides as _list_commission_overrides,
)
from finance.ota_commission_service import (
    list_ota_commission_channels as _list_ota_commission_channels,
)
from finance.ota_commission_service import (
    reset_ota_commission_defaults as _reset_ota_commission_defaults,
)
from finance.ota_commission_service import (
    save_ota_commission_channels as _save_ota_commission_channels,
)
from finance.ota_commission_service import (
    set_ota_channel_enabled as _set_ota_channel_enabled,
)
from finance.ota_commission_service import (
    upsert_commission_override as _upsert_commission_override,
)
from finance.ota_commission_service import (
    upsert_ota_commission_channel as _upsert_ota_commission_channel,
)
from finance.recon_service import (
    batch_detail_enriched as _batch_detail_enriched,
)
from finance.recon_service import (
    explain_recon_batch as _explain_recon_batch,
)
from finance.recon_service import (
    list_recon_batches_enriched as _list_recon_batches_enriched,
)
from finance.recon_service import (
    rebuild_recon_from_orders as _rebuild_recon_from_orders,
)
from finance.recon_service import (
    serialize_recon_batch as _serialize_recon_batch,
)
from finance.refund_service import (
    build_refund_order_detail as _build_refund_order_detail,
)
from finance.refund_service import (
    dual_auth as _dual_auth,
)
from finance.refund_service import (
    list_adjust_entries as _list_adjust_entries,
)
from finance.refund_service import (
    list_reverse_targets as _list_reverse_targets,
)
from finance.refund_service import (
    lookup_order_for_refund as _lookup_order_for_refund,
)
from finance.refund_service import (
    lookup_refund_by_phone as _lookup_refund_by_phone,
)
from finance.refund_service import (
    submit_adjust as _submit_adjust,
)
from finance.refund_service import (
    submit_refund as _submit_refund,
)
from finance.refund_service import (
    submit_reverse as _submit_reverse,
)
from finance.refund_service import (
    update_threshold as _update_threshold,
)

_confirm_shift_ai_draft = _cbind("commercial.finance.shift_ai_harness", "confirm_shift_ai_draft")
_generate_shift_ai_draft = _cbind("commercial.finance.shift_ai_harness", "generate_shift_ai_draft")
_reject_shift_ai_draft = _cbind("commercial.finance.shift_ai_harness", "reject_shift_ai_draft")

from finance.shift_handover_service import (
    build_workspace as _build_workspace,
)
from finance.shift_handover_service import (
    complete_handover as _complete_handover,
)
from finance.shift_handover_service import (
    escalate_task as _escalate_task,
)
from finance.shift_handover_service import (
    save_asset_count as _save_asset_count,
)
from finance.shift_handover_service import (
    save_float_count as _save_float_count,
)
from finance.shift_handover_service import (
    sign_handover as _sign_handover,
)
from finance.shift_takeover_service import (
    ack_takeover_carryover as _ack_takeover_carryover,
)
from finance.shift_takeover_service import (
    ack_takeover_deposit as _ack_takeover_deposit,
)
from finance.shift_takeover_service import (
    ack_takeover_guest as _ack_takeover_guest,
)
from finance.shift_takeover_service import (
    ack_takeover_revenue as _ack_takeover_revenue,
)
from finance.shift_takeover_service import (
    build_takeover_workspace as _build_takeover_workspace,
)
from finance.shift_takeover_service import (
    claim_takeover_task as _claim_takeover_task,
)
from finance.shift_takeover_service import (
    complete_takeover_receive as _complete_takeover_receive,
)
from finance.shift_takeover_service import (
    confirm_takeover_matters as _confirm_takeover_matters,
)
from finance.shift_takeover_service import (
    report_receive_diff as _report_receive_diff,
)
from finance.shift_takeover_service import (
    save_takeover_asset_recount as _save_takeover_asset_recount,
)
from finance.shift_takeover_service import (
    save_takeover_float_recount as _save_takeover_float_recount,
)
from finance.shift_takeover_service import (
    sign_takeover_receive as _sign_takeover_receive,
)


def apply_payment(*args, **kwargs):
    """AR/AP 付款 → commit。"""
    db = args[0]
    try:
        out = _apply_payment(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def apply_receipt(*args, **kwargs):
    """AR 收款 → commit。"""
    db = args[0]
    try:
        out = _apply_receipt(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def check_credit(*args, **kwargs):
    """薄包装 — 调 finance.ar_ap_service.check_credit。"""
    return _check_credit(*args, **kwargs)


def create_corp_charge(*args, **kwargs):
    """企业挂账 → commit。"""
    db = args[0]
    try:
        out = _create_corp_charge(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def dismiss_ar_ap_todo(*args, **kwargs):
    """关闭 AR/AP 待办 → commit。"""
    db = args[0]
    try:
        out = _dismiss_ar_ap_todo(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def list_workspace(*args, **kwargs):
    """工作台（含同步副作用）→ commit。"""
    db = args[0]
    try:
        out = _list_workspace(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def write_off_ar(*args, **kwargs):
    """坏账核销 → commit。"""
    db = args[0]
    try:
        out = _write_off_ar(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def credit_preview(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.credit_preview。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _credit_preview(*args, **kwargs)


def get_detail(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.get_detail。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_detail(*args, **kwargs)


def list_collectable_orders(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.list_collectable_orders。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_collectable_orders(*args, **kwargs)


def lookup_by_guest(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.lookup_by_guest。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_by_guest(*args, **kwargs)


def lookup_by_phone(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.lookup_by_phone。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_by_phone(*args, **kwargs)


def lookup_by_room(*args, **kwargs):
    """薄包装 — 调 finance.deposit_service.lookup_by_room。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_by_room(*args, **kwargs)


def confirm_plan(*args, **kwargs):
    """薄包装 — 调 finance.finance_ai_harness.confirm_plan。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _confirm_plan(*args, **kwargs)


def generate_plan(*args, **kwargs):
    """薄包装 — 调 finance.finance_ai_harness.generate_plan。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _generate_plan(*args, **kwargs)


def build_agreements_board(*args, **kwargs):
    """薄包装 — 调 finance.finance_board_service.build_agreements_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_agreements_board(*args, **kwargs)


def build_ar_board(*args, **kwargs):
    """薄包装 — 调 finance.finance_board_service.build_ar_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_ar_board(*args, **kwargs)


def build_finance_board(*args, **kwargs):
    """薄包装 — 调 finance.finance_board_service.build_finance_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_finance_board(*args, **kwargs)


def build_payments_shift(*args, **kwargs):
    """薄包装 — 调 finance.finance_board_service.build_payments_shift。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_payments_shift(*args, **kwargs)


def build_risk_board(*args, **kwargs):
    """薄包装 — 调 finance.finance_board_service.build_risk_board。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_risk_board(*args, **kwargs)


def approve_float_carry_finance(*args, **kwargs):
    """薄包装 — 调 finance.finance_float_service.approve_float_carry_finance。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _approve_float_carry_finance(*args, **kwargs)


def approve_float_carry_manager(*args, **kwargs):
    """薄包装 — 调 finance.finance_float_service.approve_float_carry_manager。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _approve_float_carry_manager(*args, **kwargs)


def get_float_carry_workspace(*args, **kwargs):
    """薄包装 — 调 finance.finance_float_service.get_float_carry_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_float_carry_workspace(*args, **kwargs)


def reject_float_carry_change(*args, **kwargs):
    """薄包装 — 调 finance.finance_float_service.reject_float_carry_change。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _reject_float_carry_change(*args, **kwargs)


def submit_float_carry_change(*args, **kwargs):
    """薄包装 — 调 finance.finance_float_service.submit_float_carry_change。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _submit_float_carry_change(*args, **kwargs)


def create_credit_customer(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.create_credit_customer。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _create_credit_customer(*args, **kwargs)


def get_acquiring_workspace(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.get_acquiring_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_acquiring_workspace(*args, **kwargs)


def get_credit_workspace(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.get_credit_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_credit_workspace(*args, **kwargs)


def get_tax_workspace(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.get_tax_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_tax_workspace(*args, **kwargs)


def toggle_acquiring_channel(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.toggle_acquiring_channel。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _toggle_acquiring_channel(*args, **kwargs)


def update_acquiring_rate(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.update_acquiring_rate。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _update_acquiring_rate(*args, **kwargs)


def update_bad_debt_rate(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.update_bad_debt_rate。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _update_bad_debt_rate(*args, **kwargs)


def update_credit_limit(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.update_credit_limit。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _update_credit_limit(*args, **kwargs)


def update_payment_term(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.update_payment_term。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _update_payment_term(*args, **kwargs)


def update_tax_config(*args, **kwargs):
    """薄包装 — 调 finance.finance_params_ext_service.update_tax_config。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _update_tax_config(*args, **kwargs)


def decide_action(*args, **kwargs):
    """薄包装 — 调 finance.finance_report_ai_service.decide_action。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _decide_action(*args, **kwargs)


def get_interpretation(*args, **kwargs):
    """薄包装 — 调 finance.finance_report_ai_service.get_interpretation。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_interpretation(*args, **kwargs)


def interpret_report(*args, **kwargs):
    """薄包装 — 调 finance.finance_report_ai_service.interpret_report。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _interpret_report(*args, **kwargs)


def build_center(*args, **kwargs):
    """薄包装 — 调 finance.finance_reports_service.build_center。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_center(*args, **kwargs)


def build_report(*args, **kwargs):
    """薄包装 — 调 finance.finance_reports_service.build_report。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_report(*args, **kwargs)


def create_export(*args, **kwargs):
    """薄包装 — 调 finance.finance_reports_service.create_export。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _create_export(*args, **kwargs)


def get_export_file(*args, **kwargs):
    """薄包装 — 调 finance.finance_reports_service.get_export_file。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _get_export_file(*args, **kwargs)


def list_exports(*args, **kwargs):
    """薄包装 — 调 finance.finance_reports_service.list_exports。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_exports(*args, **kwargs)


def issue_invoice(*args, **kwargs):
    """薄包装 — 调 finance.invoice_service.issue_invoice。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _issue_invoice(*args, **kwargs)


def list_invoice_workspace(*args, **kwargs):
    """薄包装 — 调 finance.invoice_service.list_invoice_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_invoice_workspace(*args, **kwargs)


def red_flush_invoice(*args, **kwargs):
    """薄包装 — 调 finance.invoice_service.red_flush_invoice。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _red_flush_invoice(*args, **kwargs)


def delete_commission_override(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.delete_commission_override。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _delete_commission_override(*args, **kwargs)


def list_channels_for_api(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.list_channels_for_api。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_channels_for_api(*args, **kwargs)


def list_commission_overrides(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.list_commission_overrides。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_commission_overrides(*args, **kwargs)


def reset_ota_commission_defaults(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.reset_ota_commission_defaults。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _reset_ota_commission_defaults(*args, **kwargs)


def save_ota_commission_channels(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.save_ota_commission_channels。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _save_ota_commission_channels(*args, **kwargs)


def set_ota_channel_enabled(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.set_ota_channel_enabled。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _set_ota_channel_enabled(*args, **kwargs)


def upsert_commission_override(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.upsert_commission_override。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _upsert_commission_override(*args, **kwargs)


def upsert_ota_commission_channel(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.upsert_ota_commission_channel。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _upsert_ota_commission_channel(*args, **kwargs)


def batch_detail_enriched(*args, **kwargs):
    """薄包装 — 调 finance.recon_service.batch_detail_enriched。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _batch_detail_enriched(*args, **kwargs)


def explain_recon_batch(*args, **kwargs):
    """薄包装 — 调 finance.recon_service.explain_recon_batch。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _explain_recon_batch(*args, **kwargs)


def list_recon_batches_enriched(*args, **kwargs):
    """薄包装 — 调 finance.recon_service.list_recon_batches_enriched。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_recon_batches_enriched(*args, **kwargs)


def rebuild_recon_from_orders(*args, **kwargs):
    """薄包装 — 调 finance.recon_service.rebuild_recon_from_orders。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _rebuild_recon_from_orders(*args, **kwargs)


def serialize_recon_batch(*args, **kwargs):
    """薄包装 — 调 finance.recon_service.serialize_recon_batch。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _serialize_recon_batch(*args, **kwargs)


def build_refund_order_detail(*args, **kwargs):
    """薄包装 — 调 finance.refund_service.build_refund_order_detail。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_refund_order_detail(*args, **kwargs)


def dual_auth(*args, **kwargs):
    """退改双授权 → commit。"""
    db = args[0]
    try:
        out = _dual_auth(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def list_adjust_entries(*args, **kwargs):
    """薄包装 — 调 finance.refund_service.list_adjust_entries。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_adjust_entries(*args, **kwargs)


def list_reverse_targets(*args, **kwargs):
    """薄包装 — 调 finance.refund_service.list_reverse_targets。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_reverse_targets(*args, **kwargs)


def lookup_order_for_refund(*args, **kwargs):
    """薄包装 — 调 finance.refund_service.lookup_order_for_refund。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_order_for_refund(*args, **kwargs)


def lookup_refund_by_phone(*args, **kwargs):
    """薄包装 — 调 finance.refund_service.lookup_refund_by_phone。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _lookup_refund_by_phone(*args, **kwargs)


def submit_adjust(*args, **kwargs):
    """账务调整申请 → commit。"""
    db = args[0]
    try:
        out = _submit_adjust(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def submit_refund(*args, **kwargs):
    """退款申请 → commit。"""
    db = args[0]
    try:
        out = _submit_refund(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def submit_reverse(*args, **kwargs):
    """反结账申请 → commit。"""
    db = args[0]
    try:
        out = _submit_reverse(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def update_threshold(*args, **kwargs):
    """大额退款阈值 → commit。"""
    db = args[0]
    try:
        out = _update_threshold(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def confirm_shift_ai_draft(*args, **kwargs):
    """薄包装 — 调 finance.shift_ai_harness.confirm_shift_ai_draft。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _confirm_shift_ai_draft(*args, **kwargs)


def generate_shift_ai_draft(*args, **kwargs):
    """薄包装 — 调 finance.shift_ai_harness.generate_shift_ai_draft。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _generate_shift_ai_draft(*args, **kwargs)


def reject_shift_ai_draft(*args, **kwargs):
    """薄包装 — 调 finance.shift_ai_harness.reject_shift_ai_draft。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _reject_shift_ai_draft(*args, **kwargs)


def build_workspace(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.build_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_workspace(*args, **kwargs)


def complete_handover(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.complete_handover。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _complete_handover(*args, **kwargs)


def escalate_task(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.escalate_task。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _escalate_task(*args, **kwargs)


def save_asset_count(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.save_asset_count。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _save_asset_count(*args, **kwargs)


def save_float_count(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.save_float_count。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _save_float_count(*args, **kwargs)


def sign_handover(*args, **kwargs):
    """薄包装 — 调 finance.shift_handover_service.sign_handover。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _sign_handover(*args, **kwargs)


def ack_takeover_carryover(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.ack_takeover_carryover。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _ack_takeover_carryover(*args, **kwargs)


def ack_takeover_deposit(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.ack_takeover_deposit。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _ack_takeover_deposit(*args, **kwargs)


def ack_takeover_guest(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.ack_takeover_guest。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _ack_takeover_guest(*args, **kwargs)


def ack_takeover_revenue(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.ack_takeover_revenue。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _ack_takeover_revenue(*args, **kwargs)


def build_takeover_workspace(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.build_takeover_workspace。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _build_takeover_workspace(*args, **kwargs)


def claim_takeover_task(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.claim_takeover_task。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _claim_takeover_task(*args, **kwargs)


def complete_takeover_receive(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.complete_takeover_receive。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _complete_takeover_receive(*args, **kwargs)


def confirm_takeover_matters(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.confirm_takeover_matters。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _confirm_takeover_matters(*args, **kwargs)


def report_receive_diff(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.report_receive_diff。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _report_receive_diff(*args, **kwargs)


def save_takeover_asset_recount(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.save_takeover_asset_recount。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _save_takeover_asset_recount(*args, **kwargs)


def save_takeover_float_recount(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.save_takeover_float_recount。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _save_takeover_float_recount(*args, **kwargs)


def sign_takeover_receive(*args, **kwargs):
    """薄包装 — 调 finance.shift_takeover_service.sign_takeover_receive。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _sign_takeover_receive(*args, **kwargs)


def can_edit_commission(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.can_edit_commission。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _can_edit_commission(*args, **kwargs)


def list_ota_commission_channels(*args, **kwargs):
    """薄包装 — 调 finance.ota_commission_service.list_ota_commission_channels。

    facade 层：业务异常透传；参数校验、事务边界后续补充。
    """
    return _list_ota_commission_channels(*args, **kwargs)


# --- orchestrated ---
# Night audit: Fat Controller 下沉后的稳定入口；事务在 night_audit_service。

from finance.night_audit_service import (
    fix_audit_exception as _fix_audit_exception,
)
from finance.night_audit_service import (
    get_night_audit_detail as _get_night_audit_detail,
)
from finance.night_audit_service import (
    list_night_audits as _list_night_audits,
)
from finance.night_audit_service import (
    run_night_audit as _run_night_audit,
)


def run_night_audit(*args, **kwargs):
    """夜审执行编排入口。"""
    return _run_night_audit(*args, **kwargs)


def list_night_audits(*args, **kwargs):
    """夜审列表。"""
    return _list_night_audits(*args, **kwargs)


def get_night_audit_detail(*args, **kwargs):
    """夜审详情。"""
    return _get_night_audit_detail(*args, **kwargs)


def fix_audit_exception(db, eid: int) -> dict:
    try:
        out = _fix_audit_exception(db, eid)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def settle_ar_ledger(
    db,
    ledger_id: int,
    *,
    hotel_id: int,
    amount,
    ref_no=None,
    note=None,
    operator_id=None,
) -> dict:
    from finance.ar_ap_service import settle_ar_ledger as _settle

    try:
        out = _settle(
            db,
            ledger_id,
            hotel_id=hotel_id,
            amount=amount,
            ref_no=ref_no,
            note=note,
            operator_id=operator_id,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


# --- deposits（写路径 commit）---


def deposit_board(*args, **kwargs):
    return _deposit_board(*args, **kwargs)


def collect_deposit(*args, **kwargs):
    db = args[0]
    try:
        out = _deposit_collect(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def capture_deposit(*args, **kwargs):
    db = args[0]
    try:
        out = _deposit_capture(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def release_deposit(*args, **kwargs):
    db = args[0]
    try:
        out = _deposit_release(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def reauthorize_deposit(*args, **kwargs):
    db = args[0]
    try:
        out = _deposit_reauthorize(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def dispute_deposit(*args, **kwargs):
    db = args[0]
    try:
        out = _deposit_dispute(*args, **kwargs)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


# --- read queries（Fat Query Router 下沉）---

from finance.finance_query_service import (
    finance_flow_summary as _finance_flow_summary,
)
from finance.finance_query_service import (
    list_audit_exceptions as _list_audit_exceptions,
)
from finance.finance_query_service import (
    list_ledger_entries as _list_ledger_entries,
)
from finance.finance_query_service import (
    list_profit_insights as _list_profit_insights,
)
from finance.finance_query_service import (
    list_recon_conflicts as _list_recon_conflicts,
)
from finance.finance_query_service import (
    list_revenue_anomalies as _list_revenue_anomalies,
)
from finance.finance_query_service import (
    list_risk_alerts as _list_risk_alerts,
)
from finance.finance_query_service import (
    list_tax_filings as _list_tax_filings,
)


def finance_flow_summary(*args, **kwargs):
    return _finance_flow_summary(*args, **kwargs)


def list_ledger(*args, **kwargs):
    """兼容路由命名：list_ledger → list_ledger_entries。"""
    return _list_ledger_entries(*args, **kwargs)


def list_ledger_entries(*args, **kwargs):
    return _list_ledger_entries(*args, **kwargs)


def list_risk_alerts(*args, **kwargs):
    return _list_risk_alerts(*args, **kwargs)


def list_audit_exceptions(*args, **kwargs):
    return _list_audit_exceptions(*args, **kwargs)


def list_recon_conflicts(*args, **kwargs):
    return _list_recon_conflicts(*args, **kwargs)


def list_tax_filings(*args, **kwargs):
    return _list_tax_filings(*args, **kwargs)


def list_profit_insights(*args, **kwargs):
    return _list_profit_insights(*args, **kwargs)


def list_revenue_anomalies(*args, **kwargs):
    return _list_revenue_anomalies(*args, **kwargs)
