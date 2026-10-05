<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'p-4 bg-surface-bright rounded-lg border border-surface-container-highest',
    raw: '<p class="text-on-surface-variant text-sm mb-1">总曝光量</p><p class="font-num-xl text-num-xl text-on-background">142.5K</p><p class="text-xs text-tertiary mt-1 flex items-center">较上周 +12%</p>',
  },
  {
    id: 1,
    cls: 'p-4 bg-surface-bright rounded-lg border border-surface-container-highest',
    raw: '<p class="text-on-surface-variant text-sm mb-1">总互动量</p><p class="font-num-xl text-num-xl text-on-background">8,432</p><p class="text-xs text-tertiary mt-1 flex items-center">较上周 +5.2%</p>',
  },
  {
    id: 2,
    cls: 'p-4 bg-surface-bright rounded-lg border border-surface-container-highest',
    raw: '<p class="text-on-surface-variant text-sm mb-1">转化率</p><p class="font-num-xl text-num-xl text-on-background">3.8%</p><p class="text-xs text-outline mt-1 flex items-center">平稳</p>',
  },
  {
    id: 3,
    cls: 'p-4 bg-surface-bright rounded-lg border border-surface-container-highest',
    raw: '<p class="text-on-surface-variant text-sm mb-1">预估 ROI（付费）</p><p class="font-num-xl text-num-xl text-on-background">2.4x</p><p class="text-xs text-error mt-1 flex items-center">较上周 -0.1 倍</p>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('xiaohongshu')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="ads" /></div>
    <div class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="font-headline-lg text-headline-lg text-on-background">
          {{ t('小红书数据分析与原生内容表现') }}
        </h1>
        <p class="text-on-surface-variant mt-1">
          {{ t('监测原生表现、发现趋势并生成高转化内容。') }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          class="px-4 py-2 bg-surface-container-high rounded-lg text-on-surface font-label-lg flex items-center gap-2 hover:bg-surface-container transition-colors border border-outline-variant"
        >
          {{ t('导出') }}</button
        ><button
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg flex items-center gap-2 hover:bg-on-primary-fixed-variant transition-colors shadow-sm"
        >
          {{ t('查看指南') }}
        </button>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- Performance Dashboard (Spans 8 cols) -->
      <section
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <h2 class="font-headline-md text-headline-md mb-4 flex items-center gap-2">
          {{ t('原生平台内容追踪') }}
        </h2>
        <div class="grid grid-cols-4 gap-4 mb-6">
          <template v-for="(item, i) in rows" :key="i"
            ><div :class="item.cls" v-html="item.raw"></div
          ></template>
        </div>
        <div
          class="h-64 bg-surface-container-low rounded-lg flex items-center justify-center border border-outline-variant border-dashed"
        >
          <!-- Chart Placeholder -->
          <p class="text-on-surface-variant font-mono text-sm">
            {{ t('互动量趋势图（自然 vs 付费）') }}
          </p>
        </div>
      </section>
      <!-- Hot Topic Trends (Spans 4 cols) -->
      <section
        class="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm ai-tinge"
      >
        <div class="flex justify-between items-start mb-4">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2">
            {{ t('热门话题关键词') }}
          </h2>
          <span
            class="bg-tertiary-fixed text-on-tertiary-fixed text-xs px-2 py-1 rounded font-mono"
            >{{ t('AI 洞察') }}</span
          >
        </div>
        <ul class="space-y-4">
          <li
            class="p-3 bg-surface-bright rounded-lg border border-surface-container-highest hover:bg-surface-container transition-colors cursor-pointer"
          >
            <div class="flex justify-between items-center mb-1">
              <span class="font-label-lg font-bold text-on-background">{{ t('#周末微度假') }}</span
              ><span class="text-xs text-tertiary bg-tertiary-fixed-dim/30 px-1.5 py-0.5 rounded">{{
                t('上升')
              }}</span>
            </div>
            <p class="text-sm text-on-surface-variant">
              {{ t('上海周边宠物友好型精品住宿互动量高。') }}
            </p>
          </li>
          <li
            class="p-3 bg-surface-bright rounded-lg border border-surface-container-highest hover:bg-surface-container transition-colors cursor-pointer"
          >
            <div class="flex justify-between items-center mb-1">
              <span class="font-label-lg font-bold text-on-background">{{ t('#治愈系民宿') }}</span
              ><span
                class="text-xs text-on-secondary-container bg-secondary-container px-1.5 py-0.5 rounded"
                >{{ t('稳定') }}</span
              >
            </div>
            <p class="text-sm text-on-surface-variant">
              {{ t('对极简设计与自然景观的关注持续。') }}
            </p>
          </li>
          <li
            class="p-3 bg-surface-bright rounded-lg border border-surface-container-highest hover:bg-surface-container transition-colors cursor-pointer"
          >
            <div class="flex justify-between items-center mb-1">
              <span class="font-label-lg font-bold text-on-background">{{ t('#打工人周末') }}</span
              ><span class="text-xs text-error bg-error-container/50 px-1.5 py-0.5 rounded">{{
                t('减弱')
              }}</span>
            </div>
            <p class="text-sm text-on-surface-variant">
              {{ t('声量下降，正向特定活动类标签转移。') }}
            </p>
          </li>
        </ul>
      </section>
      <!-- AI Workspace: Ideation (Spans 6 cols) -->
      <section
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm ai-tinge flex flex-col"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2">
            {{ t('AI 拍摄与内容建议') }}
          </h2>
          <button
            class="text-tertiary hover:bg-tertiary-fixed p-1 rounded transition-colors"
          ></button>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-on-surface mb-1">{{
            t('目标关键词 / 氛围')
          }}</label>
          <div class="flex gap-2">
            <input
              class="flex-1 rounded-md border-outline-variant shadow-sm focus:border-primary focus:ring focus:ring-primary/50 text-sm"
              type="text"
              value="Pet-friendly, Cozy, Autumn"
            /><button
              class="bg-surface-container-high text-on-surface px-3 py-2 rounded-md hover:bg-surface-container transition-colors border border-outline-variant text-sm font-label-lg"
            >
              {{ t('生成') }}
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto pr-2 space-y-4">
          <!-- Idea Card 1 -->
          <div
            class="p-4 bg-surface-bright border border-outline-variant rounded-lg relative overflow-hidden"
          >
            <div class="absolute top-0 right-0 p-2">
              <button
                class="text-primary hover:text-primary-container text-xs flex items-center gap-1 font-label-lg bg-surface-container px-2 py-1 rounded"
              >
                {{ t('复制脚本') }}
              </button>
            </div>
            <h3 class="font-label-lg font-bold text-on-background mb-2">{{ t('文案与脚本 :') }}</h3>
            <p
              class="text-sm text-on-surface-variant bg-surface p-2 rounded border border-surface-container-highest mb-3"
            >
              {{ t('秋日避世指南🍂 带毛孩子逃离城市计划！') }}
            </p>
            <h3 class="font-label-lg font-bold text-on-background mb-2 text-xs">
              {{ t('拍摄建议 :') }}
            </h3>
            <p
              class="text-xs text-on-surface-variant bg-surface p-2 rounded border border-surface-container-highest mb-3"
            >
              {{
                t(
                  '聚焦温暖、黄金时段的光线。捕捉宠物与风景环境的互动。用平视角度拍摄宠物以营造亲密感。',
                )
              }}
            </p>
            <h3 class="font-label-lg font-bold text-on-background mb-2 text-xs">
              {{ t('封面图概念：') }}
            </h3>
            <div class="flex gap-3">
              <div
                class="w-16 h-16 rounded bg-surface-container-high flex-shrink-0 flex items-center justify-center border border-outline-variant"
              ></div>
              <p class="text-xs text-on-surface-variant flex-1">
                {{
                  t(
                    '一只金毛寻回犬望向大窗外的秋叶，前景现代扶手椅上搭着温暖格纹毯。金色时段的温暖光线的。',
                  )
                }}
              </p>
            </div>
          </div>
        </div>
      </section>
      <!-- Comment Sentiment Analysis (Spans 6 cols) -->
      <section
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col"
      >
        <h2 class="font-headline-md text-headline-md mb-4 flex items-center gap-2">
          {{ t('评论情感分析') }}
        </h2>
        <div class="flex gap-4 mb-6">
          <div
            class="flex-1 bg-surface-bright p-3 rounded-lg border border-surface-container-highest flex items-center gap-3"
          >
            <div
              class="w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold"
            >
              75%
            </div>
            <div>
              <p class="font-label-lg">{{ t('正面') }}</p>
              <p class="text-xs text-on-surface-variant">{{ t('“喜欢这景色”、“干净”') }}</p>
            </div>
          </div>
          <div
            class="flex-1 bg-surface-bright p-3 rounded-lg border border-surface-container-highest flex items-center gap-3"
          >
            <div
              class="w-10 h-10 rounded-full bg-surface-container text-on-surface flex items-center justify-center font-bold"
            >
              15%
            </div>
            <div>
              <p class="font-label-lg">{{ t('中性') }}</p>
              <p class="text-xs text-on-surface-variant">{{ t('“这是哪？”、“价格？”') }}</p>
            </div>
          </div>
          <div
            class="flex-1 bg-surface-bright p-3 rounded-lg border border-surface-container-highest flex items-center gap-3"
          >
            <div
              class="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center font-bold"
            >
              10%
            </div>
            <div>
              <p class="font-label-lg">{{ t('负面') }}</p>
              <p class="text-xs text-on-surface-variant">{{ t('“停车难找”') }}</p>
            </div>
          </div>
        </div>
        <h3 class="font-label-lg mb-2 text-on-surface">{{ t('近期关键评论') }}</h3>
        <div class="space-y-3 flex-1 overflow-y-auto pr-2">
          <div
            class="p-3 bg-surface-bright rounded border border-surface-container-highest flex gap-3"
          >
            <div>
              <p class="text-sm text-on-background">
                {{ t('“阳台外的日落景色绝了，下个季节一定再来！”') }}
              </p>
              <p class="text-xs text-outline mt-1">{{ t('来自笔记：周末逃离 • 2小时前') }}</p>
            </div>
          </div>
          <div
            class="p-3 bg-surface-bright rounded border border-surface-container-highest flex gap-3"
          >
            <div>
              <p class="text-sm text-on-background">
                {{ t('“地方很美，但 Wi-Fi 很不稳定，很难远程办公。”') }}
              </p>
              <p class="text-xs text-outline mt-1">{{ t('来自笔记：远程办公目标 • 5小时前') }}</p>
            </div>
          </div>
        </div>
      </section>
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
