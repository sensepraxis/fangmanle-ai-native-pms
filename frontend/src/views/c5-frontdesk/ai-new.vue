<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 全渠道订单洞察 —— 转化排行 / 质量分档 / 趋势来自 /api/orders/channel-insight
 */
import { ref, computed, onMounted, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { confidenceLabel } from '../../lib/aiConfidence'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AnalyticsFlowNav from '../../components/AnalyticsFlowNav.vue'
import AnalyticsAiActions from '../../components/AnalyticsAiActions.vue'

const props = withDefaults(
  defineProps<{
    embedded?: boolean
  }>(),
  { embedded: false },
)

const router = useRouter()

function goAttribution() {
  if (props.embedded) {
    router.push({ path: '/analytics', query: { tab: 'insights', section: 'attribution' } })
    return
  }
  router.push('/analytics/marketing-attribution/path')
}

type Bubble = {
  id: string
  channel: string
  tone: 'direct' | 'xhs' | 'douyin' | 'ota' | string
  price: number
  conv: number
  volume: number
  label: string
  bookings?: number
  adr?: number
}

const loading = ref(false)
const loadError = ref('')
const payload = ref<any>(null)
const roomFilter = ref<string>('all')

/** 渠道 AI 解读：仅手动触发 */
const aiInsight = ref<any>(null)
const aiLoading = ref(false)
const aiError = ref('')

const roomTypes = computed(
  () => (payload.value?.room_types || []) as { id: number; name: string }[],
)
const bubbles = computed(() => (payload.value?.bubbles || []) as Bubble[])
const matrixPoints = computed(() => (payload.value?.matrix || []) as any[])

const aiSourceLabel = computed(() => {
  const s = aiInsight.value?.source
  if (s === 'llm') return t('AI 洞察')
  if (s === 'unavailable' || s === 'fallback') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 未启用')
  return ''
})

const aiModelMeta = computed(() => formatAiModelMeta(aiInsight.value))
const confText = (c: string) => confidenceLabel(c)

const toneColor: Record<string, string> = {
  direct: '#005bbf',
  xhs: '#8c33b3',
  douyin: '#ba1a1a',
  ota: '#64748b',
}
const toneLabel = (tone: string) =>
  (
    ({
      direct: t('直订'),
      xhs: t('小红书'),
      douyin: t('抖音'),
      ota: 'OTA',
    }) as Record<string, string>
  )[tone] || t('其他')

/** 左栏：按转化率排序的渠道表现（条形图，避免气泡重叠） */
const channelRank = computed(() => {
  const rows = [...bubbles.value]
  if (!rows.length) return []
  const maxConv = Math.max(1, ...rows.map((b) => Number(b.conv) || 0))
  return rows
    .map((b) => {
      const bookings = Number(b.bookings) || 0
      const conv = Number(b.conv) || 0
      const adr = Number(b.adr) || 0
      return {
        id: b.id,
        label: b.label,
        tone: b.tone,
        color: toneColor[b.tone] || '#64748b',
        group: toneLabel(b.tone),
        conv,
        adr,
        bookings,
        convPct: Math.round((conv / maxConv) * 100),
        hint:
          conv >= maxConv * 0.7
            ? t('高转化，可适当提价试探')
            : adr > 0 && conv < maxConv * 0.4
              ? t('转化偏低，检查价差/库存')
              : t('表现平稳'),
      }
    })
    .sort((a, b) => b.conv - a.conv || b.bookings - a.bookings)
})

/** 右栏：质量分档（四象限列表，替代挤成一团的气泡矩阵） */
const qualityBoard = computed(() => {
  const pts = matrixPoints.value
  if (!pts.length) {
    return [
      {
        key: 'good',
        title: t('优质'),
        desc: t('高 ADR · 低取消'),
        tone: 'good',
        items: [] as any[],
      },
      {
        key: 'pricey',
        title: t('高价高取消'),
        desc: t('客单高但易流失'),
        tone: 'warn',
        items: [] as any[],
      },
      {
        key: 'volume',
        title: t('走量'),
        desc: t('低 ADR · 低取消'),
        tone: 'mute',
        items: [] as any[],
      },
      {
        key: 'risk',
        title: t('风险区'),
        desc: t('低 ADR · 高取消'),
        tone: 'bad',
        items: [] as any[],
      },
    ]
  }
  const adrs = pts.map((p: any) => Number(p.adr_value ?? p.adr) || 0)
  const cancels = pts.map((p: any) => Number(p.cancel_rate ?? p.cancel) || 0)
  const adrMed = median(adrs)
  const cancelMed = median(cancels)

  const buckets: Record<string, any[]> = { good: [], pricey: [], volume: [], risk: [] }
  for (const p of pts) {
    const adr = Number(p.adr_value ?? p.adr) || 0
    const cancel = Number(p.cancel_rate ?? p.cancel) || 0
    const highAdr = adr >= adrMed
    const highCancel = cancel >= cancelMed
    const key =
      highAdr && !highCancel
        ? 'good'
        : highAdr && highCancel
          ? 'pricey'
          : !highAdr && !highCancel
            ? 'volume'
            : 'risk'
    buckets[key].push({
      id: p.id,
      name: p.name,
      adr,
      cancel,
      bookings: p.bookings || 0,
      tip: p.tip || '',
      color: p.tone || '#64748b',
    })
  }
  for (const k of Object.keys(buckets)) {
    buckets[k].sort((a, b) => b.bookings - a.bookings || a.cancel - b.cancel)
  }
  return [
    {
      key: 'good',
      title: t('优质'),
      desc: t('ADR≥中位 · 取消≤中位'),
      tone: 'good',
      items: buckets.good,
    },
    {
      key: 'pricey',
      title: t('高价高取消'),
      desc: t('ADR高但易取消'),
      tone: 'warn',
      items: buckets.pricey,
    },
    {
      key: 'volume',
      title: t('走量稳健'),
      desc: t('ADR偏低 · 取消可控'),
      tone: 'mute',
      items: buckets.volume,
    },
    {
      key: 'risk',
      title: t('风险区'),
      desc: t('低客单 · 高取消'),
      tone: 'bad',
      items: buckets.risk,
    },
  ]
})

function median(arr: number[]) {
  if (!arr.length) return 0
  const s = [...arr].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

async function load() {
  loading.value = true
  loadError.value = ''
  aiInsight.value = null
  aiError.value = ''
  try {
    const rt = roomFilter.value === 'all' ? null : Number(roomFilter.value) || null
    payload.value = await api.ordersChannelInsight(hotelStore.hotelId, 30, rt)
  } catch (e: any) {
    const msg = e?.message || t('加载失败')
    loadError.value =
      msg.includes('integer') || msg.includes('order_id')
        ? t('渠道洞察接口未生效，请重启后端后再刷新')
        : msg
    payload.value = null
  } finally {
    loading.value = false
  }
}

async function runAiInsight() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiError.value = ''
  try {
    const rt = roomFilter.value === 'all' ? null : Number(roomFilter.value) || null
    aiInsight.value = await api.ordersChannelInsightAi(hotelStore.hotelId, 30, rt)
  } catch (e: any) {
    aiInsight.value = null
    const msg = e?.message || t('AI 解读失败')
    aiError.value = /method not allowed/i.test(msg)
      ? t('接口未生效（405）：请重启后端后再点「AI生成渠道洞察」')
      : msg
  } finally {
    aiLoading.value = false
  }
}

onMounted(load)
watch(roomFilter, load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page" :class="{ 'is-embedded': embedded }">
    <AnalyticsFlowNav v-if="!embedded" hide-links />
    <AnalyticsAiActions v-if="!embedded" module="channel" compact class="mb-4" />

    <div
      v-if="!embedded"
      class="page-title-block mb-6 flex justify-between items-end flex-wrap gap-4"
    >
      <div>
        <h1 class="text-display-lg font-display-lg text-on-surface">{{ t('全渠道订单洞察') }}</h1>
        <p class="text-on-surface-variant text-body-lg font-body-lg mt-1">
          Order Intelligence &amp; Channel Performance
        </p>
      </div>
      <div class="flex gap-3 flex-wrap">
        <button
          type="button"
          class="px-4 py-2 rounded border border-outline text-on-surface hover:bg-surface-container-low transition-colors text-label-lg font-label-lg flex items-center gap-2"
          @click="goAttribution"
        >
          <span class="material-symbols-outlined">route</span> {{ t('渠道归因分析') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded bg-primary text-on-primary hover:bg-primary/90 transition-colors text-label-lg font-label-lg shadow-sm flex items-center gap-2"
        >
          <span class="material-symbols-outlined">download</span> {{ t('导出报告') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <!-- AI 渠道解读：手动触发 -->
      <div
        v-if="commercialEnabled()"
        class="col-span-12 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex items-start gap-4"
        style="border-left: 3px solid var(--tertiary)"
      >
        <div
          class="p-3 bg-tertiary-container text-on-tertiary-container rounded-full flex-shrink-0"
        >
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
            >auto_awesome</span
          >
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
            <h3
              class="text-headline-md font-headline-md text-on-surface flex items-center gap-2 m-0"
            >
              {{ t('AI 渠道解读') }}
            </h3>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg text-xs font-bold bg-primary text-on-primary disabled:opacity-50"
              :disabled="aiLoading || loading || !payload"
              @click="runAiInsight"
            >
              {{ aiLoading ? t('解读中…') : aiInsight ? t('重新解读') : t('AI生成渠道洞察') }}
            </button>
          </div>

          <template v-if="aiLoading">
            <p class="text-sm text-on-surface-variant m-0">{{ t('正在分析渠道数据…') }}</p>
          </template>
          <template v-else-if="aiInsight">
            <p class="text-[11px] text-on-surface-variant mb-2 flex flex-wrap gap-2 items-center">
              <span>{{ aiSourceLabel }}</span>
              <span
                v-if="aiModelMeta"
                class="px-1.5 py-0.5 rounded bg-surface-container-high font-mono"
                >{{ aiModelMeta }}</span
              >
              <span
                v-if="aiInsight.confidence"
                class="px-1.5 py-0.5 rounded bg-surface-container-high"
                >{{ confText(aiInsight.confidence) }}</span
              >
              <span v-if="aiInsight.confidence_note">· {{ t(aiInsight.confidence_note) }}</span>
            </p>
            <div
              v-if="aiInsight.source === 'llm' && aiInsight.narrative_html"
              class="ai-insight-body"
            >
              <div v-html="aiInsight.narrative_html" />
              <button type="button" class="ai-insight-link" @click="goAttribution">
                {{ t('查看多触点归因 →') }}
              </button>
            </div>
            <p v-if="aiInsight.llm_error" class="text-xs text-on-surface-variant mt-2 mb-0">
              {{ t(aiInsight.llm_error) }}
            </p>
          </template>
          <p v-if="aiError" class="text-sm text-error mt-2 mb-0">{{ aiError }}</p>
          <p v-if="loadError" class="text-sm text-error mt-1 mb-0">{{ loadError }}</p>
        </div>
      </div>

      <!-- 渠道转化排行（替代重叠气泡） -->
      <div
        class="col-span-12 lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col"
      >
        <div class="flex justify-between items-center mb-2 flex-wrap gap-3">
          <div>
            <h2 class="text-headline-md font-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">leaderboard</span
              >{{ t('渠道转化排行') }}
            </h2>
          </div>
          <select
            v-model="roomFilter"
            class="border border-outline-variant rounded-lg px-3 py-1.5 text-label-lg text-on-surface-variant bg-surface focus:ring-primary focus:border-primary"
          >
            <option value="all">{{ t('所有房型') }}</option>
            <option v-for="rt in roomTypes" :key="rt.id" :value="String(rt.id)">
              {{ rt.name }}
            </option>
          </select>
        </div>
        <div class="flex gap-4 mb-4 text-label-lg text-on-surface-variant flex-wrap">
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background: #005bbf" />{{
              t('直订')
            }}</span
          >
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background: #8c33b3" />{{
              t('小红书')
            }}</span
          >
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background: #ba1a1a" />{{
              t('抖音')
            }}</span
          >
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background: #79747e" /> OTA
          </span>
        </div>
        <div v-if="!channelRank.length && !loading" class="rank-empty">{{ t('暂无渠道数据') }}</div>
        <div v-else class="rank-list">
          <div v-for="(row, idx) in channelRank" :key="row.id" class="rank-row">
            <span class="rank-idx" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="rank-dot" :style="{ background: row.color }" />
            <div class="rank-main">
              <div class="rank-head">
                <span class="rank-name">{{ t(String(row.label || '')) }}</span>
                <span class="rank-meta"
                  >ADR ¥{{ Math.round(row.adr) }} · {{ row.bookings }} {{ t('单') }}</span
                >
              </div>
              <div class="rank-bar-track">
                <div
                  class="rank-bar-fill"
                  :style="{ width: row.convPct + '%', background: row.color }"
                />
              </div>
              <div class="rank-foot">
                <span class="rank-conv">{{ t('转化') }} {{ row.conv.toFixed(1) }}%</span>
                <span class="rank-hint">{{ row.hint }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 渠道质量分档（替代挤成一团的矩阵） -->
      <div
        class="col-span-12 lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col"
      >
        <div class="mb-2">
          <h2 class="text-headline-md font-headline-md text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">category</span
            >{{ t('渠道质量分档') }}
          </h2>
        </div>
        <div class="quality-grid">
          <div
            v-for="q in qualityBoard"
            :key="q.key"
            class="quality-card"
            :class="'tone-' + q.tone"
          >
            <div class="quality-head">
              <span class="quality-title">{{ q.title }}</span>
              <span class="quality-count">{{ q.items.length }}</span>
            </div>
            <p class="quality-desc">{{ q.desc }}</p>
            <ul v-if="q.items.length" class="quality-list">
              <li v-for="it in q.items.slice(0, 5)" :key="it.id">
                <span class="q-dot" :style="{ background: it.color }" />
                <span class="q-name" :title="it.tip">{{ t(String(it.name || '')) }}</span>
                <span class="q-stat"
                  >¥{{ Math.round(it.adr) }} · {{ Number(it.cancel).toFixed(0) }}%</span
                >
              </li>
            </ul>
            <p v-else class="quality-none">{{ t('暂无渠道落入此档') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-insight-body {
  margin: 0;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 0.75rem;
}
@media (min-width: 720px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
  }
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 0.65rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid rgba(202, 196, 208, 0.55);
  background: #faf8fc;
}
.ai-insight-body :deep(.ai-insight-sec.fact) {
  border-left: 3px solid #005bbf;
}
.ai-insight-body :deep(.ai-insight-sec.sug) {
  border-left: 3px solid #8c33b3;
  background: #f6edf9;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #49454f;
  margin-bottom: 0.45rem;
}
.ai-insight-body :deep(.ai-insight-sec.fact .ai-insight-h) {
  color: #005bbf;
}
.ai-insight-body :deep(.ai-insight-sec.sug .ai-insight-h) {
  color: #8c33b3;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding: 0 0 0 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.ai-insight-body :deep(li) {
  font-size: 0.875rem;
  line-height: 1.45;
  color: #49454f;
}
.ai-insight-body :deep(li strong) {
  color: #1c1b1f;
  font-weight: 700;
}
.ai-insight-link {
  display: inline-block;
  margin-top: 0.65rem;
  color: #005bbf;
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: underline;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
.rank-empty {
  padding: 2.5rem 1rem;
  text-align: center;
  color: #79747e;
  font-size: 0.875rem;
}
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 0.25rem;
}
.rank-row {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.55rem 0.65rem;
  border-radius: 0.75rem;
  background: rgba(247, 242, 250, 0.65);
  border: 1px solid rgba(202, 196, 208, 0.35);
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.rank-row:hover {
  background: #fff;
  border-color: rgba(0, 91, 191, 0.28);
}
.rank-idx {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 0.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: #79747e;
  background: #e7e0ec;
  flex-shrink: 0;
  margin-top: 0.15rem;
}
.rank-idx.top {
  background: #005bbf;
  color: #fff;
}
.rank-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  flex-shrink: 0;
  margin-top: 0.45rem;
}
.rank-main {
  flex: 1;
  min-width: 0;
}
.rank-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}
.rank-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1c1b1f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rank-meta {
  font-size: 0.7rem;
  color: #79747e;
  white-space: nowrap;
  flex-shrink: 0;
}
.rank-bar-track {
  height: 7px;
  border-radius: 999px;
  background: #e7e0ec;
  overflow: hidden;
}
.rank-bar-fill {
  height: 100%;
  border-radius: 999px;
  min-width: 4px;
  transition: width 0.35s ease;
}
.rank-foot {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.3rem;
}
.rank-conv {
  font-size: 0.75rem;
  font-weight: 600;
  color: #49454f;
}
.rank-hint {
  font-size: 0.7rem;
  color: #9a94a0;
}

.quality-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  flex: 1;
}
.quality-card {
  border-radius: 0.85rem;
  padding: 0.85rem 0.9rem;
  border: 1px solid transparent;
  min-height: 9.5rem;
}
.quality-card.tone-good {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.22);
}
.quality-card.tone-warn {
  background: rgba(245, 158, 11, 0.09);
  border-color: rgba(245, 158, 11, 0.25);
}
.quality-card.tone-mute {
  background: rgba(59, 130, 246, 0.07);
  border-color: rgba(59, 130, 246, 0.2);
}
.quality-card.tone-bad {
  background: rgba(239, 68, 68, 0.07);
  border-color: rgba(239, 68, 68, 0.22);
}
.quality-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.quality-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: #1c1b1f;
}
.quality-count {
  font-size: 0.65rem;
  font-weight: 700;
  color: #49454f;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
}
.quality-desc {
  font-size: 0.65rem;
  color: #79747e;
  margin: 0.25rem 0 0.55rem;
}
.quality-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.quality-list li {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
}
.q-dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 999px;
  flex-shrink: 0;
}
.q-name {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1c1b1f;
  font-weight: 500;
}
.q-stat {
  flex-shrink: 0;
  color: #79747e;
  font-variant-numeric: tabular-nums;
}
.quality-none {
  font-size: 0.7rem;
  color: #9a94a0;
  margin: 0.4rem 0 0;
}

@media (max-width: 640px) {
  .quality-grid {
    grid-template-columns: 1fr;
  }
}
</style>
