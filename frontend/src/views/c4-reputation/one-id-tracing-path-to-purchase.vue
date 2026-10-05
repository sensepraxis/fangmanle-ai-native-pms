<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 订单归因与价值分析页：忠实移植自 one-id-tracing-path-to-purchase.html 内容区
// 列表用 v-for；无数据时用 api.demo('one-id-tracing') 兜底，缺失回退原型示例。

const hotelId = 1
const meta = ref<any>({
  title: t('订单归因与价值分析'),
  subtitle: t('AI 驱动的洞察：预订路径、客人终身价值与取消风险。'),
})

// 一号通追溯：购买路径（主列表，受 api.demo 覆盖）
const steps = ref<any[]>([
  {
    label: 'XiaoHongShu',
    sub: '发现（10月12日）',
    dot: 'bg-primary text-on-primary',
    dim: false,
    tip: '',
  },
  {
    label: t('微信搜索'),
    sub: '考虑中（10月14日）',
    dot: 'bg-primary text-on-primary',
    dim: false,
    tip: '',
  },
  {
    label: t('直连小程序'),
    sub: '预订（10月15日）',
    dot: 'bg-primary text-on-primary',
    dim: false,
    tip: 'AI 洞察：60% 回访概率。',
  },
  {
    label: t('入住'),
    sub: '预计（10月20日）',
    dot: 'bg-surface-container-highest text-on-surface-variant border border-outline-variant',
    dim: true,
    tip: '',
  },
])

onMounted(async () => {
  try {
    const r: any = await api.demo('one-id-tracing')
    if (Array.isArray(r) && r.length) steps.value = r
  } catch (e) {
    /* 兜底：保留原型示例购买路径 */
  }
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <header class="mb-8">
        <h1 class="text-display-lg font-display-lg text-on-background">{{ meta.title }}</h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-2">{{ meta.subtitle }}</p>
      </header>

      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- 一号通追溯：购买路径 -->
        <div
          class="col-span-1 md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 relative overflow-hidden"
        >
          <div class="flex justify-between items-start mb-6">
            <div>
              <h2 class="text-headline-md font-headline-md flex items-center gap-2">
                {{ t('一号通追溯：购买路径') }}
              </h2>
              <p class="text-body-md font-body-md text-on-surface-variant mt-1">
                {{ t('近期直订转化路径。') }}
              </p>
            </div>
            <span
              class="bg-tertiary-fixed text-on-tertiary-fixed px-3 py-1 rounded-full text-label-lg font-label-lg flex items-center gap-1"
              >{{ t('AI 已匹配') }}</span
            >
          </div>
          <!-- 步骤条 -->
          <div class="relative mt-8 px-4">
            <div
              class="absolute top-1/2 left-8 right-8 h-0.5 bg-secondary-fixed-dim -translate-y-1/2 z-0"
            ></div>
            <div class="absolute top-1/2 left-8 w-2/3 h-0.5 bg-primary -translate-y-1/2 z-0"></div>
            <div class="flex justify-between relative z-10">
              <div
                v-for="(s, i) in steps"
                :key="s.label"
                class="flex flex-col items-center group cursor-pointer"
                :class="{ 'opacity-50': s.dim }"
              >
                <div
                  class="w-10 h-10 rounded-full flex items-center justify-center shadow-sm"
                  :class="s.dot"
                ></div>
                <span class="text-label-lg font-label-lg mt-2 font-bold text-on-background">{{
                  s.label
                }}</span>
                <span class="text-[12px] text-on-surface-variant">{{ s.sub }}</span>
                <div
                  v-if="s.tip"
                  class="absolute -top-16 left-1/2 -translate-x-1/2 bg-surface-container-highest text-on-surface border border-outline-variant p-2 rounded-lg text-label-lg font-label-lg whitespace-nowrap shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                >
                  <span class="text-tertiary font-bold">{{ t('AI 洞察：') }}</span
                  >{{ s.tip }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 客人 LTV 预测 -->
        <div
          class="col-span-1 md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 ai-tinge flex flex-col"
        >
          <h2 class="text-headline-md font-headline-md flex items-center gap-2 mb-2">
            {{ t('客人 LTV 预测') }}
          </h2>
          <p class="text-body-md font-body-md text-on-surface-variant mb-6 flex-1">
            {{ t('基于人口特征与历史行为数据的 AI 评分。') }}
          </p>
          <div class="flex items-end gap-2 mb-4">
            <span class="text-display-lg font-display-lg text-primary">¥12,500</span>
            <span class="text-body-md font-body-md text-on-surface-variant mb-1">{{
              t('预测 LTV')
            }}</span>
          </div>
          <div class="w-full bg-secondary-fixed-dim rounded-full h-2.5 mb-2">
            <div class="bg-tertiary h-2.5 rounded-full" style="width: 85%"></div>
          </div>
          <div class="flex justify-between text-label-lg font-label-lg text-on-surface-variant">
            <span>{{ t('新客') }}</span>
            <span class="text-tertiary font-bold">{{ t('高价值倾向') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.ai-tinge {
  box-shadow: -2px 0 0 0 #8c33b3;
}
</style>
