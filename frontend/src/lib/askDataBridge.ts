// SPDX-License-Identifier: Apache-2.0
/** 营收预测「智能问数」↔ 价格助手 往返桥接 */

const CACHE_KEY = 'fml_ask_data_bridge'
const MAX_AGE_MS = 2 * 60 * 60 * 1000

export type AskDataCache = {
  hotelId: number
  findings: any[]
  askSource: string
  askGeneratedAt: string
  askWarning: string
  askStream: string
  askThinking?: string
  askModelMeta?: string
  dismissed: string[]
  savedAt: number
}

export function saveAskDataCache(cache: AskDataCache) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache))
  } catch {
    /* ignore quota */
  }
}

export function loadAskDataCache(hotelId: number): AskDataCache | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const c = JSON.parse(raw) as AskDataCache
    if (!c || c.hotelId !== hotelId) return null
    if (Date.now() - Number(c.savedAt || 0) > MAX_AGE_MS) return null
    return c
  } catch {
    return null
  }
}

/** 从问数 issue 构造价格助手入口 query */
export function pricingQueryFromIssue(r: any): Record<string, string> {
  const q: Record<string, string> = { from: 'forecast' }
  const action = r?.suggested_action
  if (action && action !== '暂不动作') q.action = String(action).slice(0, 48)
  const dim = r?.dimension || r?.reco_title
  if (dim) q.dimension = String(dim).slice(0, 48)
  if (r?.severity) q.severity = String(r.severity)
  const ev = r?.evidence || r?.trigger
  if (ev) q.evidence = String(ev).slice(0, 120)
  const impact = r?.revenue_impact || r?.est_impact
  if (impact && impact !== '—') q.impact = String(impact).slice(0, 48)
  return q
}

export function forecastReturnLocation() {
  return {
    path: '/c9-finance/revenue-forecast',
    query: { restore: '1' },
    hash: '#ask-data',
  }
}
