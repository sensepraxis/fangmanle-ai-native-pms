<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 自动化对策执行记录：时间线审计日志
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

type LogRow = {
  id: number | string
  type: string
  level: string
  desc: string
  status: string
  time: string
  handled: boolean
}

const logs = ref<LogRow[]>([])

function mapLevel(raw: string) {
  const s = (raw || '').toLowerCase()
  if (s === '高' || s === 'critical' || s === 'high') return t('高')
  if (s === '中' || s === 'warning' || s === 'medium' || s === 'mid') return t('中')
  return t('低')
}

function mapAlert(r: any, i: number): LogRow {
  const status = r.status || (r.handled ? 'handled' : 'open')
  const handled = r.handled === true || ['closed', 'handled', 'ack', 'resolved'].includes(status)
  return {
    id: r.id ?? i + 1,
    type: r.type || r.alert_type || '经营',
    level: mapLevel(r.level),
    desc: r.desc || r.message || '风险事件',
    status,
    time:
      r.triggered_at || (r.created_at ? String(r.created_at).replace('T', ' ').slice(0, 16) : '—'),
    handled,
  }
}

async function load() {
  try {
    let rows: any[] = []
    try {
      const board = await api.riskBoard(hotelStore.hotelId)
      rows = board?.alerts || []
    } catch {
      rows = (await api.listRiskAlerts(hotelStore.hotelId)) || []
    }
    logs.value = rows.map(mapAlert)
  } catch {
    logs.value = []
  }
}

function statusOf(r: LogRow) {
  if (r.handled)
    return {
      label: t('成功缓解'),
      cls: 'bg-[#E6F4EA] text-[#137333] border border-[#CEEAD6]',
      icon: 'check_circle',
      iconCls: 'bg-primary-fixed text-on-primary-fixed',
    }
  if (r.level === '中')
    return {
      label: t('需人工介入 (中风险 R2)'),
      cls: 'bg-[#FEF7E0] text-[#B06000] border border-[#FAD200]',
      icon: 'warning',
      iconCls: 'bg-[#FEF7E0] text-[#B06000]',
    }
  return {
    label: t('执行中'),
    cls: 'bg-primary-container text-on-primary-container',
    icon: 'sync',
    iconCls: 'bg-surface-container-high text-primary',
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="max-w-4xl mx-auto">
      <!-- 页头 -->
      <div class="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background mb-2">
            {{ t('自动化对策执行记录') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('审查 AI 风险响应的性能并提供反馈以优化未来决策。') }}
          </p>
        </div>
        <div class="flex gap-2 flex-wrap justify-end">
          <button
            type="button"
            class="px-4 py-2 border border-outline-variant rounded-full text-on-surface hover:bg-surface-variant transition-colors font-label-lg"
            @click="router.push('/c2-risk/black-swan-warning')"
          >
            {{ t('← 返回预警') }}
          </button>
          <button
            class="px-4 py-2 border border-outline-variant rounded-full text-on-surface hover:bg-surface-variant transition-colors font-label-lg flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-[18px]">filter_list</span> {{ t('筛选') }}
          </button>
          <button
            class="px-4 py-2 border border-outline-variant rounded-full text-on-surface hover:bg-surface-variant transition-colors font-label-lg flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-[18px]">download</span> {{ t('导出') }}
          </button>
        </div>
      </div>
      <!-- 时间线 -->
      <div class="space-y-6">
        <div v-for="r in logs" :key="r.id" class="relative timeline-item flex gap-6">
          <div class="timeline-line relative flex flex-col items-center">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-sm border-2 border-white"
              :class="statusOf(r).iconCls"
            >
              <span
                class="material-symbols-outlined text-[20px]"
                :class="{ 'animate-spin': !r.handled && r.level !== '中' }"
                >{{ statusOf(r).icon }}</span
              >
            </div>
          </div>
          <div
            class="flex-1 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm hover:shadow-md transition-shadow"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="px-2.5 py-0.5 rounded-full text-[12px] font-medium"
                    :class="statusOf(r).cls"
                    >{{ statusOf(r).label }}</span
                  >
                  <span class="text-on-surface-variant text-sm font-num-md">{{ r.time }}</span>
                  <span class="text-on-surface-variant text-xs">· {{ r.status }}</span>
                </div>
                <h3 class="font-headline-md text-headline-md text-on-background">
                  {{ r.type }}{{ t('风险：') }}{{ r.desc }}
                </h3>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div class="bg-surface p-4 rounded-lg border border-outline-variant/50">
                <div class="text-xs text-on-surface-variant mb-1 uppercase tracking-wider">
                  {{ t('执行操作 (AI)') }}
                </div>
                <div class="font-body-md text-on-surface flex items-start gap-2">
                  <span class="material-symbols-outlined text-primary text-[18px] mt-0.5"
                    >smart_toy</span
                  >
                  AI {{ t('针对「') }}{{ r.desc }}」{{ t('自动生成应对动作并')
                  }}{{ r.handled ? t('已完成缓解') : t('等待人工确认') }}。
                </div>
              </div>
              <div class="bg-surface p-4 rounded-lg border border-outline-variant/50">
                <div class="text-xs text-on-surface-variant mb-1 uppercase tracking-wider">
                  {{ t('结果影响') }}
                </div>
                <div
                  class="font-body-md flex items-start gap-2 font-medium"
                  :class="r.handled ? 'text-[#137333]' : 'text-on-surface'"
                >
                  <span
                    class="material-symbols-outlined text-[18px] mt-0.5"
                    :class="r.handled ? 'savings' : 'analytics'"
                  ></span>
                  {{
                    r.handled
                      ? t('已挽回潜在损失，维持关键指标稳定。')
                      : t('若执行，预计影响收益，请确认是否放行。')
                  }}
                </div>
              </div>
            </div>
            <div
              class="border-t border-outline-variant pt-4 flex items-center justify-between bg-surface-bright -mx-6 -mb-6 px-6 py-4 rounded-b-xl"
            >
              <div class="flex items-center gap-2 text-sm text-on-surface-variant">
                <span class="material-symbols-outlined text-[18px]">thumbs_up_down</span
                >{{ t('人工反馈 (训练模型)') }}
              </div>
              <div class="flex gap-2">
                <button
                  class="px-4 py-1.5 border border-outline-variant rounded-md text-on-surface hover:bg-surface-variant transition-colors text-sm font-medium"
                >
                  {{ t('微调逻辑') }}
                </button>
                <button
                  class="px-4 py-1.5 bg-primary text-on-primary rounded-md hover:bg-primary-fixed-variant transition-colors text-sm font-medium flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-[16px]">thumb_up</span>
                  {{ t('批准模型') }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div
          v-if="!logs.length"
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 text-on-surface-variant"
        >
          {{ t('暂无执行记录') }}
        </div>
      </div>
    </div>
  </div>
</template>
