<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 系统设置 · 财务参数 · OTA佣金
 * 对齐房型管理：新增渠道 / 编辑佣金 / 启用·禁用；价格助手只读引用。
 * embedded=true 时嵌入财务参数三级 Tab，隐藏独立页头与系统配置二级导航。
 */
import { computed, onMounted, ref, watch } from 'vue'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

type ChannelRow = {
  channel_code: string
  channel_name: string
  commission_rate: number
  commission_pct: number
  settle_cycle: string
  is_enabled: boolean
  note: string
  is_zero_commission?: boolean
}

const loading = ref(true)
const saving = ref(false)
const canEdit = ref(false)
const settleCycles = ref<string[]>(['T+1', 'T+7', '月结', '实时'])
const rows = ref<ChannelRow[]>([])
const overrides = ref<any[]>([])
const roomTypes = ref<{ id: number; name: string }[]>([])

const showEditor = ref(false)
const editing = ref(false)
const form = ref({
  channel_code: '',
  channel_name: '',
  commission_pct: 10,
  settle_cycle: 'T+7',
  note: '',
  is_enabled: true,
})

const showOvEditor = ref(false)
const ovEditing = ref(false)
const ovSaving = ref(false)
const ovFilterChannel = ref('')
const ovForm = ref({
  id: null as number | null,
  channel_code: '',
  room_type_id: '' as string | number,
  rate_code: '',
  commission_pct: 12,
  effective_from: '',
  effective_to: '',
  note: '',
  is_enabled: true,
})

const enabledCount = computed(() => rows.value.filter((r) => r.is_enabled).length)
const enabledChannels = computed(() => rows.value.filter((r) => r.is_enabled))
const filteredOverrides = computed(() => {
  const code = ovFilterChannel.value
  if (!code) return overrides.value
  return overrides.value.filter((o: any) => o.channel_code === code)
})
const ovEnabledCount = computed(
  () => overrides.value.filter((o: any) => o.is_enabled !== false).length,
)

function mapRows(list: any[]): ChannelRow[] {
  return (list || []).map((c: any) => ({
    channel_code: c.channel_code || c.code,
    channel_name: c.channel_name || c.name,
    commission_rate: Number(c.commission_rate || 0),
    commission_pct: Number(c.commission_pct ?? Number(c.commission_rate || 0) * 100),
    settle_cycle: c.settle_cycle || 'T+7',
    is_enabled: c.is_enabled !== false && c.is_active !== false,
    note: c.note || '',
    is_zero_commission: !!c.is_zero_commission,
  }))
}

async function load() {
  loading.value = true
  try {
    const hid = hotelStore.hotelId
    const [data, rts] = await Promise.all([
      api.otaCommissionGet(hid),
      api.listRoomTypes(hid).catch(() => []),
    ])
    canEdit.value = !!data.can_edit
    settleCycles.value = data.settle_cycles || settleCycles.value
    rows.value = mapRows(data.channels || [])
    overrides.value = data.overrides || []
    roomTypes.value = (rts || [])
      .map((r: any) => ({ id: Number(r.id), name: String(r.name || '') }))
      .filter((r: { id: number; name: string }) => r.id && r.name)
    if (!ovForm.value.channel_code && rows.value[0]) {
      ovForm.value.channel_code = rows.value[0].channel_code
    }
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function openCreate() {
  if (!canEdit.value) {
    toast(t('当前角色仅可查看，请使用老板 / 财务账号编辑'), false)
    return
  }
  editing.value = false
  form.value = {
    channel_code: '',
    channel_name: '',
    commission_pct: 10,
    settle_cycle: 'T+7',
    note: '',
    is_enabled: true,
  }
  showEditor.value = true
}

function openEdit(r: ChannelRow) {
  if (!canEdit.value) {
    toast(t('当前角色仅可查看，请使用老板 / 财务账号编辑'), false)
    return
  }
  editing.value = true
  form.value = {
    channel_code: r.channel_code,
    channel_name: r.channel_name,
    commission_pct: Number(r.commission_pct),
    settle_cycle: r.settle_cycle || 'T+7',
    note: r.note || '',
    is_enabled: r.is_enabled,
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
}

async function saveOne() {
  if (!canEdit.value) return
  const name = form.value.channel_name.trim()
  const code = form.value.channel_code.trim()
  if (!name) {
    toast(t('请填写渠道名称'), false)
    return
  }
  if (!editing.value && !code) {
    toast(t('请填写渠道编码'), false)
    return
  }
  const pct = Number(form.value.commission_pct)
  if (Number.isNaN(pct) || pct < 0 || pct > 50) {
    toast(t('佣金率须在 0%–50%'), false)
    return
  }
  saving.value = true
  try {
    const res = await api.otaCommissionChannelUpsert(hotelStore.hotelId, {
      channel_code: code,
      channel_name: name,
      commission_pct: pct,
      settle_cycle: form.value.settle_cycle,
      note: form.value.note,
      is_enabled: form.value.is_enabled,
      channel_type: 'ota',
    })
    rows.value = mapRows(res.channels || [])
    showEditor.value = false
    toast(editing.value ? t('渠道已更新') : t('渠道已新增'))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(r: ChannelRow) {
  if (!canEdit.value) {
    toast(t('当前角色不可启用 / 禁用'), false)
    return
  }
  const next = !r.is_enabled
  const tip = next
    ? `确定启用渠道「${r.channel_name}」？`
    : `确定禁用渠道「${r.channel_name}」？未接入的渠道可禁用，列表仍保留。`
  if (!window.confirm(tip)) return
  try {
    const res = await api.otaCommissionChannelEnabled(hotelStore.hotelId, r.channel_code, next)
    rows.value = mapRows(res.channels || [])
    toast(next ? t('已启用') : t('已禁用'))
  } catch (e: any) {
    toast(e?.message || t('操作失败'), false)
  }
}

async function resetDef() {
  if (!canEdit.value) {
    toast(t('当前角色不可重置'), false)
    return
  }
  if (!window.confirm(t('确定将种子渠道佣金重置为调研默认值？自定义新增渠道不会删除。'))) return
  try {
    const res = await api.otaCommissionReset(hotelStore.hotelId)
    rows.value = mapRows(res.channels || [])
    toast(t('已重置为调研默认值'))
  } catch (e: any) {
    toast(e?.message || t('重置失败'), false)
  }
}

function exportJson() {
  const out = rows.value.map((r) => ({
    channel_code: r.channel_code,
    name: r.channel_name,
    commission_rate: Number((Number(r.commission_pct) / 100).toFixed(4)),
    settle_cycle: r.settle_cycle,
    is_enabled: r.is_enabled,
  }))
  const text = JSON.stringify(out, null, 2)
  const download = () => {
    const blob = new Blob([text], { type: 'application/json' })
    const href = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = href
    a.download = 'ota-commission.json'
    a.click()
    URL.revokeObjectURL(href)
    toast(t('已下载 JSON 文件'))
  }
  try {
    if (!navigator.clipboard?.writeText) {
      download()
      return
    }
    void navigator.clipboard.writeText(text).then(
      () => toast(t('已复制 JSON 到剪贴板')),
      () => download(),
    )
  } catch {
    download()
  }
}

function defaultOvChannel() {
  return enabledChannels.value[0]?.channel_code || rows.value[0]?.channel_code || ''
}

function basePctFor(code: string) {
  const r = rows.value.find((x) => x.channel_code === code)
  return r ? Number(r.commission_pct) : null
}

function deltaText(o: any) {
  const delta =
    o.delta_pct != null
      ? Number(o.delta_pct)
      : (() => {
          const base = basePctFor(o.channel_code)
          if (base == null) return null
          return Number(o.commission_pct) - base
        })()
  if (delta == null || Number.isNaN(delta)) return '—'
  if (Math.abs(delta) < 1e-9) return t('与默认相同')
  const n = Math.abs(Number(delta.toFixed(2)))
  return delta > 0 ? `比默认高 ${n}%` : `比默认低 ${n}%`
}

function periodText(o: any) {
  if (!o.effective_from && !o.effective_to) return t('长期有效')
  if (o.effective_from && o.effective_to) return `${o.effective_from} ~ ${o.effective_to}`
  if (o.effective_from) return `${o.effective_from} 起`
  return `至 ${o.effective_to}`
}

function openOvCreate(presetChannel?: string) {
  if (!canEdit.value) {
    toast(t('当前角色仅可查看，请使用老板 / 财务账号编辑'), false)
    return
  }
  if (!rows.value.length) {
    toast(t('请先维护渠道列表'), false)
    return
  }
  ovEditing.value = false
  const code = presetChannel || defaultOvChannel()
  const base = basePctFor(code)
  ovForm.value = {
    id: null,
    channel_code: code,
    room_type_id: '',
    rate_code: '',
    commission_pct: base ?? 12,
    effective_from: '',
    effective_to: '',
    note: '',
    is_enabled: true,
  }
  showOvEditor.value = true
}

function openOvEdit(o: any) {
  if (!canEdit.value) {
    toast(t('当前角色仅可查看，请使用老板 / 财务账号编辑'), false)
    return
  }
  ovEditing.value = true
  ovForm.value = {
    id: Number(o.id),
    channel_code: o.channel_code,
    room_type_id: o.room_type_id || '',
    rate_code: o.rate_code || '',
    commission_pct: Number(o.commission_pct),
    effective_from: o.effective_from || '',
    effective_to: o.effective_to || '',
    note: o.note || '',
    is_enabled: o.is_enabled !== false,
  }
  showOvEditor.value = true
}

function closeOvEditor() {
  showOvEditor.value = false
}

function onOvChannelChange() {
  if (ovEditing.value) return
  const base = basePctFor(ovForm.value.channel_code)
  if (base != null) ovForm.value.commission_pct = base
}

async function saveOverride() {
  if (!canEdit.value) return
  if (!ovForm.value.channel_code) {
    toast(t('请选择渠道'), false)
    return
  }
  const pct = Number(ovForm.value.commission_pct)
  if (Number.isNaN(pct) || pct < 0 || pct > 50) {
    toast(t('覆盖佣金率须在 0%–50%'), false)
    return
  }
  ovSaving.value = true
  try {
    const payload: any = {
      channel_code: ovForm.value.channel_code,
      room_type_id: ovForm.value.room_type_id ? Number(ovForm.value.room_type_id) : null,
      rate_code: ovForm.value.rate_code || null,
      commission_pct: pct,
      effective_from: ovForm.value.effective_from || null,
      effective_to: ovForm.value.effective_to || null,
      note: ovForm.value.note || null,
      is_enabled: ovForm.value.is_enabled,
    }
    if (ovForm.value.id) payload.id = ovForm.value.id
    const res = await api.otaCommissionOverrideSave(hotelStore.hotelId, payload)
    overrides.value = res.overrides || []
    showOvEditor.value = false
    toast(ovEditing.value ? t('覆盖规则已更新') : t('覆盖规则已新增'))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    ovSaving.value = false
  }
}

async function toggleOverride(o: any) {
  if (!canEdit.value) {
    toast(t('当前角色不可停用 / 启用'), false)
    return
  }
  const next = !(o.is_enabled !== false)
  const tip = next
    ? `确定启用该覆盖规则？`
    : `确定停用「${o.channel_name}」的特殊佣金？停用后按渠道默认佣金计算。`
  if (!window.confirm(tip)) return
  try {
    const res = await api.otaCommissionOverrideSave(hotelStore.hotelId, {
      id: o.id,
      channel_code: o.channel_code,
      room_type_id: o.room_type_id || null,
      rate_code: o.rate_code || null,
      commission_pct: Number(o.commission_pct),
      effective_from: o.effective_from || null,
      effective_to: o.effective_to || null,
      note: o.note || null,
      is_enabled: next,
    })
    overrides.value = res.overrides || []
    toast(next ? t('已启用覆盖') : t('已停用覆盖'))
  } catch (e: any) {
    toast(e?.message || t('操作失败'), false)
  }
}

async function removeOverride(o: any) {
  if (!canEdit.value) return
  const label = `${o.channel_name} · ${o.room_type_name || t('全部房型')}`
  if (!window.confirm(t('确定删除覆盖「${label}」？'))) return
  try {
    const res = await api.otaCommissionOverrideDelete(hotelStore.hotelId, o.id)
    overrides.value = res.overrides || []
    toast(t('已删除覆盖'))
  } catch (e: any) {
    toast(e?.message || t('删除失败'), false)
  }
}
</script>

<template>
  <main class="ota-page" :class="{ embedded: props.embedded }">
    <div class="ota-wrap">
      <SystemConfigNav v-if="!props.embedded" />
      <div v-if="!props.embedded" class="ota-head">
        <div>
          <h1 class="ota-title">{{ t('OTA佣金设置') }}</h1>
        </div>
      </div>

      <div class="ota-toolbar">
        <button
          type="button"
          class="btn-primary"
          :disabled="!canEdit || loading"
          @click="openCreate"
        >
          <span class="material-symbols-outlined">add</span>
          {{ t('新增渠道') }}
        </button>
        <button type="button" class="btn-ghost" :disabled="!canEdit || loading" @click="resetDef">
          {{ t('重置默认佣金') }}
        </button>
        <button type="button" class="btn-ghost" :disabled="!rows.length" @click="exportJson">
          {{ t('导出') }}
        </button>
      </div>

      <div class="banner">
        <span class="material-symbols-outlined">gavel</span>
        <div class="tx">
          <b>{{ t('合规红线：') }}</b
          >{{
            t(
              '佣金率为签约 / OTA 后台自选结果，系统不计算、不自动调价；仅老板 / 财务可改。 保存不触发改价或渠道推送。',
            )
          }}
        </div>
      </div>

      <div v-if="!canEdit" class="ro-hint">
        {{ t('当前账号为只读。请使用财务或店长账号编辑。') }}
      </div>

      <section class="ota-card">
        <div class="card-head">
          <h2>
            <span class="material-symbols-outlined ico">account_balance</span>
            {{ t('渠道列表') }}
            <span class="meta"
              >（{{ t('启用') }} {{ enabledCount }} / {{ t('共') }} {{ rows.length }}）</span
            >
          </h2>
        </div>

        <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
        <div v-else class="table-wrap">
          <table class="ota-table">
            <thead>
              <tr>
                <th>{{ t('渠道') }}</th>
                <th>{{ t('渠道编码') }}</th>
                <th>{{ t('基础佣金率') }}</th>
                <th>{{ t('结算周期') }}</th>
                <th>{{ t('状态') }}</th>
                <th>{{ t('说明') }}</th>
                <th class="right">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.channel_code" :class="{ off: !r.is_enabled }">
                <td class="name">{{ r.channel_name }}</td>
                <td class="code">{{ r.channel_code }}</td>
                <td class="num">{{ r.commission_pct }}%</td>
                <td>{{ t(r.settle_cycle) }}</td>
                <td>
                  <span
                    class="tag"
                    :class="{ on: r.is_enabled, zero: r.is_zero_commission && r.is_enabled }"
                  >
                    {{
                      !r.is_enabled
                        ? t('已禁用')
                        : r.is_zero_commission
                          ? t('零佣/直订')
                          : t('抽佣·启用')
                    }}</span
                  >
                </td>
                <td class="muted">{{ r.note || '—' }}</td>
                <td class="right">
                  <div class="ops">
                    <button type="button" class="op" :disabled="!canEdit" @click="openEdit(r)">
                      {{ t('编辑') }}
                    </button>
                    <button
                      type="button"
                      class="op"
                      :disabled="!canEdit || !r.is_enabled"
                      :title="t('为该渠道新增房型/价格代码覆盖')"
                      @click="openOvCreate(r.channel_code)"
                    >
                      {{ t('加覆盖') }}
                    </button>
                    <button
                      type="button"
                      class="op"
                      :class="{ danger: r.is_enabled }"
                      :disabled="!canEdit"
                      @click="toggleEnabled(r)"
                    >
                      {{ r.is_enabled ? t('禁用') : t('启用') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td colspan="7" class="empty">{{ t('暂无渠道，请先新增或重置默认佣金') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="ota-card">
        <div class="card-head ov-head">
          <h2>
            <span class="material-symbols-outlined ico">tune</span>
            {{ t('特殊佣金覆盖') }}
            <span class="meta"
              >（{{ t('启用') }} {{ ovEnabledCount }} / {{ t('共') }} {{ overrides.length }}）</span
            >
          </h2>
          <div class="ov-tools">
            <select v-model="ovFilterChannel" class="sel" :title="t('按渠道筛选')">
              <option value="">{{ t('全部渠道') }}</option>
              <option v-for="r in rows" :key="r.channel_code" :value="r.channel_code">
                {{ r.channel_name }}
              </option>
            </select>
            <button
              type="button"
              class="btn-primary sm"
              :disabled="!canEdit || !rows.length"
              @click="openOvCreate()"
            >
              <span class="material-symbols-outlined">add</span>
              {{ t('新增覆盖') }}
            </button>
          </div>
        </div>
        <div class="table-wrap">
          <table class="ota-table">
            <thead>
              <tr>
                <th>{{ t('渠道') }}</th>
                <th>{{ t('房型') }}</th>
                <th>{{ t('价格代码') }}</th>
                <th>{{ t('覆盖佣金') }}</th>
                <th>{{ t('与默认比') }}</th>
                <th>{{ t('生效期') }}</th>
                <th>{{ t('状态') }}</th>
                <th class="right">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="o in filteredOverrides"
                :key="o.id"
                :class="{ off: o.is_enabled === false }"
              >
                <td class="name">{{ o.channel_name }}</td>
                <td>{{ o.room_type_name || t('全部房型') }}</td>
                <td class="code">{{ o.rate_code || '—' }}</td>
                <td class="num">{{ o.commission_pct }}%</td>
                <td>
                  <span
                    class="delta"
                    :class="{ up: (o.delta_pct ?? 0) > 0, down: (o.delta_pct ?? 0) < 0 }"
                  >
                    {{ deltaText(o) }}</span
                  >
                </td>
                <td class="muted">{{ periodText(o) }}</td>
                <td>
                  <span class="tag" :class="{ on: o.is_enabled !== false }">
                    {{ o.is_enabled === false ? t('已停用') : t('启用中') }}</span
                  >
                </td>
                <td class="right">
                  <div class="ops">
                    <button type="button" class="op" :disabled="!canEdit" @click="openOvEdit(o)">
                      {{ t('编辑') }}
                    </button>
                    <button
                      type="button"
                      class="op"
                      :class="{ danger: o.is_enabled !== false }"
                      :disabled="!canEdit"
                      @click="toggleOverride(o)"
                    >
                      {{ o.is_enabled === false ? t('启用') : t('停用') }}
                    </button>
                    <button
                      type="button"
                      class="op danger"
                      :disabled="!canEdit"
                      @click="removeOverride(o)"
                    >
                      {{ t('删除') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!filteredOverrides.length">
                <td colspan="8" class="empty">
                  {{
                    overrides.length
                      ? t('当前筛选下暂无规则')
                      : t('暂无特殊佣金，各渠道均用上方默认值')
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ editing ? t('编辑渠道') : t('新增渠道') }}</h3>
          <button type="button" class="icon-x" @click="closeEditor">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label>
            {{ t('渠道名称') }}
            <input v-model="form.channel_name" type="text" :placeholder="t('如：携程 / 美团')" />
          </label>
          <label>
            {{ t('渠道编码') }}
            <input
              v-model="form.channel_code"
              type="text"
              :disabled="editing"
              :placeholder="t('如：ota_ctrip')"
            />
          </label>
          <label>
            {{ t('基础佣金率（%）') }}
            <input v-model.number="form.commission_pct" type="number" min="0" max="50" step="0.5" />
          </label>
          <label>
            {{ t('结算周期') }}
            <select v-model="form.settle_cycle">
              <option v-for="c in settleCycles" :key="c" :value="c">{{ t(c) }}</option>
            </select>
          </label>
          <label class="check">
            <input v-model="form.is_enabled" type="checkbox" />
            {{ t('启用该渠道') }}</label
          >
          <label class="full">
            {{ t('说明') }}
            <input v-model="form.note" type="text" :placeholder="t('签约档位 / 备注（可选）')" />
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

    <div v-if="showOvEditor" class="modal-mask" @click.self="closeOvEditor">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ ovEditing ? t('编辑覆盖规则') : t('新增覆盖规则') }}</h3>
          <button type="button" class="icon-x" @click="closeOvEditor">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label>
            {{ t('渠道') }}
            <select v-model="ovForm.channel_code" @change="onOvChannelChange">
              <option v-for="r in rows" :key="r.channel_code" :value="r.channel_code">
                {{ r.channel_name }}（{{ t('默认') }} {{ r.commission_pct }}%）
              </option>
            </select>
          </label>
          <label>
            {{ t('房型') }}
            <select v-model="ovForm.room_type_id">
              <option value="">{{ t('全部房型') }}</option>
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
            </select>
          </label>
          <label>
            {{ t('覆盖佣金率（%）') }}
            <input
              v-model.number="ovForm.commission_pct"
              type="number"
              min="0"
              max="50"
              step="0.5"
            />
          </label>
          <label>
            {{ t('价格代码（可选）') }}
            <input
              v-model="ovForm.rate_code"
              type="text"
              :placeholder="t('促销价代码，没有就留空')"
            />
          </label>
          <label>
            {{ t('生效开始') }}
            <input v-model="ovForm.effective_from" type="date" />
          </label>
          <label>
            {{ t('生效结束') }}
            <input v-model="ovForm.effective_to" type="date" />
          </label>
          <label class="check">
            <input v-model="ovForm.is_enabled" type="checkbox" />
            {{ t('启用该规则') }}</label
          >
          <label class="full">
            {{ t('备注') }}
            <input v-model="ovForm.note" type="text" :placeholder="t('如：套房签约 15%（可选）')" />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" type="button" @click="closeOvEditor">{{ t('取消') }}</button>
          <button class="btn-primary" type="button" :disabled="ovSaving" @click="saveOverride">
            {{ ovSaving ? t('保存中…') : t('保存') }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.ota-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
}
.ota-page.embedded {
  padding: 0;
  background: transparent;
  min-height: 0;
}
.ota-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.ota-page.embedded .ota-wrap {
  max-width: none;
  margin: 0;
  gap: 16px;
}
.ota-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.ota-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.ota-sub {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant, #5b616e);
  max-width: 720px;
}
.ota-sub.embedded-sub {
  margin: 0 0 4px;
}
.ota-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #fdebec;
  border: 1px solid #f5b5b5;
  border-radius: 12px;
  padding: 12px 14px;
}
.banner .material-symbols-outlined {
  color: #c62828;
  font-size: 22px;
}
.banner .tx {
  font-size: 13px;
  line-height: 1.5;
  color: #5b3030;
}
.ro-hint {
  font-size: 13px;
  color: #b26a00;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 10px;
  padding: 10px 14px;
}
.ota-card {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  overflow: hidden;
}
.card-head {
  padding: 14px 20px 0;
}
.card-head.ov-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.ov-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-bottom: 2px;
}
.delta {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
}
.delta.up {
  color: #c62828;
}
.delta.down {
  color: #2e7d32;
}
.card-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--on-surface, #1f2329);
}
.card-head .ico {
  color: var(--primary, #005bbf);
  font-size: 20px;
}
.card-head .meta {
  font-size: 13px;
  font-weight: 500;
  color: var(--on-surface-variant, #5b616e);
}
.table-wrap {
  padding: 8px 8px 12px;
  overflow-x: auto;
}
.ota-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.ota-table th {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
  white-space: nowrap;
}
.ota-table td {
  padding: 14px;
  font-size: 14px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
  vertical-align: middle;
}
.ota-table th.right,
.ota-table td.right {
  text-align: right;
}
.ota-table tbody tr:hover {
  background: var(--surface-container-low, #f2f4f5);
}
.ota-table tbody tr.off {
  opacity: 0.62;
}
.name {
  font-weight: 600;
}
.code,
.num {
  font-family: 'Roboto Mono', ui-monospace, monospace;
}
.muted {
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
}
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--surface-container-high, #e6e8e9);
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.tag.on {
  background: rgba(0, 91, 191, 0.1);
  color: var(--primary, #005bbf);
}
.tag.zero {
  background: rgba(46, 125, 50, 0.12);
  color: #2e7d32;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.inp {
  width: 84px;
  padding: 7px 9px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 13px;
  text-align: right;
}
.inp.mid {
  width: 130px;
  text-align: left;
}
.unit {
  color: var(--on-surface-variant, #5b616e);
  font-size: 12px;
  margin-left: 4px;
}
.sel {
  padding: 7px 9px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.desc {
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
  margin: 0 16px 12px;
  line-height: 1.5;
}
.desc code {
  background: var(--surface-container-low, #f2f4f5);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
}
.btn-primary,
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary {
  border: 1px solid var(--primary, #005bbf);
  background: var(--primary, #005bbf);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(0.96);
}
.btn-ghost {
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: #fff;
  color: var(--on-surface-variant, #5b616e);
}
.btn-ghost:hover:not(:disabled) {
  background: var(--surface-container-low, #f2f4f5);
}
.btn-primary:disabled,
.btn-ghost:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-primary.sm {
  padding: 7px 12px;
  font-size: 12px;
}
.btn-primary .material-symbols-outlined,
.btn-primary.sm .material-symbols-outlined {
  font-size: 18px;
}
.op {
  border: none;
  background: transparent;
  color: var(--primary, #005bbf);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  padding: 0;
}
.op.danger {
  color: #c62828;
}
.op:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.empty {
  text-align: center;
  color: #9aa1ad;
  padding: 36px !important;
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
.modal-body select {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  outline: none;
  font-weight: 400;
  color: var(--on-surface, #1f2329);
  background: #fff;
}
.modal-body input:focus,
.modal-body select:focus {
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
