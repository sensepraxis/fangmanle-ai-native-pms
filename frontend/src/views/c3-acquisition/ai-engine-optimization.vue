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
    cls: 'absolute left-[50%] top-4 bottom-4 w-px bg-outline-variant -z-10 hidden sm:block',
    raw: '',
  },
  {
    id: 1,
    cls: 'w-full bg-surface-container-low rounded-lg p-3 flex items-center justify-between border border-outline-variant/50 relative z-10 transition-transform hover:scale-[1.02]',
    raw: '\n<div class="flex items-center gap-3 w-1/3">\n<div class="bg-primary-fixed text-on-primary-fixed w-8 h-8 rounded-full flex items-center justify-center">\n<span class="material-symbols-outlined text-[18px]">visibility</span>\n</div>\n<span class="font-label-lg text-label-lg text-on-surface">曝光量</span>\n</div>\n<div class="font-num-xl text-num-xl text-on-surface w-1/3 text-center">124,500</div>\n<div class="w-1/3 text-right text-on-surface-variant font-body-md text-sm">AI 搜索与地图</div>\n',
  },
  {
    id: 2,
    cls: 'w-[90%] mx-auto bg-surface-container-low rounded-lg p-3 flex items-center justify-between border border-outline-variant/50 relative z-10 transition-transform hover:scale-[1.02]',
    raw: '\n<div class="flex items-center gap-3 w-1/3">\n<div class="bg-primary-fixed text-on-primary-fixed w-8 h-8 rounded-full flex items-center justify-center">\n<span class="material-symbols-outlined text-[18px]">touch_app</span>\n</div>\n<span class="font-label-lg text-label-lg text-on-surface">点击数</span>\n</div>\n<div class="font-num-xl text-num-xl text-on-surface w-1/3 text-center">8,230</div>\n<div class="w-1/3 text-right text-primary font-body-md text-sm font-medium">6.6% 点击率</div>\n',
  },
  {
    id: 3,
    cls: 'w-[80%] mx-auto bg-surface-container-low rounded-lg p-3 flex items-center justify-between border border-outline-variant/50 relative z-10 transition-transform hover:scale-[1.02]',
    raw: '\n<div class="flex items-center gap-3 w-1/3">\n<div class="bg-tertiary-fixed text-on-tertiary-fixed w-8 h-8 rounded-full flex items-center justify-center">\n<span class="material-symbols-outlined text-[18px]">book_online</span>\n</div>\n<span class="font-label-lg text-label-lg text-on-surface">预订量</span>\n</div>\n<div class="font-num-xl text-num-xl text-on-surface w-1/3 text-center">412</div>\n<div class="w-1/3 text-right text-tertiary font-body-md text-sm font-medium">5.0% 转化率</div>\n',
  },
  {
    id: 4,
    cls: 'w-[70%] mx-auto bg-primary text-on-primary rounded-lg p-3 flex items-center justify-between shadow-md relative z-10 transition-transform hover:scale-[1.02]',
    raw: '\n<div class="flex items-center gap-3 w-1/3">\n<div class="bg-on-primary text-primary w-8 h-8 rounded-full flex items-center justify-center shadow-sm">\n<span class="material-symbols-outlined text-[18px]">payments</span>\n</div>\n<span class="font-label-lg text-label-lg">成交总额</span>\n</div>\n<div class="font-num-xl text-num-xl w-2/3 text-right">¥ 185,400</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('ai-engine')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="geo" /></div>
    <!-- Page Header -->
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="font-headline-lg text-headline-lg text-on-surface mb-1 flex items-center gap-2">
          <span
            class="material-symbols-outlined text-tertiary-container"
            data-weight="fill"
            style="font-variation-settings: 'FILL' 1"
            >travel_explore</span
          >
          {{ t('GEO（AI 引擎优化）') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('统一管理酒店在 AI 搜索引擎与地图平台上的可见度、品牌认知与流量分发。') }}
        </p>
      </div>
      <button
        class="bg-primary text-on-primary font-label-lg text-label-lg px-4 py-2 rounded-full flex items-center gap-2 hover:bg-primary-container transition-colors shadow-sm"
      >
        <span class="material-symbols-outlined text-[18px]">sync</span>
        {{ t('立即同步数据') }}
      </button>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
      <!-- GEO Health Check (Spans 4) -->
      <div
        class="md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] flex flex-col relative overflow-hidden"
      >
        <!-- AI Tinge -->
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary-container opacity-80"></div>
        <h2 class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2">
          <span class="material-symbols-outlined text-on-surface-variant">health_and_safety</span>
          {{ t('GEO 健康检查') }}
        </h2>
        <div class="space-y-4 flex-1">
          <!-- Status Item 1 -->
          <div
            class="flex items-start justify-between p-3 bg-surface-container-low rounded-lg border border-transparent hover:border-outline-variant transition-colors"
          >
            <div class="flex items-center gap-3">
              <span
                class="material-symbols-outlined text-primary"
                data-weight="fill"
                style="font-variation-settings: 'FILL' 1"
                >check_circle</span
              >
              <div>
                <h3 class="font-label-lg text-label-lg text-on-surface">
                  {{ t('schema.org 酒店结构化数据') }}
                </h3>
                <p class="font-body-md text-[13px] text-on-surface-variant leading-tight mt-0.5">
                  {{ t('结构化数据字段已完全对齐。') }}
                </p>
              </div>
            </div>
            <span class="font-num-md text-num-md text-primary">100%</span>
          </div>
          <!-- Status Item 2 -->
          <div
            class="flex items-start justify-between p-3 bg-surface-container-low rounded-lg border border-transparent hover:border-outline-variant transition-colors"
          >
            <div class="flex items-center gap-3">
              <span
                class="material-symbols-outlined text-on-error-container"
                data-weight="fill"
                style="font-variation-settings: 'FILL' 1"
                >warning</span
              >
              <div>
                <h3 class="font-label-lg text-label-lg text-on-surface">
                  {{ t('NAP 信息一致性') }}
                </h3>
                <p class="font-body-md text-[13px] text-on-surface-variant leading-tight mt-0.5">
                  {{ t('高德地图上的地址与名称不一致。') }}
                </p>
              </div>
            </div>
            <button
              class="text-tertiary-container hover:text-tertiary font-label-lg text-label-lg underline decoration-1 underline-offset-2"
            >
              {{ t('立即修复') }}
            </button>
          </div>
          <!-- Status Item 3 -->
          <div
            class="flex items-start justify-between p-3 bg-surface-container-low rounded-lg border border-transparent hover:border-outline-variant transition-colors"
          >
            <div class="flex items-center gap-3">
              <span
                class="material-symbols-outlined text-primary"
                data-weight="fill"
                style="font-variation-settings: 'FILL' 1"
                >check_circle</span
              >
              <div>
                <h3 class="font-label-lg text-label-lg text-on-surface">
                  {{ t('llms.txt 大模型就绪度') }}
                </h3>
                <p class="font-body-md text-[13px] text-on-surface-variant leading-tight mt-0.5">
                  {{ t('面向 LLM 爬虫的内容已优化。') }}
                </p>
              </div>
            </div>
            <span
              class="font-label-lg text-label-lg text-primary bg-primary-fixed text-on-primary-fixed px-2 py-0.5 rounded-full text-[12px]"
              >V1.2</span
            >
          </div>
        </div>
      </div>
      <!-- Distribution Status (Spans 8) -->
      <div
        class="md:col-span-8 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)]"
      >
        <h2 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-on-surface-variant">share</span>
          {{ t('分发状态总览') }}
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <!-- Provider: Google Maps -->
          <div
            class="flex flex-col items-center justify-center p-4 bg-surface rounded-xl border border-outline-variant text-center"
          >
            <span class="material-symbols-outlined text-[32px] text-primary mb-2">map</span>
            <h3 class="font-label-lg text-label-lg text-on-surface">{{ t('Google 地图') }}</h3>
            <p class="font-body-md text-[13px] text-on-surface-variant mt-1">
              {{ t('2 小时前已同步') }}
            </p>
            <div class="mt-3 w-full bg-surface-container-highest rounded-full h-1.5">
              <div class="bg-primary h-1.5 rounded-full" style="width: 100%"></div>
            </div>
          </div>
          <!-- Provider: Amap -->
          <div
            class="flex flex-col items-center justify-center p-4 bg-error-container/20 rounded-xl border border-error-container text-center relative"
          >
            <span class="absolute top-2 right-2 flex h-3 w-3">
              <span
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75"
              ></span>
              <span class="relative inline-flex rounded-full h-3 w-3 bg-error"></span>
            </span>
            <span class="material-symbols-outlined text-[32px] text-on-surface-variant mb-2"
              >navigation</span
            >
            <h3 class="font-label-lg text-label-lg text-on-surface">{{ t('高德地图') }}</h3>
            <p class="font-body-md text-[13px] text-error mt-1">{{ t('NAP 信息不一致') }}</p>
            <div class="mt-3 w-full bg-surface-container-highest rounded-full h-1.5">
              <div class="bg-error h-1.5 rounded-full" style="width: 85%"></div>
            </div>
          </div>
          <!-- Provider: Baidu Maps -->
          <div
            class="flex flex-col items-center justify-center p-4 bg-surface rounded-xl border border-outline-variant text-center"
          >
            <span class="material-symbols-outlined text-[32px] text-primary mb-2">location_on</span>
            <h3 class="font-label-lg text-label-lg text-on-surface">{{ t('百度地图') }}</h3>
            <p class="font-body-md text-[13px] text-on-surface-variant mt-1">
              {{ t('5 小时前已同步') }}
            </p>
            <div class="mt-3 w-full bg-surface-container-highest rounded-full h-1.5">
              <div class="bg-primary h-1.5 rounded-full" style="width: 100%"></div>
            </div>
          </div>
          <!-- Provider: AI Endpoints -->
          <div
            class="flex flex-col items-center justify-center p-4 bg-tertiary-fixed/30 rounded-xl border border-tertiary-fixed-dim text-center"
          >
            <span class="material-symbols-outlined text-[32px] text-tertiary-container mb-2"
              >smart_toy</span
            >
            <h3 class="font-label-lg text-label-lg text-on-surface">{{ t('AI 搜索接口') }}</h3>
            <p class="font-body-md text-[13px] text-on-surface-variant mt-1">
              {{ t('实时推送中') }}
            </p>
            <div class="mt-3 w-full bg-surface-container-highest rounded-full h-1.5">
              <div class="bg-tertiary-container h-1.5 rounded-full" style="width: 100%"></div>
            </div>
          </div>
        </div>
      </div>
      <!-- Content Optimization A/B Testing (Spans 6) -->
      <div
        class="md:col-span-6 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)]"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-tertiary-container">science</span>
            {{ t('内容 A/B 测试') }}
          </h2>
          <span
            class="bg-surface-container-high text-on-surface-variant px-3 py-1 rounded-full font-label-lg text-label-lg text-[12px]"
            >{{ t('运行中（近 7 天）') }}</span
          >
        </div>
        <div class="space-y-4">
          <!-- Variant A -->
          <div class="p-4 rounded-lg border-2 border-outline-variant bg-surface relative">
            <div
              class="absolute -top-3 left-4 bg-surface-container-lowest px-2 font-label-lg text-label-lg text-on-surface-variant"
            >
              {{ t('版本 A（对照组）') }}
            </div>
            <p class="font-body-md text-body-md text-on-surface mt-2 mb-3">
              {{ t('"市中心现代精品酒店，邻近地铁站；免费 Wi-Fi 与自助早餐。"') }}
            </p>
            <div class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-1 text-on-surface-variant">
                <span class="material-symbols-outlined text-[16px]">visibility</span>
                <span class="font-num-md">{{ t('4,201 次曝光') }}</span>
              </div>
              <div class="flex items-center gap-1 text-on-surface-variant">
                <span class="material-symbols-outlined text-[16px]">touch_app</span>
                <span class="font-num-md">{{ t('312 次点击（7.4%）') }}</span>
              </div>
            </div>
          </div>
          <!-- Variant B (Winning) -->
          <div
            class="p-4 rounded-lg border-2 border-tertiary-container bg-tertiary-fixed/10 relative"
          >
            <div
              class="absolute -top-3 left-4 bg-surface-container-lowest px-2 font-label-lg text-label-lg text-tertiary-container font-bold flex items-center gap-1"
            >
              <span class="material-symbols-outlined text-[16px]">emoji_events</span>
              {{ t('版本 B（AI 推荐）') }}
            </div>
            <p class="font-body-md text-body-md text-on-surface mt-2 mb-3">
              {{ t('"市中心宠物友好精品酒店，步行 2 分钟即到地铁；配备智能客房与 AI 自助入住。"') }}
            </p>
            <div class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-1 text-on-surface-variant">
                <span class="material-symbols-outlined text-[16px]">visibility</span>
                <span class="font-num-md">{{ t('4,188 次曝光') }}</span>
              </div>
              <div class="flex items-center gap-1 text-primary">
                <span class="material-symbols-outlined text-[16px]">touch_app</span>
                <span class="font-num-md font-bold">{{ t('489 次点击（11.6%）') }}</span>
                <span
                  class="ml-2 bg-primary-container text-on-primary-container px-1.5 rounded text-[10px]"
                  >{{ t('+56% 提升') }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Performance Metrics Funnel (Spans 6) -->
      <div
        class="md:col-span-6 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] flex flex-col"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">filter_alt</span>
            {{ t('AI 发现漏斗') }}
          </h2>
          <select
            class="bg-surface-container-low border-none text-on-surface text-sm rounded-md font-label-lg py-1 pl-3 pr-8 focus:ring-1 focus:ring-primary-container cursor-pointer"
          >
            <option>{{ t('近 30 天') }}</option>
            <option>{{ t('近 7 天') }}</option>
          </select>
        </div>
        <div class="flex-1 flex flex-col justify-center space-y-2 relative">
          <template v-for="(item, i) in rows" :key="i"
            ><div :class="item.cls" v-html="item.raw"></div
          ></template>
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
