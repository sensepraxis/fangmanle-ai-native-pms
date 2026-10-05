// SPDX-License-Identifier: Apache-2.0
// Shared API client: Bearer + { ok, data }
import { clearRbac } from '../../store/rbac'
import { localeHeader, t } from '../i18n'

// API base path: 与后端 api.py 的 API_V1_PREFIX 对齐
const BASE = '/api/v1'

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...localeHeader(), ...(extra || {}) }
  const token = localStorage.getItem('fml_token')
  if (token) h.Authorization = `Bearer ${token}`
  return h
}

function clearLocalAuth() {
  localStorage.removeItem('fml_token')
  localStorage.removeItem('fml_session')
  localStorage.removeItem('fml_user')
  clearRbac()
}

export async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: authHeaders(body ? { 'Content-Type': 'application/json' } : undefined),
    body: body ? JSON.stringify(body) : undefined,
  })
  const json: any = await res.json().catch(() => ({}))
  if (res.status === 401) {
    clearLocalAuth()
    const hash = location.hash || ''
    const onPublic =
      hash.includes('/login') ||
      hash.includes('/wecom/') ||
      hash === '#/' ||
      hash === '#' ||
      hash === '' ||
      hash.startsWith('#/?')
    if (!onPublic) {
      location.hash = '#/login'
    }
    throw new Error(json.detail || t('未登录或令牌失效'))
  }
  if (!res.ok || json.ok === false) {
    const detail = json.detail
    let msg =
      typeof detail === 'string' ? detail : detail?.[0]?.msg || json.message || t('请求失败')
    if (res.status === 405) {
      msg = t('接口未生效（Method Not Allowed），请重启后端服务后再试')
    }
    throw new Error(msg)
  }
  return json.data as T
}

export { BASE, authHeaders }
