<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 营销获客 · 私域运营
 * 线索跟进 → 企微承接 → 转预订到店
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AcquisitionLoopPanel from '../../components/AcquisitionLoopPanel.vue'

type TabId = 'leads' | 'funnel' | 'attribution'

const route = useRoute()
const router = useRouter()

const tabs: { id: TabId; label: string; icon: string }[] = [
  { id: 'leads', label: t('线索列表'), icon: 'person_search' },
  { id: 'funnel', label: t('互动转化'), icon: 'filter_alt' },
  { id: 'attribution', label: t('归因分析'), icon: 'payments' },
]

const activeTab = ref<TabId>('leads')
const board = ref<any>(null)
const roiData = ref<any>(null)
const bindings = ref<any[]>([])
const loading = ref(false)

const funnel = computed(() => board.value?.funnel || {})
const metrics = computed(() => board.value?.metrics || {})
const primaryBinding = computed(() => bindings.value[0] || null)

const cvr = computed(() => {
  const total = metrics.value.leads || 0
  const booked = (funnel.value.booked || 0) + (funnel.value.arrived || 0)
  return total > 0 ? `${Math.round((booked / total) * 1000) / 10}%` : '—'
})

const funnelCards = computed(() => [
  { label: t('待跟进'), value: funnel.value.new ?? 0, hint: t('新线索待认领'), tone: 'primary' },
  {
    label: t('跟进中'),
    value: funnel.value.claimed ?? 0,
    hint: t('已认领未进私域'),
    tone: 'default',
  },
  {
    label: t('已进私域'),
    value: funnel.value.private ?? 0,
    hint: t('企微/私域承接'),
    tone: 'default',
  },
  {
    label: t('已转预订/到店'),
    value: (funnel.value.booked ?? 0) + (funnel.value.arrived ?? 0),
    hint: t('闭环成交'),
    tone: 'tertiary',
  },
  { label: t('闭环转化率'), value: cvr.value, hint: t('成交 / 线索'), tone: 'highlight' },
])

const funnelSteps = computed(() => [
  {
    label: t('平台引流'),
    sub: t('Webhook / 手工录入'),
    count: metrics.value.leads ?? 0,
    active: true,
  },
  { label: t('认领跟进'), sub: t('销售跟进线索'), count: funnel.value.claimed ?? 0, active: false },
  { label: t('进私域'), sub: t('添加管家微信'), count: funnel.value.private ?? 0, active: false },
  {
    label: t('转预订到店'),
    sub: t('人工确认后下单'),
    count: (funnel.value.booked ?? 0) + (funnel.value.arrived ?? 0),
    active: false,
  },
])

function syncTabFromRoute() {
  const t = route.query.tab as string
  if (t === 'trade') return
  if (t === 'funnel' || t === 'attribution' || t === 'leads') activeTab.value = t
}

function selectTab(id: TabId) {
  activeTab.value = id
  const q: Record<string, string> = id === 'leads' ? {} : { tab: id }
  router.replace({ path: '/acquisition', query: Object.keys(q).length ? q : undefined })
}

async function loadBoard() {
  loading.value = true
  try {
    const hid = hotelStore.hotelId
    const [b, bind, roi] = await Promise.all([
      api.acquisitionBoard(hid),
      api.acquisitionChannelBindings(hid),
      api.acquisitionRoiAttribution(hid),
    ])
    board.value = b
    bindings.value = bind || []
    roiData.value = roi
  } catch {
    board.value = null
    bindings.value = []
    roiData.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  syncTabFromRoute()
  loadBoard()
})
watch(() => hotelStore.hotelId, loadBoard)
watch(() => route.query.tab, syncTabFromRoute)
</script>

<template>
  <div class="space-y-6">
    <!-- 页头：对齐 one-id / roi 原型 -->
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ t('私域运营') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('线索认领、企微承接、转预订到店 — 私域转化工作台') }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div
          class="bg-surface-container-low px-4 py-2 rounded-lg border border-outline-variant flex items-center gap-2"
        >
          <span
            class="w-2 h-2 rounded-full"
            :class="primaryBinding ? 'bg-green-500' : 'bg-orange-400'"
          ></span>
          <span class="font-label-lg text-label-lg text-on-surface-variant">
            {{ primaryBinding ? t('渠道 Webhook 已绑定') : t('未配置 Webhook') }}</span
          >
        </div>
      </div>
    </div>

    <!-- Tab：胶囊分段，贴近原型筛选条 -->
    <div
      class="inline-flex p-1 rounded-xl bg-surface-container-low border border-outline-variant gap-1"
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
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col justify-between"
        >
          <div>
            <div class="flex items-center gap-3 mb-4">
              <div
                class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary"
              >
                <span class="material-symbols-outlined">hub</span>
              </div>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('渠道接入状态') }}
              </h2>
            </div>
            <div class="flex items-center gap-2 mb-2">
              <span
                class="w-2 h-2 rounded-full"
                :class="primaryBinding ? 'bg-green-500' : 'bg-orange-400'"
              ></span>
              <span class="font-body-lg text-body-lg text-on-surface font-semibold">
                {{ primaryBinding ? t('已绑定') : t('待配置') }}</span
              >
            </div>
            <p class="font-body-md text-body-md text-on-surface-variant mb-2">
              {{ t('账户：') }}
              <span class="text-on-surface">{{
                primaryBinding?.xhs_ad_account_id || primaryBinding?.label || '—'
              }}</span>
            </p>
            <p class="font-body-md text-body-md text-on-surface-variant mb-6">
              {{ t('Webhook 验签：') }}
              <span class="text-on-surface">{{
                primaryBinding?.webhook_secret_set ? t('已配置') : t('未配置')
              }}</span>
            </p>
          </div>
          <div class="bg-surface-container-low rounded-lg p-4 flex justify-between items-center">
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('待认领线索') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary mt-1">{{ funnel.new ?? 0 }}</p>
            </div>
            <div class="text-right">
              <p class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('Webhook 入库') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface mt-1">
                {{ metrics.webhook_leads ?? 0 }}
              </p>
            </div>
          </div>
        </div>

        <div
          class="col-span-12 md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface mb-6">
            {{ t('今日概览') }}
          </h2>
          <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="p-4 border border-outline-variant rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('线索总量') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">{{ metrics.leads ?? 0 }}</p>
            </div>
            <div class="p-4 border border-outline-variant rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('已进私域') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">{{ funnel.private ?? 0 }}</p>
            </div>
            <div class="p-4 border border-outline-variant rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('闭环转化率') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary">{{ cvr }}</p>
            </div>
          </div>
          <div class="bg-[#e8f0fe] rounded-lg p-4 border border-[#d2e3fc]">
            <h4 class="font-label-lg text-label-lg text-primary mb-1">{{ t('操作提示') }}</h4>
            <p class="font-body-md text-body-md text-on-surface-variant">
              {{
                t('公域种草与投放在对应入口完成；本页聚焦线索认领 → 私域承接 → 转预订 → 到店闭环。')
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
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">list_alt</span>
            {{ t('线索工作台') }}
          </h2>
          <span
            class="bg-error-container text-on-error-container text-[10px] px-2 py-1 rounded-full font-bold"
          >
            {{ funnel.new ?? 0 }} {{ t('待跟进') }}
          </span>
        </div>
        <div class="p-4 md:p-5">
          <AcquisitionLoopPanel simple view="leads" focus="overview" />
        </div>
      </div>
    </section>

    <!-- 互动转化 -->
    <section v-show="activeTab === 'funnel'" class="space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <div
          v-for="c in funnelCards"
          :key="c.label"
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm"
          :class="{
            'border-l-4 border-l-primary': c.tone === 'primary',
            'border-l-4 border-l-tertiary': c.tone === 'tertiary',
            'ring-1 ring-primary/30 bg-primary-fixed/20': c.tone === 'highlight',
          }"
        >
          <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">{{ c.label }}</p>
          <p
            class="font-num-xl text-num-xl"
            :class="
              c.tone === 'highlight' || c.tone === 'primary' ? 'text-primary' : 'text-on-surface'
            "
          >
            {{ c.value }}
          </p>
          <p class="text-xs text-on-surface-variant mt-2">{{ c.hint }}</p>
        </div>
      </div>

      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
      >
        <h2 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">account_tree</span>
          {{ t('私域转化漏斗') }}
        </h2>
        <p class="font-body-md text-body-md text-on-surface-variant mb-8 max-w-3xl">
          {{
            t('从 Webhook 入库到转预订到店的跟进路径。请按阶段推进，避免跳过人工确认房价与日期。')
          }}
        </p>
        <div class="relative flex items-start justify-between w-full max-w-4xl mx-auto mb-2 px-2">
          <div class="absolute left-8 right-8 top-5 h-0.5 bg-surface-variant z-0"></div>
          <div class="absolute left-8 top-5 h-0.5 bg-primary z-0" style="width: 28%"></div>
          <div
            v-for="(s, i) in funnelSteps"
            :key="s.label"
            class="relative z-10 flex flex-col items-center gap-2 flex-1"
          >
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center shadow-md text-sm font-bold"
              :class="
                i === 0
                  ? 'bg-primary text-on-primary'
                  : 'bg-surface text-on-surface-variant border-2 border-outline-variant'
              "
            >
              {{ s.count }}
            </div>
            <span
              class="font-label-lg text-label-lg whitespace-nowrap"
              :class="i === 0 ? 'text-primary font-bold' : 'text-on-surface'"
            >
              {{ s.label }}</span
            >
            <span class="font-body-md text-[12px] text-on-surface-variant text-center px-1">{{
              s.sub
            }}</span>
          </div>
        </div>
      </div>

      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden"
      >
        <div class="p-5 border-b border-outline-variant bg-surface-bright">
          <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('阶段明细') }}</h2>
        </div>
        <div class="p-4 md:p-5">
          <AcquisitionLoopPanel simple view="funnel" focus="funnel" />
        </div>
      </div>
    </section>

    <!-- 归因分析：对齐 roi.vue -->
    <section v-show="activeTab === 'attribution'" class="space-y-6">
      <div class="flex justify-between items-end flex-wrap gap-4">
        <div>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('获客渠道 ROI 复盘') }}
          </h2>
          <p v-if="roiData?.summary" class="text-body-md text-on-surface-variant mt-2">
            {{ t('线索') }} {{ roiData.summary.leads }} {{ t('条 · 成交') }}
            {{ roiData.summary.booked }} {{ t('条 ·') }} {{ t('投流') }} ¥{{
              roiData.summary.spend
            }}
            · ROI {{ roiData.summary.roi != null ? roiData.summary.roi + 'x' : '—' }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            type="button"
            class="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg bg-surface text-on-surface-variant hover:bg-surface-container-low transition-colors text-label-lg font-label-lg"
          >
            <span class="material-symbols-outlined text-[20px]">calendar_today</span>
            {{ t('近 30 天') }}
          </button>
        </div>
      </div>

      <div v-if="roiData" class="grid grid-cols-12 gap-6">
        <section
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h3 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('按广告计划归因') }}
          </h3>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b border-outline-variant">
                <th class="pb-2 font-medium">{{ t('计划') }}</th>
                <th class="pb-2 font-medium">{{ t('线索') }}</th>
                <th class="pb-2 font-medium">{{ t('成交') }}</th>
                <th class="pb-2 font-medium">ROI</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in roiData.by_plan"
                :key="p.plan_id"
                class="border-b border-outline-variant/30 hover:bg-surface-container-low transition-colors"
              >
                <td class="py-3">{{ p.campaign_name || p.plan_id }}</td>
                <td>{{ p.leads }}</td>
                <td>{{ p.booked }}</td>
                <td class="font-semibold text-primary">{{ p.roi != null ? p.roi + 'x' : '—' }}</td>
              </tr>
              <tr v-if="!roiData.by_plan?.length">
                <td colspan="4" class="py-6 text-on-surface-variant text-center">
                  {{ t('暂无计划归因（需 Webhook 带 plan_id）') }}
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h3 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('按种草笔记归因') }}
          </h3>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b border-outline-variant">
                <th class="pb-2 font-medium">{{ t('笔记') }}</th>
                <th class="pb-2 font-medium">{{ t('线索') }}</th>
                <th class="pb-2 font-medium">{{ t('成交') }}</th>
                <th class="pb-2 font-medium">{{ t('收入') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="n in roiData.by_note"
                :key="n.key"
                class="border-b border-outline-variant/30 hover:bg-surface-container-low transition-colors"
              >
                <td class="py-3 max-w-[200px] truncate">{{ n.key }}</td>
                <td>{{ n.leads }}</td>
                <td>{{ n.booked }}</td>
                <td>¥{{ n.rev }}</td>
              </tr>
              <tr v-if="!roiData.by_note?.length">
                <td colspan="4" class="py-6 text-on-surface-variant text-center">
                  {{ t('暂无笔记归因') }}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <div
        v-else
        class="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 text-center text-on-surface-variant"
      >
        {{ t('暂无归因数据') }}
      </div>

      <div
        class="border border-tertiary-fixed-dim bg-gradient-to-r from-tertiary-container/10 to-surface rounded-xl p-5 shadow-sm relative overflow-hidden flex items-start gap-4"
      >
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
        <div class="p-2 bg-surface rounded-full shadow-sm text-tertiary shrink-0">
          <span class="material-symbols-outlined">auto_awesome</span>
        </div>
        <div class="flex-1">
          <h3 class="text-headline-md font-headline-md text-on-surface mb-1">
            {{ t('归因说明') }}
          </h3>
          <p class="text-body-md text-on-surface-variant">
            {{
              t(
                'ROI 按线索上的广告计划 / 种草笔记汇总。种草内容在小红书侧发布，PMS 只做成交归因与复盘。',
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
</style>
