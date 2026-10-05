<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 常住客订单中心（长租合同）—— listOrders source=longstay
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const contracts = ref<any[]>([])
const loading = ref(false)

const STATUS_CLS: Record<string, string> = {
  overdue: 'bg-error-container text-on-error-container border border-error/20',
  renew: 'bg-[#fef7e0] text-[#b06000] border border-[#fbbc04]/30',
  active: 'bg-primary/10 text-primary border border-primary/20',
}

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function mapContract(o: any) {
  const nights = Number(o.nights || 0)
  const months = Math.max(1, Math.round(nights / 30) || 1)
  const total = Number(o.total_amount || 0)
  const paidRatio =
    o.payment_status === 'paid' || o.payment_status === 'settled'
      ? 1
      : o.payment_status === 'partial'
        ? 0.6
        : o.payment_status === 'on_account'
          ? 0.4
          : o.status === 'checked_in'
            ? 0.7
            : 0.3
  const paid = Math.round(total * paidRatio)
  const due = Math.max(0, total - paid)
  const ci = o.check_in || ''
  const co = o.check_out || ''
  const start = typeof ci === 'string' ? ci.slice(0, 10) : ci
  const end = typeof co === 'string' ? co.slice(0, 10) : co

  let progress = 50
  if (start && end) {
    const a = new Date(start).getTime()
    const b = new Date(end).getTime()
    const now = Date.now()
    if (b > a) progress = Math.min(99, Math.max(5, Math.round(((now - a) / (b - a)) * 100)))
  }

  let status = 'active'
  let statusText = t('正常履约')
  let next = '账单已结清'
  let nextErr = false
  if (
    due > 0 &&
    (o.payment_status === 'unpaid' || o.payment_status === 'partial' || progress > 70)
  ) {
    status = 'overdue'
    statusText = t('账务逾期')
    next = `${end || '—'} (待收 ${money(due)})`
    nextErr = true
  } else if (progress >= 80 || (end && new Date(end).getTime() - Date.now() < 14 * 86400000)) {
    status = 'renew'
    statusText = t('即将续约')
    next = end || '—'
  } else if (due <= 0) {
    next = '账单已结清'
  } else {
    next = end || '—'
  }

  const tag = nights >= 30 ? '长住偏好' : o.note ? String(o.note).slice(0, 24) : '常住客画像'

  return {
    id: o.id,
    room: o.room_no || '待排房',
    roomType: o.room_type_name || '—',
    name: o.guest_name || '常住客人',
    status,
    statusText,
    tag,
    start: start || '—',
    months: `${months} 个月`,
    end: end || '—',
    progress,
    total: money(total),
    paid: money(paid),
    due: money(due),
    next,
    nextErr,
  }
}

const kpi = computed(() => {
  const all = contracts.value
  const active = all.filter(
    (c) => c.status === 'active' || c.status === 'renew' || c.status === 'overdue',
  ).length
  const renew = all.filter((c) => c.status === 'renew').length
  const overdue = all.filter((c) => c.status === 'overdue').length
  return { active, renew, overdue }
})

const insight = computed(() => {
  const { renew, overdue, active } = kpi.value
  if (overdue > 0) {
    return `当前有 ${overdue} 笔常住账务待催收，建议优先跟进逾期合同并核对挂账余额。`
  }
  if (renew > 0) {
    return `有 ${renew} 份合同临近到期。建议启动续约沟通，避免长租空置率上升。`
  }
  return `在住常住合同 ${active} 份。可结合企业长租优惠补充下月客源。`
})

async function load() {
  loading.value = true
  try {
    const rows = await api.listOrders(hotelStore.hotelId, undefined, { source: 'longstay' })
    const prefer = (rows || []).filter((o: any) =>
      ['checked_in', 'confirmed', 'pending'].includes(o.status),
    )
    const list = prefer.length ? prefer : rows || []
    contracts.value = list.slice(0, 12).map(mapContract)
  } catch {
    contracts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end mb-8 flex-wrap gap-3">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('常住客订单中心') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('长租续约办理（时长驱动）；企业协议客请进入「协议企业」') }}
        </p>
      </div>
      <div class="flex flex-col items-end gap-3">
        <OrdersFlowNav mode="longstay" hide-back />
        <div class="flex gap-4">
          <button
            class="flex items-center gap-2 px-4 py-2 border border-outline rounded-lg text-on-surface font-label-lg hover:bg-surface-container-low transition-colors"
          >
            <span class="material-symbols-outlined">filter_list</span> {{ t('筛选') }}
          </button>
          <button
            class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary/90 transition-colors shadow-sm"
          >
            <span class="material-symbols-outlined">add</span> {{ t('新建长租合同') }}
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter mb-8">
      <div
        class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between"
      >
        <div class="flex items-center gap-2 text-on-surface-variant mb-4">
          <span class="material-symbols-outlined text-primary">groups</span>
          <span class="font-label-lg text-label-lg">{{ t('在住长租客') }}</span>
        </div>
        <div class="font-num-xl text-[48px] leading-tight text-on-surface font-bold">
          {{ kpi.active }}
        </div>
        <div class="text-sm text-on-surface-variant mt-2">{{ t('来自订单表 · 常住渠道') }}</div>
      </div>
      <div
        class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between"
      >
        <div class="flex items-center gap-2 text-on-surface-variant mb-4">
          <span class="material-symbols-outlined text-error">warning</span>
          <span class="font-label-lg text-label-lg">{{ t('即将到期/欠费') }}</span>
        </div>
        <div class="flex gap-6">
          <div>
            <div class="font-num-xl text-[32px] text-on-surface font-bold">{{ kpi.renew }}</div>
            <div class="text-sm text-on-surface-variant">{{ t('即将续约') }}</div>
          </div>
          <div>
            <div class="font-num-xl text-[32px] text-error font-bold">{{ kpi.overdue }}</div>
            <div class="text-sm text-on-surface-variant">{{ t('账务逾期') }}</div>
          </div>
        </div>
      </div>
      <div
        class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border-l-4 border-l-tertiary shadow-sm relative overflow-hidden group"
      >
        <div
          class="absolute inset-0 bg-tertiary/5 opacity-0 group-hover:opacity-100 transition-opacity"
        ></div>
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-2 text-tertiary">
            <span class="material-symbols-outlined">auto_awesome</span>
            <span class="font-label-lg text-label-lg font-bold">{{ t('AI 洞察') }}</span>
          </div>
        </div>
        <p class="font-body-md text-on-surface">{{ insight }}</p>
      </div>
    </div>

    <div v-if="loading" class="text-on-surface-variant py-8 text-center">
      {{ t('加载常住合同中…') }}
    </div>
    <div v-else-if="!contracts.length" class="text-on-surface-variant py-8 text-center">
      {{ t('暂无常住客订单') }}
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-gutter">
      <div
        v-for="c in contracts"
        :key="c.id"
        class="bg-surface-container-lowest rounded-xl border shadow-sm flex flex-col overflow-hidden relative cursor-pointer"
        :class="c.status === 'overdue' ? 'border-error-container' : 'border-outline-variant'"
        @click="router.push(`/orders/${c.id}`)"
      >
        <div
          v-if="c.status === 'renew'"
          class="absolute top-0 left-0 w-full h-1"
          style="background: #fbbc04"
        ></div>
        <div
          class="p-5 border-b border-outline-variant"
          :class="c.status === 'overdue' ? 'bg-error/5' : ''"
        >
          <div class="flex justify-between items-start mb-3">
            <div>
              <div class="font-num-xl text-num-xl text-on-surface flex items-center gap-2">
                {{ c.room }}
                <span
                  class="text-sm font-normal text-on-surface-variant bg-surface-container p-1 rounded"
                  >{{ c.roomType }}</span
                >
              </div>
              <div class="font-headline-md text-headline-md text-on-surface mt-1">{{ c.name }}</div>
            </div>
            <span
              class="inline-flex items-center px-2 py-1 rounded text-xs font-medium"
              :class="STATUS_CLS[c.status]"
              >{{ c.statusText }}</span
            >
          </div>
          <div class="flex flex-wrap gap-2 mt-2">
            <span
              class="inline-flex items-center gap-1 px-2 py-1 rounded bg-tertiary/10 text-tertiary text-xs border border-tertiary/20"
            >
              <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
              {{ c.tag }}</span
            >
          </div>
        </div>
        <div class="p-5 flex-1 flex flex-col gap-4">
          <div>
            <div class="flex justify-between text-sm text-on-surface-variant mb-1">
              <span>{{ c.start }}</span>
              <span class="font-medium text-on-surface">{{ c.months }}</span>
              <span>{{ c.end }}</span>
            </div>
            <div class="w-full bg-surface-variant rounded-full h-2">
              <div class="bg-primary h-2 rounded-full" :style="{ width: c.progress + '%' }"></div>
            </div>
          </div>
          <div
            class="bg-surface-container-low rounded-lg p-3 grid grid-cols-2 gap-4 border border-outline-variant"
          >
            <div>
              <div class="text-xs text-on-surface-variant">{{ t('合同总额') }}</div>
              <div class="font-num-md text-num-md text-on-surface">{{ c.total }}</div>
            </div>
            <div>
              <div class="text-xs text-on-surface-variant">{{ t('已付 / 待付') }}</div>
              <div
                class="font-num-md text-num-md"
                :class="c.status === 'overdue' ? 'text-error' : 'text-on-surface'"
              >
                {{ c.paid }} / <span class="font-bold">{{ c.due }}</span>
              </div>
            </div>
            <div class="col-span-2">
              <div class="text-xs text-on-surface-variant">{{ t('下期付款日') }}</div>
              <div
                class="font-num-md text-sm flex items-center gap-1"
                :class="c.nextErr ? 'text-error' : 'text-on-surface'"
              >
                <span class="material-symbols-outlined text-[16px]">{{
                  c.nextErr ? 'event_busy' : c.status === 'active' ? 'check_circle' : 'event'
                }}</span>
                {{ c.next }}
              </div>
            </div>
          </div>
        </div>
        <div
          class="p-4 border-t border-outline-variant bg-surface-container-lowest flex justify-end gap-3"
          @click.stop
        >
          <button
            v-if="c.status === 'overdue'"
            type="button"
            class="px-4 py-2 border border-outline rounded-lg text-on-surface font-label-lg hover:bg-surface-container-low transition-colors"
            @click="router.push(`/orders/${c.id}`)"
          >
            {{ t('查看分账') }}
          </button>
          <button
            v-if="c.status === 'renew'"
            type="button"
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary/90 transition-colors shadow-sm flex items-center gap-1"
            @click="router.push(`/orders/${c.id}`)"
          >
            <span class="material-symbols-outlined text-[18px]">autorenew</span> {{ t('续约') }}
          </button>
          <button
            v-if="c.status === 'active'"
            type="button"
            class="px-4 py-2 border border-outline rounded-lg text-on-surface font-label-lg hover:bg-surface-container-low transition-colors"
            @click="router.push(`/orders/${c.id}`)"
          >
            {{ t('查看订单') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
