<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// PA-3 需求预测引擎（收益管理 C1）：模型配置 + 出租率预测 vs 实际 + 外部因子矩阵
// 数据：api.demo('yield') 取每日预测入住率，渲染为图表占位（CSS 柱条）
import { ref, onMounted, computed } from 'vue'
import { api } from '../../lib/api'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('yield')
})
// 解析 "84%" -> 84
function occPct(s: string) {
  return Number(String(s || '0').replace('%', '')) || 0
}
const maxOcc = computed(() => Math.max(100, ...rows.value.map((r) => occPct(r.predicted_occ))))
</script>

<template>
  <div class="page">
    <!-- 页头 + 模型配置面板 -->
    <div class="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-primary mb-1">
          <span class="material-symbols-outlined text-sm">auto_awesome</span>
          <span class="font-label-lg text-label-lg tracking-wider uppercase">Price Assistant</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-background">
          {{ t('PA-3 需求预测引擎') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-2 max-w-2xl">
          {{ t('配置预测模型并查看预期出租率对比历史基线。') }}AI {{ t('当前对') }}
          {{ rows.length || 30 }} {{ t('天预测窗口的准确率为') }} 94.2%。
        </p>
      </div>
      <div
        class="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-sm flex items-center gap-4 w-full md:w-auto"
      >
        <div class="flex-1">
          <label class="font-label-lg text-label-lg text-on-surface-variant block mb-1">{{
            t('当前模型')
          }}</label>
          <select
            class="w-full bg-transparent border-none font-headline-md text-headline-md text-primary p-0 focus:ring-0 cursor-pointer"
          >
            <option>{{ t('集成模型 (统计基线 + Pick-up)') }}</option>
            <option>Pure Statistical Baseline</option>
            <option>Event-Driven Aggressive</option>
          </select>
        </div>
        <div class="h-10 w-px bg-outline-variant mx-2"></div>
        <button
          class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">tune</span>{{ t('配置模型') }}
        </button>
      </div>
    </div>

    <!-- Bento 网格 -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter max-w-max-content-width">
      <!-- KPI 卡 -->
      <div
        class="md:col-span-3 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 flex flex-col justify-between shadow-sm relative overflow-hidden"
      >
        <div
          class="absolute -right-4 -top-4 w-24 h-24 bg-tertiary/10 rounded-full blur-xl pointer-events-none"
        ></div>
        <div>
          <h3 class="font-label-lg text-label-lg text-on-surface-variant flex items-center gap-2">
            <span class="material-symbols-outlined text-sm">target</span
            >{{ t('系统准确度 (MAPE)') }}
          </h3>
          <div class="mt-4 flex items-baseline gap-2">
            <span class="font-display-lg text-display-lg font-roboto-mono text-tertiary">5.8%</span>
            <span class="font-body-md text-body-md text-primary flex items-center"
              ><span class="material-symbols-outlined text-sm">trending_down</span> 1.2%</span
            >
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mt-2 text-sm">
            {{ t('过去 90 天的平均绝对百分比误差。越低越好。') }}
          </p>
        </div>
        <div class="mt-6">
          <div class="flex justify-between font-label-lg text-label-lg mb-1">
            <span class="text-on-surface-variant">{{ t('置信评分') }}</span
            ><span class="text-primary font-bold">{{ t('高') }}</span>
          </div>
          <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
            <div class="bg-primary h-full w-[92%] rounded-full"></div>
          </div>
        </div>
      </div>

      <!-- 主预测图（CSS 柱条占位，绑定 yield 数据） -->
      <div
        class="md:col-span-9 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="font-headline-md text-headline-md text-on-background">
            {{ t('出租率：预测 vs 实际') }}
          </h2>
          <div class="flex gap-2">
            <button
              class="px-3 py-1 text-sm border border-outline-variant rounded-md hover:bg-surface-container-low"
            >
              7D
            </button>
            <button
              class="px-3 py-1 text-sm bg-primary-container text-on-primary-container rounded-md"
            >
              30D
            </button>
            <button
              class="px-3 py-1 text-sm border border-outline-variant rounded-md hover:bg-surface-container-low"
            >
              90D
            </button>
          </div>
        </div>
        <div
          class="h-64 w-full relative flex items-end gap-2 pl-8 border-l border-b border-outline-variant"
        >
          <div
            v-for="r in rows"
            :key="r.id"
            class="flex-1 flex flex-col items-center justify-end h-full"
          >
            <span class="text-[10px] font-roboto-mono text-on-surface-variant mb-1">{{
              r.predicted_occ
            }}</span>
            <div
              class="w-full rounded-t bg-primary"
              :style="{ height: (occPct(r.predicted_occ) / maxOcc) * 100 + '%', opacity: 0.85 }"
            ></div>
          </div>
        </div>
        <div class="mt-4 flex gap-6 justify-center text-sm font-label-lg">
          <div class="flex items-center gap-2">
            <div class="w-4 h-0.5 bg-on-secondary-container"></div>
            <span class="text-on-surface">{{ t('实际出租率') }}</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-4 h-4 bg-primary rounded-sm"></div>
            <span class="text-on-surface">{{ t('AI 预测入住率') }}</span>
          </div>
        </div>
      </div>

      <!-- 外部因子影响矩阵 -->
      <div
        class="md:col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
      >
        <div
          class="p-6 border-b border-outline-variant flex justify-between items-center bg-surface-bright"
        >
          <div>
            <h2
              class="font-headline-md text-headline-md text-on-background flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-tertiary">bubble_chart</span
              >{{ t('外部因子影响矩阵') }}
            </h2>
            <p class="font-body-md text-body-md text-on-surface-variant mt-1">
              {{ t('外部事件对预测房型需求提升的贡献度。') }}
            </p>
          </div>
          <div class="hidden md:flex items-center gap-2 text-xs">
            <span class="text-on-surface-variant">{{ t('低影响') }}</span>
            <div
              class="w-32 h-2 rounded-full bg-gradient-to-r from-surface-container to-primary"
            ></div>
            <span class="text-on-surface-variant">{{ t('高提升') }}</span>
          </div>
        </div>
        <div class="p-6 overflow-x-auto">
          <table class="w-full min-w-[800px] text-left border-collapse">
            <thead>
              <tr>
                <th
                  class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant border-b border-outline-variant w-1/4"
                >
                  {{ t('外部因子') }}
                </th>
                <th
                  class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant border-b border-outline-variant text-center"
                >
                  {{ t('高级大床房') }}
                </th>
                <th
                  class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant border-b border-outline-variant text-center"
                >
                  {{ t('双床大床房') }}
                </th>
                <th
                  class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant border-b border-outline-variant text-center"
                >
                  {{ t('行政套房') }}
                </th>
                <th
                  class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant border-b border-outline-variant text-center"
                >
                  {{ t('家庭连通房') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-outline-variant/50 hover:bg-surface-bright">
                <td class="py-3 px-4 flex items-center gap-3">
                  <span class="material-symbols-outlined text-secondary">festival</span>
                  <div>
                    <div class="font-label-lg text-on-surface">{{ t('城市马拉松') }}</div>
                    <div class="text-xs text-on-surface-variant">{{ t('Nov 12 - 本地活动') }}</div>
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/40 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium"
                  >
                    +15%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/20 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium"
                  >
                    +8%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/10 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium"
                  >
                    +3%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/80 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-white"
                  >
                    +32%
                  </div>
                </td>
              </tr>
              <tr class="border-b border-outline-variant/50 hover:bg-surface-bright">
                <td class="py-3 px-4 flex items-center gap-3">
                  <span class="material-symbols-outlined text-secondary">cloud</span>
                  <div>
                    <div class="font-label-lg text-on-surface">{{ t('大雨预警') }}</div>
                    <div class="text-xs text-on-surface-variant">{{ t('Oct 28 - 天气') }}</div>
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-error/20 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-on-error-container"
                  >
                    -5%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-error/30 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-on-error-container"
                  >
                    -8%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-surface-container h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-on-surface-variant"
                  >
                    0%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-error/40 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-on-error-container"
                  >
                    -12%
                  </div>
                </td>
              </tr>
              <tr class="hover:bg-surface-bright">
                <td class="py-3 px-4 flex items-center gap-3">
                  <span class="material-symbols-outlined text-secondary">flight_takeoff</span>
                  <div>
                    <div class="font-label-lg text-on-surface">{{ t('法定节假日') }}</div>
                    <div class="text-xs text-on-surface-variant">{{ t('Dec 24-26 - 宏观') }}</div>
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/60 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-white"
                  >
                    +25%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/70 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-white"
                  >
                    +28%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/90 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-white"
                  >
                    +40%
                  </div>
                </td>
                <td class="p-1">
                  <div
                    class="bg-primary/80 h-10 rounded-md flex items-center justify-center font-roboto-mono text-sm font-medium text-white"
                  >
                    +35%
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
