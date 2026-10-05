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
    cls: 'bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant ai-glow flex flex-col justify-between',
    raw: '<div><div class="flex justify-between items-start mb-4"><span class="bg-tertiary-container/20 text-tertiary text-xs font-bold px-2 py-1 rounded">小红书</span><span class="text-on-surface-variant text-sm flex items-center gap-1">热点</span></div><h3 class="font-headline-lg text-headline-lg text-on-surface mb-2">#周末逃离城市计划</h3><p class="font-body-md text-body-md text-on-surface-variant line-clamp-3 mb-4">基于近期降温天气，AI 建议一套带有“私汤”、“温暖”标签的短图文拍摄分镜与灵感碎片。已有 80% 本地竞品开始推送此类内容。</p></div><button class="w-full bg-surface-container text-primary font-label-lg py-2 rounded-lg hover:bg-primary-container/10 transition-colors border border-outline-variant">生成拍摄脚本</button>',
  },
  {
    id: 1,
    cls: 'bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant flex flex-col justify-between relative overflow-hidden group',
    raw: '<div class="absolute inset-0 bg-gradient-to-br from-transparent to-surface-container opacity-0 group-hover:opacity-100 transition-opacity"></div><div class="relative z-10"><div class="flex justify-between items-start mb-4"><span class="bg-secondary-container text-on-secondary-container text-xs font-bold px-2 py-1 rounded">视频号</span><span class="text-on-surface-variant text-sm flex items-center gap-1">节假日预热</span></div><h3 class="font-headline-lg text-headline-lg text-on-surface mb-2">元旦跨年氛围感</h3><p class="font-body-md text-body-md text-on-surface-variant line-clamp-3 mb-4">建议剪辑一段 15s 的酒店大堂壁炉氛围视频，配以温馨音乐，提前锁定跨年夜房源预订。</p></div><button class="relative z-10 w-full bg-surface-container text-on-surface font-label-lg py-2 rounded-lg hover:bg-surface-variant transition-colors border border-outline-variant">查看拍摄指导</button>',
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
    <div class="flex justify-between items-end mb-6">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">
          {{ t('内容种草中心') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('内容集成中心 - AI 驱动的社媒管理。') }}
        </p>
      </div>
      <button
        class="bg-primary text-on-primary font-label-lg text-label-lg px-6 py-3 rounded-full hover:bg-primary-fixed-dim hover:text-on-primary-fixed transition-colors shadow-sm flex items-center gap-2"
      >
        {{ t('创作灵感库') }}
      </button>
    </div>
    <!-- Pro Tip Notice -->
    <div
      class="mb-6 bg-secondary-container/50 border border-secondary-fixed text-on-secondary-container px-4 py-3 rounded-lg flex items-start gap-3"
    >
      <div>
        <p class="font-label-lg font-bold">{{ t('发文提示') }}</p>
        <p class="text-sm mt-1">
          {{
            t(
              '为了获得平台的最高流量推荐（最大化曝光），强烈建议您将此处生成的脚本和素材导出后，直接在抖音或小红书官方App内完成最终编辑与发布。',
            )
          }}
        </p>
      </div>
    </div>
    <div class="grid grid-cols-12 gap-gutter">
      <!-- AI Suggestions (Bento Grid Style) -->
      <div class="col-span-12 lg:col-span-8 grid grid-cols-2 gap-gutter">
        <template v-for="(item, i) in rows" :key="i"
          ><div :class="item.cls" v-html="item.raw"></div
        ></template>
      </div>
      <!-- Content Calendar -->
      <div
        class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant flex flex-col"
      >
        <div class="p-6 border-b border-outline-variant flex justify-between items-center">
          <h2 class="font-headline-md text-headline-md text-on-background">{{ t('近期日历') }}</h2>
          <button class="text-primary hover:bg-primary-container/10 p-1 rounded"></button>
        </div>
        <div class="p-4 flex-1">
          <div class="space-y-4">
            <!-- Event 1 -->
            <div class="flex gap-4 items-start">
              <div
                class="flex flex-col items-center justify-center bg-primary-container/10 text-primary rounded-lg w-12 h-12 flex-shrink-0"
              >
                <span class="text-sm font-bold">{{ t('今天') }}</span>
              </div>
              <div class="flex-1 bg-surface rounded-lg p-3 border border-outline-variant">
                <div class="flex justify-between mb-1">
                  <span class="font-label-lg text-on-surface">{{ t('下午茶上新推广') }}}</span
                  ><span class="text-xs text-on-surface-variant">14:00</span>
                </div>
                <span
                  class="text-xs bg-error-container text-on-error-container px-2 py-0.5 rounded"
                  >{{ t('未发布') }}</span
                >
              </div>
            </div>
            <!-- Event 2 -->
            <div class="flex gap-4 items-start">
              <div
                class="flex flex-col items-center justify-center bg-surface-container-high text-on-surface-variant rounded-lg w-12 h-12 flex-shrink-0"
              >
                <span class="text-sm">{{ t('24日') }}</span>
              </div>
              <div
                class="flex-1 bg-surface rounded-lg p-3 border border-outline-variant opacity-75"
              >
                <div class="flex justify-between mb-1">
                  <span class="font-label-lg text-on-surface">{{ t('圣诞主题房探店视频') }}}</span
                  ><span class="text-xs text-on-surface-variant">{{ t('待定') }}</span>
                </div>
                <span
                  class="text-xs bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded"
                  >{{ t('草稿中') }}</span
                >
              </div>
            </div>
          </div>
        </div>
        <div
          class="p-4 border-t border-outline-variant bg-surface-container-low/50 mt-auto rounded-b-xl"
        >
          <button class="w-full text-center text-primary font-label-lg hover:underline">
            {{ t('查看完整日历') }}
          </button>
        </div>
      </div>
      <!-- Asset Library Preview -->
      <div class="col-span-12 mt-4">
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-headline-md text-headline-md text-on-background">
            {{ t('素材库快速预览') }}
          </h2>
          <a class="text-primary font-label-lg hover:underline flex items-center gap-1" href="#">{{
            t('全部素材')
          }}</a>
        </div>
        <div class="grid grid-cols-4 gap-4">
          <div class="aspect-square bg-surface-container rounded-xl overflow-hidden relative group">
            <img
              class="w-full h-full object-cover"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDyzYWPht5MnC8rsiXjofG6Eh3ldODJLmNuUbqR06hOuzfZJTLljBe-kctxfQ-WGqanlHAYNJ_y4l9PIH3UK2w2ZKevxAV4RBkn2BdB3_lMQdechSDRC7zhPgyeu9ph3NPDlCZkaPEPyNgQv39RLl7NCEPSqJyWMLuXCy2uqq-ePCe8rEnIYfJQkTCU1Zh_qxC-k6VzHyGn0Yt69tQcK6xnjPiMO8K85OWx_VeqVzcxbf22E2Iz5B4"
            />
            <div
              class="absolute inset-0 bg-on-background/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
            >
              <button class="bg-surface text-on-surface rounded-full p-2"></button>
            </div>
          </div>
          <div
            class="aspect-square bg-surface-container rounded-xl overflow-hidden relative group border-2 border-dashed border-outline-variant flex items-center justify-center hover:bg-surface-container-high transition-colors cursor-pointer"
          >
            <div class="text-center text-on-surface-variant">
              <p class="font-label-lg">{{ t('上传新素材') }}</p>
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
