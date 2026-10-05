<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * ⚙ 定价参数配置（L0-L5 · 活动热度模型 · 红线禁用）
 */
import { computed, reactive, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import { channelLabel } from './labels'

const props = defineProps<{ open: boolean; config: any }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', cfg: any): void
}>()

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
  // 兜底：仅档案主码
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

const form = reactive<any>({
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
})
const staffNo = ref('')

const heatCoeff = computed(() => {
  const heat = Number(form.ev_heat_demo || 0) * Number(form.ev_heat_map || 1)
  const cap = Number(form.ev_cap || 100)
  const capped = Math.min(heat, cap)
  return {
    raw: Math.round(heat * 10) / 10,
    capped: Math.round(capped * 10) / 10,
    hitCap: heat > cap,
  }
})

watch(
  () => props.open,
  (v) => {
    if (v && props.config?.params) {
      Object.assign(form, props.config.params)
      form.ev_cap = 100
      if (form.ev_boom == null) form.ev_boom = 80
      if (form.ev_heat_map == null) form.ev_heat_map = 1.0
      if (form.ev_heat_demo == null) form.ev_heat_demo = 95
      if (form.hol_short == null) form.hol_short = 15
      if (form.hol_mid == null) form.hol_mid = 30
      if (form.hol_long == null) form.hol_long = 45
      staffNo.value = ''
    }
  },
)

async function save() {
  if ((staffNo.value || '').trim().length < 4) {
    toast(t('修改参数须工号 ≥4 位'), false)
    return
  }
  try {
    const cfg = await api.paUpdateConfig(hotelStore.hotelId, {
      params: { ...form, ev_cap: 100 },
      staff_no: staffNo.value.trim(),
    })
    emit('saved', cfg)
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  }
}

function reset() {
  Object.assign(form, {
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
  })
}
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <div class="modal card-clean">
      <div class="head">
        <div>
          <div class="title">{{ t('⚙ 价格助手配置 · 参数与系数') }}</div>
          <div class="sub">{{ t('① 功能级可调 · ② 系统配置护栏只读 · ③ 红线禁用') }}</div>
        </div>
        <button type="button" class="x" @click="emit('close')">×</button>
      </div>

      <div class="pg">{{ t('① 价格助手配置（功能级）') }}</div>

      <div class="sec">
        <div class="ps-head"><span class="lv">L5</span> {{ t('策略与取整') }}</div>
        <div class="row">
          <div class="pn">{{ t('策略档位（激进度）') }}</div>
          <div class="agg">
            <button
              type="button"
              :class="{ on: form.agg === 'conservative' }"
              @click="form.agg = 'conservative'"
            >
              {{ t('保守 ×0.7') }}
            </button>
            <button
              type="button"
              :class="{ on: form.agg === 'balanced' }"
              @click="form.agg = 'balanced'"
            >
              {{ t('均衡 ×1.0') }}
            </button>
            <button
              type="button"
              :class="{ on: form.agg === 'aggressive' }"
              @click="form.agg = 'aggressive'"
            >
              {{ t('激进 ×1.3') }}
            </button>
          </div>
        </div>
        <div class="row">
          <div class="pn">{{ t('取整粒度 / 成本底线') }}</div>
          <input v-model.number="form.round" type="number" :title="t('取整')" />
          <span>{{ t('元 ·') }}</span>
          <input v-model.number="form.cost_pct" type="number" :title="t('成本%')" />
          <span>{{ t('%×基准价') }}</span>
        </div>
      </div>

      <div class="sec">
        <div class="ps-head"><span class="lv">L1</span> {{ t('活动 / 节假日系数') }}</div>
        <div class="annot">
          {{ t('活动溢价%') }} ≈ {{ t('热度') }} × {{ t('灵敏度（示例：热度') }}
          {{ form.ev_heat_demo }} → +{{ heatCoeff.capped }}%），
          节假日另按假期长度系数（短/中/长假）。
        </div>

        <div class="pn block">{{ t('① 活动四档强度锚点') }}</div>
        <div class="row tight">
          <span class="lbl">{{ t('弱') }}</span
          ><input v-model.number="form.ev_weak" type="number" />
          <span class="lbl">{{ t('中') }}</span
          ><input v-model.number="form.ev_mid" type="number" />
          <span class="lbl">{{ t('强') }}</span
          ><input v-model.number="form.ev_strong" type="number" />
          <span class="lbl">{{ t('爆') }}</span
          ><input v-model.number="form.ev_boom" type="number" />
          <span>%</span>
        </div>

        <div class="pn block">{{ t('② 活动热度（示意）与溢价灵敏度') }}</div>
        <div class="row">
          <div class="pn">{{ t('活动热度（示意）') }}</div>
          <input v-model.number="form.ev_heat_demo" type="number" min="0" max="100" />
          <span>{{ t('分') }}</span>
          <span class="heat-out">
            → {{ t('溢价') }} +{{ heatCoeff.capped }}%
            <template v-if="heatCoeff.hitCap">（已受硬上限 +{{ form.ev_cap }}% 约束）</template>
          </span>
        </div>
        <div class="row">
          <div class="pn">{{ t('热度 → 溢价灵敏度') }}</div>
          <input v-model.number="form.ev_heat_map" type="number" step="0.1" min="0.1" max="2" />
          <span>{{ t('%/分') }}</span>
          <span class="vtag a">{{ t('店级可调') }}</span>
        </div>

        <div class="pn block">
          {{ t('③ 假期长度系数') }}
          <div class="pd">{{ t('短假(1天) / 中假(3天) / 长假(7天+)，再乘假日形状') }}</div>
        </div>
        <div class="row tight">
          <span class="lbl">{{ t('短假') }}</span
          ><input v-model.number="form.hol_short" type="number" />
          <span class="lbl">{{ t('中假') }}</span
          ><input v-model.number="form.hol_mid" type="number" />
          <span class="lbl">{{ t('长假') }}</span
          ><input v-model.number="form.hol_long" type="number" />
          <span>%</span>
        </div>

        <div class="row">
          <div class="pn">{{ t('④ 活动触发距离') }}</div>
          <input v-model.number="form.ev_km" type="number" step="0.5" />
          <span>km</span>
          <span class="vtag t">{{ t('阈值') }}</span>
        </div>
        <p class="locked-note">
          🔒 活动因子硬上限 +{{ form.ev_cap }}%（红线，下方只读）；与「相对前日涨幅 +{{
            form.cap_pct
          }}%」独立。
        </p>
      </div>

      <div class="sec">
        <div class="ps-head">
          <span class="lv">L2</span> {{ t('算法规则参数') }}
          <span class="vtag t">{{ t('阈值可配') }}</span>
        </div>
        <div class="row">
          <div class="pn">{{ t('预订进度 涨 / 降阈值') }}</div>
          <input v-model.number="form.pace_up" type="number" step="0.01" />
          <input v-model.number="form.pace_down" type="number" step="0.01" />
        </div>
        <div class="row">
          <div class="pn">{{ t('竞品权重默认值') }}</div>
          <input v-model.number="form.comp_w" type="number" step="0.1" min="0.1" max="1" />
        </div>
        <div class="row">
          <div class="pn">{{ t('单次改价步长 %') }}</div>
          <input v-model.number="form.step_pct" type="number" />
        </div>
      </div>

      <div class="pg sys">{{ t('② 系统配置接管 · 合规护栏（只读）') }}</div>

      <div class="sec sys">
        <div class="ps-head">
          <span class="lv">L3</span> {{ t('合规闸门') }}
          <span class="vtag sys">{{ t('系统配置') }}</span>
        </div>
        <div class="row">
          <div class="pn">{{ t('相对前日涨幅封顶 %') }}</div>
          <input :value="form.cap_pct" type="number" disabled />
          <span class="vtag sys">{{ t('只读') }}</span>
        </div>
        <div class="row">
          <div class="pn">{{ t('净到手下限 ¥') }}</div>
          <input :value="form.n_floor" type="number" disabled />
          <span class="vtag sys">{{ t('只读') }}</span>
        </div>
      </div>

      <div class="sec sys">
        <div class="ps-head">
          <span class="lv">L4</span> {{ t('公平价带') }}
          <span class="vtag sys">{{ t('系统配置') }}</span>
        </div>
        <div class="row">
          <div class="pn">{{ t('事件日 / 平日偏离上限 %') }}</div>
          <input :value="form.fair_ev" type="number" disabled />
          <input :value="form.fair_day" type="number" disabled />
        </div>
      </div>

      <div class="sec sys">
        <div class="ps-head">
          <span class="lv">{{ t('红线') }}</span> {{ t('活动因子硬上限') }}
          <span class="vtag r">{{ t('监管红线') }}</span>
        </div>
        <p class="locked-note">
          任何事件/档位系数不得超过此值；与日环比 +{{ form.cap_pct }}% 是两条独立约束。
        </p>
        <div class="row">
          <div class="pn">{{ t('活动因子硬上限') }}</div>
          <input :value="form.ev_cap" type="number" disabled />
          <span>%</span>
          <span class="vtag r">{{ t('红线') }}</span>
        </div>
      </div>

      <div class="sec">
        <div class="ps-head">
          <span class="lv">{{ t('只读') }}</span> {{ t('渠道佣金率') }}
        </div>
        <p class="ro-note">
          {{ t('价格助手只读引用系统配置佣金，不在此编辑。修改请前往')
          }}<a href="#/a-ai-core/finance-params-float-carry?tab=ota">{{
            t('系统配置 · 财务参数 · OTA佣金')
          }}</a
          >。 挂牌价按净价一致：渠道挂价 = 净到手 ÷ (1 − 佣金率)。
        </p>
        <div class="comm-grid">
          <div v-for="(pct, code) in commissionRows" :key="code" class="comm-item">
            <span>{{ channelLabel(String(code)) }}</span>
            <b>{{ pct }}%</b>
          </div>
        </div>
      </div>

      <div class="foot">
        <input v-model="staffNo" class="staff" :placeholder="t('工号 ≥4 位')" maxlength="16" />
        <button type="button" class="btn btn-ghost" @click="reset">{{ t('恢复默认') }}</button>
        <button type="button" class="btn btn-ghost" @click="emit('close')">{{ t('取消') }}</button>
        <button type="button" class="btn btn-primary" @click="save">{{ t('保存并重算') }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  width: min(680px, 96vw);
  max-height: 90vh;
  overflow: auto;
  padding: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.title {
  font-weight: 700;
  font-size: 15px;
}
.sub {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}
.pg {
  margin: 8px 16px 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: #eef2ff;
  font-size: 12px;
  font-weight: 700;
  color: #3730a3;
}
.pg.sys {
  background: #f1f5f9;
  color: #475569;
}
.sec {
  margin: 10px 16px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.sec.sys {
  background: #f8fafc;
}
.ps-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 10px;
}
.lv {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e0e7ff;
  color: #3730a3;
}
.annot {
  font-size: 12px;
  line-height: 1.55;
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #fff7ed;
  border-radius: 6px;
  border-left: 3px solid #f59e0b;
}
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.row.tight input {
  width: 56px;
}
.pn {
  flex: 1 1 160px;
  font-size: 12px;
  font-weight: 600;
}
.pn.block {
  flex: 1 1 100%;
  margin: 8px 0 4px;
}
.pd {
  font-weight: 400;
  color: var(--on-surface-variant);
  font-size: 11px;
  margin-top: 2px;
}
.lbl {
  font-size: 11px;
  color: var(--on-surface-variant);
}
input[type='number'] {
  width: 72px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
}
input:disabled {
  background: #f1f5f9;
  color: #64748b;
}
.heat-out {
  font-size: 12px;
  color: var(--primary, #005bbf);
  font-weight: 600;
}
.agg {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.agg button {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 16px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.agg button.on {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  font-weight: 600;
}
.vtag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
}
.vtag.m {
  background: #dcfce7;
  color: #16a34a;
}
.vtag.t {
  background: #fef3c7;
  color: #d97706;
}
.vtag.r {
  background: #fee2e2;
  color: #dc2626;
}
.vtag.sys {
  background: #e2e8f0;
  color: #475569;
}
.vtag.a {
  background: #e0e7ff;
  color: #4338ca;
}
.locked-note {
  margin: 0 0 8px;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.55;
}
.ro-note {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.55;
}
.ro-note a {
  color: var(--primary, #005bbf);
  font-weight: 600;
}
.comm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}
.comm-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface-container-low, #f3f4f6);
  font-size: 12px;
}
.comm-item b {
  font-variant-numeric: tabular-nums;
}
.foot {
  display: flex;
  gap: 8px;
  padding: 12px 16px 16px;
  align-items: center;
  flex-wrap: wrap;
  position: sticky;
  bottom: 0;
  background: #fff;
  border-top: 1px solid #e5e7eb;
}
.staff {
  flex: 1;
  min-width: 120px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 13px;
}
</style>
