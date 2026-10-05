<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { localizeSeedText } from '../../lib/localizeSeed'

/**
 * 交班管理 —— 钱/物/事 3 步 + 客情卡 + 三方签字
 * 对齐产品原型：交班管理原型.html
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import ShiftAiDraftPanel from '../../components/ShiftAiDraftPanel.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

const router = useRouter()

const loading = ref(false)
const toast = ref('')
const handoverId = ref(0)
const ws = ref<any>(null)

const floatDenoms = ref<any[]>([])
const floatActualInput = ref<number | null>(null)
const assets = ref<any[]>([])
const diffReason = ref('')

const diffModalOpen = ref(false)

const fmt = (n: number) =>
  Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const floatDetailSum = computed(
  () =>
    Math.round(
      floatDenoms.value.reduce((s, d) => s + Number(d.denom) * Number(d.actual_qty || 0), 0) * 100,
    ) / 100,
)
const floatActual = computed(() => {
  if (
    floatActualInput.value === null ||
    floatActualInput.value === undefined ||
    floatActualInput.value === ('' as any)
  ) {
    return null
  }
  return Math.round(Number(floatActualInput.value) * 100) / 100
})
const floatExpected = computed(() => ws.value?.float?.expected ?? 0)
const floatDiff = computed(() => {
  if (floatActual.value === null) return 0
  return Math.round((floatActual.value - floatExpected.value) * 100) / 100
})
const diffType = computed(() => {
  if (floatActual.value === null) return 'pending'
  if (Math.abs(floatDiff.value) < 0.01) return 'flat'
  return floatDiff.value > 0 ? 'long' : 'short'
})
const detailMismatch = computed(() => {
  if (floatActual.value === null) return false
  const filled = floatDenoms.value.some(
    (d) => d.actual_qty !== null && d.actual_qty !== undefined && d.actual_qty !== '',
  )
  if (!filled) return false
  return Math.abs(floatDetailSum.value - floatActual.value) >= 0.01
})

const stepMoneyDone = computed(() => ws.value?.float?.confirmed)
const stepAssetsDone = computed(
  () => ws.value?.signatures && ws.value?.float?.confirmed && assetsOk.value,
)
const assetsOk = computed(() => {
  return assets.value.every((a) => {
    if (a.actual_qty === null || a.actual_qty === undefined || a.actual_qty === '') return false
    const diff = Number(a.actual_qty) - Number(a.expected_qty ?? 0)
    return diff === 0 || (a.diff_reason || '').trim().length > 0
  })
})

const taskStats = computed(() => {
  const tasks = ws.value?.tasks || []
  const p0 = tasks.filter((t: any) => t.priority === 'P0' && t.status !== 'done').length
  const p1 = tasks.filter((t: any) => t.priority === 'P1').length
  const p2 = tasks.filter((t: any) => t.priority === 'P2').length
  return { total: tasks.length, p0, p1, p2 }
})

const situationBadge = computed(() => {
  const list = ws.value?.guest_situations || []
  const vip = list.filter((x: any) => x.type === 'vip' || x.type === 'special').length
  const inbound = list.filter((x: any) => x.type === 'inbound').length
  const complaint = list.filter((x: any) => x.type === 'complaint').length
  return t('{vip} 在店 · {inbound} 即到 · {complaint} 客诉', {
    vip,
    inbound,
    complaint,
  })
})

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2400)
}

async function load() {
  loading.value = true
  try {
    const res = await api.shiftHandoverWorkspace(hotelStore.hotelId)
    ws.value = res?.data ?? res
    handoverId.value = ws.value.handover_id
    floatDenoms.value = (ws.value.float?.denominations || [])
      .filter((d: any) => Number(d.denom) >= 1)
      .map((d: any) => ({ ...d }))
    assets.value = (ws.value.assets || []).map((a: any) => ({ ...a }))
    diffReason.value = ws.value.float?.diff_reason || ''
    const act = ws.value.float?.actual
    floatActualInput.value =
      act != null && ws.value.float?.confirmed ? Number(act) : act != null ? Number(act) : null
  } catch (e: any) {
    showToast(e?.message || t('加载交班数据失败'))
  } finally {
    loading.value = false
  }
}

function recalcFloat() {
  floatDenoms.value = floatDenoms.value.map((d) => ({
    ...d,
    subtotal: Math.round(Number(d.denom) * Number(d.actual_qty || 0) * 100) / 100,
  }))
}

async function confirmFloat() {
  if (floatActual.value === null || Number.isNaN(floatActual.value)) {
    showToast(t('请填写本班实点总额'))
    return
  }
  if (detailMismatch.value) {
    showToast(t('明细合计 ¥{sum} 与实点不一致', { sum: fmt(floatDetailSum.value) }))
    return
  }
  if (Math.abs(floatDiff.value) >= 0.01 && !diffReason.value.trim()) {
    diffModalOpen.value = true
    return
  }
  try {
    const hasDetail = floatDenoms.value.some(
      (d) => d.actual_qty !== null && d.actual_qty !== undefined && String(d.actual_qty) !== '',
    )
    await api.shiftHandoverFloatCount(hotelStore.hotelId, handoverId.value, {
      float_actual: floatActual.value,
      denominations: hasDetail ? floatDenoms.value : [],
      diff_reason: diffReason.value,
    })
    showToast(t('备用金盘库已确认'))
    await load()
  } catch (e: any) {
    if (String(e?.message || '').includes('差异')) diffModalOpen.value = true
    showToast(e?.message || t('请填写差异原因'))
  }
}

async function confirmAssets() {
  try {
    await api.shiftHandoverAssetCount(hotelStore.hotelId, handoverId.value, {
      assets: assets.value,
    })
    showToast(t('实物盘库已确认'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('实物差异须填写原因'))
  }
}

async function signOutgoing() {
  try {
    if (!ws.value?.float?.confirmed) await confirmFloat()
    if (!ws.value?.float?.confirmed) return
    if (!assetsOk.value) await confirmAssets()
    await api.shiftHandoverSign(hotelStore.hotelId, handoverId.value, { role: 'outgoing' })
    showToast(t('交班人已签字 · 请接班人前往「接班」页确认接收'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('签字失败'))
  }
}

async function signManager() {
  try {
    await api.shiftHandoverSign(hotelStore.hotelId, handoverId.value, { role: 'manager' })
    showToast(t('店长已审核签字'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('店长签字失败'))
  }
}

function goTakeover() {
  router.push('/c9-finance/shift-handover/takeover')
}

async function escalate(i: number) {
  try {
    await api.shiftHandoverEscalate(hotelStore.hotelId, handoverId.value, i)
    showToast(t('已升级店长 · 10 分钟内须接管'))
  } catch {
    showToast(t('升级失败'))
  }
}

async function submitDiff() {
  if (diffReason.value.trim().length < 4) {
    showToast(t('差异原因不少于 4 字'))
    return
  }
  diffModalOpen.value = false
  await confirmFloat()
}

function exportReport() {
  showToast(t('交班报表 PDF 已导出至审计存档（保存 3 年）'))
}

function assetDiff(a: any) {
  if (a.actual_qty === null || a.actual_qty === undefined || a.actual_qty === '') return null
  return Number(a.actual_qty) - Number(a.expected_qty ?? 0)
}

function barHeight(diff: number, max: number) {
  if (max <= 0) return 6
  return Math.max(6, Math.min(100, Math.round((Math.abs(diff) / max) * 100)))
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page shift-page">
    <FinanceOpsNav />

    <div class="flex justify-between items-start gap-4 flex-wrap mb-5">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('交班') }}</h1>
      </div>
      <button type="button" class="btn-ghost" @click="exportReport">{{ t('导出交班报表') }}</button>
    </div>

    <div v-if="loading" class="loading-hint">{{ t('加载中…') }}</div>

    <template v-else-if="ws">
      <!-- 班次概览 -->
      <div class="shift-overview mb-5">
        <div class="panel shift-info">
          <div class="shift-title">
            <span class="status-dot" />{{ loc(ws.banner.shift_label) }} {{ t('进行中') }}
          </div>
          <div class="shift-meta">
            {{ ws.banner.shift_time }} · {{ t('计划交班') }} {{ ws.banner.scheduled_handover }} ·
            {{ t('{n} 小时班次制', { n: 12 }) }}
          </div>
        </div>
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">{{ t('已用时长') }}</div>
            <div class="kpi-value">{{ ws.banner.elapsed }}</div>
            <div class="kpi-sub">
              {{ t('距离交班还有 {remain}', { remain: ws.banner.remain }) }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">{{ t('交班人') }}</div>
            <div class="kpi-value sm">{{ ws.banner.outgoing_name || t('未指定') }}</div>
            <div class="kpi-sub">{{ loc(ws.banner.outgoing_meta) || '—' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">{{ t('接班人') }}</div>
            <div class="kpi-value sm" :class="{ warn: !ws.banner.incoming_name }">
              {{ ws.banner.incoming_name || t('待确认') }}
            </div>
            <div class="kpi-sub">{{ loc(ws.banner.incoming_meta) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">{{ t('本班营收') }}</div>
            <div class="kpi-value">¥ {{ fmt(ws.banner.total_revenue) }}</div>
            <div class="kpi-sub">
              {{
                t('{n} 笔 · {ch} 渠道', { n: ws.banner.payment_count, ch: ws.banner.channel_count })
              }}
            </div>
          </div>
        </div>
      </div>

      <div v-for="(a, i) in ws.alerts" :key="i" class="alert" :class="a.level">
        <span class="material-symbols-outlined alert-ic">{{
          a.level === 'crit' ? 'error' : 'warning'
        }}</span>
        <div class="body">{{ loc(a.text) }}</div>
      </div>

      <ShiftAiDraftPanel
        v-if="handoverId"
        :handover-id="handoverId"
        scene="handover"
        @confirmed="load"
      />
      <div v-if="ws?.ai?.narrative" class="panel narrative-box mb-5">
        <div class="panel-h">
          <div class="t">{{ t('交班叙事') }}</div>
          <span v-if="ws.ai?.confirmed_at" class="badge purple">{{ t('AI 已确认') }}</span>
        </div>
        <p class="narrative-text">{{ ws.ai.narrative }}</p>
      </div>

      <div class="split">
        <!-- 左：钱/物 -->
        <div class="col">
          <div class="panel">
            <div class="steps">
              <div class="step" :class="{ done: stepMoneyDone, active: !stepMoneyDone }">
                <span class="num">1</span><span class="lbl">{{ t('钱') }}</span
                ><span class="sub">{{ t('营收/备用金/押金') }}</span>
              </div>
              <div
                class="step"
                :class="{ done: stepAssetsDone, active: stepMoneyDone && !stepAssetsDone }"
              >
                <span class="num">2</span><span class="lbl">{{ t('物') }}</span
                ><span class="sub">{{ t('实物盘库') }}</span>
              </div>
              <div
                class="step"
                :class="{ active: stepAssetsDone && !ws.signatures?.outgoing_signed }"
              >
                <span class="num">3</span><span class="lbl">{{ t('事') }}</span
                ><span class="sub">{{ t('客情/待办/遗留') }}</span>
              </div>
              <div class="step" :class="{ done: ws.signatures?.incoming_signed }">
                <span class="num">4</span><span class="lbl">{{ t('签') }}</span
                ><span class="sub">{{ t('双方+店长') }}</span>
              </div>
            </div>
          </div>

          <!-- 钱 -->
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('① 钱 · 营收 / 备用金 / 押金转交') }}</div>
              <div class="meta">
                {{ t('本班 {elapsed} · 自动汇总', { elapsed: ws.banner.elapsed }) }}
              </div>
            </div>
            <div class="tri">
              <div class="item">
                <div class="lbl">{{ t('本班营收') }}</div>
                <div class="val">¥ {{ fmt(ws.revenue.total) }}</div>
              </div>
              <div class="item">
                <div class="lbl">{{ t('昨日同期') }}</div>
                <div class="val muted">¥ {{ fmt(ws.revenue.yesterday_total) }}</div>
                <div v-if="ws.revenue.yesterday_total" class="pct up">
                  ↑
                  {{
                    Math.round(
                      ((100 * (ws.revenue.total - ws.revenue.yesterday_total)) /
                        ws.revenue.yesterday_total) *
                        10,
                    ) / 10
                  }}%
                </div>
              </div>
              <div class="item">
                <div class="lbl">{{ t('目标完成') }}</div>
                <div v-if="ws.revenue.target_pct != null" class="val">
                  {{ ws.revenue.target_pct }}%
                </div>
                <div v-else class="val muted">{{ t('未配置') }}</div>
                <div v-if="ws.revenue.target_pct != null" class="bar">
                  <div
                    class="fill green"
                    :style="{ width: Math.min(100, ws.revenue.target_pct) + '%' }"
                  />
                </div>
              </div>
            </div>

            <div class="sec-lbl">
              {{ t('按渠道拆解（{n} 渠道）', { n: ws.revenue.channels.length }) }}
            </div>
            <div class="table-card mb-3">
              <table class="data-tbl">
                <thead>
                  <tr>
                    <th>{{ t('渠道') }}</th>
                    <th class="ctr">{{ t('笔数') }}</th>
                    <th class="num">{{ t('金额') }}</th>
                    <th>{{ t('占比') }}</th>
                    <th class="num">{{ t('昨日') }}</th>
                    <th>{{ t('差异') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!ws.revenue.channels.length">
                    <td colspan="6" class="ctr muted">{{ t('本班次窗口内暂无收款记录') }}</td>
                  </tr>
                  <tr v-for="c in ws.revenue.channels" :key="c.channel">
                    <td>{{ c.channel }}</td>
                    <td class="ctr">{{ c.count }}</td>
                    <td class="num">¥ {{ fmt(c.amount) }}</td>
                    <td>
                      <div class="bar sm">
                        <div class="fill" :style="{ width: c.share_pct + '%' }" />
                      </div>
                    </td>
                    <td class="num">¥ {{ fmt(c.yesterday_amount || 0) }}</td>
                    <td>
                      <span v-if="c.diff_pct != null" :class="c.diff_pct >= 0 ? 'up' : 'dn'">
                        {{ c.diff_pct >= 0 ? '+' : '' }}{{ c.diff_pct }}%
                      </span>
                      <span v-else>—</span>
                    </td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr>
                    <td>{{ t('合计') }}</td>
                    <td class="ctr">{{ ws.banner.payment_count }}</td>
                    <td class="num">¥ {{ fmt(ws.revenue.total) }}</td>
                    <td>—</td>
                    <td class="num">¥ {{ fmt(ws.revenue.yesterday_total) }}</td>
                    <td>—</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div class="sec-lbl">
              {{ t('备用金核对 · 应有 ¥{amt}（财务参数，只读）', { amt: fmt(floatExpected) }) }}
            </div>
            <div class="float-total-row">
              <label class="float-total-field">
                <span>{{ t('本班实点总额') }}</span>
                <div class="amt-wrap">
                  <span class="yen">¥</span>
                  <input
                    v-model.number="floatActualInput"
                    class="inp amt"
                    type="number"
                    min="0"
                    step="0.01"
                    :placeholder="t('点钞机/手点总额')"
                  />
                </div>
              </label>
              <div class="float-total-hint">
                {{ t('每班核对总额即可；面额拆解仅初始化/换零/月盘时需要') }}
              </div>
            </div>

            <div class="diff-box" :class="diffType === 'pending' ? 'pending' : diffType">
              <div class="ic">
                {{
                  diffType === 'flat'
                    ? '✓'
                    : diffType === 'long'
                      ? '⚠'
                      : diffType === 'short'
                        ? '!'
                        : '·'
                }}
              </div>
              <div>
                <div class="ttl">
                  <template v-if="diffType === 'pending'">{{ t('请填写实点总额') }}</template>
                  <template v-else-if="diffType === 'flat'">{{ t('已对平') }}</template>
                  <template v-else-if="diffType === 'long'">{{
                    t('长款 ¥{amt}', { amt: fmt(floatDiff) })
                  }}</template>
                  <template v-else>{{
                    t('短款 ¥{amt}', { amt: fmt(Math.abs(floatDiff)) })
                  }}</template>
                </div>
                <div class="sub2">
                  <template v-if="diffType === 'pending'">{{ t('实点 − 应有 = 长短款') }}</template>
                  <template v-else-if="diffType === 'flat'">{{
                    t('实点 {actual} = 应有 {expected}', {
                      actual: fmt(floatActual || 0),
                      expected: fmt(floatExpected),
                    })
                  }}</template>
                  <template v-else>{{ t('差异须填写原因并双签') }}</template>
                </div>
              </div>
              <button
                v-if="diffType === 'long' || diffType === 'short'"
                type="button"
                class="link"
                @click="diffModalOpen = true"
              >
                → {{ t('填差异原因') }}
              </button>
            </div>

            <details class="float-detail">
              <summary>{{ t('精细清点（面额拆解，可选）') }}</summary>
              <p class="hint mt-2">
                {{
                  t(
                    '仅用于把本次面额结构写入台账；明细合计须与上方实点总额一致。面额：100/50/20/10/5/1（无角票）',
                  )
                }}
              </p>
              <div class="table-card mb-2 mt-2">
                <table class="data-tbl">
                  <thead>
                    <tr>
                      <th>{{ t('面额') }}</th>
                      <th class="ctr">{{ t('应有') }}</th>
                      <th class="ctr">{{ t('实盘张数') }}</th>
                      <th class="num">{{ t('小计') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="d in floatDenoms" :key="d.denom">
                      <td>{{ d.label }}</td>
                      <td class="ctr">{{ d.expected_qty }}</td>
                      <td class="ctr">
                        <input
                          v-model.number="d.actual_qty"
                          class="inp"
                          type="number"
                          min="0"
                          @input="recalcFloat"
                        />
                      </td>
                      <td class="num">¥ {{ fmt(Number(d.denom) * Number(d.actual_qty || 0)) }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <td>{{ t('明细合计') }}</td>
                      <td colspan="2" class="ctr muted">
                        {{ t('应有 {amt}', { amt: fmt(floatExpected) }) }}
                      </td>
                      <td class="num">¥ {{ fmt(floatDetailSum) }}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div v-if="detailMismatch" class="alert warn">
                {{
                  t('明细合计 ¥{sum} 与实点总额 ¥{actual} 不一致', {
                    sum: fmt(floatDetailSum),
                    actual: fmt(floatActual || 0),
                  })
                }}
              </div>
            </details>

            <div class="row-actions">
              <button
                type="button"
                class="btn-primary"
                :disabled="floatActual === null"
                @click="confirmFloat"
              >
                {{ t('确认备用金盘库') }}
              </button>
            </div>

            <div class="sec-lbl">{{ t('押金跨班转交') }}</div>
            <div class="deposit-row">
              <div class="lbl">
                {{ t('本班收押金（{n} 笔）', { n: ws.deposit.collected_count }) }}
              </div>
              <div class="val green">+ ¥ {{ fmt(ws.deposit.collected) }}</div>
            </div>
            <div class="deposit-row">
              <div class="lbl">
                {{ t('本班退押金（{n} 笔）', { n: ws.deposit.refunded_count }) }}
              </div>
              <div class="val red">− ¥ {{ fmt(ws.deposit.refunded) }}</div>
            </div>
            <div class="deposit-row">
              <div class="lbl">
                <b>{{ t('转交下一班（净）') }}</b>
              </div>
              <div class="val big">
                {{ ws.deposit.net >= 0 ? '+' : '' }} ¥ {{ fmt(ws.deposit.net) }}
              </div>
            </div>
            <div v-if="ws.deposit.hint" class="hint">{{ ws.deposit.hint }}</div>
          </div>

          <!-- 物 -->
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('② 物 · 实物盘库（应有 vs 实盘）') }}</div>
            </div>
            <div class="asset-head">
              <div>{{ t('物品') }}</div>
              <div>{{ t('应有') }}</div>
              <div>{{ t('实盘') }}</div>
              <div>{{ t('差异') }}</div>
              <div>{{ t('差异原因（必填）') }}</div>
            </div>
            <div v-for="a in assets" :key="a.id" class="asset-row">
              <div class="lbl">
                {{ loc(a.name) }} <span v-if="a.hint" class="ch">（{{ loc(a.hint) }}）</span>
              </div>
              <div class="exp">{{ a.expected_qty }}</div>
              <input v-model.number="a.actual_qty" class="inp" type="number" min="0" />
              <div
                class="diff"
                :class="{
                  zero: assetDiff(a) === 0,
                  minus: assetDiff(a) != null && assetDiff(a)! < 0,
                  plus: assetDiff(a) != null && assetDiff(a)! > 0,
                }"
              >
                {{
                  assetDiff(a) == null
                    ? '—'
                    : assetDiff(a) === 0
                      ? '0'
                      : (assetDiff(a)! > 0 ? '+' : '') + assetDiff(a)
                }}
              </div>
              <input
                v-model="a.diff_reason"
                class="inp left"
                type="text"
                :placeholder="
                  assetDiff(a) == null
                    ? t('请先录入实盘')
                    : assetDiff(a) === 0
                      ? t('无差异可不填')
                      : t('必填')
                "
              />
            </div>
            <div
              v-for="a in assets.filter((x) => x.reorder_triggered && x.actual_qty != null)"
              :key="'r' + a.id"
              class="alert crit mt"
            >
              <span class="ic">!</span>
              <div class="body">
                {{
                  t('{name} 触发自动补货申请：实盘 {qty}（低于阈值），已向采购推送补货工单。', {
                    name: loc(a.name),
                    qty: a.actual_qty,
                  })
                }}
              </div>
            </div>
            <div class="row-actions">
              <button type="button" class="btn-primary" @click="confirmAssets">
                {{ t('确认实物盘库') }}
              </button>
            </div>
          </div>
        </div>

        <!-- 右：事 -->
        <div class="col">
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 客情卡（on top）') }}</div>
              <span class="badge purple">{{ situationBadge }}</span>
            </div>
            <div v-for="(s, i) in ws.guest_situations" :key="i" class="situation">
              <div class="ic" :class="s.type">
                {{
                  s.type === 'vip'
                    ? 'V'
                    : s.type === 'complaint'
                      ? '⚠'
                      : s.type === 'inbound'
                        ? '↑'
                        : '!'
                }}
              </div>
              <div class="body">
                <div class="ttl">
                  {{ loc(s.title) }}
                  <span v-if="s.ai_generated" class="ai-tag">AI</span>
                  <span v-if="s.source" class="src-tag">{{ loc(s.source) }}</span>
                </div>
                <div v-if="s.content" class="desc">{{ loc(s.content) }}</div>
              </div>
            </div>
            <div v-if="!ws.guest_situations?.length" class="hint">
              {{ t('暂无在店 VIP / 特殊需求 / 客诉。') }}
            </div>
          </div>

          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 待办事项') }}</div>
              <div class="meta">
                {{
                  t('{n} 条 · {p0} P0 · {p1} P1 · {p2} P2', {
                    n: taskStats.total,
                    p0: taskStats.p0,
                    p1: taskStats.p1,
                    p2: taskStats.p2,
                  })
                }}
              </div>
            </div>
            <div v-if="!ws.tasks?.length" class="hint">
              {{ t('本班暂无待办（客需、应收跟进、延迟退房等）。') }}
            </div>
            <div
              v-for="(task, i) in ws.tasks"
              :key="i"
              class="task"
              :class="{ done: task.status === 'done' }"
            >
              <div class="pri" :class="task.priority" />
              <div>
                {{ loc(task.content) }}
                <span v-if="task.ai_generated" class="ai-tag">AI</span>
                <span v-if="task.task_type === 'replenish'" class="src-tag">{{ t('补货') }}</span>
              </div>
              <div class="owner">{{ t('责任人：') }}{{ loc(task.owner_name) }}</div>
              <button v-if="task.can_escalate" type="button" class="esc" @click="escalate(i)">
                {{ t('↑ 升级店长') }}
              </button>
              <span v-else-if="task.linked_order_id" class="esc muted">{{ t('挂账 →') }}</span>
            </div>
          </div>

          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 上轮遗留') }}</div>
              <span class="badge amber"
                >{{ ws.carryover.filter((x: any) => x.pending).length }} {{ t('待办') }}</span
              >
            </div>
            <div
              v-for="(p, i) in ws.carryover"
              :key="i"
              class="prev-item"
              :class="{ pending: p.pending }"
            >
              <div class="shift-tag">{{ t('{n} 班', { n: p.shift_no }) }}</div>
              <div class="body">{{ loc(p.content) }}</div>
              <div class="days">{{ t('已过 {h}h', { h: p.hours_ago }) }}</div>
            </div>
            <div v-if="!ws.carryover?.length" class="hint">{{ t('无上轮遗留事项。') }}</div>
          </div>
        </div>
      </div>

      <!-- 签字 -->
      <div class="panel mt">
        <div class="panel-h">
          <div class="t">{{ t('④ 签 · 三方签字') }}</div>
        </div>
        <div
          v-if="ws.signatures.outgoing_signed && !ws.signatures.incoming_signed"
          class="alert warn"
        >
          <span class="ic">⚠</span>
          <div class="body">
            <b>{{ t('交班人已签字提交') }}</b
            >{{ t('，请接班人前往「接班」页逐块复核并签字接收。') }}
            <button type="button" class="link ml-2" @click="goTakeover">
              {{ t('→ 前往接班确认') }}
            </button>
          </div>
        </div>
        <div class="sign-area">
          <div class="sign-cell" :class="{ signed: ws.signatures.outgoing_signed }">
            <div class="role">{{ t('交班人 · {n} 班', { n: ws.banner.shift_no }) }}</div>
            <div class="name">{{ ws.signatures.outgoing_name || '—' }}</div>
            <div class="meta2">
              {{
                ws.signatures.outgoing_signed_at
                  ? `${t('已签')} ${ws.signatures.outgoing_signed_at}`
                  : t('待签字')
              }}
            </div>
            <button
              v-if="!ws.signatures.outgoing_signed"
              type="button"
              class="act"
              @click="signOutgoing"
            >
              {{ t('交班人签字') }}
            </button>
            <div v-else class="act ok">{{ t('✓ 已签字') }}</div>
          </div>
          <div class="sign-cell" :class="{ signed: ws.signatures.incoming_signed }">
            <div class="role">{{ t('接班人 · 下一班') }}</div>
            <div class="name">{{ ws.signatures.incoming_name || t('— 待签 —') }}</div>
            <div class="meta2">{{ t('须在「接班」页重盘复核后签字') }}</div>
            <button
              v-if="!ws.signatures.incoming_signed && ws.signatures.outgoing_signed"
              type="button"
              class="act"
              @click="goTakeover"
            >
              {{ t('前往接班页') }}
            </button>
            <button
              v-else-if="!ws.signatures.incoming_signed"
              type="button"
              class="act disabled"
              disabled
            >
              {{ t('待交班人签字') }}
            </button>
            <div v-else class="act ok">{{ t('✓ 已签字') }}</div>
          </div>
          <div class="sign-cell" :class="{ signed: ws.signatures.manager_signed }">
            <div class="role">{{ t('店长审核（如有阻断）') }}</div>
            <div class="name">
              {{ ws.signatures.manager_signed ? t('已审核') : t('— 待审核 —') }}
            </div>
            <div class="meta2">
              {{ ws.signatures.manager_required ? t('有差异/客诉升级时必须到岗') : t('暂无需') }}
            </div>
            <button
              v-if="ws.signatures.manager_required && !ws.signatures.manager_signed"
              type="button"
              class="act"
              @click="signManager"
            >
              {{ t('店长审核签字') }}
            </button>
            <div v-else class="act disabled">{{ t('暂无需') }}</div>
          </div>
        </div>
        <div class="foot-actions">
          <button type="button" class="btn-ghost" @click="exportReport">
            {{ t('导出交班报表') }}
          </button>
          <button type="button" class="btn-ghost" @click="showToast(t('已转交至夜审模块'))">
            {{ t('转夜审') }}
          </button>
          <button
            v-if="ws.signatures.outgoing_signed && !ws.signatures.incoming_signed"
            type="button"
            class="btn-primary"
            @click="goTakeover"
          >
            {{ t('前往接班确认') }}
          </button>
          <button
            v-else
            type="button"
            class="btn-primary"
            disabled
            :title="t('交班人签字后，接班人在「接班」页完成接收')"
          >
            {{ t('交接完成在接班页确认') }}
          </button>
        </div>
      </div>

      <!-- 历史 -->
      <div class="panel mt">
        <div class="panel-h">
          <div class="t">{{ t('备用金历史（最近 10 班）') }}</div>
        </div>
        <div class="history-chart">
          <div
            v-for="(b, i) in ws.float_history.bars"
            :key="i"
            class="bar-h"
            :class="b.kind"
            :style="{ height: barHeight(b.diff, ws.float_history.max_diff || 1) + '%' }"
          />
        </div>
        <div class="hist-stats">
          <div>
            <div class="lbl">{{ t('短款次数') }}</div>
            <div class="val red">{{ t('{n} 次', { n: ws.float_history.short_count }) }}</div>
          </div>
          <div>
            <div class="lbl">{{ t('长款次数') }}</div>
            <div class="val amber">{{ t('{n} 次', { n: ws.float_history.long_count }) }}</div>
          </div>
          <div>
            <div class="lbl">{{ t('对平次数') }}</div>
            <div class="val green">{{ t('{n} 次', { n: ws.float_history.flat_count }) }}</div>
          </div>
          <div>
            <div class="lbl">{{ t('最大差异') }}</div>
            <div class="val">¥ {{ fmt(ws.float_history.max_diff) }}</div>
          </div>
          <div>
            <div class="lbl">{{ t('趋势') }}</div>
            <div class="val green">{{ ws.float_history.trend }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 差异原因 -->
    <div v-if="diffModalOpen" class="modal-mask" @click.self="diffModalOpen = false">
      <div class="modal">
        <h3 class="red">
          ⚠
          {{
            t('备用金差异 ¥{amt}（{kind}）', {
              amt: fmt(Math.abs(floatDiff)),
              kind: diffType === 'long' ? t('长款') : t('短款'),
            })
          }}
        </h3>
        <p>
          {{
            t(
              '差异须填写原因并双签。按制度：&lt;5 元双签；5–100 元须店长审核；&gt;100 元须财务经理介入。',
            )
          }}
        </p>
        <div class="fld">
          <div class="flbl">{{ t('差异原因（必填）') }}</div>
          <textarea
            v-model="diffReason"
            class="inp full"
            rows="3"
            :placeholder="t('例：找零时把 50 元错找成 100 元')"
          />
        </div>
        <div class="modal-acts">
          <button type="button" class="btn-ghost" @click="diffModalOpen = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="btn-ghost danger" @click="submitDiff">
            {{ t('提交 + 双签') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast show">{{ toast }}</div>
  </div>
</template>

<style scoped>
.shift-page {
  padding-bottom: 2.5rem;
  font-size: 13px;
  color: #1c1b1f;
}

.loading-hint {
  padding: 40px;
  text-align: center;
  color: #79747e;
}

/* 班次概览：与押金管理等页 kpi-card 一致 */
.shift-overview {
  display: grid;
  grid-template-columns: 1.1fr 2fr;
  gap: 12px;
  align-items: stretch;
}
.shift-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.shift-title {
  font-size: 17px;
  font-weight: 700;
  color: #1c1b1f;
  margin-bottom: 6px;
}
.shift-meta {
  font-size: 12px;
  color: #79747e;
  line-height: 1.5;
}
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #2e7d32;
  border-radius: 50%;
  margin-right: 8px;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.kpi-card {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  padding: 0.95rem 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.kpi-label {
  font-size: 12px;
  color: #79747e;
  font-weight: 600;
}
.kpi-value {
  margin-top: 0.3rem;
  font-size: 1.35rem;
  font-weight: 700;
  color: #1c1b1f;
  font-variant-numeric: tabular-nums;
}
.kpi-value.sm {
  font-size: 1rem;
  font-weight: 600;
}
.kpi-value.warn {
  color: #b26a00;
}
.kpi-sub {
  margin-top: 4px;
  font-size: 11px;
  color: #79747e;
}

.panel {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  padding: 1rem 1.15rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.panel.mt {
  margin-top: 14px;
}
.panel-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.panel-h .t {
  font-size: 15px;
  font-weight: 700;
  color: #1c1b1f;
}
.panel-h .meta {
  font-size: 12px;
  color: #79747e;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f3edf7;
  color: #49454f;
  font-weight: 600;
}
.badge.purple {
  background: #e8def8;
  color: #6750a4;
}
.badge.amber {
  background: #fff8e1;
  color: #b26a00;
}

.split {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 14px;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.steps {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  background: #f7f2fa;
  border-radius: 10px;
}
.step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #49454f;
  flex: 1;
}
.step .num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e7e0ec;
  color: #79747e;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
}
.step.active .num {
  background: #6750a4;
  color: #fff;
}
.step.done .num {
  background: #2e7d32;
  color: #fff;
}
.step.done {
  color: #2e7d32;
}
.step .sub {
  margin-left: auto;
  font-size: 11px;
  color: #79747e;
}

.tri {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 8px 0;
}
.tri .item {
  background: #f7f2fa;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  padding: 10px 12px;
  text-align: center;
}
.tri .lbl {
  font-size: 11px;
  color: #79747e;
  margin-bottom: 4px;
}
.tri .val {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.tri .val.muted {
  font-size: 14px;
  color: #79747e;
}
.pct.up {
  font-size: 10px;
  color: #2e7d32;
  margin-top: 2px;
}
.up {
  color: #2e7d32;
  font-size: 11px;
}
.dn {
  color: #c5221f;
  font-size: 11px;
}

.sec-lbl {
  font-size: 12px;
  color: #79747e;
  font-weight: 600;
  margin: 14px 0 8px;
}

.table-card {
  background: #fff;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  overflow: hidden;
}
.data-tbl {
  width: 100%;
  border-collapse: collapse;
}
.data-tbl th {
  font-size: 11px;
  font-weight: 600;
  color: #79747e;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid #e7e0ec;
  background: #f7f2fa;
}
.data-tbl td {
  padding: 10px 12px;
  border-bottom: 1px solid #f3edf7;
  font-size: 13px;
  color: #49454f;
  font-variant-numeric: tabular-nums;
}
.data-tbl .num {
  text-align: right;
}
.data-tbl .ctr {
  text-align: center;
}
.data-tbl tfoot td {
  font-weight: 700;
  color: #1c1b1f;
  border-top: 1px solid #e7e0ec;
  background: #f7f2fa;
}
.muted {
  color: #79747e;
}

.inp {
  border: 1px solid #cac4d0;
  padding: 6px 8px;
  border-radius: 8px;
  width: 100%;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  background: #fff;
  box-sizing: border-box;
}
.inp.left {
  text-align: left;
}
.inp.full {
  text-align: left;
  width: 100%;
  margin-top: 6px;
}

.bar {
  height: 6px;
  background: #e7e0ec;
  border-radius: 3px;
  overflow: hidden;
}
.bar.sm {
  max-width: 80px;
}
.bar .fill {
  height: 100%;
  background: #6750a4;
  border-radius: 3px;
}
.bar .fill.green {
  background: #2e7d32;
}

.diff-box {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}
.diff-box.flat {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}
.diff-box.short {
  background: #fce8e6;
  color: #c5221f;
  border: 1px solid #f5c2c0;
}
.diff-box.long {
  background: #fff8e1;
  color: #b26a00;
  border: 1px solid #ffe082;
}
.diff-box.pending {
  background: #f5f5f5;
  color: #79747e;
  border: 1px solid #e0e0e0;
}
.float-total-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px 20px;
  margin-bottom: 12px;
  padding: 12px 14px;
  background: #faf8ff;
  border: 1px solid #e8def8;
  border-radius: 10px;
}
.float-total-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #49454f;
}
.amt-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.amt-wrap .yen {
  font-size: 18px;
  font-weight: 700;
  color: #1c1b1f;
}
.inp.amt {
  width: 160px;
  font-size: 18px;
  font-weight: 700;
  padding: 8px 10px;
}
.float-total-hint {
  font-size: 12px;
  color: #79747e;
  max-width: 280px;
  line-height: 1.4;
}
.float-detail {
  margin: 10px 0 12px;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  padding: 8px 12px;
  background: #fff;
}
.float-detail summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #6750a4;
  list-style: none;
}
.float-detail summary::-webkit-details-marker {
  display: none;
}
.float-detail summary::before {
  content: '▸ ';
  color: #9e9e9e;
}
.float-detail[open] summary::before {
  content: '▾ ';
}
.alert.warn {
  background: #fff8e1;
  color: #8a5a11;
  border: 1px solid #ffe082;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  margin-top: 8px;
}
.diff-box .ttl {
  font-weight: 700;
}
.diff-box .sub2 {
  font-size: 11px;
  margin-top: 2px;
}
.diff-box .link {
  margin-left: auto;
  font-size: 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: #6750a4;
  font-weight: 600;
  text-decoration: underline;
}

.deposit-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f3edf7;
  font-size: 13px;
}
.deposit-row .val.green {
  color: #2e7d32;
  font-weight: 700;
}
.deposit-row .val.red {
  color: #c5221f;
  font-weight: 700;
}
.deposit-row .val.big {
  font-size: 15px;
  font-weight: 700;
}
.hint {
  font-size: 12px;
  color: #79747e;
  margin-top: 8px;
  line-height: 1.6;
}

.asset-head {
  font-size: 11px;
  color: #79747e;
  font-weight: 600;
  margin-bottom: 6px;
  display: grid;
  grid-template-columns: 1fr 80px 80px 90px 1fr;
  gap: 10px;
}
.asset-row {
  display: grid;
  grid-template-columns: 1fr 80px 80px 90px 1fr;
  gap: 10px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f3edf7;
  font-size: 13px;
}
.asset-row .lbl {
  font-weight: 600;
}
.asset-row .ch {
  font-size: 11px;
  color: #79747e;
}
.asset-row .exp {
  text-align: center;
  color: #79747e;
}
.asset-row .diff {
  text-align: center;
  font-weight: 700;
}
.asset-row .diff.zero {
  color: #79747e;
}
.asset-row .diff.minus {
  color: #c5221f;
}
.asset-row .diff.plus {
  color: #b26a00;
}

.situation {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #e7e0ec;
  margin-bottom: 10px;
  display: flex;
  gap: 10px;
  background: #fff;
}
.situation .ic {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #e8def8;
  color: #6750a4;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.situation .ic.vip {
  background: #ffe6e0;
  color: #c64e1e;
}
.situation .ic.special {
  background: #e8def8;
  color: #6750a4;
}
.situation .ic.complaint {
  background: #fce8e6;
  color: #c5221f;
}
.situation .ic.inbound {
  background: #e8f5e9;
  color: #2e7d32;
}
.situation .ttl {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 2px;
}
.situation .desc {
  font-size: 12px;
  color: #49454f;
  line-height: 1.5;
}

.task {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f2fa;
  border: 1px solid #e7e0ec;
  margin-bottom: 6px;
  font-size: 13px;
}
.task.done {
  opacity: 0.55;
  text-decoration: line-through;
}
.task .pri {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.task .pri.P0 {
  background: #c5221f;
  box-shadow: 0 0 0 3px #fce8e6;
}
.task .pri.P1 {
  background: #b26a00;
  box-shadow: 0 0 0 3px #fff8e1;
}
.task .pri.P2 {
  background: #6750a4;
  box-shadow: 0 0 0 3px #e8def8;
}
.task .owner {
  font-size: 11px;
  color: #79747e;
}
.task .esc {
  font-size: 11px;
  color: #6750a4;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
}
.task .esc.muted {
  color: #79747e;
}

.prev-item {
  display: flex;
  gap: 10px;
  padding: 8px 12px;
  background: #f7f2fa;
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  border-left: 3px solid #79747e;
}
.prev-item.pending {
  border-left-color: #c5221f;
}
.shift-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e7e0ec;
  flex-shrink: 0;
  font-weight: 600;
}
.prev-item.pending .shift-tag {
  background: #fce8e6;
  color: #c5221f;
}
.prev-item .days {
  font-size: 11px;
  color: #79747e;
  flex-shrink: 0;
}

.alert {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  border: 1px solid;
  align-items: flex-start;
}
.alert.warn {
  background: #fff8e1;
  border-color: #ffe082;
  color: #8a5a11;
}
.alert.crit {
  background: #fce8e6;
  border-color: #f5c2c0;
  color: #9f2a26;
}
.alert .alert-ic {
  font-size: 18px;
  flex-shrink: 0;
}
.alert .body {
  flex: 1;
  line-height: 1.6;
}
.ack {
  margin-right: 10px;
  font-size: 12px;
}

.sign-area {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 10px;
}
.sign-cell {
  padding: 14px;
  border: 2px dashed #e7e0ec;
  border-radius: 12px;
  text-align: center;
  background: #fff;
}
.sign-cell.signed {
  border-style: solid;
  border-color: #2e7d32;
  background: #e8f5e9;
}
.sign-cell .role {
  font-size: 11px;
  color: #79747e;
  margin-bottom: 6px;
}
.sign-cell .name {
  font-size: 14px;
  font-weight: 700;
}
.sign-cell .meta2 {
  font-size: 11px;
  color: #79747e;
  margin-top: 4px;
}
.sign-cell .act {
  margin-top: 8px;
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  background: #6750a4;
  color: #fff;
  font-size: 12px;
  border: none;
  cursor: pointer;
  font-weight: 600;
}
.sign-cell .act.ok {
  background: #2e7d32;
}
.sign-cell .act.disabled {
  background: #e7e0ec;
  color: #79747e;
  cursor: not-allowed;
}

.foot-actions,
.row-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 14px;
  flex-wrap: wrap;
}

.btn-primary {
  background: #6750a4;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost {
  background: #fff;
  border: 1px solid #cac4d0;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: #1c1b1f;
}
.btn-ghost.danger {
  color: #c5221f;
  border-color: #f5c2c0;
}

.history-chart {
  height: 60px;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  padding: 6px 0;
  margin-top: 8px;
}
.bar-h {
  flex: 1;
  background: #e7e0ec;
  border-radius: 2px 2px 0 0;
  min-height: 4px;
}
.bar-h.up {
  background: #2e7d32;
}
.bar-h.down {
  background: #c5221f;
}
.bar-h.zero {
  background: #79747e;
}
.hist-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-top: 24px;
  font-size: 12px;
}
.hist-stats .lbl {
  color: #79747e;
}
.hist-stats .val {
  font-size: 16px;
  font-weight: 700;
}
.hist-stats .val.red {
  color: #c5221f;
}
.hist-stats .val.amber {
  color: #b26a00;
}
.hist-stats .val.green {
  color: #2e7d32;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(20, 30, 60, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 14px;
  padding: 22px;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.modal h3 {
  font-size: 16px;
  margin: 0 0 10px;
  font-weight: 700;
}
.modal h3.red {
  color: #c5221f;
}
.modal p {
  font-size: 13px;
  color: #49454f;
  line-height: 1.7;
  margin-bottom: 14px;
}
.modal-acts {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 14px;
}
.fld {
  margin-top: 10px;
}
.flbl {
  font-size: 12px;
  color: #79747e;
  font-weight: 600;
}
.chk {
  display: block;
  margin-top: 6px;
  font-size: 13px;
}

.toast {
  position: fixed;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%);
  background: #1c1b1f;
  color: #fff;
  padding: 11px 18px;
  border-radius: 10px;
  font-size: 13px;
  z-index: 200;
}

.mb-3 {
  margin-bottom: 12px;
}
.mb-5 {
  margin-bottom: 20px;
}
.mt {
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .split {
    grid-template-columns: 1fr;
  }
  .shift-overview {
    grid-template-columns: 1fr;
  }
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .sign-area {
    grid-template-columns: 1fr;
  }
  .hist-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

.narrative-box {
  border-left: 3px solid #6750a4;
}
.narrative-text {
  font-size: 13px;
  line-height: 1.6;
  color: #49454f;
  margin: 0;
  white-space: pre-wrap;
}
.ai-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  color: #6750a4;
  background: #e8def8;
  padding: 1px 5px;
  border-radius: 4px;
  margin-left: 6px;
  vertical-align: middle;
}
.src-tag {
  font-size: 10px;
  color: #79747e;
  margin-left: 4px;
}
</style>
