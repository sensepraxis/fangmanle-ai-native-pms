<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { getLocale, t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 房务任务 · 任务（列表 / 看板）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast, roomFloorNum } from '../../lib/ui'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import HousekeepingTasksSubnav from '../../components/HousekeepingTasksSubnav.vue'
import HkAiPlanDrawer, { type HkAiScene } from '../../components/HkAiPlanDrawer.vue'

const route = useRoute()
const router = useRouter()

type Status = 'waiting' | 'progress' | 'inspect' | 'done'
type TaskRow = Record<string, any> & {
  _status: Status
  floorNum: number
  floorLabel: string
  roomType: string
  taskType: string
  taskTypeLabel: string
  isVip: boolean
  urgent: boolean
  rush: boolean
  note?: string
  etaMin: number
  elapsedMin: number | null
  deadline?: string
  suggestName?: string
}

const queue = ref<TaskRow[]>([])
const staff = ref<any[]>([])
const statusSnap = ref<Record<string, any> | null>(null)
const aiAdvice = ref('')
const aiAdviceMeta = ref('')
const aiSuggestName = ref('')
const riskHint = ref('')
const finishing = ref<number | null>(null)
const acting = ref<number | null>(null)
const applyingAi = ref(false)
const aiPlanOpen = ref(false)
const aiPlanScene = ref<HkAiScene>('dispatch_assign')
const adopting = ref(false)
const proposedTasks = ref<any[]>([])
const roomsMaster = ref<any[]>([])
const newTaskOpen = ref(false)

const hasStatus = computed(() => {
  const s = statusSnap.value
  if (!s) return false
  return s.rooms_total != null || s.dirty != null || s.to_clean != null || !!s.text
})

const capacityVerdict = computed(() => {
  const s = statusSnap.value
  if (!s) return { text: '—', tone: '' as '' | 'ok' | 'bad' }
  if (s.capacity_ok === true) return { text: t('够'), tone: 'ok' as const }
  if (s.capacity_ok === false) return { text: t('不够'), tone: 'bad' as const }
  const raw = String(s.decision_text || s.text || '')
  if (/不够/.test(raw)) return { text: t('不够'), tone: 'bad' as const }
  if (/→\s*够|够了|产能充足/.test(raw)) return { text: t('够'), tone: 'ok' as const }
  return { text: '—', tone: '' as const }
})

/** 产能一句话：去掉与上方重复的房态/任务罗列 */
const decisionBrief = computed(() => {
  const raw = String(statusSnap.value?.decision_text || '')
  if (!raw) return ''
  // 后端已按 locale 翻译；英文不再依赖中文正则截取
  if (getLocale() === 'en') return raw.length <= 160 ? raw : raw.slice(0, 158) + '…'
  const m = raw.match(/(\d{2}:00 前[^。]*?(?:够|不够))/)
  if (m) return m[1]
  if (raw.length <= 72) return raw
  return raw.slice(0, 70) + '…'
})

const hotFloorNote = computed(() => {
  const s = statusSnap.value
  if (!s?.hot_floor || !s.hot_floor_open) return ''
  return t('积压最重 {floor} 楼（开放 {n}）', { floor: s.hot_floor, n: s.hot_floor_open })
})
const newTaskSaving = ref(false)
const newTask = ref({
  room_id: '' as string | number,
  task_type: 'clean',
  assignee_id: '' as string | number,
  priority: 3,
})
const reassignFor = ref<number | null>(null)

const FAIL_ITEMS = [
  t('未换布草'),
  t('有污渍'),
  t('异味'),
  t('客用品缺失'),
  t('设施未复位'),
  t('其他'),
] as const
const rejectOpen = ref(false)
const rejectTask = ref<TaskRow | null>(null)
const rejectItems = ref<string[]>([])
const rejectNote = ref('')
const rejectSaving = ref(false)

const statusFilter = ref<'all' | Status>('all')
const floorFilter = ref<'all' | string>('all')
const typeFilter = ref<'all' | string>('all')
const assigneeFilter = ref<'all' | string>('all')
const roomQuery = ref('')
const dateFilter = ref<'today' | 'tomorrow' | 'all'>('today')
const showDone = ref(false)
const selected = ref<Set<number>>(new Set())
const hoverTaskId = ref<number | null>(null)
const lastClickedId = ref<number | null>(null)

/** 批量派单面板 */
const dispatchOpen = ref(false)
const dispatchMode = ref<'single' | 'by_floor' | 'smart'>('by_floor')
const dispatchAssigneeId = ref<number | null>(null)
const dispatchStaff = ref<any[]>([])
const dispatchPreview = ref<any[]>([])
const dispatchBusy = ref(false)
const dragTaskIds = ref<number[]>([])

const viewMode = computed(() => (String(route.query.view || 'list') === 'board' ? 'board' : 'list'))

function setView(v: 'list' | 'board') {
  router.replace({ path: '/c6-housekeeping/housekeeping', query: v === 'list' ? {} : { view: v } })
}
function filterDone() {
  statusFilter.value = 'done'
  showDone.value = true
}

function rawOf(t: any) {
  return String(t?.raw_status || t?.status || '')
}

function normStatus(t: any): Status {
  const raw = rawOf(t)
  const st = String(t?.status || '')
  if (raw === 'pending_inspect' || st === 'inspect') return 'inspect'
  if (raw === 'done' || st === 'done' || st === 'closed') return 'done'
  if (['in_progress', 'progress'].includes(raw) || st === 'progress') return 'progress'
  return 'waiting'
}

const TYPE_CN: Record<string, string> = {
  clean: t('退房清洁'),
  checkout: t('退房清洁'),
  daily: t('日常清洁'),
  turn: t('日常清洁'),
  repair: t('维修'),
  maint: t('维修'),
  service: t('客中服务'),
  inspect: t('查房验收'),
}

function parseFloor(t: any) {
  return roomFloorNum(t)
}

function parseMinutes(v: any): number | null {
  if (v == null || v === '') return null
  if (typeof v === 'number' && Number.isFinite(v)) {
    // 异常测试数据：> 8 小时按分钟不合理，截断/换算
    if (v > 480) return Math.min(90, Math.round(v / 60))
    return Math.max(0, Math.round(v))
  }
  const s = String(v)
  const m = s.match(/(\d+)/)
  if (!m) return null
  let n = Number(m[1])
  if (/小时|h/i.test(s)) n *= 60
  if (n > 480) n = Math.min(90, Math.round(n / 60))
  return n
}

function enrich(t: any, staffList: any[]): TaskRow {
  const status = normStatus(t)
  const floorNum = parseFloor(t)
  const tt = String(t.task_type || t.type || 'clean').toLowerCase()
  const priority = Number(t.priority ?? t.priority_rank ?? 99)
  // 仅高优才标 VIP，避免全员 VIP
  const isVip = Boolean(t.vip) || priority <= 1 || Boolean(t.priority_flag && priority <= 2)
  const urgent = priority <= 1 || Boolean(t.urgent)
  const rush = Boolean(t.rush) || priority === 2
  const etaMin = parseMinutes(t.eta_min ?? t.estimate_min) ?? (tt.includes('repair') ? 40 : 25)
  let elapsedMin = parseMinutes(t.elapsed_min ?? t.elapsed)
  if (elapsedMin != null && elapsedMin > 180) elapsedMin = Math.min(45, Math.round(elapsedMin / 30))
  if (status === 'progress' && elapsedMin == null && t.created_at) {
    const created = Date.parse(t.created_at)
    if (Number.isFinite(created)) {
      elapsedMin = Math.max(1, Math.round((Date.now() - created) / 60000))
      if (elapsedMin > 180) elapsedMin = Math.min(45, Math.round(elapsedMin / 30))
    }
  }

  // 推荐就近空闲/低负载保洁（人员名单来自 API / 排班）
  const sameFloor = staffList.filter((s) => {
    const fl = Number(String(s.room || s.area || '').match(/(\d)/)?.[1] || 0)
    return (
      fl === floorNum ||
      String(s.area || '').includes(`${floorNum}F`) ||
      String(s.area || '').includes(`${floorNum}楼`)
    )
  })
  const idle = staffList.filter((s) => s._status === 'idle')
  const suggest =
    sameFloor.find((s) => s._status === 'idle') ||
    idle[0] ||
    sameFloor[0] ||
    staffList.find((s) => s._status !== 'rest')

  return {
    ...t,
    _status: status,
    floorNum,
    floorLabel: floorNum ? `${floorNum}F` : '—',
    roomType: t.room_type || t.room_type_name || '—',
    taskType:
      tt.includes('repair') || tt.includes('maint')
        ? 'repair'
        : tt.includes('service')
          ? 'service'
          : tt.includes('daily') || tt.includes('turn')
            ? 'daily'
            : 'clean',
    taskTypeLabel: TYPE_CN[tt] || t.title || t('退房清洁'),
    isVip,
    urgent,
    rush,
    note: t.fail_reason || t.note || t.tip || '',
    fail_reason: t.fail_reason || '',
    fail_count: Number(t.fail_count || 0),
    escalate: Boolean(t.escalate) || Number(t.fail_count || 0) >= 2,
    etaMin,
    elapsedMin: elapsedMin ?? null,
    deadline: t.deadline || undefined,
    suggestName: status === 'waiting' ? suggest?.name : undefined,
    assignee: t.assignee || '',
  }
}

function canStart(t: any) {
  const id = Number(t?.id)
  if (!Number.isFinite(id) || id <= 0 || t?.synthetic) return false
  return t._status === 'waiting' || ['open', 'assigned', 'rework'].includes(rawOf(t))
}
function canFinish(t: any) {
  const id = Number(t?.id)
  if (!Number.isFinite(id) || id <= 0 || t?.synthetic) return false
  return t._status === 'progress'
}
function canInspect(t: any) {
  const id = Number(t?.id)
  if (!Number.isFinite(id) || id <= 0 || t?.synthetic) return false
  return t._status === 'inspect'
}

function resolveStaffId(name?: string | null): number | undefined {
  if (!name) return undefined
  const s = staff.value.find((x) => x.name === name || String(x.id) === String(name))
  const id = Number(s?.id)
  return Number.isFinite(id) && id > 0 ? id : undefined
}

function pickReassignTarget(t: TaskRow): { id?: number; name: string } | null {
  const candidates = staff.value.filter((s) => s._status !== 'rest' && Number(s.id) > 0)
  const idle = candidates.filter((s) => s._status === 'idle')
  const pool = idle.length ? idle : candidates
  if (!pool.length) return null
  const cur = String(t.assignee || '')
  const next = pool.find((s) => s.name !== cur) || pool[0]
  return { id: Number(next.id), name: next.name }
}

async function startTask(task: any, e?: Event) {
  e?.stopPropagation?.()
  if (!canStart(task) || acting.value != null) return
  const id = Number(task.id)
  acting.value = id
  try {
    const name = task.suggestName || aiSuggestName.value || ''
    const assigneeId = resolveStaffId(name)
    await api.hkStart(id, {
      ...(assigneeId ? { assignee_id: assigneeId } : {}),
      ...(name && !assigneeId ? { assignee_name: name } : {}),
    })
    toast(
      name
        ? t('{room} 已派单给 {name}', { room: task.room_no, name })
        : t('{room} 已派单并开始清洁', { room: task.room_no }),
    )
    await load()
  } catch (err: any) {
    toast(t(err?.message || '派单失败'), false)
  } finally {
    acting.value = null
  }
}

async function finishTask(task: any, e?: Event) {
  e?.stopPropagation?.()
  if (!canFinish(task) || finishing.value != null) return
  const id = Number(task.id)
  finishing.value = id
  try {
    const isRepair = task.taskType === 'repair' || String(task.task_type || '').includes('repair')
    await api.finishHousekeeping(id, isRepair ? { to_status: 'VC' } : undefined)
    toast(
      isRepair
        ? t('{room} 维修完成，已恢复空净', { room: task.room_no })
        : t('{room} 已完成，待验收', { room: task.room_no }),
    )
    await load()
  } catch (err: any) {
    toast(t(err?.message || '提交失败'), false)
  } finally {
    finishing.value = null
  }
}

async function inspectTask(task: any, passed: boolean, e?: Event) {
  e?.stopPropagation?.()
  if (!canInspect(task) || acting.value != null) return
  if (!passed) {
    openReject(task)
    return
  }
  const id = Number(task.id)
  acting.value = id
  try {
    await api.hkInspect(id, { passed: true })
    toast(t('{room} 验收通过', { room: task.room_no }))
    await load()
  } catch (err: any) {
    toast(t(err?.message || '查房失败'), false)
  } finally {
    acting.value = null
  }
}

function openReject(t: TaskRow) {
  rejectTask.value = t
  rejectItems.value = []
  rejectNote.value = ''
  rejectOpen.value = true
}

function toggleRejectItem(item: string) {
  const i = rejectItems.value.indexOf(item)
  if (i >= 0) rejectItems.value.splice(i, 1)
  else rejectItems.value.push(item)
}

async function submitReject() {
  const task = rejectTask.value
  if (!task || rejectSaving.value) return
  if (!rejectItems.value.length && !rejectNote.value.trim()) {
    toast(t('请勾选不合格项或填写原因'), false)
    return
  }
  rejectSaving.value = true
  acting.value = Number(task.id)
  try {
    const res = await api.hkInspect(Number(task.id), {
      passed: false,
      fail_items: [...rejectItems.value],
      fail_reason: rejectNote.value.trim() || undefined,
    })
    rejectOpen.value = false
    if (res?.escalate) {
      toast(
        t('{room} 已连续退回 {n} 次，请通知店长跟进', {
          room: task.room_no,
          n: res.fail_count || 2,
        }),
        false,
      )
    } else {
      toast(
        t('{room} 已退回重扫：{reason}', {
          room: task.room_no,
          reason: res?.fail_reason || t('查房不通过'),
        }),
      )
    }
    await load()
  } catch (err: any) {
    toast(t(err?.message || '退回失败'), false)
  } finally {
    rejectSaving.value = false
    acting.value = null
  }
}

function openReassign(t: TaskRow, e?: Event) {
  e?.stopPropagation?.()
  reassignFor.value = reassignFor.value === Number(t.id) ? null : Number(t.id)
}

async function confirmReassign(task: TaskRow, staffIdOrName: string | number) {
  const id = Number(task.id)
  if (!Number.isFinite(id) || id <= 0) return
  acting.value = id
  try {
    const sid = Number(staffIdOrName)
    const payload =
      Number.isFinite(sid) && sid > 0
        ? { assignee_id: sid }
        : { assignee_name: String(staffIdOrName) }
    const res = await api.hkAssign(id, payload)
    const name =
      res?.assignee || staff.value.find((s) => Number(s.id) === sid)?.name || String(staffIdOrName)
    toast(t('{room} 已改派给 {name}', { room: task.room_no, name }))
    reassignFor.value = null
    await load()
  } catch (err: any) {
    toast(t(err?.message || '改派失败'), false)
  } finally {
    acting.value = null
  }
}

async function quickReassign(t: TaskRow, e?: Event) {
  e?.stopPropagation?.()
  const pick = t.suggestName
    ? { id: resolveStaffId(t.suggestName), name: t.suggestName }
    : pickReassignTarget(t)
  if (!pick?.name) {
    openReassign(t, e)
    return
  }
  await confirmReassign(t, pick.id || pick.name)
}

async function markIgnore(task: TaskRow, e?: Event) {
  e?.stopPropagation?.()
  const id = Number(task.id)
  if (!Number.isFinite(id) || id <= 0 || acting.value != null) return
  acting.value = id
  try {
    await api.hkIgnore(id, { reason: t('主管忽略') })
    toast(t('{room} 已忽略', { room: task.room_no }))
    selected.value.delete(id)
    await load()
  } catch (err: any) {
    toast(t(err?.message || '忽略失败'), false)
  } finally {
    acting.value = null
  }
}

async function urge(task: TaskRow, e?: Event) {
  e?.stopPropagation?.()
  const id = Number(task.id)
  if (!Number.isFinite(id) || id <= 0 || acting.value != null) return
  acting.value = id
  try {
    await api.hkUrge(id)
    toast(
      t('已催办 {who} · {room}（已标紧急）', {
        who: task.assignee || t('执行人'),
        room: task.room_no,
      }),
    )
    await load()
  } catch (err: any) {
    toast(t(err?.message || '催办失败'), false)
  } finally {
    acting.value = null
  }
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const rawStaff = (board?.staff || []).map((s: any) => {
      const busy = s.busy ?? Number(s.open || 0) > 0
      let st: 'work' | 'idle' | 'rest' | 'maint' = 'idle'
      if (s.status === 'rest' || s.statusLabel === t('休息')) st = 'rest'
      else if (busy) st = /工程|维保|维修/.test(String(s.role || s.title || '')) ? 'maint' : 'work'
      return {
        ...s,
        busy,
        _status: st,
        statusLabel:
          s.statusLabel ||
          (st === 'work'
            ? t('工作中')
            : st === 'rest'
              ? t('休息')
              : st === 'maint'
                ? t('维修中')
                : t('空闲')),
        room: s.area || s.room || s.current_task || '',
        role: s.role || s.title || t('保洁'),
        open: Number(s.open || 0),
        done: Number(s.done || 0),
      }
    })
    // 补负载：按任务统计（仅真实库内任务）
    const rawTasks = (board?.queue || board?.tasks || []).filter(
      (t: any) => Number(t?.id) > 0 && !t?.synthetic,
    )
    const tmpQueue = rawTasks.map((t: any) => enrich(t, rawStaff))
    for (const s of rawStaff) {
      s.open = tmpQueue.filter((t) => t.assignee === s.name && t._status === 'progress').length
      s.done = tmpQueue.filter((t) => t.assignee === s.name && t._status === 'done').length
      s.loadLabel =
        s._status === 'rest'
          ? t('休息')
          : s._status === 'idle'
            ? t('空闲')
            : t('进行中 {open} · 今日完成 {done}', { open: s.open, done: s.done })
    }
    staff.value = rawStaff
    queue.value = tmpQueue.map((t) => enrich(t, rawStaff))
    roomsMaster.value = Array.isArray(board?.rooms) ? board.rooms : []

    const snap = board?.status_snapshot
    statusSnap.value =
      snap && typeof snap === 'object' ? snap : board?.flow_hint ? { text: board.flow_hint } : null
    aiSuggestName.value =
      rawStaff.find((s) => s._status === 'idle')?.name || rawStaff[0]?.name || ''
    riskHint.value = ''
  } catch {
    queue.value = []
    staff.value = []
    roomsMaster.value = []
    statusSnap.value = null
    riskHint.value = ''
  }
}

onMounted(load)
watch(
  () => hotelStore.hotelId,
  () => {
    aiAdvice.value = ''
    aiAdviceMeta.value = ''
    proposedTasks.value = []
    load()
  },
)
watch(
  () => route.query.date,
  (d) => {
    if (d === 'tomorrow' || d === 'today' || d === 'all') dateFilter.value = d
  },
  { immediate: true },
)

const floors = computed(() => {
  const set = new Set(queue.value.map((row) => row.floorLabel).filter((x) => x && x !== '—'))
  return Array.from(set).sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
})

const assignees = computed(() => {
  const set = new Set(
    queue.value
      .map((row) => row.assignee)
      .filter((x: string) => x && x !== t('待分配') && x !== t('未分配')),
  )
  return Array.from(set).sort() as string[]
})

const overview = computed(() => {
  const all = queue.value
  const done = all.filter((t) => t._status === 'done').length
  const total = all.length
  return {
    total,
    waiting: all.filter((t) => t._status === 'waiting').length,
    progress: all.filter((t) => t._status === 'progress').length,
    inspect: all.filter((t) => t._status === 'inspect').length,
    done,
    rate: total ? Math.round((done / total) * 100) : 0,
  }
})

const filteredBase = computed(() => {
  return queue.value.filter((row) => {
    if (statusFilter.value !== 'all' && row._status !== statusFilter.value) return false
    if (floorFilter.value !== 'all' && row.floorLabel !== floorFilter.value) return false
    if (typeFilter.value !== 'all' && row.taskType !== typeFilter.value) return false
    if (assigneeFilter.value !== 'all') {
      if ((row.assignee || '未分配') !== assigneeFilter.value) return false
    }
    if (roomQuery.value.trim()) {
      const q = roomQuery.value.trim()
      if (!String(row.room_no || '').includes(q)) return false
    }
    // 日期：数据默认今日；明日筛出空或带 tomorrow 标记
    if (dateFilter.value === 'tomorrow') return Boolean(row.for_tomorrow)
    if (dateFilter.value === 'today' && row.for_tomorrow) return false
    return true
  })
})

const listTasks = computed(() => {
  const active = filteredBase.value.filter((t) => t._status !== 'done')
  const done = filteredBase.value.filter((t) => t._status === 'done')
  if (statusFilter.value === 'done') return done
  if (showDone.value || statusFilter.value === 'all') {
    // 全部时：未完成在前，已完成默认折叠不展示，除非 showDone
    return showDone.value
      ? [...active, ...done]
      : active.length
        ? active
        : filteredBase.value.filter((t) => t._status !== 'done')
  }
  return active
})

const doneCountHidden = computed(
  () => filteredBase.value.filter((t) => t._status === 'done').length,
)

const kanban = computed(() => ({
  waiting: filteredBase.value.filter((t) => t._status === 'waiting'),
  progress: filteredBase.value.filter((t) => t._status === 'progress'),
  inspect: filteredBase.value.filter((t) => t._status === 'inspect'),
  done: filteredBase.value.filter((t) => t._status === 'done'),
}))

const STATUS_UI: Record<Status, { label: string; cls: string }> = {
  waiting: { label: t('待分配'), cls: 'st-wait' },
  progress: { label: t('进行中'), cls: 'st-prog' },
  inspect: { label: t('待验收'), cls: 'st-insp' },
  done: { label: t('已完成'), cls: 'st-done' },
}

const COLS = [
  { key: 'waiting' as const, title: t('待分配'), tone: 'wait' },
  { key: 'progress' as const, title: t('进行中'), tone: 'prog' },
  { key: 'inspect' as const, title: t('待验收'), tone: 'insp' },
  { key: 'done' as const, title: t('已完成'), tone: 'done' },
]

function timeLine(task: TaskRow) {
  if (task._status === 'progress' && task.elapsedMin != null)
    return t('已用 {n} 分钟', { n: task.elapsedMin })
  if (task._status === 'waiting') {
    const parts = [t('预计 {n} 分钟', { n: task.etaMin })]
    if (task.deadline) parts.push(t('截止 {d}', { d: task.deadline }))
    return parts.join(' · ')
  }
  if (task._status === 'inspect') return t('待领班验收')
  return t('已完成')
}

function toggleSelect(id: number, e?: MouseEvent) {
  e?.stopPropagation?.()
  const next = new Set(selected.value)
  if (e?.shiftKey && lastClickedId.value != null) {
    const ids = listTasks.value.map((t) => Number(t.id)).filter((x) => x > 0)
    const a = ids.indexOf(lastClickedId.value)
    const b = ids.indexOf(id)
    if (a >= 0 && b >= 0) {
      const [lo, hi] = a < b ? [a, b] : [b, a]
      for (let i = lo; i <= hi; i++) next.add(ids[i])
      selected.value = next
      lastClickedId.value = id
      return
    }
  }
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
  lastClickedId.value = id
}

function clearSelected() {
  selected.value = new Set()
  lastClickedId.value = null
}

const selectedTasks = computed(() =>
  queue.value.filter((t) => Number.isFinite(Number(t.id)) && selected.value.has(Number(t.id))),
)

async function openDispatchPanel(ids?: number[]) {
  const list = (
    ids && ids.length ? queue.value.filter((t) => ids.includes(Number(t.id))) : selectedTasks.value
  ).filter(canStart)
  if (!list.length) return toast(t('请先选择可派单的待分配任务'), false)
  selected.value = new Set(list.map((t) => Number(t.id)))
  dispatchOpen.value = true
  dispatchMode.value = 'by_floor'
  dispatchBusy.value = true
  try {
    dispatchStaff.value = (await api.hkDispatchStaff(hotelStore.hotelId)) || []
    if (!dispatchAssigneeId.value && dispatchStaff.value.length) {
      dispatchAssigneeId.value = Number(dispatchStaff.value[0].id)
    }
    await refreshDispatchPreview()
  } catch (e: any) {
    toast(t(e?.message || '加载派单面板失败'), false)
    dispatchOpen.value = false
  } finally {
    dispatchBusy.value = false
  }
}

async function refreshDispatchPreview() {
  const ids = [...selected.value]
  if (!ids.length) {
    dispatchPreview.value = []
    return
  }
  if (dispatchMode.value === 'single' && !dispatchAssigneeId.value) {
    dispatchPreview.value = []
    return
  }
  try {
    const res = await api.hkBatchDispatch({
      task_ids: ids,
      mode: dispatchMode.value,
      assignee_id: dispatchMode.value === 'single' ? Number(dispatchAssigneeId.value) : undefined,
      preview: true,
    })
    dispatchPreview.value = res?.items || []
    if (res?.staff?.length) dispatchStaff.value = res.staff
  } catch (e: any) {
    dispatchPreview.value = []
    toast(t(e?.message || '预览失败'), false)
  }
}

watch([dispatchMode, dispatchAssigneeId], () => {
  if (dispatchOpen.value) refreshDispatchPreview()
})

async function confirmDispatch() {
  const ids = [...selected.value]
  if (!ids.length) return
  if (dispatchMode.value === 'single' && !dispatchAssigneeId.value) {
    return toast(t('请选择保洁员'), false)
  }
  dispatchBusy.value = true
  applyingAi.value = true
  try {
    const res = await api.hkBatchDispatch({
      task_ids: ids,
      mode: dispatchMode.value,
      assignee_id: dispatchMode.value === 'single' ? Number(dispatchAssigneeId.value) : undefined,
      preview: false,
      notify: true,
    })
    const n = res?.count || 0
    const rooms = (res?.items || [])
      .map((x: any) => x.room_no)
      .slice(0, 4)
      .join('/')
    const pushOk = (res?.wecom || []).filter((w: any) => w.pushed).length
    const pushHint = (res?.wecom || []).find((w: any) => !w.pushed)?.hint
    toast(
      t('已派单 {n} 项{rooms}{push}', {
        n,
        rooms: rooms ? t('（{rooms}{more}）', { rooms, more: n > 4 ? '…' : '' }) : '',
        push: pushOk
          ? t(' · 企微已推 {n} 人', { n: pushOk })
          : pushHint
            ? t(' · 企微：{hint}', { hint: pushHint })
            : '',
      }),
    )
    dispatchOpen.value = false
    clearSelected()
    await load()
  } catch (e: any) {
    toast(t(e?.message || '批量派单失败'), false)
  } finally {
    dispatchBusy.value = false
    applyingAi.value = false
  }
}

function batchStart() {
  openDispatchPanel()
}

async function batchFinish() {
  const list = selectedTasks.value.filter(canFinish)
  if (!list.length) return toast(t('没有可完成的任务'), false)
  applyingAi.value = true
  try {
    for (const row of list) await api.finishHousekeeping(Number(row.id))
    toast(t('已批量完成 {n} 个任务', { n: list.length }))
    clearSelected()
    await load()
  } catch (e: any) {
    toast(t(e?.message || '批量完成失败'), false)
  } finally {
    applyingAi.value = false
  }
}

async function batchInspect() {
  const list = selectedTasks.value.filter(canInspect)
  if (!list.length) return toast(t('没有可验收的任务'), false)
  applyingAi.value = true
  try {
    for (const row of list) await api.hkInspect(Number(row.id), { passed: true })
    toast(t('已批量验收 {n} 个任务', { n: list.length }))
    clearSelected()
    await load()
  } catch (e: any) {
    toast(t(e?.message || '批量验收失败'), false)
  } finally {
    applyingAi.value = false
  }
}

/** 看板：Shift 多选 */
function onKanbanCardClick(t: TaskRow, e: MouseEvent) {
  const id = Number(t.id)
  if (!Number.isFinite(id) || id <= 0) return
  if (e.shiftKey || e.metaKey || e.ctrlKey) {
    e.preventDefault()
    const next = new Set(selected.value)
    if (e.shiftKey && lastClickedId.value != null) {
      const flat = COLS.flatMap((c) => kanban.value[c.key].map((x) => Number(x.id)))
      const a = flat.indexOf(lastClickedId.value)
      const b = flat.indexOf(id)
      if (a >= 0 && b >= 0) {
        const [lo, hi] = a < b ? [a, b] : [b, a]
        for (let i = lo; i <= hi; i++) if (flat[i] > 0) next.add(flat[i])
        selected.value = next
        lastClickedId.value = id
        return
      }
    }
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selected.value = next
    lastClickedId.value = id
  }
}

function onKanbanDragStart(t: TaskRow, e: DragEvent) {
  const id = Number(t.id)
  if (!Number.isFinite(id) || id <= 0) return
  let ids = selected.value.has(id) ? [...selected.value] : [id]
  ids = ids.filter((x) => {
    const row = queue.value.find((q) => Number(q.id) === x)
    return row && canStart(row)
  })
  if (!ids.length) {
    e.preventDefault()
    return
  }
  dragTaskIds.value = ids
  e.dataTransfer?.setData('text/plain', ids.join(','))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}

function onKanbanDragEnd() {
  dragTaskIds.value = []
}

function onProgressColDrop(e: DragEvent) {
  e.preventDefault()
  const raw = e.dataTransfer?.getData('text/plain') || dragTaskIds.value.join(',')
  const ids = raw
    .split(',')
    .map((x) => Number(x))
    .filter((x) => x > 0)
  dragTaskIds.value = []
  if (!ids.length) return
  openDispatchPanel(ids)
}

function onProgressColDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

async function applyAiSuggest() {
  // 兼容旧「直接应用」；主按钮改为 Harness 确认流
  aiPlanScene.value = 'dispatch_assign'
  aiPlanOpen.value = true
}

function openAiPlan(scene: HkAiScene) {
  aiPlanScene.value = scene
  aiPlanOpen.value = true
}

async function onAiPlanConfirmed(res: any) {
  aiAdvice.value = res?.message || t('安排已生效')
  aiAdviceMeta.value = `已执行 ${res?.applied || 0} 项`
  await load()
}

async function adoptProposed() {
  if (!proposedTasks.value.length || adopting.value) return
  adopting.value = true
  try {
    const res = await api.hkCreateTasks(hotelStore.hotelId, {
      tasks: proposedTasks.value.map((t) => ({
        room_id: Number(t.room_id),
        task_type: t.task_type || 'clean',
        assignee_id: t.assignee_id ? Number(t.assignee_id) : undefined,
        priority: Number(t.priority) || 3,
      })),
    })
    const n = res?.created ?? res?.count ?? proposedTasks.value.length
    proposedTasks.value = []
    toast(t('已采纳并新建 {n} 个任务', { n }))
    await load()
  } catch (e: any) {
    toast(t(e?.message || '采纳失败'), false)
  } finally {
    adopting.value = false
  }
}

function openNewTask() {
  if (!newTask.value.room_id && roomsMaster.value[0]?.id) {
    newTask.value.room_id = roomsMaster.value[0].id
  }
  newTaskOpen.value = true
}

async function submitNewTask() {
  const rid = Number(newTask.value.room_id)
  if (!Number.isFinite(rid) || rid <= 0) {
    toast(t('请选择房间'), false)
    return
  }
  newTaskSaving.value = true
  try {
    const aid = Number(newTask.value.assignee_id)
    const res = await api.hkCreateTasks(hotelStore.hotelId, {
      room_id: rid,
      task_type: newTask.value.task_type || 'clean',
      assignee_id: Number.isFinite(aid) && aid > 0 ? aid : undefined,
      priority: Number(newTask.value.priority) || 3,
    })
    const row = res?.tasks?.[0]
    const skipped = res?.skipped > 0 && res?.created === 0
    toast(
      skipped
        ? t('{room} 已有未完成的同类任务', { room: row?.room_no || '' })
        : t('已新建 {room} {title}', {
            room: row?.room_no || '',
            title: row?.title || t('任务'),
          }),
    )
    newTaskOpen.value = false
    newTask.value = { room_id: rid, task_type: 'clean', assignee_id: '', priority: 3 }
    await load()
  } catch (e: any) {
    toast(t(e?.message || '新建任务失败'), false)
  } finally {
    newTaskSaving.value = false
  }
}

function clickOverview(key: 'all' | Status) {
  statusFilter.value = key
  if (key === 'done') showDone.value = true
}

function staffHighlight(s: any) {
  if (!hoverTaskId.value) return false
  const t = queue.value.find((x) => Number(x.id) === hoverTaskId.value)
  return Boolean(t?.suggestName && t.suggestName === s.name)
}

function goRoom(t: TaskRow) {
  router.push({ path: '/room-board', query: { highlight: String(t.room_no || '') } })
}
</script>

<template>
  <div class="page tasks-page">
    <RoomOpsNav />
    <HousekeepingTasksSubnav />

    <div v-if="hasStatus" class="status-panel" :class="{ advised: !!aiAdvice }">
      <div class="status-top">
        <div class="status-title">
          <span class="material-symbols-outlined tip-ico">{{
            aiAdvice ? 'auto_awesome' : 'monitoring'
          }}</span>
          <strong>{{ t('系统现状') }}</strong>
        </div>
        <div class="ai-actions">
          <template v-if="commercialEnabled()">
            <button
              v-if="proposedTasks.length"
              type="button"
              class="btn-adopt"
              :disabled="adopting || applyingAi"
              @click="adoptProposed"
            >
              {{ adopting ? t('采纳中…') : t('AI一键采纳') }}
            </button>
            <button
              type="button"
              class="btn-apply"
              :disabled="adopting"
              @click="openAiPlan('cleaning_plan')"
            >
              {{ t('AI清扫安排') }}
            </button>
            <button
              type="button"
              class="btn-apply"
              :disabled="adopting"
              @click="openAiPlan('dispatch_assign')"
            >
              {{ t('AI智能派工') }}
            </button>
          </template>
        </div>
      </div>

      <div class="status-grid">
        <section class="status-group" :aria-label="t('房态')">
          <div class="sg-label">{{ t('房态') }}</div>
          <div class="sg-metrics">
            <div class="sg-item">
              <span class="sg-k">{{ t('总房') }}</span>
              <strong class="sg-v">{{ statusSnap?.rooms_total ?? '—' }}</strong>
            </div>
            <div class="sg-item dirty">
              <span class="sg-k">{{ t('脏房') }}</span>
              <strong class="sg-v">{{ statusSnap?.dirty ?? '—' }}</strong>
            </div>
            <div class="sg-item clean">
              <span class="sg-k">{{ t('净房') }}</span>
              <strong class="sg-v">{{ statusSnap?.vacant ?? '—' }}</strong>
            </div>
            <div class="sg-item mute">
              <span class="sg-k">{{ t('占用/锁房') }}</span>
              <strong class="sg-v">{{
                statusSnap ? Number(statusSnap.occupied || 0) + Number(statusSnap.ooo || 0) : '—'
              }}</strong>
            </div>
          </div>
        </section>

        <section class="status-group" :aria-label="t('清洁任务')">
          <div class="sg-label">{{ t('清洁任务') }}</div>
          <div class="sg-metrics">
            <div class="sg-item primary">
              <span class="sg-k">{{ t('待清洁') }}</span>
              <strong class="sg-v">{{ statusSnap?.to_clean ?? '—' }}</strong>
            </div>
            <div class="sg-item">
              <span class="sg-k">{{ t('待分配') }}</span>
              <strong class="sg-v">{{ statusSnap?.waiting ?? '—' }}</strong>
            </div>
            <div class="sg-item">
              <span class="sg-k">{{ t('进行中') }}</span>
              <strong class="sg-v">{{ statusSnap?.progress ?? '—' }}</strong>
            </div>
            <div class="sg-item">
              <span class="sg-k">{{ t('待验收') }}</span>
              <strong class="sg-v">{{ statusSnap?.inspect ?? '—' }}</strong>
            </div>
            <div class="sg-item">
              <span class="sg-k">{{
                statusSnap?.on_duty_label ? t(String(statusSnap.on_duty_label)) : t('作业在岗')
              }}</span>
              <strong class="sg-v">{{ statusSnap?.on_duty ?? '—' }}</strong>
            </div>
          </div>
        </section>

        <section class="status-group cap" :aria-label="t('产能判断')" :class="capacityVerdict.tone">
          <div class="sg-label">{{ t('产能') }}</div>
          <div class="cap-row">
            <span class="cap-pill" :class="capacityVerdict.tone">{{ capacityVerdict.text }}</span>
            <div class="cap-text">
              <p v-if="decisionBrief" class="cap-main">{{ decisionBrief }}</p>
              <p v-if="hotFloorNote" class="cap-sub">{{ hotFloorNote }}</p>
              <p v-else-if="statusSnap?.peak_label" class="cap-sub">{{ statusSnap.peak_label }}</p>
            </div>
          </div>
        </section>
      </div>

      <div v-if="aiAdvice" class="status-extra advice">
        <strong>{{ t('AI 建议') }}</strong>
        <span>{{ aiAdvice }}</span>
        <em v-if="aiAdviceMeta" class="ai-src">{{ aiAdviceMeta }}</em>
      </div>
      <div v-if="proposedTasks.length" class="status-extra proposed">
        <strong>{{ t('待建任务') }}</strong>
        <ul class="proposed-list">
          <li v-for="(item, i) in proposedTasks.slice(0, 6)" :key="i">
            {{ item.room_no }} ·
            {{ item.task_type_label || TYPE_CN[item.task_type] || item.task_type }}
          </li>
        </ul>
        <span v-if="proposedTasks.length > 6" class="more">等共 {{ proposedTasks.length }} 单</span>
      </div>
    </div>

    <HkAiPlanDrawer v-model:open="aiPlanOpen" :scene="aiPlanScene" @confirmed="onAiPlanConfirmed" />

    <div class="toolbar">
      <div class="filters">
        <button
          type="button"
          class="fchip"
          :class="{ on: statusFilter === 'all' }"
          @click="statusFilter = 'all'"
        >
          {{ t('全部') }}
        </button>
        <button
          type="button"
          class="fchip"
          :class="{ on: statusFilter === 'waiting' }"
          @click="statusFilter = 'waiting'"
        >
          {{ t('待分配') }}
        </button>
        <button
          type="button"
          class="fchip"
          :class="{ on: statusFilter === 'progress' }"
          @click="statusFilter = 'progress'"
        >
          {{ t('进行中') }}
        </button>
        <button
          type="button"
          class="fchip"
          :class="{ on: statusFilter === 'inspect' }"
          @click="statusFilter = 'inspect'"
        >
          {{ t('待验收') }}
        </button>
        <button
          type="button"
          class="fchip"
          :class="{ on: statusFilter === 'done' }"
          @click="filterDone"
        >
          {{ t('已完成') }}
        </button>
      </div>
      <div class="toolbar-right">
        <div class="view-toggle" role="group" :aria-label="t('视图')">
          <button type="button" :class="{ on: viewMode === 'list' }" @click="setView('list')">
            <span class="material-symbols-outlined">view_list</span>{{ t('列表') }}
          </button>
          <button type="button" :class="{ on: viewMode === 'board' }" @click="setView('board')">
            <span class="material-symbols-outlined">view_kanban</span>{{ t('看板') }}
          </button>
        </div>
        <button type="button" class="btn-new" @click="openNewTask">{{ t('+ 新建任务') }}</button>
      </div>
    </div>

    <div class="filters-2">
      <label>
        {{ t('楼层') }}
        <select v-model="floorFilter">
          <option value="all">{{ t('全部') }}</option>
          <option v-for="f in floors" :key="f" :value="f">{{ f }}</option>
        </select>
      </label>
      <label>
        {{ t('类型') }}
        <select v-model="typeFilter">
          <option value="all">{{ t('全部') }}</option>
          <option value="clean">{{ t('退房清洁') }}</option>
          <option value="daily">{{ t('日常清洁') }}</option>
          <option value="repair">{{ t('维修') }}</option>
          <option value="service">{{ t('客中服务') }}</option>
        </select>
      </label>
      <label>
        {{ t('执行人') }}
        <select v-model="assigneeFilter">
          <option value="all">{{ t('全部') }}</option>
          <option value="未分配">{{ t('未分配') }}</option>
          <option v-for="a in assignees" :key="a" :value="a">{{ a }}</option>
        </select>
      </label>
      <label>
        {{ t('日期') }}
        <select v-model="dateFilter">
          <option value="today">{{ t('今日') }}</option>
          <option value="tomorrow">{{ t('明日') }}</option>
          <option value="all">{{ t('全部') }}</option>
        </select>
      </label>
      <label class="search">
        <span class="material-symbols-outlined">search</span>
        <input v-model="roomQuery" type="search" :placeholder="t('搜索房号')" />
      </label>
      <label class="chk" v-if="viewMode === 'list'">
        <input v-model="showDone" type="checkbox" />
        {{ t('显示已完成（') }}{{ doneCountHidden }}）
      </label>
    </div>

    <div v-if="selected.size" class="bulk-bar">
      <span>{{ t('已选') }} {{ selected.size }} {{ t('项') }}</span>
      <button type="button" @click="batchStart" :disabled="applyingAi">{{ t('批量派单') }}</button>
      <button type="button" @click="batchFinish" :disabled="applyingAi">{{ t('批量完成') }}</button>
      <button type="button" @click="batchInspect" :disabled="applyingAi">
        {{ t('批量验收') }}
      </button>
      <button type="button" class="ghost" @click="clearSelected">{{ t('取消') }}</button>
    </div>

    <div v-if="newTaskOpen" class="dispatch-mask" @click.self="newTaskOpen = false">
      <div class="dispatch-panel" role="dialog" :aria-label="t('新建任务')">
        <header>
          <h3>{{ t('新建保洁任务') }}</h3>
          <button type="button" class="x" @click="newTaskOpen = false">×</button>
        </header>
        <p class="mode-hint">{{ t('选择房间与类型后写入工单，效果与 AI「一键采纳」相同。') }}</p>
        <div class="new-task-form">
          <label>
            {{ t('房间') }}
            <select v-model="newTask.room_id">
              <option value="">{{ t('请选择') }}</option>
              <option v-for="r in roomsMaster" :key="r.id" :value="r.id">
                {{ r.room_no }}{{ r.floor ? ` · ${r.floor}F` : ''
                }}{{ r.status ? ` · ${r.status}` : '' }}
              </option>
            </select>
          </label>
          <label>
            {{ t('类型') }}
            <select v-model="newTask.task_type">
              <option value="clean">{{ t('退房清洁') }}</option>
              <option value="daily">{{ t('日常清洁') }}</option>
              <option value="turn">{{ t('住中整理') }}</option>
              <option value="service">{{ t('客中服务') }}</option>
              <option value="repair">{{ t('维修') }}</option>
              <option value="inspect">{{ t('查房验收') }}</option>
            </select>
          </label>
          <label>
            {{ t('执行人') }}
            <select v-model="newTask.assignee_id">
              <option value="">{{ t('暂不指定') }}</option>
              <option
                v-for="s in staff.filter((x) => x._status !== 'rest')"
                :key="s.id"
                :value="s.id"
              >
                {{ s.name }}
              </option>
            </select>
          </label>
          <label>
            {{ t('优先级') }}
            <select v-model.number="newTask.priority">
              <option :value="1">{{ t('紧急') }}</option>
              <option :value="2">{{ t('高') }}</option>
              <option :value="3">{{ t('普通') }}</option>
              <option :value="4">{{ t('低') }}</option>
            </select>
          </label>
        </div>
        <footer>
          <button
            type="button"
            class="ghost"
            :disabled="newTaskSaving"
            @click="newTaskOpen = false"
          >
            {{ t('取消') }}
          </button>
          <button
            type="button"
            class="primary"
            :disabled="newTaskSaving || !newTask.room_id"
            @click="submitNewTask"
          >
            {{ newTaskSaving ? t('创建中…') : t('创建任务') }}
          </button>
        </footer>
      </div>
    </div>

    <div v-if="rejectOpen" class="dispatch-mask" @click.self="rejectOpen = false">
      <div class="dispatch-panel reject-panel" role="dialog" :aria-label="t('查房不通过')">
        <header>
          <h3>{{ t('退回重扫 ·') }} {{ rejectTask?.room_no }}</h3>
          <button type="button" class="x" @click="rejectOpen = false">×</button>
        </header>
        <p class="mode-hint">{{ t('勾选不合格项（可多选），确认后任务回到清洁员重扫。') }}</p>
        <div class="fail-items">
          <button
            v-for="item in FAIL_ITEMS"
            :key="item"
            type="button"
            class="fail-chip"
            :class="{ on: rejectItems.includes(item) }"
            @click="toggleRejectItem(item)"
          >
            {{ item }}
          </button>
        </div>
        <label class="reject-note">
          {{ t('补充说明') }}
          <input v-model="rejectNote" type="text" maxlength="120" :placeholder="t('可选')" />
        </label>
        <footer>
          <button type="button" class="ghost" :disabled="rejectSaving" @click="rejectOpen = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="primary" :disabled="rejectSaving" @click="submitReject">
            {{ rejectSaving ? t('提交中…') : t('确认退回') }}
          </button>
        </footer>
      </div>
    </div>

    <div v-if="dispatchOpen" class="dispatch-mask" @click.self="dispatchOpen = false">
      <div class="dispatch-panel" role="dialog" :aria-label="t('批量派单')">
        <header>
          <h3>{{ t('批量派单') }} · {{ selected.size }} {{ t('项') }}</h3>
          <button type="button" class="x" @click="dispatchOpen = false">×</button>
        </header>
        <div class="modes" role="tablist">
          <button
            type="button"
            :class="{ on: dispatchMode === 'single' }"
            @click="dispatchMode = 'single'"
          >
            {{ t('指定一人') }}
          </button>
          <button
            type="button"
            :class="{ on: dispatchMode === 'by_floor' }"
            @click="dispatchMode = 'by_floor'"
          >
            {{ t('按楼层拆分') }}
          </button>
          <button
            type="button"
            :class="{ on: dispatchMode === 'smart' }"
            @click="dispatchMode = 'smart'"
          >
            {{ t('智能分配') }}
          </button>
        </div>
        <p class="mode-hint">
          <template v-if="dispatchMode === 'single'">{{
            t('所选任务全部派给同一位保洁，适合临时集中处理。')
          }}</template>
          <template v-else-if="dispatchMode === 'by_floor'">{{
            t('按房号楼层自动分给对应区域负责人，减少跨层跑动。')
          }}</template>
          <template v-else>{{ t('按在手任务数 + 楼层就近自动匹配，适合退房高峰。') }}</template>
        </p>
        <div v-if="dispatchMode === 'single'" class="single-pick">
          <label>{{ t('保洁员') }}</label>
          <select v-model.number="dispatchAssigneeId">
            <option v-for="s in dispatchStaff" :key="s.id" :value="Number(s.id)">
              {{ s.name }} · 在手 {{ s.open || 0 }}
              <template v-if="s.floors?.length"> · {{ s.floors.join('/') }}F</template>
            </option>
          </select>
        </div>
        <div class="preview-wrap">
          <div class="preview-head">{{ t('分配预览') }}</div>
          <ul v-if="dispatchPreview.length" class="preview-list">
            <li v-for="(p, i) in dispatchPreview" :key="p.task_id || i">
              <strong>{{ p.room_no }}</strong>
              <span>{{ p.floor ? p.floor + 'F' : '—' }}</span>
              <em>→ {{ p.assignee }}</em>
              <small>{{ p.reason }}</small>
            </li>
          </ul>
          <div v-else class="preview-empty">{{ dispatchBusy ? t('计算中…') : t('暂无预览') }}</div>
        </div>
        <footer>
          <button
            type="button"
            class="ghost"
            :disabled="dispatchBusy"
            @click="dispatchOpen = false"
          >
            {{ t('取消') }}
          </button>
          <button
            type="button"
            class="primary"
            :disabled="dispatchBusy || !dispatchPreview.length"
            @click="confirmDispatch"
          >
            {{ dispatchBusy ? t('处理中…') : t('确认派单并推送企微') }}
          </button>
        </footer>
      </div>
    </div>

    <!-- 列表 -->
    <div v-if="viewMode === 'list'" class="list-layout">
      <div class="task-list">
        <article
          v-for="(task, i) in listTasks"
          :key="task.id || i"
          class="task-card"
          :class="{ vip: task.isVip, on: hoverTaskId === Number(task.id) }"
          @mouseenter="hoverTaskId = Number(task.id) || null"
          @mouseleave="hoverTaskId = null"
        >
          <label class="cb" @click.stop>
            <input
              type="checkbox"
              :checked="selected.has(Number(task.id))"
              :disabled="!Number.isFinite(Number(task.id)) || Number(task.id) <= 0"
              @click.prevent="toggleSelect(Number(task.id), $event)"
            />
          </label>
          <div class="task-main">
            <div class="task-title-row">
              <h3>
                <span class="room">{{ task.room_no }}</span>
                {{ task.taskTypeLabel }}
              </h3>
              <span v-if="task.isVip" class="tag tag-vip">VIP</span>
              <span v-if="task.urgent" class="tag tag-urgent">{{ t('紧急') }}</span>
              <span v-else-if="task.rush" class="tag tag-rush">{{ t('加急') }}</span>
              <span class="tag" :class="STATUS_UI[task._status].cls">{{
                STATUS_UI[task._status].label
              }}</span>
            </div>
            <div class="task-meta">
              <span>{{ task.floorLabel }}</span>
              <span>{{ task.roomType }}</span>
              <span>{{ t('执行人：{name}', { name: task.assignee || t('未分配') }) }}</span>
              <span>{{ timeLine(task) }}</span>
              <span v-if="task.escalate" class="tag tag-urgent">{{ t('需店长关注') }}</span>
              <span v-if="task.note" class="note">{{
                String(task.note).startsWith('高优') || String(task.note).includes('建议')
                  ? t(String(task.note))
                  : task.note
              }}</span>
            </div>
            <div v-if="task._status === 'waiting' && task.suggestName" class="suggest">
              {{ t('建议：{name}', { name: task.suggestName }) }}
            </div>
            <div class="task-actions">
              <template v-if="task._status === 'waiting'">
                <button
                  type="button"
                  class="btn-act primary"
                  :disabled="acting === Number(task.id)"
                  @click="startTask(task, $event)"
                >
                  {{ acting === Number(task.id) ? '…' : t('派单') }}
                </button>
                <button
                  type="button"
                  class="btn-act"
                  :disabled="acting === Number(task.id)"
                  @click="markIgnore(task, $event)"
                >
                  {{ t('忽略') }}
                </button>
                <button type="button" class="btn-act ghost" @click="goRoom(task)">
                  {{ t('查看房间') }}
                </button>
              </template>
              <template v-else-if="task._status === 'progress'">
                <button
                  type="button"
                  class="btn-act primary"
                  :disabled="finishing === Number(task.id)"
                  @click="finishTask(task, $event)"
                >
                  {{
                    finishing === Number(task.id)
                      ? '…'
                      : task.taskType === 'repair'
                        ? t('维修完成')
                        : t('完成')
                  }}
                </button>
                <button
                  type="button"
                  class="btn-act"
                  :disabled="acting === Number(task.id)"
                  @click="quickReassign(task, $event)"
                >
                  {{ t('换执行人') }}
                </button>
                <button type="button" class="btn-act ghost" @click="openReassign(task, $event)">
                  {{ t('选人') }}
                </button>
                <button
                  type="button"
                  class="btn-act"
                  :disabled="acting === Number(task.id)"
                  @click="urge(task, $event)"
                >
                  {{ t('催办') }}
                </button>
              </template>
              <template v-else-if="task._status === 'inspect'">
                <button
                  type="button"
                  class="btn-act primary"
                  :disabled="acting === Number(task.id)"
                  @click="inspectTask(task, true, $event)"
                >
                  {{ t('通过') }}
                </button>
                <button
                  type="button"
                  class="btn-act"
                  :disabled="acting === Number(task.id)"
                  @click="inspectTask(task, false, $event)"
                >
                  {{ t('退回重扫') }}
                </button>
              </template>
              <template v-else>
                <button type="button" class="btn-act ghost" @click="goRoom(task)">
                  {{ t('查看详情') }}
                </button>
              </template>
            </div>
            <div v-if="reassignFor === Number(task.id)" class="reassign-row" @click.stop>
              <select
                class="reassign-sel"
                :disabled="acting === Number(task.id)"
                @change="confirmReassign(task, ($event.target as HTMLSelectElement).value)"
              >
                <option value="">{{ t('选择执行人…') }}</option>
                <option
                  v-for="s in staff.filter((x) => Number(x.id) > 0 && x._status !== 'rest')"
                  :key="s.id"
                  :value="s.id"
                >
                  {{ s.name }}（{{ s.statusLabel || s._status }}）
                </option>
              </select>
            </div>
          </div>
        </article>
        <div v-if="!listTasks.length" class="empty">{{ t('当前筛选下暂无任务') }}</div>
        <button
          v-if="!showDone && doneCountHidden && statusFilter !== 'done'"
          type="button"
          class="show-done"
          @click="showDone = true"
        >
          {{ t('展开已完成（{n}）', { n: doneCountHidden }) }}
        </button>
      </div>

      <aside class="side">
        <section class="side-card">
          <h2>{{ t('今日概览') }}</h2>
          <div class="ov-grid">
            <button type="button" @click="clickOverview('all')">
              <div class="ov-n">{{ overview.total }}</div>
              <div class="ov-l">{{ t('总任务') }}</div>
            </button>
            <button type="button" @click="clickOverview('waiting')">
              <div class="ov-n">{{ overview.waiting }}</div>
              <div class="ov-l">{{ t('待分配') }}</div>
            </button>
            <button type="button" @click="clickOverview('progress')">
              <div class="ov-n">{{ overview.progress }}</div>
              <div class="ov-l">{{ t('进行中') }}</div>
            </button>
            <button type="button" @click="clickOverview('inspect')">
              <div class="ov-n">{{ overview.inspect }}</div>
              <div class="ov-l">{{ t('待验收') }}</div>
            </button>
          </div>
          <div class="ov-extra">
            <div>
              {{ t('完成率') }}
              <strong>{{ overview.done }}/{{ overview.total }}（{{ overview.rate }}%）</strong>
            </div>
            <div v-if="riskHint" class="risk">{{ riskHint }}</div>
          </div>
        </section>
        <section class="side-card">
          <h2>{{ t('人员状态') }}</h2>
          <ul class="staff-list">
            <li v-for="(s, i) in staff" :key="s.id || i" :class="{ hi: staffHighlight(s) }">
              <span class="dot" :class="s._status"></span>
              <div class="staff-name">
                <strong>{{ s.name }}</strong>
                <em>({{ t(String(s.role || '')) || s.role }})</em>
                <div class="load">{{ s.loadLabel }}</div>
              </div>
              <div class="staff-task">{{ s.room || s.statusLabel }}</div>
            </li>
            <li v-if="!staff.length" class="empty-inline">{{ t('暂无人员数据') }}</li>
          </ul>
        </section>
      </aside>
    </div>

    <!-- 看板 -->
    <div v-else class="board-wrap">
      <h2 class="board-title">
        {{ t('任务看板') }}{{ t('（按状态 · Shift 多选 · 拖到「进行中」批量派单）') }}
      </h2>
      <div v-if="selected.size" class="bulk-bar board-bulk">
        <span>已选 {{ selected.size }} 项</span>
        <button type="button" @click="batchStart" :disabled="applyingAi">
          {{ t('批量派单') }}
        </button>
        <button type="button" class="ghost" @click="clearSelected">{{ t('取消') }}</button>
      </div>
      <div class="kanban">
        <div
          v-for="col in COLS"
          :key="col.key"
          class="k-col"
          :class="['tone-' + col.tone, { droppable: col.key === 'progress' && dragTaskIds.length }]"
          @dragover="col.key === 'progress' ? onProgressColDragOver($event) : undefined"
          @drop="col.key === 'progress' ? onProgressColDrop($event) : undefined"
        >
          <div class="k-head">
            <span>{{ col.title }}</span>
            <em>{{ kanban[col.key].length }}</em>
          </div>
          <div class="k-body">
            <article
              v-for="(task, i) in kanban[col.key]"
              :key="task.id || i"
              class="k-card"
              :class="{
                selected: selected.has(Number(task.id)),
                dragging: dragTaskIds.includes(Number(task.id)),
              }"
              :draggable="canStart(task) || selected.has(Number(task.id))"
              @click="onKanbanCardClick(task, $event)"
              @dragstart="onKanbanDragStart(task, $event)"
              @dragend="onKanbanDragEnd"
              @mouseenter="hoverTaskId = Number(task.id) || null"
              @mouseleave="hoverTaskId = null"
            >
              <div class="k-title">{{ task.room_no }} {{ task.taskTypeLabel }}</div>
              <div class="k-sub">{{ task.floorLabel }} · {{ task.assignee || t('未分配') }}</div>
              <div class="k-tags">
                <span v-if="task.isVip" class="tag tag-vip">VIP</span>
                <span class="tag" :class="STATUS_UI[task._status].cls">{{
                  STATUS_UI[task._status].label
                }}</span>
              </div>
              <div class="k-act">
                <button
                  v-if="canStart(task)"
                  type="button"
                  class="btn-act sm primary"
                  @click.stop="startTask(task, $event)"
                >
                  {{ t('派单') }}
                </button>
                <button
                  v-else-if="canFinish(task)"
                  type="button"
                  class="btn-act sm primary"
                  @click.stop="finishTask(task, $event)"
                >
                  {{ t('完成') }}
                </button>
                <button
                  v-else-if="canInspect(task)"
                  type="button"
                  class="btn-act sm primary"
                  @click.stop="inspectTask(task, true, $event)"
                >
                  {{ t('通过') }}
                </button>
              </div>
            </article>
            <div v-if="!kanban[col.key].length" class="k-empty">
              {{ col.key === 'progress' ? t('拖入待分配任务可批量派单') : t('暂无') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tasks-page {
  display: flex;
  flex-direction: column;
}

.status-panel {
  background: #fff8e8;
  border: 1px solid #f5e0b8;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
  color: #5c4a2a;
}
.status-panel.advised {
  border-color: #e8c98a;
  background: #fff6e0;
}
.status-top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.status-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 800;
  color: #3b2a12;
}
.tip-ico {
  color: #c9852a;
  font-size: 22px;
}
.status-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.3fr 1fr;
  gap: 12px;
}
@media (max-width: 1100px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
.status-group {
  background: #fff;
  border: 1px solid #f0e2c8;
  border-radius: 10px;
  padding: 10px 12px;
}
.status-group.cap.bad {
  border-color: #f5c26b;
  background: #fffbf2;
}
.status-group.cap.ok {
  border-color: #86efac;
  background: #f6fdf8;
}
.sg-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #8a7048;
  margin-bottom: 8px;
}
.sg-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
  gap: 8px;
}
.sg-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #faf6ef;
  border: 1px solid transparent;
}
.sg-item.dirty {
  background: #fff8e8;
  border-color: #f5e0b8;
}
.sg-item.clean {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.sg-item.mute {
  background: #f8f9fb;
  border-color: #e5e7eb;
}
.sg-item.primary {
  background: #eef4ff;
  border-color: #c5d4f5;
}
.sg-k {
  font-size: 11px;
  font-weight: 700;
  color: #8a7048;
}
.sg-v {
  font-size: 22px;
  font-weight: 800;
  color: #2c241b;
  line-height: 1.15;
}
.cap-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.cap-pill {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 800;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f3e6c8;
  color: #5c4a2a;
}
.cap-pill.bad {
  background: #ba1a1a;
  color: #fff;
}
.cap-pill.ok {
  background: #16a34a;
  color: #fff;
}
.cap-text {
  min-width: 0;
  flex: 1;
}
.cap-main {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 700;
  color: #3b2a12;
  line-height: 1.45;
}
.cap-sub {
  margin: 0;
  font-size: 12px;
  color: #8a7048;
  line-height: 1.4;
}
.status-extra {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e8d9c4;
  font-size: 13px;
  line-height: 1.45;
}
.status-extra strong {
  font-size: 12px;
  color: #8a7048;
}
.status-extra.advice {
  color: #3b2a12;
}
.ai-src {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  font-style: normal;
  color: #8a7048;
  background: #f3e6c8;
  border-radius: 999px;
  padding: 1px 8px;
}
.proposed-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.proposed-list li {
  font-size: 12px;
  font-weight: 600;
  color: #5c4a2a;
  background: #fff;
  border: 1px solid #f0e2c8;
  border-radius: 6px;
  padding: 3px 8px;
}
.proposed-list + .more,
.status-extra .more {
  font-size: 12px;
  color: #8a7048;
}
.ai-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.btn-adopt {
  border: 1px solid #2c241b;
  background: #fff;
  color: #2c241b;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.btn-adopt:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-apply {
  border: none;
  background: #2c241b;
  color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.btn-apply:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.fchip {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
}
.fchip.on {
  background: #2c241b;
  border-color: #2c241b;
  color: #fff;
}
.toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.view-toggle {
  display: inline-flex;
  padding: 3px;
  background: #f3f4f6;
  border-radius: 10px;
  gap: 2px;
}
.view-toggle button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
}
.view-toggle button .material-symbols-outlined {
  font-size: 16px;
}
.view-toggle button.on {
  background: #e8d9c4;
  color: #2c241b;
}
.btn-new {
  border: none;
  background: #8b6914;
  color: #fff;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.filters-2 {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 10px;
}
.filters-2 label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #5b616e;
  font-weight: 600;
}
.filters-2 select,
.filters-2 input {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 5px 8px;
  font-size: 12px;
  background: #fff;
}
.filters-2 .search {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0 8px;
}
.filters-2 .search input {
  border: none;
  outline: none;
  min-width: 100px;
}
.filters-2 .search .material-symbols-outlined {
  font-size: 16px;
  color: #9aa1ad;
}
.filters-2 .chk {
  font-weight: 500;
}

.bulk-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  background: #1f2329;
  color: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 12px;
}
.bulk-bar button {
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.bulk-bar button.ghost {
  border-color: transparent;
  background: transparent;
}
.board-bulk {
  margin-bottom: 12px;
}

.dispatch-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.dispatch-panel {
  width: min(560px, 100%);
  background: #fff;
  border-radius: 14px;
  padding: 18px 18px 14px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
  max-height: 90vh;
  overflow: auto;
}
.dispatch-panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.dispatch-panel h3 {
  margin: 0;
  font-size: 16px;
}
.dispatch-panel .x {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}
.modes {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.modes button {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: #4b5563;
}
.modes button.on {
  background: #2c241b;
  border-color: #2c241b;
  color: #fff;
}
.mode-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}
.single-pick {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 13px;
}
.single-pick select {
  flex: 1;
  height: 34px;
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 0 10px;
}
.preview-wrap {
  border: 1px solid #e8eaed;
  border-radius: 10px;
  padding: 10px;
  background: #fafafa;
  margin-bottom: 14px;
}
.preview-head {
  font-size: 12px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 8px;
}
.preview-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 220px;
  overflow: auto;
}
.preview-list li {
  display: grid;
  grid-template-columns: 64px 40px 1fr;
  gap: 6px 10px;
  align-items: baseline;
  padding: 6px 0;
  border-bottom: 1px solid #eee;
  font-size: 12px;
}
.preview-list li small {
  grid-column: 1 / -1;
  color: #9ca3af;
}
.preview-empty {
  font-size: 12px;
  color: #9ca3af;
  padding: 12px 0;
  text-align: center;
}
.dispatch-panel footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.dispatch-panel footer button {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid #d0d5dd;
  background: #fff;
}
.dispatch-panel footer button.primary {
  background: #2c241b;
  border-color: #2c241b;
  color: #fff;
}
.dispatch-panel footer button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.new-task-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}
.new-task-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
}
.new-task-form select {
  height: 36px;
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 0 10px;
  font-size: 13px;
  background: #fff;
}
@media (max-width: 520px) {
  .new-task-form {
    grid-template-columns: 1fr;
  }
}

.list-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
@media (max-width: 960px) {
  .list-layout {
    grid-template-columns: 1fr;
  }
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-card {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 8px;
  align-items: start;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.task-card.vip {
  border-left: 3px solid #c45c4a;
}
.task-card.on {
  border-color: #c4b5a0;
  box-shadow: 0 0 0 2px rgba(139, 105, 20, 0.12);
}
.cb {
  padding-top: 4px;
}
.task-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.task-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1f2329;
}
.task-title-row .room {
  margin-right: 4px;
}
.tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}
.tag-vip {
  background: #fde8e4;
  color: #b42318;
}
.tag-urgent {
  background: #fee4e2;
  color: #b42318;
}
.tag-rush {
  background: #ffefd6;
  color: #b54708;
}
.st-wait {
  background: #fff4e5;
  color: #b54708;
}
.st-prog {
  background: #e8f0fe;
  color: #1a73e8;
}
.st-insp {
  background: #f3e8ff;
  color: #7c3aed;
}
.st-done {
  background: #e6f4ea;
  color: #137333;
}
.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}
.task-meta .note {
  color: #b54708;
}
.suggest {
  font-size: 12px;
  color: #1a73e8;
  font-weight: 600;
  margin-bottom: 8px;
}
.reassign-row {
  margin-bottom: 8px;
}
.reassign-sel {
  width: 100%;
  max-width: 260px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 0 10px;
  font-size: 12px;
  background: #fff;
}
.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-act {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #1f2329;
  cursor: pointer;
}
.btn-act.primary {
  background: #2c241b;
  border-color: #2c241b;
  color: #fff;
}
.btn-act.ghost {
  color: #6b7280;
}
.btn-act.sm {
  padding: 4px 10px;
  font-size: 11px;
}
.btn-act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.show-done {
  border: 1px dashed #d0d5dd;
  background: #fafafa;
  border-radius: 10px;
  padding: 10px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
}

.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 12px;
}
.side-card {
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 12px;
  padding: 14px;
}
.side-card h2 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
}
.ov-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.ov-grid button {
  border: 1px solid #eef0f3;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
}
.ov-grid button:hover {
  border-color: #c4b5a0;
}
.ov-n {
  font-size: 22px;
  font-weight: 800;
  color: #1f2329;
}
.ov-l {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}
.ov-extra {
  margin-top: 12px;
  font-size: 12px;
  color: #5b616e;
  line-height: 1.5;
}
.ov-extra .risk {
  margin-top: 6px;
  color: #b54708;
}

.staff-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.staff-list li {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 8px;
  align-items: start;
  font-size: 12px;
  padding: 6px;
  border-radius: 8px;
}
.staff-list li.hi {
  background: #fff8e8;
  outline: 1px solid #f5e0b8;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9aa1ad;
  margin-top: 5px;
}
.dot.work {
  background: #f59e0b;
}
.dot.idle {
  background: #22c55e;
}
.dot.rest {
  background: #9aa1ad;
}
.dot.maint {
  background: #3b82f6;
}
.staff-name strong {
  font-weight: 700;
  color: #1f2329;
}
.staff-name em {
  font-style: normal;
  color: #9aa1ad;
  margin-left: 2px;
}
.staff-name .load {
  color: #6b7280;
  margin-top: 2px;
  font-size: 11px;
}
.staff-task {
  color: #6b7280;
  text-align: right;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.board-wrap {
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 12px;
  padding: 14px;
}
.board-title {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 700;
}
.board-title span {
  color: #9aa1ad;
  font-weight: 500;
  font-size: 13px;
}
.kanban {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 1100px) {
  .kanban {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .kanban {
    grid-template-columns: 1fr;
  }
}
.k-col {
  background: #f8f9fb;
  border-radius: 10px;
  padding: 10px;
  min-height: 280px;
}
.k-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
}
.k-head em {
  font-style: normal;
  background: #fff;
  border-radius: 999px;
  padding: 1px 8px;
  font-size: 11px;
  color: #6b7280;
}
.tone-wait .k-head {
  color: #b54708;
}
.tone-prog .k-head {
  color: #1a73e8;
}
.tone-insp .k-head {
  color: #7c3aed;
}
.tone-done .k-head {
  color: #137333;
}
.k-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.k-card {
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: grab;
  user-select: none;
}
.k-card.selected {
  border-color: #2c241b;
  box-shadow: 0 0 0 2px rgba(44, 36, 27, 0.15);
}
.k-card.dragging {
  opacity: 0.55;
}
.k-col.droppable {
  outline: 2px dashed #2c241b;
  outline-offset: -4px;
  background: #faf8f5;
}
.k-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}
.k-sub {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 6px;
}
.k-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.k-act {
  margin-top: 4px;
}
.k-empty,
.empty,
.empty-inline {
  text-align: center;
  color: #9aa1ad;
  font-size: 12px;
  padding: 16px 8px;
}
.fail-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 14px;
}
.fail-chip {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}
.fail-chip.on {
  border-color: #b54708;
  background: #fff7ed;
  color: #b54708;
}
.reject-note {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 14px;
}
.reject-note input {
  height: 36px;
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 0 10px;
  font-weight: 500;
}
</style>
