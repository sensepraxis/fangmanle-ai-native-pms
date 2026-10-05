<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { localizeSeedText } from '../../lib/localizeSeed'

/**
 * 设备设施首页 —— 总览 + 资产清单
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { ASSETS_EMPTY } from '../../lib/assetsEmpty'
import { hotelStore } from '../../store/hotel'
import AssetHealthPanorama from '../../components/AssetHealthPanorama.vue'
import RoomOpsNav from '../../components/RoomOpsNav.vue'

const route = useRoute()
const router = useRouter()
const listRef = ref<HTMLElement | null>(null)

type AssetRow = {
  id: number
  assetNo: string
  name: string
  category: string
  location: string
  health: number
  healthLabel: string
  status: string
  statusLabel: string
}

const board = ref<any>(null)
const assets = ref<AssetRow[]>([])
const search = ref('')
const categoryFilters = ref<string[]>([])
const statusFilters = ref<string[]>([])
const quickFilter = ref<'none' | 'low_health' | 'maint' | 'high_priority'>('none')
const loading = ref(false)
const showRegister = ref(false)
const registering = ref(false)
const registerError = ref('')

const ASSET_CATEGORIES = [
  t('卫浴设备'),
  t('空调暖通'),
  t('客房电器'),
  t('门锁安防'),
  t('电梯机电'),
  t('其他'),
]

function defaultRegForm() {
  return {
    reason: 'new' as 'new' | 'replace' | 'expand',
    category: t('客房电器'),
    assetNo: '',
    name: '',
    spec: '',
    qty: 1,
    budget: '',
    room: '',
    supplier: '',
    note: '',
    replaceAssetId: '' as string | number,
  }
}

const regForm = ref(defaultRegForm())

const STATUS_OPTIONS = [
  { value: 'active', label: t('在用') },
  { value: 'abnormal', label: t('故障') },
  { value: 'maintenance', label: t('维保中') },
  { value: 'retired', label: t('已报废') },
] as const

const QUICK_FILTERS = [
  { key: 'low_health' as const, label: t('低健康分') },
  { key: 'maint' as const, label: t('待维保') },
  { key: 'high_priority' as const, label: t('建议更换') },
]

const categories = computed(() => {
  const set = new Set(assets.value.map((a) => a.category).filter(Boolean))
  return [...set].sort()
})

const highPriorityIds = computed(() => {
  const insights = board.value?.insights || []
  return new Set(
    insights
      .filter((i: any) => i.asset_id && ['replace', 'roi'].includes(i.category))
      .map((i: any) => Number(i.asset_id)),
  )
})

const filteredAssets = computed(() => {
  let list = assets.value
  if (categoryFilters.value.length) {
    list = list.filter((a) => categoryFilters.value.includes(a.category))
  }
  if (statusFilters.value.length) {
    list = list.filter((a) => statusFilters.value.includes(a.status))
  }
  if (quickFilter.value === 'low_health') {
    list = list.filter((a) => a.health < 55 || a.status === 'abnormal')
  } else if (quickFilter.value === 'maint') {
    list = list.filter((a) => a.status === 'maintenance' || a.health < 75)
  } else if (quickFilter.value === 'high_priority') {
    list = list.filter((a) => highPriorityIds.value.has(a.id))
  }
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(
    (a) =>
      a.name.toLowerCase().includes(q) ||
      a.location.toLowerCase().includes(q) ||
      a.assetNo.toLowerCase().includes(q) ||
      a.category.toLowerCase().includes(q) ||
      String(a.id).includes(q),
  )
})

function toggleCategory(cat: string) {
  const i = categoryFilters.value.indexOf(cat)
  if (i >= 0) categoryFilters.value.splice(i, 1)
  else categoryFilters.value.push(cat)
}

function toggleStatus(status: string) {
  const i = statusFilters.value.indexOf(status)
  if (i >= 0) statusFilters.value.splice(i, 1)
  else statusFilters.value.push(status)
}

function toggleQuick(key: typeof quickFilter.value) {
  quickFilter.value = quickFilter.value === key ? 'none' : key
}

function resetFilters() {
  search.value = ''
  categoryFilters.value = []
  statusFilters.value = []
  quickFilter.value = 'none'
}

const hasActiveFilters = computed(
  () =>
    !!search.value.trim() ||
    categoryFilters.value.length > 0 ||
    statusFilters.value.length > 0 ||
    quickFilter.value !== 'none',
)

function roomLabel(a: any) {
  if (a.room_no) return t('{n} 房', { n: a.room_no })
  return a.location ? t(String(a.location)) : '—'
}

function statusLabel(s?: string) {
  if (s === 'active') return t('在用')
  if (s === 'maintenance') return t('维保中')
  if (s === 'retired') return t('已报废')
  if (s === 'abnormal') return t('故障')
  return s || t('在用')
}

function healthPillClass(a: AssetRow) {
  if (a.status === 'abnormal' || a.health < 55) return 'pill-rose'
  if (a.status === 'maintenance' || a.health < 75) return 'pill-amber'
  return 'pill-green'
}

function mapAssets(list: any[]) {
  assets.value = list.map((a: any) => ({
    id: a.id,
    assetNo: a.asset_no || a.sn || `EQ-${String(a.id).padStart(5, '0')}`,
    name: localizeSeedText(a.name || t('设备')),
    category: t(String(a.category || '其他')),
    location: roomLabel(a),
    health: Number(a.health_score || 0),
    healthLabel: a.health_label ? t(String(a.health_label)) : '—',
    status: a.status || 'active',
    statusLabel: statusLabel(a.status),
  }))
}

async function load() {
  loading.value = true
  try {
    const data = await api.assetsBoard(hotelStore.hotelId)
    board.value = data
    mapAssets(data?.assets || [])
  } catch {
    board.value = null
    assets.value = []
  } finally {
    loading.value = false
  }
}

function openProfile(id: number) {
  router.push(`/c8-assets/assets/${id}`)
}

function scrollToList() {
  listRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function syncRegisterQuery(open: boolean) {
  const q: Record<string, any> = { ...route.query }
  if (open) {
    q.action = 'register'
    if (regForm.value.replaceAssetId) q.replace_asset_id = String(regForm.value.replaceAssetId)
    else delete q.replace_asset_id
  } else {
    delete q.action
    delete q.replace_asset_id
  }
  router.replace({ query: q })
}

function prefillReplaceAsset(replaceAssetId: number) {
  const a = (board.value?.assets || []).find((x: any) => Number(x.id) === replaceAssetId)
  if (!a) return
  regForm.value.assetNo = a.asset_no || a.sn || ''
  regForm.value.name = a.name || ''
  regForm.value.room = a.room_no || a.location || ''
  const pv = Number(a.purchase_value || 0)
  regForm.value.budget = pv ? String(Math.round(pv * 0.95)) : ''
  if (/马桶|卫浴|淋浴/.test(a.name || '')) regForm.value.category = t('卫浴设备')
  else if (/空调/.test(a.name || '')) regForm.value.category = t('空调暖通')
}

function openRegister(replaceAssetId?: number) {
  regForm.value = defaultRegForm()
  if (replaceAssetId) {
    regForm.value.reason = 'replace'
    regForm.value.replaceAssetId = replaceAssetId
    prefillReplaceAsset(replaceAssetId)
  }
  showRegister.value = true
  syncRegisterQuery(true)
}

function closeRegister() {
  showRegister.value = false
  registerError.value = ''
  syncRegisterQuery(false)
}

async function submitRegister() {
  const name = regForm.value.name.trim()
  if (!name) return
  registering.value = true
  registerError.value = ''
  try {
    await api.registerAsset(hotelStore.hotelId, {
      reason: regForm.value.reason,
      category: regForm.value.category,
      asset_no: regForm.value.assetNo.trim() || undefined,
      name,
      spec: regForm.value.spec.trim() || undefined,
      qty: regForm.value.qty,
      budget: regForm.value.budget.trim() || undefined,
      room: regForm.value.room.trim() || undefined,
      supplier: regForm.value.supplier.trim() || undefined,
      note: regForm.value.note.trim() || undefined,
      replace_asset_id: regForm.value.replaceAssetId
        ? Number(regForm.value.replaceAssetId)
        : undefined,
    })
    await load()
    showRegister.value = false
    syncRegisterQuery(false)
    scrollToList()
  } catch (e: any) {
    registerError.value = e?.message || t('登记失败，请稍后重试')
  } finally {
    registering.value = false
  }
}

onMounted(async () => {
  await load()
  if (route.query.action === 'register') {
    const rid = Number(route.query.replace_asset_id || 0)
    openRegister(rid > 0 ? rid : undefined)
  }
})
watch(
  () => hotelStore.hotelId,
  () => {
    closeRegister()
    load()
  },
)
watch(
  () => route.query.action,
  (action) => {
    if (action === 'register' && !showRegister.value) {
      const rid = Number(route.query.replace_asset_id || 0)
      openRegister(rid > 0 ? rid : undefined)
    } else if (action !== 'register') {
      showRegister.value = false
    }
  },
)
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <div class="page-head">
      <div>
        <h1>{{ t('设备设施总览') }}</h1>
      </div>
      <div class="head-actions">
        <button type="button" class="btn btn-ghost">{{ t('导出报告') }}</button>
      </div>
    </div>

    <AssetHealthPanorama
      :board="board"
      @scroll-to-list="scrollToList"
      @register-asset="openRegister()"
    />

    <!-- 资产清单 -->
    <section ref="listRef" class="list-section">
      <div class="list-head">
        <div>
          <h2>{{ t('资产清单') }}</h2>
          <p class="sub">
            {{ loading ? t('加载中…') : `共 ${assets.length} 项在册资产` }}
            <span v-if="filteredAssets.length !== assets.length || hasActiveFilters">
              · {{ t('筛选显示') }} {{ filteredAssets.length }} {{ t('项') }}
            </span>
          </p>
        </div>
        <button type="button" class="btn btn-primary" @click="openRegister()">
          <span class="material-symbols-outlined">add</span>
          {{ t('登记新资产') }}
        </button>
      </div>

      <!-- 登记新资产（清单区上方展开） -->
      <div v-if="showRegister" class="register-panel card-clean">
        <div class="register-head">
          <h2>{{ t('登记新资产') }}</h2>
          <button class="btn btn-ghost" type="button" @click="closeRegister">
            {{ t('关闭') }}
          </button>
        </div>
        <fieldset class="register-type">
          <legend>{{ t('申请类型') }}</legend>
          <label class="radio">
            <input v-model="regForm.reason" type="radio" value="new" />
            {{ t('新店 / 新增') }}</label
          >
          <label class="radio">
            <input v-model="regForm.reason" type="radio" value="replace" />
            {{ t('更换旧设备') }}</label
          >
          <label class="radio">
            <input v-model="regForm.reason" type="radio" value="expand" />
            {{ t('扩容增购') }}</label
          >
        </fieldset>
        <div class="register-grid">
          <label>
            {{ t('品类') }}
            <select v-model="regForm.category" class="field-input">
              <option v-for="c in ASSET_CATEGORIES" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>
          <label>
            {{ t('设备编号') }}
            <input
              v-model="regForm.assetNo"
              class="field-input"
              type="text"
              :placeholder="t('留空由系统分配')"
            />
          </label>
          <label class="span-2">
            {{ t('设备名称') }}
            <input
              v-model="regForm.name"
              class="field-input"
              type="text"
              :placeholder="t('如：TOTO 智能马桶')"
              required
            />
          </label>
          <label>
            {{ t('规格 / 型号') }}
            <input
              v-model="regForm.spec"
              class="field-input"
              type="text"
              :placeholder="t('型号、尺寸等')"
            />
          </label>
          <label>
            {{ t('数量') }}
            <input v-model.number="regForm.qty" class="field-input" type="number" min="1" />
          </label>
          <label>
            {{ t('预算（元）') }}
            <input
              v-model="regForm.budget"
              class="field-input"
              type="text"
              :placeholder="t('AI 参考：同类均价 ±15%')"
            />
          </label>
          <label>
            {{ t('安装位置 / 房号') }}
            <input
              v-model="regForm.room"
              class="field-input"
              type="text"
              :placeholder="t('305 / 2F 机房')"
            />
          </label>
          <label>
            {{ t('建议供应商') }}
            <input
              v-model="regForm.supplier"
              class="field-input"
              type="text"
              :placeholder="t('输入供应商名称')"
            />
          </label>
          <label class="span-2">
            {{ t('备注') }}
            <input
              v-model="regForm.note"
              class="field-input"
              type="text"
              :placeholder="t('更换原因、工期要求…')"
            />
          </label>
        </div>
        <div class="register-foot">
          <p v-if="registerError" class="register-error">{{ registerError }}</p>
          <button class="btn btn-ghost" type="button" @click="closeRegister">
            {{ t('取消') }}
          </button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="registering || !regForm.name.trim()"
            @click="submitRegister"
          >
            {{ registering ? t('提交中…') : t('提交登记') }}
          </button>
        </div>
      </div>

      <div class="list-body">
        <!-- 组合筛选侧栏（对齐客户资源全景） -->
        <aside class="filter-aside">
          <div class="filter-head">
            <h3>{{ t('筛选条件') }}</h3>
            <button type="button" class="filter-reset" @click="resetFilters">
              {{ t('重置') }}
            </button>
          </div>
          <div class="filter-body">
            <div class="filter-search">
              <span class="material-symbols-outlined">search</span>
              <input v-model="search" type="search" :placeholder="t('搜索筛选……')" />
            </div>

            <div class="filter-block">
              <h4>{{ t('品类') }}</h4>
              <div class="filter-checks">
                <label v-for="c in categories" :key="c" class="filter-check">
                  <input
                    type="checkbox"
                    :checked="categoryFilters.includes(c)"
                    @change="toggleCategory(c)"
                  />
                  <span>{{ c }}</span>
                </label>
                <p v-if="!categories.length" class="filter-empty">{{ t('暂无品类') }}</p>
              </div>
            </div>

            <hr class="filter-divider" />

            <div class="filter-block">
              <h4>{{ t('状态') }}</h4>
              <div class="filter-checks">
                <label v-for="s in STATUS_OPTIONS" :key="s.value" class="filter-check">
                  <input
                    type="checkbox"
                    :checked="statusFilters.includes(s.value)"
                    @change="toggleStatus(s.value)"
                  />
                  <span>{{ s.label }}</span>
                </label>
              </div>
            </div>

            <hr class="filter-divider" />

            <div class="filter-block">
              <h4>{{ t('快捷筛选') }}</h4>
              <div class="filter-chips">
                <button
                  v-for="f in QUICK_FILTERS"
                  :key="f.key"
                  type="button"
                  class="filter-chip"
                  :class="{
                    active: quickFilter === f.key,
                    warn: f.key === 'low_health',
                    hi: f.key === 'high_priority',
                  }"
                  @click="toggleQuick(f.key)"
                >
                  {{ f.label }}
                </button>
              </div>
            </div>
          </div>
        </aside>

        <div class="card-clean list-card">
          <div class="list-toolbar">
            <div class="toolbar-search">
              <span class="material-symbols-outlined">search</span>
              <input
                v-model="search"
                type="search"
                :placeholder="t('按编号、名称、位置或品类搜索……')"
              />
            </div>
            <div class="toolbar-meta">
              {{
                loading
                  ? t('加载中…')
                  : `显示 ${assets.length} 项资产中的 ${filteredAssets.length} 项`
              }}
            </div>
          </div>

          <div class="table-wrap">
            <table class="data">
              <thead>
                <tr>
                  <th>{{ t('设备编号') }}</th>
                  <th>{{ t('设备名称') }}</th>
                  <th>{{ t('品类') }}</th>
                  <th>{{ t('位置') }}</th>
                  <th>{{ t('健康分') }}</th>
                  <th>{{ t('状态') }}</th>
                  <th class="center">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredAssets.length">
                  <td colspan="7" class="empty-hint center">
                    {{ loading ? t('加载中…') : ASSETS_EMPTY }}
                  </td>
                </tr>
                <tr
                  v-for="a in filteredAssets"
                  :key="a.id"
                  class="clickable"
                  @click="openProfile(a.id)"
                >
                  <td class="num">{{ a.assetNo }}</td>
                  <td>
                    <div class="name-cell">
                      <span class="avatar">{{ (a.name || t('设'))[0] }}</span>
                      <strong>{{ a.name }}</strong>
                    </div>
                  </td>
                  <td>{{ a.category }}</td>
                  <td>{{ a.location }}</td>
                  <td>
                    <span
                      class="font-num-md"
                      :class="a.health < 55 ? 'text-error' : a.health < 75 ? 'text-warn' : ''"
                      >{{ a.health || '—' }}</span
                    >
                  </td>
                  <td>
                    <span class="pill" :class="healthPillClass(a)">{{ a.statusLabel }}</span>
                  </td>
                  <td class="center" @click.stop>
                    <button type="button" class="act-btn" @click="openProfile(a.id)">
                      {{ t('资产画像') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.page-head h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  line-height: 40px;
  font-family: 'Source Sans 3', system-ui, sans-serif;
  color: var(--on-surface);
}
.sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.list-section {
  scroll-margin-top: 72px;
}
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px;
}
.list-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
}
.list-head .btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.list-head .btn .material-symbols-outlined {
  font-size: 18px;
}
.list-body {
  display: flex;
  gap: 16px;
  align-items: stretch;
  min-height: 360px;
}
@media (max-width: 960px) {
  .list-body {
    flex-direction: column;
  }
}
.filter-aside {
  width: 256px;
  flex-shrink: 0;
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (max-width: 960px) {
  .filter-aside {
    width: 100%;
  }
}
.filter-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  position: sticky;
  top: 0;
  z-index: 1;
}
.filter-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--on-surface);
}
.filter-reset {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.filter-reset:hover {
  text-decoration: underline;
}
.filter-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}
.filter-search {
  position: relative;
}
.filter-search .material-symbols-outlined {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--on-surface-variant);
  pointer-events: none;
}
.filter-search input {
  width: 100%;
  padding: 8px 12px 8px 40px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: var(--surface-container-low);
  font-size: 13px;
  outline: none;
}
.filter-search input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}
.filter-block h4 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
}
.filter-checks {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-check {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.filter-check:hover span {
  color: var(--on-surface);
}
.filter-check input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
  cursor: pointer;
}
.filter-empty {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.filter-divider {
  border: none;
  border-top: 1px solid var(--outline-variant);
  margin: 0;
}
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-chip {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-high);
  font-size: 12px;
  color: var(--on-surface-variant);
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s;
}
.filter-chip:hover {
  background: var(--surface-variant);
}
.filter-chip.active {
  background: var(--primary-container);
  color: var(--on-primary-container);
  border-color: var(--primary-container);
}
.filter-chip.warn.active {
  background: var(--error-container);
  color: var(--on-error-container);
  border-color: var(--error-container);
}
.filter-chip.hi.active {
  background: #fef3c7;
  color: #92400e;
  border-color: #fcd34d;
}
.list-card {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.list-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  flex-wrap: wrap;
}
.toolbar-search {
  position: relative;
  flex: 1;
  min-width: 220px;
  max-width: 360px;
}
.toolbar-search .material-symbols-outlined {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--on-surface-variant);
  pointer-events: none;
}
.toolbar-search input {
  width: 100%;
  padding: 8px 12px 8px 40px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: var(--surface-container-low);
  font-size: 13px;
  outline: none;
}
.toolbar-search input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}
.toolbar-meta {
  font-size: 13px;
  color: var(--on-surface-variant);
  white-space: nowrap;
}
.table-wrap {
  overflow-x: auto;
}
.name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.act-btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
}
.act-btn:hover {
  background: var(--primary-container);
}
.center {
  text-align: center;
}
.empty-hint.center {
  padding: 32px 16px;
}
.text-error {
  color: var(--error);
  font-weight: 600;
}
.text-warn {
  color: #f57f17;
}
.register-panel {
  margin-bottom: 16px;
  padding: 20px;
  border: 1px solid var(--outline-variant);
}
.register-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.register-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--on-surface);
}
.register-type {
  border: none;
  margin: 0 0 16px;
  padding: 0;
}
.register-type legend {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--on-surface-variant);
}
.radio {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: 20px;
  font-size: 13px;
  color: var(--on-surface);
}
.register-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 12px;
}
.register-grid label {
  grid-column: span 6;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.register-grid .span-2 {
  grid-column: span 12;
}
.field-input {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  color: var(--on-surface);
  font-size: 13px;
  font-family: inherit;
}
.register-foot {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.register-error {
  flex: 1;
  margin: 0;
  font-size: 12px;
  color: var(--error);
  text-align: left;
}
@media (max-width: 720px) {
  .register-grid label {
    grid-column: span 12;
  }
}
</style>
