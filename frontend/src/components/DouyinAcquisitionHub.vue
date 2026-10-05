<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 营销获客 · 抖音（线索 + 交易双轨）
 * Tab：线索列表 | 互动转化 | 团购交易 | 归因分析
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import AcquisitionLoopPanel from './AcquisitionLoopPanel.vue'

type TabId = 'leads' | 'funnel' | 'trade' | 'attribution'

const route = useRoute()
const router = useRouter()

const tabs: { id: TabId; label: string; icon: string }[] = [
  { id: 'leads', label: t('线索列表'), icon: 'person_search' },
  { id: 'funnel', label: t('互动转化'), icon: 'filter_alt' },
  { id: 'trade', label: t('团购交易'), icon: 'confirmation_number' },
  { id: 'attribution', label: t('归因分析'), icon: 'payments' },
]

const activeTab = ref<TabId>('leads')
const board = ref<any>(null)
const tradeBoard = ref<any>(null)
const roiData = ref<any>(null)
const bindings = ref<any[]>([])
const loading = ref(false)

const funnel = computed(() => board.value?.funnel || {})
const metrics = computed(() => board.value?.metrics || {})
const tradeFunnel = computed(() => tradeBoard.value?.funnel || {})
const tradeMetrics = computed(() => tradeBoard.value?.metrics || {})
const primaryBinding = computed(() => bindings.value[0] || null)

const cvr = computed(() => {
  const total = metrics.value.leads || 0
  const booked = (funnel.value.booked || 0) + (funnel.value.arrived || 0)
  return total > 0 ? `${Math.round((booked / total) * 1000) / 10}%` : '—'
})

const leadFunnelCards = computed(() => [
  { label: t('待跟进'), value: funnel.value.new ?? 0, hint: t('留资待认领') },
  { label: t('跟进中'), value: funnel.value.claimed ?? 0, hint: t('已认领') },
  { label: t('已进私域'), value: funnel.value.private ?? 0, hint: t('企微承接') },
  {
    label: t('已转预订'),
    value: (funnel.value.booked ?? 0) + (funnel.value.arrived ?? 0),
    hint: t('线索路成交'),
  },
])

const tradeFunnelSteps = computed(() => [
  { label: t('浏览量'), value: tradeFunnel.value.views ?? 0, sub: '' },
  { label: t('点击量'), value: tradeFunnel.value.clicks ?? 0, sub: '18.6%' },
  { label: t('券销量'), value: tradeFunnel.value.sold ?? 0, sub: '14.2%' },
  {
    label: t('已核销'),
    value: tradeFunnel.value.verified ?? 0,
    sub: `${tradeMetrics.value.verify_rate ?? 0}%`,
  },
])

const leadSteps = computed(() => [
  { label: t('平台引流'), sub: t('来客 Webhook / 手工录入'), count: metrics.value.leads ?? 0 },
  { label: t('认领跟进'), sub: t('销售跟进'), count: funnel.value.claimed ?? 0 },
  { label: t('进私域'), sub: t('添加管家微信'), count: funnel.value.private ?? 0 },
  {
    label: t('转预订'),
    sub: t('人工确认下单'),
    count: (funnel.value.booked ?? 0) + (funnel.value.arrived ?? 0),
  },
])

function syncTabFromRoute() {
  const t = route.query.tab as string
  if (t === 'funnel' || t === 'trade' || t === 'attribution' || t === 'leads') activeTab.value = t
}

function selectTab(id: TabId) {
  activeTab.value = id
  const q: Record<string, string> = { channel: 'douyin' }
  if (id !== 'leads') q.tab = id
  router.replace({ path: '/acquisition', query: q })
}

function goVerify() {
  router.push('/c5-frontdesk/voucher-verification')
}

function goOrders() {
  router.push('/orders')
}

async function loadAll() {
  loading.value = true
  try {
    const hid = hotelStore.hotelId
    const [b, bind, roi, trade] = await Promise.all([
      api.acquisitionBoard(hid, 'douyin'),
      api.acquisitionChannelBindings(hid, 'douyin'),
      api.acquisitionRoiAttribution(hid, 'douyin'),
      api.acquisitionDouyinTradeBoard(hid),
    ])
    board.value = b
    bindings.value = bind || []
    roiData.value = roi
    tradeBoard.value = trade
  } catch {
    board.value = null
    bindings.value = []
    roiData.value = null
    tradeBoard.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  syncTabFromRoute()
  loadAll()
})
watch(() => hotelStore.hotelId, loadAll)
watch(() => route.query.tab, syncTabFromRoute)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <div class="flex items-center gap-2 text-on-surface-variant mb-1">
          <span
            class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#1A1A1A]/10 text-[#1A1A1A] text-[12px] font-bold"
            >{{ t('抖') }}</span
          >
          <span class="text-label-lg font-label-lg">{{ t('营销获客 / 抖音') }}</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ t('抖音获客') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('线索路：留资跟进转预订 · 交易路：团购券售卖 → 到店核销成单') }}
        </p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div
          class="bg-surface-container-low px-4 py-2 rounded-lg border border-outline-variant flex items-center gap-2"
        >
          <span
            class="w-2 h-2 rounded-full"
            :class="primaryBinding ? 'bg-green-500' : 'bg-orange-400'"
          ></span>
          <span class="font-label-lg text-label-lg text-on-surface-variant">
            {{ primaryBinding ? t('来客已绑定') : t('未配置 OAuth') }}</span
          >
        </div>
        <button
          type="button"
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:opacity-90"
          @click="goVerify"
        >
          {{ t('去核销') }}
        </button>
      </div>
    </div>

    <div
      class="inline-flex p-1 rounded-xl bg-surface-container-low border border-outline-variant gap-1 flex-wrap"
    >
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="px-4 py-2 rounded-lg font-label-lg text-label-lg transition-colors flex items-center gap-2"
        :class="
          activeTab === tab.id
            ? 'bg-surface-container-lowest text-on-surface shadow-sm border border-outline-variant'
            : 'text-on-surface-variant hover:text-on-surface'
        "
        @click="selectTab(tab.id)"
      >
        <span class="material-symbols-outlined text-[18px]">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </div>

    <p v-if="loading" class="font-body-md text-body-md text-on-surface-variant">
      {{ t('加载中…') }}
    </p>

    <!-- 线索列表 -->
    <section v-show="activeTab === 'leads'" class="space-y-6">
      <div class="grid grid-cols-12 gap-6">
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex items-center gap-3 mb-4">
            <div
              class="w-10 h-10 rounded-full bg-[#1A1A1A]/10 flex items-center justify-center font-bold text-sm"
            >
              {{ t('来') }}
            </div>
            <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('来客账户') }}</h2>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-2">
            {{ t('商家 ID：')
            }}<span class="text-on-surface">{{
              primaryBinding?.xhs_ad_account_id || tradeBoard?.poi?.merchant_id || '—'
            }}</span>
          </p>
          <p class="font-body-md text-body-md text-on-surface-variant mb-4">
            {{ t('状态：')
            }}<span class="text-on-surface">{{ tradeBoard?.poi?.status || t('待绑定') }}</span>
          </p>
          <div class="bg-surface-container-low rounded-lg p-4 flex justify-between">
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('待跟进线索') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary mt-1">{{ funnel.new ?? 0 }}</p>
            </div>
            <div class="text-right">
              <p class="font-label-lg text-label-lg text-on-surface-variant">{{ t('线索总量') }}</p>
              <p class="font-num-xl text-num-xl text-on-surface mt-1">{{ metrics.leads ?? 0 }}</p>
            </div>
          </div>
        </div>
        <div
          class="col-span-12 md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface mb-4">
            {{ t('双轨概览') }}
          </h2>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div class="p-4 border border-outline-variant rounded-lg border-l-4 border-l-primary">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('线索路 · 闭环转化率') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary">{{ cvr }}</p>
            </div>
            <div class="p-4 border border-outline-variant rounded-lg border-l-4 border-l-tertiary">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('交易路 · 待核销') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">
                {{ tradeMetrics.pending_verify ?? 0 }}
              </p>
            </div>
          </div>
          <div class="bg-surface-container-low rounded-lg p-4 border border-outline-variant">
            <p class="font-body-md text-body-md text-on-surface-variant">
              {{
                t(
                  '短视频/直播/POI 在来客侧运营。PMS 接收留资线索（线索路）与团购订单（交易路），最终在订单中心汇合。',
                )
              }}
            </p>
          </div>
        </div>
      </div>
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden"
      >
        <div
          class="p-5 border-b border-outline-variant bg-surface-bright flex justify-between items-center"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('线索工作台') }}</h2>
          <span
            class="bg-error-container text-on-error-container text-[10px] px-2 py-1 rounded-full font-bold"
          >
            {{ funnel.new ?? 0 }} {{ t('待跟进') }}
          </span>
        </div>
        <div class="p-4 md:p-5">
          <AcquisitionLoopPanel simple view="leads" focus="overview" channel="douyin" />
        </div>
      </div>
    </section>

    <!-- 互动转化 -->
    <section v-show="activeTab === 'funnel'" class="space-y-6">
      <div class="grid grid-cols-12 gap-6">
        <div
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface mb-4">
            {{ t('线索路 · 私域漏斗') }}
          </h2>
          <div class="grid grid-cols-2 gap-3 mb-6">
            <div
              v-for="c in leadFunnelCards"
              :key="c.label"
              class="p-3 border border-outline-variant rounded-lg"
            >
              <p class="text-xs text-on-surface-variant">{{ c.label }}</p>
              <p class="font-num-xl text-num-xl text-on-surface">{{ c.value }}</p>
            </div>
          </div>
          <div class="relative flex items-start justify-between max-w-lg mx-auto">
            <div
              v-for="(s, i) in leadSteps"
              :key="s.label"
              class="flex flex-col items-center gap-1 flex-1 text-center"
            >
              <div
                class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
                :class="i === 0 ? 'bg-primary text-on-primary' : 'border-2 border-outline-variant'"
              >
                {{ s.count }}
              </div>
              <span class="text-xs font-medium">{{ s.label }}</span>
            </div>
          </div>
        </div>
        <div
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface mb-4">
            {{ t('交易路 · 券转化漏斗（近30天）') }}
          </h2>
          <div class="flex justify-between items-center px-2">
            <template v-for="(s, i) in tradeFunnelSteps" :key="s.label">
              <div class="flex flex-col items-center z-10">
                <div
                  class="w-12 h-12 rounded-full bg-surface-container border-2 border-outline-variant flex items-center justify-center mb-1"
                >
                  <span class="material-symbols-outlined text-[18px] text-primary"
                    >trending_up</span
                  >
                </div>
                <span class="text-xs text-on-surface-variant">{{ s.label }}</span>
                <span class="font-num-md font-bold text-primary">{{ s.value }}</span>
                <span v-if="s.sub" class="text-[10px] text-on-surface-variant">{{ s.sub }}</span>
              </div>
              <div
                v-if="i < tradeFunnelSteps.length - 1"
                class="flex-1 h-0.5 bg-outline-variant mx-1 mt-[-20px]"
              ></div>
            </template>
          </div>
        </div>
      </div>
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden"
      >
        <div class="p-5 border-b border-outline-variant bg-surface-bright">
          <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('线索阶段明细') }}</h2>
        </div>
        <div class="p-4 md:p-5">
          <AcquisitionLoopPanel simple view="funnel" focus="funnel" channel="douyin" />
        </div>
      </div>
    </section>

    <!-- 团购交易 -->
    <section v-show="activeTab === 'trade'" class="space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm"
        >
          <p class="font-label-lg text-label-lg text-on-surface-variant">{{ t('券 GMV') }}</p>
          <p class="font-num-xl text-num-xl text-on-surface">¥{{ tradeMetrics.gmv ?? 0 }}</p>
        </div>
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm"
        >
          <p class="font-label-lg text-label-lg text-on-surface-variant">{{ t('核销收入') }}</p>
          <p class="font-num-xl text-num-xl text-primary">¥{{ tradeMetrics.verified_rev ?? 0 }}</p>
        </div>
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm border-l-4 border-l-tertiary"
        >
          <p class="font-label-lg text-label-lg text-on-surface-variant">{{ t('待核销') }}</p>
          <p class="font-num-xl text-num-xl text-on-surface">
            {{ tradeMetrics.pending_verify ?? 0 }}
          </p>
        </div>
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm"
        >
          <p class="font-label-lg text-label-lg text-on-surface-variant">{{ t('核销率') }}</p>
          <p class="font-num-xl text-num-xl text-on-surface">
            {{ tradeMetrics.verify_rate ?? 0 }}%
          </p>
        </div>
      </div>

      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden"
      >
        <div
          class="p-5 border-b border-outline-variant bg-surface-bright flex justify-between items-center flex-wrap gap-3"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">confirmation_number</span
            >{{ t('团购券套餐') }}
          </h2>
          <div class="flex gap-2">
            <button type="button" class="btn-outline" @click="goVerify">{{ t('去核销') }}</button>
            <button type="button" class="btn-outline" @click="goOrders">{{ t('订单中心') }}</button>
          </div>
        </div>
        <div class="p-4 space-y-4">
          <div
            v-for="c in tradeBoard?.coupons || []"
            :key="c.id"
            class="border border-outline-variant rounded-lg p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors flex-wrap gap-4"
          >
            <div class="flex items-center gap-4">
              <div
                class="w-12 h-12 rounded-md bg-primary-container text-on-primary-container flex items-center justify-center font-bold"
              >
                ¥{{ c.price }}
              </div>
              <div>
                <h4 class="font-label-lg text-label-lg text-on-surface">{{ c.name }}</h4>
                <p class="text-sm text-on-surface-variant">
                  有效期至 {{ c.expire }} · {{ c.status }}
                </p>
              </div>
            </div>
            <div class="flex gap-6 text-right text-sm">
              <div>
                <p class="text-on-surface-variant">{{ t('已售') }}</p>
                <p class="font-bold">{{ c.sold }}</p>
              </div>
              <div>
                <p class="text-on-surface-variant">{{ t('待核销') }}</p>
                <p class="font-bold text-tertiary">{{ c.pending_verify }}</p>
              </div>
              <div>
                <p class="text-on-surface-variant">{{ t('已核销') }}</p>
                <p class="font-bold">{{ c.verified }}</p>
              </div>
            </div>
          </div>
          <p v-if="!tradeBoard?.coupons?.length" class="text-center text-on-surface-variant py-8">
            {{ t('暂无团购券数据') }}
          </p>
        </div>
      </div>

      <div
        v-if="tradeBoard?.recent_orders?.length"
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
      >
        <h3 class="font-headline-md text-headline-md text-on-surface mb-4">
          {{ t('最近核销订单') }}
        </h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-on-surface-variant border-b">
              <th class="pb-2">{{ t('订单号') }}</th>
              <th class="pb-2">{{ t('客人') }}</th>
              <th class="pb-2">{{ t('入住') }}</th>
              <th class="pb-2">{{ t('金额') }}</th>
              <th class="pb-2">{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in tradeBoard.recent_orders"
              :key="o.id"
              class="border-b border-outline-variant/30"
            >
              <td class="py-2">{{ o.order_no }}</td>
              <td>{{ o.guest_name || '—' }}</td>
              <td>{{ o.check_in || '—' }}</td>
              <td>¥{{ o.total_amount }}</td>
              <td>{{ o.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bg-[#fef7e8] rounded-lg p-4 border border-[#f5dfa0]">
        <h4 class="font-label-lg text-label-lg text-on-surface mb-1">{{ t('交易路操作') }}</h4>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{
            t(
              '客人在抖音购买团购券 → PMS 同步券订单 → 到店后前台在「团购核销」扫券验真 → 匹配房型成单 → 订单中心可见。',
            )
          }}
        </p>
      </div>
    </section>

    <!-- 归因分析 -->
    <section v-show="activeTab === 'attribution'" class="space-y-6">
      <div class="flex justify-between items-end flex-wrap gap-4">
        <div>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('抖音双轨 ROI 复盘') }}
          </h2>
          <p v-if="roiData?.summary" class="text-body-md text-on-surface-variant mt-2">
            线索 {{ roiData.summary.leads }} 条 · 成交 {{ roiData.summary.booked }} 条 · 核销收入
            ¥{{ tradeMetrics.verified_rev ?? 0 }}
          </p>
        </div>
      </div>
      <div class="grid grid-cols-12 gap-6">
        <section
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h3 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('线索路 · 按计划/视频') }}
          </h3>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b">
                <th class="pb-2">{{ t('计划') }}</th>
                <th>{{ t('线索') }}</th>
                <th>{{ t('成交') }}</th>
                <th>ROI</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in roiData?.by_plan || []"
                :key="p.plan_id"
                class="border-b border-outline-variant/30"
              >
                <td class="py-2">{{ p.campaign_name || p.plan_id }}</td>
                <td>{{ p.leads }}</td>
                <td>{{ p.booked }}</td>
                <td>{{ p.roi != null ? p.roi + 'x' : '—' }}</td>
              </tr>
              <tr v-if="!roiData?.by_plan?.length">
                <td colspan="4" class="py-6 text-center text-on-surface-variant">
                  {{ t('暂无计划归因') }}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
        <section
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h3 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('交易路 · 团购 SKU') }}
          </h3>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b">
                <th class="pb-2">{{ t('套餐') }}</th>
                <th>{{ t('已售') }}</th>
                <th>{{ t('已核销') }}</th>
                <th>{{ t('待核销') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in tradeBoard?.coupons || []"
                :key="c.id"
                class="border-b border-outline-variant/30"
              >
                <td class="py-2 max-w-[180px] truncate">{{ c.name }}</td>
                <td>{{ c.sold }}</td>
                <td>{{ c.verified }}</td>
                <td>{{ c.pending_verify }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <div
        class="border border-tertiary-fixed-dim bg-gradient-to-r from-tertiary-container/10 to-surface rounded-xl p-5 relative overflow-hidden flex items-start gap-4"
      >
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
        <div class="flex-1">
          <h3 class="text-headline-md font-headline-md text-on-surface mb-1">
            {{ t('回传优化（第⑥步）') }}
          </h3>
          <p class="text-body-md text-on-surface-variant">
            {{
              t(
                '线索阶段变更与券核销成交将回传巨量/飞鱼，用于优化投放模型（当前环境暂未接真实 API）。',
              )
            }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.btn-outline {
  padding: 8px 14px;
  border: 1px solid var(--outline-variant, #c9ced8);
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-outline:hover {
  background: var(--surface-container-low, #f5f6f8);
}
</style>
