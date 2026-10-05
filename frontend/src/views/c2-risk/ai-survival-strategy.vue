<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 风险演变仿真与压力测试：当前轨迹 vs 风险影响 + 仿真参数 + AI 应对策略
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

type RiskOpt = { id: string | number; label: string; severity: number }

const risks = ref<RiskOpt[]>([])
const selectedId = ref<string | number>('')
const eventDay = ref(3)

const DAYS = 14

/** 基准轨迹：平稳偏升的日净利指数（相对 0–100 绘图高度） */
const baselineSeries = computed(() => {
  return Array.from({ length: DAYS }, (_, i) => {
    const wave = Math.sin(i / 2.2) * 6
    return Math.round(62 + i * 1.4 + wave)
  })
})

const selectedSeverity = computed(() => {
  const hit = risks.value.find((r) => String(r.id) === String(selectedId.value))
  return hit?.severity ?? 0.55
})

/** 压力轨迹：事件日后下探再缓慢回升 */
const stressSeries = computed(() => {
  const sev = selectedSeverity.value
  const ed = eventDay.value
  return baselineSeries.value.map((base, i) => {
    if (i < ed) return base
    const drop = sev * 48 * Math.min(1, (i - ed + 1) / 3)
    const recover = Math.max(0, (i - ed - 4) * 2.2)
    return Math.max(18, Math.round(base - drop + recover))
  })
})

function toPolyline(values: number[], w = 320, h = 160, pad = 12) {
  const max = 100
  const min = 0
  const usableW = w - pad * 2
  const usableH = h - pad * 2
  return values
    .map((v, i) => {
      const x = pad + (i / Math.max(values.length - 1, 1)) * usableW
      const y = pad + usableH - ((v - min) / (max - min)) * usableH
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function toAreaPath(values: number[], w = 320, h = 160, pad = 12) {
  const line = toPolyline(values, w, h, pad)
  const first = line.split(' ')[0]
  const last = line.split(' ').at(-1)!
  const [lx] = last.split(',')
  const [fx] = first.split(',')
  const bottom = h - pad
  return `M ${fx},${bottom} L ${line.replace(/ /g, ' L ')} L ${lx},${bottom} Z`
}

const basePoly = computed(() => toPolyline(baselineSeries.value))
const baseArea = computed(() => toAreaPath(baselineSeries.value))
const stressPoly = computed(() => toPolyline(stressSeries.value))
const stressArea = computed(() => toAreaPath(stressSeries.value))
const baseOverlayOnStress = computed(() => toPolyline(baselineSeries.value))

const baseKpis = computed(() => {
  const last = baselineSeries.value.at(-1) || 70
  const revpar = Math.round(380 + last * 1.1)
  const occ = Math.round(70 + last * 0.22)
  const profit = Math.round(80 + last * 0.65)
  return { revpar, occ: Math.min(96, occ), profit }
})

const stressKpis = computed(() => {
  const last = stressSeries.value.at(-1) || 40
  const baseLast = baselineSeries.value.at(-1) || 70
  const revpar = Math.round(380 + last * 1.1)
  const occ = Math.min(96, Math.round(70 + last * 0.22))
  const profit = Math.round(80 + last * 0.65)
  const dRev = Math.round(((revpar - (380 + baseLast * 1.1)) / (380 + baseLast * 1.1)) * 100)
  const dOcc = occ - Math.min(96, Math.round(70 + baseLast * 0.22))
  const dProfit = Math.round(((profit - (80 + baseLast * 0.65)) / (80 + baseLast * 0.65)) * 100)
  return { revpar, occ, profit, dRev, dOcc, dProfit }
})

const chartBarsBase = computed(() =>
  [0, 3, 6, 9, 13].map((idx) => ({
    label: `D${idx}`,
    h: baselineSeries.value[idx] ?? 60,
  })),
)

const chartBarsStress = computed(() =>
  [0, 3, 6, 9, 13].map((idx) => ({
    label: `D${idx}`,
    h: stressSeries.value[idx] ?? 40,
    base: baselineSeries.value[idx] ?? 60,
  })),
)

function scenarioLabel(r: any) {
  const type = r.type || r.alert_type || '经营'
  const desc = r.desc || r.message || '风险事件'
  return `${type}风险：${desc}`
}

function severityOf(r: any) {
  const lv = String(r.level || '').toLowerCase()
  if (lv === '高' || lv === 'critical' || lv === 'high') return 0.72
  if (lv === '中' || lv === 'warning' || lv === 'medium') return 0.55
  return 0.38
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
    risks.value = rows.map((r: any, i: number) => ({
      id: r.id ?? i + 1,
      label: scenarioLabel(r),
      severity: severityOf(r),
    }))
    selectedId.value = risks.value[0]?.id ?? ''
  } catch {
    risks.value = []
    selectedId.value = ''
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="space-y-6">
      <!-- 页头：与预警页同级字号 -->
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface">
            {{ t('风险演变仿真与压力测试') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            {{ t('模拟特定风险事件对核心指标的影响，并生成生存策略。') }}
          </p>
        </div>
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low"
          @click="router.push('/c2-risk/log')"
        >
          {{ t('查看执行记录 →') }}
        </button>
      </div>

      <!-- 仿真对照 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- 基准 -->
        <div
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col h-full"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">trending_up</span>
              <h3 class="font-headline-md text-headline-md text-on-surface">
                {{ t('当前轨迹 (基准)') }}
              </h3>
            </div>
            <span class="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded"
              >T+0 ~ T+14</span
            >
          </div>

          <div class="rounded-lg border border-outline-variant bg-surface p-3 mb-3">
            <svg class="w-full h-[160px]" viewBox="0 0 320 160" preserveAspectRatio="none">
              <defs>
                <linearGradient id="baseFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.28" />
                  <stop offset="100%" stop-color="var(--primary)" stop-opacity="0.02" />
                </linearGradient>
              </defs>
              <line
                x1="12"
                y1="40"
                x2="308"
                y2="40"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <line
                x1="12"
                y1="80"
                x2="308"
                y2="80"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <line
                x1="12"
                y1="120"
                x2="308"
                y2="120"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <path :d="baseArea" fill="url(#baseFill)" />
              <polyline
                :points="basePoly"
                fill="none"
                stroke="var(--primary)"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div class="flex justify-between text-[10px] text-on-surface-variant px-1">
              <span>{{ t('发生前走势平稳') }}</span>
              <span>{{ t('日净利指数') }}</span>
            </div>
          </div>

          <div class="h-16 flex items-end gap-2 mb-4 px-1">
            <div
              v-for="b in chartBarsBase"
              :key="b.label"
              class="flex-1 flex flex-col items-center gap-1"
            >
              <div
                class="w-full max-w-[36px] bg-primary/70 rounded-t-sm"
                :style="{ height: Math.max(12, b.h * 0.55) + 'px' }"
              ></div>
              <span class="text-[10px] text-on-surface-variant">{{ b.label }}</span>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="bg-surface-container-low p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('预计 RevPAR') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">¥{{ baseKpis.revpar }}</p>
            </div>
            <div class="bg-surface-container-low p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('预计入住率') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">{{ baseKpis.occ }}%</p>
            </div>
            <div class="bg-surface-container-low p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('预计净利') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-surface">¥{{ baseKpis.profit }}k</p>
            </div>
          </div>
        </div>

        <!-- 风险影响 -->
        <div
          class="col-span-12 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col h-full relative overflow-hidden"
        >
          <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
          <div class="flex items-center justify-between mb-4 pl-3">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-error">warning</span>
              <h3 class="font-headline-md text-headline-md text-on-surface">
                {{ t('风险影响预测') }}
              </h3>
            </div>
            <span
              class="bg-error-container text-on-error-container text-xs px-2 py-1 rounded font-bold"
              >{{ t('模拟中 · 第') }} {{ eventDay }} {{ t(' 天触发') }}</span
            >
          </div>

          <div class="rounded-lg border border-outline-variant bg-surface p-3 mb-3 ml-3">
            <svg class="w-full h-[160px]" viewBox="0 0 320 160" preserveAspectRatio="none">
              <defs>
                <linearGradient id="stressFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#c5221f" stop-opacity="0.3" />
                  <stop offset="100%" stop-color="#c5221f" stop-opacity="0.03" />
                </linearGradient>
              </defs>
              <line
                x1="12"
                y1="40"
                x2="308"
                y2="40"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <line
                x1="12"
                y1="80"
                x2="308"
                y2="80"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <line
                x1="12"
                y1="120"
                x2="308"
                y2="120"
                stroke="var(--outline-variant)"
                stroke-dasharray="4 4"
              />
              <polyline
                :points="baseOverlayOnStress"
                fill="none"
                stroke="var(--outline)"
                stroke-width="1.5"
                stroke-dasharray="5 4"
                opacity="0.7"
              />
              <path :d="stressArea" fill="url(#stressFill)" />
              <polyline
                :points="stressPoly"
                fill="none"
                stroke="#c5221f"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div class="flex justify-between text-[10px] text-on-surface-variant px-1">
              <span class="flex items-center gap-2">
                <span class="inline-block w-4 border-t border-dashed border-outline"></span
                >{{ t('基准') }} <span class="inline-block w-4 border-t-2 border-[#c5221f]"></span
                >{{ t('压力') }}</span
              >
              <span>{{ t('触发后下探再缓慢回升') }}</span>
            </div>
          </div>

          <div class="h-16 flex items-end gap-2 mb-4 px-1 ml-3">
            <div
              v-for="b in chartBarsStress"
              :key="'s-' + b.label"
              class="flex-1 flex flex-col items-center gap-1"
            >
              <div
                class="w-full max-w-[40px] flex items-end justify-center gap-0.5"
                style="height: 48px"
              >
                <div
                  class="w-[45%] bg-surface-container-highest rounded-t-sm"
                  :style="{ height: Math.max(8, b.base * 0.45) + 'px' }"
                ></div>
                <div
                  class="w-[45%] bg-error/80 rounded-t-sm"
                  :style="{ height: Math.max(8, b.h * 0.45) + 'px' }"
                ></div>
              </div>
              <span class="text-[10px] text-on-surface-variant">{{ b.label }}</span>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-4 pl-3">
            <div class="bg-error-container p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-error-container mb-1">
                {{ t('压力 RevPAR') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-error-container">
                ¥{{ stressKpis.revpar }}
                <span class="text-sm font-normal text-error">({{ stressKpis.dRev }}%)</span>
              </p>
            </div>
            <div class="bg-error-container p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-error-container mb-1">
                {{ t('压力入住率') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-error-container">
                {{ stressKpis.occ }}%
                <span class="text-sm font-normal text-error">({{ stressKpis.dOcc }}%)</span>
              </p>
            </div>
            <div class="bg-error-container p-4 rounded-lg">
              <p class="font-label-lg text-label-lg text-on-error-container mb-1">
                {{ t('压力净利') }}
              </p>
              <p class="font-num-xl text-num-xl text-on-error-container">
                ¥{{ stressKpis.profit }}k
                <span class="text-sm font-normal text-error">({{ stressKpis.dProfit }}%)</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- 仿真参数 -->
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
      >
        <h3 class="font-headline-md text-headline-md text-on-surface mb-4">
          {{ t('设定仿真参数') }}
        </h3>
        <div class="flex flex-col lg:flex-row lg:items-end gap-6">
          <div class="w-full lg:w-1/3">
            <label class="block font-label-lg text-label-lg text-on-surface-variant mb-2">{{
              t('风险场景')
            }}</label>
            <select
              v-model="selectedId"
              class="w-full bg-surface border border-outline-variant rounded-lg py-2 px-3 text-on-surface focus:ring-2 focus:ring-primary outline-none"
            >
              <option v-if="!risks.length" value="">{{ t('暂无风险场景') }}</option>
              <option v-for="r in risks" :key="r.id" :value="r.id">{{ r.label }}</option>
            </select>
          </div>
          <div class="flex-1">
            <div
              class="flex justify-between font-label-lg text-label-lg text-on-surface-variant mb-2"
            >
              <span>{{ t('影响时间轴 (T+0 至 T+14)') }}</span>
              <span class="font-num-md text-num-md"
                >{{ t('第') }} {{ eventDay }} {{ t('天') }}</span
              >
            </div>
            <input
              v-model.number="eventDay"
              class="w-full h-2 bg-surface-variant rounded-lg appearance-none cursor-pointer accent-primary"
              max="14"
              min="0"
              type="range"
            />
            <div class="flex justify-between text-xs text-on-surface-variant mt-1">
              <span>{{ t('发生日') }}</span>
              <span>{{ t('+1周') }}</span>
              <span>{{ t('+2周') }}</span>
            </div>
          </div>
          <div>
            <button
              type="button"
              class="bg-primary text-on-primary px-6 py-2 rounded-lg font-label-lg text-label-lg flex items-center gap-2 hover:opacity-90 transition-colors shadow-sm"
            >
              <span class="material-symbols-outlined">play_circle</span>
              {{ t('运行仿真') }}
            </button>
          </div>
        </div>
      </div>

      <!-- AI 应对策略 -->
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm relative overflow-hidden"
      >
        <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
        <div class="pl-3">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-tertiary">psychology</span>
            <h3 class="font-headline-md text-headline-md text-on-surface">
              {{ t('AI 应对策略推荐 (Survival Strategy)') }}
            </h3>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              class="bg-surface p-4 rounded-lg border border-outline-variant flex gap-4 items-start"
            >
              <div class="bg-tertiary-container text-on-tertiary-container p-2 rounded-full mt-1">
                <span class="material-symbols-outlined">local_offer</span>
              </div>
              <div>
                <h4 class="font-label-lg text-label-lg text-on-surface font-bold mb-1">
                  {{ t('本地客源闪促 (Flash Sale)') }}
                </h4>
                <p class="font-body-md text-body-md text-on-surface-variant mb-3">
                  {{
                    t(
                      '针对暴雨天气，长途客源减少。建议向本地会员发送周边游「微度假」套餐，降低未售出库存风险。',
                    )
                  }}
                </p>
                <button
                  type="button"
                  class="text-primary font-label-lg text-label-lg font-bold hover:underline"
                >
                  {{ t('一键生成营销短信') }}
                </button>
              </div>
            </div>
            <div
              class="bg-surface p-4 rounded-lg border border-outline-variant flex gap-4 items-start"
            >
              <div class="bg-tertiary-container text-on-tertiary-container p-2 rounded-full mt-1">
                <span class="material-symbols-outlined">handshake</span>
              </div>
              <div>
                <h4 class="font-label-lg text-label-lg text-on-surface font-bold mb-1">
                  {{ t('室内游乐设施联动') }}
                </h4>
                <p class="font-body-md text-body-md text-on-surface-variant mb-3">
                  {{
                    t(
                      '与周边 2 公里内的室内儿童乐园、温泉馆合作，推出「风雨无阻」联票，增加产品附加值。',
                    )
                  }}
                </p>
                <button
                  type="button"
                  class="text-primary font-label-lg text-label-lg font-bold hover:underline"
                >
                  {{ t('查看合作商户列表') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
