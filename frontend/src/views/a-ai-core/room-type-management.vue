<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 房型管理 —— 系统配置 · 定义有哪些房型（类型，非物理房间实例）
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import SystemConfigNav from '../../components/SystemConfigNav.vue'

type RoomTypeRow = {
  id?: number
  name: string
  code: string
  area: number
  bed: string
  tags: string[]
  room_count?: number
  base_price?: number
  capacity?: number
  breakfast_included?: boolean
  description?: string
  image_url?: string
  has_window?: boolean
  orientation?: string
}

const router = useRouter()
const types = ref<RoomTypeRow[]>([])
const loadError = ref('')
const saving = ref(false)
const showEditor = ref(false)
const editing = ref<RoomTypeRow | null>(null)
const form = ref({
  id: 0,
  name: '',
  code: '',
  area: 28,
  bed: '大床',
  tagsText: '',
  capacity: 2,
  base_price: 0,
  description: '',
  image_url: '',
  has_window: true,
  orientation: '',
})

async function load() {
  loadError.value = ''
  try {
    const rows = await api.listRoomTypes(hotelStore.hotelId)
    types.value = (rows || []).map((rt: any) => ({
      id: rt.id,
      name: rt.name,
      code: rt.code,
      area: rt.area ?? 28,
      bed: rt.bed || rt.bed_type || '标准床型',
      tags: Array.isArray(rt.tags) ? rt.tags : [],
      room_count: rt.linked_rooms ?? rt.room_count ?? 0,
      base_price: rt.base_price != null ? Number(rt.base_price) : 0,
      capacity: rt.capacity ?? 2,
      breakfast_included: !!rt.breakfast_included,
      description: rt.description || '',
      image_url: rt.image_url || '',
      has_window: rt.has_window !== false,
      orientation: rt.orientation || '',
    }))
  } catch (e: any) {
    types.value = []
    loadError.value = e?.message || t('房型加载失败')
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

function openCreate() {
  editing.value = null
  form.value = {
    id: 0,
    name: '',
    code: '',
    area: 28,
    bed: '大床',
    tagsText: '含早, 淋浴',
    capacity: 2,
    base_price: 399,
    description: '',
    image_url: '',
    has_window: true,
    orientation: '南向',
  }
  showEditor.value = true
}

function openEdit(row: RoomTypeRow) {
  editing.value = row
  form.value = {
    id: row.id || 0,
    name: row.name,
    code: row.code,
    area: row.area,
    bed: row.bed,
    tagsText: (row.tags || []).join(', '),
    capacity: row.capacity || 2,
    base_price: row.base_price || 0,
    description: row.description || '',
    image_url: row.image_url || '',
    has_window: row.has_window !== false,
    orientation: row.orientation || '',
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
}

function viewRooms(row: RoomTypeRow) {
  if (!row.id) return
  router.push({ path: '/a-ai-core/room-master', query: { room_type_id: String(row.id) } })
}

async function saveOne() {
  if (!form.value.name.trim() || !form.value.code.trim()) {
    toast(t('请填写房型名称与代码'), false)
    return
  }
  saving.value = true
  try {
    const tags = form.value.tagsText
      .split(/[,，]/)
      .map((x) => x.trim())
      .filter(Boolean)
    const payload = {
      hotel_id: hotelStore.hotelId,
      name: form.value.name.trim(),
      code: form.value.code.trim(),
      area: Number(form.value.area) || 28,
      bed: form.value.bed.trim() || '标准床型',
      tags,
      capacity: Number(form.value.capacity) || 2,
      base_price: Number(form.value.base_price) || 0,
      breakfast_included: tags.includes('含早'),
      description: form.value.description.trim(),
      image_url: form.value.image_url.trim(),
      has_window: !!form.value.has_window,
      orientation: form.value.orientation.trim(),
    }
    if (editing.value?.id) {
      await api.updateRoomType(editing.value.id, payload)
      toast(t('房型已保存'))
    } else {
      await api.createRoomType(payload)
      toast(t('房型已新增'))
    }
    showEditor.value = false
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function removeType(row: RoomTypeRow) {
  if (!row.id) return
  const n = row.room_count || 0
  if (n > 0) {
    toast(`仍有 ${n} 间关联房间，请先在房间档案中改绑或删除`, false)
    return
  }
  if (!window.confirm(t('确定删除房型「{name}」？', { name: row.name }))) return
  try {
    await api.deleteRoomType(row.id)
    toast(t('已删除'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('删除失败'), false)
  }
}

function exportCsv() {
  const header = [
    t('名称'),
    t('代码'),
    t('面积'),
    t('床型'),
    t('最大入住'),
    t('门市价'),
    t('关联房间数'),
    t('配置'),
    t('有窗'),
    t('朝向'),
    t('描述'),
  ]
  const lines = types.value.map((row) =>
    [
      row.name,
      row.code,
      row.area,
      row.bed,
      row.capacity,
      row.base_price,
      row.room_count ?? 0,
      (row.tags || []).join('|'),
      row.has_window === false ? t('否') : t('是'),
      row.orientation || '',
      (row.description || '').replace(/[\r\n,]/g, ' '),
    ].join(','),
  )
  const blob = new Blob([[header.join(','), ...lines].join('\n')], {
    type: 'text/csv;charset=utf-8',
  })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `room-types-${hotelStore.hotelId}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<template>
  <main class="rtm-page">
    <div class="rtm-wrap">
      <SystemConfigNav />
      <div class="rtm-head">
        <div>
          <h1 class="rtm-title">{{ t('房型管理') }}</h1>
          <p v-if="loadError" class="rtm-err">{{ loadError }}</p>
        </div>
      </div>

      <div class="rtm-toolbar">
        <button class="btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span>
          {{ t('新增房型') }}
        </button>
        <button class="btn-ghost" type="button" disabled :title="t('暂未接文件导入')">
          {{ t('导入房型') }}
        </button>
        <button class="btn-ghost" type="button" :disabled="!types.length" @click="exportCsv">
          {{ t('导出') }}
        </button>
      </div>

      <section class="rtm-card">
        <div class="card-head">
          <h2>
            <span class="material-symbols-outlined ico">meeting_room</span>
            {{ t('房型列表') }}
            <span class="meta">（{{ types.length }} {{ t('种）') }}</span>
          </h2>
        </div>

        <div class="table-wrap">
          <table class="rtm-table">
            <thead>
              <tr>
                <th>{{ t('房型名称') }}</th>
                <th>{{ t('代码') }}</th>
                <th>{{ t('面积') }}</th>
                <th>{{ t('床型') }}</th>
                <th>{{ t('最大入住') }}</th>
                <th>{{ t('门市价') }}</th>
                <th>{{ t('关联房间数') }}</th>
                <th>{{ t('基础配置') }}</th>
                <th class="right">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in types" :key="row.id || row.code || i">
                <td class="name">
                  <div class="name-cell">
                    <img v-if="row.image_url" class="thumb" :src="row.image_url" alt="" />
                    <span>{{ row.name }}</span>
                  </div>
                </td>
                <td class="code">{{ row.code }}</td>
                <td class="num">{{ row.area }} m²</td>
                <td>{{ row.bed }}</td>
                <td class="num">{{ row.capacity ?? 2 }}</td>
                <td class="num">¥{{ Math.round(Number(row.base_price) || 0) }}</td>
                <td class="num">
                  <button type="button" class="link-count" @click="viewRooms(row)">
                    {{ row.room_count ?? 0 }}
                  </button>
                </td>
                <td>
                  <div class="tags">
                    <span v-for="(tag, j) in row.tags" :key="j" class="tag">{{ tag }}</span>
                    <span v-if="row.has_window === false" class="tag muted">{{ t('无窗') }}</span>
                    <span v-else-if="row.orientation" class="tag muted">{{ row.orientation }}</span>
                    <span v-if="!row.tags.length" class="tag">{{ t('标准配置') }}</span>
                  </div>
                </td>
                <td class="right">
                  <div class="ops">
                    <button class="op" type="button" @click="openEdit(row)">{{ t('编辑') }}</button>
                    <button class="op danger" type="button" @click="removeType(row)">
                      {{ t('删除') }}
                    </button>
                    <button class="op" type="button" @click="viewRooms(row)">
                      {{ t('查看房间') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!types.length">
                <td colspan="9" class="empty">{{ t('暂无房型，请先新增') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ editing ? t('编辑房型') : t('新增房型') }}</h3>
          <button type="button" class="icon-x" @click="closeEditor">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label>{{ t('房型名称') }}<input v-model="form.name" type="text" /></label>
          <label
            >{{ t('代码') }}<input v-model="form.code" type="text" :disabled="!!editing"
          /></label>
          <label
            >{{ t('面积 (m²)') }}<input v-model.number="form.area" type="number" min="1"
          /></label>
          <label>{{ t('床型') }}<input v-model="form.bed" type="text" /></label>
          <label
            >{{ t('最大入住人数') }}<input v-model.number="form.capacity" type="number" min="1"
          /></label>
          <label
            >{{ t('门市价基准') }}<input v-model.number="form.base_price" type="number" min="0"
          /></label>
          <label
            >{{ t('朝向')
            }}<input v-model="form.orientation" type="text" :placeholder="t('南向 / 城景')"
          /></label>
          <label class="check">
            <input v-model="form.has_window" type="checkbox" />
            {{ t('有窗') }}</label
          >
          <label class="full"
            >{{ t('房型图片 URL')
            }}<input v-model="form.image_url" type="text" placeholder="https://…"
          /></label>
          <label class="full"
            >{{ t('基础配置（逗号分隔）')
            }}<input v-model="form.tagsText" type="text" :placeholder="t('含早, 淋浴, 景观')"
          /></label>
          <label class="full"
            >{{ t('房型描述（卖点）') }}
            <textarea v-model="form.description" rows="3" :placeholder="t('给客人看的房型亮点…')" />
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
.rtm-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
}
.rtm-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.rtm-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.rtm-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.rtm-err {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--error, #ba1a1a);
}
.rtm-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.btn-ghost {
  padding: 8px 16px;
  border: 1px solid var(--outline, #727785);
  border-radius: 8px;
  background: transparent;
  color: var(--on-surface, #1f2329);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--primary, #005bbf);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.7;
}
.btn-primary .material-symbols-outlined {
  font-size: 18px;
}
.rtm-card {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 20px 24px;
}
.card-head h2 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-head .ico {
  color: var(--primary, #005bbf);
}
.card-head .meta {
  font-size: 12px;
  font-weight: 400;
  color: var(--on-surface-variant, #5b616e);
}
.table-wrap {
  overflow-x: auto;
}
.rtm-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.rtm-table th {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
  white-space: nowrap;
}
.rtm-table td {
  padding: 14px;
  font-size: 14px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
  vertical-align: middle;
}
.rtm-table th.right,
.rtm-table td.right {
  text-align: right;
}
.rtm-table tbody tr:hover {
  background: var(--surface-container-low, #f2f4f5);
}
.name {
  font-weight: 600;
}
.name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.thumb {
  width: 40px;
  height: 32px;
  object-fit: cover;
  border-radius: 4px;
  background: #eee;
}
.code,
.num {
  font-family: 'Roboto Mono', ui-monospace, monospace;
}
.link-count {
  border: none;
  background: none;
  color: var(--primary, #005bbf);
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  font-size: inherit;
  padding: 0;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--surface-container-high, #e6e8e9);
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.tag.muted {
  background: transparent;
  border: 1px dashed var(--outline-variant, #c1c6d6);
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.op {
  border: none;
  background: none;
  color: var(--primary, #005bbf);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.op.danger {
  color: #c62828;
}
.empty {
  text-align: center;
  padding: 32px !important;
  color: var(--on-surface-variant, #5b616e);
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
  width: min(640px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
}
.modal-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.icon-x {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--on-surface-variant, #5b616e);
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
  color: var(--on-surface-variant, #5b616e);
}
.modal-body label.full {
  grid-column: 1 / -1;
}
.modal-body label.check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding-top: 22px;
}
.modal-body input,
.modal-body textarea {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  outline: none;
}
.modal-body input:focus,
.modal-body textarea:focus {
  border-color: var(--primary, #005bbf);
}
.modal-body input:disabled {
  background: #f2f4f5;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--outline-variant, #e2e5eb);
}
</style>
