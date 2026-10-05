<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 分发策略与 AI 平衡：渠道佣金与权重设定 + 仿真区
// 核心域：api.listChannels 渲染渠道权重（佣金越低权重越高，派生展示）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const channels = ref<any[]>([])
onMounted(async () => {
  channels.value = await api.listChannels()
})
// 目标权重：佣金越低权重越高（派生）
function weight(c: any) {
  const comm = Number(c.commission_rate || 0)
  return Math.min(65, Math.max(8, Math.round((1 - comm) * 50)))
}
function commText(c: any) {
  return (Number(c.commission_rate || 0) * 100).toFixed(0) + '%'
}
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto space-y-6">
      <!-- 页头 -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-1">
            {{ t('分发策略与AI平衡') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('配置渠道权重、库存阈值，并测试AI自动调配逻辑。') }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <div
            class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border border-outline-variant text-sm shadow-sm"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span class="font-medium text-on-surface">{{ t('AI 自动调配: 运行中') }}</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input checked="" class="sr-only peer" type="checkbox" value="" />
            <div
              class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-outline-variant after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
            ></div>
          </label>
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- 左列：渠道权重 -->
        <div class="lg:col-span-7 flex flex-col gap-6">
          <div
            class="bg-white rounded-xl border border-outline-variant p-6 shadow-sm relative overflow-hidden"
          >
            <div
              class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-tertiary opacity-70"
            ></div>
            <div class="flex justify-between items-start mb-6">
              <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">account_tree</span>
                {{ t('渠道佣金与权重设定') }}
              </h2>
              <button class="text-primary hover:bg-primary-fixed/20 p-1 rounded transition-colors">
                <span class="material-symbols-outlined text-[20px]">edit</span>
              </button>
            </div>
            <!-- 渠道权重列表（数据驱动：listChannels） -->
            <div class="space-y-5">
              <div v-for="c in channels" :key="c.id" class="group">
                <div class="flex justify-between items-end mb-2">
                  <div class="flex items-center gap-2">
                    <div
                      class="w-8 h-8 rounded bg-surface-container-high flex items-center justify-center"
                    >
                      <span class="material-symbols-outlined text-[18px] text-on-surface-variant"
                        >hub</span
                      >
                    </div>
                    <div>
                      <div class="font-label-lg text-label-lg font-bold text-on-surface">
                        {{ c.name }}
                      </div>
                      <div class="text-xs text-on-surface-variant">
                        {{ t('佣金:') }} {{ commText(c) }}
                      </div>
                    </div>
                  </div>
                  <div class="font-num-md text-num-md text-primary">
                    {{ t('目标权重:') }} {{ weight(c) }}%
                  </div>
                </div>
                <div class="w-full bg-surface-variant rounded-full h-2.5">
                  <div
                    class="bg-primary h-2.5 rounded-full"
                    :style="{ width: weight(c) + '%' }"
                  ></div>
                </div>
              </div>
              <div v-if="!channels.length" class="text-on-surface-variant text-sm py-4">
                {{ t('加载渠道中…') }}
              </div>
            </div>
            <div class="mt-6 p-3 bg-primary-fixed/30 rounded-lg flex gap-3 ai-border">
              <span class="material-symbols-outlined text-primary mt-0.5">lightbulb</span>
              <div>
                <div class="font-label-lg text-label-lg text-on-surface font-semibold mb-1">
                  {{ t('AI 建议') }}
                </div>
                <div class="text-sm text-on-surface-variant">
                  {{
                    t(
                      '基于历史数据，建议将 Direct 目标权重提升至 65%，以优化整体 RevPAR。当前配置可能会在旺季流失部分高净值散客。',
                    )
                  }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 右列：仿真 -->
        <div class="lg:col-span-5 flex flex-col gap-6">
          <div
            class="bg-white rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col h-full"
          >
            <h2
              class="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-2"
            >
              <span class="material-symbols-outlined text-tertiary">science</span>
              {{ t('仿真区') }}
            </h2>
            <p class="text-sm text-on-surface-variant mb-6">
              {{ t('测试规则配置在极端流量波动下的表现。') }}
            </p>
            <div class="bg-surface-bright border border-outline-variant rounded-lg p-4 mb-6">
              <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                t('选择模拟场景')
              }}</label>
              <select
                class="w-full bg-white border border-outline-variant text-on-surface text-sm rounded-lg focus:ring-primary focus:border-primary block p-2.5 outline-none"
              >
                <option>{{ t('如果 Ctrip 流量上涨 30%') }}</option>
                <option>{{ t('如果 Direct 预订取消率增加 15%') }}</option>
                <option>{{ t('如果 周边竞对整体降价 10%') }}</option>
              </select>
            </div>
            <div class="flex-1 flex flex-col">
              <div class="font-label-lg text-label-lg text-on-surface font-semibold mb-4">
                {{ t('AI 动态响应预测') }}
              </div>
              <div
                class="relative pl-6 pb-6 border-l-2 border-primary/20 last:border-0 last:pb-0 space-y-6"
              >
                <div class="relative">
                  <div class="absolute -left-[31px] bg-white p-1 rounded-full">
                    <div class="w-3 h-3 bg-primary rounded-full ring-4 ring-primary/20"></div>
                  </div>
                  <div
                    class="bg-surface-container-low rounded-lg p-3 border border-outline-variant/50"
                  >
                    <div class="font-medium text-sm text-on-surface mb-1">
                      {{ t('触发阈值响应') }}
                    </div>
                    <div class="text-xs text-on-surface-variant">
                      {{ t('检测到 Ctrip 流量激增，预计2小时内突破 30% 权重上限。') }}
                    </div>
                  </div>
                </div>
                <div class="relative">
                  <div class="absolute -left-[31px] bg-white p-1 rounded-full">
                    <div class="w-3 h-3 bg-tertiary rounded-full ring-4 ring-tertiary/20"></div>
                  </div>
                  <div
                    class="bg-surface-container-low rounded-lg p-3 border border-outline-variant/50 ai-border"
                  >
                    <div class="flex justify-between items-start mb-1">
                      <div class="font-medium text-sm text-tertiary flex items-center gap-1">
                        <span class="material-symbols-outlined text-[14px]">auto_fix</span>
                        {{ t('自动干预 (T+5 mins)') }}
                      </div>
                    </div>
                    <ul
                      class="text-xs text-on-surface-variant space-y-1 mt-2 list-disc list-inside"
                    >
                      <li>{{ t('锁定基础房型（标准间）在 Ctrip 的可用库存 5 间。') }}</li>
                      <li>{{ t('将 Direct 渠道的基础房型价格下调 2% 以吸引溢出流量。') }}</li>
                    </ul>
                  </div>
                </div>
              </div>
              <button
                class="w-full mt-6 bg-primary text-on-primary hover:bg-primary/90 font-label-lg text-label-lg py-2.5 rounded-full transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                <span class="material-symbols-outlined text-[20px]">play_arrow</span>
                {{ t('运行完整仿真') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
