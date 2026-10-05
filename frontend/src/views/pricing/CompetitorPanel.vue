<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 竞品对比面板：折叠摘要 + 编辑态三步卡片
 * 1 地图圈选 · 2 手工补充 · 3 按入住日录价（列=本店房型）
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt, toast } from '../../lib/ui'
import { channelLabel, sourceLabel } from './labels'
import CompetitorMapPicker from './CompetitorMapPicker.vue'

const props = defineProps<{ config: any }>()
const emit = defineEmits<{
  (e: 'config-change', cfg: any): void
  (e: 'changed'): void
}>()

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function shiftDate(iso: string, days: number) {
  const d = new Date(iso + 'T12:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const collapsed = ref(false)
const editing = ref(false)
const sets = ref<any[]>([])
const hotelRoomTypes = ref<{ id: number; name: string }[]>([])
const busyAdd = ref(false)
const busySaveRate = ref(false)

const stepOpen = ref({ 1: true, 2: false, 3: false })

const addForm = ref({
  comp_name: '',
  address: '',
  distance_km: '' as string | number,
  ota_public_url: '',
})

const stayDate = ref(todayIso())
const rateChannel = ref('ota_ctrip')
/** 界面编辑值 */
const rateDraft = ref<Record<string, string>>({})
/** 已落库值（用于着色：绿=已入库且未改） */
const rateSaved = ref<Record<string, string>>({})
const savingKey = ref('')

const importOpen = ref(false)
const importText = ref('')

const propsList = computed(() => sets.value.flatMap((s) => s.properties || []))
const compOn = computed(() => !!props.config?.comp_compare_enabled)

const roomTypeCols = computed(() => {
  return hotelRoomTypes.value.map((r) => ({ id: r.id, name: r.name }))
})

function syncStepDefaults() {
  if (!propsList.value.length) {
    stepOpen.value = { 1: true, 2: true, 3: false }
  } else {
    stepOpen.value = { 1: false, 2: false, 3: true }
  }
}

async function load() {
  const hid = hotelStore.hotelId
  const [setsRes, rts] = await Promise.all([
    api.paCompetitorSets(hid),
    api.listRoomTypes(hid).catch(() => []),
  ])
  sets.value = setsRes
  hotelRoomTypes.value = (rts || [])
    .map((r: any) => ({ id: Number(r.id ?? r.room_type_id), name: String(r.name || '') }))
    .filter((r: { id: number; name: string }) => r.id && r.name)
  if (editing.value) await loadDayRates(false)
}

/** preserveUnsaved=true：只刷新已入库标记，保留用户尚未点「存」的草稿 */
async function loadDayRates(preserveUnsaved = false) {
  if (!stayDate.value) return
  try {
    const rows =
      (await api.paListCompetitorRates(hotelStore.hotelId, stayDate.value, rateChannel.value)) || []
    const nextSaved: Record<string, string> = {}
    for (const p of propsList.value) {
      for (const rt of roomTypeCols.value) {
        const hit =
          rows.find(
            (r: any) => r.comp_id === p.comp_id && String(r.room_type_eq || '') === rt.name,
          ) || rows.find((r: any) => r.comp_id === p.comp_id && !r.room_type_eq)
        const key = rateKey(p.comp_id, rt.name)
        nextSaved[key] =
          hit?.observed_price != null && hit?.observed_price !== ''
            ? String(hit.observed_price)
            : ''
      }
    }
    if (!preserveUnsaved) {
      rateSaved.value = nextSaved
      rateDraft.value = { ...nextSaved }
      return
    }
    const prevSaved = rateSaved.value
    const nextDraft = { ...rateDraft.value }
    for (const key of Object.keys(nextSaved)) {
      const draft = nextDraft[key]
      const oldSaved = prevSaved[key] || ''
      const dirty = draft !== undefined && draft !== '' && draft !== oldSaved
      if (!dirty) nextDraft[key] = nextSaved[key]
    }
    rateSaved.value = nextSaved
    rateDraft.value = nextDraft
  } catch {
    if (!preserveUnsaved) {
      rateSaved.value = {}
      rateDraft.value = {}
    }
  }
}

async function onMapAdded() {
  await load()
  emit('changed')
  syncStepDefaults()
}

onMounted(async () => {
  await load()
})
watch(() => hotelStore.hotelId, load)
watch(editing, async (v) => {
  if (v) {
    syncStepDefaults()
    await loadDayRates(false)
  }
})
watch([stayDate, rateChannel], () => {
  if (editing.value) loadDayRates(false)
})
watch(propsList, () => {
  if (editing.value) loadDayRates(true)
})

function toggleStep(n: 1 | 2 | 3) {
  stepOpen.value = { ...stepOpen.value, [n]: !stepOpen.value[n] }
}

async function toggleComp(on: boolean) {
  try {
    const cfg = await api.paUpdateConfig(hotelStore.hotelId, { comp_compare_enabled: on })
    emit('config-change', cfg)
    try {
      await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
      toast(on ? t('已开启竞品对比 · 建议已重算') : t('已关闭竞品对比 · 建议已重算'))
    } catch {
      toast(on ? t('已开启竞品对比') : t('已关闭竞品对比 · 仅本店信号'))
    }
    emit('changed')
  } catch (e: any) {
    toast(e?.message || t('切换失败'), false)
  }
}

async function addCompetitor() {
  const name = String(addForm.value.comp_name || '').trim()
  if (!name) {
    toast(t('请填写竞品酒店名称'), false)
    return
  }
  busyAdd.value = true
  try {
    const dist = addForm.value.distance_km
    await api.paAddCompetitor(hotelStore.hotelId, {
      comp_name: name,
      address: String(addForm.value.address || '').trim() || undefined,
      distance_km: dist === '' || dist == null ? undefined : Number(dist),
      ota_public_url: String(addForm.value.ota_public_url || '').trim() || undefined,
      data_source: 'manual',
      source_ref: 'manager',
      set_name: t('默认竞品集'),
    })
    toast(t('已加入竞品「{name}」', { name }))
    addForm.value = { comp_name: '', address: '', distance_km: '', ota_public_url: '' }
    await load()
    emit('changed')
    stepOpen.value = { ...stepOpen.value, 3: true }
  } catch (e: any) {
    toast(e?.message || t('添加失败'), false)
  } finally {
    busyAdd.value = false
  }
}

async function removeComp(compId: string) {
  try {
    await api.paDeactivateCompetitor(hotelStore.hotelId, compId)
    try {
      await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
      toast(t('已移除竞品并重算建议'))
    } catch {
      toast(t('已移除竞品（建议重算失败，请手动重新生成）'))
    }
    await load()
    emit('changed')
  } catch (e: any) {
    toast(e?.message || t('移除失败'), false)
  }
}

function rateKey(compId: string, roomName: string) {
  return `${compId}::${roomName}`
}

function cellState(compId: string, roomName: string): 'saved' | 'dirty' | 'empty' {
  const key = rateKey(compId, roomName)
  const draft = String(rateDraft.value[key] ?? '').trim()
  const saved = String(rateSaved.value[key] ?? '').trim()
  if (!draft) return 'empty'
  if (saved && draft === saved) return 'saved'
  return 'dirty'
}

async function saveCellRate(compId: string, roomName: string) {
  const key = rateKey(compId, roomName)
  const raw = rateDraft.value[key]
  if (raw === '' || raw == null) {
    toast(t('请填写公开客人支付价'), false)
    return
  }
  savingKey.value = key
  try {
    const price = Number(raw)
    await api.paCompetitorRate(hotelStore.hotelId, {
      comp_id: compId,
      stay_date: stayDate.value,
      channel: rateChannel.value,
      room_type_eq: roomName,
      observed_price: price,
      data_source: 'manual',
    })
    const val = String(price)
    rateSaved.value = { ...rateSaved.value, [key]: val }
    rateDraft.value = { ...rateDraft.value, [key]: val }
    try {
      await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
      toast(t('已保存并重算建议 · {date}', { date: stayDate.value }))
    } catch {
      toast(t('已保存价格，但建议重算失败，请点「重新生成建议」'), false)
    }
    emit('changed')
  } catch (e: any) {
    toast(e?.message || t('录入失败'), false)
  } finally {
    savingKey.value = ''
  }
}

async function saveAllDraftRates() {
  const jobs: { key: string; compId: string; roomName: string; price: number }[] = []
  for (const p of propsList.value) {
    for (const rt of roomTypeCols.value) {
      const key = rateKey(p.comp_id, rt.name)
      const raw = rateDraft.value[key]
      if (raw === '' || raw == null) continue
      jobs.push({ key, compId: p.comp_id, roomName: rt.name, price: Number(raw) })
    }
  }
  if (!jobs.length) {
    toast(t('没有可保存的价格'), false)
    return
  }
  busySaveRate.value = true
  try {
    await Promise.all(
      jobs.map((j) =>
        api.paCompetitorRate(hotelStore.hotelId, {
          comp_id: j.compId,
          stay_date: stayDate.value,
          channel: rateChannel.value,
          room_type_eq: j.roomName,
          observed_price: j.price,
          data_source: 'manual',
        }),
      ),
    )
    const nextSaved = { ...rateSaved.value }
    const nextDraft = { ...rateDraft.value }
    for (const j of jobs) {
      const val = String(j.price)
      nextSaved[j.key] = val
      nextDraft[j.key] = val
    }
    rateSaved.value = nextSaved
    rateDraft.value = nextDraft
    try {
      await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
      toast(t('已保存 {n} 条并重算建议 · {date}', { n: jobs.length, date: stayDate.value }))
    } catch {
      toast(
        t('已保存 {n} 条 · {date}（建议重算失败，请手动重新生成）', {
          n: jobs.length,
          date: stayDate.value,
        }),
      )
    }
    emit('changed')
  } catch (e: any) {
    toast(e?.message || t('批量保存失败'), false)
  } finally {
    busySaveRate.value = false
  }
}

function setStayQuick(kind: 'today' | 'tomorrow' | 'week') {
  if (kind === 'today') stayDate.value = todayIso()
  else if (kind === 'tomorrow') stayDate.value = shiftDate(todayIso(), 1)
  else stayDate.value = shiftDate(todayIso(), 7)
}

function downloadTemplate() {
  const cid = propsList.value[0]?.comp_id || 'cp_xxx'
  const sample =
    'comp_id,stay_date,observed_price,channel,room_type_eq\n' +
    `${cid},${stayDate.value},428,ota_ctrip,大床房\n`
  const blob = new Blob([sample], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'competitor_rates_template.csv'
  a.click()
}

async function doImport() {
  if (!importText.value.trim()) {
    toast(t('请粘贴 CSV 内容'), false)
    return
  }
  try {
    const r = await api.paImportCompetitorRates(hotelStore.hotelId, importText.value)
    toast(t('导入 {n} 条并已重算建议', { n: r.imported ?? 0 }))
    importText.value = ''
    importOpen.value = false
    await load()
    await loadDayRates(false)
    emit('changed')
  } catch (e: any) {
    toast(e?.message || t('导入失败'), false)
  }
}
</script>

<template>
  <div class="comp-panel card-clean" :class="{ collapsed, off: !compOn, editing }">
    <div class="comp-head">
      <button
        type="button"
        class="chev"
        @click="collapsed = !collapsed"
        :aria-expanded="!collapsed"
      >
        {{ collapsed ? '▸' : '▾' }}
      </button>
      <div class="comp-title">
        <span class="material-symbols-outlined">travel_explore</span>
        {{ t('竞品对比') }}
        <span class="comp-state">{{ compOn ? t('已开启') : t('未开启') }}</span>
        <span class="count">{{ propsList.length }} {{ t('家') }}</span>
      </div>
      <div class="comp-actions">
        <label class="switch" :title="t('开启竞品对比')">
          <input
            type="checkbox"
            :checked="compOn"
            @change="toggleComp(($event.target as HTMLInputElement).checked)"
          />
          <span class="slider" />
        </label>
        <button type="button" class="btn btn-ghost sm" @click="editing = !editing">
          {{ editing ? t('完成') : t('编辑') }}
        </button>
      </div>
    </div>

    <div v-if="!compOn && !collapsed" class="comp-hint">
      {{ t('竞品对比未开启：定价建议仅基于') }} <b>{{ t('本店房态 / 库存 / 销售') }}</b
      >{{ t('信号。开启后可获得竞品对标与穿透分析。') }}
    </div>

    <div v-if="compOn && !collapsed && !editing" class="comp-body">
      <span v-for="p in propsList" :key="p.comp_id" class="comp-chip" :title="p.address || ''">
        {{ p.comp_name }}
        <span v-if="p.latest_price" class="px">{{ fmt(p.latest_price) }}</span>
        <button type="button" class="rm" :title="t('移除')" @click="removeComp(p.comp_id)">
          ×
        </button>
      </span>
      <span v-if="!propsList.length" class="empty-hint">{{
        t('尚未配置竞品 · 点「编辑」按步骤维护')
      }}</span>
    </div>

    <div v-if="editing && !collapsed" class="comp-edit">
      <!-- 步骤 1 -->
      <section class="step-card" :class="{ open: stepOpen[1] }">
        <button type="button" class="step-head" @click="toggleStep(1)">
          <span class="step-no">1</span>
          <span class="step-ttl">{{ t('地图圈选竞品') }}</span>
          <span class="step-sub">{{ t('本店锚点 · 3/5 公里周边勾选加入') }}</span>
          <span class="step-chev">{{ stepOpen[1] ? '▾' : '▸' }}</span>
        </button>
        <div v-if="stepOpen[1]" class="step-body">
          <CompetitorMapPicker
            :config="config"
            :selected-competitors="propsList"
            @config-change="(cfg) => emit('config-change', cfg)"
            @added="onMapAdded"
          />
        </div>
      </section>

      <!-- 步骤 2 -->
      <section class="step-card" :class="{ open: stepOpen[2] }">
        <button type="button" class="step-head" @click="toggleStep(2)">
          <span class="step-no">2</span>
          <span class="step-ttl">{{ t('手工补充录入竞品') }}</span>
          <span class="step-sub">{{ t('地图搜不到时手动加入对标名单') }}</span>
          <span class="step-chev">{{ stepOpen[2] ? '▾' : '▸' }}</span>
        </button>
        <div v-if="stepOpen[2]" class="step-body">
          <p class="hint">
            {{
              t('填写名称即可加入；地址 / 距离 / OTA 链接可选。价格请在步骤 3 按入住日录入（口径为')
            }}
            <b>{{ t('OTA 公开展示客付价') }}</b
            >）。
          </p>
          <div class="add-grid">
            <input v-model="addForm.comp_name" :placeholder="t('竞品酒店名称 *')" class="grow" />
            <input v-model="addForm.address" :placeholder="t('地址（可选）')" class="grow" />
            <input
              v-model="addForm.distance_km"
              type="number"
              step="0.1"
              min="0"
              :placeholder="t('约几公里')"
              class="narrow"
            />
            <input
              v-model="addForm.ota_public_url"
              :placeholder="t('OTA 公开链接（可选）')"
              class="grow"
            />
            <button
              type="button"
              class="btn btn-primary sm"
              :disabled="busyAdd"
              @click="addCompetitor"
            >
              {{ busyAdd ? t('添加中…') : t('加入竞品集') }}
            </button>
          </div>
          <div v-if="propsList.length" class="picked">
            <div class="picked-h">{{ t('当前竞品集（') }}{{ propsList.length }}）</div>
            <div v-for="p in propsList" :key="p.comp_id" class="row">
              <span class="nm">
                {{ p.comp_name }}
                <a
                  v-if="p.ota_public_url"
                  class="ota"
                  :href="p.ota_public_url"
                  target="_blank"
                  rel="noopener"
                  >OTA</a
                >
              </span>
              <span class="tag">
                {{ sourceLabel(p.data_source) }}
                <template v-if="Number(p.distance_km) > 0">
                  · {{ t('约 {n} 公里', { n: p.distance_km }) }}</template
                >
              </span>
              <button type="button" class="del" @click="removeComp(p.comp_id)">
                {{ t('移除') }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 步骤 3 -->
      <section class="step-card" :class="{ open: stepOpen[3] }">
        <button type="button" class="step-head" @click="toggleStep(3)">
          <span class="step-no">3</span>
          <span class="step-ttl">{{ t('竞品房型与价格录入') }}</span>
          <span class="step-sub">{{ t('先选入住日，再按本店房型列录入公开客付价') }}</span>
          <span class="step-chev">{{ stepOpen[3] ? '▾' : '▸' }}</span>
        </button>
        <div v-if="stepOpen[3]" class="step-body">
          <div v-if="!propsList.length" class="empty-hint">
            {{ t('请先在步骤 1 / 2 加入竞品') }}
          </div>
          <template v-else>
            <div class="date-bar">
              <label class="date-lbl"
                >{{ t('入住日') }}<input v-model="stayDate" type="date" class="date-input" />
              </label>
              <button type="button" class="chip-btn" @click="setStayQuick('today')">
                {{ t('今天') }}
              </button>
              <button type="button" class="chip-btn" @click="setStayQuick('tomorrow')">
                {{ t('明天') }}
              </button>
              <button type="button" class="chip-btn" @click="setStayQuick('week')">
                {{ t('+7 天') }}
              </button>
              <label class="date-lbl ch"
                >{{ t('渠道')
                }}<select v-model="rateChannel">
                  <option value="ota_ctrip">{{ channelLabel('ota_ctrip') }}</option>
                  <option value="ota_meituan">{{ channelLabel('ota_meituan') }}</option>
                  <option value="ota_booking">{{ channelLabel('ota_booking') }}</option>
                  <option value="direct">{{ channelLabel('direct') }}</option>
                </select>
              </label>
              <button
                type="button"
                class="btn btn-primary sm"
                :disabled="busySaveRate"
                @click="saveAllDraftRates"
              >
                {{ t('保存本日全部价格') }}
              </button>
            </div>

            <div class="sub-block">
              <div class="sub-ttl">
                {{ stayDate }} · {{ channelLabel(rateChannel) }} · {{ t('公开客付价') }}
                <span class="legend-mini">
                  <i class="swatch saved" />{{ t('已入库') }} <i class="swatch dirty" />{{
                    t('未保存')
                  }}</span
                >
              </div>
              <div v-if="!roomTypeCols.length" class="empty-hint">
                {{ t('暂无本店房型列，无法录价网格') }}
              </div>
              <div v-else class="table-wrap">
                <table class="rtable">
                  <thead>
                    <tr>
                      <th>{{ t('竞品') }}</th>
                      <th v-for="rt in roomTypeCols" :key="'h-' + rt.id" class="rt">
                        {{ rt.name }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in propsList" :key="'r-' + p.comp_id">
                      <td class="left">{{ p.comp_name }}</td>
                      <td v-for="rt in roomTypeCols" :key="rt.id" class="cell">
                        <div class="cell-in" :class="cellState(p.comp_id, rt.name)">
                          <input
                            v-model="rateDraft[rateKey(p.comp_id, rt.name)]"
                            type="number"
                            min="0"
                            step="1"
                            placeholder="¥"
                          />
                          <button
                            type="button"
                            class="link"
                            :disabled="
                              savingKey === rateKey(p.comp_id, rt.name) ||
                              busySaveRate ||
                              cellState(p.comp_id, rt.name) === 'empty' ||
                              cellState(p.comp_id, rt.name) === 'saved'
                            "
                            @click="saveCellRate(p.comp_id, rt.name)"
                          >
                            {{
                              savingKey === rateKey(p.comp_id, rt.name)
                                ? '…'
                                : cellState(p.comp_id, rt.name) === 'saved'
                                  ? t('已存')
                                  : t('存')
                            }}
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="import-bar">
              <button type="button" class="link" @click="importOpen = !importOpen">
                {{ importOpen ? t('收起 CSV') : t('批量导入 CSV') }}
              </button>
              <button type="button" class="link" @click="downloadTemplate">
                {{ t('下载模板') }}
              </button>
            </div>
            <div v-if="importOpen" class="import-box">
              <textarea
                v-model="importText"
                rows="4"
                :placeholder="t('粘贴 CSV：comp_id,stay_date,observed_price,channel,room_type_eq')"
              />
              <button type="button" class="btn btn-primary sm" @click="doImport">
                {{ t('导入') }}
              </button>
            </div>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.comp-panel {
  margin-bottom: 4px;
  padding: 0;
  overflow: hidden;
}
.comp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}
.chev {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--on-surface-variant);
  width: 20px;
}
.comp-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 650;
  font-size: 14px;
}
.comp-title .material-symbols-outlined {
  font-size: 20px;
  color: var(--primary);
}
.comp-state {
  font-size: 12px;
  font-weight: 500;
  color: #16a34a;
}
.off .comp-state {
  color: #9ca3af;
}
.count {
  font-size: 12px;
  color: var(--on-surface-variant);
  font-weight: 500;
}
.comp-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  background: #cbd5e1;
  border-radius: 20px;
  cursor: pointer;
  transition: 0.2s;
}
.slider:before {
  content: '';
  position: absolute;
  height: 14px;
  width: 14px;
  left: 3px;
  top: 3px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}
.switch input:checked + .slider {
  background: var(--primary);
}
.switch input:checked + .slider:before {
  transform: translateX(20px);
}
.btn.sm {
  padding: 5px 10px;
  font-size: 12px;
}
.comp-hint {
  padding: 0 14px 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.comp-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 14px 12px;
  align-items: center;
}
.comp-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 20px;
  font-size: 12px;
}
.comp-chip .px {
  font-weight: 600;
  color: var(--primary);
}
.comp-chip .rm {
  border: none;
  background: transparent;
  color: #dc2626;
  cursor: pointer;
  font-weight: 700;
  padding: 0 2px;
}
.empty-hint {
  font-size: 12px;
  color: var(--on-surface-variant);
  padding: 4px 0;
}
.comp-edit {
  padding: 10px 14px 14px;
  border-top: 1px dashed #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.step-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}
.step-card.open {
  border-color: #c7d2fe;
  box-shadow: 0 1px 0 rgba(37, 99, 235, 0.06);
}
.step-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
}
.step-card.open .step-head {
  background: #eef2ff;
}
.step-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-ttl {
  font-size: 13px;
  font-weight: 650;
  color: #0f172a;
}
.step-sub {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-left: 4px;
  flex: 1;
}
.step-chev {
  color: var(--on-surface-variant);
  font-size: 12px;
}
.step-body {
  padding: 12px;
  border-top: 1px solid #edf1f6;
}
.hint {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin: 0 0 8px;
  line-height: 1.5;
}
.add-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}
.add-grid input {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  min-width: 0;
}
.add-grid .grow {
  flex: 1 1 140px;
}
.add-grid .narrow {
  flex: 0 0 110px;
}
.picked-h {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  font-size: 12px;
  border-bottom: 1px solid #edf1f6;
}
.row .nm {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}
.row .ota {
  font-size: 11px;
  color: var(--primary);
  text-decoration: none;
}
.tag {
  font-size: 11px;
  color: var(--on-surface-variant);
  background: #f3f4f6;
  padding: 2px 7px;
  border-radius: 4px;
}
.del,
.link {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 5px;
  font-size: 11px;
  padding: 3px 8px;
  cursor: pointer;
}
.del {
  color: #dc2626;
}
.date-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  padding: 10px;
  background: #eff6ff;
  border-radius: 8px;
  border: 1px solid #bfdbfe;
}
.date-lbl {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 650;
  color: #1e3a8a;
}
.date-lbl.ch {
  font-weight: 500;
}
.date-input,
.date-lbl select {
  border: 1px solid #93c5fd;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 12px;
  background: #fff;
}
.chip-btn {
  border: 1px solid #bfdbfe;
  background: #fff;
  border-radius: 14px;
  padding: 4px 10px;
  font-size: 11px;
  cursor: pointer;
  color: #1d4ed8;
}
.chip-btn:hover {
  background: #dbeafe;
}
.sub-block {
  margin-top: 12px;
}
.sub-ttl {
  font-size: 12px;
  font-weight: 650;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.legend-mini {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--on-surface-variant);
}
.legend-mini .swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid #e5e7eb;
}
.legend-mini .swatch.saved {
  background: #d1fae5;
  border-color: #6ee7b7;
}
.legend-mini .swatch.dirty {
  background: #fef3c7;
  border-color: #fcd34d;
}
.table-wrap {
  overflow-x: auto;
}
.rtable {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.rtable th,
.rtable td {
  border: 1px solid #edf1f6;
  padding: 5px 6px;
  text-align: center;
}
.rtable thead th {
  background: #f9fafb;
}
.rtable thead th.rt {
  background: #eef2ff;
  color: var(--primary);
}
.rtable td.left {
  text-align: left;
  padding-left: 8px;
  font-weight: 600;
  white-space: nowrap;
}
.rtable td.cell {
  min-width: 120px;
  vertical-align: middle;
}
.cell-in {
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: center;
}
.cell-in input {
  width: 72px;
  border: 1px solid #e5e7eb;
  border-radius: 5px;
  padding: 4px 6px;
  font-size: 12px;
  background: #fff;
}
.cell-in.saved input {
  background: #ecfdf5;
  border-color: #6ee7b7;
  color: #065f46;
}
.cell-in.dirty input {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #92400e;
}
.cell-in .link:disabled {
  opacity: 0.45;
  cursor: default;
}
.import-bar {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.import-box {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
.import-box textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
  font-family: ui-monospace, monospace;
}
</style>
