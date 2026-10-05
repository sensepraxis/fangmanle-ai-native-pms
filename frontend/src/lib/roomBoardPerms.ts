// SPDX-License-Identifier: Apache-2.0
import { t } from './i18n'
/** 房态看板操作权限：对齐 RBAC 四角色 admin/gm/rm/fd（hk 能力并入 fd 有限） */
export type BoardRole = 'fd' | 'gm' | 'rm' | 'admin'

export function resolveBoardRole(code?: string | null): BoardRole {
  const c = String(code || '')
    .toLowerCase()
    .trim()
  if (c === 'fd' || c === 'front' || c === 'hk' || c === 'housekeeping') return 'fd'
  if (c === 'rm' || c === 'revenue') return 'rm'
  if (c === 'admin') return 'admin'
  // gm / mgr / fin / 空 → 店长能力
  return 'gm'
}

export type BoardAction =
  | 'checkin'
  | 'checkout'
  | 'viewOrder'
  | 'book'
  | 'hkTake'
  | 'hkDone'
  | 'hkInspect'
  | 'price'
  | 'lock'
  | 'ooo'
  | 'dirty'
  | 'extend'
  | 'changeRoom'
  | 'clearOoo'
  | 'clearLock'

const ALLOWED: Record<BoardAction, BoardRole[]> = {
  checkin: ['fd', 'gm', 'admin'],
  checkout: ['fd', 'gm', 'admin'],
  viewOrder: ['fd', 'gm', 'admin', 'rm'],
  book: ['fd', 'gm', 'admin'],
  hkTake: ['fd', 'gm', 'admin'],
  hkDone: ['fd', 'gm', 'admin'],
  hkInspect: ['fd', 'gm', 'admin'],
  price: ['gm', 'admin'],
  lock: ['gm', 'admin'],
  ooo: ['gm', 'admin'],
  dirty: ['fd', 'gm', 'admin'],
  extend: ['fd', 'gm', 'admin'],
  changeRoom: ['fd', 'gm', 'admin'],
  clearOoo: ['gm', 'admin'],
  clearLock: ['gm', 'admin'],
}

export function canBoardAction(role: BoardRole, action: BoardAction): boolean {
  return (ALLOWED[action] || []).includes(role)
}

export function roleLabel(role: BoardRole): string {
  if (role === 'fd') return t('前台')
  if (role === 'rm') return t('收益经理')
  if (role === 'admin') return t('管理员')
  return t('店长')
}
