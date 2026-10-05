<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { localizeSeedText } from '../../lib/localizeSeed'

/** 维修追踪 —— 固定资产维保（空调 / 门锁 / 淋浴等），非布草 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { ASSETS_EMPTY } from '../../lib/assetsEmpty'
import { hotelStore } from '../../store/hotel'
import MaintenanceScheduleCalendar, {
  type ScheduleItem,
} from '../../components/MaintenanceScheduleCalendar.vue'
import RoomOpsNav from '../../components/RoomOpsNav.vue'

const route = useRoute()
const router = useRouter()
const tasks = ref<any[]>([])
const parts = ref<any[]>([])
const assetOptions = ref<{ id: number; label: string; room: string; name: string }[]>([])
const insight = ref({ desc: ASSETS_EMPTY })
const activeTab = ref('all')
const showCreate = ref(false)
const creating = ref(false)
const drawerOpen = ref(false)
const selectedTask = ref<any>(null)
const assetFilterName = ref('')
const viewMode = ref<'calendar' | 'list'>('calendar')
const form = ref({
  assetId: '' as string | number,
  title: '',
  by: t('前台报修'),
  owner: t('张师傅'),
  executor: 'internal' as 'internal' | 'vendor',
  vendor: t('TOTO 授权商'),
})

const VENDORS = [t('TOTO 授权商'), t('大金售后'), t('本地工程外包'), t('电梯维保合同商')]
const INTERNALS = [t('张师傅'), t('李师傅'), t('王师傅')]

const STATUS_MAP: Record<string, { label: string; cls: string; step: number; done?: boolean }> = {
  open: { label: t('待处理'), cls: 'rose', step: 1 },
  repairing: { label: t('维修中'), cls: 'blue', step: 2 },
  closed: { label: t('已完成'), cls: 'slate', step: 3, done: true },
}

function mapMaintStatus(s?: string) {
  if (s === 'doing') return 'repairing'
  if (s === 'done') return 'closed'
  return 'open' // scheduled / overdue
}

function roomLabel(room?: string, loc?: string, name?: string) {
  if (room) return String(room)
  if (loc) return localizeSeedText(String(loc).replace(/\s*房$/, '')) || String(loc)
  return localizeSeedText(name) || '—'
}

const tabs = computed(() => {
  const all = listForView.value
  return [
    { k: 'all', label: t('全部任务'), count: all.length },
    { k: 'pending', label: t('待处理'), count: all.filter((t) => t.raw === 'open').length },
    { k: 'repairing', label: t('维修中'), count: all.filter((t) => t.raw === 'repairing').length },
    { k: 'done', label: t('已完成'), count: all.filter((t) => t.done).length },
  ]
})

const assetFilterId = computed(() => {
  const id = Number(route.query.asset_id || 0)
  return id > 0 ? id : null
})

const listForView = computed(() => {
  if (!assetFilterId.value) return tasks.value
  return tasks.value.filter((t) => Number(t.assetId) === assetFilterId.value)
})

const filtered = computed(() => {
  let list = listForView.value
  if (activeTab.value === 'pending') list = list.filter((t) => t.raw === 'open')
  else if (activeTab.value === 'repairing') list = list.filter((t) => t.raw === 'repairing')
  else if (activeTab.value === 'done') list = list.filter((t) => t.done)
  return list
})

const flowSteps = [t('已报修'), t('已派工'), t('维修中'), t('已完成')]

const drawerTimeline = computed(() => {
  const task = selectedTask.value
  if (!task) return []
  const items = [
    { label: t('工单创建'), time: task.createdAt || task.time || '—', done: task.step >= 1 },
    {
      label: t('派工确认'),
      time: task.worker ? `${t('指派')} ${String(task.worker).replace(/（.*$/, '')}` : t('待指派'),
      done: task.step >= 2,
    },
    {
      label: t('现场维修'),
      time: task.part || (task.raw === 'repairing' ? t('处理中') : '—'),
      done: task.step >= 3,
    },
    { label: t('验收关单'), time: task.done ? t('已完成') : t('待完成'), done: task.done },
  ]
  return items
})

function partHint(assetName: string, message: string) {
  const text = `${assetName} ${message}`
  if (/门锁|电量|电池/.test(text)) return t('已消耗 1x 智能门锁电池')
  if (/空调|滤网/.test(text)) return t('建议领用空调滤网')
  if (/淋浴|喷头|卫浴|马桶/.test(text)) return t('建议核对淋浴喷头备件')
  if (/遥控|电视/.test(text)) return t('建议核对遥控器库存')
  return ''
}

async function load() {
  try {
    const board = await api.assetsBoard(hotelStore.hotelId)
    const assets = board?.assets || []
    const byId: Record<number, any> = {}
    for (const a of assets) byId[a.id] = a

    assetOptions.value = assets.slice(0, 40).map((a: any) => ({
      id: a.id,
      name: a.name || t('设备'),
      assetNo: a.asset_no || a.sn || `EQ-${String(a.id).padStart(5, '0')}`,
      room: roomLabel(a.room_no, a.location, a.name),
      label: `${a.asset_no || a.sn || `EQ-${String(a.id).padStart(5, '0')}`} · ${roomLabel(a.room_no, a.location, a.name)} · ${a.name || t('设备')}`,
    }))

    const seen = new Set<string>()
    const list: any[] = []

    for (const m of board?.maintenance || []) {
      const a = byId[m.asset_id] || {}
      const raw = mapMaintStatus(m.status)
      const ui = STATUS_MAP[raw]
      const woId = `WO-${m.id}`
      seen.add(`asset-${m.asset_id}`)
      const title = localizeSeedText(m.note || m.task_type || a.insight || a.name || t('维保任务'))
      list.push({
        id: woId,
        woId,
        assetId: m.asset_id,
        assetName: localizeSeedText(a.name || ''),
        assetNo:
          a.asset_no || a.sn || (m.asset_id ? `EQ-${String(m.asset_id).padStart(5, '0')}` : ''),
        type: t(String(m.task_type || '维保')),
        raw,
        room: roomLabel(a.room_no, a.location, a.name),
        title,
        status: ui.label,
        statusCls: ui.cls,
        time: m.due_date
          ? t('到期 {date}', { date: String(m.due_date).slice(0, 10) })
          : m.completed_at
            ? String(m.completed_at).replace('T', ' ').slice(0, 16)
            : '',
        createdAt: m.due_date ? String(m.due_date).slice(0, 10) : '',
        by: t(String(m.task_type || '工程维保')),
        part: raw === 'repairing' ? partHint(a.name || '', title) : '',
        worker:
          raw === 'repairing' && m.owner
            ? t('{name}（预计 15 分钟完成）', { name: localizeSeedText(m.owner) })
            : localizeSeedText(m.owner || ''),
        executor: /外协|授权|合同|外包/.test(String(m.owner || '')) ? 'vendor' : 'internal',
        done: !!ui.done,
        step: ui.step,
      })
    }

    for (const al of board?.alerts || []) {
      if (al.status && al.status !== 'open') continue
      const aid = al.asset_id
      if (aid && seen.has(`asset-${aid}`)) continue
      const woId = `AL-${al.id}`
      if (aid) seen.add(`asset-${aid}`)
      const a = aid ? byId[aid] || {} : {}
      // 门锁电量类告警标记为「维修中」；其余高优待处理
      const raw = /电量|电池|iot/i.test(`${al.alert_type} ${al.message}`) ? 'repairing' : 'open'
      const ui = STATUS_MAP[raw]
      const title = localizeSeedText(al.message || al.asset_name || t('设备告警'))
      list.push({
        id: woId,
        woId,
        assetId: aid,
        assetName: localizeSeedText(al.asset_name || a.name || ''),
        assetNo: a.asset_no || a.sn || (aid ? `EQ-${String(aid).padStart(5, '0')}` : ''),
        type: al.severity === 'high' ? t('紧急报修') : t('IoT 告警'),
        raw,
        room: roomLabel(al.room_no || a.room_no, al.floor || a.location, al.asset_name || a.name),
        title,
        status: ui.label,
        statusCls: ui.cls,
        time: al.created_at ? String(al.created_at).replace('T', ' ').slice(0, 16) : '',
        createdAt: al.created_at ? String(al.created_at).replace('T', ' ').slice(0, 16) : '',
        by: al.severity === 'high' ? t('前台 / IoT 告警') : t('工程巡检'),
        part: raw === 'repairing' ? partHint(al.asset_name || a.name || '', title) : '',
        worker: raw === 'repairing' ? t('张师傅（预计 15 分钟完成）') : '',
        executor: /外协|授权|合同|IoT/i.test(`${al.alert_type} ${al.message}`)
          ? 'vendor'
          : 'internal',
        done: false,
        step: ui.step,
      })
    }

    // 待处理优先，再维修中，已完成靠后
    const order = { open: 0, repairing: 1, closed: 2 } as Record<string, number>
    list.sort((x, y) => (order[x.raw] ?? 9) - (order[y.raw] ?? 9))
    tasks.value = list

    if (assetFilterId.value) {
      const hit = assets.find((a: any) => Number(a.id) === assetFilterId.value)
      assetFilterName.value = hit
        ? `${hit.asset_no || hit.sn || ''} · ${hit.name || t('设备')}`.replace(/^ · /, '')
        : ''
    } else {
      assetFilterName.value = ''
    }

    tryOpenFromQuery()

    // 备件预警：来自设备盘点差异（滤网/电池/喷头等）
    const audits = (board?.audit_items || []).filter((x: any) => {
      const n = x.name || ''
      return (
        /电池|滤网|喷头|遥控|备件/.test(n) ||
        Number(x.theoretical_qty || 0) !== Number(x.actual_qty || 0)
      )
    })
    parts.value = audits.slice(0, 4).map((x: any) => {
      const left = Number(x.actual_qty || 0)
      const theo = Number(x.theoretical_qty || 0)
      const danger = left < theo || left <= 5
      return {
        icon: /电池|滤网|喷头/.test(x.name || '') ? 'settings_input_component' : 'inventory_2',
        name: t(String(x.name || '')),
        left: danger && left <= 5 ? t('仅剩 {n}', { n: left }) : t('剩余 {n}', { n: left }),
        danger,
      }
    })
    // 若盘点无备件项，用告警推导备件名（不编造库存数字）
    if (!parts.value.length) {
      const names = new Set<string>()
      for (const al of board?.alerts || []) {
        const hay = `${al.asset_name || ''} ${al.message || ''}`
        if (/滤网|空调/.test(hay)) names.add(t('空调滤网'))
        if (/喷头|淋浴|卫浴/.test(hay)) names.add(t('淋浴喷头'))
        if (/门锁|电量|电池/.test(hay)) names.add(t('智能门锁电池'))
      }
      parts.value = [...names].slice(0, 4).map((name) => ({
        icon: 'settings_input_component',
        name,
        left: t('待盘点'),
        danger: true,
      }))
    }

    const high =
      (board?.alerts || []).find((a: any) => a.severity === 'high') || (board?.alerts || [])[0]
    const openMaint = Number(board?.counts?.open_maint || 0)
    if (high) {
      const room = high.room_no || high.floor || ''
      const who = t('张师傅')
      const assetRaw = String(high.asset_name || '设备')
      // 房号已单独展示时，去掉资产名里重复的房号前缀（如 0105智能门锁）
      const assetName =
        localizeSeedText(
          room && assetRaw.startsWith(String(room))
            ? assetRaw.slice(String(room).length)
            : assetRaw,
        ) || t('设备')
      insight.value = {
        desc: t(
          '检测到 {room}{asset}（{msg}）优先级极高，建议指派给 {who}，他目前距离该楼层最近且即将空闲。',
          {
            room: room ? `${room} ` : '',
            asset: assetName,
            msg: localizeSeedText(String(high.message || '故障')).slice(0, 48),
            who,
          },
        ),
      }
    } else if (openMaint) {
      insight.value = {
        desc: t('当前有 {n} 项待维保任务，建议按健康分与楼层就近派工。', { n: openMaint }),
      }
    } else {
      insight.value = { desc: ASSETS_EMPTY }
    }
  } catch {
    tasks.value = []
    parts.value = []
    assetOptions.value = []
    insight.value = { desc: ASSETS_EMPTY }
  }
}

function syncQuery(patch: Record<string, string | undefined>) {
  const q: Record<string, any> = { ...route.query }
  for (const [k, v] of Object.entries(patch)) {
    if (v == null || v === '') delete q[k]
    else q[k] = v
  }
  router.replace({ query: q })
}

function openTask(t: any) {
  if (!t) return
  selectedTask.value = t
  drawerOpen.value = true
  syncQuery({ wo_id: t.woId || t.id })
}

function closeDrawer() {
  drawerOpen.value = false
  selectedTask.value = null
  syncQuery({ wo_id: undefined })
}

function findTask(woId: string) {
  return tasks.value.find((t) => t.woId === woId || t.id === woId)
}

function tryOpenFromQuery() {
  const woId = String(route.query.wo_id || '')
  if (!woId) return
  const hit = findTask(woId)
  if (hit) {
    selectedTask.value = hit
    drawerOpen.value = true
  }
}

function patchTask(woId: string, patch: Record<string, any>) {
  tasks.value = tasks.value.map((t) => (t.woId === woId ? { ...t, ...patch } : t))
  if (selectedTask.value?.woId === woId) {
    selectedTask.value = { ...selectedTask.value, ...patch }
  }
}

function claimTask(task: any) {
  const worker = form.value.owner || t('张师傅')
  patchTask(task.woId, {
    raw: 'repairing',
    status: t('维修中'),
    statusCls: 'blue',
    step: 3,
    worker: t('{name}（预计 15 分钟完成）', { name: worker }),
    part: partHint(task.assetName || '', task.title),
  })
}

function completeTask(task: any) {
  patchTask(task.woId, {
    raw: 'closed',
    status: t('已完成'),
    statusCls: 'slate',
    step: 4,
    done: true,
    time: t('刚刚完成'),
  })
}

function goAsset(t: any) {
  if (t?.assetId) router.push(`/c8-assets/assets/${t.assetId}`)
}

function clearAssetFilter() {
  syncQuery({ asset_id: undefined, wo_id: undefined })
  closeDrawer()
}

function adoptDispatch() {
  const first = tasks.value.find((t) => t.raw === 'open')
  if (first) {
    claimTask(first)
    openTask(findTask(first.woId) || first)
  }
}

function onScheduleSelect(item: ScheduleItem) {
  const hit = item.woId ? findTask(item.woId) : tasks.value.find((t) => t.assetId === item.assetId)
  if (hit) {
    openTask(hit)
    return
  }
  if (item.assetId) router.push(`/c8-assets/assets/${item.assetId}`)
}

function openCreate(prefillAssetId?: number) {
  showCreate.value = true
  if (prefillAssetId) form.value.assetId = prefillAssetId
  else if (!form.value.assetId && assetOptions.value.length) {
    form.value.assetId = assetOptions.value[0].id
  }
}

function closeCreate() {
  showCreate.value = false
}

function submitCreate() {
  const opt = assetOptions.value.find((a) => String(a.id) === String(form.value.assetId))
  const title = (form.value.title || '').trim() || t('设备报修')
  if (!opt && !title) return
  creating.value = true
  const id = `WO-NEW-${Date.now()}`
  const task = {
    id,
    woId: id,
    assetId: opt?.id,
    assetName: opt?.name || '',
    assetNo: opt?.assetNo || '',
    type: t('紧急报修'),
    raw: 'open',
    room: opt?.room || '—',
    title: opt ? `${opt.name}：${title}` : title,
    status: t('待处理'),
    statusCls: 'rose',
    time: t('刚刚创建'),
    createdAt: t('刚刚'),
    by: form.value.by || t('前台报修'),
    part: '',
    worker:
      form.value.executor === 'vendor' ? `${form.value.vendor}（外协）` : form.value.owner || '',
    executor: form.value.executor,
    done: false,
    step: 1,
  }
  tasks.value = [task, ...tasks.value]
  activeTab.value = 'pending'
  form.value.title = ''
  creating.value = false
  showCreate.value = false
  openTask(task)
}

onMounted(async () => {
  await load()
  if (route.query.view === 'list') viewMode.value = 'list'
  else if (route.query.view === 'calendar') viewMode.value = 'calendar'
  if (route.query.action === 'repair') {
    const aid = Number(route.query.asset_id || 0)
    openCreate(aid || undefined)
  }
})
watch(() => hotelStore.hotelId, load)
watch(
  () => route.query.wo_id,
  () => {
    if (!route.query.wo_id) {
      drawerOpen.value = false
      selectedTask.value = null
      return
    }
    tryOpenFromQuery()
  },
)
watch(() => route.query.asset_id, load)
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <div class="page-head track-head">
      <div>
        <h1>{{ t('维修追踪') }}</h1>
      </div>
      <div class="track-head-actions">
        <button class="btn btn-ghost" type="button">
          <span class="material-symbols-outlined">filter_list</span> {{ t('筛选') }}
        </button>
        <button class="btn btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span> {{ t('新建报修') }}
        </button>
      </div>
    </div>

    <div v-if="assetFilterId" class="asset-filter-bar">
      <span class="material-symbols-outlined">filter_alt</span>
      <span
        >{{ t('仅显示设备工单：')
        }}{{ localizeSeedText(assetFilterName) || t('资产 #{id}', { id: assetFilterId }) }}</span
      >
      <button type="button" class="link" @click="clearAssetFilter">{{ t('查看全部') }}</button>
    </div>

    <!-- 新建报修表单 -->
    <div
      v-if="showCreate"
      class="create-panel card-clean"
      style="margin-bottom: 16px; padding: 20px"
    >
      <div
        style="
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        "
      >
        <h2 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--on-surface)">
          {{ t('新建报修单') }}
        </h2>
        <button class="btn btn-ghost" type="button" @click="closeCreate">{{ t('关闭') }}</button>
      </div>
      <div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px">
        <label
          style="
            grid-column: span 6;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('报修设备') }}
          <select
            v-model="form.assetId"
            style="
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid var(--outline-variant);
              background: var(--surface);
              color: var(--on-surface);
              font-size: 13px;
            "
          >
            <option disabled value="">{{ t('选择设备……') }}</option>
            <option v-for="a in assetOptions" :key="a.id" :value="a.id">{{ a.label }}</option>
          </select>
        </label>
        <label
          style="
            grid-column: span 12;
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('执行方') }}
          <div style="display: flex; gap: 16px; flex-wrap: wrap">
            <label
              style="
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                color: var(--on-surface);
              "
            >
              <input v-model="form.executor" type="radio" value="internal" />
              {{ t('内部工程') }}</label
            >
            <label
              style="
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                color: var(--on-surface);
              "
            >
              <input v-model="form.executor" type="radio" value="vendor" />
              {{ t('外协供应商') }}</label
            >
          </div>
        </label>
        <label
          v-if="form.executor === 'internal'"
          style="
            grid-column: span 6;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('指派工程员') }}
          <select
            v-model="form.owner"
            style="
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid var(--outline-variant);
              background: var(--surface);
              color: var(--on-surface);
              font-size: 13px;
            "
          >
            <option v-for="p in INTERNALS" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label
          v-else
          style="
            grid-column: span 6;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('外协供应商') }}
          <select
            v-model="form.vendor"
            style="
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid var(--outline-variant);
              background: var(--surface);
              color: var(--on-surface);
              font-size: 13px;
            "
          >
            <option v-for="v in VENDORS" :key="v" :value="v">{{ v }}</option>
          </select>
        </label>
        <label
          style="
            grid-column: span 3;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('报修来源') }}
          <select
            v-model="form.by"
            style="
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid var(--outline-variant);
              background: var(--surface);
              color: var(--on-surface);
              font-size: 13px;
            "
          >
            <option>{{ t('前台报修') }}</option>
            <option>{{ t('客房服务') }}</option>
            <option>{{ t('工程巡检') }}</option>
            <option>{{ t('IoT 告警') }}</option>
          </select>
        </label>
        <label
          style="
            grid-column: span 12;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: var(--on-surface-variant);
          "
        >
          {{ t('故障描述') }}
          <input
            v-model="form.title"
            type="text"
            :placeholder="t('例如：出水压力不足 / 滤网堵塞 / 门锁电量低')"
            style="
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid var(--outline-variant);
              background: var(--surface);
              color: var(--on-surface);
              font-size: 13px;
            "
          />
        </label>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px">
        <button class="btn btn-ghost" type="button" @click="closeCreate">{{ t('取消') }}</button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="creating || !form.assetId"
          @click="submitCreate"
        >
          {{ t('提交报修') }}
        </button>
      </div>
    </div>

    <div class="view-tabs">
      <button
        type="button"
        class="view-tab"
        :class="{ active: viewMode === 'calendar' }"
        @click="viewMode = 'calendar'"
      >
        <span class="material-symbols-outlined">calendar_month</span>
        {{ t('排期日历') }}
      </button>
      <button
        type="button"
        class="view-tab"
        :class="{ active: viewMode === 'list' }"
        @click="viewMode = 'list'"
      >
        <span class="material-symbols-outlined">format_list_bulleted</span>
        {{ t('工单列表') }}
      </button>
    </div>

    <MaintenanceScheduleCalendar
      v-show="viewMode === 'calendar'"
      class="mb-4"
      :external-tasks="tasks"
      @select="onScheduleSelect"
    />

    <div
      v-show="viewMode === 'list'"
      style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; align-items: start"
    >
      <div style="grid-column: span 3; display: flex; flex-direction: column; gap: 16px">
        <div class="ai-card">
          <div
            style="
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 12px;
              color: var(--tertiary);
            "
          >
            <span class="material-symbols-outlined">auto_awesome</span>
            <h3 style="font-size: 14px; font-weight: 700; margin: 0">{{ t('AI 调度确认') }}</h3>
          </div>
          <p
            style="
              font-size: 13px;
              color: var(--on-surface-variant);
              margin: 0 0 16px;
              line-height: 1.6;
            "
          >
            {{ insight.desc }}
          </p>
          <button class="adopt-btn" type="button" @click="adoptDispatch">
            {{ t('一键采纳调度') }}
          </button>
        </div>

        <div class="card-clean" style="padding: 16px">
          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 16px;
            "
          >
            <h3 style="font-size: 13px; font-weight: 700; color: var(--on-surface); margin: 0">
              {{ t('备件预警') }}
            </h3>
          </div>
          <div style="display: flex; flex-direction: column; gap: 12px">
            <p v-if="!parts.length" class="empty-hint">{{ ASSETS_EMPTY }}</p>
            <div
              v-for="(p, i) in parts"
              :key="i"
              style="display: flex; align-items: center; justify-content: space-between"
            >
              <div style="display: flex; align-items: center; gap: 8px">
                <div
                  :style="{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: p.danger
                      ? 'var(--error-container)'
                      : 'var(--surface-container-high)',
                    color: p.danger ? 'var(--on-error-container)' : 'var(--on-surface-variant)',
                  }"
                >
                  <span class="material-symbols-outlined" style="font-size: 16px">{{
                    p.icon
                  }}</span>
                </div>
                <span style="font-size: 13px; color: var(--on-surface)">{{ p.name }}</span>
              </div>
              <span
                :style="{
                  fontSize: '13px',
                  fontWeight: 500,
                  color: p.danger ? 'var(--error)' : 'var(--on-surface-variant)',
                }"
                >{{ p.left }}</span
              >
            </div>
          </div>
        </div>
      </div>

      <div style="grid-column: span 9">
        <div
          class="card-clean"
          style="overflow: hidden; display: flex; flex-direction: column; height: 100%"
        >
          <div
            style="
              display: flex;
              border-bottom: 1px solid var(--outline-variant);
              background: var(--surface-low);
            "
          >
            <button
              v-for="t in tabs"
              :key="t.k"
              type="button"
              @click="activeTab = t.k"
              :style="{
                padding: '12px 24px',
                borderBottom: '2px solid ' + (activeTab === t.k ? 'var(--primary)' : 'transparent'),
                color: activeTab === t.k ? 'var(--primary)' : 'var(--on-surface-variant)',
                fontWeight: 500,
                fontSize: '13px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }"
            >
              {{ t.label }} ({{ t.count }})
            </button>
          </div>
          <div style="flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 8px">
            <p v-if="!filtered.length" class="empty-hint">{{ ASSETS_EMPTY }}</p>
            <div
              v-for="(item, i) in filtered"
              :key="item.id || i"
              style="
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 16px;
                border-radius: 8px;
                border: 1px solid var(--outline-variant);
                background: var(--surface);
                cursor: pointer;
              "
              :class="{ 'ai-glow': item.status === '维修中' }"
              @click="openTask(item)"
            >
              <div
                :style="{
                  flexShrink: 0,
                  width: '48px',
                  height: '48px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid var(--outline-variant)',
                  background: item.done
                    ? 'var(--surface-container)'
                    : item.status === '待处理'
                      ? 'rgba(186,26,26,0.08)'
                      : 'var(--surface-container-highest)',
                }"
              >
                <span
                  class="material-symbols-outlined"
                  :style="{
                    color: item.done
                      ? 'var(--secondary)'
                      : item.status === '待处理'
                        ? 'var(--error)'
                        : 'var(--on-surface-variant)',
                  }"
                  >{{
                    item.done ? 'check_circle' : item.status === '待处理' ? 'warning' : 'build'
                  }}</span
                >
              </div>
              <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                  <span
                    style="
                      font:
                        700 14px 'Roboto Mono',
                        monospace;
                      color: var(--on-surface);
                    "
                    :style="{
                      textDecoration: item.done ? 'line-through' : 'none',
                      opacity: item.done ? 0.6 : 1,
                    }"
                    >{{ item.room }}</span
                  >
                  <span
                    style="
                      font-size: 13px;
                      font-weight: 500;
                      color: var(--on-surface);
                      white-space: nowrap;
                      overflow: hidden;
                      text-overflow: ellipsis;
                    "
                    >{{ item.title }}</span
                  >
                  <span class="pill" :class="'pill-' + item.statusCls">{{ item.status }}</span>
                  <span
                    v-if="t.part"
                    style="
                      font-size: 11px;
                      color: var(--tertiary);
                      display: flex;
                      align-items: center;
                      gap: 4px;
                      background: rgba(140, 51, 179, 0.1);
                      padding: 2px 6px;
                      border-radius: 4px;
                    "
                    ><span class="material-symbols-outlined" style="font-size: 12px"
                      >inventory_2</span
                    >
                    {{ t.part }}</span
                  >
                </div>
                <div
                  style="
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    font-size: 11px;
                    color: var(--on-surface-variant);
                    flex-wrap: wrap;
                  "
                >
                  <span v-if="t.time" style="display: flex; align-items: center; gap: 4px"
                    ><span class="material-symbols-outlined" style="font-size: 14px">schedule</span
                    >{{ t.time }}</span
                  >
                  <span v-if="t.by" style="display: flex; align-items: center; gap: 4px"
                    ><span class="material-symbols-outlined" style="font-size: 14px">person</span
                    >{{ t.by }}</span
                  >
                  <span v-if="t.worker" style="display: flex; align-items: center; gap: 4px">
                    <span class="material-symbols-outlined" style="font-size: 14px"
                      >engineering</span
                    >
                    {{ t.worker }}
                    <span v-if="t.executor === 'vendor'" class="exec-tag">{{ t('外协') }}</span>
                  </span>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 12px" @click.stop>
                <div style="display: flex; align-items: center">
                  <span
                    :style="{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: t.step >= 1 ? 'var(--primary)' : 'var(--surface-variant)',
                    }"
                  ></span>
                  <span
                    :style="{
                      width: '32px',
                      height: '2px',
                      background: t.step >= 2 ? 'var(--primary)' : 'var(--surface-variant)',
                    }"
                  ></span>
                  <span
                    :style="{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: t.step >= 2 ? 'var(--primary)' : 'var(--surface-variant)',
                    }"
                  ></span>
                  <span
                    :style="{
                      width: '32px',
                      height: '2px',
                      background: t.step >= 3 ? 'var(--primary)' : 'var(--surface-variant)',
                    }"
                  ></span>
                  <span
                    :style="{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: t.step >= 3 ? 'var(--primary)' : 'var(--surface-variant)',
                    }"
                  ></span>
                </div>
                <button
                  v-if="item.status === '待处理'"
                  class="btn btn-primary"
                  type="button"
                  style="font-size: 12px; padding: 6px 12px"
                  @click="openTask(item)"
                >
                  {{ t('抢单') }}
                </button>
                <button
                  v-else-if="item.status === '维修中'"
                  class="btn btn-ghost"
                  type="button"
                  style="font-size: 12px; padding: 6px 12px"
                  @click="openTask(item)"
                >
                  {{ t('查看进度') }}
                </button>
                <button
                  v-else
                  class="icon-btn"
                  type="button"
                  style="width: 32px; height: 32px"
                  @click="openTask(item)"
                >
                  <span class="material-symbols-outlined">more_vert</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 工单详情抽屉（不跳转新页） -->
    <Teleport to="body">
      <div v-if="drawerOpen && selectedTask" class="wo-drawer-root" @click.self="closeDrawer">
        <aside class="wo-drawer">
          <div class="wo-drawer-head">
            <div>
              <p class="wo-drawer-k">{{ t('工单编号') }}</p>
              <h2 class="wo-drawer-id">{{ selectedTask.woId || selectedTask.id }}</h2>
            </div>
            <button type="button" class="icon-btn" @click="closeDrawer">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <div class="wo-drawer-body">
            <div class="wo-drawer-top">
              <span class="pill" :class="'pill-' + selectedTask.statusCls">{{
                selectedTask.status
              }}</span>
              <span class="wo-type-tag">{{ selectedTask.type || selectedTask.by }}</span>
            </div>

            <h3 class="wo-drawer-title">{{ selectedTask.title }}</h3>
            <p class="wo-drawer-meta">
              <span>{{ selectedTask.room }}</span>
              <span v-if="selectedTask.time">· {{ selectedTask.time }}</span>
              <span v-if="selectedTask.by">· {{ selectedTask.by }}</span>
            </p>

            <div v-if="selectedTask.assetId" class="wo-asset-card" @click="goAsset(selectedTask)">
              <span class="material-symbols-outlined">inventory_2</span>
              <div class="min-w-0">
                <div class="font-semibold text-sm">
                  {{ selectedTask.assetName || t('关联设备') }}
                </div>
                <div class="text-xs text-on-surface-variant">
                  {{ selectedTask.assetNo }} · {{ t('点击查看资产画像') }}
                </div>
              </div>
              <span class="material-symbols-outlined text-on-surface-variant">chevron_right</span>
            </div>

            <div class="wo-flow">
              <div class="wo-flow-labels">
                <span
                  v-for="(s, i) in flowSteps"
                  :key="s"
                  :class="{ on: (selectedTask.step || 1) > i || (selectedTask.done && i === 3) }"
                  >{{ s }}</span
                >
              </div>
              <div class="wo-flow-track">
                <template v-for="(_, i) in flowSteps" :key="i">
                  <span
                    class="wo-flow-dot"
                    :class="{ on: (selectedTask.step || 1) > i || (selectedTask.done && i <= 3) }"
                  />
                  <span
                    v-if="i < flowSteps.length - 1"
                    class="wo-flow-line"
                    :class="{ on: (selectedTask.step || 1) > i + 1 }"
                  />
                </template>
              </div>
            </div>

            <div class="wo-timeline">
              <h4>{{ t('流转记录') }}</h4>
              <div v-for="(ev, i) in drawerTimeline" :key="i" class="wo-tl-item">
                <span class="wo-tl-dot" :class="{ on: ev.done }" />
                <div>
                  <div class="wo-tl-label">{{ ev.label }}</div>
                  <div class="wo-tl-time">{{ ev.time }}</div>
                </div>
              </div>
            </div>

            <p v-if="selectedTask.part" class="wo-part">
              <span class="material-symbols-outlined">inventory_2</span>
              {{ selectedTask.part }}
            </p>
            <p v-if="selectedTask.worker" class="wo-worker">
              <span class="material-symbols-outlined">engineering</span>
              {{ selectedTask.worker }}
              <span v-if="selectedTask.executor === 'vendor'" class="exec-tag">{{
                t('外协')
              }}</span>
            </p>
          </div>

          <div class="wo-drawer-foot">
            <button
              v-if="selectedTask.raw === 'open'"
              type="button"
              class="btn btn-primary w-full"
              @click="claimTask(selectedTask)"
            >
              {{ t('抢单并开始维修') }}
            </button>
            <button
              v-else-if="selectedTask.raw === 'repairing'"
              type="button"
              class="btn btn-primary w-full"
              @click="completeTask(selectedTask)"
            >
              {{ t('完成并关单') }}
            </button>
            <button
              v-if="selectedTask.assetId"
              type="button"
              class="btn btn-ghost w-full"
              @click="goAsset(selectedTask)"
            >
              {{ t('查看关联资产') }}
            </button>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.empty-hint {
  margin: 0;
  padding: 24px;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
.adopt-btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: var(--tertiary-container);
  color: #ffffff;
}
.adopt-btn:hover {
  opacity: 0.92;
  color: #ffffff;
}
.create-panel {
  border: 1px solid var(--outline-variant);
}
.track-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.track-head-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}
.exec-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #e3f2fd;
  color: #1565c0;
}
.asset-filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--primary) 8%, var(--surface-container-lowest));
  border: 1px solid color-mix(in srgb, var(--primary) 22%, var(--outline-variant));
  font-size: 13px;
  color: var(--on-surface);
}
.asset-filter-bar .material-symbols-outlined {
  font-size: 18px;
  color: var(--primary);
}
.asset-filter-bar .link {
  margin-left: auto;
  border: none;
  background: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 13px;
}
.view-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: var(--surface-container);
  border: 1px solid var(--outline-variant);
}
.view-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}
.view-tab .material-symbols-outlined {
  font-size: 18px;
}
.view-tab.active {
  background: var(--surface-container-lowest);
  color: var(--primary);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
.view-tab:hover:not(.active) {
  color: var(--on-surface);
}
.mb-4 {
  margin-bottom: 16px;
}
.wo-drawer-root {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.wo-drawer {
  width: min(420px, 100vw);
  height: 100%;
  background: var(--surface-container-lowest);
  border-left: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.12);
}
.wo-drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--outline-variant);
}
.wo-drawer-k {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.wo-drawer-id {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
}
.wo-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.wo-drawer-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.wo-type-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.wo-drawer-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.4;
}
.wo-drawer-meta {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.wo-asset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  cursor: pointer;
}
.wo-asset-card:hover {
  border-color: var(--primary);
}
.wo-asset-card .material-symbols-outlined:first-child {
  color: var(--primary);
}
.wo-flow {
  padding: 12px 0;
}
.wo-flow-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
}
.wo-flow-labels .on {
  color: var(--primary);
  font-weight: 600;
}
.wo-flow-track {
  display: flex;
  align-items: center;
}
.wo-flow-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--surface-variant);
  flex-shrink: 0;
}
.wo-flow-dot.on {
  background: var(--primary);
}
.wo-flow-line {
  flex: 1;
  height: 2px;
  background: var(--surface-variant);
  margin: 0 4px;
}
.wo-flow-line.on {
  background: var(--primary);
}
.wo-timeline h4 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
}
.wo-tl-item {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}
.wo-tl-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 5px;
  background: var(--outline-variant);
  flex-shrink: 0;
}
.wo-tl-dot.on {
  background: var(--primary);
}
.wo-tl-label {
  font-size: 14px;
  font-weight: 600;
}
.wo-tl-time {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.wo-part,
.wo-worker {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-container);
}
.wo-drawer-foot {
  padding: 16px 20px;
  border-top: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wo-drawer-foot .w-full {
  width: 100%;
  justify-content: center;
}
</style>
