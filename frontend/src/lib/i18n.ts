// SPDX-License-Identifier: Apache-2.0
/** 前端 i18n：与后端 locales 共用同一套 key / 中文 msgid。 */
import zhCN from '@locales/zh-CN.json'
import en from '@locales/en.json'

export type Locale = 'zh-CN' | 'en'

const STORAGE_KEY = 'fml_locale'

type Dict = Record<string, unknown>

function flatten(obj: Dict, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(obj || {})) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      Object.assign(out, flatten(v as Dict, key))
    } else if (v != null) {
      out[key] = String(v)
      if (!prefix) out[k] = String(v)
    }
  }
  return out
}

const catalogs: Record<Locale, Record<string, string>> = {
  'zh-CN': flatten(zhCN as Dict),
  en: buildEnCatalog(en as Dict),
}

function buildEnCatalog(raw: Dict): Record<string, string> {
  const flat = flatten(raw)
  const phrases = (raw as any).phrases
  if (phrases && typeof phrases === 'object') {
    for (const [mk, mv] of Object.entries(phrases as Record<string, unknown>)) {
      const key = String(mk)
      const val = String(mv ?? '')
      const existing = flat[key]
      // 顶层已有真译文时，跳过 phrases 里「中=中」占位，避免盖掉 EN
      if (existing != null && existing !== key && val === key) continue
      flat[key] = val
    }
  }
  // 顶层字符串键最终胜出
  for (const [mk, mv] of Object.entries(raw)) {
    if (mk === 'phrases' || typeof mv !== 'string') continue
    flat[String(mk)] = mv
  }
  return flat
}

let current: Locale = 'zh-CN'

function normalize(raw?: string | null): Locale {
  const s = String(raw || '')
    .trim()
    .toLowerCase()
  if (s.startsWith('en')) return 'en'
  if (s.startsWith('zh')) return 'zh-CN'
  return 'zh-CN'
}

export function getLocale(): Locale {
  return current
}

export function setLocale(locale: string) {
  current = normalize(locale)
  try {
    localStorage.setItem(STORAGE_KEY, current)
  } catch {
    /* ignore */
  }
  try {
    document.documentElement.lang = current === 'en' ? 'en' : 'zh-CN'
  } catch {
    /* ignore */
  }
  // 通知订阅者（简易）
  window.dispatchEvent(new CustomEvent('fml:locale', { detail: current }))
}

export function initLocale() {
  let saved = ''
  try {
    saved = localStorage.getItem(STORAGE_KEY) || ''
  } catch {
    /* ignore */
  }
  if (!saved && typeof navigator !== 'undefined') {
    saved = navigator.language || ''
  }
  setLocale(saved || 'zh-CN')
}

export function t(msgid: string, params?: Record<string, string | number>): string {
  if (!msgid) return ''
  const cat = catalogs[current] || {}
  let text = cat[msgid]
  if (text == null) {
    // zh：回退原文；en：再试 phrases / 原文
    text = current.startsWith('zh') ? msgid : (cat[msgid] ?? msgid)
  }
  if (params) {
    text = text.replace(/\{(\w+)\}/g, (_, k: string) =>
      params[k] != null ? String(params[k]) : `{${k}}`,
    )
  }
  return text
}

/** code → map[code] 当作 msgid 再翻译 */
export function td(map: Record<string, string>, code: string, fallback?: string): string {
  const msgid = map[code]
  if (msgid == null) return fallback != null ? fallback : code
  return t(msgid)
}

/** 模板里短写 */
export function useI18n() {
  return { t, td, locale: () => current, setLocale, getLocale }
}

export function localeHeader(): Record<string, string> {
  return {
    'Accept-Language': current === 'en' ? 'en' : 'zh-CN',
    'X-Locale': current,
  }
}
