// SPDX-License-Identifier: Apache-2.0
import { ref } from 'vue'
import { applyCurrency } from './money'

/** 产品白标：前端展示名 / 钱包源码。可用 VITE_* 覆盖，亦可被 /system/branding 覆盖。 */
export const NATIVE_WALLET_SOURCE = 'native_mkt'

const envName = (import.meta as any).env?.VITE_APP_NAME as string | undefined
const envNameEn = (import.meta as any).env?.VITE_APP_NAME_EN as string | undefined
const envTagline = (import.meta as any).env?.VITE_APP_TAGLINE as string | undefined

let _appName = (envName && envName.trim()) || '房满乐'
let _appNameEn = (envNameEn && envNameEn.trim()) || 'fangmanle'
let _tagline = (envTagline && envTagline.trim()) || 'AI 原生酒店 PMS'
let _walletSourceLabel = '本店私域'
let _channelVendor = 'wecom'
let _channelFallback: string[] = []
let _channelPacks: string[] = ['private_ops_core']
let _packsProfile = 'cn'
let _taxDocumentsEnabled = true
let _menusHidden: string[] = []
let _primaryColor = ''
let _logoUrl = ''
let _commercialEnabled = false

/** Sidebar / RBAC 订阅 pack 菜单隐藏变化 */
export const packUiRev = ref(0)

export function appName() {
  return _appName
}

export function appNameEn() {
  return _appNameEn
}

export function tagline() {
  return _tagline
}

export function walletSourceLabel() {
  return _walletSourceLabel
}

export function logoUrl() {
  void packUiRev.value
  return _logoUrl
}

export function primaryColor() {
  void packUiRev.value
  return _primaryColor
}

/** 把白标色写入 CSS 变量（主题最小换肤） */
export function applyThemeFromBranding() {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (_primaryColor) {
    root.style.setProperty('--primary', _primaryColor)
    root.style.setProperty('--md-sys-color-primary', _primaryColor)
  }
}

export function applyBranding(payload: {
  app_name?: string
  app_name_en?: string
  tagline?: string
  wallet_source_label?: string
  private_channel_vendor?: string
  private_channel_fallback?: string[]
  private_channel_packs?: string[]
  packs_profile?: string
  tax_documents_enabled?: boolean
  menus_hidden?: string[]
  currency?: string
  currency_symbol?: string
  primary_color?: string
  logo_url?: string
  commercial_enabled?: boolean
}) {
  if (payload.app_name) _appName = String(payload.app_name)
  if (payload.app_name_en) _appNameEn = String(payload.app_name_en)
  if (payload.tagline) _tagline = String(payload.tagline)
  if (payload.wallet_source_label) _walletSourceLabel = String(payload.wallet_source_label)
  if (payload.private_channel_vendor) _channelVendor = String(payload.private_channel_vendor)
  if (Array.isArray(payload.private_channel_fallback)) {
    _channelFallback = payload.private_channel_fallback.map(String)
  }
  if (Array.isArray(payload.private_channel_packs)) {
    _channelPacks = payload.private_channel_packs.map(String)
  }
  if (payload.packs_profile) _packsProfile = String(payload.packs_profile)
  if (typeof payload.tax_documents_enabled === 'boolean') {
    _taxDocumentsEnabled = payload.tax_documents_enabled
  }
  if (Array.isArray(payload.menus_hidden)) {
    _menusHidden = payload.menus_hidden.map((x) => String(x))
  }
  if (payload.primary_color !== undefined) _primaryColor = String(payload.primary_color || '')
  if (payload.logo_url !== undefined) _logoUrl = String(payload.logo_url || '')
  if (typeof payload.commercial_enabled === 'boolean') {
    _commercialEnabled = payload.commercial_enabled
  }
  if (payload.currency || payload.currency_symbol) {
    applyCurrency({
      currency: payload.currency,
      currency_symbol: payload.currency_symbol,
    })
  }
  applyThemeFromBranding()
  packUiRev.value += 1
}

export function privateChannelVendor() {
  return _channelVendor
}

export function privateChannelFallback() {
  void packUiRev.value
  return _channelFallback
}

export function privateChannelPacks() {
  void packUiRev.value
  return _channelPacks
}

export function packsProfile() {
  return _packsProfile
}

export function taxDocumentsEnabled() {
  return _taxDocumentsEnabled
}

export function menusHidden() {
  return _menusHidden
}

export function isMenuHiddenByPack(code: string) {
  void packUiRev.value
  return _menusHidden.includes(code)
}

/** 商业包 LLM 场景是否启用（/system/branding.commercial_enabled） */
export function commercialEnabled() {
  void packUiRev.value
  return _commercialEnabled
}

export function isNativeWalletSource(src: string | null | undefined): boolean {
  const s = String(src || '').trim()
  return s === NATIVE_WALLET_SOURCE || s === 'fangmanle_mkt' || s.startsWith('mkt_')
}

export const WALLET_SOURCE_LABELS: Record<string, string> = {
  [NATIVE_WALLET_SOURCE]: walletSourceLabel(),
  fangmanle_mkt: walletSourceLabel(),
  wecom: '企业微信',
  line: 'LINE',
  whatsapp: 'WhatsApp',
  grant: walletSourceLabel(),
  guest_coupon: '企业微信',
  meituan: '美团',
  douyin: '抖音',
  xhs: '小红书',
  ota: 'OTA',
}

export function labelForWalletSource(src: string | null | undefined): string {
  const s = String(src || '').trim()
  if (isNativeWalletSource(s)) return walletSourceLabel()
  return WALLET_SOURCE_LABELS[s] || s || '未知'
}
