// SPDX-License-Identifier: Apache-2.0
import { reactive, computed } from 'vue'
import { api } from '../lib/api'
import { applyRbac, clearRbac, rbacStore } from './rbac'
import { applyBranding } from '../lib/branding'

type Hotel = { id: number; name: string; code?: string; city?: string }
type SessionUser = { id?: number; username?: string; name?: string; role?: string }

export const hotelStore = reactive({
  hotelId: 1,
  hotelName: '',
  user: null as SessionUser | null,
  hotels: [] as Hotel[],
  token: (typeof localStorage !== 'undefined' && localStorage.getItem('fml_token')) || '',
})

export const currentHotel = computed(
  () => hotelStore.hotels.find((h) => h.id === hotelStore.hotelId) || null,
)

;(hotelStore as any).current = currentHotel

export function applySession(data: {
  access_token: string
  hotel_id: number
  hotel_name?: string
  user?: SessionUser
  menus?: string[]
  scopes?: string[]
}) {
  hotelStore.token = data.access_token
  hotelStore.hotelId = data.hotel_id
  hotelStore.hotelName = data.hotel_name || ''
  hotelStore.user = data.user || null
  applyRbac({
    role: data.user?.role,
    menus: data.menus,
    scopes: data.scopes,
  })
  localStorage.setItem('fml_token', data.access_token)
  localStorage.setItem(
    'fml_session',
    JSON.stringify({
      hotel_id: data.hotel_id,
      hotel_name: data.hotel_name,
      user: data.user,
    }),
  )
}

export function clearSession() {
  hotelStore.token = ''
  hotelStore.hotelName = ''
  hotelStore.user = null
  clearRbac()
  localStorage.removeItem('fml_token')
  localStorage.removeItem('fml_session')
  localStorage.removeItem('fml_user')
}

/** 用 /auth/me 校验登录态；失败则清会话并返回 false */
export async function ensureSession(): Promise<boolean> {
  const token = localStorage.getItem('fml_token')
  if (!token) {
    clearSession()
    return false
  }
  try {
    const me = await api.me()
    if (!me || (!me.user_id && !me.role)) {
      clearSession()
      return false
    }
    hotelStore.token = token
    hotelStore.user = {
      id: me.user_id,
      username: me.username,
      name: me.name,
      role: me.role,
    }
    if (me.hotel_id) hotelStore.hotelId = me.hotel_id
    if (me.hotel_name) hotelStore.hotelName = me.hotel_name
    applyRbac({
      role: me.role,
      menus: me.menus,
      scopes: me.scopes,
    })
    try {
      const b = await api.branding()
      if (b) applyBranding(b)
    } catch {
      /* pack 菜单隐藏以后端 branding 为准；失败不阻断登录 */
    }
    return true
  } catch {
    clearSession()
    return false
  }
}

export async function refreshRbac() {
  return ensureSession()
}

export async function initHotel() {
  if (!localStorage.getItem('fml_token')) {
    clearSession()
    return
  }
  const ok = await ensureSession()
  if (!ok) return
  try {
    const hs: Hotel[] = await api.listHotels()
    hotelStore.hotels = hs
    if (hs.length) {
      hotelStore.hotelId = hs[0].id
      hotelStore.hotelName = hs[0].name
    }
  } catch {
    clearSession()
  }
}

export function isLoggedIn(): boolean {
  return !!hotelStore.token && rbacStore.loaded
}
