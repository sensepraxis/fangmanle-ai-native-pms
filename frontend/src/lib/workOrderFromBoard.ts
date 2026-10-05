// SPDX-License-Identifier: Apache-2.0
import type { WorkOrderTask } from '../components/WorkOrderDrawer.vue'
import { t } from './i18n'

const STATUS_MAP: Record<string, { label: string; cls: string; step: number; done?: boolean }> = {
  open: { label: '待处理', cls: 'rose', step: 1 },
  repairing: { label: '维修中', cls: 'blue', step: 2 },
  closed: { label: '已完成', cls: 'slate', step: 3, done: true },
}

function roomLabel(room?: string, loc?: string, name?: string) {
  if (room) return String(room)
  if (loc) return String(loc).replace(/\s*房$/, '')
  return name || '—'
}

function mapMaintStatus(s?: string) {
  if (s === 'doing') return 'repairing'
  if (s === 'done') return 'closed'
  return 'open'
}

function mapDamageStatus(s?: string) {
  if (s === 'repairing') return 'repairing'
  if (s === 'open') return 'open'
  return 'closed'
}

function partHint(assetName: string, message: string) {
  const text = `${assetName} ${message}`
  if (/门锁|电量|电池/.test(text)) return t('已消耗 1x 智能门锁电池')
  if (/空调|滤网/.test(text)) return t('建议领用空调滤网')
  if (/淋浴|喷头|卫浴|马桶|水龙头|花洒/.test(text)) return t('建议核对淋浴/水龙头备件')
  return ''
}

function normKey(s: string | null | undefined) {
  return String(s || '')
    .replace(/\s+/g, '')
    .toLowerCase()
}

export type WoIndex = {
  byWoId: Map<string, WorkOrderTask>
  byName: Map<string, WorkOrderTask>
}

export function buildWorkOrderIndex(raw: {
  damages: any[]
  alerts: any[]
  maintenance: any[]
  assets: any[]
}): WoIndex {
  const byWoId = new Map<string, WorkOrderTask>()
  const byName = new Map<string, WorkOrderTask>()
  const byId = Object.fromEntries((raw.assets || []).map((a) => [a.id, a]))

  const register = (task: WorkOrderTask, names: Array<string | null | undefined>) => {
    byWoId.set(task.woId, task)
    for (const n of names) {
      const k = normKey(n)
      if (k) byName.set(k, task)
    }
  }

  for (const m of raw.maintenance || []) {
    const a = byId[m.asset_id] || {}
    const rawSt = mapMaintStatus(m.status)
    const ui = STATUS_MAP[rawSt]
    const title = m.note || m.task_type || a.name || '维保任务'
    const task: WorkOrderTask = {
      woId: `WO-${m.id}`,
      assetId: m.asset_id,
      assetName: a.name || '',
      assetNo:
        a.asset_no || a.sn || (m.asset_id ? `EQ-${String(m.asset_id).padStart(5, '0')}` : ''),
      type: m.task_type || '维保',
      raw: rawSt,
      room: roomLabel(a.room_no, a.location, a.name),
      title,
      status: ui.label,
      statusCls: ui.cls,
      time: m.due_date
        ? `到期 ${String(m.due_date).slice(0, 10)}`
        : m.completed_at
          ? String(m.completed_at).replace('T', ' ').slice(0, 16)
          : '',
      createdAt: m.due_date ? String(m.due_date).slice(0, 10) : '',
      by: m.task_type || '工程维保',
      part: rawSt === 'repairing' ? partHint(a.name || '', title) : '',
      worker: rawSt === 'repairing' && m.owner ? `${m.owner}（预计 15 分钟完成）` : m.owner || '',
      executor: /外协|授权|合同/.test(String(m.owner || '')) ? 'vendor' : 'internal',
      done: !!ui.done,
      step: ui.step,
    }
    register(task, [title, a.name, `维保#${m.id}`, `维修#${m.id}`])
  }

  for (const al of raw.alerts || []) {
    if (al.status && al.status !== 'open') continue
    const aid = al.asset_id
    const a = aid ? byId[aid] || {} : {}
    const rawSt = /电量|电池|iot/i.test(`${al.alert_type} ${al.message}`) ? 'repairing' : 'open'
    const ui = STATUS_MAP[rawSt]
    const title = al.message || al.asset_name || '设备告警'
    const task: WorkOrderTask = {
      woId: `AL-${al.id}`,
      assetId: aid,
      assetName: al.asset_name || a.name || '',
      assetNo: a.asset_no || a.sn || (aid ? `EQ-${String(aid).padStart(5, '0')}` : ''),
      type: al.severity === 'high' ? '紧急报修' : 'IoT 告警',
      raw: rawSt,
      room: roomLabel(al.room_no || a.room_no, al.floor || a.location, al.asset_name || a.name),
      title,
      status: ui.label,
      statusCls: ui.cls,
      time: al.created_at ? String(al.created_at).replace('T', ' ').slice(0, 16) : '',
      createdAt: al.created_at ? String(al.created_at).replace('T', ' ').slice(0, 16) : '',
      by: al.severity === 'high' ? '前台 / IoT 告警' : '工程巡检',
      part: rawSt === 'repairing' ? partHint(al.asset_name || a.name || '', title) : '',
      worker: rawSt === 'repairing' ? '张师傅（预计 15 分钟完成）' : '',
      executor: /外协|授权|合同|IoT/i.test(`${al.alert_type} ${al.message}`)
        ? 'vendor'
        : 'internal',
      done: false,
      step: ui.step,
    }
    register(task, [title, al.asset_name, a.name, `告警#${al.id}`])
  }

  for (const d of raw.damages || []) {
    const rawSt = mapDamageStatus(d.status)
    const ui = STATUS_MAP[rawSt]
    const title = d.item_name || d.description || '报损单'
    const task: WorkOrderTask = {
      woId: `DT-${d.id}`,
      assetId: d.asset_id,
      assetName: d.item_name || '',
      assetNo: d.room_no ? `${d.room_no}房` : '',
      type: '报损单',
      raw: rawSt,
      room: roomLabel(d.room_no, '', d.item_name),
      title,
      status: ui.label,
      statusCls: ui.cls,
      time: d.created_at ? String(d.created_at).replace('T', ' ').slice(0, 16) : '',
      createdAt: d.created_at ? String(d.created_at).replace('T', ' ').slice(0, 16) : '',
      by: d.asset_category || '设备报损',
      part: d.description || d.note || '',
      worker: rawSt === 'repairing' ? '工程部处理中' : '',
      done: !!ui.done,
      step: ui.step,
    }
    register(task, [title, d.item_name, d.description, `报损#${d.id}`])
  }

  return { byWoId, byName }
}

export type RefInput = string | { type?: string; id?: number; label?: string }

export function resolveWorkOrderRef(ref: RefInput, index: WoIndex): WorkOrderTask | null {
  if (typeof ref === 'object' && ref !== null) {
    const label = String(ref.label || '').trim()
    const type = String(ref.type || '').toLowerCase()
    const id = Number(ref.id || 0)
    if (id > 0) {
      if (type === 'damage' || type === '报损') return index.byWoId.get(`DT-${id}`) || null
      if (type === 'alert' || type === '告警') return index.byWoId.get(`AL-${id}`) || null
      if (type === 'maintenance' || type === 'maint' || type === '维保' || type === '维修') {
        return index.byWoId.get(`WO-${id}`) || null
      }
    }
    if (label) return findWorkOrderByLabel(label, index)
    return null
  }
  return findWorkOrderByLabel(String(ref), index)
}

export function findWorkOrderByLabel(label: string, index: WoIndex): WorkOrderTask | null {
  const text = String(label || '').trim()
  if (!text) return null

  const patterns: Array<[RegExp, (id: string) => string]> = [
    [/报损#(\d+)/, (id) => `DT-${id}`],
    [/告警#(\d+)/, (id) => `AL-${id}`],
    [/(?:维保|维修)#(\d+)/, (id) => `WO-${id}`],
  ]
  for (const [re, wo] of patterns) {
    const m = text.match(re)
    if (m?.[1]) {
      const hit = index.byWoId.get(wo(m[1]))
      if (hit) return hit
    }
  }

  const tail = text.split('·').pop()?.trim() || text
  const key = normKey(tail)
  if (index.byName.has(key)) return index.byName.get(key)!

  for (const [name, task] of index.byName) {
    if (key.includes(name) || name.includes(key)) return task
  }
  return null
}
