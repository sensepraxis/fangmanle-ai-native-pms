// SPDX-License-Identifier: Apache-2.0
/**
 * 金额展示：符号来自 /system/branding 的 currency，禁止写死 ¥。
 */
import { packUiRev } from './branding'

let _code = 'CNY'
let _symbol = '¥'

export function applyCurrency(payload: { currency?: string; currency_symbol?: string }) {
  if (payload.currency) _code = String(payload.currency).toUpperCase()
  if (payload.currency_symbol) _symbol = String(payload.currency_symbol)
  else if (payload.currency) _symbol = symbolFor(payload.currency)
  packUiRev.value += 1
}

function symbolFor(code: string): string {
  const c = String(code || '').toUpperCase()
  const map: Record<string, string> = {
    CNY: '¥',
    JPY: '¥',
    USD: '$',
    SGD: 'S$',
    GBP: '£',
    EUR: '€',
    HKD: 'HK$',
    TWD: 'NT$',
    KRW: '₩',
    THB: '฿',
    VND: '₫',
    MYR: 'RM',
    IDR: 'Rp',
    AUD: 'A$',
    CAD: 'C$',
  }
  return map[c] || `${c} `
}

export function currencyCode() {
  void packUiRev.value
  return _code
}

export function currencySymbol() {
  void packUiRev.value
  return _symbol
}

/** 格式化金额，默认带货币符号 */
export function formatMoney(
  amount: number | string | null | undefined,
  opts?: { digits?: number; withSymbol?: boolean },
): string {
  void packUiRev.value
  const digits = opts?.digits ?? 2
  const withSymbol = opts?.withSymbol !== false
  const n = Number(amount)
  const safe = Number.isFinite(n) ? n : 0
  const body = safe.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
  return withSymbol ? `${_symbol}${body}` : body
}

/** 仅符号（模板里替代硬编码 ¥） */
export function yen() {
  return currencySymbol()
}
