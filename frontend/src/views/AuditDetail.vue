<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { fmt, toast } from '../lib/ui'
import { hotelStore } from '../store/hotel'

const route = useRoute()
const router = useRouter()
const d = ref<any>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    d.value = await api.auditDetail(hotelStore.hotelId, String(route.params.biz_date))
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => route.params.biz_date, load)

async function rerunAudit() {
  if (!confirm(t('确认重新执行该日夜审？将覆盖已有审计结果。'))) return
  await api.runAudit({ hotel_id: hotelStore.hotelId, biz_date: String(route.params.biz_date) })
  toast(t('夜审已重跑'))
  load()
}
</script>

<template>
  <div class="page">
    <a class="back-link" @click="router.push('/finance')">
      <span class="material-symbols-outlined" style="font-size: 18px">arrow_back</span>
      {{ t('返回财务看板') }}</a
    >

    <div v-if="loading" style="color: #9aa1ad">{{ t('加载中…') }}</div>
    <div v-else-if="d">
      <div class="page-actions">
        <div class="page-head" style="margin: 0">
          <h1>{{ t('夜审 ·') }} {{ d.biz_date }}</h1>
          <p>
            {{ t('午夜自动核对账务 / 房务 / 价格，标记异常项；店长可在此查阅当日明细。') }}
          </p>
        </div>
        <button class="btn btn-ghost" @click="rerunAudit">{{ t('重跑夜审') }}</button>
      </div>

      <div style="display: flex; gap: 8px; margin-bottom: 14px">
        <span v-if="d.log" class="pill pill-green">{{ t('已通过') }}</span>
        <span v-else class="pill pill-amber">{{ t('未执行') }}</span>
        <span v-if="d.exceptions > 0" class="pill pill-rose">{{ d.exceptions }} 项异常</span>
        <span v-else class="pill pill-slate">{{ t('无异常') }}</span>
      </div>

      <!-- 汇总 KPI -->
      <div class="kpi-grid" style="margin-bottom: 16px">
        <div class="kpi">
          <div class="k">{{ t('当日营收') }}</div>
          <div class="v">{{ fmt(d.log?.revenue || 0) }}</div>
          <div class="d up">{{ d.payments.length }} {{ t('笔支付') }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('售出间夜') }}</div>
          <div class="v">{{ d.log?.room_nights || 0 }}</div>
          <div class="d flat">{{ t('退房订单') }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('No-Show 数') }}</div>
          <div class="v" :style="{ color: d.exceptions > 0 ? '#be123c' : 'var(--on-surface)' }">
            {{ d.exceptions }}
          </div>
          <div class="d" :class="d.exceptions > 0 ? 'down' : 'flat'">{{ t('异常工单') }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('护栏命中') }}</div>
          <div
            class="v"
            :style="{ color: d.blocked_pricing?.length ? '#be123c' : 'var(--on-surface)' }"
          >
            {{ d.blocked_pricing?.length || 0 }}
          </div>
          <div class="d flat">{{ t('需人工复核') }}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px">
        <!-- 支付明细 -->
        <div class="card-clean">
          <div class="card-head">
            <span>{{ t('支付明细 (') }}{{ d.payments.length }})</span>
          </div>
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('编号') }}</th>
                <th>{{ t('方式') }}</th>
                <th class="num">{{ t('金额') }}</th>
                <th>{{ t('时间') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in d.payments.slice(0, 12)" :key="p.id">
                <td
                  style="
                    font:
                      500 12px 'Roboto Mono',
                      monospace;
                  "
                >
                  {{ p.id }}
                </td>
                <td>
                  <span class="pill pill-blue">{{ p.method }}</span>
                </td>
                <td class="num">{{ fmt(p.amount) }}</td>
                <td style="color: var(--on-surface-variant); font-size: 12px">
                  {{ (p.paid_at || '').slice(11, 16) }}
                </td>
              </tr>
              <tr v-if="!d.payments.length">
                <td colspan="4" style="text-align: center; color: #9aa1ad; padding: 18px">
                  {{ t('暂无支付') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 退房订单 -->
        <div class="card-clean">
          <div class="card-head">
            <span>{{ t('退房订单 (') }}{{ d.checked_out_orders.length }})</span>
          </div>
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('订单号') }}</th>
                <th class="num">{{ t('金额') }}</th>
                <th>{{ t('支付') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="o in d.checked_out_orders.slice(0, 12)"
                :key="o.id"
                class="clickable"
                @click="router.push('/orders/' + o.id)"
              >
                <td
                  style="
                    font:
                      500 12px 'Roboto Mono',
                      monospace;
                  "
                >
                  {{ o.order_no }}
                </td>
                <td class="num">{{ fmt(o.total_amount) }}</td>
                <td>
                  <span class="pill pill-green">{{ o.payment_status }}</span>
                </td>
              </tr>
              <tr v-if="!d.checked_out_orders.length">
                <td colspan="3" style="text-align: center; color: #9aa1ad; padding: 18px">
                  {{ t('无退房记录') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 护栏命中 -->
      <div
        v-if="d.blocked_pricing?.length"
        class="card-clean"
        style="margin-top: 14px; border-left: 3px solid #be123c"
      >
        <div class="card-head">
          <span>{{ t('护栏命中建议（需人工复核）') }}</span>
        </div>
        <table class="data">
          <thead>
            <tr>
              <th>{{ t('房型') }}</th>
              <th class="num">{{ t('基础价') }}</th>
              <th class="num">{{ t('建议价') }}</th>
              <th>{{ t('原因') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in d.blocked_pricing" :key="p.id">
              <td>{{ p.room_type_name || p.room_type_id }}</td>
              <td class="num">—</td>
              <td class="num" style="color: #be123c">{{ fmt(p.suggested_price) }}</td>
              <td style="color: var(--on-surface-variant)">{{ p.guardrail_msg || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 发票 -->
      <div v-if="d.invoices?.length" class="card-clean" style="margin-top: 14px">
        <div class="card-head">
          <span>{{ t('开具发票 (') }}{{ d.invoices.length }})</span>
        </div>
        <div style="padding: 12px 16px; font-size: 13px; color: var(--on-surface-variant)">
          {{ t('合计') }} {{ d.invoices.length }} {{ t('张发票，含税合计') }} ¥{{
            fmt(d.invoices.reduce((a: number, i: any) => a + Number(i.amount || 0), 0))
          }}
        </div>
      </div>
    </div>
  </div>
</template>
