<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { fmt, toast } from '../lib/ui'

const router = useRouter()
const d = ref<any>(null)
const board = ref<any>(null)
const audit = ref<any>(null)
const auditing = ref(false)
const audits = ref<any[]>([])
const payMethods = ref<any[]>([])

async function load() {
  const hid = hotelStore.hotelId
  const [dash, auditsList, fb] = await Promise.all([
    api.dashboard(hid),
    api.listAudits(hid),
    api.financeBoard(hid).catch(() => null),
  ])
  d.value = dash
  audits.value = auditsList
  board.value = fb
  payMethods.value = (fb?.payment_by_method || []).slice(0, 5)
  const today = new Date().toISOString().slice(0, 10)
  audit.value = audits.value.find((a) => a.biz_date === today) || null
}
async function runAudit() {
  auditing.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    audit.value = await api.runAudit({ hotel_id: hotelStore.hotelId, biz_date: today })
    toast(t('夜审完成'))
    audits.value = await api.listAudits(hotelStore.hotelId)
  } finally {
    auditing.value = false
  }
}
async function go(path: string) {
  try {
    await router.push(path)
  } catch {
    toast(t('前端资源已更新，正在刷新页面…'))
    location.hash = `#${path}`
    location.reload()
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('财务管理') }}</h1>
      <p>{{ t('营收、账务与智能夜审。夜审将锁定当日营业数据并生成对账凭证。') }}</p>
      <div style="margin-top: 12px">
        <button class="btn btn-primary" type="button" @click="go('/c9-finance/night-audit')">
          {{ t('进入 ⑨ 日结财务动线（从夜审开始）→') }}
        </button>
        <button
          class="btn btn-link"
          type="button"
          style="margin-left: 8px"
          @click="go('/orders?status=checked_in')"
        >
          {{ t('相关：去订单中心选在住单退房 ↗') }}
        </button>
      </div>
    </div>

    <div v-if="d" class="kpi-grid">
      <div class="kpi">
        <div class="k">{{ t('今日营收') }}</div>
        <div class="v">{{ fmt(board?.payment_total ?? d.revenue_today) }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('在住房间') }}</div>
        <div class="v">{{ board?.room_status?.occupied ?? d.occupied }} {{ t('间') }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('待确认价格建议') }}</div>
        <div class="v">{{ d.pending_price }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('营收异常') }}</div>
        <div class="v">{{ board?.counts?.open_anomalies ?? d.open_risks }}</div>
      </div>
    </div>

    <div v-if="payMethods.length" class="card-clean card-pad" style="margin-top: 16px">
      <h3 style="font-size: 14px; font-weight: 600; margin: 0 0 12px; color: var(--on-surface)">
        {{ t('支付方式汇总（payments）') }}
      </h3>
      <div
        style="
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 10px;
        "
      >
        <div
          v-for="(m, i) in payMethods"
          :key="i"
          class="card-clean card-pad"
          style="text-align: center"
        >
          <div style="font-size: 12px; color: var(--on-surface-variant)">{{ m.method }}</div>
          <div
            class="tnum"
            style="font-size: 16px; font-weight: 700; color: var(--primary); margin-top: 4px"
          >
            {{ fmt(m.net) }}
          </div>
          <div style="font-size: 11px; color: var(--on-surface-variant); margin-top: 2px">
            {{ m.count }} {{ t('笔') }}
          </div>
        </div>
      </div>
    </div>

    <div class="card-clean card-pad" style="margin-top: 16px">
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        "
      >
        <h3 style="font-size: 14px; font-weight: 600; margin: 0; color: var(--on-surface)">
          {{ t('智能夜审') }}
        </h3>
        <button class="btn btn-primary" :disabled="auditing" @click="runAudit">
          <span class="material-symbols-outlined" style="font-size: 18px">nightlight</span>
          {{ auditing ? t('审计中…') : t('运行当日夜审') }}
        </button>
      </div>

      <div v-if="audit" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px">
        <div class="card-clean card-pad" style="text-align: center">
          <div style="font-size: 12px; color: var(--on-surface-variant)">{{ t('营业收入') }}</div>
          <div
            class="tnum"
            style="font-size: 20px; font-weight: 700; color: var(--primary); margin-top: 4px"
          >
            {{ fmt(audit.revenue) }}
          </div>
        </div>
        <div class="card-clean card-pad" style="text-align: center">
          <div style="font-size: 12px; color: var(--on-surface-variant)">{{ t('过夜房晚') }}</div>
          <div
            class="tnum"
            style="font-size: 20px; font-weight: 700; color: var(--on-surface); margin-top: 4px"
          >
            {{ audit.room_nights }}
          </div>
        </div>
        <div class="card-clean card-pad" style="text-align: center">
          <div style="font-size: 12px; color: var(--on-surface-variant)">{{ t('异常单数') }}</div>
          <div
            class="tnum"
            style="font-size: 20px; font-weight: 700; color: #be123c; margin-top: 4px"
          >
            {{ audit.exceptions }}
          </div>
        </div>
      </div>
      <div v-else style="color: #9aa1ad; font-size: 13px">
        {{ t('尚未运行。点击右上角按钮对当前营业日执行夜审。') }}
      </div>
      <div v-if="audit" style="margin-top: 12px; text-align: right">
        <button class="btn btn-link" @click="router.push('/finance/audit/' + audit.biz_date)">
          {{ t('查看当日夜审详情 ↗') }}
        </button>
      </div>
    </div>

    <div class="card-clean" style="margin-top: 16px">
      <div class="card-pad" style="border-bottom: 1px solid var(--outline-variant)">
        <h3 style="font-size: 14px; font-weight: 600; margin: 0">{{ t('夜审历史') }}</h3>
      </div>
      <div class="card-pad" style="padding-top: 0">
        <table class="data-table" style="width: 100%">
          <thead>
            <tr>
              <th>{{ t('营业日') }}</th>
              <th>{{ t('营收') }}</th>
              <th>{{ t('房晚') }}</th>
              <th>{{ t('异常') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="a in audits.slice(0, 10)"
              :key="a.id"
              style="cursor: pointer"
              @click="router.push('/finance/audit/' + a.biz_date)"
            >
              <td>{{ a.biz_date }}</td>
              <td class="tnum">{{ fmt(a.revenue) }}</td>
              <td class="tnum">{{ a.room_nights }}</td>
              <td class="tnum">{{ a.exceptions }}</td>
              <td>{{ a.status }}</td>
            </tr>
            <tr v-if="!audits.length">
              <td colspan="5" style="color: #9aa1ad">{{ t('暂无夜审记录') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
