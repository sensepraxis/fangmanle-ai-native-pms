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
    cls: 'glass-card rounded-xl p-5 border-t-4 border-t-tertiary-fixed-dim flex-1',
    raw: '\n<h3 class="font-headline-md text-headline-md text-on-surface mb-3 flex items-center">\n<span class="material-symbols-outlined text-tertiary mr-2">lightbulb</span>\n                        AI 转化洞察\n                    </h3>\n<p class="text-sm text-on-surface-variant mb-4">\n                        当前从小程序注册到添加企微的转化率高达 <strong class="text-on-surface">82%</strong>。AI 建议针对未添加企微的用户发送二次召回短信。\n                    </p>\n<div class="bg-surface-container-low p-3 rounded border border-outline-variant/50 text-sm">\n<span class="text-outline text-xs block mb-1">建议动作</span>\n<div class="flex justify-between items-center">\n<span class="font-medium">配置 24 小时未加微触达</span>\n<button class="text-primary text-xs font-bold hover:underline">去配置</button>\n</div>\n</div>\n',
  },
  {
    id: 1,
    cls: 'glass-card rounded-xl p-5 flex-1',
    raw: '\n<h3 class="font-headline-md text-headline-md text-on-surface mb-3 flex items-center">\n<span class="material-symbols-outlined text-secondary mr-2">confirmation_number</span>\n                        引流券发放状态\n                    </h3>\n<div class="space-y-3">\n<div>\n<div class="flex justify-between text-xs mb-1">\n<span class="text-on-surface-variant">新客 50 元立减券</span>\n<span class="font-num-md">8,430 / 10,000</span>\n</div>\n<div class="w-full bg-surface-container-high rounded-full h-2">\n<div class="bg-primary h-2 rounded-full" style="width: 84%"></div>\n</div>\n</div>\n<div>\n<div class="flex justify-between text-xs mb-1">\n<span class="text-on-surface-variant">周末特惠 8 折券</span>\n<span class="font-num-md">3,120 / 5,000</span>\n</div>\n<div class="w-full bg-surface-container-high rounded-full h-2">\n<div class="bg-tertiary h-2 rounded-full" style="width: 62%"></div>\n</div>\n</div>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('funnel')
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
    <AcquisitionLoopPanel focus="overview" />
    <!-- Header -->
    <div class="mb-8 flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('私域转化全链路监控') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('实时追踪从公域曝光到企微沉淀的转化效率与 AI 触达效果。') }}
        </p>
      </div>
      <div class="flex space-x-4">
        <div
          class="bg-surface-container-low px-4 py-2 rounded-lg border border-outline-variant flex items-center"
        >
          <span class="material-symbols-outlined text-primary mr-2">calendar_today</span>
          <span class="font-label-lg text-label-lg text-on-surface-variant">{{
            t('过去 7 天')
          }}</span>
        </div>
        <button
          class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg flex items-center hover:bg-surface-tint transition-colors"
        >
          <span class="material-symbols-outlined mr-2">download</span>
          {{ t('导出报告') }}
        </button>
      </div>
    </div>
    <!-- Funnel Overview & AI Insights Bento Grid -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter mb-8">
      <!-- Left: Funnel Chart (Spans 8 cols) -->
      <div class="md:col-span-8 glass-card rounded-xl p-6 relative overflow-hidden">
        <h2 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center">
          <span class="material-symbols-outlined text-primary mr-2">filter_alt</span>
          {{ t('转化漏斗图') }}
        </h2>
        <!-- Funnel Visualization Placeholder (CSS Based) -->
        <div class="flex flex-col items-center w-full space-y-4 py-4">
          <!-- Step 1 -->
          <div class="w-full max-w-3xl relative">
            <div
              class="bg-primary-container/20 rounded-lg p-4 flex justify-between items-center border border-primary-container/30"
            >
              <div class="flex items-center">
                <div
                  class="w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center mr-4"
                >
                  <span class="material-symbols-outlined">visibility</span>
                </div>
                <div>
                  <h3 class="font-label-lg text-label-lg font-bold">
                    {{ t('小红书/视频号曝光') }}
                  </h3>
                  <p class="text-xs text-on-surface-variant">{{ t('公域内容触达') }}</p>
                </div>
              </div>
              <div class="text-right">
                <span class="font-num-xl text-num-xl text-primary">125,430</span>
                <span class="text-xs text-on-surface-variant ml-1">{{ t('次') }}</span>
              </div>
            </div>
            <!-- Connector -->
            <div
              class="absolute left-1/2 bottom-[-16px] w-0.5 h-4 bg-outline-variant -translate-x-1/2"
            ></div>
          </div>
          <!-- Step 2 -->
          <div class="w-11/12 max-w-2xl relative">
            <div
              class="bg-tertiary-container/20 rounded-lg p-4 flex justify-between items-center border border-tertiary-container/30"
            >
              <div class="flex items-center">
                <div
                  class="w-10 h-10 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center mr-4"
                >
                  <span class="material-symbols-outlined">local_activity</span>
                </div>
                <div>
                  <h3 class="font-label-lg text-label-lg font-bold">{{ t('领券中心访问') }}</h3>
                  <p class="text-xs text-on-surface-variant">{{ t('转化率: 12.4%') }}</p>
                </div>
              </div>
              <div class="text-right">
                <span class="font-num-xl text-num-xl text-tertiary">15,553</span>
                <span class="text-xs text-on-surface-variant ml-1">{{ t('人') }}</span>
              </div>
            </div>
            <!-- Connector -->
            <div
              class="absolute left-1/2 bottom-[-16px] w-0.5 h-4 bg-outline-variant -translate-x-1/2"
            ></div>
          </div>
          <!-- Step 3 -->
          <div class="w-10/12 max-w-xl relative">
            <div
              class="bg-secondary-container/30 rounded-lg p-4 flex justify-between items-center border border-secondary-container/50"
            >
              <div class="flex items-center">
                <div
                  class="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center mr-4"
                >
                  <span class="material-symbols-outlined">app_registration</span>
                </div>
                <div>
                  <h3 class="font-label-lg text-label-lg font-bold">{{ t('小程序注册') }}</h3>
                  <p class="text-xs text-on-surface-variant">{{ t('转化率: 45.2%') }}</p>
                </div>
              </div>
              <div class="text-right">
                <span class="font-num-xl text-num-xl text-on-surface">7,029</span>
                <span class="text-xs text-on-surface-variant ml-1">{{ t('人') }}</span>
              </div>
            </div>
            <!-- Connector -->
            <div
              class="absolute left-1/2 bottom-[-16px] w-0.5 h-4 bg-outline-variant -translate-x-1/2"
            ></div>
          </div>
          <!-- Step 4 -->
          <div class="w-8/12 max-w-md relative">
            <div
              class="bg-surface-container-highest rounded-lg p-4 flex justify-between items-center border border-outline-variant border-l-4 border-l-primary ai-glow"
            >
              <div class="flex items-center">
                <div
                  class="w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center mr-4 shadow-sm"
                >
                  <span class="material-symbols-outlined">person_add</span>
                </div>
                <div>
                  <h3 class="font-label-lg text-label-lg font-bold">
                    {{ t('添加企微 (私域沉淀)') }}
                  </h3>
                  <p class="text-xs text-primary-container font-medium flex items-center">
                    <span class="material-symbols-outlined text-[14px] mr-1"
                      >temp_preferences_custom</span
                    >
                    {{ t('AI 自动引导率: 82%') }}
                  </p>
                </div>
              </div>
              <div class="text-right">
                <span class="font-num-xl text-num-xl text-on-surface">5,763</span>
                <span class="text-xs text-on-surface-variant ml-1">{{ t('人') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Right: AI Insights (Spans 4 cols) -->
      <div class="md:col-span-4 flex flex-col gap-gutter">
        <template v-for="(item, i) in rows" :key="i"
          ><div :class="item.cls" v-html="item.raw"></div
        ></template>
      </div>
    </div>
    <!-- AI Script Templates Table -->
    <div class="glass-card rounded-xl overflow-hidden mb-8">
      <div
        class="p-5 border-b border-outline-variant flex justify-between items-center bg-surface-bright"
      >
        <h2 class="font-headline-md text-headline-md text-on-surface flex items-center">
          <span class="material-symbols-outlined text-primary mr-2">chat</span>
          {{ t('转化路径 AI 话术模板') }}
        </h2>
        <button class="text-primary font-label-lg text-label-lg hover:underline flex items-center">
          <span class="material-symbols-outlined text-[18px] mr-1">add</span>{{ t('新建模板') }}
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr
              class="bg-surface-container-low text-on-surface-variant text-sm border-b border-outline-variant"
            >
              <th class="p-4 font-medium">{{ t('触发节点') }}</th>
              <th class="p-4 font-medium">{{ t('话术类型') }}</th>
              <th class="p-4 font-medium w-1/2">{{ t('内容预览') }}</th>
              <th class="p-4 font-medium text-center">{{ t('状态') }}</th>
              <th class="p-4 font-medium text-right">{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody class="text-sm">
            <tr
              class="border-b border-outline-variant/50 hover:bg-surface-container-lowest transition-colors"
            >
              <td class="p-4 font-medium text-on-surface">{{ t('小程序注册成功') }}</td>
              <td class="p-4">
                <span class="bg-primary/10 text-primary px-2 py-1 rounded text-xs">{{
                  t('欢迎语 + 企微引导')
                }}</span>
              </td>
              <td class="p-4 text-on-surface-variant italic line-clamp-2">
                {{
                  t(
                    '\"哈喽！欢迎注册房满乐，您的 50 元新人礼包已到账。添加专属管家微信，即可激活使用，并获取更多隐秘房型推荐哦~\"',
                  )
                }}
              </td>
              <td class="p-4 text-center">
                <span
                  class="inline-flex items-center text-[#146c2e] bg-[#e6f4ea] px-2 py-1 rounded-full text-xs"
                >
                  <span class="w-2 h-2 rounded-full bg-[#146c2e] mr-1"></span>
                  {{ t('运行中') }}</span
                >
              </td>
              <td class="p-4 text-right">
                <button class="text-primary hover:text-surface-tint">
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
              </td>
            </tr>
            <tr
              class="border-b border-outline-variant/50 hover:bg-surface-container-lowest transition-colors"
            >
              <td class="p-4 font-medium text-on-surface">{{ t('领券后未核销 (24h)') }}</td>
              <td class="p-4">
                <span class="bg-tertiary/10 text-tertiary px-2 py-1 rounded text-xs">{{
                  t('优惠催化')
                }}</span>
              </td>
              <td class="p-4 text-on-surface-variant italic">
                {{
                  t(
                    '\"您的 50 元新人券即将过期，最近这几套网红江景房正空出，快来找管家预定吧，立享优惠！\"',
                  )
                }}
              </td>
              <td class="p-4 text-center">
                <span
                  class="inline-flex items-center text-[#146c2e] bg-[#e6f4ea] px-2 py-1 rounded-full text-xs"
                >
                  <span class="w-2 h-2 rounded-full bg-[#146c2e] mr-1"></span>
                  {{ t('运行中') }}</span
                >
              </td>
              <td class="p-4 text-right">
                <button class="text-primary hover:text-surface-tint">
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
              </td>
            </tr>
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="p-4 font-medium text-on-surface">{{ t('添加企微成功') }}</td>
              <td class="p-4">
                <span class="bg-secondary/10 text-secondary px-2 py-1 rounded text-xs">{{
                  t('管家破冰')
                }}</span>
              </td>
              <td class="p-4 text-on-surface-variant italic">
                {{
                  t(
                    '\"您好，我是您的专属管家。已为您激活新人优惠！请问您近期有出行计划吗？我可以为您推荐适合的房源。\"',
                  )
                }}
              </td>
              <td class="p-4 text-center">
                <span
                  class="inline-flex items-center text-outline bg-surface-container px-2 py-1 rounded-full text-xs"
                >
                  <span class="w-2 h-2 rounded-full bg-outline mr-1"></span> {{ t('已暂停') }}</span
                >
              </td>
              <td class="p-4 text-right">
                <button class="text-primary hover:text-surface-tint">
                  <span class="material-symbols-outlined text-[20px]">play_arrow</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
