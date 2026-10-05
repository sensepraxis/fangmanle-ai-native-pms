<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 协议客工作台：合作企业 · 企业协议价阶梯（量价置换）· 挂账 · 价格刚性
 * 与常住「入住天数折扣」明确拆分
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt, ORDER_ST_CN, ORDER_ST_PILL, PAY_CN, PAY_PILL, toast } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const loadError = ref('')
const summary = ref<any>({})
const companies = ref<any[]>([])
const recent = ref<any[]>([])
const selectedId = ref<number | null>(null)
const arLedgers = ref<any[]>([])
const arSummary = ref<any>({})
const settleAmt = ref<Record<number, number>>({})
const settleRef = ref<Record<number, string>>({})
const settling = ref(false)

const selected = computed(
  () => companies.value.find((c) => c.id === selectedId.value) || companies.value[0] || null,
)

async function load() {
  loadError.value = ''
  try {
    const [data, ar] = await Promise.all([
      api.agreementsBoard(hotelStore.hotelId),
      api.arBoard(hotelStore.hotelId).catch(() => null),
    ])
    summary.value = data?.summary || {}
    companies.value = data?.companies || []
    recent.value = data?.recent_orders || []
    arLedgers.value = ar?.ledgers || []
    arSummary.value = ar?.summary || {}
    if (!selectedId.value && companies.value.length) {
      selectedId.value = companies.value[0].id
    }
  } catch (e: any) {
    loadError.value = e?.message || t('加载失败')
    companies.value = []
    recent.value = []
  }
}

async function doSettle(led: any) {
  const amt = Number(settleAmt.value[led.ar_ledger_id] || 0)
  if (amt <= 0) {
    toast(t('请输入核销金额'), false)
    return
  }
  settling.value = true
  try {
    await api.arSettle(led.ar_ledger_id, {
      amount: amt,
      ref_no: settleRef.value[led.ar_ledger_id] || undefined,
      note: '协议回款核销',
    })
    toast(t('已核销'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('核销失败'), false)
  } finally {
    settling.value = false
  }
}

function volumeLabel(t: any) {
  const mn = t.min_annual_nights ?? 0
  const mx = t.max_annual_nights
  if (mx == null) return `年累计 ≥${mn} 间夜`
  return `年累计 ${mn}–${mx} 间夜`
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end mb-8 flex-wrap gap-3">
      <div>
        <h1 class="font-display-lg text-display-lg font-bold text-on-surface mb-2">
          {{ t('协议客 · 合作企业') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('企业协议价 · 量价阶梯 · 挂账结算 · 价格刚性（不随淡旺季波动）· 停留可长可短') }}
        </p>
      </div>
      <div class="flex flex-col items-end gap-3">
        <OrdersFlowNav mode="base" hide-back />
        <div class="flex gap-2">
          <button
            type="button"
            class="flex items-center gap-2 px-4 py-2 border border-outline rounded-lg text-on-surface font-label-lg hover:bg-surface-container-low"
            @click="router.push({ path: '/orders', query: { source: 'agreement' } })"
          >
            <span class="material-symbols-outlined text-[18px]">list_alt</span>
            {{ t('协议客订单') }}
          </button>
          <button
            type="button"
            class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary/90 shadow-sm"
            @click="load"
          >
            <span class="material-symbols-outlined text-[18px]">refresh</span>
            {{ t('刷新') }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="loadError" class="text-sm text-error mb-4">{{ loadError }}</p>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
        <div class="text-xs font-bold text-on-surface mb-1">{{ t('合作企业') }}</div>
        <div class="font-num-xl text-2xl font-bold">
          {{ summary.corp_count ?? companies.length }}
        </div>
      </div>
      <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
        <div class="text-xs font-bold text-on-surface mb-1">{{ t('结算方式') }}</div>
        <div class="text-lg font-semibold text-on-surface">
          {{ summary.settlement_default || t('挂账') }}
        </div>
      </div>
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 md:col-span-2"
      >
        <div class="text-xs font-bold text-on-surface mb-1">{{ t('定价逻辑') }}</div>
        <div class="text-sm text-on-surface leading-relaxed">
          {{ summary.price_policy || t('刚性协议价') }}；{{ summary.ladder_hint || t('量价阶梯') }}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-3">
        <h2
          class="font-headline-md text-headline-md font-bold text-on-surface flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-primary">handshake</span>
          {{ t('合作企业') }}
        </h2>
        <button
          v-for="c in companies"
          :key="c.id"
          type="button"
          class="text-left rounded-xl border p-4 transition-colors"
          :class="
            selected?.id === c.id
              ? 'border-primary bg-primary/5 shadow-sm'
              : 'border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low'
          "
          @click="selectedId = c.id"
        >
          <div class="flex justify-between items-start gap-2">
            <div>
              <div class="font-bold text-on-surface">{{ c.name }}</div>
              <div class="text-xs text-on-surface-variant mt-1">
                {{ c.code }} · {{ c.industry || t('企业') }}
              </div>
            </div>
            <span
              class="text-[10px] px-2 py-0.5 rounded bg-sky-100 text-sky-800 border border-sky-200 shrink-0"
              >{{ t('挂账') }}</span
            >
          </div>
          <div class="mt-3 flex flex-wrap gap-2 text-[11px]">
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">{{
              t('刚性价')
            }}</span>
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">
              YTD {{ c.used_nights_ytd }}/{{ c.annual_commit_nights }} {{ t('间') }}{{ t('夜') }}
            </span>
            <span v-if="c.active_tier" class="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary">{{
              c.active_tier
            }}</span>
          </div>
        </button>
        <p v-if="!companies.length" class="text-sm text-on-surface-variant">
          {{ t('暂无合作企业数据') }}
        </p>
      </div>

      <div class="col-span-12 lg:col-span-8 flex flex-col gap-4">
        <template v-if="selected">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
          >
            <div class="flex flex-wrap justify-between gap-3 mb-4">
              <div>
                <h2 class="font-headline-md text-headline-md font-bold text-on-surface">
                  {{ selected.name }}
                </h2>
                <p class="text-sm text-on-surface-variant mt-1">
                  {{ t('联系') }}{{ t('人') }} {{ selected.contact_name || '—' }}
                  <span v-if="selected.contact_phone"> · {{ selected.contact_phone }}</span>
                  · {{ t('有效期') }} {{ selected.valid_from || '—' }} ~
                  {{ selected.valid_to || '—' }}
                </p>
              </div>
              <div class="flex flex-wrap gap-2 items-start">
                <span
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-sky-100 text-sky-900 border border-sky-200"
                >
                  <span class="material-symbols-outlined text-[14px]">account_balance</span>
                  {{ t('结算：挂账') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200"
                >
                  <span class="material-symbols-outlined text-[14px]">lock</span>
                  {{ t('价格刚性') }}</span
                >
              </div>
            </div>
            <p class="text-sm text-on-surface-variant mb-4">
              {{ selected.note || summary.stay_hint }}
            </p>
            <div class="h-2 rounded-full bg-surface-container-high overflow-hidden mb-1">
              <div
                class="h-full bg-primary/70 rounded-full transition-all"
                :style="{ width: Math.min(100, selected.fulfillment_pct || 0) + '%' }"
              />
            </div>
            <div class="text-xs text-on-surface-variant">
              {{ t('年承诺履行') }} {{ selected.fulfillment_pct }}%（{{
                selected.used_nights_ytd
              }}
              / {{ selected.annual_commit_nights }} {{ t('间') }}{{ t('夜）') }}
            </div>
          </div>

          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
          >
            <h3
              class="font-headline-md text-headline-md font-bold text-on-surface mb-1 flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-primary">stairs</span>
              {{ t('企业协议价阶梯（量价置换）') }}
            </h3>
            <p class="text-xs text-on-surface-variant mb-5">
              {{
                t(
                  '按年累计间夜换档；合同期内固定价，不随淡旺季浮动。区别于常住客「入住天数折扣」。',
                )
              }}
            </p>

            <div v-for="block in selected.ladders" :key="block.room_type_id" class="mb-6 last:mb-0">
              <div class="flex items-baseline justify-between mb-2">
                <div class="font-bold text-on-surface">{{ block.room_type_name }}</div>
                <div class="text-xs text-on-surface-variant">
                  {{ t('门市参考') }} {{ block.base_price != null ? fmt(block.base_price) : '—' }}
                </div>
              </div>
              <div class="overflow-x-auto rounded-lg border border-outline-variant">
                <table class="w-full text-left text-sm">
                  <thead class="bg-surface-container-low text-on-surface-variant text-xs">
                    <tr>
                      <th class="p-3 font-medium">{{ t('档位') }}</th>
                      <th class="p-3 font-medium">{{ t('年累计间夜门槛') }}</th>
                      <th class="p-3 font-medium">{{ t('协议价 / 晚') }}</th>
                      <th class="p-3 font-medium">{{ t('淡旺季') }}</th>
                      <th class="p-3 font-medium">{{ t('状态') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="tag in block.tiers"
                      :key="tag.tier_name"
                      class="border-t border-outline-variant/60"
                      :class="tag.active ? 'bg-primary/5' : ''"
                    >
                      <td class="p-3 font-medium">{{ tag.tier_name }}</td>
                      <td class="p-3 text-on-surface-variant">{{ volumeLabel(t) }}</td>
                      <td class="p-3 font-num-md">{{ fmt(tag.contract_price) }}</td>
                      <td class="p-3">
                        <span class="text-xs text-emerald-700">{{ t('不浮动（刚性）') }}</span>
                      </td>
                      <td class="p-3">
                        <span
                          v-if="tag.active"
                          class="text-xs px-2 py-0.5 rounded bg-primary/15 text-primary font-medium"
                          >{{ t('当前档') }}</span
                        >
                        <span v-else class="text-xs text-on-surface-variant">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <p v-if="!selected.ladders?.length" class="text-sm text-on-surface-variant">
              {{ t('暂无阶梯价') }}
            </p>
          </div>
        </template>
        <p v-else class="text-sm text-on-surface-variant">{{ t('请选择左侧合作企业') }}</p>

        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex justify-between items-center mb-4">
            <h3
              class="font-headline-md text-headline-md font-bold text-on-surface flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-primary">receipt_long</span
              >{{ t('近期协议客订单') }}
            </h3>
            <span class="text-xs text-on-surface-variant">{{ t('可长可短 · 统一挂账') }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs text-on-surface-variant border-b border-outline-variant">
                <tr>
                  <th class="py-2 pr-3">{{ t('单号') }}</th>
                  <th class="py-2 pr-3">{{ t('入住人') }}</th>
                  <th class="py-2 pr-3">{{ t('房型') }}</th>
                  <th class="py-2 pr-3">{{ t('晚数') }}</th>
                  <th class="py-2 pr-3">{{ t('金额') }}</th>
                  <th class="py-2 pr-3">{{ t('结算') }}</th>
                  <th class="py-2">{{ t('状态') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="o in recent" :key="o.id" class="border-b border-outline-variant/50">
                  <td class="py-2.5 pr-3 font-medium">{{ o.order_no }}</td>
                  <td class="py-2.5 pr-3">{{ o.guest_name }}</td>
                  <td class="py-2.5 pr-3 text-on-surface-variant">{{ o.room_type_name }}</td>
                  <td class="py-2.5 pr-3">
                    <span class="font-num-md">{{ o.nights }}</span>
                    <span class="text-xs text-on-surface-variant ml-1">{{
                      o.nights >= 7 ? t('长住亦可') : t('短住')
                    }}</span>
                  </td>
                  <td class="py-2.5 pr-3 font-num-md">{{ fmt(o.total_amount) }}</td>
                  <td class="py-2.5 pr-3">
                    <span :class="PAY_PILL[o.payment_status] || 'pill pill-amber'">
                      {{ t(PAY_CN[o.payment_status] || '挂账') }}</span
                    >
                  </td>
                  <td class="py-2.5">
                    <span :class="ORDER_ST_PILL[o.status] || 'pill'">{{
                      t(ORDER_ST_CN[o.status] || o.status)
                    }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="!recent.length" class="text-sm text-on-surface-variant py-4">
              {{ t('暂无协议客订单') }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- AR 核销 -->
    <div
      class="mt-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
    >
      <div class="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h3 class="font-headline-md font-bold text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">account_balance_wallet</span
          >{{ t('协议 AR 挂账核销') }}
        </h3>
        <span class="text-sm text-on-surface-variant">
          未结余额合计 {{ fmt(arSummary.open_balance || 0) }} · {{ arSummary.corp_count || 0 }} 家
        </span>
      </div>
      <div v-if="!arLedgers.length" class="text-sm text-on-surface-variant">
        {{ t('暂无 AR 账本') }}
      </div>
      <div
        v-for="led in arLedgers"
        :key="led.ar_ledger_id"
        class="border border-outline-variant rounded-lg p-4 mb-3"
      >
        <div class="flex justify-between flex-wrap gap-2 mb-2">
          <div>
            <b>{{ led.corp_name }}</b>
            <span class="text-xs text-on-surface-variant ml-2"
              >{{ led.corp_code }} · {{ led.settle_cycle }}</span
            >
          </div>
          <div class="text-sm">
            {{ t('余额') }} <b class="text-primary">{{ fmt(led.balance) }}</b> · 授信占用
            {{ fmt(led.credit_used) }} / {{ fmt(led.credit_limit) }}
          </div>
        </div>
        <div class="flex flex-wrap gap-2 items-end">
          <div>
            <label class="text-xs text-on-surface-variant">{{ t('核销金额') }}</label>
            <input
              v-model.number="settleAmt[led.ar_ledger_id]"
              class="block border border-outline-variant rounded-lg px-3 py-2 text-sm"
              type="number"
              min="0"
              step="0.01"
              :placeholder="String(led.balance || 0)"
            />
          </div>
          <div>
            <label class="text-xs text-on-surface-variant">{{ t('打款单号') }}</label>
            <input
              v-model="settleRef[led.ar_ledger_id]"
              class="block border border-outline-variant rounded-lg px-3 py-2 text-sm"
              :placeholder="t('银行回单号')"
            />
          </div>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="settling || !(led.balance > 0)"
            @click="doSettle(led)"
          >
            {{ t('确认核销') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
