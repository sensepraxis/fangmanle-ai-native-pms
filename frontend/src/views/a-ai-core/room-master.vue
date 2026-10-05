<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 房间档案 —— 列表 + 内联详情（原「状态登记」右侧详情并入）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { STATUS_CN, toast } from '../../lib/ui'
import SystemConfigNav from '../../components/SystemConfigNav.vue'

const route = useRoute()
const router = useRouter()

const rooms = ref<any[]>([])
const roomTypes = ref<any[]>([])
const loadError = ref('')
const filterTypeId = ref<string>('')
const searchQ = ref('')
const saving = ref(false)
const showEditor = ref(false)
const editing = ref<any | null>(null)
const selectedId = ref<number | null>(null)
const physBusy = ref(false)

const PHYS = computed(() => [
  { v: 'normal', label: t('正常') },
  { v: 'maintenance', label: t('维修') },
  { v: 'oos', label: t('停用') },
])

const form = ref({
  id: 0,
  room_no: '',
  room_type_id: '' as string | number,
  building: '',
  floor: 1 as number | string,
  smoking: false,
  featureTagsText: '',
  lock_id: '',
  physical_status: 'normal',
})

const selected = computed(() => rooms.value.find((r) => r.id === selectedId.value) || null)

const typeName = computed(() => {
  const id = Number(filterTypeId.value)
  if (!id) return ''
  return roomTypes.value.find((t) => t.id === id)?.name || ''
})

const attrTags = computed(() => {
  const r = selected.value
  if (!r) return [] as string[]
  const tags: string[] = []
  if (r.physical_status === 'maintenance') tags.push(t('维修关停'))
  if (r.physical_status === 'oos') tags.push(t('停用'))
  if (r.room_type_name) tags.push(r.room_type_name)
  for (const tag of r.feature_tags || []) tags.push(t(tag))
  if (r.lock_id) tags.push(t('门锁 {id}', { id: r.lock_id }))
  return [...new Set(tags)]
})

async function loadTypes() {
  try {
    roomTypes.value = (await api.listRoomTypes(hotelStore.hotelId)) || []
  } catch {
    roomTypes.value = []
  }
}

async function loadRooms() {
  loadError.value = ''
  try {
    const tid = filterTypeId.value ? Number(filterTypeId.value) : undefined
    rooms.value = (await api.listRoomMaster(hotelStore.hotelId, tid, searchQ.value)) || []
    if (selectedId.value && !rooms.value.some((r) => r.id === selectedId.value)) {
      selectedId.value = rooms.value[0]?.id ?? null
    }
  } catch (e: any) {
    rooms.value = []
    loadError.value = e?.message || t('房间档案加载失败')
  }
}

async function load() {
  await loadTypes()
  const q = route.query.room_type_id
  if (q != null && String(q)) filterTypeId.value = String(q)
  if (route.query.q != null) searchQ.value = String(route.query.q)
  await loadRooms()
  if (route.query.room_id) {
    const rid = Number(route.query.room_id)
    if (rooms.value.some((r) => r.id === rid)) selectedId.value = rid
  }
  if (!selectedId.value && rooms.value.length) selectedId.value = rooms.value[0].id
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(
  () => route.query.room_type_id,
  (v) => {
    filterTypeId.value = v != null && String(v) ? String(v) : ''
    loadRooms()
  },
)

function syncQuery() {
  const q: Record<string, string> = {}
  if (filterTypeId.value) q.room_type_id = filterTypeId.value
  if (searchQ.value.trim()) q.q = searchQ.value.trim()
  if (selectedId.value) q.room_id = String(selectedId.value)
  router.replace({ path: '/a-ai-core/room-master', query: q })
}

function onFilterChange() {
  syncQuery()
  loadRooms()
}

function onSearch() {
  syncQuery()
  loadRooms()
}

function selectRoom(r: any) {
  selectedId.value = r.id
  syncQuery()
}

function openCreate() {
  editing.value = null
  form.value = {
    id: 0,
    room_no: '',
    room_type_id: filterTypeId.value || (roomTypes.value[0]?.id ?? ''),
    building: t('主楼'),
    floor: 1,
    smoking: false,
    featureTagsText: '',
    lock_id: '',
    physical_status: 'normal',
  }
  showEditor.value = true
}

function openEdit(r: any) {
  selectRoom(r)
  editing.value = r
  const tags = (r.feature_tags || []).filter((t: string) => t !== '无烟' && t !== '可吸烟')
  form.value = {
    id: r.id,
    room_no: r.room_no,
    room_type_id: r.room_type_id ?? '',
    building: r.building || '',
    floor: r.floor ?? '',
    smoking: !!r.smoking,
    featureTagsText: tags.join(', '),
    lock_id: r.lock_id || '',
    physical_status: r.physical_status || 'normal',
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
}

watch(
  () => form.value.room_no,
  (no) => {
    if (editing.value) return
    const n = String(no || '').trim()
    if (n && !form.value.lock_id) form.value.lock_id = `LOCK-${n}`
  },
)

async function saveOne() {
  if (!String(form.value.room_no).trim()) {
    toast(t('请填写房号'), false)
    return
  }
  if (!String(form.value.lock_id).trim()) {
    toast(t('请填写门锁 ID（预留对接字段）'), false)
    return
  }
  saving.value = true
  try {
    const feature_tags = form.value.featureTagsText
      .split(/[,，]/)
      .map((x) => x.trim())
      .filter(Boolean)
    const payload = {
      hotel_id: hotelStore.hotelId,
      room_no: String(form.value.room_no).trim(),
      room_type_id: form.value.room_type_id || null,
      building: String(form.value.building || '').trim(),
      floor: form.value.floor === '' ? null : Number(form.value.floor),
      smoking: !!form.value.smoking,
      feature_tags,
      lock_id: String(form.value.lock_id).trim(),
      physical_status: form.value.physical_status || 'normal',
    }
    if (editing.value?.id) {
      const updated = await api.updateRoomMaster(editing.value.id, payload)
      toast(t('房间档案已更新'))
      selectedId.value = editing.value.id
      if (updated?.id) Object.assign(rooms.value.find((x) => x.id === updated.id) || {}, updated)
    } else {
      const created = await api.createRoomMaster(payload)
      toast(t('房间已建档'))
      if (created?.id) selectedId.value = created.id
    }
    showEditor.value = false
    await loadRooms()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function removeRoom(r: any) {
  if (!window.confirm(t('确定删除房间 {no} 的档案？', { no: r.room_no }))) return
  try {
    await api.deleteRoomMaster(r.id)
    toast(t('已删除'))
    if (selectedId.value === r.id) selectedId.value = null
    await loadRooms()
  } catch (e: any) {
    toast(e?.message || t('删除失败'), false)
  }
}

async function onPhysChange(ev: Event) {
  const r = selected.value
  if (!r?.id) return
  const val = (ev.target as HTMLSelectElement).value
  physBusy.value = true
  try {
    const updated = await api.updateRoomMaster(r.id, { physical_status: val })
    toast(t('物理状态已更新'))
    const row = rooms.value.find((x) => x.id === r.id)
    if (row && updated) Object.assign(row, updated)
  } catch (e: any) {
    toast(e?.message || t('更新失败'), false)
  } finally {
    physBusy.value = false
  }
}

function statusLabel(s: string) {
  return STATUS_CN[s] || s
}

function physLabel(s: string) {
  return PHYS.value.find((p) => p.v === s)?.label || s || t('正常')
}

function physClass(s: string) {
  if (s === 'maintenance') return 'phys maint'
  if (s === 'oos') return 'phys oos'
  return 'phys ok'
}

function floorText(r: any) {
  if (r.floor == null) return '—'
  const b = r.building ? t(String(r.building)) : ''
  return `${b ? b + ' · ' : ''}${r.floor}F`
}
</script>

<template>
  <main class="rm-page">
    <div class="rm-wrap">
      <SystemConfigNav />
      <div class="rm-head">
        <div>
          <h1 class="rm-title">{{ t('房间档案') }}</h1>
          <p v-if="loadError" class="rm-err">{{ loadError }}</p>
        </div>
      </div>

      <div class="rm-toolbar">
        <label class="filter">
          <span>{{ t('按房型筛选') }}</span>
          <select v-model="filterTypeId" @change="onFilterChange">
            <option value="">{{ t('全部房型') }}</option>
            <option v-for="rt in roomTypes" :key="rt.id" :value="String(rt.id)">
              {{ rt.name }}（{{ rt.linked_rooms ?? rt.room_count ?? 0 }}）
            </option>
          </select>
        </label>
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input
            v-model="searchQ"
            type="search"
            :placeholder="t('搜索房号 / 门锁 ID')"
            @keydown.enter="onSearch"
          />
          <button type="button" class="search-go" @click="onSearch">{{ t('搜索') }}</button>
        </div>
        <span v-if="typeName" class="chip">{{ t('当前') }}：{{ typeName }}</span>
        <div class="spacer" />
        <button class="btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span>
          {{ t('新增房间') }}
        </button>
      </div>

      <div class="rm-layout" :class="{ 'has-detail': !!selected }">
        <section class="rm-card">
          <div class="table-wrap">
            <table class="rm-table">
              <thead>
                <tr>
                  <th>{{ t('房号') }}</th>
                  <th>{{ t('房型') }}</th>
                  <th>{{ t('楼栋') }}</th>
                  <th>{{ t('楼层') }}</th>
                  <th>{{ t('特征标签') }}</th>
                  <th>{{ t('门锁 ID') }}</th>
                  <th>{{ t('物理状态') }}</th>
                  <th>{{ t('当前状态') }}</th>
                  <th class="right">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="r in rooms"
                  :key="r.id"
                  class="row"
                  :class="{ on: r.id === selectedId }"
                  @click="selectRoom(r)"
                >
                  <td class="no">{{ r.room_no }}</td>
                  <td>{{ r.room_type_name || '—' }}</td>
                  <td>{{ r.building ? t(String(r.building)) : '—' }}</td>
                  <td class="num">{{ r.floor != null ? r.floor + 'F' : '—' }}</td>
                  <td>
                    <div class="tags">
                      <span v-for="(tag, i) in r.feature_tags || []" :key="i" class="tag">{{
                        t(tag)
                      }}</span>
                      <span v-if="!(r.feature_tags || []).length" class="muted">—</span>
                    </div>
                  </td>
                  <td class="mono">{{ r.lock_id || '—' }}</td>
                  <td>
                    <span :class="physClass(r.physical_status)">{{
                      physLabel(r.physical_status)
                    }}</span>
                  </td>
                  <td>
                    <span class="st">{{ statusLabel(r.status) }}</span>
                  </td>
                  <td class="right" @click.stop>
                    <button class="op" type="button" @click="openEdit(r)">{{ t('编辑') }}</button>
                    <button class="op danger" type="button" @click="removeRoom(r)">
                      {{ t('删除') }}
                    </button>
                  </td>
                </tr>
                <tr v-if="!rooms.length">
                  <td colspan="9" class="empty">{{ t('暂无房间档案') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 内联详情：原「状态登记」右侧 -->
        <aside v-if="selected" class="detail">
          <div class="detail-head">
            <div>
              <div class="detail-title">
                <h2>{{ selected.room_no }}</h2>
                <span>{{ selected.room_type_name || t('客房') }}</span>
              </div>
              <p class="detail-loc">
                <span class="material-symbols-outlined">location_on</span>
                {{ floorText(selected) }}
                <template v-if="selected.lock_id"> · {{ selected.lock_id }}</template>
              </p>
            </div>
            <div class="status-box">
              <label>{{ t('物理状态') }}</label>
              <select
                :value="selected.physical_status || 'normal'"
                :disabled="physBusy"
                @change="onPhysChange"
              >
                <option v-for="p in PHYS" :key="p.v" :value="p.v">{{ p.label }}</option>
              </select>
              <p class="hint">
                {{ t('当日房态') }}：{{ statusLabel(selected.status) }}（{{
                  t('请在房态看板变更')
                }}）
              </p>
            </div>
          </div>

          <div class="attr-block">
            <h3>{{ t('房间属性') }}</h3>
            <div class="attr-row">
              <span v-for="tagItem in attrTags" :key="tagItem" class="attr-tag">{{ tagItem }}</span>
              <button type="button" class="attr-add" @click="openEdit(selected)">
                + {{ t('编辑属性') }}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ editing ? t('编辑房间档案') : t('新增房间') }}</h3>
          <button type="button" class="icon-x" @click="closeEditor">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label
            >{{ t('房号') }}<input v-model="form.room_no" type="text" placeholder="0301"
          /></label>
          <label
            >{{ t('房型') }}
            <select v-model="form.room_type_id">
              <option value="">{{ t('未绑定') }}</option>
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
            </select>
          </label>
          <label>{{ t('楼栋') }}<input v-model="form.building" type="text" /></label>
          <label>{{ t('楼层') }}<input v-model.number="form.floor" type="number" /></label>
          <label
            >{{ t('门锁 ID') }}<input v-model="form.lock_id" type="text" placeholder="LOCK-0301"
          /></label>
          <label
            >{{ t('物理状态') }}
            <select v-model="form.physical_status">
              <option v-for="p in PHYS" :key="p.v" :value="p.v">{{ p.label }}</option>
            </select>
          </label>
          <label class="check">
            <input v-model="form.smoking" type="checkbox" />
            {{ t('可吸烟房（默认无烟）') }}</label
          >
          <label class="full"
            >{{ t('特征标签（逗号分隔）') }}
            <input
              v-model="form.featureTagsText"
              type="text"
              :placeholder="t('加床, 景观, 无障碍')"
            />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" type="button" @click="closeEditor">{{ t('取消') }}</button>
          <button class="btn-primary" type="button" :disabled="saving" @click="saveOne">
            {{ saving ? t('保存中…') : t('保存') }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.rm-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: #fff;
}
.rm-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.rm-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
}
.rm-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}
.rm-err {
  margin: 6px 0 0;
  font-size: 12px;
  color: #ba1a1a;
}
.rm-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.filter {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #5b616e;
}
.filter select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #c1c6d6;
  font-size: 13px;
  min-width: 160px;
}
.search-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 4px 0 10px;
  border: 1px solid #c1c6d6;
  border-radius: 8px;
  min-width: 240px;
}
.search-box .material-symbols-outlined {
  font-size: 18px;
  color: #9aa1ad;
}
.search-box input {
  flex: 1;
  border: none;
  outline: none;
  padding: 8px 4px;
  font-size: 13px;
}
.search-go {
  border: none;
  background: #f2f4f5;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.chip {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(0, 91, 191, 0.08);
  color: #005bbf;
  font-weight: 600;
}
.spacer {
  flex: 1;
}
.btn-ghost {
  padding: 8px 16px;
  border: 1px solid #727785;
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: #005bbf;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary .material-symbols-outlined {
  font-size: 18px;
}

.rm-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: start;
}
@media (min-width: 1200px) {
  .rm-layout.has-detail {
    grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
  }
}

.rm-card {
  border: 1px solid #c1c6d6;
  border-radius: 12px;
  overflow: hidden;
}
.table-wrap {
  overflow-x: auto;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}
.rm-table {
  width: 100%;
  border-collapse: collapse;
}
.rm-table th {
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
  padding: 12px 12px;
  text-align: left;
  font-size: 12px;
  color: #5b616e;
  border-bottom: 1px solid #c1c6d6;
  white-space: nowrap;
}
.rm-table td {
  padding: 12px;
  font-size: 13px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.4);
  vertical-align: middle;
}
.rm-table th.right,
.rm-table td.right {
  text-align: right;
}
.row {
  cursor: pointer;
}
.row:hover {
  background: #f7f8fa;
}
.row.on {
  background: rgba(0, 91, 191, 0.06);
}
.no {
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
}
.num,
.mono {
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #e6e8e9;
  font-size: 11px;
  color: #5b616e;
}
.muted {
  color: #9aa1ad;
}
.phys {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.phys.ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.phys.maint {
  background: #fff3e0;
  color: #e65100;
}
.phys.oos {
  background: #eeeeee;
  color: #616161;
}
.st {
  font-size: 12px;
  font-weight: 600;
  color: #5b616e;
}
.op {
  border: none;
  background: none;
  color: #005bbf;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  margin-left: 8px;
}
.op.danger {
  color: #c62828;
}
.empty {
  text-align: center;
  padding: 36px !important;
  color: #9aa1ad;
}

.detail {
  border: 1px solid #c1c6d6;
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: calc(100vh - 220px);
  overflow: auto;
}
.detail-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}
.detail-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.detail-title h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
}
.detail-title span {
  font-size: 14px;
  color: #5b616e;
}
.detail-loc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #5b616e;
  display: flex;
  align-items: center;
  gap: 4px;
}
.detail-loc .material-symbols-outlined {
  font-size: 16px;
}
.status-box label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #5b616e;
  margin-bottom: 4px;
}
.status-box select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #c1c6d6;
  font-size: 13px;
  font-weight: 600;
  min-width: 120px;
}
.status-box .hint {
  margin: 6px 0 0;
  font-size: 11px;
  color: #9aa1ad;
}
.attr-block h3,
.panel-head h3,
.ai-panel > h3 {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}
.attr-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.attr-tag {
  padding: 6px 10px;
  border-radius: 8px;
  background: #f2f4f5;
  font-size: 12px;
  font-weight: 600;
  color: #3c4048;
}
.attr-add {
  border: 1px dashed #c1c6d6;
  background: transparent;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: #005bbf;
  cursor: pointer;
  font-weight: 600;
}
.detail-split {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel {
  border: 1px solid #e2e5eb;
  border-radius: 10px;
  padding: 12px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.link-btn {
  border: none;
  background: none;
  color: #005bbf;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.link-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.ai-err {
  margin: 0;
  font-size: 12px;
  color: #c62828;
  line-height: 1.45;
}
.ico-err {
  color: #c62828;
  font-size: 18px;
}
.ico-ai {
  color: #5e35b1;
  font-size: 18px;
}
.fault-box {
  background: #fce8e6;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.fault-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #8c1d18;
}
.fault-time {
  font-weight: 500;
  color: #9aa1ad;
  font-size: 12px;
}
.fault-desc {
  margin: 6px 0;
  font-size: 12px;
  color: #5b616e;
}
.fault-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #5b616e;
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tl-item {
  position: relative;
  padding-left: 16px;
}
.tl-dot {
  position: absolute;
  left: 0;
  top: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #90a4ae;
}
.tl-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}
.tl-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9aa1ad;
}
.ai-panel {
  border-color: #d1c4e9;
  background: linear-gradient(180deg, #faf7ff 0%, #fff 48%);
}
.ai-intro {
  margin: 0 0 10px;
  font-size: 12px;
  color: #5b616e;
}
.ai-trigger {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px;
}
.ai-gen-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #7e57c2;
  background: #fff;
  color: #5e35b1;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.ai-gen-btn .material-symbols-outlined {
  font-size: 18px;
}
.ai-gen-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}
.ai-gen-btn:hover:not(:disabled) {
  background: #f3eefa;
}
.ai-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-top: 1px solid #eee;
}
.ai-main {
  display: flex;
  gap: 8px;
  min-width: 0;
}
.ai-main .material-symbols-outlined {
  font-size: 20px;
  color: #5e35b1;
}
.ai-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}
.ai-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #5b616e;
}
.ai-desc.danger {
  color: #c62828;
}
.ai-act {
  flex-shrink: 0;
  border: 1px solid #c1c6d6;
  background: #fff;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.ai-act.danger {
  border-color: #ef9a9a;
  color: #c62828;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal {
  width: min(560px, 100%);
  background: #fff;
  border-radius: 12px;
  border: 1px solid #c1c6d6;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e5eb;
}
.modal-head h3 {
  margin: 0;
  font-size: 16px;
}
.icon-x {
  border: none;
  background: none;
  cursor: pointer;
}
.modal-body {
  padding: 16px 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.modal-body label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #5b616e;
}
.modal-body label.full {
  grid-column: 1 / -1;
}
.modal-body label.check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding-top: 22px;
  grid-column: 1 / -1;
}
.modal-body input,
.modal-body select {
  border: 1px solid #c1c6d6;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid #e2e5eb;
}
</style>
