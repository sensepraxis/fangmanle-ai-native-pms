<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// C9 营收异常与欺诈监控（manual-price-override）— 对齐 tables/.tmp/c9 原型
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

type Tone = 'high' | 'mid' | 'low'
type Anomaly = {
  id: string
  title: string
  sub: string
  score: number
  tone: Tone
  icon: string
  filter: 'all' | 'price' | 'ota' | 'void'
  desc?: string
  detailTitle: string
  who: string
  room: string
  time: string
  orig: string
  newPrice: string
  diff: string
  timeline: Step[]
  aiHint: string
  status?: string
}

type Step = {
  tone: 'primary' | 'error' | 'tertiary'
  title: string
  time: string
  text: string
  ai?: boolean
}

const anomalies = ref<Anomaly[]>([])

const filters = [
  { key: 'all' as const, label: t('全部告警') },
  { key: 'price' as const, label: t('价格改写') },
  { key: 'ota' as const, label: t('OTA 渗漏') },
  { key: 'void' as const, label: t('作废交易') },
]

const activeFilter = ref<'all' | 'price' | 'ota' | 'void'>('all')
const selectedId = ref('')

const filtered = computed(() =>
  activeFilter.value === 'all'
    ? anomalies.value
    : anomalies.value.filter((a) => a.filter === activeFilter.value),
)

const emptyDetail: Anomaly = {
  id: '—',
  title: t('暂无告警'),
  sub: '',
  score: 0,
  tone: 'low',
  icon: 'info',
  filter: 'price',
  detailTitle: '暂无告警',
  who: '—',
  room: '—',
  time: '—',
  orig: '0',
  newPrice: '0',
  diff: '',
  timeline: [],
  aiHint: '当前无待处理营收异常。',
}

const selected = computed(
  () => anomalies.value.find((a) => a.id === selectedId.value) || anomalies.value[0] || emptyDetail,
)

const activeAlerts = computed(
  () =>
    anomalies.value.filter(
      (a) => a.tone === 'high' && a.status !== 'closed' && a.status !== 'resolved',
    ).length,
)

function iconByCategory(cat: string) {
  if (cat === 'ota') return 'travel_explore'
  if (cat === 'void') return 'receipt_long'
  if (cat === 'price') return 'gavel'
  return 'percent'
}

function fmtAmt(n: number | string | null | undefined) {
  return Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function mapRow(r: any): Anomaly {
  const cat = (r.category || 'price') as Anomaly['filter']
  const code = r.code || `ANM-${r.id}`
  return {
    id: code.startsWith('#') ? code : `#${code}`,
    title: r.title || '营收异常',
    sub: r.subtitle || '',
    score: Number(r.score || 0),
    tone: (r.tone || 'mid') as Tone,
    icon: iconByCategory(cat),
    filter: cat === 'ota' || cat === 'void' || cat === 'price' ? cat : 'price',
    desc: r.description || '',
    detailTitle: r.detail_title || r.title || '异常详情',
    who: r.actor || '—',
    room: r.room_label || '—',
    time: r.event_time || '—',
    orig: fmtAmt(r.orig_amount),
    newPrice: fmtAmt(r.new_amount),
    diff: r.diff_label || '',
    timeline: Array.isArray(r.timeline) ? r.timeline : [],
    aiHint: r.ai_hint || '',
    status: r.status,
  }
}

async function load() {
  try {
    const rows = await api.listRevenueAnomalies(hotelStore.hotelId)
    anomalies.value = (rows || []).map(mapRow)
    selectedId.value = anomalies.value[0]?.id || ''
  } catch {
    anomalies.value = []
    selectedId.value = ''
  }
}

function selectAnomaly(a: Anomaly) {
  selectedId.value = a.id
}

function toneBar(t: Tone) {
  if (t === 'high') return 'bg-error'
  if (t === 'mid') return 'bg-[#f9a825]'
  return 'bg-primary'
}

function toneIconWrap(t: Tone) {
  if (t === 'high') return 'bg-error-container text-on-error-container'
  if (t === 'mid') return 'bg-[#fff8e1] text-[#f9a825]'
  return 'bg-primary-container text-on-primary-container'
}

function toneScore(t: Tone) {
  if (t === 'high') return 'text-error'
  if (t === 'mid') return 'text-[#f9a825]'
  return 'text-primary'
}

function cardBorder(a: Anomaly) {
  const selected = a.id === selectedId.value
  if (a.tone === 'high' || selected) return 'border-2 border-error'
  if (a.tone === 'mid') return 'border border-outline-variant hover:border-tertiary/50'
  return 'border border-outline-variant hover:border-primary/50 opacity-75'
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <!-- 页头（对齐原型 mb-8 / 成对字体） -->
    <div class="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2 flex items-center gap-3">
          {{ t('营收异常与欺诈监控') }}
        </h1>
        <p class="font-body-md text-body-md text-secondary">
          {{ t('实时监测可疑财务活动与营收渗漏。') }}
        </p>
      </div>
      <div class="flex items-center gap-3 flex-wrap justify-end">
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low transition-colors"
          @click="router.push('/c9-finance/daily-operations')"
        >
          {{ t('← 返回财务报表') }}
        </button>
        <div
          class="flex items-center gap-2 bg-error-container text-on-error-container px-4 py-2 rounded-lg font-label-lg text-label-lg shadow-sm border border-error/20"
        >
          <div class="w-2 h-2 rounded-full bg-error animate-pulse"></div>
          {{ activeAlerts }} {{ t('条活跃高风险告警') }}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <!-- 左列：告警列表 -->
      <div class="col-span-12 lg:col-span-7 flex flex-col gap-gutter">
        <div class="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          <button
            v-for="f in filters"
            :key="f.key"
            type="button"
            class="px-4 py-2 rounded-full font-label-lg text-label-lg whitespace-nowrap transition-colors"
            :class="
              activeFilter === f.key
                ? 'bg-on-surface text-surface'
                : 'bg-surface-container text-on-surface hover:bg-surface-container-high border border-outline-variant'
            "
            @click="activeFilter = f.key"
          >
            {{ f.label }}
          </button>
        </div>

        <div
          v-for="a in filtered"
          :key="a.id"
          class="bg-surface-container-lowest rounded-xl p-5 shadow-sm relative overflow-hidden cursor-pointer transition-transform hover:-translate-y-1"
          :class="cardBorder(a)"
          @click="selectAnomaly(a)"
        >
          <div class="absolute top-0 left-0 w-1 h-full" :class="toneBar(a.tone)"></div>
          <div class="flex justify-between items-start mb-3">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                :class="toneIconWrap(a.tone)"
              >
                <span class="material-symbols-outlined text-[20px]">{{ a.icon }}</span>
              </div>
              <div>
                <h3 class="font-headline-md text-headline-md text-on-surface">{{ a.title }}</h3>
                <p class="font-body-md text-body-md text-secondary">{{ a.sub }}</p>
              </div>
            </div>
            <div class="flex flex-col items-end shrink-0 ml-3">
              <span class="font-num-xl text-num-xl font-bold" :class="toneScore(a.tone)">{{
                a.score
              }}</span>
              <span class="text-xs text-secondary uppercase tracking-wider">{{
                t('风险评分')
              }}</span>
            </div>
          </div>
          <div
            v-if="a.desc && (a.tone === 'high' || a.id === selectedId)"
            class="flex items-center gap-4 mt-4 p-3 bg-error-container/20 rounded-lg border border-error/10"
          >
            <p class="font-body-md text-body-md text-on-surface-variant text-sm">{{ a.desc }}</p>
          </div>
        </div>

        <div
          v-if="!filtered.length"
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 font-body-md text-body-md text-secondary"
        >
          {{ t('当前筛选下暂无告警') }}
        </div>
      </div>

      <!-- 右列：详情 -->
      <div class="col-span-12 lg:col-span-5">
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm h-full flex flex-col sticky top-[88px]"
        >
          <div
            class="p-6 border-b border-outline-variant bg-surface-container-lowest rounded-t-xl relative overflow-hidden"
          >
            <div class="absolute inset-0 high-risk-bg opacity-10"></div>
            <div class="flex items-center justify-between mb-4 relative z-10 gap-2 flex-wrap">
              <div
                class="flex items-center gap-2 text-error font-label-lg text-label-lg bg-error-container px-3 py-1 rounded-full"
              >
                <span class="material-symbols-outlined text-[16px]">priority_high</span>
                {{ t('高优先级排查') }}
              </div>
              <span class="font-num-md text-num-md text-secondary"
                >{{ t('编号：') }}{{ selected.id }}</span
              >
            </div>
            <h2 class="font-display-lg text-display-lg text-on-surface mb-2 relative z-10">
              {{ selected.detailTitle }}
            </h2>
            <div
              class="flex items-center gap-4 text-secondary font-body-md text-body-md relative z-10 flex-wrap"
            >
              <span class="flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">person</span
                >{{ selected.who }}</span
              >
              <span class="flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">meeting_room</span
                >{{ selected.room }}</span
              >
              <span class="flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">schedule</span
                >{{ selected.time }}</span
              >
            </div>
          </div>

          <div class="p-6 flex-1 overflow-y-auto">
            <div class="flex gap-4 mb-8">
              <div class="flex-1 bg-surface-container p-4 rounded-lg border border-outline-variant">
                <div class="text-secondary text-sm mb-1 uppercase tracking-wider">
                  {{ t('原价') }}
                </div>
                <div
                  class="font-num-xl text-num-xl text-on-surface line-through decoration-secondary/50"
                >
                  ¥{{ selected.orig }}
                </div>
              </div>
              <div
                class="flex-1 bg-error-container/30 p-4 rounded-lg border border-error/30 relative overflow-hidden"
              >
                <div class="absolute inset-0 ai-shimmer opacity-20"></div>
                <div
                  class="text-error text-sm mb-1 uppercase tracking-wider font-bold relative z-10"
                >
                  {{ t('改写价') }}
                </div>
                <div class="font-num-xl text-num-xl text-error font-bold relative z-10">
                  ¥{{ selected.newPrice
                  }}<span class="text-sm font-normal">{{ selected.diff }}</span>
                </div>
              </div>
            </div>

            <h4 class="font-headline-md text-headline-md text-on-surface mb-4">
              {{ t('事件时间线') }}
            </h4>
            <div
              class="relative pl-6 space-y-6 before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px before:h-full before:w-0.5 before:bg-outline-variant"
            >
              <div v-for="(s, i) in selected.timeline" :key="i" class="relative">
                <!-- primary -->
                <div
                  v-if="s.tone === 'primary'"
                  class="absolute -left-[35px] bg-surface-container-lowest h-6 w-6 rounded-full border-2 border-primary flex items-center justify-center z-10"
                >
                  <div class="h-2 w-2 bg-primary rounded-full"></div>
                </div>
                <!-- error -->
                <div
                  v-else-if="s.tone === 'error'"
                  class="absolute -left-[35px] bg-surface-container-lowest h-6 w-6 rounded-full border-2 border-error flex items-center justify-center z-10"
                >
                  <div class="h-2 w-2 bg-error rounded-full"></div>
                </div>
                <!-- ai / tertiary -->
                <div
                  v-else
                  class="absolute -left-[35px] bg-tertiary h-6 w-6 rounded-full flex items-center justify-center z-10 shadow-[0_0_8px_rgba(168,79,206,0.6)]"
                >
                  <span
                    class="material-symbols-outlined text-white text-[14px]"
                    style="font-variation-settings: 'FILL' 1"
                  >
                    auto_awesome
                  </span>
                </div>

                <div
                  class="p-4 rounded-lg border shadow-sm"
                  :class="
                    s.tone === 'error'
                      ? 'bg-error-container/10 border-error/30'
                      : s.tone === 'tertiary'
                        ? 'bg-surface-container-lowest border-tertiary/40 relative overflow-hidden'
                        : 'bg-surface-container-lowest border-outline-variant'
                  "
                >
                  <div v-if="s.ai" class="absolute left-0 top-0 w-1 h-full bg-tertiary"></div>
                  <div class="flex justify-between items-start mb-1 gap-2">
                    <div
                      class="font-label-lg text-label-lg"
                      :class="
                        s.tone === 'error'
                          ? 'text-error font-bold'
                          : s.tone === 'tertiary'
                            ? 'text-tertiary font-bold'
                            : 'text-on-surface'
                      "
                    >
                      {{ s.title }}
                    </div>
                    <div class="font-num-md text-num-md text-secondary text-sm shrink-0">
                      {{ s.time }}
                    </div>
                  </div>
                  <div class="font-body-md text-body-md text-secondary text-sm">{{ s.text }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="p-6 border-t border-outline-variant bg-surface-container-low rounded-b-xl">
            <div class="flex items-start gap-3 mb-4">
              <span
                class="material-symbols-outlined text-tertiary mt-0.5"
                style="font-variation-settings: 'FILL' 1"
              >
                auto_awesome
              </span>
              <div>
                <h4 class="font-label-lg text-label-lg text-on-surface font-bold">
                  {{ t('AI 建议操作') }}
                </h4>
                <p class="font-body-md text-body-md text-secondary text-sm">
                  {{ selected.aiHint }}
                </p>
              </div>
            </div>
            <div class="flex gap-3 mt-4">
              <button
                type="button"
                class="flex-1 bg-surface-container-lowest text-on-surface border border-outline-variant py-2 rounded-lg font-label-lg text-label-lg hover:bg-surface-container-high transition-colors"
              >
                {{ t('确认（误报）') }}
              </button>
              <button
                type="button"
                class="flex-1 bg-error text-on-error py-2 rounded-lg font-label-lg text-label-lg hover:bg-error/90 transition-colors shadow-sm flex items-center justify-center gap-2"
              >
                <span class="material-symbols-outlined text-[18px]">lock</span>
                {{ t('升级并锁定账单') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.high-risk-bg {
  background: repeating-linear-gradient(
    -45deg,
    rgba(186, 26, 26, 0.35),
    rgba(186, 26, 26, 0.35) 8px,
    rgba(186, 26, 26, 0.08) 8px,
    rgba(186, 26, 26, 0.08) 16px
  );
}
.ai-shimmer {
  background: linear-gradient(90deg, transparent, rgba(186, 26, 26, 0.18), transparent);
  background-size: 200% 100%;
  animation: fraud-shimmer 2.4s infinite linear;
}
@keyframes fraud-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
