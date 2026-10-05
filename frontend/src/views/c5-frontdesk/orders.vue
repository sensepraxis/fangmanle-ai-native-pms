<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt, ORDER_ST_CN, ORDER_ST_PILL, PAY_CN, PAY_PILL, toast } from '../../lib/ui'

const router = useRouter()
function goDetail(id: number) {
  router.push(`/orders/${id}`)
}
function goGuest(id?: number) {
  if (id) router.push(`/guests/${id}`)
}

const statusFilter = ref('')
const channelFilter = ref('')
const orders = ref<any[]>([])
const channels = ref<any[]>([])

async function load() {
  orders.value = await api.listOrders(hotelStore.hotelId, statusFilter.value || undefined)
}
function clearFilters() {
  statusFilter.value = ''
  channelFilter.value = ''
  load()
}
async function loadMeta() {
  channels.value = await api.listChannels()
}
onMounted(async () => {
  await loadMeta()
  await load()
})
watch(
  () => hotelStore.hotelId,
  async () => {
    await loadMeta()
    await load()
  },
)

async function doCheckin(id: number) {
  if (!confirm(t('确认为该订单办理入住（自动分配同房型空房）？'))) return
  await api.checkin(id)
  toast(t('已办理入住'))
  load()
}
function goCheckout(o: any) {
  router.push({
    path: '/c5-frontdesk/cashiering-checkout',
    query: { orderId: String(o.id) },
  })
}
function checkoutBtnLabel(o: any) {
  const sg = String(o.source_group || '')
  const pay = String(o.payment_status || '')
  if (sg === 'agreement' || pay === 'on_account') return t('挂账退房')
  if (sg === 'ota' || sg === 'voucher' || pay === 'paid') return t('核对退房')
  return t('收银退房')
}
function openCreate() {
  router.push('/c5-frontdesk/front-desk-booking')
}
function channelPill(c: string) {
  if (c?.includes('OTA') || c?.includes('携程') || c?.includes('美团')) return 'pill-blue'
  if (c?.includes('抖音')) return 'pill-rose'
  if (c?.includes('直接')) return 'pill-slate'
  return 'pill-blue'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('订单管理') }}</h1>
      <p>{{ t('管理所有渠道的预订和客单') }}</p>
    </div>

    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8px 0 16px;
        flex-wrap: wrap;
        gap: 12px;
      "
    >
      <div class="toolbar" style="flex: 1; min-width: 320px">
        <select v-model="statusFilter" @change="load">
          <option value="">{{ t('所有状态') }}</option>
          <option value="pending">{{ t('待入住') }}</option>
          <option value="checked_in">{{ t('在住') }}</option>
          <option value="checked_out">{{ t('已退房') }}</option>
          <option value="cancelled">{{ t('已取消') }}</option>
        </select>
        <select v-model="channelFilter" @change="load">
          <option value="">{{ t('所有渠道') }}</option>
          <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <span style="flex: 1"></span>
        <button class="btn btn-link" @click="clearFilters">
          {{ t('清除过滤') }}
        </button>
      </div>
      <button class="btn btn-primary" @click="openCreate">
        <span class="material-symbols-outlined" style="font-size: 18px">add</span>
        {{ t('新建订单') }}
      </button>
    </div>

    <div class="card-clean" style="overflow: hidden">
      <table class="data">
        <thead>
          <tr>
            <th style="width: 170px">{{ t('订单编号') }}</th>
            <th style="width: 120px">{{ t('渠道') }}</th>
            <th style="width: 140px">{{ t('客人姓名') }}</th>
            <th style="width: 160px">{{ t('房型') }}</th>
            <th style="width: 180px">{{ t('入住日期') }}</th>
            <th class="num" style="width: 120px">{{ t('总金额') }}</th>
            <th style="width: 160px">{{ t('状态 / 标签') }}</th>
            <th class="center" style="width: 200px">{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id" class="clickable" @click="goDetail(o.id)">
            <td style="font-variant-numeric: tabular-nums; font-weight: 500">
              <span class="link">{{ o.order_no }}</span>
            </td>
            <td>
              <span class="pill" :class="channelPill(o.channel_name)">{{ o.channel_name }}</span>
            </td>
            <td>
              <div style="font-weight: 500; color: var(--on-surface)">
                <span class="link" @click.stop="goGuest(o.guest_id)">{{ o.guest_name }}</span>
              </div>
              <div style="color: #9aa1ad; font-size: 12px">{{ o.phone || '—' }}</div>
            </td>
            <td>
              <div>{{ o.room_type_name }}</div>
              <div style="color: #9aa1ad; font-size: 12px">
                {{ o.nights || 1 }}{{ t('晚 (') }}{{ o.rooms || 1 }} {{ t('间') }})
              </div>
            </td>
            <td style="color: #5b616e; font-variant-numeric: tabular-nums">
              {{ o.check_in }} ~ {{ o.check_out }}
            </td>
            <td class="num">{{ fmt(o.total_amount) }}</td>
            <td>
              <div style="display: flex; gap: 6px; flex-wrap: wrap">
                <span class="pill" :class="ORDER_ST_PILL[o.status] || 'pill-slate'">{{
                  t(ORDER_ST_CN[o.status] || o.status)
                }}</span>
                <span class="pill" :class="PAY_PILL[o.payment_status] || 'pill-slate'">{{
                  t(PAY_CN[o.payment_status] || o.payment_status)
                }}</span>
              </div>
            </td>
            <td class="center">
              <div style="display: flex; gap: 6px; justify-content: center">
                <button
                  v-if="o.status === 'pending'"
                  class="btn btn-primary"
                  style="padding: 5px 12px; font-size: 12px"
                  @click.stop="doCheckin(o.id)"
                >
                  {{ t('办理入住') }}
                </button>
                <button
                  v-if="o.status === 'checked_in'"
                  class="btn btn-primary"
                  style="padding: 5px 12px; font-size: 12px"
                  @click.stop="goCheckout(o)"
                >
                  {{ checkoutBtnLabel(o) }}
                </button>
                <span
                  v-if="o.status === 'checked_out' || o.status === 'cancelled'"
                  style="color: #9aa1ad; font-size: 12px"
                  >—</span
                >
              </div>
            </td>
          </tr>
          <tr v-if="!orders.length">
            <td colspan="8" style="text-align: center; color: #9aa1ad; padding: 30px">
              {{ t('暂无订单') }}
            </td>
          </tr>
        </tbody>
      </table>
      <div
        style="
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          border-top: 1px solid var(--outline-variant);
          color: var(--on-surface-variant);
          font-size: 13px;
        "
      >
        <span
          >{{ t('显示第') }} <b style="color: var(--on-surface)">1</b> {{ t('到') }}
          <b style="color: var(--on-surface)">{{ orders.length }}</b> {{ t('条结果，共') }}
          <b style="color: var(--on-surface)">{{ orders.length }}</b> {{ t('条') }}</span
        >
        <div style="display: flex; gap: 4px">
          <span class="pill pill-slate" style="cursor: default">1</span>
          <span class="pill pill-slate" style="cursor: default">2</span>
          <span class="pill pill-slate" style="cursor: default">3</span>
        </div>
      </div>
    </div>
  </div>
</template>
