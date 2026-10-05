<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 智能布草周转与预测 —— 忠实对照 C7 real-time-linen-status 原型
 */
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
import SuppliesFocusBar from '../../components/SuppliesFocusBar.vue'

const route = useRoute()
const router = useRouter()
const focusSummary = ref('')
const snapTime = ref(t('今日 14:30'))
const linenStatus = ref<any[]>([])
const insightId = ref<number | null>(null)
const insight = ref({
  title: t('暂无洞察'),
  desc: SUPPLIES_EMPTY,
  actionLabel: t('查看 AI 预测'),
})

function goForecast() {
  const q = insightId.value ? `?insight_id=${insightId.value}` : ''
  router.push(`/c7-supplies/supply-intelligence${q}`)
}

function goLifecycle() {
  router.push('/c7-supplies/linen-lifecycle-loss')
}

function displayName(itemType: string) {
  if (itemType === t('床单')) return t('床单（大床/双床）')
  return itemType
}

function buildSegs(s: any) {
  const inRoom = Number(s.in_room || 0)
  const inWash = Number(s.in_wash || 0)
  const pending = Number(s.pending_wash || 0)
  const storage = Number(s.in_storage || 0)
  const total = Math.max(1, inRoom + inWash + pending + storage)
  const pct = (n: number) => Math.round((n / total) * 100)
  return {
    name: displayName(String(s.item_type || '')),
    total: String(total),
    segs: [
      { label: t('在房'), pct: pct(inRoom), cls: 'bg-primary', width: pct(inRoom) },
      { label: t('洗涤中'), pct: pct(inWash), cls: 'bg-tertiary', width: pct(inWash) },
      { label: t('待洗'), pct: pct(pending), cls: 'bg-error/80', width: pct(pending) },
      { label: t('仓储'), pct: pct(storage), cls: 'bg-green-600', width: pct(storage) },
    ],
  }
}

/** 无快照时留空，由空态提示；不回退硬编码样例数 */
async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'linen')
    const snaps = board?.linen_snapshots || []
    const prefer = [t('床单'), t('浴巾')]
    const ordered = prefer.map((t) => snaps.find((s: any) => s.item_type === t)).filter(Boolean)
    if (ordered.length) {
      linenStatus.value = ordered.map(buildSegs)
    } else if (snaps.length) {
      linenStatus.value = snaps.slice(0, 2).map(buildSegs)
    } else {
      linenStatus.value = []
    }

    const now = new Date()
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    snapTime.value = `今日 ${hh}:${mm}`

    const alertId = Number(route.query.alert_id || 0)
    const qInsightId = Number(route.query.insight_id || 0)
    insightId.value = null

    if (alertId) {
      let alert = (board?.alerts || []).find((x: any) => Number(x.id) === alertId)
      if (!alert) {
        const full = await api.suppliesBoard(hotelStore.hotelId)
        alert = (full?.alerts || []).find((x: any) => Number(x.id) === alertId)
      }
      if (alert) {
        focusSummary.value = `${alert.floor || alert.room_no || t('告警')} · ${alert.supply_name || ''}：${alert.message || ''}`
        insight.value = {
          title:
            `${alert.floor || ''} ${alert.room_no || ''}`.trim() ||
            alert.supply_name ||
            t('布草告警'),
          desc: alert.message || SUPPLIES_EMPTY,
          actionLabel: t('查看 AI 预测'),
        }
      } else {
        focusSummary.value = ''
        insight.value = {
          title: t('暂无洞察'),
          desc: SUPPLIES_EMPTY,
          actionLabel: t('查看 AI 预测'),
        }
      }
    } else if (qInsightId) {
      let ins = (board?.insights || []).find((x: any) => Number(x.id) === qInsightId)
      if (!ins) {
        const full = await api.suppliesBoard(hotelStore.hotelId)
        ins = (full?.insights || []).find((x: any) => Number(x.id) === qInsightId)
      }
      if (ins) {
        insightId.value = Number(ins.id)
        focusSummary.value = `洞察：${ins.title}`
        insight.value = {
          title: ins.title || t('布草洞察'),
          desc: ins.recommendation || SUPPLIES_EMPTY,
          actionLabel: t('执行建议'),
        }
      } else {
        focusSummary.value = ''
        insight.value = {
          title: t('暂无洞察'),
          desc: SUPPLIES_EMPTY,
          actionLabel: t('查看 AI 预测'),
        }
      }
    } else {
      focusSummary.value = ''
      const ins =
        (board?.insights || []).find((x: any) => x.category === 'turnover') || board?.insights?.[0]
      if (ins?.title) {
        insightId.value = Number(ins.id) || null
        insight.value = {
          title: ins.title,
          desc: ins.recommendation || SUPPLIES_EMPTY,
          actionLabel: t('执行建议'),
        }
      } else {
        insight.value = {
          title: t('暂无洞察'),
          desc: SUPPLIES_EMPTY,
          actionLabel: t('查看 AI 预测'),
        }
      }
    }
  } catch {
    linenStatus.value = []
    insight.value = { title: t('暂无洞察'), desc: SUPPLIES_EMPTY, actionLabel: t('查看 AI 预测') }
  }
}
onMounted(load)
watch(() => [hotelStore.hotelId, route.query.alert_id, route.query.insight_id], load)
</script>

<template>
  <div class="page">
    <SuppliesFocusBar :summary="focusSummary" />

    <!-- Page Header —— 对齐原型 -->
    <div class="flex justify-between items-end">
      <div>
        <h2 class="font-display-lg text-display-lg text-on-surface">
          {{ t('智能布草周转与预测') }}
        </h2>
        <p class="font-body-md text-body-md text-on-surface-variant mt-1">
          {{ t('AI 驱动的布草管理与需求预测') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          type="button"
          class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg font-label-lg text-label-lg hover:bg-surface-container-highest transition-colors flex items-center gap-2 border border-outline-variant/50"
          @click="goLifecycle"
        >
          {{ t('寿命与待换') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm"
        >
          {{ t('登记入库') }}
        </button>
      </div>
    </div>

    <!-- Bento Grid -->
    <div class="grid grid-cols-12 gap-gutter mt-6">
      <!-- Real-time Status Card (Spans 8) -->
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 flex flex-col shadow-sm"
      >
        <div class="flex justify-between items-center mb-6">
          <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            {{ t('实时布草状态') }}
          </h3>
          <span
            class="font-label-lg text-label-lg text-on-surface-variant bg-surface-container px-2 py-1 rounded"
            >{{ snapTime }}</span
          >
        </div>
        <p v-if="!linenStatus.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div v-else class="space-y-6 flex-1">
          <div v-for="(row, i) in linenStatus" :key="i">
            <div class="flex justify-between font-label-lg text-label-lg mb-2">
              <span class="text-on-surface font-semibold">{{ row.name }}</span>
              <span class="text-on-surface-variant">{{ t('总计：') }}{{ row.total }}</span>
            </div>
            <div class="h-4 flex rounded-full overflow-hidden bg-surface-container">
              <div
                v-for="(s, j) in row.segs"
                :key="j"
                class="h-4"
                :class="s.cls"
                :style="{ width: s.width + '%' }"
                :title="`${s.label}: ${s.pct}%`"
              />
            </div>
            <div
              class="flex justify-between mt-2 font-body-md text-body-md text-xs text-on-surface-variant"
            >
              <div v-for="(s, j) in row.segs" :key="j" class="flex items-center gap-1">
                <span class="w-2 h-2 rounded-full" :class="s.cls" />
                {{ s.label }}（{{ s.pct }}%）
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI 洞察 (Spans 4) -->
      <div
        class="col-span-12 lg:col-span-4 bg-tertiary/5 border border-tertiary/20 rounded-xl p-6 flex flex-col relative overflow-hidden ai-glow"
      >
        <div class="absolute top-0 right-0 p-4 opacity-10" />
        <div class="flex items-center gap-2 mb-4 relative z-10">
          <h3 class="font-headline-md text-headline-md text-tertiary font-bold">
            {{ t('AI 洞察') }}
          </h3>
        </div>
        <div class="flex-1 relative z-10">
          <h4 class="font-headline-md text-headline-md text-on-surface mb-2">
            {{ insight.title }}
          </h4>
          <p class="font-body-md text-body-md text-on-surface-variant mb-4">{{ insight.desc }}</p>
          <div
            class="bg-surface-container-lowest rounded-lg p-4 border-l-4 border-tertiary shadow-sm"
          >
            <div class="font-label-lg text-label-lg text-on-surface font-semibold mb-1">
              {{ t('建议操作') }}
            </div>
            <div
              class="font-body-md text-body-md text-on-surface-variant flex justify-between items-center gap-2"
            >
              <span>{{ insight.actionLabel }}</span>
              <button
                type="button"
                class="text-tertiary hover:text-tertiary-container font-semibold shrink-0"
                @click="goForecast"
              >
                {{ t('执行') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 7 天需求预测 (Spans 12) —— 柱高与原型一致 -->
      <div
        class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
      >
        <div class="flex justify-between items-center mb-6">
          <div>
            <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('7 天需求预测') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">
              {{ t('预测周转需求 vs 可用洁净库存') }}
            </p>
          </div>
          <div class="flex gap-4 font-label-lg text-label-lg">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 bg-primary rounded-sm" />{{ t('需求') }}
            </div>
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 bg-tertiary rounded-sm" />{{ t('可用洁净') }}
            </div>
          </div>
        </div>

        <div
          class="h-64 w-full relative border-l border-b border-outline-variant/50 pt-4 pr-4 chart-area"
        >
          <div
            class="absolute left-[-30px] top-0 h-full flex flex-col justify-between font-num-md text-num-md text-xs text-on-surface-variant pb-6"
          >
            <span>300</span><span>200</span><span>100</span><span>0</span>
          </div>
          <div class="absolute inset-0 pl-4 pb-6 flex items-end justify-around">
            <!-- Day 1 -->
            <div class="w-12 h-[80%] flex flex-col justify-end gap-1 group relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[80%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[60%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 2 -->
            <div class="w-12 h-[90%] flex flex-col justify-end gap-1 relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[90%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[75%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 3 (Peak) -->
            <div class="w-12 h-full flex flex-col justify-end gap-1 relative">
              <div
                class="absolute -top-6 left-1/2 -translate-x-1/2 text-error text-xs font-bold bg-error/10 px-2 py-0.5 rounded whitespace-nowrap"
              >
                {{ t('缺口！') }}
              </div>
              <div
                class="w-full bg-error/20 absolute bottom-0 h-[100%] rounded-t-sm border border-error border-dashed"
              />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[65%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 4 -->
            <div class="w-12 h-[70%] flex flex-col justify-end gap-1 relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[70%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[80%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 5 -->
            <div class="w-12 h-[50%] flex flex-col justify-end gap-1 relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[50%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[85%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 6 -->
            <div class="w-12 h-[60%] flex flex-col justify-end gap-1 relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[60%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[85%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
            <!-- Day 7 -->
            <div class="w-12 h-[65%] flex flex-col justify-end gap-1 relative">
              <div class="w-full bg-primary/20 absolute bottom-0 h-[65%] rounded-t-sm" />
              <div
                class="w-full bg-tertiary/80 absolute bottom-0 h-[80%] rounded-t-sm z-10 border-t-2 border-tertiary"
              />
            </div>
          </div>
          <div
            class="absolute bottom-0 left-0 w-full pl-4 flex justify-around font-label-lg text-label-lg text-on-surface-variant"
          >
            <span>{{ t('周一') }}</span
            ><span>{{ t('周二') }}</span
            ><span class="text-error font-bold">{{ t('周三') }}</span
            ><span>{{ t('周四') }}</span
            ><span>{{ t('周五') }}</span
            ><span>{{ t('周六') }}</span
            ><span>{{ t('周日') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-hint {
  margin: 0;
  padding: 24px 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
.chart-area {
  margin-left: 30px;
}
</style>
