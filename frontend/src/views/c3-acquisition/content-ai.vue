<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'
import AcquisitionLoopPanel from '../../components/AcquisitionLoopPanel.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'w-full max-w-md bg-surface border border-outline-variant rounded-xl p-4 flex items-center justify-between relative z-10 hover:shadow-md transition-shadow',
    raw: '<div class="flex items-center gap-4"><div class="w-12 h-12 rounded-full bg-primary-container text-primary flex items-center justify-center"></div><div><div class="font-label-lg text-label-lg text-on-surface-variant">私信互动</div><div class="font-num-xl text-num-xl text-on-surface mt-1">1,245</div></div></div><div class="text-right"><div class="text-xs text-primary font-medium bg-primary-fixed px-2 py-1 rounded-full">+12% vs 上月</div></div>',
  },
  {
    id: 1,
    cls: 'h-6 w-px bg-outline-variant relative',
    raw: '<div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-surface-container-highest rounded-full px-2 py-0.5 text-[10px] text-on-surface-variant">45% 转化率</div>',
  },
  {
    id: 2,
    cls: 'w-full max-w-[400px] bg-surface border border-outline-variant rounded-xl p-4 flex items-center justify-between relative z-10 hover:shadow-md transition-shadow',
    raw: '<div class="flex items-center gap-4"><div class="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center"></div><div><div class="font-label-lg text-label-lg text-on-surface-variant">点击预订链接</div><div class="font-num-xl text-num-xl text-on-surface mt-1">560</div></div></div>',
  },
  {
    id: 3,
    cls: 'h-6 w-px bg-outline-variant relative',
    raw: '<div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-surface-container-highest rounded-full px-2 py-0.5 text-[10px] text-on-surface-variant">15% 转化率</div>',
  },
  {
    id: 4,
    cls: 'w-full max-w-[350px] bg-surface border-2 border-primary rounded-xl p-4 flex items-center justify-between relative z-10 hover:shadow-md transition-shadow',
    raw: '\n<!-- Sparkle highlight for final conversion -->\n<div class="absolute -top-2 -right-2 w-4 h-4 bg-tertiary rounded-full animate-ping opacity-75"></div><div class="absolute -top-2 -right-2 w-4 h-4 bg-tertiary rounded-full"></div><div class="flex items-center gap-4"><div class="w-10 h-10 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center"></div><div><div class="font-label-lg text-label-lg text-on-surface-variant">完成预订</div><div class="font-num-xl text-num-xl text-on-surface mt-1">84</div></div></div><div class="text-right"><div class="text-xs text-tertiary font-medium bg-tertiary-fixed px-2 py-1 rounded-full">￥124k 收入</div></div>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.listCampaigns(hotelId)
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="main" /></div>
    <AcquisitionLoopPanel focus="funnel" />
    <div class="max-w-[1440px] mx-auto h-full flex flex-col gap-6">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-2">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background mb-1">
            {{ t('小红书私域转化漏斗') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant flex items-center gap-2">
            {{ t('监控从私信到预订链接到最终转化的全链路') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 bg-surface-container-low text-on-surface border border-outline-variant rounded-lg font-label-lg text-label-lg hover:bg-surface-container transition-colors flex items-center gap-2"
          >
            {{ t('导出报告') }}</button
          ><button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg shadow-sm hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            {{ t('新建广告系列追踪') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-12 gap-gutter flex-1">
        <!-- Left Column: Funnel & AI Efficiency (8 cols) -->
        <div class="col-span-12 lg:col-span-8 flex flex-col gap-gutter">
          <!-- The Funnel Visualizer (Glassmorphism/Premium Card) -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex-1 min-h-[400px] flex flex-col relative overflow-hidden"
          >
            <!-- Subtle AI Background Glow -->
            <div
              class="absolute top-0 right-0 w-64 h-64 bg-primary-fixed-dim opacity-10 rounded-full blur-3xl pointer-events-none"
            ></div>
            <h2
              class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2"
            >
              {{ t('转化路径分析 (近30天)') }}
            </h2>
            <div class="flex-1 flex flex-col justify-center items-center gap-4 relative">
              <template v-for="(item, i) in rows" :key="i"
                ><div :class="item.cls" v-html="item.raw"></div
              ></template>
            </div>
          </div>
          <!-- AI Auto-reply Efficiency Dashboard (2 Columns within) -->
          <div class="grid grid-cols-2 gap-gutter h-48">
            <!-- Card 1: Response Time -->
            <div
              class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-5 flex flex-col justify-between border-l-4 border-l-primary"
            >
              <div class="flex items-center justify-between">
                <span class="font-label-lg text-label-lg text-on-surface-variant">{{
                  t('AI 自动回复平均耗时')
                }}</span>
              </div>
              <div>
                <div class="font-num-xl text-[32px] leading-tight font-bold text-on-surface">
                  1.2s
                </div>
                <p class="text-xs text-on-surface-variant mt-1 flex items-center gap-1">
                  <span class="text-green-600">{{ t('快于人工 98%') }}</span>
                </p>
              </div>
              <!-- Micro Chart Placeholder -->
              <div class="w-full h-8 mt-2 flex items-end gap-1 opacity-60">
                <div class="w-1/6 h-full bg-surface-variant rounded-t-sm"></div>
                <div class="w-1/6 h-4/5 bg-surface-variant rounded-t-sm"></div>
                <div class="w-1/6 h-3/5 bg-surface-variant rounded-t-sm"></div>
                <div class="w-1/6 h-2/5 bg-primary-fixed rounded-t-sm"></div>
                <div class="w-1/6 h-1/5 bg-primary-fixed rounded-t-sm"></div>
                <div class="w-1/6 h-[10%] bg-primary rounded-t-sm"></div>
              </div>
            </div>
            <!-- Card 2: AI Resolution Rate -->
            <div
              class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-5 flex flex-col justify-between relative overflow-hidden"
            >
              <!-- AI Tinge -->
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary opacity-80"></div>
              <div class="flex items-center justify-between">
                <span
                  class="font-label-lg text-label-lg text-on-surface-variant flex items-center gap-1"
                  >{{ t('AI 独立解决率') }}</span
                >
              </div>
              <div>
                <div class="font-num-xl text-[32px] leading-tight font-bold text-on-surface">
                  76%
                </div>
                <p class="text-xs text-on-surface-variant mt-1">
                  {{ t('无需人工介入的对话占比') }}
                </p>
              </div>
              <div class="w-full bg-surface-variant h-2 rounded-full mt-4 overflow-hidden">
                <div class="bg-tertiary h-full rounded-full" style="width: 76%"></div>
              </div>
            </div>
          </div>
        </div>
        <!-- Right Column: High Intent Leads (4 cols) -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col overflow-hidden"
        >
          <div
            class="p-5 border-b border-outline-variant bg-surface-bright flex justify-between items-center"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <!-- Changed from specific target icon to generic for standard icon set, assuming target exists -->
              {{ t('高意向潜在客源') }}
            </h2>
            <span
              class="bg-error-container text-on-error-container text-[10px] px-2 py-1 rounded-full font-bold animate-pulse"
              >{{ t('12 新线索') }}</span
            >
          </div>
          <!-- Guardrail Banner R1 (Low Risk - Review Suggested) -->
          <div
            class="mx-4 mt-4 bg-surface-container-low border border-yellow-400/50 rounded-lg p-3 flex gap-3 items-start"
          >
            <div>
              <h4 class="font-label-lg text-label-lg text-on-surface">
                {{ t('AI 提示：建议复核') }}
              </h4>
              <p class="text-xs text-on-surface-variant mt-1">
                {{ t('有 3 位高价值客户在询问周末特价，建议提供专属优惠码促单。') }}
              </p>
            </div>
          </div>
          <!-- Leads List -->
          <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            <!-- Lead Item 1 -->
            <div
              class="p-3 border border-outline-variant rounded-lg bg-surface hover:bg-surface-container-low transition-colors cursor-pointer group"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-xs"
                  >
                    @M
                  </div>
                  <div>
                    <div class="font-label-lg text-sm text-on-surface font-medium">
                      @Momo_Travel
                    </div>
                    <div class="text-[10px] text-on-surface-variant">
                      {{ t('5 分钟前 • 询问价格') }}
                    </div>
                  </div>
                </div>
                <span
                  class="text-[10px] font-bold text-error bg-error-container px-2 py-0.5 rounded"
                  >{{ t('热门') }}</span
                >
              </div>
              <p
                class="text-xs text-on-surface-variant line-clamp-2 bg-surface-container-lowest p-2 rounded border border-surface-dim"
              >
                {{ t('\"你好，请问下个月中旬带狗入住有空房吗？看到你们小红书的笔记觉得很棒。\"') }}
              </p>
              <div
                class="mt-2 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <button
                  class="text-[10px] px-2 py-1 bg-primary text-on-primary rounded hover:opacity-90"
                >
                  {{ t('发送预订链接') }}
                </button>
              </div>
            </div>
            <!-- Lead Item 2 -->
            <div
              class="p-3 border border-outline-variant rounded-lg bg-surface hover:bg-surface-container-low transition-colors cursor-pointer group"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-xs"
                  >
                    @L
                  </div>
                  <div>
                    <div class="font-label-lg text-sm text-on-surface font-medium">
                      {{ t('@LiLi_周末游') }}
                    </div>
                    <div class="text-[10px] text-on-surface-variant">
                      {{ t('1 小时前 • 设施咨询') }}
                    </div>
                  </div>
                </div>
                <span
                  class="text-[10px] font-bold text-orange-600 bg-orange-100 px-2 py-0.5 rounded"
                  >{{ t('温热') }}</span
                >
              </div>
              <p
                class="text-xs text-on-surface-variant line-clamp-2 bg-surface-container-lowest p-2 rounded border border-surface-dim"
              >
                {{ t('\"房间里有咖啡机吗？早餐是送到房间还是去餐厅？\"') }}
              </p>
              <!-- AI Reasoning Tooltip context -->
              <div class="mt-2 flex items-center gap-1 text-[10px] text-tertiary">
                {{ t('AI 已自动回复详细设施列表') }}
              </div>
            </div>
            <!-- Lead Item 3 -->
            <div
              class="p-3 border border-outline-variant rounded-lg bg-surface hover:bg-surface-container-low transition-colors cursor-pointer group"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-xs"
                  >
                    @Z
                  </div>
                  <div>
                    <div class="font-label-lg text-sm text-on-surface font-medium">
                      {{ t('@摄影师Zoe') }}
                    </div>
                    <div class="text-[10px] text-on-surface-variant">
                      {{ t('3 小时前 • 商单合作意向') }}
                    </div>
                  </div>
                </div>
              </div>
              <p
                class="text-xs text-on-surface-variant line-clamp-2 bg-surface-container-lowest p-2 rounded border border-surface-dim"
              >
                {{ t('\"您好，我是商业摄影师，想了解下是否可以预订场地进行拍摄...\"') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原型自定义工具类（v-html 内联卡片的根节点由 Vue 渲染，可命中） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
  border-left: 2px solid #8c33b3;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
