// SPDX-License-Identifier: Apache-2.0
import { t } from './i18n'

// ===== 通用格式化 =====
export const fmt = (n: number | string | null | undefined) =>
  '¥' +
  Number(n || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
export const pct = (n: number | string | null | undefined) =>
  (Number(n || 0) * 100).toFixed(1) + '%'

/** code→msgid 字典；读取时按当前 locale 翻译 */
function translatingMap(raw: Record<string, string>): Record<string, string> {
  return new Proxy(raw, {
    get(target, prop: string | symbol) {
      if (typeof prop !== 'string') return undefined
      if (prop in target) return t(target[prop])
      return undefined
    },
  }) as Record<string, string>
}

// ===== 房间状态（标准码 + 兼容旧值；界面按 locale 展示） =====
export const STATUS_CN: Record<string, string> = translatingMap({
  VC: '空净房',
  VD: '空脏房',
  OCC: '已入住房',
  EA: '预抵房',
  DO: '预离房',
  OOO: '维修房',
  BLK: '锁房',
  vacant: '空净房',
  clean: '空净房',
  inspected: '空净房',
  occupied: '已入住房',
  dirty: '空脏房',
  cleaning: '空脏房',
  maintenance: '维修房',
  ooo: '维修房',
})
export const STATUS_COLOR: Record<string, string> = {
  VC: 'room-cell room-vacant',
  VD: 'room-cell room-dirty',
  OCC: 'room-cell room-occupied',
  EA: 'room-cell room-occupied',
  DO: 'room-cell room-occupied',
  OOO: 'room-cell room-ooo',
  BLK: 'room-cell room-ooo',
  vacant: 'room-cell room-vacant',
  occupied: 'room-cell room-occupied',
  dirty: 'room-cell room-dirty',
  cleaning: 'room-cell room-clean',
  maintenance: 'room-cell room-clean',
  ooo: 'room-cell room-ooo',
}
export const STATUS_DOT: Record<string, string> = {
  VC: '#10b981',
  VD: '#fb923c',
  OCC: '#2563eb',
  EA: '#3b82f6',
  DO: '#f59e0b',
  OOO: '#94a3b8',
  BLK: '#64748b',
  vacant: '#10b981',
  occupied: '#2563eb',
  dirty: '#fb923c',
  cleaning: '#fbbf24',
  maintenance: '#94a3b8',
  ooo: '#94a3b8',
}

// ===== 订单 =====
export const ORDER_ST_CN: Record<string, string> = translatingMap({
  pending: '待入住',
  confirmed: '已确认',
  checked_in: '在住',
  checked_out: '已退房',
  cancelled: '已取消',
  no_show: '未到店',
})
export const ORDER_ST_PILL: Record<string, string> = {
  pending: 'pill pill-amber',
  confirmed: 'pill pill-amber',
  checked_in: 'pill pill-blue',
  checked_out: 'pill pill-slate',
  cancelled: 'pill pill-rose',
  no_show: 'pill pill-rose',
}
export const PAY_CN: Record<string, string> = translatingMap({
  unpaid: '未支付',
  partial: '部分付',
  paid: '已支付',
  refunded: '已退',
  on_account: '挂账',
})
export const PAY_PILL: Record<string, string> = {
  unpaid: 'pill pill-rose',
  partial: 'pill pill-amber',
  paid: 'pill pill-green',
  refunded: 'pill pill-slate',
  on_account: 'pill pill-amber',
}

// ===== 价格建议 =====
export const PRICE_ST_CN: Record<string, string> = translatingMap({
  pending: '待确认',
  accepted: '已采纳',
  rejected: '已驳回',
  blocked: '已拦截',
})
export const PRICE_ST_PILL: Record<string, string> = {
  pending: 'pill pill-amber',
  accepted: 'pill pill-green',
  rejected: 'pill pill-slate',
  blocked: 'pill pill-rose',
}

// ===== 房务 =====
export const TASK_CN: Record<string, string> = translatingMap({
  clean: '清扫',
  inspect: '查房',
  turnover: '周转',
  on_demand: '临时',
})
export const TASK_ST_CN: Record<string, string> = translatingMap({
  open: '待处理',
  assigned: '已分派',
  in_progress: '进行中',
  done: '已完成',
  verified: '已核验',
})
export const TASK_ST_PILL: Record<string, string> = {
  open: 'pill pill-slate',
  assigned: 'pill pill-blue',
  in_progress: 'pill pill-amber',
  done: 'pill pill-green',
  verified: 'pill pill-green',
}

// ===== 客户 =====
export const VIP_CN: Record<string, string> = translatingMap({
  normal: '普通',
  silver: '银卡',
  gold: '金卡',
  platinum: '白金',
})
export const VIP_PILL: Record<string, string> = {
  normal: 'pill pill-slate',
  silver: 'pill pill-blue',
  gold: 'pill pill-amber',
  platinum: 'pill pill-rose',
}
export const CONF_CN: Record<string, string> = translatingMap({
  high: '高',
  medium: '中',
  low: '低',
})

/** 房间楼层数字。主档 floor=0 视为缺失（0301 首字符误判）；房号 0301→3、0101→1、1001→10。 */
export function roomFloorNum(r: { floor?: any; room_no?: any } | null | undefined): number {
  const f = Number(r?.floor)
  if (Number.isFinite(f) && f > 0) return f
  const digits = String(r?.room_no || '').replace(/\D/g, '')
  if (digits.length >= 4) {
    const n = Number(digits.slice(0, 2))
    if (n > 0) return n
  }
  if (digits.length >= 3) {
    const n = Number(digits[0])
    if (n > 0) return n
  }
  return 0
}

export function roomFloorLabel(r: { floor?: any; room_no?: any } | null | undefined): string {
  const n = roomFloorNum(r)
  return n > 0 ? `${n}F` : '—'
}

// ===== Toast =====
export function toast(msg: string, ok = true) {
  const el = document.createElement('div')
  el.style.cssText =
    'position:fixed;top:18px;right:18px;z-index:9999;padding:8px 16px;border-radius:8px;color:#fff;font-size:13px;box-shadow:0 4px 16px rgba(0,0,0,.16);background:' +
    (ok ? '#059669' : '#e11d48') +
    ';font-family:inherit'
  el.textContent = msg
  document.body.appendChild(el)
  setTimeout(() => el.remove(), 2500)
}
