<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 排班：远期日/周/月网格 + 非破坏性 AI 建议。不创建房务任务。
 * 风格沿用：card-clean / ai-card / 既有班次色。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { confidenceLabel } from '../../lib/aiConfidence'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import HousekeepingTasksSubnav from '../../components/HousekeepingTasksSubnav.vue'
import HkAiPlanDrawer from '../../components/HkAiPlanDrawer.vue'

type ViewMode = 'day' | 'week' | 'month'

const WD_KEYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const

const SHIFT_OPTS = [
  { code: 'morning', labelKey: '早班', hours: '08-16' },
  { code: 'afternoon', labelKey: '中班', hours: '12-20' },
  { code: 'night', labelKey: '晚班', hours: '16-24' },
  { code: 'off', labelKey: '休息', hours: '' },
] as const

function dayLabel(d: any) {
  if (!d) return ''
  if (d.date != null && d.weekday != null) {
    const parts = String(d.date).split('-')
    const m = Number(parts[1])
    const day = Number(parts[2])
    const wd = WD_KEYS[Number(d.weekday)] || '周一'
    return `${t(wd)} ${m}/${day}`
  }
  const raw = String(d.label || '')
  for (const w of WD_KEYS) {
    if (raw.startsWith(w)) return `${t(w)}${raw.slice(w.length)}`
  }
  return raw
}

function cellLabel(sh: any) {
  const code = sh?.shift || sh?.type
  if (code === 'morning') return t('早班')
  if (code === 'afternoon') return t('中班')
  if (code === 'night') return t('晚班')
  if (code === 'off') return t('休息')
  const name = sh?.name || String(sh?.label || '').split('\n')[0]
  return name ? t(name) : t('未排')
}

function roleLabel(role?: string) {
  return role ? t(role) : t('内部员工')
}

const view = ref<ViewMode>('week')
const start = ref('')
const data = ref<any>({
  week_label: '',
  range_start: '',
  days: [],
  weeks: [],
  staff: [],
  forecast: { title: t('AI 排班建议'), days: [] },
  templates: [],
  applications: [],
  assignees: [],
  addable: [],
})
const loading = ref(false)
const applying = ref(false)
const aiReady = ref(false)
const aiLoading = ref(false)
const confText = (c: string) => confidenceLabel(c)

const planOpen = ref(false)
const copying = ref(false)
const savingTpl = ref(false)
const pick = ref<null | {
  staffId: number
  name: string
  date: string
  dateLabel: string
  shift: string
}>(null)
const pickSaving = ref(false)
const addOpen = ref(false)
const addSaving = ref(false)
const addUserId = ref<string | number>('')

const forecast = computed(() => data.value.forecast || {})
const aiDays = computed(() => forecast.value.days || [])
const gapDays = computed(() => aiDays.value.filter((d: any) => d.has_gap))
const applyFrom = computed(() => forecast.value.apply_from || gapDays.value[0]?.date)
const applyTo = computed(
  () => forecast.value.apply_to || gapDays.value[gapDays.value.length - 1]?.date,
)
const pendingApps = computed(() =>
  (data.value.applications || []).filter((a: any) => a.status === 'pending'),
)
const doneApps = computed(() =>
  (data.value.applications || []).filter((a: any) => a.status !== 'pending'),
)
const colCount = computed(() => Math.max(1, (data.value.days || []).length))
const gridStyle = computed(() => ({
  gridTemplateColumns: `148px repeat(${view.value === 'month' ? 7 : colCount.value}, minmax(72px, 1fr))`,
}))
const monthWeeks = computed(() => data.value.weeks || [])
const visibleStaff = computed(() => data.value.staff || [])

function iso(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function parseIso(s: string) {
  const [y, m, d] = (s || '').split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

function shiftClass(type?: string) {
  if (type === 'morning') return 'sh-morning'
  if (type === 'afternoon') return 'sh-afternoon'
  if (type === 'night') return 'sh-night'
  if (type === 'off') return 'sh-off'
  return 'sh-empty'
}

function payloadView() {
  return { view: view.value, start: start.value || data.value.range_start }
}

async function load() {
  loading.value = true
  try {
    const board = await api.housekeepingStaffing(hotelStore.hotelId, {
      view: view.value,
      start: start.value || undefined,
    })
    data.value = board || data.value
    aiReady.value = false
    if (board?.range_start) start.value = board.range_start
    if (!addUserId.value && data.value.addable?.[0]?.id) {
      addUserId.value = data.value.addable[0].id
    }
  } catch (e: any) {
    toast(e?.message || t('排班加载失败'), false)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

async function setView(v: ViewMode) {
  if (view.value === v) return
  view.value = v
  await load()
}

async function nav(dir: number) {
  const base = parseIso(start.value || data.value.range_start || iso(new Date()))
  const step = view.value === 'day' ? 1 : view.value === 'week' ? 7 : 28
  base.setDate(base.getDate() + dir * step)
  start.value = iso(base)
  await load()
}

async function goToday() {
  start.value = iso(new Date())
  await load()
}

function openPick(staff: any, day: any, sh: any) {
  if (!day?.date) return
  pick.value = {
    staffId: Number(staff.id),
    name: staff.name,
    date: day.date,
    dateLabel: dayLabel(day),
    shift: sh?.shift || 'morning',
  }
}

async function confirmPick(code: string) {
  if (!pick.value || pickSaving.value) return
  pickSaving.value = true
  try {
    const board = await api.hkStaffingUpsertShift(hotelStore.hotelId, {
      user_id: pick.value.staffId,
      date: pick.value.date,
      shift: code,
      ...payloadView(),
    })
    data.value = board
    pick.value = null
    toast(t('班次已更新'))
  } catch (e: any) {
    toast(e?.message || t('改班失败'), false)
  } finally {
    pickSaving.value = false
  }
}

async function copyLastWeek() {
  if (copying.value) return
  copying.value = true
  try {
    const board = await api.hkStaffingCopyWeek(hotelStore.hotelId, payloadView())
    data.value = board
    const c = board?.copy || {}
    toast(
      t('已套用上周模板：写入 {n} 格{skipped}', {
        n: c.copied || 0,
        skipped: c.skipped ? t('，跳过手改 {n} 格', { n: c.skipped }) : '',
      }),
    )
  } catch (e: any) {
    toast(e?.message || t('复制失败'), false)
  } finally {
    copying.value = false
  }
}

async function saveTemplate() {
  if (savingTpl.value) return
  savingTpl.value = true
  try {
    const res = await api.hkStaffingSaveTemplate(hotelStore.hotelId, {
      start: start.value,
      name: t('默认周模板'),
    })
    toast(t('已存为模板「{name}」', { name: res?.name || t('默认周模板') }))
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    savingTpl.value = false
  }
}

async function submitAddStaff() {
  const uid = Number(addUserId.value)
  if (!uid) {
    toast(t('请选择员工'), false)
    return
  }
  addSaving.value = true
  try {
    const board = await api.hkStaffingAddStaff(hotelStore.hotelId, {
      user_id: uid,
      ...payloadView(),
    })
    data.value = board
    addOpen.value = false
    toast(t('已加入排班表'))
  } catch (e: any) {
    toast(e?.message || t('添加失败'), false)
  } finally {
    addSaving.value = false
  }
}

async function generateAiForecast() {
  if (aiLoading.value) return
  aiLoading.value = true
  try {
    const narr = await api.hkStaffingAiNarrate(hotelStore.hotelId, { days: 7 })
    data.value = { ...data.value, forecast: narr }
    aiReady.value = true
    const src = narr?.source
    if (src === 'llm') {
      toast(t('已生成 AI 排班建议'))
    } else if (src === 'rules_disabled') {
      toast(t('大模型未启用'), false)
    } else {
      toast(t('未能调用大模型，未生成 AI 建议。'), false)
    }
  } catch (e: any) {
    toast(e?.message || t('生成失败'), false)
  } finally {
    aiLoading.value = false
  }
}

function aiSourceLabel(insight: any) {
  const s = insight?.source
  if (s === 'llm') return t('AI 解读')
  if (s === 'fallback' || s === 'unavailable') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 未启用')
  return ''
}

async function applyDay(dayIso: string) {
  if (applying.value) return
  applying.value = true
  const prevForecast = data.value.forecast
  try {
    const res = await api.hkStaffingAiApply(hotelStore.hotelId, { day: dayIso })
    toast(
      t('已写入 {n} 格{skipped}', {
        n: res?.applied || 0,
        skipped: res?.skipped ? t('，手改跳过 {n}', { n: res.skipped }) : '',
      }),
    )
    const visible = (data.value.days || []).some((d: any) => d.date === dayIso)
    if (!visible && dayIso) {
      view.value = 'week'
      start.value = dayIso
    }
    await load()
    // 保留已生成的 LLM 解读面板（load 只刷新排班表）
    if (prevForecast?.narrative_html || prevForecast?.source) {
      data.value = { ...data.value, forecast: prevForecast }
      aiReady.value = true
    }
  } catch (e: any) {
    toast(e?.message || t('应用失败'), false)
  } finally {
    applying.value = false
  }
}

async function applyRange() {
  if (applying.value) return
  if (!applyFrom.value || !applyTo.value) {
    toast(t('当前无需改班'))
    return
  }
  // 走 Harness：先预览勾选再写库
  planOpen.value = true
}

async function onPlanConfirmed(res: any) {
  const prevForecast = data.value.forecast
  toast(t(res?.message || '补班安排已生效'))
  await load()
  if (prevForecast?.narrative_html || prevForecast?.source) {
    data.value = { ...data.value, forecast: prevForecast }
    aiReady.value = true
  }
}

async function decideApp(id: number, approved: boolean) {
  try {
    const board = await api.hkStaffingDecideRequest(hotelStore.hotelId, id, {
      approved,
      ...payloadView(),
    })
    data.value = board
    toast(approved ? t('已通过并写回排班') : t('已驳回'))
  } catch (e: any) {
    toast(e?.message || t('处理失败'), false)
  }
}

function sliceShifts(staff: any, offset: number, n = 7) {
  return (staff.shifts || []).slice(offset, offset + n)
}
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <HousekeepingTasksSubnav />
    <div class="page-head head-row">
      <div>
        <h1>{{ t('排班') }}</h1>
      </div>
      <div class="head-actions">
        <button class="btn btn-ghost" type="button" :disabled="copying" @click="copyLastWeek">
          {{ copying ? t('复制中…') : t('复制上周模板') }}
        </button>
        <button class="btn btn-ghost" type="button" :disabled="savingTpl" @click="saveTemplate">
          {{ savingTpl ? t('保存中…') : t('存为模板') }}
        </button>
        <button class="btn btn-primary" type="button" @click="addOpen = true">
          {{ t('+ 员工') }}
        </button>
      </div>
    </div>

    <div class="main-grid">
      <div class="card-clean cal-card">
        <div class="card-head cal-head-bar">
          <div class="toolbar-left">
            <div class="view-seg" role="tablist" :aria-label="t('视图')">
              <button type="button" :class="{ on: view === 'day' }" @click="setView('day')">
                {{ t('日') }}
              </button>
              <button type="button" :class="{ on: view === 'week' }" @click="setView('week')">
                {{ t('周') }}
              </button>
              <button type="button" :class="{ on: view === 'month' }" @click="setView('month')">
                {{ t('月') }}
              </button>
            </div>
            <div class="date-nav">
              <button type="button" class="nav-arr" :aria-label="t('上一区间')" @click="nav(-1)">
                ‹
              </button>
              <span class="range"
                >{{ data.week_label }}{{ loading ? ` · ${t('加载中')}` : '' }}</span
              >
              <button type="button" class="nav-arr" :aria-label="t('下一区间')" @click="nav(1)">
                ›
              </button>
              <button type="button" class="btn-today" @click="goToday">{{ t('今天') }}</button>
            </div>
          </div>
          <div class="cal-legend bar-legend">
            <span><i class="lg morning"></i>{{ t('早班 08-16') }}</span>
            <span><i class="lg afternoon"></i>{{ t('中班 12-20') }}</span>
            <span><i class="lg night"></i>{{ t('晚班 16-24') }}</span>
            <span><i class="lg off"></i>{{ t('休息') }}</span>
          </div>
        </div>

        <div class="cal-scroll">
          <!-- 日 / 周：单表 -->
          <div
            v-if="view !== 'month'"
            class="cal-inner"
            :style="{ minWidth: view === 'day' ? '420px' : '780px' }"
          >
            <div class="cal-head" :style="gridStyle">
              <div class="col-emp">{{ t('员工 / 日期') }}</div>
              <div
                v-for="(d, i) in data.days || []"
                :key="d.date || i"
                class="col-day"
                :class="{ today: d.is_today }"
              >
                {{ dayLabel(d) }}
              </div>
            </div>
            <div
              v-for="(s, si) in visibleStaff"
              :key="s.id || si"
              class="cal-row"
              :style="gridStyle"
            >
              <div class="cal-name">
                <div class="avatar-sm">{{ s.initial || (s.name || t('员')).slice(0, 1) }}</div>
                <div class="name-meta">
                  <div class="name">{{ s.name }}</div>
                  <div class="role">{{ roleLabel(s.role) }}</div>
                </div>
              </div>
              <button
                v-for="(sh, di) in s.shifts || []"
                :key="di"
                type="button"
                class="cal-cell"
                :class="[
                  shiftClass(sh?.shift || sh?.type),
                  {
                    today: data.days?.[di]?.is_today,
                    'ai-mark': sh?.ai,
                    'manual-mark': sh?.manual,
                  },
                ]"
                :title="
                  sh?.manual
                    ? t('手改班次，AI 不会覆盖')
                    : sh?.ai
                      ? t('AI 建议已写入')
                      : t('点击改班次')
                "
                @click="openPick(s, data.days?.[di], sh)"
              >
                <span v-if="sh?.ai" class="ai-corner">AI</span>
                <span class="cell-label">{{ cellLabel(sh) }}</span>
              </button>
            </div>
            <div v-if="!visibleStaff.length" class="empty">{{ t('暂无排班数据') }}</div>
          </div>

          <!-- 月：四张周表 -->
          <div v-else class="month-stack">
            <div v-for="w in monthWeeks" :key="w.offset" class="month-week">
              <div class="week-cap">{{ w.label }}</div>
              <div class="cal-inner month-inner">
                <div class="cal-head" :style="gridStyle">
                  <div class="col-emp">{{ t('员工 / 日期') }}</div>
                  <div
                    v-for="(d, i) in w.days || []"
                    :key="d.date || i"
                    class="col-day"
                    :class="{ today: d.is_today }"
                  >
                    {{ dayLabel(d) }}
                  </div>
                </div>
                <div
                  v-for="(s, si) in visibleStaff"
                  :key="s.id || si"
                  class="cal-row"
                  :style="gridStyle"
                >
                  <div class="cal-name">
                    <div class="avatar-sm">{{ s.initial || (s.name || t('员')).slice(0, 1) }}</div>
                    <div class="name-meta">
                      <div class="name">{{ s.name }}</div>
                      <div class="role">{{ roleLabel(s.role) }}</div>
                    </div>
                  </div>
                  <button
                    v-for="(sh, di) in sliceShifts(s, w.offset)"
                    :key="di"
                    type="button"
                    class="cal-cell"
                    :class="[
                      shiftClass(sh?.shift || sh?.type),
                      {
                        today: w.days?.[di]?.is_today,
                        'ai-mark': sh?.ai,
                        'manual-mark': sh?.manual,
                      },
                    ]"
                    :title="
                      sh?.manual
                        ? t('手改班次，AI 不会覆盖')
                        : sh?.ai
                          ? t('AI 建议已写入')
                          : t('点击改班次')
                    "
                    @click="openPick(s, w.days?.[di], sh)"
                  >
                    <span v-if="sh?.ai" class="ai-corner">AI</span>
                    <span class="cell-label">{{ cellLabel(sh) }}</span>
                  </button>
                </div>
              </div>
            </div>
            <div v-if="!monthWeeks.length" class="empty">{{ t('暂无月排班') }}</div>
          </div>
        </div>
      </div>

      <div class="side-col">
        <div v-if="commercialEnabled()" class="ai-card ai-side">
          <div class="ttl">
            <span class="material-symbols-outlined">auto_awesome</span>
            {{ t(forecast.title || 'AI 排班建议') }}
          </div>
          <template v-if="aiLoading">
            <p class="ai-wait">{{ t('正在结合规则事实调用本地模型生成解读…') }}</p>
          </template>
          <template v-else-if="aiReady && forecast.source === 'llm'">
            <p class="ai-meta">
              <span>{{ aiSourceLabel(forecast) }}</span>
              <span v-if="formatAiModelMeta(forecast)" class="conf-pill">{{
                formatAiModelMeta(forecast)
              }}</span>
              <span v-if="forecast.confidence" class="conf-pill">{{
                confText(forecast.confidence)
              }}</span>
              <span v-if="forecast.confidence_note"> · {{ t(forecast.confidence_note) }}</span>
            </p>
            <div
              v-if="forecast.narrative_html"
              class="ai-insight-body"
              v-html="forecast.narrative_html"
            />
            <p v-if="forecast.llm_error" class="ai-soft-err">{{ t(forecast.llm_error) }}</p>
            <div class="ai-days">
              <div v-for="c in aiDays" :key="c.date" class="ai-day" :class="{ gap: c.has_gap }">
                <div class="ai-day-top">
                  <strong>{{ c.label }}</strong>
                  <span class="need">{{ t('预离 {n} 间', { n: c.need_clean }) }}</span>
                </div>
                <p class="ai-reason">{{ c.reason }}</p>
                <p class="ai-suggest">{{ t('建议：') }}{{ c.suggest }}</p>
                <button
                  class="btn btn-primary sm"
                  type="button"
                  :disabled="applying || !c.has_gap"
                  @click="applyDay(c.date)"
                >
                  {{ t('AI应用到 {day}', { day: c.short }) }}
                </button>
              </div>
              <div v-if="!aiDays.length" class="empty">{{ t('暂无预测') }}</div>
            </div>
            <button
              class="btn btn-primary bulk"
              type="button"
              :disabled="applying || !gapDays.length"
              @click="applyRange"
            >
              {{ t('AI生成补班安排') }}
            </button>
            <button
              class="btn btn-ghost bulk"
              type="button"
              :disabled="aiLoading"
              @click="generateAiForecast"
            >
              {{ t('重新生成建议') }}
            </button>
          </template>
          <template v-else-if="aiReady">
            <p class="ai-meta">
              <span>{{ t('AI 暂不可用') }}</span>
            </p>
            <p class="ai-soft-err">
              {{ t(forecast.llm_error || '未能调用大模型，未生成 AI 建议。') }}
            </p>
            <button
              class="btn btn-ghost bulk"
              type="button"
              :disabled="aiLoading"
              @click="generateAiForecast"
            >
              {{ t('重新生成建议') }}
            </button>
          </template>
          <template v-else>
            <button
              class="btn btn-primary bulk"
              type="button"
              :disabled="aiLoading || loading"
              @click="generateAiForecast"
            >
              {{ t('生成 AI 排班建议') }}
            </button>
          </template>
          <HkAiPlanDrawer
            v-model:open="planOpen"
            scene="staffing_gap"
            @confirmed="onPlanConfirmed"
          />
        </div>

        <div class="card-clean apps-card">
          <div class="card-head">
            <span class="title">{{ t('请假 / 换班') }}</span>
          </div>
          <div class="card-pad">
            <div v-for="a in pendingApps" :key="a.id" class="app-item">
              <div class="app-top">
                <span class="app-kind">{{
                  t(a.kind_label || (a.kind === 'leave' ? '请假' : '换班'))
                }}</span>
                <span class="app-date">{{ a.date }}</span>
              </div>
              <p class="app-note">
                <strong>{{ a.staff }}</strong> · {{ t(a.note || '') }}
              </p>
              <div class="app-act">
                <button type="button" class="btn btn-primary sm" @click="decideApp(a.id, true)">
                  {{ t('通过') }}
                </button>
                <button type="button" class="btn btn-ghost sm" @click="decideApp(a.id, false)">
                  {{ t('驳回') }}
                </button>
              </div>
            </div>
            <div v-if="!pendingApps.length" class="empty">{{ t('暂无待批申请') }}</div>
            <div v-if="doneApps.length" class="done-apps">
              <div v-for="a in doneApps.slice(0, 4)" :key="'d' + a.id" class="app-done">
                {{ a.staff }} · {{ t(a.kind_label || '') }} · {{ t(a.status_label || '') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pick" class="mask" @click.self="pick = null">
      <div class="panel" role="dialog" :aria-label="t('改班次')">
        <header>
          <h3>{{ t('改班次') }}</h3>
          <button type="button" class="x" @click="pick = null">×</button>
        </header>
        <p class="pick-meta">{{ pick.name }} · {{ pick.dateLabel }}</p>
        <div class="shift-grid">
          <button
            v-for="opt in SHIFT_OPTS"
            :key="opt.code"
            type="button"
            class="shift-opt"
            :class="[shiftClass(opt.code), { on: pick.shift === opt.code }]"
            :disabled="pickSaving"
            @click="confirmPick(opt.code)"
          >
            <strong>{{ t(opt.labelKey) }}</strong>
            <span>{{ opt.hours || t('全天休息') }}</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="addOpen" class="mask" @click.self="addOpen = false">
      <div class="panel" role="dialog" :aria-label="t('添加员工')">
        <header>
          <h3>{{ t('添加员工') }}</h3>
          <button type="button" class="x" @click="addOpen = false">×</button>
        </header>
        <div class="form">
          <label
            >{{ t('员工')
            }}<select v-model="addUserId">
              <option v-for="a in data.addable || []" :key="a.id" :value="a.id">
                {{ a.name }}
              </option>
            </select>
          </label>
          <p v-if="!(data.addable || []).length" class="hint-inline">
            {{ t('当前店内员工都已在排班表中。') }}
          </p>
        </div>
        <footer>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="addSaving"
            @click="addOpen = false"
          >
            {{ t('取消') }}
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="addSaving || !(data.addable || []).length"
            @click="submitAddStaff"
          >
            {{ addSaving ? t('添加中…') : t('加入本区间') }}
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.main-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
}
.cal-card {
  grid-column: span 8;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.cal-head-bar {
  background: var(--surface-low);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.view-seg {
  display: inline-flex;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.view-seg button {
  height: 32px;
  padding: 0 12px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
}
.view-seg button.on {
  background: var(--primary);
  color: #fff;
}
.date-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-arr {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}
.range {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
  min-width: 132px;
  text-align: center;
}
.btn-today {
  height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}
.bar-legend {
  margin: 0;
  padding: 0;
  gap: 12px;
}
.cal-scroll {
  padding: 16px;
  overflow-x: auto;
}
.cal-inner {
  min-width: 780px;
}
.month-inner {
  min-width: 760px;
}
.month-week {
  margin-bottom: 18px;
}
.week-cap {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin: 0 0 8px;
}
.cal-head {
  display: grid;
  gap: 8px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin-bottom: 12px;
}
.col-emp {
  text-align: left;
  padding-left: 8px;
}
.col-day {
  padding: 4px;
  border-radius: 8px;
}
.col-day.today {
  color: var(--primary);
  background: rgba(0, 91, 191, 0.08);
}
.cal-row {
  display: grid;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.cal-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--secondary-container);
  color: var(--on-secondary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.name {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.role {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.cal-cell {
  height: 48px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4px 2px;
  position: relative;
  white-space: pre-line;
  line-height: 1.25;
  cursor: pointer;
  font-family: inherit;
}
.cal-cell.today {
  box-shadow: inset 0 0 0 2px var(--primary);
}
.cal-cell.ai-mark {
  box-shadow: inset 0 0 0 2px #c9a227;
}
.cal-cell.ai-mark.today {
  box-shadow:
    inset 0 0 0 2px #c9a227,
    0 0 0 1px var(--primary);
}
.ai-corner {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 9px;
  font-weight: 800;
  color: #8a6d12;
  background: #f5e6a8;
  border-radius: 3px;
  padding: 0 3px;
  line-height: 1.4;
}
.sh-morning {
  background: #d6e4ff;
  color: #0b3b8c;
  border: 1px solid rgba(11, 59, 140, 0.22);
}
.sh-afternoon {
  background: #d7f3e3;
  color: #0d5c32;
  border: 1px solid rgba(13, 92, 50, 0.22);
}
.sh-night {
  background: #e8ddff;
  color: #3b1d7a;
  border: 1px solid rgba(59, 29, 122, 0.22);
}
.sh-off {
  background: var(--surface-high);
  color: rgba(65, 71, 84, 0.55);
  border: 1px solid transparent;
}
.sh-empty {
  background: var(--surface);
  color: var(--on-surface-variant);
  border: 1px dashed var(--outline-variant);
}
.cal-legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  flex-wrap: wrap;
}
.cal-legend .lg {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
  margin-right: 4px;
  vertical-align: -2px;
}
.lg.morning {
  background: #d6e4ff;
  border: 1px solid rgba(11, 59, 140, 0.3);
}
.lg.afternoon {
  background: #d7f3e3;
  border: 1px solid rgba(13, 92, 50, 0.3);
}
.lg.night {
  background: #e8ddff;
  border: 1px solid rgba(59, 29, 122, 0.3);
}
.lg.off {
  background: var(--surface-high);
}
.hint {
  margin: 0 16px 14px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.hint-inline {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.side-col {
  grid-column: span 4;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ai-side {
  padding: 16px;
}

.ai-meta {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin: 0 0 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.conf-pill {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 700;
  color: #475569;
}
.ai-insight-body {
  margin-bottom: 12px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 8px;
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid var(--outline-variant);
  background: #f8fafc;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 11px;
  font-weight: 800;
  color: var(--primary);
  margin-bottom: 6px;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 16px;
}
.ai-insight-body :deep(li) {
  font-size: 12px;
  line-height: 1.45;
  margin-bottom: 3px;
}
.ai-soft-err {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin: 0 0 8px;
}

.ai-wait {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ai-sub {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.ai-days {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
}
.ai-day {
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--surface-low);
}
.ai-day.gap {
  background: #fff;
}
.ai-day-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.ai-day-top strong {
  font-size: 13px;
}
.need {
  font-size: 11px;
  font-weight: 700;
  color: var(--tertiary);
}
.ai-reason,
.ai-suggest {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.ai-suggest {
  color: var(--on-surface);
  font-weight: 600;
}
.btn.sm {
  padding: 6px 10px;
  font-size: 12px;
}
.btn.bulk {
  width: 100%;
  margin-top: 12px;
}
.ai-disc {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.card-head .title {
  font-size: 16px;
  font-weight: 700;
}
.app-item {
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  background: var(--surface-low);
}
.app-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 6px;
}
.app-kind {
  font-weight: 700;
  color: var(--primary);
}
.app-note {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.4;
}
.app-act {
  display: flex;
  gap: 8px;
}
.app-done {
  font-size: 12px;
  color: var(--on-surface-variant);
  padding: 4px 0;
}
.done-apps {
  margin-top: 8px;
  border-top: 1px dashed var(--outline-variant);
  padding-top: 8px;
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  padding: 16px;
  font-size: 13px;
}
.mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.panel {
  width: min(420px, 100%);
  background: #fff;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
}
.panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.panel h3 {
  margin: 0;
  font-size: 16px;
}
.panel .x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  color: #6b7280;
}
.pick-meta {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.shift-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.shift-opt {
  border-radius: 10px;
  padding: 12px 8px;
  cursor: pointer;
  font-family: inherit;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}
.shift-opt.on {
  outline: 2px solid var(--primary);
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
}
.form select {
  height: 36px;
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 0 10px;
}
.panel footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
@media (max-width: 960px) {
  .cal-card,
  .side-col {
    grid-column: span 12 !important;
  }
}
</style>
