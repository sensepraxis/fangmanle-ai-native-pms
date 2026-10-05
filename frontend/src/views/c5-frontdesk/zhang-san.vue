<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// C5 常住账务流水与分账 —— 数据来自 ledger_entries
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const summary = ref({
  billed: '—',
  deposits: '—',
  outstanding: '—',
  utility: '—',
})

type Tx = {
  date: string
  icon: string
  iconCls: string
  desc: string
  amount: string
  paid: boolean
}
const txs = ref<Tx[]>([])
const guestName = ref('常住客')
const roomBadge = ref('—')
const stayHint = ref('')

type Month = { label: string; rent: number; util: number; current?: boolean }
const months = ref<Month[]>([])

async function load() {
  const hid = hotelStore.hotelId
  try {
    const [ledger, guests, rooms] = await Promise.all([
      api.listLedger(hid, 30),
      api.listGuests(hid).catch(() => []),
      api.listRooms(hid).catch(() => []),
    ])
    txs.value = (ledger?.entries || []).map((e: any) => ({
      date: e.date || '—',
      icon: e.icon || 'home',
      iconCls: e.iconCls || '',
      desc: e.desc || '账务',
      amount: e.amount || '0.00',
      paid: Boolean(e.paid),
    }))
    if (ledger?.summary) summary.value = { ...summary.value, ...ledger.summary }

    const vip =
      (guests || []).find((g: any) => String(g.vip_level || '').toLowerCase() !== 'normal') ||
      (guests || [])[0]
    if (vip) guestName.value = vip.name
    const occ = (rooms || []).find((r: any) => r.status === 'occupied')
    roomBadge.value = occ?.room_no || '—'
    stayHint.value = txs.value.length
      ? `账务流水 ${txs.value.length} 条 · 来自 ledger_entries`
      : '暂无账务流水'

    // 按月聚合柱图
    const bag: Record<string, { rent: number; util: number }> = {}
    for (const e of ledger?.entries || []) {
      const m = String(e.date || '').slice(5, 7)
      if (!m) continue
      const label = `${Number(m)}月`
      const b = bag[label] || { rent: 0, util: 0 }
      const n = Number(e.amount_num || 0)
      if (e.icon === 'bolt') b.util += n
      else b.rent += n
      bag[label] = b
    }
    const keys = Object.keys(bag).slice(0, 6)
    const max = Math.max(1, ...keys.map((k) => bag[k].rent + bag[k].util))
    months.value = keys.map((label, i) => ({
      label,
      rent: Math.round((100 * bag[label].rent) / max),
      util: Math.round((100 * bag[label].util) / max),
      current: i === keys.length - 1,
    }))
  } catch {
    txs.value = []
    stayHint.value = t('账务加载失败，请确认已登录')
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <main class="flex-1 overflow-y-auto p-container-padding">
    <div class="max-w-max-content-width mx-auto space-y-6">
      <!-- 页头 & 客人信息 -->
      <div
        class="flex justify-between items-end border-b border-surface-variant pb-4 flex-wrap gap-3"
      >
        <div>
          <div class="flex items-center gap-3 mb-2">
            <span
              class="bg-primary-container text-on-primary-container px-2 py-1 rounded font-num-xl"
              >{{ roomBadge }}</span
            >
            <h1 class="font-headline-lg text-on-surface">{{ guestName }}</h1>
            <span
              class="bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded-full text-xs font-label-lg"
              >{{ t('长租客 (Long-Stay)') }}</span
            >
          </div>
          <p class="font-body-md text-on-surface-variant">
            {{ stayHint || t('账务流水来自 ledger_entries') }} · {{ t('常住支线') }}
          </p>
        </div>
        <div class="flex flex-col items-end gap-3">
          <OrdersFlowNav mode="longstay" hide-back />
          <!-- AI 推送横幅 -->
          <div
            class="bg-tertiary-fixed-dim/20 border-l-4 border-tertiary p-3 rounded-r-lg flex items-center gap-4 max-w-md shadow-sm"
          >
            <span
              class="material-symbols-outlined text-tertiary"
              style="font-variation-settings: 'FILL' 1"
              >smart_toy</span
            >
            <div class="flex-1">
              <h4 class="font-label-lg text-on-surface font-semibold mb-1">
                {{ t('Automated Billing (AI 推送)') }}
              </h4>
              <p class="text-xs text-on-surface-variant">
                {{ t('建议开启微信账单定期推送，提高账款回收率。') }}
              </p>
            </div>
            <button
              class="bg-tertiary text-on-tertiary px-3 py-1.5 rounded font-label-lg hover:bg-tertiary-container hover:text-on-tertiary-container transition-colors shadow-sm"
            >
              {{ t('开启推送') }}
            </button>
          </div>
        </div>
      </div>
      <!-- 概览卡 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-gutter">
        <div
          class="bg-surface rounded-xl p-5 border border-outline-variant shadow-sm flex flex-col justify-between h-32 relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-3 opacity-10">
            <span class="material-symbols-outlined text-4xl">account_balance_wallet</span>
          </div>
          <h3 class="font-label-lg text-on-surface-variant">{{ t('总账单额 (Total Billed)') }}</h3>
          <div>
            <span class="font-num-xl text-on-surface">¥{{ summary.billed }}}</span
            ><span class="text-xs text-secondary ml-1">.00</span>
          </div>
        </div>
        <div
          class="bg-surface rounded-xl p-5 border border-outline-variant shadow-sm flex flex-col justify-between h-32 relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-3 opacity-10">
            <span class="material-symbols-outlined text-4xl">lock</span>
          </div>
          <h3 class="font-label-lg text-on-surface-variant">{{ t('已收押金 (Deposits Held)') }}</h3>
          <div>
            <span class="font-num-xl text-on-surface">¥{{ summary.deposits }}}</span
            ><span class="text-xs text-secondary ml-1">.00</span>
          </div>
        </div>
        <div
          class="bg-error-container rounded-xl p-5 border border-error/20 shadow-sm flex flex-col justify-between h-32 relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-3 opacity-20 text-error">
            <span class="material-symbols-outlined text-4xl">warning</span>
          </div>
          <h3 class="font-label-lg text-on-error-container">{{ t('待结余额 (Outstanding)') }}</h3>
          <div>
            <span class="font-num-xl text-error">¥{{ summary.outstanding }}}</span
            ><span class="text-xs text-error/70 ml-1">.50</span>
          </div>
        </div>
        <div
          class="bg-surface rounded-xl p-5 border-l-4 border-primary shadow-sm flex flex-col justify-between h-32 relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-3 opacity-10 text-primary">
            <span class="material-symbols-outlined text-4xl">water_drop</span>
          </div>
          <div class="flex items-center gap-1">
            <h3 class="font-label-lg text-on-surface-variant">
              {{ t('本月水电预估 (Utility Est)') }}
            </h3>
            <span class="material-symbols-outlined text-[14px] text-tertiary"
              >arrow_back_ios_new</span
            >
          </div>
          <div>
            <span class="font-num-xl text-primary">¥{{ summary.utility }}</span>
            <span
              class="text-xs text-on-surface-variant ml-2 bg-surface-variant px-1.5 py-0.5 rounded"
              >{{ t('↑ 12% 环比') }}</span
            >
          </div>
        </div>
      </div>
      <!-- 账务流水 & 图表 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <!-- 流水明细 -->
        <div
          class="lg:col-span-2 bg-surface rounded-xl border border-outline-variant shadow-sm flex flex-col"
        >
          <div
            class="p-4 border-b border-surface-variant flex justify-between items-center bg-surface-container-low rounded-t-xl"
          >
            <h2 class="font-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined">list_alt</span>
              {{ t('账务流水明细 (Transaction List)') }}
            </h2>
            <div class="flex gap-2">
              <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                <span class="material-symbols-outlined">filter_list</span>
              </button>
              <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                <span class="material-symbols-outlined">download</span>
              </button>
            </div>
          </div>
          <div class="overflow-x-auto flex-1">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr
                  class="bg-surface-bright border-b border-surface-variant font-label-lg text-on-surface-variant"
                >
                  <th class="p-4 font-medium">{{ t('日期 (Date)') }}</th>
                  <th class="p-4 font-medium">{{ t('摘要 (Description)') }}</th>
                  <th class="p-4 font-medium text-right">{{ t('金额 (Amount)') }}</th>
                  <th class="p-4 font-medium">{{ t('状态 (Status)') }}</th>
                  <th class="p-4 font-medium">{{ t('操作 (Action)') }}</th>
                </tr>
              </thead>
              <tbody class="font-body-md text-on-surface">
                <tr
                  v-for="(item, i) in txs"
                  :key="i"
                  class="border-b border-surface-variant hover:bg-surface-container-lowest transition-colors"
                  :class="t.paid ? 'bg-surface-container-lowest/50' : ''"
                >
                  <td
                    class="p-4 font-num-md text-on-surface-variant"
                    :class="t.paid ? 'opacity-70' : ''"
                  >
                    {{ t.date }}
                  </td>
                  <td class="p-4">
                    <div class="flex items-center gap-2">
                      <span
                        class="material-symbols-outlined text-sm"
                        :class="t.paid ? '' : t.iconCls"
                        >{{ t.icon }}</span
                      >
                      {{ t.desc }}
                    </div>
                  </td>
                  <td
                    class="p-4 font-num-md text-right"
                    :class="t.paid ? 'text-on-surface-variant/70' : ''"
                  >
                    ¥{{ t.amount }}
                  </td>
                  <td class="p-4">
                    <span
                      v-if="!t.paid"
                      class="bg-error-container text-on-error-container px-2 py-1 rounded-full text-xs font-label-lg border border-error/20 flex w-max items-center gap-1"
                    >
                      <span class="w-1.5 h-1.5 rounded-full bg-error"></span>
                      {{ t('未付 (Pending)') }}</span
                    >
                    <span
                      v-else
                      class="bg-surface-variant text-on-surface-variant px-2 py-1 rounded-full text-xs font-label-lg flex w-max items-center gap-1"
                    >
                      <span class="material-symbols-outlined text-[12px]">check_circle</span>
                      {{ t('已付 (Paid)') }}</span
                    >
                  </td>
                  <td class="p-4">
                    <button v-if="!t.paid" class="text-primary hover:underline text-sm">
                      {{ t('催款') }}
                    </button>
                    <button v-else class="text-secondary hover:text-primary transition-colors">
                      <span class="material-symbols-outlined text-sm">receipt</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- 右列：趋势 & 入账 -->
        <div class="flex flex-col gap-gutter">
          <!-- 月度消费趋势 -->
          <div class="bg-surface rounded-xl border border-outline-variant shadow-sm p-5 flex-1">
            <div class="flex justify-between items-center mb-6">
              <h2 class="font-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined">bar_chart</span> {{ t('月度消费趋势') }}
              </h2>
              <span
                class="text-xs text-on-surface-variant bg-surface-container-low px-2 py-1 rounded"
                >{{ t('近6个月') }}</span
              >
            </div>
            <div class="relative w-full h-[180px] flex flex-col justify-end">
              <div
                class="absolute left-0 top-0 bottom-6 w-8 flex flex-col justify-between text-[10px] text-on-surface-variant font-num-md"
              >
                <span>¥4k</span><span>¥2k</span><span>0</span>
              </div>
              <div
                class="absolute left-8 right-0 top-1.5 bottom-6 flex flex-col justify-between z-0"
              >
                <div class="w-full border-t border-dashed border-outline-variant/30"></div>
                <div class="w-full border-t border-dashed border-outline-variant/30"></div>
                <div class="w-full border-t border-solid border-outline-variant/50"></div>
              </div>
              <div class="ml-8 z-10 flex justify-between items-end h-[150px] pb-6 relative">
                <div
                  v-for="(m, i) in months"
                  :key="i"
                  class="flex flex-col items-center gap-2 group"
                >
                  <div class="relative w-8 h-[150px] flex flex-col justify-end">
                    <div
                      class="bar bg-tertiary w-full"
                      :style="{ height: m.util + '%', borderRadius: 0 }"
                      :class="
                        m.current
                          ? 'opacity-50 border-2 border-dashed border-tertiary bg-transparent'
                          : ''
                      "
                    ></div>
                    <div
                      class="bar bg-primary w-full"
                      :style="{
                        height: m.rent + '%',
                        borderBottomLeftRadius: '4px',
                        borderBottomRightRadius: '4px',
                      }"
                    ></div>
                  </div>
                  <span
                    class="text-[10px] text-on-surface-variant"
                    :class="m.current ? 'text-primary font-bold' : ''"
                    >{{ m.label }}</span
                  >
                </div>
              </div>
            </div>
            <div class="flex justify-center gap-4 mt-2">
              <div class="flex items-center gap-1 text-xs text-on-surface-variant">
                <span class="w-3 h-3 bg-primary rounded-sm block"></span> {{ t('房租') }}
              </div>
              <div class="flex items-center gap-1 text-xs text-on-surface-variant">
                <span class="w-3 h-3 bg-tertiary rounded-sm block"></span> {{ t('杂费/水电') }}
              </div>
            </div>
          </div>
          <!-- 手动入账 -->
          <div class="bg-surface rounded-xl border border-outline-variant shadow-sm p-5">
            <h2 class="font-headline-md text-on-surface mb-4">{{ t('手动入账') }}</h2>
            <div class="space-y-3">
              <select
                class="w-full bg-transparent border border-outline-variant rounded-md px-3 py-2 text-body-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option>{{ t('选择费用类型...') }}</option>
                <option>{{ t('房租') }}</option>
                <option>{{ t('电费') }}</option>
                <option>{{ t('水费') }}</option>
                <option>{{ t('宽带费') }}</option>
                <option>{{ t('赔偿金') }}</option>
              </select>
              <div class="flex gap-2">
                <div class="relative flex-1">
                  <span
                    class="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant font-num-md"
                    >¥</span
                  >
                  <input
                    class="w-full bg-transparent border border-outline-variant rounded-md pl-8 pr-3 py-2 text-body-md font-num-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                    placeholder="0.00"
                    type="number"
                  />
                </div>
                <button
                  class="bg-primary text-on-primary px-4 py-2 rounded-md font-label-lg hover:bg-primary/90 transition-colors shadow-sm"
                >
                  {{ t('添加') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
