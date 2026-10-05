<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'flex items-center justify-between p-2 hover:bg-surface-container-low rounded transition-colors',
    raw: '<div class="flex items-center gap-3"><div class="w-8 h-8 rounded bg-blue-100 text-blue-600 flex items-center justify-center"></div><span class="font-body-md text-body-md text-on-surface">OTA 渠道（携程）</span></div><span class="font-num-md text-num-md text-on-surface-variant">45%</span>',
  },
  {
    id: 1,
    cls: 'flex items-center justify-between p-2 hover:bg-surface-container-low rounded transition-colors',
    raw: '<div class="flex items-center gap-3"><div class="w-8 h-8 rounded bg-green-100 text-green-600 flex items-center justify-center"></div><span class="font-body-md text-body-md text-on-surface">微信小程序</span></div><span class="font-num-md text-num-md text-on-surface-variant">35%</span>',
  },
  {
    id: 2,
    cls: 'flex items-center justify-between p-2 hover:bg-surface-container-low rounded transition-colors',
    raw: '<div class="flex items-center gap-3"><div class="w-8 h-8 rounded bg-orange-100 text-orange-600 flex items-center justify-center"></div><span class="font-body-md text-body-md text-on-surface">私域流量（直订）</span></div><span class="font-num-md text-num-md text-on-surface-variant">20%</span>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('reputation')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <!-- Breadcrumb & Header -->
    <div class="mb-6 flex justify-between items-end">
      <div>
        <nav class="flex text-on-surface-variant font-label-lg text-label-lg mb-2">
          <ol class="inline-flex items-center space-x-1 md:space-x-3">
            <li class="inline-flex items-center">
              <a class="inline-flex items-center hover:text-primary transition-colors" href="#">{{
                t('客人')
              }}</a>
            </li>
            <li>
              <div class="flex items-center">
                <a class="hover:text-primary transition-colors" href="#">{{ t('资料') }}</a>
              </div>
            </li>
            <li aria-current="page">
              <div class="flex items-center">
                <span class="text-on-surface">{{ t('Ms. Lin (林女士)') }}</span>
              </div>
            </li>
          </ol>
        </nav>
        <h1 class="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          {{ t('宾客画像智能分析')
          }}<span
            class="bg-tertiary-fixed text-on-tertiary-fixed px-3 py-1 rounded-full font-label-lg text-label-lg flex items-center gap-1 border border-tertiary-fixed-dim shadow-sm"
            >{{ t('AI 已核验') }}</span
          >
        </h1>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-surface-container-low text-on-surface border border-outline-variant rounded-lg font-label-lg text-label-lg hover:bg-surface-container transition-colors flex items-center gap-2 shadow-sm"
        >
          {{ t('编辑档案') }}</button
        ><button
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2 shadow-sm"
        >
          {{ t('记录互动') }}
        </button>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter max-w-max-content-width">
      <!-- Left Column: Core Identity (4 cols) -->
      <div class="col-span-12 md:col-span-4 flex flex-col gap-gutter">
        <!-- ID Card -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 relative overflow-hidden"
        >
          <div
            class="absolute top-0 right-0 w-32 h-32 bg-primary-fixed rounded-bl-full opacity-50 -z-10"
          ></div>
          <div class="flex items-start gap-4 mb-6">
            <div
              class="w-20 h-20 rounded-full border-2 border-primary-container overflow-hidden shrink-0 shadow-sm relative"
            >
              <img
                class="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0C7HXI_gb0Ip2OGdQ47QJdoRZmxsqrfRSDFw91QlahzxwZcow9gmvvib0zKT50WkkBya8A3fSWq7ZtbauhDnbzqsmlpx_IiGk-52SyncbWPv7w8lTPWYcAf-XbA-Nps57jQF9ySq0ff07uI2nLd1vRrdj9OuPxoOk37fcqMxbHI3QNyA0i-MKgl4JYaxdJMutMMmG6KnjKgi9Rh2VAaIiSlVim47h17PfgoXdlIpV_ObOPnc6q5g"
              />
              <div
                class="absolute bottom-0 right-0 w-6 h-6 bg-green-500 rounded-full border-2 border-surface-container-lowest flex items-center justify-center"
              ></div>
            </div>
            <div>
              <h2 class="font-headline-lg text-headline-lg text-on-surface mb-1">
                {{ t('Lin 女士')
                }}<span class="text-on-surface-variant font-body-md text-body-md">{{
                  t('(林女士)')
                }}</span>
              </h2>
              <p
                class="font-num-md text-num-md text-on-surface-variant flex items-center gap-1 mb-2"
              >
                +86 138 **** 5678
              </p>
              <div class="flex gap-2">
                <span
                  class="px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded text-xs font-label-lg flex items-center gap-1"
                  >{{ t('黄金贵宾') }}</span
                >
              </div>
            </div>
          </div>
          <div class="space-y-4">
            <div>
              <p class="text-sm text-on-surface-variant font-label-lg mb-1">{{ t('即将入住') }}</p>
              <div
                class="flex items-center gap-2 p-3 bg-surface-container-low rounded-lg border border-outline-variant border-l-4 border-l-primary"
              >
                <div>
                  <p class="font-num-md text-num-md text-on-surface">
                    {{ t('2023年10月12日 - 10月15日') }}
                  </p>
                  <p class="text-sm text-on-surface-variant font-body-md">
                    {{ t('3 Nights • 客房 802 (山景 查看)') }}
                  </p>
                </div>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="p-3 bg-surface-container-low rounded-lg border border-outline-variant">
                <p class="text-xs text-on-surface-variant font-label-lg mb-1">
                  {{ t('总入住次数') }}
                </p>
                <p class="font-num-xl text-num-xl text-primary">12</p>
              </div>
              <div class="p-3 bg-surface-container-low rounded-lg border border-outline-variant">
                <p class="text-xs text-on-surface-variant font-label-lg mb-1">
                  {{ t('终身价值') }}
                </p>
                <p class="font-num-xl text-num-xl text-on-surface">¥45.2k</p>
              </div>
            </div>
          </div>
        </div>
        <!-- Data Sources -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <h3
            class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
          >
            {{ t('数据源综合') }}
          </h3>
          <div class="space-y-3">
            <template v-for="(item, i) in rows" :key="i"
              ><div :class="item.cls" v-html="item.raw"></div
            ></template>
          </div>
        </div>
      </div>
      <!-- Right Column: AI Insights & Tags (8 cols) -->
      <div class="col-span-12 md:col-span-8 flex flex-col gap-gutter">
        <!-- AI Summary Banner -->
        <div
          class="ai-glow bg-surface-container-lowest rounded-xl shadow-sm p-6 relative overflow-hidden"
        >
          <div class="flex items-start gap-4">
            <div
              class="w-10 h-10 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center shrink-0"
            ></div>
            <div>
              <h3 class="font-headline-md text-headline-md text-on-surface mb-2">
                {{ t('AI 服务策略摘要') }}
              </h3>
              <p class="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                {{ t('Lin 女士是位高价值回头客，强烈偏好')
                }}<strong class="text-on-surface">{{ t('山景') }}</strong
                >{{ t('位于') }}<strong class="text-on-surface">{{ t('低楼层') }}</strong
                >{{ t('（低于第 5 名）。她一直要求')
                }}<strong class="text-on-surface">{{ t('额外矿泉水') }}</strong
                >{{
                  t(
                    '与硬枕头。鉴于其即将到来的入住恰逢生日周末，强烈建议优先安排安静环境并准备低调的欢迎礼遇。',
                  )
                }}
              </p>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-gutter">
          <!-- Tags & Preferences -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
          >
            <h3
              class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
            >
              {{ t('已识别画像标签') }}
            </h3>
            <div class="space-y-6">
              <div>
                <p class="text-sm text-on-surface-variant font-label-lg mb-3">
                  {{ t('主要动机（85% 置信度）') }}
                </p>
                <div class="flex flex-wrap gap-2">
                  <span
                    class="px-3 py-1.5 bg-primary-container text-on-primary-container rounded-lg font-label-lg flex items-center gap-1 shadow-sm"
                    >{{ t('商务旅客') }}</span
                  ><span
                    class="px-3 py-1.5 bg-surface-variant text-on-surface-variant border border-outline-variant rounded-lg font-label-lg flex items-center gap-1"
                    >{{ t('周末休闲') }}</span
                  >
                </div>
              </div>
              <div>
                <p class="text-sm text-on-surface-variant font-label-lg mb-3">
                  {{ t('服务偏好') }}
                </p>
                <div class="flex flex-wrap gap-2">
                  <span
                    class="px-3 py-1.5 bg-surface-container-high text-on-surface border border-outline-variant rounded-lg font-label-lg flex items-center gap-1"
                    >{{ t('安静偏好') }}</span
                  ><span
                    class="px-3 py-1.5 bg-surface-container-high text-on-surface border border-outline-variant rounded-lg font-label-lg flex items-center gap-1"
                    >{{ t('额外矿泉水') }}}</span
                  ><span
                    class="px-3 py-1.5 bg-surface-container-high text-on-surface border border-outline-variant rounded-lg font-label-lg flex items-center gap-1"
                    >{{ t('山景') }}</span
                  ><span
                    class="px-3 py-1.5 bg-surface-container-high text-on-surface border border-outline-variant rounded-lg font-label-lg flex items-center gap-1"
                    >{{ t('硬枕头') }}</span
                  >
                </div>
              </div>
              <div>
                <p class="text-sm text-on-surface-variant font-label-lg mb-3">
                  {{ t('特殊触发') }}
                </p>
                <span
                  class="px-3 py-1.5 bg-error-container text-on-error-container rounded-lg font-label-lg flex items-center gap-1 w-fit shadow-sm border border-red-200"
                  >{{ t('生日到访临近') }}</span
                >
              </div>
            </div>
          </div>
          <!-- Emotional History & Probability -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex flex-col"
          >
            <h3
              class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
            >
              {{ t('情感与概率') }}
            </h3>
            <!-- Emotion History -->
            <div class="mb-6">
              <p class="text-sm text-on-surface-variant font-label-lg mb-3">{{ t('历史情感') }}</p>
              <div class="flex items-center gap-4">
                <div
                  class="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center border-4 border-green-100 shrink-0"
                ></div>
                <div>
                  <p class="font-headline-md text-headline-md text-green-700 mb-1">
                    {{ t('正面 / 感激') }}
                  </p>
                  <p class="font-body-md text-body-md text-on-surface-variant">
                    {{ t('基于 8 条历史评论与微信互动。') }}
                  </p>
                </div>
              </div>
            </div>
            <!-- Probability Scores -->
            <div class="mt-auto">
              <p class="text-sm text-on-surface-variant font-label-lg mb-3">
                {{ t('偏好概率评分') }}
              </p>
              <div class="space-y-4">
                <div>
                  <div class="flex justify-between font-label-lg text-label-lg mb-1">
                    <span class="text-on-surface">{{ t('预订 SPA 可能性') }}</span
                    ><span class="font-num-md text-primary">72%</span>
                  </div>
                  <div class="w-full bg-surface-container-high rounded-full h-2">
                    <div class="bg-primary h-2 rounded-full" style="width: 72%"></div>
                  </div>
                </div>
                <div>
                  <div class="flex justify-between font-label-lg text-label-lg mb-1">
                    <span class="text-on-surface">{{ t('需要延迟退房') }}</span
                    ><span class="font-num-md text-primary">88%</span>
                  </div>
                  <div class="w-full bg-surface-container-high rounded-full h-2">
                    <div class="bg-primary h-2 rounded-full" style="width: 88%"></div>
                  </div>
                </div>
                <div>
                  <div class="flex justify-between font-label-lg text-label-lg mb-1">
                    <span class="text-on-surface">{{ t('客房服务使用') }}</span
                    ><span class="font-num-md text-on-surface-variant">35%</span>
                  </div>
                  <div class="w-full bg-surface-container-high rounded-full h-2">
                    <div class="bg-outline-variant h-2 rounded-full" style="width: 35%"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Action Guardrail -->
        <div
          class="mt-2 p-4 bg-[#fff3e0] border border-[#ffb74d] rounded-xl flex items-start gap-3 shadow-sm"
        >
          <div>
            <h4 class="font-label-lg text-label-lg text-[#e65100] mb-1">
              {{ t('建议复核：生日礼遇') }}
            </h4>
            <p class="font-body-md text-body-md text-[#e65100] opacity-90">
              {{ t('系统检测到临近生日。是否自动安排 10月13日 19:00 免费果盘配送？') }}
            </p>
            <div class="mt-3 flex gap-2">
              <button
                class="px-3 py-1.5 bg-[#ef6c00] text-white rounded text-sm font-medium hover:bg-[#e65100] transition-colors shadow-sm"
              >
                {{ t('审批并排程') }}</button
              ><button
                class="px-3 py-1.5 border border-[#ef6c00] text-[#ef6c00] rounded text-sm font-medium hover:bg-[#ffe0b2] transition-colors"
              >
                {{ t('忽略') }}
              </button>
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
