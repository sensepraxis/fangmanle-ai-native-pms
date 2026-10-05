<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 价格助手参数配置 —— 对齐「全屏页 v2」原型：
 * 场景预设 + 分组参数行（名/说明/控件）
 */
import { computed, reactive, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import { channelLabel } from './labels'

const props = defineProps<{ config: any }>()
const emit = defineEmits<{
  (e: 'saved', cfg: any): void
}>()

const collapsed = ref(false)
const editing = ref(false)
const saving = ref(false)
const scenario = ref<'biz' | 'scenic' | 'new' | 'chain' | 'custom'>('biz')

const DEFAULTS = {
  agg: 'balanced',
  target_occ: 78,
  round: 10,
  cost_pct: 55,
  ev_weak: 15,
  ev_mid: 30,
  ev_strong: 50,
  ev_boom: 80,
  ev_heat_map: 1.0,
  ev_heat_demo: 95,
  hol_short: 15,
  hol_mid: 30,
  hol_long: 45,
  ev_cap: 100,
  ev_km: 5,
  pace_up: 1.1,
  pace_down: 0.9,
  comp_w: 1.0,
  cap_pct: 50,
  n_floor: 240,
  fair_ev: 80,
  fair_day: 30,
  step_pct: 15,
}

const SCENARIOS = {
  biz: {
    label: t('商务为主'),
    emoji: '🏢',
    preview: t('涨幅保守、节奏适中'),
    patch: {
      agg: 'conservative',
      pace_up: 1.15,
      pace_down: 0.85,
      step_pct: 12,
      comp_w: 0.7,
      ev_km: 5,
    },
  },
  scenic: {
    label: t('景区周末'),
    emoji: '🏔',
    preview: t('溢价大胆、依赖活动因子'),
    patch: {
      agg: 'aggressive',
      pace_up: 1.05,
      pace_down: 0.92,
      step_pct: 18,
      comp_w: 0.3,
      ev_km: 10,
    },
  },
  new: {
    label: t('新店试营'),
    emoji: '🌱',
    preview: t('价格保守、优先保出租率'),
    patch: {
      agg: 'conservative',
      pace_up: 1.2,
      pace_down: 0.8,
      step_pct: 10,
      comp_w: 0.5,
      cost_pct: 60,
    },
  },
  chain: {
    label: t('连锁标准'),
    emoji: '🏨',
    preview: t('规则统一、改价保守'),
    patch: { ...DEFAULTS },
  },
} as const

const commissionRows = computed(() => {
  const list = Array.isArray(props.config?.commission_channels)
    ? props.config.commission_channels
    : []
  const out: Record<string, string> = {}
  if (list.length) {
    for (const row of list) {
      const k = String(row.code || '')
      if (!k) continue
      const pct =
        Math.round(Number(row.commission_pct ?? Number(row.commission_rate || 0) * 100) * 100) / 100
      out[k] = String(pct)
        .replace(/\.0+$/, '')
        .replace(/(\.\d*?)0+$/, '$1')
    }
    return out
  }
  const FALLBACK = [
    'direct',
    'ota_ctrip',
    'ota_meituan',
    'ota_fliggy',
    'ota_douyin',
    'ota_tongcheng',
    'ota_elong',
    'jd',
    'member',
    'ota_agoda',
  ]
  const c = props.config?.commission || {}
  for (const k of FALLBACK) {
    if (!(k in c) && k !== 'direct') continue
    const pct = Math.round(Number(c[k] ?? 0) * 10000) / 100
    out[k] = String(pct)
      .replace(/\.0+$/, '')
      .replace(/(\.\d*?)0+$/, '$1')
  }
  return out
})

const form = reactive<any>({ ...DEFAULTS })
const baseline = reactive<any>({ ...DEFAULTS })
const staffNo = ref('')

const heatCoeff = computed(() => {
  // 示例：用 95 分（周杰伦级）灵敏度效果；真实热度在活动台
  const heat = 95 * Number(form.ev_heat_map || 1)
  const cap = Number(form.ev_cap || 100)
  const capped = Math.min(heat, cap)
  return {
    raw: Math.round(heat * 10) / 10,
    capped: Math.round(capped * 10) / 10,
    hitCap: heat > cap,
  }
})

const aggLabel = computed(() => {
  if (form.agg === 'conservative') return t('保守')
  if (form.agg === 'aggressive') return t('激进')
  return t('均衡')
})

const modifiedCount = computed(() => {
  let n = 0
  for (const k of Object.keys(DEFAULTS)) {
    if (Number(form[k]) !== Number(baseline[k]) && String(form[k]) !== String(baseline[k])) n += 1
  }
  return n
})

const scenarioPreviewHtml = computed(() => {
  if (scenario.value === 'custom') {
    return t('当前：<b>自定义</b> · 已手工调整参数')
  }
  const s = SCENARIOS[scenario.value]
  return `当前：<b>${s.label}</b> · ${s.preview}`
})

function syncFromConfig() {
  if (!props.config?.params) return
  Object.assign(form, DEFAULTS, props.config.params)
  form.ev_cap = 100
  Object.assign(baseline, form)
  staffNo.value = ''
  scenario.value = 'custom'
}

watch(
  () => props.config,
  () => {
    if (!editing.value) syncFromConfig()
  },
  { immediate: true, deep: true },
)

function startEdit() {
  syncFromConfig()
  editing.value = true
  collapsed.value = false
}

function cancelEdit() {
  syncFromConfig()
  editing.value = false
}

function applyScenario(key: keyof typeof SCENARIOS) {
  scenario.value = key
  Object.assign(form, DEFAULTS, SCENARIOS[key].patch)
  form.ev_cap = 100
}

function resetField(keys: string[], values: Record<string, number | string>) {
  for (const k of keys) {
    if (k in values) form[k] = values[k]
  }
  scenario.value = 'custom'
}

function onManualChange() {
  scenario.value = 'custom'
}

function reset() {
  Object.assign(form, DEFAULTS)
  scenario.value = 'chain'
}

async function save() {
  if ((staffNo.value || '').trim().length < 4) {
    toast(t('修改参数须工号 ≥4 位'), false)
    return
  }
  saving.value = true
  try {
    const cfg = await api.paUpdateConfig(hotelStore.hotelId, {
      params: { ...form, ev_cap: 100 },
      staff_no: staffNo.value.trim(),
    })
    editing.value = false
    emit('saved', cfg)
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

const commissionSummary = computed(() => {
  const rows = Object.entries(commissionRows.value).slice(0, 6)
  if (!rows.length) return t('暂无佣金数据')
  return rows.map(([code, pct]) => `${channelLabel(code)} ${pct}%`).join(' · ')
})
</script>

<template>
  <div class="params-panel card-clean" :class="{ collapsed, editing }">
    <div class="panel-head">
      <button
        type="button"
        class="chev"
        :aria-expanded="!collapsed"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '▸' : '▾' }}
      </button>
      <div class="panel-title">
        <span class="material-symbols-outlined">tune</span>
        {{ t('价格助手参数配置') }}
      </div>
      <div class="panel-actions">
        <button v-if="!editing" type="button" class="btn btn-ghost sm" @click="startEdit">
          {{ t('编辑') }}
        </button>
        <button v-else type="button" class="btn btn-ghost sm" @click="cancelEdit">
          {{ t('完成') }}
        </button>
      </div>
    </div>

    <div v-if="!collapsed && !editing" class="summary">
      <span class="chip">{{ t('策略') }} {{ aggLabel }}</span>
      <span class="chip">{{ t('取整') }} {{ form.round }} {{ t('元') }}</span>
      <span class="chip">{{ t('成本底线') }} {{ form.cost_pct }}%</span>
      <span class="chip">{{ t('活动硬上限') }} +{{ form.ev_cap }}%</span>
      <span class="chip">{{ t('改价步长') }} {{ form.step_pct }}%</span>
    </div>

    <div v-if="!collapsed && editing" class="edit-shell">
      <!-- 场景预设 -->
      <div class="scenarios">
        <span class="scenarios-label">{{ t('一键应用预设') }}</span>
        <button
          v-for="(s, key) in SCENARIOS"
          :key="key"
          type="button"
          class="scenario"
          :class="{ on: scenario === key }"
          @click="applyScenario(key)"
        >
          <span class="emoji">{{ s.emoji }}</span
          >{{ s.label }}
        </button>
        <span class="scenario-preview" v-html="scenarioPreviewHtml" />
      </div>

      <div class="main">
        <div class="left">
          <!-- ① 策略与取整 -->
          <section class="group">
            <header class="group-head">
              <span class="gnum">①</span>
              <div>
                <div class="gtitle">{{ t('策略与取整') }}</div>
                <div class="gsubtitle">{{ t('定调子 · 决定算法的「性格」') }}</div>
              </div>
              <span class="gtag">{{ t('功能级 · 可改') }}</span>
            </header>
            <div class="params">
              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('响应强度档位') }}</div>
                  <div class="param-desc">
                    {{ t('系统的') }} <b>{{ t('「性格」') }}</b
                    >{{ t('。保守只在信号很强时才动价，激进任何机会都追。') }}
                    <b>{{ t('建议：') }}</b
                    >{{ t('新手先选「均衡」观察 2 周。') }}
                  </div>
                </div>
                <div class="param-input">
                  <select v-model="form.agg" @change="onManualChange">
                    <option value="conservative">{{ t('保守 ×0.7（少动）') }}</option>
                    <option value="balanced">{{ t('均衡 ×1.0（推荐）') }}</option>
                    <option value="aggressive">{{ t('激进 ×1.3（紧追市场）') }}</option>
                  </select>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['agg'], { agg: 'balanced' })"
                  >
                    {{ t('↺ 恢复推荐') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('成本底线') }}</div>
                  <div class="param-desc">
                    {{ t('建议价的') }} <b>{{ t('最低防线') }}</b
                    >{{ t('，低于此线 = 亏本卖。') }} <b>{{ t('建议：') }}</b
                    >{{ t('餐饮酒店 55%，纯房酒店 60%。') }}
                  </div>
                </div>
                <div class="param-input">
                  <span class="unit">{{ t('基准价 ×') }}</span>
                  <input
                    v-model.number="form.cost_pct"
                    type="number"
                    min="0"
                    max="100"
                    @input="onManualChange"
                  />
                  <span class="unit">%</span>
                  <button
                    type="button"
                    class="reco"
                    @click="resetField(['cost_pct'], { cost_pct: 55 })"
                  >
                    {{ t('推荐 55') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['cost_pct'], { cost_pct: 55 })"
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('价格取整粒度') }}</div>
                  <div class="param-desc">
                    {{ t('建议价不出现') }} <b>¥617</b> {{ t('这类零头。') }}
                    <b>{{ t('建议：') }}</b
                    >{{ t('经济型 ¥10，中高端 ¥20。') }}
                  </div>
                </div>
                <div class="param-input">
                  <select v-model.number="form.round" @change="onManualChange">
                    <option :value="1">{{ t('¥1（不取整）') }}</option>
                    <option :value="10">{{ t('¥10（推荐）') }}</option>
                    <option :value="20">¥20</option>
                  </select>
                </div>
                <div class="param-meta">
                  <button type="button" class="reset" @click="resetField(['round'], { round: 10 })">
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- ② 活动/节假日 -->
          <section class="group">
            <header class="group-head">
              <span class="gnum">②</span>
              <div>
                <div class="gtitle">{{ t('活动 / 节假日系数') }}</div>
                <div class="gsubtitle">{{ t('算法因子：演唱会 / 节假日的影响力度') }}</div>
              </div>
              <span class="gtag">{{ t('功能级 · 可改') }}</span>
            </header>
            <div class="params">
              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('四档强度') }}</div>
                  <div class="param-desc">
                    {{ t('事件分成弱 / 中 / 强 / 爆，每档对应一个') }} <b>{{ t('天花板') }}</b
                    >{{ t('。实际系数还要看热度。') }}
                  </div>
                </div>
                <div class="param-input multy">
                  <div class="m-item">
                    <span class="m-label">{{ t('弱') }}</span>
                    <div class="m-input">
                      <input v-model.number="form.ev_weak" type="number" @input="onManualChange" />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('中') }}</span>
                    <div class="m-input">
                      <input v-model.number="form.ev_mid" type="number" @input="onManualChange" />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('强') }}</span>
                    <div class="m-input">
                      <input
                        v-model.number="form.ev_strong"
                        type="number"
                        @input="onManualChange"
                      />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('爆') }}</span>
                    <div class="m-input">
                      <input v-model.number="form.ev_boom" type="number" @input="onManualChange" />
                      <span class="unit">%</span>
                    </div>
                  </div>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="
                      resetField(['ev_weak', 'ev_mid', 'ev_strong', 'ev_boom'], {
                        ev_weak: 15,
                        ev_mid: 30,
                        ev_strong: 50,
                        ev_boom: 80,
                      })
                    "
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('热度 → 溢价灵敏度') }}</div>
                  <div class="param-desc">
                    {{ t('店级旋钮：每一分热度换多少溢价。真实场次热度在「活动台」维护。') }}
                    <b>{{ t('公式：') }}</b
                    >{{ t('活动溢价% = 活动热度 × 灵敏度（再受硬上限约束）。') }}
                    {{ t('例：热度 95 ×') }} {{ form.ev_heat_map }} ≈
                    <b>+{{ heatCoeff.capped }}%</b>
                    <template v-if="heatCoeff.hitCap">{{ t('（已触硬上限）') }}</template
                    >。 <b>{{ t('建议：') }}</b
                    >{{ t('默认 1.0；想少跟风活动就调到 0.5–0.7。') }}
                  </div>
                </div>
                <div class="param-input">
                  <input
                    v-model.number="form.ev_heat_map"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="2"
                    @input="onManualChange"
                  />
                  <span class="unit">{{ t('%/分') }}</span>
                  <button
                    type="button"
                    class="reco"
                    @click="resetField(['ev_heat_map'], { ev_heat_map: 1 })"
                  >
                    {{ t('推荐 1.0') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['ev_heat_map'], { ev_heat_map: 1 })"
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('假期长度系数') }}</div>
                  <div class="param-desc">
                    {{ t('短假 / 中假 / 长假三档，再乘') }} <b>{{ t('逐日形状') }}</b
                    >{{ t('（首尾高、中间略低）。') }} <b>{{ t('例：') }}</b
                    >{{ t('中秋走短假，国庆走长假。') }}
                  </div>
                </div>
                <div class="param-input multy">
                  <div class="m-item">
                    <span class="m-label">{{ t('短假') }}</span>
                    <div class="m-input">
                      <input
                        v-model.number="form.hol_short"
                        type="number"
                        @input="onManualChange"
                      />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('中假') }}</span>
                    <div class="m-input">
                      <input v-model.number="form.hol_mid" type="number" @input="onManualChange" />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('长假') }}</span>
                    <div class="m-input">
                      <input v-model.number="form.hol_long" type="number" @input="onManualChange" />
                      <span class="unit">%</span>
                    </div>
                  </div>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="
                      resetField(['hol_short', 'hol_mid', 'hol_long'], {
                        hol_short: 15,
                        hol_mid: 30,
                        hol_long: 45,
                      })
                    "
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('触发距离') }}</div>
                  <div class="param-desc">
                    {{
                      t(
                        '活动地点到本酒店的距离，小于此值才触发溢价。场次距离在「活动台」维护；此处只调店级阈值。',
                      )
                    }}
                    <b>{{ t('建议：') }}</b
                    >{{ t('5km（城市）/ 10km（度假）。') }}
                  </div>
                </div>
                <div class="param-input">
                  <input
                    v-model.number="form.ev_km"
                    type="number"
                    min="1"
                    max="30"
                    step="0.5"
                    @input="onManualChange"
                  />
                  <span class="unit">km</span>
                  <button type="button" class="reco" @click="resetField(['ev_km'], { ev_km: 5 })">
                    {{ t('推荐 5') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button type="button" class="reset" @click="resetField(['ev_km'], { ev_km: 5 })">
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- ③ 算法规则 -->
          <section class="group">
            <header class="group-head">
              <span class="gnum">③</span>
              <div>
                <div class="gtitle">{{ t('算法规则参数') }}</div>
                <div class="gsubtitle">{{ t('调阈值 · 决定算法「何时出手」') }}</div>
              </div>
              <span class="gtag">{{ t('功能级 · 可改') }}</span>
            </header>
            <div class="params">
              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('预订进度阈值') }}</div>
                  <div class="param-desc">
                    {{
                      t(
                        '已订 ÷ 去年同期。高于上涨阈值 → 热门建议涨价；低于下降阈值 → 冷门建议降价。',
                      )
                    }}
                  </div>
                </div>
                <div class="param-input multy">
                  <div class="m-item">
                    <span class="m-label">{{ t('上涨阈值') }}</span>
                    <div class="m-input">
                      <span class="unit">&gt;</span>
                      <input
                        v-model.number="form.pace_up"
                        type="number"
                        min="1"
                        max="2"
                        step="0.01"
                        @input="onManualChange"
                      />
                    </div>
                  </div>
                  <div class="m-item">
                    <span class="m-label">{{ t('下降阈值') }}</span>
                    <div class="m-input">
                      <span class="unit">&lt;</span>
                      <input
                        v-model.number="form.pace_down"
                        type="number"
                        min="0"
                        max="1"
                        step="0.01"
                        @input="onManualChange"
                      />
                    </div>
                  </div>
                  <button
                    type="button"
                    class="reco"
                    @click="resetField(['pace_up', 'pace_down'], { pace_up: 1.1, pace_down: 0.9 })"
                  >
                    {{ t('推荐 1.10 / 0.90') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['pace_up', 'pace_down'], { pace_up: 1.1, pace_down: 0.9 })"
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('竞品默认权重') }}</div>
                  <div class="param-desc">
                    {{ t('竞品价对建议价的影响权重。') }} <b>{{ t('建议：') }}</b
                    >{{ t('商务区 0.7，景区 0.3（主要看自家）。') }}
                  </div>
                </div>
                <div class="param-input">
                  <input
                    v-model.number="form.comp_w"
                    type="number"
                    min="0.1"
                    max="1"
                    step="0.05"
                    @input="onManualChange"
                  />
                  <button type="button" class="reco" @click="resetField(['comp_w'], { comp_w: 1 })">
                    {{ t('推荐 1.00') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['comp_w'], { comp_w: 1 })"
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>

              <div class="param">
                <div class="param-info">
                  <div class="param-name">{{ t('改价步长') }}</div>
                  <div class="param-desc">
                    {{ t('单次改价的') }} <b>{{ t('最大幅度') }}</b
                    >{{ t('，超过则') }} <b>{{ t('拆分到多日') }}</b
                    >。 <b>{{ t('建议：') }}</b
                    >{{ t('15%（防吓跑客人）。') }}
                  </div>
                </div>
                <div class="param-input">
                  <input
                    v-model.number="form.step_pct"
                    type="number"
                    min="5"
                    max="30"
                    @input="onManualChange"
                  />
                  <span class="unit">%</span>
                  <button
                    type="button"
                    class="reco"
                    @click="resetField(['step_pct'], { step_pct: 15 })"
                  >
                    {{ t('推荐 15') }}
                  </button>
                </div>
                <div class="param-meta">
                  <button
                    type="button"
                    class="reset"
                    @click="resetField(['step_pct'], { step_pct: 15 })"
                  >
                    {{ t('↺ 恢复') }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- ④ 系统护栏 -->
          <section class="group sys">
            <header class="group-head">
              <span class="gnum sys">④</span>
              <div>
                <div class="gtitle">{{ t('系统护栏') }}</div>
                <div class="gsubtitle">
                  {{ t('红线 / 公平 · 只读 · 在「系统配置 → 风控·合规」可改') }}
                </div>
              </div>
              <span class="gtag lock">{{ t('系统配置 · 只读') }}</span>
            </header>
            <div class="params">
              <div class="param locked">
                <div class="param-info">
                  <div class="param-name">{{ t('前日涨幅封顶 🔒') }}</div>
                  <div class="param-desc">{{ t('建议价不得高于昨日 × (1+此值)。') }}</div>
                </div>
                <div class="param-input">
                  <input :value="form.cap_pct" type="number" disabled />
                  <span class="unit">%</span>
                </div>
                <div class="param-meta muted">{{ t('只读') }}</div>
              </div>
              <div class="param locked">
                <div class="param-info">
                  <div class="param-name">{{ t('净到手下限 🔒') }}</div>
                  <div class="param-desc">{{ t('扣除佣金与促销后的到手价下限。') }}</div>
                </div>
                <div class="param-input">
                  <span class="unit">¥</span>
                  <input :value="form.n_floor" type="number" disabled />
                </div>
                <div class="param-meta muted">{{ t('只读') }}</div>
              </div>
              <div class="param locked">
                <div class="param-info">
                  <div class="param-name">{{ t('公平价带 · 事件日 / 平日 🔒') }}</div>
                  <div class="param-desc">{{ t('允许偏离竞品中位的最大幅度。') }}</div>
                </div>
                <div class="param-input">
                  <input :value="form.fair_ev" type="number" disabled />
                  <span class="unit">%</span>
                  <input :value="form.fair_day" type="number" disabled />
                  <span class="unit">%</span>
                </div>
                <div class="param-meta muted">{{ t('只读') }}</div>
              </div>
              <div class="param locked danger">
                <div class="param-info">
                  <div class="param-name bad">{{ t('⚠ 活动因子硬上限 🔒') }}</div>
                  <div class="param-desc bad">
                    {{ t('单个事件因子对基准价的绝对上限，防止被认定为价格欺诈。') }}
                  </div>
                </div>
                <div class="param-input">
                  <input :value="form.ev_cap" type="number" disabled />
                  <span class="unit">%</span>
                </div>
                <div class="param-meta">
                  <span class="danger-tag">{{ t('监管红线') }}</span>
                </div>
              </div>
              <div class="param locked">
                <div class="param-info">
                  <div class="param-name">{{ t('渠道佣金率 🔒') }}</div>
                  <div class="param-desc">{{ commissionSummary }}</div>
                </div>
                <div class="param-input">
                  <span class="unit">{{ Object.keys(commissionRows).length }} 个渠道</span>
                </div>
                <div class="param-meta">
                  <a class="reset" href="#/a-ai-core/finance-params-float-carry?tab=ota">{{
                    t('前往系统配置 →')
                  }}</a>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div class="footer">
        <div class="footer-info">
          <span>
            {{ t('本次已修改') }} <b>{{ modifiedCount }}</b>
            {{ t('项 · 影响约未来 30 天建议价，保存后重算') }}</span
          >
          <input v-model="staffNo" class="staff" :placeholder="t('工号 ≥4 位')" maxlength="16" />
        </div>
        <div class="footer-actions">
          <button type="button" class="btn" @click="reset">{{ t('↺ 恢复默认') }}</button>
          <button type="button" class="btn" @click="cancelEdit">{{ t('取消') }}</button>
          <button type="button" class="btn primary" :disabled="saving" @click="save">
            {{ saving ? t('保存中…') : t('保存并重算建议') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.params-panel {
  --brand: #2b6cd4;
  --brand-light: #eaf1fb;
  --brand-darker: #1e4d99;
  --border: #e5e9f0;
  --text: #1f2937;
  --sub: #6b7280;
  --good: #10b981;
  --bad: #ef4444;
  --lock-bg: #f3f4f6;
  --ai-bg: #fff8e6;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  --shadow-l: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 4px;
  padding: 0;
  overflow: hidden;
  color: var(--text);
}
.params-panel.editing {
  border-color: #c5d0e0;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}
.chev {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--sub);
  width: 20px;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 650;
  font-size: 14px;
}
.panel-title .material-symbols-outlined {
  font-size: 20px;
  color: var(--brand);
}
.panel-actions {
  margin-left: auto;
}
.btn.sm {
  padding: 5px 10px;
  font-size: 12px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 14px 12px;
}
.chip {
  padding: 4px 10px;
  background: #f3f4f6;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.edit-shell {
  border-top: 1px solid var(--border);
  background: #f5f7fa;
}

.scenarios {
  background: linear-gradient(135deg, var(--brand-light) 0%, #fff 100%);
  border-bottom: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.scenarios-label {
  font-size: 12px;
  color: var(--sub);
  font-weight: 600;
}
.scenario {
  padding: 6px 12px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--border);
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  color: var(--text);
}
.scenario:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.scenario.on {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.scenario-preview {
  margin-left: auto;
  font-size: 11px;
  color: var(--sub);
}
.scenario-preview :deep(b) {
  color: var(--brand);
}

.main {
  display: block;
  padding: 16px;
  width: 100%;
  max-width: none;
}
.left {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.group {
  background: #fff;
  border-radius: 10px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.group.sys {
  background: #fafafa;
}
.group-head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
}
.gnum {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.gnum.sys {
  background: #6b7280;
}
.gtitle {
  font-size: 14px;
  font-weight: 650;
}
.gsubtitle {
  font-size: 11px;
  color: var(--sub);
  margin-top: 2px;
}
.gtag {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  background: var(--brand-light);
  color: var(--brand);
  white-space: nowrap;
}
.gtag.lock {
  background: var(--lock-bg);
  color: #6b7280;
}

.param {
  padding: 14px 16px;
  border-bottom: 1px solid #f3f4f6;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, max-content) max-content;
  gap: 12px 20px;
  align-items: center;
}
.param:last-child {
  border-bottom: none;
}
.param:hover {
  background: #fafbfc;
}
.param.locked {
  background: #fafafa;
  opacity: 0.92;
}
.param.danger {
  background: #fef2f2;
}
.param-name {
  font-size: 13px;
  font-weight: 600;
}
.param-name.bad {
  color: var(--bad);
}
.param-desc {
  font-size: 11px;
  color: var(--sub);
  line-height: 1.55;
  margin-top: 4px;
}
.param-desc b {
  color: var(--text);
  font-weight: 600;
}
.param-desc.bad {
  color: #7f1d1d;
}
.param-input {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  justify-self: end;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}
.param-input input[type='number'],
.param-input select {
  width: 72px;
  padding: 7px 8px;
  border: 1px solid var(--border);
  border-radius: 5px;
  font-size: 13px;
  font-weight: 600;
  background: #fff;
  font-family: inherit;
  color: var(--text);
  text-align: right;
}
.param-input select {
  width: auto;
  min-width: 12.5rem;
  max-width: 20rem;
  text-align: left;
  text-align-last: left;
}
.param-input input:focus,
.param-input select:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-light);
}
.param-input input:disabled,
.param-input select:disabled {
  background: var(--lock-bg);
  color: #9ca3af;
}
.unit {
  font-size: 12px;
  color: var(--sub);
}
.reco {
  font-size: 11px;
  color: var(--brand);
  background: var(--brand-light);
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  border: none;
  font-family: inherit;
}
.reco:hover {
  background: var(--brand);
  color: #fff;
}
.param-meta {
  font-size: 11px;
  color: var(--sub);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-self: end;
  gap: 4px;
  text-align: right;
  white-space: nowrap;
  min-width: 7.5rem;
}
.param-meta.muted {
  color: #9ca3af;
}
.reset {
  color: var(--brand);
  cursor: pointer;
  font-size: 11px;
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  text-decoration: none;
}
.reset:hover {
  text-decoration: underline;
}
.danger-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 8px;
  background: #fef2f2;
  color: var(--bad);
  font-weight: 600;
}

.multy {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  align-items: flex-end;
  justify-content: flex-end;
}
.multy .reco {
  align-self: flex-end;
  margin-bottom: 1px;
}
.m-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 0 0 auto;
}
.m-label {
  font-size: 11px;
  color: var(--sub);
}
.m-input {
  display: flex;
  align-items: center;
  gap: 3px;
}
.m-input input {
  width: 56px !important;
  min-width: 56px;
  text-align: right;
}
.param:has(.multy) {
  grid-template-columns: minmax(0, 1fr) minmax(280px, max-content) max-content;
  align-items: start;
}

.footer {
  position: sticky;
  bottom: 0;
  background: #fff;
  border-top: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
  z-index: 2;
}
.footer-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
  color: var(--sub);
  flex: 1;
  min-width: 200px;
}
.footer-info b {
  color: var(--brand);
}
.staff {
  max-width: 160px;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 13px;
  font-family: inherit;
}
.footer-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.btn {
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid var(--border);
  background: #fff;
  font-family: inherit;
  color: var(--text);
}
.btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.btn.primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.btn.primary:hover {
  background: var(--brand-darker);
  color: #fff;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .param,
  .param:has(.multy) {
    grid-template-columns: 1fr;
    gap: 8px;
    align-items: start;
  }
  .param-input,
  .param-meta {
    justify-self: stretch;
    align-items: flex-end;
  }
  .multy {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
