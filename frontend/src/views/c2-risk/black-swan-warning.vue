<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 经营风险预警 (Black Swan)：综合风险指数 + 黑天鹅预警池 + 潜在损益评估
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

type RiskRow = {
  id: number | string
  type: string
  level: string
  desc: string
  triggered_at: string
  handled?: boolean
}

const risks = ref<RiskRow[]>([])
const boardLoaded = ref(false)
const boardRiskIndex = ref(0)
const boardEstimatedLoss = ref(0)
const boardRevparDelta = ref(0)
const boardRecoverPct = ref(0)

/** 四周收益对比：正常 vs 风险冲击 */
const revenueWeeks = ref<
  { label: string; normal: number; risk: number; normalAmt: string; riskAmt: string }[]
>([])

const riskIndex = computed(() => {
  if (boardLoaded.value) return boardRiskIndex.value
  const open = risks.value.filter((r) => !r.handled)
  if (!open.length) return 28
  const score = open.reduce((s, r) => {
    if (r.level === '高') return s + 28
    if (r.level === '中') return s + 16
    return s + 8
  }, 20)
  return Math.min(96, score)
})

const profitLoss = computed(() => {
  if (boardLoaded.value) return boardEstimatedLoss.value
  const open = risks.value.filter((r) => !r.handled)
  const high = open.filter((r) => r.level === '高').length
  const mid = open.filter((r) => r.level === '中').length
  const low = open.filter((r) => r.level === '低').length
  return high * 18500 + mid * 9200 + low * 2100
})

const revparDelta = computed(() => {
  if (boardLoaded.value) return String(boardRevparDelta.value)
  const open = risks.value.filter((r) => !r.handled).length
  return Math.min(28, 6 + open * 2.2).toFixed(1)
})

const recoverPct = computed(() => {
  if (boardLoaded.value) return boardRecoverPct.value
  const base = 82
  const openHigh = risks.value.filter((r) => !r.handled && r.level === '高').length
  return Math.max(65, base - openHigh * 3)
})

function levelPill(level: string) {
  if (level === '高')
    return 'bg-error text-on-error font-label-lg text-[12px] px-2 py-0.5 rounded uppercase tracking-wider'
  if (level === '中')
    return 'bg-orange-500 text-white font-label-lg text-[12px] px-2 py-0.5 rounded uppercase tracking-wider'
  return 'bg-yellow-500 text-white font-label-lg text-[12px] px-2 py-0.5 rounded uppercase tracking-wider'
}
function cardBorder(level: string) {
  if (level === '高') return 'bg-error-container/20 border-l-4 border-error rounded-r-xl'
  if (level === '中') return 'bg-orange-50 border-l-4 border-orange-400 rounded-r-xl'
  return 'bg-surface-container-low border-l-4 border-yellow-400 rounded-r-xl'
}
function impactColor(level: string) {
  return level === '高' ? 'text-error' : level === '中' ? 'text-orange-600' : 'text-on-surface'
}
function countBy(lv: string) {
  return risks.value.filter((r) => r.level === lv).length
}

async function load() {
  try {
    const board = await api.riskBoard(hotelStore.hotelId)
    risks.value = (board?.alerts || []).map((a: any) => ({
      id: a.id,
      type: a.type || '经营',
      level: a.level || '低',
      desc: a.desc || '',
      triggered_at: a.triggered_at || '—',
      handled: !!a.handled,
    }))
    revenueWeeks.value = (board?.revenue_weeks || []).map((w: any) => ({
      label: w.label,
      normal: Number(w.normal || 0),
      risk: Number(w.risk || 0),
      normalAmt: w.normalAmt || `${w.normal}k`,
      riskAmt: w.riskAmt || `${w.risk}k`,
    }))
    boardRiskIndex.value = Number(board?.risk_index ?? 0)
    boardEstimatedLoss.value = Number(board?.estimated_loss ?? 0)
    boardRevparDelta.value = Number(board?.revpar_delta_pct ?? 0)
    boardRecoverPct.value = Number(board?.recover_pct ?? 0)
    boardLoaded.value = true
  } catch {
    risks.value = []
    revenueWeeks.value = []
    boardLoaded.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <header class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          {{ t('经营风险预警 (Black Swan)') }}
          <span
            class="bg-error-container text-on-error-container font-label-lg text-label-lg px-2 py-1 rounded-md flex items-center gap-1 border border-error/20"
          >
            <span class="material-symbols-outlined text-[16px]">warning</span>
            {{ countBy('高') > 0 ? t('高风险活跃') : t('监测中') }}</span
          >
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-1">
          {{ t('AI 持续监控外部数据源，为您预测并拦截潜在收益损失。') }}
        </p>
      </div>
      <div class="flex flex-wrap gap-3 justify-end">
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low"
          @click="router.push('/c2-risk/nl-command')"
        >
          {{ t('规则配置') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low"
          @click="router.push('/c2-risk/ai-survival-strategy')"
        >
          {{ t('风险仿真 →') }}
        </button>
        <button
          type="button"
          class="bg-primary text-on-primary font-label-lg text-label-lg px-6 py-3 rounded-full hover:bg-primary-fixed-variant transition-colors flex items-center justify-center gap-2 shadow-sm whitespace-nowrap h-fit ai-glow"
          @click="router.push('/c2-risk/log')"
        >
          <span class="material-symbols-outlined">bolt</span>
          {{ t('一键执行所有AI对策') }}
        </button>
      </div>
    </header>

    <section class="grid grid-cols-1 md:grid-cols-4 gap-gutter mb-8">
      <div
        class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.02)] flex flex-col justify-between"
      >
        <div class="flex justify-between items-start">
          <h3 class="font-headline-md text-headline-md text-on-surface">{{ t('综合风险指数') }}</h3>
          <span class="material-symbols-outlined text-outline">info</span>
        </div>
        <div class="mt-4 flex items-end gap-2">
          <span class="font-num-xl text-[48px] leading-none text-error font-bold">{{
            riskIndex
          }}</span>
          <span class="font-body-md text-body-md text-on-surface-variant mb-1">/ 100</span>
        </div>
        <div class="w-full bg-surface-container h-2 rounded-full mt-4 overflow-hidden">
          <div
            class="bg-gradient-to-r from-secondary to-error h-full rounded-full transition-all"
            :style="{ width: riskIndex + '%' }"
          ></div>
        </div>
      </div>
      <div
        class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.02)] md:col-span-3 grid grid-cols-3 gap-4 divide-x divide-outline-variant/50"
      >
        <div class="flex flex-col items-center justify-center px-4">
          <span class="material-symbols-outlined text-error text-3xl mb-2">gpp_bad</span>
          <span class="font-num-xl text-num-xl text-error">{{ countBy('高') }}</span>
          <span class="font-body-md text-body-md text-on-surface-variant">{{ t('严重威胁') }}</span>
        </div>
        <div class="flex flex-col items-center justify-center px-4">
          <span class="material-symbols-outlined text-orange-500 text-3xl mb-2">warning</span>
          <span class="font-num-xl text-num-xl text-orange-600">{{ countBy('中') }}</span>
          <span class="font-body-md text-body-md text-on-surface-variant">{{ t('中等风险') }}</span>
        </div>
        <div class="flex flex-col items-center justify-center px-4">
          <span class="material-symbols-outlined text-yellow-500 text-3xl mb-2">info</span>
          <span class="font-num-xl text-num-xl text-on-surface">{{ countBy('低') }}</span>
          <span class="font-body-md text-body-md text-on-surface-variant">{{
            t('低风险提示')
          }}</span>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <div class="lg:col-span-7 flex flex-col gap-gutter">
        <h2 class="font-headline-lg text-headline-lg text-on-surface flex items-center gap-2 mb-2">
          <span class="material-symbols-outlined text-tertiary">radar</span>
          {{ t('黑天鹅预警池') }}
        </h2>
        <article
          v-for="r in risks"
          :key="r.id"
          :class="cardBorder(r.level) + ' p-6 relative overflow-hidden'"
        >
          <div class="flex justify-between items-start mb-4">
            <div>
              <div class="flex items-center gap-2 mb-1">
                <span :class="levelPill(r.level)">{{
                  r.level === '高' ? t('严重') : r.level === '中' ? t('中等') : t('低')
                }}</span>
                <h3 class="font-headline-md text-headline-md text-on-surface">
                  {{ r.type }}{{ t('风险预警') }}
                </h3>
              </div>
              <p class="font-body-md text-body-md text-on-surface-variant">{{ r.desc }}</p>
            </div>
            <span
              class="font-num-md text-num-md flex flex-col items-end"
              :class="impactColor(r.level)"
            >
              <span class="text-[12px] text-on-surface-variant">{{ t('触发时间') }}</span
              >{{ r.triggered_at }}</span
            >
          </div>
          <div
            class="bg-surface-container-lowest rounded-lg p-4 border border-outline-variant ai-tinge shadow-sm"
          >
            <div class="flex items-center gap-2 mb-2">
              <span class="material-symbols-outlined text-tertiary">auto_awesome</span>
              <span class="font-label-lg text-label-lg text-on-surface font-semibold">{{
                t('AI 推荐对策')
              }}</span>
            </div>
            <ul class="font-body-md text-sm text-on-surface-variant space-y-2 mb-4">
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[18px] text-primary mt-0.5"
                  >check_circle</span
                >
                {{ t('启动针对该') }}{{ r.type
                }}{{ t('风险的定向缓解策略，降低未售出库存与客诉风险。') }}
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[18px] text-primary mt-0.5"
                  >check_circle</span
                >
                {{ t('动态调整价格护栏与退改政策，平衡入住率与利润率。') }}
              </li>
            </ul>
            <div class="flex justify-end gap-2">
              <button
                type="button"
                class="border border-outline-variant text-on-surface font-label-lg text-sm px-4 py-2 rounded-lg hover:bg-surface-container-low transition-colors"
                @click="router.push('/c2-risk/ai-survival-strategy')"
              >
                {{ t('仿真影响') }}
              </button>
              <button
                type="button"
                class="bg-primary-container text-on-primary-container font-label-lg text-sm px-4 py-2 rounded-lg hover:bg-primary hover:text-on-primary transition-colors flex items-center gap-1"
                @click="router.push('/c2-risk/log')"
              >
                {{ t('执行对策') }}
              </button>
            </div>
          </div>
        </article>
        <div
          v-if="!risks.length"
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 text-on-surface-variant"
        >
          {{ t('暂无风险预警') }}
        </div>
      </div>

      <div class="lg:col-span-5 flex flex-col gap-gutter">
        <h2 class="font-headline-lg text-headline-lg text-on-surface flex items-center gap-2 mb-2">
          <span class="material-symbols-outlined text-primary">monitoring</span>
          {{ t('潜在损益评估') }}
        </h2>
        <div
          class="bg-surface-container-lowest/80 backdrop-blur-md rounded-xl p-6 border border-outline-variant shadow-[0_8px_30px_rgba(0,0,0,0.04)] h-full flex flex-col"
        >
          <p class="font-body-md text-body-md text-on-surface-variant mb-6">
            {{ t('如果上述黑天鹅风险发生且未采取任何干预措施，预计未来 30 天的财务影响：') }}
          </p>
          <div class="grid grid-cols-2 gap-4 mb-8">
            <div class="bg-error-container/30 rounded-lg p-4 border border-error/10">
              <span class="font-label-lg text-label-lg text-on-surface-variant block mb-1">{{
                t('预计净利润损失')
              }}</span>
              <div class="flex items-baseline gap-1">
                <span class="font-num-xl text-[28px] text-error font-bold">
                  -¥{{ profitLoss.toLocaleString('zh-CN') }}</span
                >
              </div>
            </div>
            <div class="bg-surface-container-low rounded-lg p-4 border border-outline-variant/50">
              <span class="font-label-lg text-label-lg text-on-surface-variant block mb-1">{{
                t('RevPAR 偏离度')
              }}</span>
              <div class="flex items-baseline gap-1">
                <span class="font-num-xl text-[28px] text-on-surface font-bold"
                  >-{{ revparDelta }}%</span
                >
              </div>
            </div>
          </div>

          <div class="flex-1 mt-auto">
            <div class="flex items-center justify-between mb-3">
              <h4 class="font-label-lg text-label-lg text-on-surface">
                {{ t('预期收益走势对比') }}
              </h4>
              <span class="text-[11px] text-on-surface-variant">{{ t('单位：万元量级示意') }}</span>
            </div>
            <div class="h-48 w-full relative pl-8 pr-1">
              <div
                class="absolute left-0 top-2 bottom-6 flex flex-col justify-between text-[10px] text-outline font-num-md"
              >
                <span>100k</span>
                <span>50k</span>
                <span>0</span>
              </div>
              <div
                class="h-full border-l border-b border-outline-variant flex items-stretch gap-1 pt-2 pb-0"
              >
                <div
                  v-for="w in revenueWeeks"
                  :key="w.label"
                  class="flex-1 flex flex-col items-center min-w-0"
                >
                  <div
                    class="flex-1 w-full flex items-end justify-center gap-1.5 px-1.5 min-h-[120px]"
                  >
                    <div
                      class="w-[42%] max-w-[28px] bg-surface-container-highest rounded-t-md transition-all hover:opacity-90 relative group"
                      :style="{ height: w.normal + '%' }"
                      :title="`${t('正常')} ${w.normalAmt}`"
                    >
                      <span
                        class="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-num-md text-on-surface-variant opacity-0 group-hover:opacity-100 whitespace-nowrap"
                      >
                        {{ w.normalAmt }}</span
                      >
                    </div>
                    <div
                      class="w-[42%] max-w-[28px] bg-error/80 rounded-t-md transition-all hover:opacity-90 relative group"
                      :style="{ height: w.risk + '%' }"
                      :title="`${t('风险下')} ${w.riskAmt}`"
                    >
                      <span
                        class="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-num-md text-error opacity-0 group-hover:opacity-100 whitespace-nowrap"
                      >
                        {{ w.riskAmt }}</span
                      >
                    </div>
                  </div>
                  <span class="text-[10px] text-on-surface-variant mt-2 shrink-0">{{
                    w.label
                  }}</span>
                </div>
              </div>
            </div>
            <div
              v-if="!revenueWeeks.length"
              class="text-sm text-on-surface-variant py-8 text-center"
            >
              {{ t('暂无周收益对比数据') }}
            </div>
            <div class="flex justify-center gap-4 mt-4 text-xs text-on-surface-variant">
              <div class="flex items-center gap-1">
                <span class="w-3 h-3 bg-surface-container-highest rounded-sm"></span>
                {{ t('正常预期') }}
              </div>
              <div class="flex items-center gap-1">
                <span class="w-3 h-3 bg-error/80 rounded-sm"></span>
                {{ t('风险下预期') }}
              </div>
            </div>
            <div class="mt-4 grid grid-cols-4 gap-2 text-center">
              <div
                v-for="w in revenueWeeks"
                :key="w.label + '-delta'"
                class="rounded-lg bg-error-container/20 px-1 py-2"
              >
                <div class="text-[10px] text-on-surface-variant">{{ w.label }}{{ t('落差') }}</div>
                <div class="text-xs font-bold text-error">-{{ w.normal - w.risk }}k</div>
              </div>
            </div>
          </div>

          <div
            class="mt-6 p-3 bg-primary-container/10 rounded-lg border border-primary/20 flex items-start gap-2"
          >
            <span class="material-symbols-outlined text-primary text-[18px]">verified_user</span>
            <p class="text-sm text-on-surface-variant leading-snug">
              {{ t('执行 AI 推荐对策后，预计可挽回') }}
              <strong class="text-primary font-semibold">{{ recoverPct }}%</strong>
              {{ t('的潜在损失，并将撤回高风险警报。') }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
