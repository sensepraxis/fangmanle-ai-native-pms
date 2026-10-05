<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 活动台：维护周边场次（名称/类型/日期/距离/热度），决定是否纳入定价。
 * 参数页只调「灵敏度 / 触发距离」；真实活动在本面板录入。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const props = defineProps<{ config: any }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const EVENT_TYPE_OPTS = [
  { value: 'concert', label: '演唱会' },
  { value: 'exhibition', label: '展会' },
  { value: 'sport', label: '赛事' },
  { value: 'school', label: '开学/校园' },
  { value: 'holiday', label: '节假日' },
  { value: 'self', label: '本店活动' },
  { value: 'other', label: '其它' },
] as const

const INTENSITY_OPTS = ['弱', '中', '强', '爆'] as const
const HEAT_BY_INTENSITY: Record<string, number> = { 弱: 20, 中: 40, 强: 65, 爆: 90 }

const collapsed = ref(false)
const editing = ref(false)
const events = ref<any[]>([])
const busy = ref(false)
const editId = ref<string | null>(null)

const todayStr = () => new Date().toISOString().slice(0, 10)

function emptyForm() {
  const d = todayStr()
  return {
    event_name: '',
    event_type: 'concert',
    start_date: d,
    end_date: d,
    distance_km: '' as string | number,
    intensity: '中',
    heat_score: 40 as string | number,
    venue_address: '',
    note: '',
    is_active: true,
  }
}

const form = ref(emptyForm())

const activeCount = computed(() => events.value.filter((e) => e.is_active !== false).length)
const affectingCount = computed(() => events.value.filter((e) => e.affects_pricing).length)

function typeLabel(code: string) {
  const hit = EVENT_TYPE_OPTS.find((x) => x.value === code)?.label
  return hit ? t(hit) : t(code || '其它')
}

function onIntensityChange() {
  const h = HEAT_BY_INTENSITY[form.value.intensity]
  if (h != null) form.value.heat_score = h
}

async function load() {
  events.value = await api.paEvents(hotelStore.hotelId, true)
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function startCreate() {
  editId.value = null
  form.value = emptyForm()
  editing.value = true
}

function startEdit(ev: any) {
  editId.value = ev.event_id
  form.value = {
    event_name: ev.event_name || '',
    event_type: ev.event_type || 'other',
    start_date: ev.start_date || todayStr(),
    end_date: ev.end_date || todayStr(),
    distance_km: ev.distance_km ?? '',
    intensity: ev.intensity || '中',
    heat_score: ev.heat_score ?? HEAT_BY_INTENSITY[ev.intensity || '中'] ?? 40,
    venue_address: ev.venue_address || '',
    note: ev.note || '',
    is_active: ev.is_active !== false,
  }
  editing.value = true
  collapsed.value = false
}

function cancelEdit() {
  editId.value = null
  form.value = emptyForm()
  editing.value = false
}

async function afterMutate(msg: string) {
  await load()
  emit('changed')
  try {
    await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
    toast(t('{msg} · 建议已重算', { msg }))
  } catch {
    toast(msg)
  }
}

async function save() {
  const name = String(form.value.event_name || '').trim()
  if (!name) {
    toast(t('请填写活动名称'), false)
    return
  }
  if (!form.value.start_date || !form.value.end_date) {
    toast(t('请填写起止日期'), false)
    return
  }
  busy.value = true
  const payload: any = {
    event_name: name,
    event_type: form.value.event_type,
    start_date: form.value.start_date,
    end_date: form.value.end_date,
    intensity: form.value.intensity,
    heat_score: Number(form.value.heat_score),
    venue_address: String(form.value.venue_address || '').trim() || undefined,
    note: String(form.value.note || '').trim() || undefined,
    is_active: !!form.value.is_active,
  }
  if (form.value.event_type !== 'holiday') {
    if (form.value.distance_km !== '' && form.value.distance_km != null) {
      payload.distance_km = Number(form.value.distance_km)
    }
    // 有场馆地址则后端自动 geocode + 算距；勿再默认 0km
    payload.auto_distance = true
  } else if (form.value.distance_km !== '' && form.value.distance_km != null) {
    payload.distance_km = Number(form.value.distance_km)
  }
  try {
    if (editId.value) {
      await api.paUpdateEvent(hotelStore.hotelId, editId.value, payload)
      cancelEdit()
      await afterMutate(t('活动已保存'))
    } else {
      const created = await api.paCreateEvent(hotelStore.hotelId, payload)
      cancelEdit()
      const note = created?.geo_note ? `（${created.geo_note}）` : ''
      await afterMutate(t('已添加活动「{name}」{note}', { name, note }))
    }
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    busy.value = false
  }
}

async function toggleActive(ev: any, on: boolean) {
  try {
    await api.paUpdateEvent(hotelStore.hotelId, ev.event_id, { is_active: on })
    await afterMutate(on ? t('已纳入定价') : t('已取消纳入定价'))
  } catch (e: any) {
    toast(e?.message || t('更新失败'), false)
  }
}

async function removeEvent(ev: any) {
  if (ev.source === 'builtin') {
    try {
      await api.paDeactivateEvent(hotelStore.hotelId, ev.event_id)
      await afterMutate(t('内置节假日已停用（不可删除）'))
    } catch (e: any) {
      toast(e?.message || t('停用失败'), false)
    }
    return
  }
  if (!confirm(t('确定删除活动「{name}」？', { name: ev.event_name }))) return
  try {
    await api.paDeleteEvent(hotelStore.hotelId, ev.event_id)
    if (editId.value === ev.event_id) cancelEdit()
    await afterMutate(t('已删除活动'))
  } catch (e: any) {
    toast(e?.message || t('删除失败'), false)
  }
}
</script>

<template>
  <div class="ev-panel card-clean" :class="{ collapsed, editing }">
    <div class="ev-head">
      <button
        type="button"
        class="chev"
        @click="collapsed = !collapsed"
        :aria-expanded="!collapsed"
      >
        {{ collapsed ? '▸' : '▾' }}
      </button>
      <div class="ev-title">
        <span class="material-symbols-outlined">event</span>
        {{ t('活动台') }}
        <span class="count">{{ activeCount }} {{ t('场启用') }}</span>
        <span class="count muted">· {{ affectingCount }} {{ t('场计入定价') }}</span>
      </div>
      <div class="ev-actions">
        <button type="button" class="btn btn-ghost sm" @click="startCreate">{{ t('新增') }}</button>
        <button type="button" class="btn btn-ghost sm" @click="editing = !editing">
          {{ editing ? t('收起编辑') : t('编辑') }}
        </button>
      </div>
    </div>

    <div v-if="!collapsed && !editing" class="ev-body">
      <span
        v-for="ev in events.filter((e) => e.is_active !== false).slice(0, 8)"
        :key="ev.event_id"
        class="ev-chip"
        :class="{ out: !ev.affects_pricing }"
        :title="ev.affects_pricing ? t('计入定价') : t('距离超限或不计入')"
      >
        {{ ev.event_name }}
        <span v-if="ev.heat_score != null" class="heat">{{ Math.round(ev.heat_score) }}°</span>
        <span v-if="ev.distance_km != null" class="dist">{{ ev.distance_km }}km</span>
      </span>
      <span v-if="!activeCount" class="empty-hint">{{ t('尚未配置活动 · 点「新增」录入') }}</span>
      <span v-else-if="events.filter((e) => e.is_active !== false).length > 8" class="empty-hint">{{
        t('…点编辑查看全部')
      }}</span>
    </div>

    <div v-if="editing && !collapsed" class="ev-edit">
      <div class="sec-title">{{ editId ? t('编辑活动') : t('① 新增活动') }}</div>
      <div class="add-grid">
        <input v-model="form.event_name" :placeholder="t('活动名称 *')" class="grow" />
        <select v-model="form.event_type" class="narrow">
          <option v-for="opt in EVENT_TYPE_OPTS" :key="opt.value" :value="opt.value">
            {{ t(opt.label) }}
          </option>
        </select>
        <input v-model="form.start_date" type="date" class="date" />
        <span class="dash">{{ t('至') }}</span>
        <input v-model="form.end_date" type="date" class="date" />
        <select v-model="form.intensity" class="narrow" @change="onIntensityChange">
          <option v-for="i in INTENSITY_OPTS" :key="i" :value="i">{{ t(i) }}</option>
        </select>
        <input
          v-model.number="form.heat_score"
          type="number"
          min="0"
          max="100"
          :placeholder="t('热度 0–100')"
          class="narrow"
        />
        <input
          v-model="form.venue_address"
          :placeholder="t('场馆地址（填后自动定位算距）')"
          class="grow"
        />
        <input
          v-if="form.event_type !== 'holiday'"
          v-model="form.distance_km"
          type="number"
          step="0.1"
          min="0"
          :placeholder="t('距本店 km（可空，由地图算）')"
          class="narrow"
        />
        <input v-model="form.note" :placeholder="t('备注（可选）')" class="grow" />
        <label class="chk">
          <input v-model="form.is_active" type="checkbox" />
          {{ t('纳入定价') }}</label
        >
        <button type="button" class="btn btn-primary sm" :disabled="busy" @click="save">
          {{ busy ? t('保存中…') : editId ? t('保存修改') : t('添加活动') }}
        </button>
        <button v-if="editId" type="button" class="btn btn-ghost sm" @click="cancelEdit">
          {{ t('取消') }}
        </button>
      </div>

      <div class="sec-title">{{ t('② 已录活动') }}</div>
      <div
        v-for="ev in events"
        :key="ev.event_id"
        class="row"
        :class="{ off: ev.is_active === false }"
      >
        <div class="nm">
          <b>{{ ev.event_name }}</b>
          <span class="tag">{{ typeLabel(ev.event_type) }}</span>
          <span class="tag">{{ ev.start_date }} → {{ ev.end_date }}</span>
          <span v-if="ev.intensity" class="tag"
            >{{ t(ev.intensity) }} · {{ t('热度') }} {{ ev.heat_score ?? '—' }}</span
          >
          <span v-if="ev.distance_km != null" class="tag">{{ ev.distance_km }} km</span>
          <span class="tag" :class="ev.affects_pricing ? 'ok' : 'warn'">
            {{
              ev.affects_pricing
                ? t('计入定价')
                : ev.is_active === false
                  ? t('已停用')
                  : ev.needs_location
                    ? t('待定位')
                    : t('距离超限')
            }}</span
          >
          <span v-if="ev.source === 'builtin'" class="tag">{{ t('内置') }}</span>
        </div>
        <label class="chk sm">
          <input
            type="checkbox"
            :checked="ev.is_active !== false"
            @change="toggleActive(ev, ($event.target as HTMLInputElement).checked)"
          />
          {{ t('纳入') }}</label
        >
        <button type="button" class="link" @click="startEdit(ev)">{{ t('改') }}</button>
        <button type="button" class="del" @click="removeEvent(ev)">
          {{ ev.source === 'builtin' ? t('停用') : t('删') }}
        </button>
      </div>
      <div v-if="!events.length" class="empty-hint" style="padding: 8px 0">{{ t('暂无活动') }}</div>
    </div>
  </div>
</template>

<style scoped>
.ev-panel {
  margin-bottom: 4px;
  padding: 0;
  overflow: hidden;
}
.ev-head {
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
.ev-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 650;
  font-size: 14px;
  flex-wrap: wrap;
}
.ev-title .material-symbols-outlined {
  font-size: 20px;
  color: var(--primary);
}
.count {
  font-size: 12px;
  color: var(--on-surface-variant);
  font-weight: 500;
}
.count.muted {
  color: #9ca3af;
}
.ev-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn.sm {
  padding: 5px 10px;
  font-size: 12px;
}
.ev-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 14px 12px;
  align-items: center;
}
.ev-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 20px;
  font-size: 12px;
}
.ev-chip.out {
  opacity: 0.55;
}
.ev-chip .heat {
  font-weight: 600;
  color: var(--primary);
}
.ev-chip .dist {
  color: var(--on-surface-variant);
  font-size: 11px;
}
.empty-hint {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ev-edit {
  padding: 10px 14px 14px;
  border-top: 1px dashed #e5e7eb;
}
.sec-title {
  font-size: 12px;
  font-weight: 650;
  margin: 6px 0 8px;
}
.add-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}
.add-grid input,
.add-grid select {
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
.add-grid .date {
  flex: 0 0 132px;
}
.dash {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.chk {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
}
.chk.sm {
  font-size: 11px;
  white-space: nowrap;
}
.row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  font-size: 12px;
  border-bottom: 1px solid #edf1f6;
}
.row.off {
  opacity: 0.55;
}
.row .nm {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.tag {
  font-size: 11px;
  color: var(--on-surface-variant);
  background: #f3f4f6;
  padding: 2px 7px;
  border-radius: 4px;
}
.tag.ok {
  background: #ecfdf5;
  color: #16a34a;
}
.tag.warn {
  background: #fff7ed;
  color: #c2410c;
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
</style>
