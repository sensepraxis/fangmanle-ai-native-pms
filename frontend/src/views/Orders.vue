<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, td } from '../lib/i18n'

import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { fmt, ORDER_ST_CN, ORDER_ST_PILL, PAY_CN, PAY_PILL, toast } from '../lib/ui'
import BoardAiPanel from '../components/BoardAiPanel.vue'
import {
  checkoutBtnLabel,
  primaryOrderAction,
  primaryOrderActionLabel,
  isUnassignedOrder,
  assignStatusOf,
  ASSIGN_ST_CN,
  ASSIGN_ST_PILL,
  ORDER_WORK_TABS,
  ORDER_BASE_FLOWS,
  ORDER_SOURCE_BRANCH,
  ORDER_GROUP_KEYS,
  ORDER_COMBO_SEARCH_FIELDS,
  emptyComboSearch,
  hasComboSearch,
  comboSearchSummary,
  SOURCE_LABEL,
  workTabCount,
  sourcePillClass,
  channelDisplayLabel,
  stayTypeLabel,
  formatOrderDateTime,
  normalizeWorkSummary,
  type OrderWorkView,
  type OrderWorkSummary,
  type OrderComboSearch,
} from '../lib/orderFlow'

const router = useRouter()
const route = useRoute()

const workView = ref<OrderWorkView>('arrivals')
const sourceTab = ref('all')
const searchDraft = ref<OrderComboSearch>(emptyComboSearch())
const searchApplied = ref<OrderComboSearch>(emptyComboSearch())
const bizDate = ref(new Date().toISOString().slice(0, 10))
const page = ref(1)
const pageSize = ref(20)

const orders = ref<any[]>([])
const total = ref(0)
const summary = ref<OrderWorkSummary | null>(null)
const channels = ref<any[]>([])
const roomTypes = ref<any[]>([])
const loadError = ref('')
const loading = ref(false)
const pendingAssignCount = computed(() => summary.value?.unassigned ?? 0)
const boardSources = ref<{ key: string; label: string; count: number }[]>([])
const aiRiskById = ref<Record<number, any>>({})
const sourceBranch = computed(() => ORDER_SOURCE_BRANCH[sourceTab.value] || null)

const activeSourceLabel = computed(() => {
  if (sourceTab.value === 'all') return t('全部来源')
  const raw =
    SOURCE_LABEL[sourceTab.value] ||
    groupPills.value.find((p) => p.key === sourceTab.value)?.label ||
    sourceTab.value
  return t(raw)
})

const activeWorkLabel = computed(() =>
  t(ORDER_WORK_TABS.find((x) => x.key === workView.value)?.label || ''),
)

const emptyFilterDesc = computed(() => {
  // 【按产品要求】去掉 '当前筛选：... 搜索会在上述条件下查找...' 这一行字
  return ''
})

const hasActiveFilter = computed(() => {
  if (loading.value || orders.value.length) return false
  if (workView.value !== 'all') return true
  if (sourceTab.value !== 'all') return true
  if (hasComboSearch(searchApplied.value)) return true
  return false
})

const groupPills = computed(() => {
  const map = new Map(boardSources.value.map((s) => [s.key, s]))
  return ORDER_GROUP_KEYS.map((key) => {
    const hit = map.get(key)
    return {
      key,
      label: t(SOURCE_LABEL[key] || hit?.label || key),
      count: hit?.count ?? 0,
    }
  })
})

const hasAppliedCombo = computed(() => hasComboSearch(searchApplied.value))

const workTabs = computed(() =>
  ORDER_WORK_TABS.map((tab) => ({
    ...tab,
    label: t(tab.label),
    count: workTabCount(summary.value, tab.key),
  })),
)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const pageRange = computed(() => {
  const start = total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1
  const end = Math.min(page.value * pageSize.value, total.value)
  return { start, end }
})

function selectSource(key: string) {
  sourceTab.value = key
  onSourceChange()
}

function clearSourceFilter() {
  selectSource('all')
}

function clearWorkFilter() {
  setView('all')
}

function searchInAllSources() {
  if (sourceTab.value === 'all') return
  selectSource('all')
}

function clearAllFilters() {
  searchDraft.value = emptyComboSearch()
  searchApplied.value = emptyComboSearch()
  sourceTab.value = 'all'
  workView.value = 'all'
  page.value = 1
  router.replace({ query: {} })
  load()
}

function openBaseFlow(card: { path?: string; sourceKey?: string }) {
  if (card.path) {
    router.push(card.path)
    return
  }
  if (card.sourceKey) selectSource(card.sourceKey)
}

async function loadMeta() {
  const [rts, chs] = await Promise.all([api.listRooms(hotelStore.hotelId), api.listChannels()])
  const map: Record<number, any> = {}
  rts.forEach((r: any) => {
    if (!map[r.room_type_id]) {
      map[r.room_type_id] = {
        id: r.room_type_id,
        name: r.room_type_name,
        base_price: r.base_price,
      }
    }
  })
  roomTypes.value = Object.values(map)
  channels.value = chs
}

async function loadBoard() {
  try {
    const board = await api.ordersBoard(hotelStore.hotelId)
    const map = new Map<string, { label?: string; count?: number }>(
      (board?.sources || []).map((s: any) => [String(s.key), s]),
    )
    boardSources.value = ORDER_GROUP_KEYS.map((key) => ({
      key,
      label: SOURCE_LABEL[key] || map.get(key)?.label || key,
      count: Number(map.get(key)?.count ?? 0),
    }))
  } catch {
    boardSources.value = ORDER_GROUP_KEYS.map((key) => ({
      key,
      label: SOURCE_LABEL[key] || key,
      count: 0,
    }))
  }
}

async function loadAiRisks() {
  try {
    const res = await api.ordersAiRisks(hotelStore.hotelId)
    const map: Record<number, any> = {}
    for (const [k, v] of Object.entries(res?.by_order_id || {})) {
      map[Number(k)] = v
    }
    aiRiskById.value = map
  } catch {
    aiRiskById.value = {}
  }
}

function riskOf(o: any) {
  return aiRiskById.value[o?.id]
}

async function load() {
  loadError.value = ''
  loading.value = true
  const applied = searchApplied.value
  try {
    const [res, sumRaw] = await Promise.all([
      api.listOrdersPage(hotelStore.hotelId, {
        view: workView.value,
        source: sourceTab.value,
        onDate: bizDate.value,
        page: page.value,
        pageSize: pageSize.value,
        channelId: applied.channel_id || undefined,
        roomTypeId: applied.room_type_id || undefined,
        status: applied.status || undefined,
        paymentStatus: applied.payment_status || undefined,
        combo: {
          order_no: applied.order_no,
          external_order_no: applied.external_order_no,
          reception_no: applied.reception_no,
          room_no: applied.room_no,
          guest_name: applied.guest_name,
          phone: applied.phone,
          note: applied.note,
        },
      }),
      api.ordersSummary(hotelStore.hotelId, bizDate.value).catch(() => null),
    ])
    orders.value = res.items
    total.value = res.total
    summary.value = normalizeWorkSummary(sumRaw || res.summary, bizDate.value)
  } catch (e: any) {
    orders.value = []
    total.value = 0
    loadError.value = e?.message || t('订单加载失败')
  } finally {
    loading.value = false
  }
}

function onSourceChange() {
  router.replace({
    query: { ...route.query, source: sourceTab.value === 'all' ? undefined : sourceTab.value },
  })
  onFilterChange()
}

function setView(key: OrderWorkView) {
  workView.value = key
  page.value = 1
  router.replace({ query: { ...route.query, view: key === 'arrivals' ? undefined : key } })
  load()
}

function onFilterChange() {
  page.value = 1
  load()
}

function runSearch() {
  searchApplied.value = { ...searchDraft.value }
  page.value = 1
  load()
}

function resetComboSearch() {
  searchDraft.value = emptyComboSearch()
  searchApplied.value = emptyComboSearch()
  page.value = 1
  load()
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  load()
}

async function doCheckin(id: number) {
  if (!confirm(t('确认为该订单办理入住（自动分配同房型空房）？'))) return
  await api.checkin(id)
  toast(t('已办理入住'))
  await Promise.all([loadBoard(), load()])
}

async function doPrimary(o: any) {
  const act = primaryOrderAction(o)
  if (act === 'checkin') {
    if (o.is_group || o.source_group === 'group' || o.order_type === 5) {
      router.push(`/orders/${o.id}`)
      return
    }
    if (isUnassignedOrder(o)) {
      router.push({
        path: '/c5-frontdesk/pending-assignment',
        query: { orderId: String(o.id) },
      })
      return
    }
    await doCheckin(o.id)
    return
  }
  if (act === 'checkout') {
    router.push({ path: '/c5-frontdesk/cashiering-checkout', query: { orderId: String(o.id) } })
    return
  }
  router.push(`/orders/${o.id}`)
}

async function doCancel(o: any, e?: Event) {
  e?.stopPropagation()
  if (!confirm(t('确认取消订单 {no}？', { no: o.order_no }))) return
  await api.cancelOrder(o.id, t('前台取消'))
  toast(t('订单已取消'))
  await Promise.all([loadBoard(), load()])
}

onMounted(async () => {
  const v = route.query.view
  const views = [
    'all',
    'arrivals',
    'inhouse',
    'departures',
    'created_today',
    'unassigned',
    'pending',
  ]
  if (typeof v === 'string' && views.includes(v)) {
    workView.value = v as OrderWorkView
  }
  const src = route.query.source
  if (typeof src === 'string' && src) sourceTab.value = src
  const gn = route.query.guest_name
  if (typeof gn === 'string' && gn.trim()) {
    searchDraft.value.guest_name = gn.trim()
    searchApplied.value.guest_name = gn.trim()
  }
  const pay = route.query.payment_status
  if (typeof pay === 'string' && pay.trim()) {
    searchDraft.value.payment_status = pay.trim()
    searchApplied.value.payment_status = pay.trim()
  }
  const st = route.query.status
  if (typeof st === 'string' && st.trim()) {
    searchDraft.value.status = st.trim()
    searchApplied.value.status = st.trim()
  }
  await loadMeta()
  await Promise.all([loadBoard(), load(), loadAiRisks()])
})

watch(
  () => hotelStore.hotelId,
  async () => {
    await loadMeta()
    page.value = 1
    await Promise.all([loadBoard(), load(), loadAiRisks()])
  },
)
</script>

<template>
  <div class="page orders-hub">
    <header class="hub-head">
      <div class="hub-head-row">
        <div>
          <h1>{{ t('订单中心') }}</h1>
          <div v-if="summary" class="hub-stats">
            <span class="stat"
              >{{ t('预抵') }} <strong>{{ summary.arrivals }}</strong></span
            >
            <span class="stat-sep">·</span>
            <span class="stat"
              >{{ t('在住') }} <strong>{{ summary.inhouse }}</strong></span
            >
            <span class="stat-sep">·</span>
            <span class="stat"
              >{{ t('预离') }} <strong>{{ summary.departures }}</strong></span
            >
            <template v-if="pendingAssignCount > 0">
              <span class="stat-sep">·</span>
              <button type="button" class="stat-link" @click="setView('unassigned')">
                {{ t('待分房') }} {{ pendingAssignCount }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </header>
    <p v-if="loadError" class="err">{{ loadError }}</p>

    <BoardAiPanel
      kind="order_risks"
      :title="t('订单风险 AI 解读')"
      idle=""
      :run-label="t('解读风险订单')"
      :rerun-label="t('重新解读')"
      :wait-label="t('正在汇总催付/逾期/取消风险…')"
    />

    <section class="hub-section">
      <h2 class="section-title">{{ t('到店办单') }}</h2>
      <div class="base-grid">
        <button
          v-for="card in ORDER_BASE_FLOWS"
          :key="card.key"
          type="button"
          class="flow-card"
          @click="openBaseFlow(card)"
        >
          <span class="material-symbols-outlined flow-ico">{{ card.icon }}</span>
          <div class="flow-title">{{ t(card.title) }}</div>
          <div class="flow-desc">{{ t(card.desc) }}</div>
        </button>
      </div>
    </section>

    <section class="hub-section work-section">
      <h2 class="section-title">{{ t('住宿订单') }}</h2>
      <nav class="view-tabs view-tabs-scroll">
        <button
          v-for="tag in workTabs"
          :key="tag.key"
          type="button"
          class="view-tab"
          :class="{ active: workView === tag.key }"
          @click="setView(tag.key as OrderWorkView)"
        >
          {{ tag.label }}
          <span class="cnt">{{ tag.count }}</span>
        </button>
      </nav>

      <div class="combo-search card-clean">
        <div class="combo-search-head">
          <span class="combo-search-title">{{ t('订单搜索') }}</span>
        </div>
        <div class="combo-form-grid">
          <label v-for="field in ORDER_COMBO_SEARCH_FIELDS" :key="field.key" class="combo-field">
            <span class="combo-label">{{ t(field.label) }}</span>
            <input
              v-model="searchDraft[field.key as keyof OrderComboSearch]"
              class="combo-inp"
              type="text"
              :placeholder="t(field.placeholder)"
              @keydown.enter.prevent="runSearch"
            />
          </label>
          <label class="combo-field">
            <span class="combo-label">{{ t('渠道') }}</span>
            <select v-model.number="searchDraft.channel_id" class="combo-inp">
              <option :value="0">{{ t('全部渠道') }}</option>
              <option v-for="c in channels" :key="c.id" :value="c.id">{{ t(c.name) }}</option>
            </select>
          </label>
          <label class="combo-field">
            <span class="combo-label">{{ t('房型') }}</span>
            <select v-model.number="searchDraft.room_type_id" class="combo-inp">
              <option :value="0">{{ t('全部房型') }}</option>
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
            </select>
          </label>
          <label class="combo-field">
            <span class="combo-label">{{ t('入住状态') }}</span>
            <select v-model="searchDraft.status" class="combo-inp">
              <option value="">{{ t('全部') }}</option>
              <option value="pending">{{ t('待入住') }}</option>
              <option value="confirmed">{{ t('已确认') }}</option>
              <option value="checked_in">{{ t('在住') }}</option>
              <option value="checked_out">{{ t('已退房') }}</option>
              <option value="cancelled">{{ t('已取消') }}</option>
            </select>
          </label>
          <label class="combo-field">
            <span class="combo-label">{{ t('结账状态') }}</span>
            <select v-model="searchDraft.payment_status" class="combo-inp">
              <option value="">{{ t('全部') }}</option>
              <option value="unpaid">{{ t('未支付') }}</option>
              <option value="partial">{{ t('部分付') }}</option>
              <option value="paid">{{ t('已支付') }}</option>
              <option value="on_account">{{ t('挂账') }}</option>
              <option value="refunded">{{ t('已退') }}</option>
            </select>
          </label>
          <label class="combo-field">
            <span class="combo-label">{{ t('营业日') }}</span>
            <input v-model="bizDate" type="date" class="combo-inp" />
          </label>
        </div>
        <div class="combo-actions">
          <button type="button" class="btn btn-primary" @click="runSearch">{{ t('搜索') }}</button>
          <button type="button" class="btn btn-ghost" @click="resetComboSearch">
            {{ t('重置') }}
          </button>
          <span v-if="hasAppliedCombo" class="combo-applied">
            {{ t('已生效') }}：{{ comboSearchSummary(searchApplied).join(' · ') }}</span
          >
        </div>
      </div>

      <div class="group-bar card-clean">
        <div class="group-bar-head">
          <span class="group-label">{{ t('来源') }}</span>
          <button
            v-if="sourceTab !== 'all'"
            type="button"
            class="link-btn"
            @click="clearSourceFilter"
          >
            {{ t('清除过滤') }}
          </button>
        </div>
        <div class="group-pills">
          <button
            v-for="pill in groupPills"
            :key="pill.key"
            type="button"
            class="group-pill"
            :class="{ active: sourceTab === pill.key }"
            @click="selectSource(pill.key)"
          >
            {{ pill.label }}
            <span class="pill-cnt">{{ pill.count }}</span>
          </button>
        </div>
      </div>

      <div v-if="sourceTab !== 'all' || workView !== 'all'" class="filter-ribbon">
        <span class="filter-ribbon-label">{{ t('当前筛选') }}</span>
        <button
          v-if="workView !== 'all'"
          type="button"
          class="filter-chip"
          :title="t('点击去掉该条件')"
          @click="clearWorkFilter"
        >
          {{ activeWorkLabel }}
          <span class="chip-x" aria-hidden="true">×</span>
        </button>
        <button
          v-if="sourceTab !== 'all'"
          type="button"
          class="filter-chip"
          :title="t('点击去掉该条件')"
          @click="clearSourceFilter"
        >
          {{ activeSourceLabel }}
          <span class="chip-x" aria-hidden="true">×</span>
        </button>
        <button type="button" class="filter-chip clear" @click="clearAllFilters">
          {{ t('清除全部') }}
        </button>
      </div>

      <div v-if="sourceBranch" class="context-bar card-clean">
        <span class="material-symbols-outlined ctx-ico">{{ sourceBranch.icon }}</span>
        <p class="ctx-text">{{ t(sourceBranch.hint) }}</p>
        <button
          type="button"
          class="btn btn-outline btn-sm ctx-btn"
          @click="router.push(sourceBranch.path)"
        >
          {{ t(sourceBranch.label) }} →
        </button>
      </div>

      <div class="card-clean table-wrap">
        <div v-if="loading" class="table-loading">{{ t('加载中…') }}</div>
        <div v-else-if="!orders.length" class="empty-box">
          <p class="empty-title">{{ t('暂无符合条件的订单') }}</p>
          <div v-if="hasActiveFilter" class="empty-actions">
            <button
              v-if="sourceTab !== 'all' && hasAppliedCombo"
              type="button"
              class="btn btn-primary btn-sm"
              @click="searchInAllSources"
            >
              {{ t('清除来源筛选并保留组合条件') }}
            </button>
            <button
              v-if="sourceTab !== 'all'"
              type="button"
              class="btn btn-ghost btn-sm"
              @click="clearSourceFilter"
            >
              {{ t('清除来源筛选') }}
            </button>
            <button
              v-if="workView !== 'all'"
              type="button"
              class="btn btn-ghost btn-sm"
              @click="setView('all')"
            >
              {{ t('切换到全部预订') }}
            </button>
          </div>
        </div>
        <table v-else class="data order-table order-table-wide">
          <thead>
            <tr>
              <th>{{ t('订单号') }}</th>
              <th>{{ t('渠道单号') }}</th>
              <th>{{ t('联系人') }}</th>
              <th>{{ t('手机号') }}</th>
              <th>{{ t('入住类型') }}</th>
              <th>{{ t('房型') }}</th>
              <th>{{ t('分房') }}</th>
              <th>{{ t('入住时间') }}</th>
              <th>{{ t('离店时间') }}</th>
              <th>{{ t('渠道') }}</th>
              <th class="num">{{ t('房费') }}</th>
              <th class="num">{{ t('订单总额') }}</th>
              <th>{{ t('入住状态') }}</th>
              <th>{{ t('结账状态') }}</th>
              <th>{{ t('创建时间') }}</th>
              <th class="center">{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in orders"
              :key="o.id"
              class="clickable"
              @click="router.push(`/orders/${o.id}`)"
            >
              <td>
                <span class="mono link order-no" @click.stop="router.push(`/orders/${o.id}`)">{{
                  o.order_no
                }}</span>
                <div v-if="o.reception_no" class="sub mono">
                  {{ t('预分') }} {{ o.reception_no }}
                </div>
                <div v-if="riskOf(o)" class="ai-risk-wrap">
                  <span
                    class="ai-risk"
                    :class="'risk-' + (riskOf(o).risk_code || 'pay')"
                    :title="riskOf(o).reason"
                    @click.stop="
                      router.push({
                        path: '/analytics/order-health/churn-warning',
                        query: { focus_order_id: String(o.id) },
                      })
                    "
                    >{{ t(riskOf(o).risk_label) }}</span
                  >
                </div>
              </td>
              <td class="mono sub-cell">
                {{ o.external_order_no || o.voucher_code || '—' }}
              </td>
              <td>
                <span
                  class="link guest-name"
                  @click.stop="o.guest_id && router.push(`/guests/${o.guest_id}`)"
                  >{{ o.guest_name }}</span
                >
              </td>
              <td class="mono sub-cell">{{ o.phone || '—' }}</td>
              <td>
                <span class="stay-type">{{ stayTypeLabel(o) }}</span>
              </td>
              <td>{{ o.room_type_name || '—' }}</td>
              <td>
                <span class="pill" :class="ASSIGN_ST_PILL[assignStatusOf(o)] || 'pill-slate'">
                  {{ td(ASSIGN_ST_CN, assignStatusOf(o), assignStatusOf(o)) }}</span
                >
              </td>
              <td class="dates">
                {{ o.check_in }}{{ o.arrival_time ? ` ${o.arrival_time}` : '' }}
              </td>
              <td class="dates">{{ o.check_out }}</td>
              <td>
                <span class="src-pill" :class="sourcePillClass(o.source_group)">
                  {{ channelDisplayLabel(o) }}</span
                >
              </td>
              <td class="num">{{ fmt(o.room_charge ?? o.total_amount) }}</td>
              <td class="num">{{ fmt(o.total_amount) }}</td>
              <td>
                <span class="pill" :class="ORDER_ST_PILL[o.status] || 'pill-slate'">
                  {{ td(ORDER_ST_CN, o.status, o.status) }}</span
                >
              </td>
              <td>
                <span class="pill" :class="PAY_PILL[o.payment_status] || 'pill-slate'">
                  {{ td(PAY_CN, o.payment_status, o.payment_status) }}</span
                >
              </td>
              <td class="dates">{{ formatOrderDateTime(o.created_at, o.check_in) }}</td>
              <td class="center" @click.stop>
                <div class="row-actions">
                  <button
                    class="btn btn-ghost btn-sm"
                    type="button"
                    @click="router.push(`/orders/${o.id}`)"
                  >
                    {{ t('详情') }}
                  </button>
                  <button
                    v-if="primaryOrderAction(o)"
                    class="btn btn-primary btn-sm"
                    type="button"
                    @click="doPrimary(o)"
                  >
                    {{
                      primaryOrderAction(o) === 'checkout'
                        ? checkoutBtnLabel(o)
                        : primaryOrderActionLabel(o)
                    }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="pager">
        <span class="pager-info">
          {{
            t('第 {start}–{end} 条，共 {total} 条', {
              start: pageRange.start,
              end: pageRange.end,
              total,
            })
          }}</span
        >
        <div class="pager-btns">
          <button
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="page <= 1"
            @click="goPage(page - 1)"
          >
            {{ t('上一页') }}
          </button>
          <span class="pager-num">{{ page }} / {{ totalPages }}</span>
          <button
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="page >= totalPages"
            @click="goPage(page + 1)"
          >
            {{ t('下一页') }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.orders-hub {
  width: 100%;
  max-width: none;
}
.hub-head {
  margin-bottom: 20px;
}
.hub-head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.hub-head h1 {
  font-family: 'Source Sans 3', system-ui, sans-serif;
  margin: 0 0 6px;
  font-size: 32px;
  font-weight: 700;
  line-height: 40px;
  color: var(--on-surface, #1f2329);
}
.hub-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: #5b616e;
}
.stat strong {
  font-variant-numeric: tabular-nums;
  color: #1f2329;
}
.stat-sep {
  color: #d1d5db;
}
.stat-link {
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #b45309;
}
.stat-link:hover {
  text-decoration: underline;
}

.hub-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.ops-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ops-arrow {
  font-size: 16px;
}

.err {
  margin: 0 0 8px;
  color: var(--error, #b91c1c);
  font-size: 12px;
}

.hub-section {
  margin-bottom: 20px;
}
.section-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.section-title.inline {
  display: inline;
  margin-right: 8px;
}

.base-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 900px) {
  .base-grid {
    grid-template-columns: 1fr;
  }
}
.flow-card {
  text-align: left;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: #fff;
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.flow-card:hover {
  border-color: #94a3b8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.flow-ico {
  font-size: 22px;
  color: var(--primary, #1a73e8);
  display: block;
  margin-bottom: 8px;
}
.flow-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 4px;
}
.flow-desc {
  font-size: 12px;
  color: #5b616e;
  line-height: 1.45;
}

.group-bar {
  padding: 12px 14px;
  margin-bottom: 10px;
}
.group-bar-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.group-label {
  font-size: 12px;
  font-weight: 700;
  color: #1f2329;
}
.link-btn {
  border: none;
  background: none;
  color: var(--primary, #1a73e8);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
  margin-left: auto;
}
.group-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.group-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: #fff;
  cursor: pointer;
}
.group-pill.active {
  background: #1f2329;
  color: #fff;
  border-color: #1f2329;
}
.pill-cnt {
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  opacity: 0.85;
}
.group-pill.active .pill-cnt {
  opacity: 1;
}

.context-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 14px;
  margin-bottom: 10px;
  background: #f0f9ff;
  border-color: #bae6fd;
}
.ctx-ico {
  font-size: 20px;
  color: #0369a1;
  flex-shrink: 0;
}
.ctx-text {
  flex: 1;
  margin: 0;
  font-size: 13px;
  color: #0c4a6e;
  line-height: 1.45;
}
.ctx-btn {
  flex-shrink: 0;
}

.filter-ribbon {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 12px;
}
.filter-ribbon-label {
  color: #9aa1ad;
  margin-right: 2px;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  background: #1f2329;
  color: #fff;
  font-weight: 600;
  border: none;
  cursor: pointer;
  font: inherit;
}
.filter-chip:hover {
  background: #3a3f47;
}
.filter-chip .chip-x {
  opacity: 0.75;
  font-weight: 400;
  font-size: 14px;
  line-height: 1;
}
.filter-chip.clear {
  cursor: pointer;
  background: #fff;
  color: #5b616e;
  border: 1px solid var(--outline-variant, #e2e5eb);
}
.filter-chip.clear:hover {
  background: #f5f6f8;
}

.empty-box {
  text-align: center;
  padding: 36px 16px;
}
.empty-title {
  margin: 0 0 8px;
  color: #5b616e;
  font-size: 14px;
  font-weight: 600;
}
.empty-desc {
  margin: 0 0 14px;
  color: #9aa1ad;
  font-size: 12px;
  line-height: 1.55;
  max-width: 520px;
  margin-inline: auto;
}
.empty-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.work-section .view-tabs {
  margin-top: 0;
}

.view-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  margin-bottom: 12px;
  overflow-x: auto;
}
.view-tabs-scroll {
  flex-wrap: nowrap;
}
.view-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: var(--on-surface-variant, #5b616e);
  cursor: pointer;
}
.view-tab:hover {
  color: var(--on-surface, #1f2329);
}
.view-tab.active {
  color: var(--on-surface, #1f2329);
  border-bottom-color: var(--on-surface, #1f2329);
  font-weight: 600;
}
.view-tab .cnt {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: #9aa1ad;
  font-weight: 600;
}
.view-tab.active .cnt {
  color: var(--on-surface-variant, #5b616e);
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #fff;
  border: 1px solid var(--outline-variant, #e2e5eb);
  color: var(--on-surface, #1f2329);
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.combo-search {
  padding: 14px 16px;
  margin-bottom: 12px;
}
.combo-search-head {
  margin-bottom: 0;
}
.combo-search-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2329;
  margin-bottom: 12px;
  display: block;
}
.combo-form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px 12px;
}
@media (max-width: 1000px) {
  .combo-form-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .combo-form-grid {
    grid-template-columns: 1fr;
  }
}
.combo-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.combo-label {
  font-size: 11px;
  color: #9aa1ad;
  font-weight: 600;
}
.combo-inp {
  width: 100%;
  box-sizing: border-box;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  font-size: 13px;
  background: #fff;
}
.combo-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--outline-variant, #e2e5eb);
}
.combo-applied {
  font-size: 12px;
  color: #5b616e;
  margin-left: 4px;
}

.tool-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tool-label {
  font-size: 12px;
  color: #5b616e;
  white-space: nowrap;
}
.tool-sel {
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  font-size: 13px;
  background: #fff;
}

.adv-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.adv-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
}
.adv-label {
  font-size: 11px;
  color: #9aa1ad;
}

.table-wrap {
  overflow-x: auto;
  min-height: 120px;
}
.order-table-wide {
  min-width: 1400px;
}
.order-table-wide th,
.order-table-wide td {
  white-space: nowrap;
  font-size: 12px;
  padding: 8px 10px;
}
.order-no {
  font-weight: 700;
}
.ai-risk-wrap {
  margin-top: 4px;
}
.ai-risk {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
}
.ai-risk.risk-pay {
  background: #ffedd5;
  color: #c2410c;
}
.ai-risk.risk-overdue {
  background: #fee2e2;
  color: #b91c1c;
}
.ai-risk.risk-cancel {
  background: #fef3c7;
  color: #b45309;
}
.stay-type {
  font-size: 11px;
  font-weight: 600;
  color: #5b616e;
}
.sub-cell {
  font-size: 12px;
  color: #5b616e;
}
.table-loading,
.empty {
  text-align: center;
  color: #9aa1ad;
  padding: 40px 16px;
  font-size: 13px;
}
.order-table {
  width: 100%;
}
.guest-name {
  font-weight: 600;
}
.sub {
  color: #9aa1ad;
  font-size: 11px;
  margin-top: 2px;
}
.dates {
  color: #5b616e;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}
.mono {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}
.src-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.src-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  width: fit-content;
}
.src-ota {
  background: #dbeafe;
  color: #1d4ed8;
}
.src-voucher {
  background: #ffedd5;
  color: #c2410c;
}
.src-direct {
  background: #d1fae5;
  color: #047857;
}
.src-group {
  background: #e0e7ff;
  color: #3730a3;
}
.src-map {
  background: #ccfbf1;
  color: #0f766e;
}
.src-geo {
  background: #ede9fe;
  color: #7c3aed;
}
.src-longstay {
  background: #fef3c7;
  color: #b45309;
}
.src-agreement {
  background: #e0f2fe;
  color: #0369a1;
}
.src-wechat {
  background: #ecfdf5;
  color: #059669;
}
.ch-name {
  font-size: 11px;
}
.status-cell {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.row-actions {
  display: flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
}
.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.pager-info {
  font-size: 12px;
  color: #5b616e;
}
.pager-btns {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pager-num {
  font-size: 12px;
  color: #5b616e;
  font-variant-numeric: tabular-nums;
}
</style>
