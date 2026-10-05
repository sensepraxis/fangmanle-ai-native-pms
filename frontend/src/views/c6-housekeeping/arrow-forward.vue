<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * AI 服务质量保障 —— KPI/对话表优先 board.service_requests；培训文案页内兜底。
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const router = useRouter()

const FALLBACK = {
  coaching: t('本周前台团队对英文咨询的响应积极度提升了 15%。建议保持当前的沟通模板库更新频率。'),
  kpis: [
    {
      label: t('AI 自动解决率'),
      value: '68',
      unit: '%',
      delta: '↑ 5%',
      deltaUp: true,
      note: t('较上周提升，复杂客需仍建议人工复核'),
      icon: 'smart_toy',
      accent: 'primary',
    },
    {
      label: t('待人工介入'),
      value: '4',
      unit: t('单'),
      delta: '↓ 2',
      deltaUp: true,
      note: t('开放客需中需复核对话'),
      icon: 'support_agent',
      accent: 'primary',
    },
    {
      label: t('客诉风险指数'),
      value: '12',
      unit: '',
      delta: '↓ 8%',
      deltaUp: true,
      note: t('情感得分加权风险'),
      icon: 'sentiment_dissatisfied',
      accent: 'tertiary',
      glow: true,
      chart: t('趋势向好'),
    },
  ],
  dialogs: [
    {
      room: '302',
      guest: 'John Doe',
      when: '14:02',
      mood: t('焦虑'),
      moodIcon: 'sentiment_dissatisfied',
      risk: 'high',
      topic: t('空调噪音影响休息，要求换房'),
      act: t('经理介入'),
      actIcon: 'supervisor_account',
    },
    {
      room: '508',
      guest: t('王女士'),
      when: '13:18',
      mood: t('一般'),
      moodIcon: 'sentiment_neutral',
      risk: 'mid',
      topic: t('额外枕头送达延迟 25 分钟'),
      act: t('致歉+补偿'),
      actIcon: 'redeem',
    },
    {
      room: '1206',
      guest: t('李先生'),
      when: '11:45',
      mood: t('平和'),
      moodIcon: 'sentiment_satisfied',
      risk: 'low',
      topic: t('咨询周边餐厅推荐'),
      act: t('AI 已回复'),
      actIcon: 'check_circle',
    },
  ],
}

const data = ref<any>({ ...FALLBACK })

function riskFromPriority(p?: number) {
  if ((p || 5) <= 2) return 'high'
  if ((p || 5) <= 3) return 'mid'
  return 'low'
}

function moodFromRisk(risk: string) {
  if (risk === 'high') return { mood: t('焦虑'), moodIcon: 'sentiment_dissatisfied' }
  if (risk === 'mid') return { mood: t('一般'), moodIcon: 'sentiment_neutral' }
  return { mood: t('平和'), moodIcon: 'sentiment_satisfied' }
}

function actFromRisk(risk: string) {
  if (risk === 'high') return { act: t('经理介入'), actIcon: 'supervisor_account' }
  if (risk === 'mid') return { act: t('致歉+补偿'), actIcon: 'redeem' }
  return { act: t('AI 已回复'), actIcon: 'check_circle' }
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const srs = board?.service_requests || board?.stream || []
    const openSr = srs.filter((x: any) => x.open)
    const closedSr = srs.filter((x: any) => !x.open)
    const autoRate = srs.length
      ? Math.round((100 * closedSr.length) / srs.length)
      : FALLBACK.kpis[0].value

    const dialogs = openSr.slice(0, 8).map((r: any) => {
      const risk = riskFromPriority(r.priority)
      const mood = moodFromRisk(risk)
      const act = actFromRisk(risk)
      return {
        room: (r.room || r.room_no || '—').replace(/^0+/, '').slice(-4) || r.room,
        guest: r.guest || r.assignee || t('住客'),
        when: r.time || '—',
        topic: r.content || r.msg || r.parse || t('客需'),
        risk,
        ...mood,
        ...act,
      }
    })

    const perf = board?.performance || {}
    const coachingIns = (perf.insights || [])[0]
    const coaching =
      typeof coachingIns === 'string'
        ? coachingIns
        : coachingIns?.d || coachingIns?.desc || FALLBACK.coaching

    data.value = {
      coaching,
      kpis: [
        {
          label: t('AI 自动解决率'),
          value: String(autoRate),
          unit: '%',
          delta: closedSr.length ? t('↑ 实时') : FALLBACK.kpis[0].delta,
          deltaUp: true,
          note: `已关闭 ${closedSr.length} / 总计 ${srs.length} 单客需`,
          icon: 'smart_toy',
          accent: 'primary',
        },
        {
          label: t('待人工介入'),
          value: String(openSr.length || FALLBACK.kpis[1].value),
          unit: t('单'),
          delta: openSr.length ? t('需复核') : '↓ 0',
          deltaUp: !openSr.length,
          note: t('开放客需中需复核对话'),
          icon: 'support_agent',
          accent: 'primary',
        },
        {
          ...FALLBACK.kpis[2],
          value: String(Math.max(5, Math.min(40, openSr.length * 3 + 8))),
          note: openSr.length ? `${openSr.length} 单开放客需加权风险` : FALLBACK.kpis[2].note,
        },
      ],
      dialogs: dialogs.length ? dialogs : FALLBACK.dialogs,
    }
  } catch {
    data.value = { ...FALLBACK }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="page-head head-row">
      <div>
        <h1>{{ t('AI 服务质量保障仪表盘') }}</h1>
        <p>{{ t('客诉情绪监测、AI 响应效能与人工介入建议。') }}</p>
      </div>
      <div class="head-actions">
        <HousekeepingFlowNav mode="guest" />
      </div>
    </div>

    <!-- AI 培训洞察横幅 -->
    <div
      class="rounded-r-lg shadow-sm flex items-start gap-3 p-4 mb-6"
      style="background: rgba(140, 51, 179, 0.1); border-left: 4px solid var(--tertiary)"
    >
      <span class="material-symbols-outlined text-tertiary mt-0.5">tips_and_updates</span>
      <div>
        <h4 class="font-label-lg text-on-surface font-semibold mb-1">{{ t('AI 培训洞察') }}</h4>
        <p class="text-on-surface-variant">{{ data.coaching }}</p>
      </div>
    </div>

    <!-- KPI 三联 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      <template v-for="(k, i) in data.kpis || []" :key="i">
        <div class="card-clean card-pad flex flex-col shadow-sm" :class="k.glow ? 'ai-glow' : ''">
          <div class="flex justify-between items-center mb-4">
            <span class="font-label-lg text-on-surface-variant">{{ k.label }}</span>
            <span
              class="material-symbols-outlined rounded-full text-[20px] p-1.5"
              :class="k.accent === 'tertiary' ? 'text-tertiary' : 'text-primary'"
              :style="
                k.accent === 'tertiary'
                  ? 'background:rgba(140,51,179,.12)'
                  : 'background:var(--primary-fixed)'
              "
              >{{ k.icon }}</span
            >
          </div>
          <div class="flex items-baseline gap-2">
            <span class="font-num-xl text-[36px] text-on-surface font-bold leading-none">{{
              k.value
            }}</span>
            <span v-if="k.unit" class="text-on-surface-variant text-sm">{{ k.unit }}</span>
            <span
              v-if="k.delta"
              class="font-label-lg text-label-lg px-2 py-0.5 rounded flex items-center"
              :style="
                k.deltaUp ? 'color:#1e8e3e;background:#e6f4ea' : 'color:#ba1a1a;background:#ffdad6'
              "
            >
              <span class="material-symbols-outlined text-[14px] mr-0.5">{{
                k.deltaUp ? 'arrow_upward' : 'arrow_downward'
              }}</span
              >{{ k.delta }}</span
            >
          </div>
          <p class="text-outline mt-2 text-sm">{{ k.note }}</p>
          <div v-if="k.chart" class="h-16 w-full relative mt-2">
            <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
              <path
                d="M0,35 Q10,20 20,25 T40,15 T60,20 T80,5 T100,10"
                fill="none"
                stroke="var(--tertiary)"
                stroke-width="2"
              ></path>
              <path
                d="M0,35 Q10,20 20,25 T40,15 T60,20 T80,5 T100,10 L100,40 L0,40 Z"
                fill="var(--tertiary)"
                opacity="0.1"
              ></path>
            </svg>
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span
                class="font-num-md text-tertiary font-bold px-3 py-1 rounded-full shadow-sm text-sm border"
                style="background: var(--surface-lowest); border-color: rgba(235, 178, 255, 0.5)"
                >{{ k.chart }}</span
              >
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 需人工介入对话表 -->
    <div class="card-clean shadow-sm overflow-hidden flex flex-col">
      <div class="p-6 border-b border-outline-variant flex justify-between items-center">
        <div>
          <h3 class="font-semibold text-lg text-on-surface">
            {{ t('近期标记对话 (需人工介入)') }}
          </h3>
          <p class="text-sm text-on-surface-variant mt-1">
            {{ t('AI 检测到潜在客诉风险，建议复核。') }}
          </p>
        </div>
        <button
          class="flex items-center gap-2 px-4 py-2 border rounded-lg font-label-lg text-on-surface hover:bg-surface-low transition-colors"
        >
          <span class="material-symbols-outlined text-[18px]">filter_list</span>{{ t('筛选') }}
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="table-data w-full text-left border-collapse">
          <thead>
            <tr class="bg-surface-low">
              <th>{{ t('房间/客户') }}</th>
              <th>{{ t('情感得分') }}</th>
              <th>{{ t('话题摘要') }}</th>
              <th>{{ t('AI 建议动作') }}</th>
              <th class="text-right">{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody class="bg-surface-lowest">
            <template v-for="(r, i) in data.dialogs || []" :key="i">
              <tr
                :class="r.risk === 'high' ? '' : 'hover:bg-surface-low transition-colors group'"
                :style="r.risk === 'high' ? 'background:rgba(186,26,26,.08)' : ''"
              >
                <td class="p-4">
                  <div class="flex items-center gap-3">
                    <div
                      class="w-8 h-8 rounded bg-surface-high flex items-center justify-center font-num-md text-sm font-bold text-on-surface"
                    >
                      {{ r.room }}
                    </div>
                    <div>
                      <div class="font-semibold text-on-surface">{{ r.guest }}</div>
                      <div class="text-xs text-on-surface-variant">{{ r.when }}</div>
                    </div>
                  </div>
                </td>
                <td class="p-4">
                  <div class="flex items-center gap-1.5">
                    <span
                      class="material-symbols-outlined text-[18px]"
                      :class="
                        r.risk === 'high'
                          ? 'text-error'
                          : r.risk === 'mid'
                            ? 'text-amber'
                            : 'text-on-surface-variant'
                      "
                      >{{ r.moodIcon }}</span
                    >
                    <span
                      class="font-medium"
                      :class="
                        r.risk === 'high'
                          ? 'text-error'
                          : r.risk === 'mid'
                            ? 'text-amber'
                            : 'text-on-surface-variant'
                      "
                      >{{ r.mood }}</span
                    >
                  </div>
                </td>
                <td class="p-4 text-on-surface-variant">{{ r.topic }}</td>
                <td class="p-4">
                  <span
                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border"
                    :style="
                      r.risk === 'high'
                        ? 'background:#ffdad6;color:#93000a;border-color:rgba(186,26,26,.3)'
                        : r.risk === 'mid'
                          ? 'background:#fff3cd;color:#856404;border-color:#ffeeba'
                          : 'background:rgba(140,51,179,.12);color:#72008a;border-color:rgba(235,178,255,.5)'
                    "
                  >
                    <span class="material-symbols-outlined text-[14px]">{{ r.actIcon }}</span>
                    {{ r.act }}</span
                  >
                </td>
                <td class="p-4 text-right">
                  <button
                    class="text-primary hover:text-primary-container font-label-lg font-medium transition-colors"
                    type="button"
                    @click="router.push('/c6-housekeeping/room-302-john-doe')"
                  >
                    {{ t('查看对话') }}
                  </button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="p-4 border-t border-outline-variant bg-surface-lowest flex justify-end">
        <button
          class="font-label-lg text-primary hover:underline flex items-center gap-1"
          type="button"
          @click="router.push('/c6-housekeeping/view-full-incident-log')"
        >
          {{ t('查看完整报告')
          }}<span class="material-symbols-outlined text-[18px]">arrow_forward</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}
.head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.ai-glow {
  box-shadow: -2px 0 8px rgba(140, 51, 179, 0.15);
  border-left: 2px solid var(--tertiary);
}
</style>
