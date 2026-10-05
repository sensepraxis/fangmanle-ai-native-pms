<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// PA-4 价格弹性估计（收益管理 C1）：各房型弹性系数 + 交互式需求曲线
// 数据：api.demo('rate') 取房型，按建议价相对当前价推导弹性系数占位
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('rate')
})
// 由价格建议推导一个示意弹性系数（负向，绝对值越小越低弹性）
function elasticity(r: any) {
  const c = Number(r.current_price || 0)
  const s = Number(r.suggested_price || 0)
  if (!c) return -1.0
  const e = -((s - c) / c) * 12.4
  return Math.round(e * 100) / 100
}
function conf(r: any) {
  if (r.confidence === '高') return t('高置信度')
  if (r.confidence === '中') return t('AI 推导')
  return t('市场基线')
}
</script>

<template>
  <div class="page">
    <header class="mb-8 flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">
          {{ t('PA-4 价格弹性估计') }}
        </h1>
        <p class="text-on-surface-variant font-body-lg">
          {{ t('PA-4 模块 · 针对所有房型场景的动态需求建模。') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-surface-container-high text-on-surface hover:bg-surface-variant rounded-lg font-label-lg transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">download</span> {{ t('导出数据') }}
        </button>
      </div>
    </header>

    <div class="grid grid-cols-12 gap-gutter">
      <!-- 弹性系数列表（v-for 绑定 demo('rate')） -->
      <div class="col-span-12 xl:col-span-4 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h2
            class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-primary">data_table</span
            >{{ t('弹性系数') }}
          </h2>
          <div class="space-y-4">
            <div
              v-for="(r, i) in rows"
              :key="r.id"
              class="p-4 rounded-lg bg-surface-bright border border-outline-variant/50 hover:bg-surface-container-low transition-colors cursor-pointer group"
              :class="{ 'ai-tinge': i % 2 === 1 }"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="font-label-lg text-on-surface font-semibold">
                  {{ r.room_type || t('房型') }}
                </div>
                <div
                  class="px-2 py-0.5 rounded font-num-md text-sm"
                  :class="
                    i % 2 === 1
                      ? 'bg-tertiary-container text-on-tertiary-container'
                      : 'bg-secondary-container text-on-secondary-container'
                  "
                >
                  {{ elasticity(r) }}
                </div>
              </div>
              <div class="w-full bg-surface-variant rounded-full h-1.5 mb-2 overflow-hidden">
                <div
                  class="h-1.5 rounded-full"
                  :class="i % 2 === 1 ? 'bg-tertiary' : 'bg-primary'"
                  :style="{ width: Math.min(100, Math.abs(elasticity(r)) * 60) + '%' }"
                ></div>
              </div>
              <div class="flex justify-between text-xs text-on-surface-variant">
                <span>{{ Math.abs(elasticity(r)) > 1 ? t('高弹性') : t('低弹性') }}</span>
                <span>{{ conf(r) }}</span>
              </div>
            </div>
            <div
              v-if="!rows.length"
              class="p-4 rounded-lg bg-surface-container border border-dashed border-outline text-on-surface-variant text-sm"
            >
              {{ t('暂无弹性数据') }}
            </div>
          </div>
        </div>
      </div>

      <!-- 交互式需求曲线（图表占位） -->
      <div class="col-span-12 xl:col-span-8 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex-1 flex flex-col"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">monitoring</span
              >{{ t('交互式需求曲线') }}
            </h2>
            <div class="flex bg-surface-container rounded-lg p-1">
              <button
                class="px-3 py-1 rounded bg-surface-container-lowest shadow-sm text-on-surface font-label-lg text-sm"
              >
                {{ t('标准') }}
              </button>
              <button
                class="px-3 py-1 rounded text-on-surface-variant hover:text-on-surface font-label-lg text-sm"
              >
                {{ t('套房') }}
              </button>
            </div>
          </div>
          <div
            class="relative w-full flex-1 min-h-[300px] bg-surface-bright border border-outline-variant/30 rounded-lg overflow-hidden flex items-center justify-center p-4"
          >
            <div
              class="absolute inset-x-8 bottom-8 top-8 border-l border-b border-outline-variant/50 flex items-end"
            >
              <div
                class="absolute -left-8 top-0 h-full flex flex-col justify-between text-xs text-on-surface-variant font-num-md py-2"
              >
                <span>100</span><span>50</span><span>0</span>
              </div>
              <div
                class="absolute -bottom-6 left-0 w-full flex justify-between text-xs text-on-surface-variant font-num-md px-2"
              >
                <span>$100</span><span>$200</span><span>$300</span>
              </div>
              <svg class="w-full h-full" preserveaspectratio="none" viewbox="0 0 100 100">
                <path
                  class="text-primary opacity-80"
                  d="M0,20 Q20,25 40,50 T80,80 L100,90"
                  fill="none"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-width="2"
                ></path>
                <path
                  d="M0,90 L0,20 Q20,25 40,50 T80,80 L100,90 L100,90 Z"
                  fill="#005bbf"
                  opacity="0.2"
                ></path>
                <circle
                  cx="40"
                  cy="50"
                  fill="#ffffff"
                  r="3"
                  stroke="#005bbf"
                  stroke-width="1.5"
                ></circle>
              </svg>
              <div
                class="absolute left-[38%] top-[40%] bg-surface-container-highest text-on-surface p-2 rounded shadow-md border border-outline-variant z-10 w-32"
              >
                <div class="text-xs text-on-surface-variant mb-1 font-label-lg">
                  {{ t('价位点') }}
                </div>
                <div class="font-num-md text-primary">$185.00</div>
                <div
                  class="text-[10px] text-on-surface-variant mt-1 border-t border-outline-variant pt-1"
                >
                  {{ t('预估需求: 64%') }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-gutter">
          <div
            class="bg-surface-bright border border-outline-variant rounded-xl p-4 flex items-start gap-3"
          >
            <span class="material-symbols-outlined text-secondary mt-0.5">lightbulb</span>
            <div>
              <h4 class="font-label-lg text-on-surface mb-1">{{ t('解读') }}</h4>
              <p class="text-body-md text-sm text-on-surface-variant">
                {{ t('系数为负表示价格上涨会导致需求下降，绝对值越大弹性越高。') }}
              </p>
            </div>
          </div>
          <div class="bg-[#fff8e1] border border-[#ffecb3] rounded-xl p-4 flex items-start gap-3">
            <span class="material-symbols-outlined text-[#fbc02d] mt-0.5">warning</span>
            <div>
              <h4 class="font-label-lg text-[#f57f17] mb-1">{{ t('建议复核') }}</h4>
              <p class="text-body-md text-sm text-[#f57f17]">
                {{ t('即将到来的节假日周末弹性表现出异常波动，AI 建议对标准客房进行人工复核。') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
