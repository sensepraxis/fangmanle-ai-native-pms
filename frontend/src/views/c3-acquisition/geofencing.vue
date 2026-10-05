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
    cls: 'bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm relative overflow-hidden group',
    raw: '\n<div class="absolute top-0 left-0 w-1 h-full bg-primary"></div>\n<div class="flex justify-between items-start mb-4">\n<div>\n<h2 class="text-headline-md font-headline-md text-on-surface flex items-center gap-2">\n<span class="material-symbols-outlined text-primary" data-icon="map">map</span>\n                                    地理围栏设置 (Geofencing)\n                                </h2>\n<p class="text-body-md font-body-md text-on-surface-variant mt-1">设置广告触达的地理范围，AI 建议以酒店为中心 5km 半径。</p>\n</div>\n<button class="text-primary hover:bg-primary-container px-3 py-1.5 rounded-lg text-label-lg font-label-lg transition-colors flex items-center gap-1">\n<span class="material-symbols-outlined text-[18px]" data-icon="edit">edit</span> 编辑区域\n                            </button>\n</div>\n<div class="relative w-full h-64 rounded-lg overflow-hidden border border-outline-variant mt-4">\n<!-- Using a map placeholder -->\n<img class="w-full h-full object-cover" data-alt="A high-resolution, light-mode stylized digital map interface centered on a modern urban area (Shanghai), featuring clean white and light grey streets. A semi-transparent blue circular overlay (geofence) covers a central district, with a bold blue pin indicating the hotel\'s location. The aesthetic is clean, professional, and consistent with an enterprise SaaS dashboard." data-location="Shanghai" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBO9EhS9u7WxFQLjPOtMiQBX-YuUxJJ1I0PSL1bzdSj3c0GYTZ6-guMzK0SSwN5aHLprFWMnR9rGERYCpZ93XjiOdLKImnjSW9q4WVSC3siUE421AsVz16cFCurb1i3099mcm323rhQD1IabBBXsd2ZsVagd0JNeBI0oU5KRDPs_SOlYN_6OntPxacQRUPiio6Sj1UYEFUAL_V5PS7yJv6fVTee5wtAxHkUHfT6U84-bAQ_Xx8_wE4">\n<!-- Overlay Controls -->\n<div class="absolute bottom-4 right-4 flex flex-col gap-2">\n<button class="w-10 h-10 bg-surface-container-lowest rounded shadow text-on-surface hover:bg-surface-container transition-colors flex items-center justify-center">\n<span class="material-symbols-outlined" data-icon="add">add</span>\n</button>\n<button class="w-10 h-10 bg-surface-container-lowest rounded shadow text-on-surface hover:bg-surface-container transition-colors flex items-center justify-center">\n<span class="material-symbols-outlined" data-icon="remove">remove</span>\n</button>\n</div>\n<!-- Geofence Info Tag -->\n<div class="absolute top-4 left-4 bg-surface-container-lowest/90 backdrop-blur px-3 py-2 rounded shadow-sm border border-outline-variant flex items-center gap-2">\n<span class="w-3 h-3 rounded-full bg-primary"></span>\n<span class="text-label-lg font-label-lg font-num-md text-on-surface">半径: 5.0 km</span>\n</div>\n</div>\n',
  },
  {
    id: 1,
    cls: 'bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm relative',
    raw: '\n<div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>\n<h2 class="text-headline-md font-headline-md text-on-surface flex items-center gap-2 mb-2">\n<span class="material-symbols-outlined text-tertiary" data-icon="group_add">group_add</span>\n                            目标人群筛选\n                        </h2>\n<p class="text-body-md font-body-md text-on-surface-variant mb-6 flex items-center gap-1">\n<span class="material-symbols-outlined text-tertiary text-[16px]" data-icon="auto_awesome">auto_awesome</span>\n                            AI 洞察：近期本地展会密集，商旅客户转化率预期提升 24%。\n                        </p>\n<div class="flex flex-wrap gap-3">\n<label class="relative flex items-center gap-2 px-4 py-2 border-2 border-primary bg-primary-fixed-dim rounded-lg cursor-pointer transition-all">\n<input checked class="text-primary focus:ring-primary h-4 w-4 rounded border-primary" type="checkbox">\n<span class="text-on-primary-fixed-variant font-label-lg text-label-lg">商旅客户</span>\n</label>\n<label class=")relative flex items-center gap-2 px-4 py-2 border border-outline-variant hover:border-primary hover:bg-surface-container rounded-lg cursor-pointer transition-all">\n<input class="text-primary focus:ring-primary h-4 w-4 rounded border-outline" type="checkbox">\n<span class="text-on-surface font-label-lg text-label-lg">亲子游客</span>\n</label>\n<label class=")relative flex items-center gap-2 px-4 py-2 border-2 border-primary bg-primary-fixed-dim rounded-lg cursor-pointer transition-all">\n<input checked class="text-primary focus:ring-primary h-4 w-4 rounded border-primary" type="checkbox">\n<span class="text-on-primary-fixed-variant font-label-lg text-label-lg">高净值旅客</span>\n</label>\n<label class=")relative flex items-center gap-2 px-4 py-2 border border-outline-variant hover:border-primary hover:bg-surface-container rounded-lg cursor-pointer transition-all">\n<input class="text-primary focus:ring-primary h-4 w-4 rounded border-outline" type="checkbox">\n<span class="text-on-surface font-label-lg text-label-lg">长租客</span>\n</label>\n<button class="px-4 py-2 border border-dashed border-outline-variant text-outline hover:text-primary hover:border-primary rounded-lg flex items-center gap-1 transition-all">\n<span class="material-symbols-outlined text-[18px]" data-icon="add">add</span> 自定义标签\n                            </button>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('geofencing')
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
    <!-- Breadcrumb & Header -->
    <div class="mb-8">
      <div class="flex items-center text-label-lg font-label-lg text-outline mb-2">
        <span>{{ t('价格助手') }}</span>
        <span class="material-symbols-outlined text-[16px] mx-1" data-icon="chevron_right"
          >chevron_right</span
        >
        <span>{{ t('投放策略') }}</span>
        <span class="material-symbols-outlined text-[16px] mx-1" data-icon="chevron_right"
          >chevron_right</span
        >
        <span class="text-primary font-medium">GEO Campaign Setup</span>
      </div>
      <h1 class="text-display-lg font-display-lg text-on-surface mb-2">
        {{ t('智能投放方案配置') }}
      </h1>
      <p class="text-body-lg font-body-lg text-on-surface-variant flex items-center gap-2">
        <span class="material-symbols-outlined text-tertiary" data-icon="auto_awesome"
          >auto_awesome</span
        >
        {{ t('AI 已为您生成初步的地理围栏及人群策略，请确认并调整配置。') }}
      </p>
    </div>
    <!-- Stepper -->
    <div class="flex items-center mb-8 px-4">
      <div class="flex items-center text-primary">
        <div
          class="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-num-md"
        >
          1
        </div>
        <span class="ml-2 font-label-lg text-label-lg">{{ t('基础设定') }}</span>
      </div>
      <div class="flex-1 h-[2px] bg-primary mx-4"></div>
      <div class="flex items-center text-primary">
        <div
          class="w-8 h-8 rounded-full border-2 border-primary bg-primary-container text-on-primary-container flex items-center justify-center font-num-md"
        >
          2
        </div>
        <span class="ml-2 font-label-lg text-label-lg">{{ t('GEO 配置') }}</span>
      </div>
      <div class="flex-1 h-[2px] bg-surface-container-high mx-4"></div>
      <div class="flex items-center text-outline">
        <div
          class="w-8 h-8 rounded-full border-2 border-outline bg-surface text-outline flex items-center justify-center font-num-md"
        >
          3
        </div>
        <span class="ml-2 font-label-lg text-label-lg">{{ t('预算与排期') }}</span>
      </div>
      <div class="flex-1 h-[2px] bg-surface-container-high mx-4"></div>
      <div class="flex items-center text-tertiary">
        <div
          class="w-8 h-8 rounded-full border-2 border-tertiary bg-tertiary-container text-on-tertiary-container flex items-center justify-center font-num-md"
        >
          <span class="material-symbols-outlined text-[16px]" data-icon="auto_awesome"
            >auto_awesome</span
          >
        </div>
        <span class="ml-2 font-label-lg text-label-lg relative group cursor-help">
          {{ t('AI 效果预测') }}
          <div
            class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-inverse-surface text-inverse-on-surface text-label-lg rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 text-center"
          >
            {{ t('基于当前配置预测的转化率') }}
          </div>
        </span>
      </div>
    </div>
    <div class="grid grid-cols-12 gap-gutter">
      <!-- Left Column: Config -->
      <div class="col-span-12 lg:col-span-8 flex flex-col gap-6">
        <template v-for="(item, i) in rows" :key="i"
          ><div :class="item.cls" v-html="item.raw"></div
        ></template>
      </div>
      <!-- Right Column: AI Sidebar & Actions -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-6">
        <!-- Smart Bidding Toggle -->
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-headline-md font-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary" data-icon="smart_toy"
                >smart_toy</span
              >
              {{ t('AI 自动调价') }}
            </h3>
            <label class="relative inline-flex items-center cursor-pointer">
              <input checked class="sr-only peer" type="checkbox" value="" />
              <div
                class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-outline-variant after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
              ></div>
            </label>
          </div>
          <p class="text-body-md font-body-md text-on-surface-variant mb-4">
            {{ t('允许系统根据实时市场需求和库存状况，自动优化竞价策略。') }}
          </p>
          <!-- R1 Low Risk Banner -->
          <div
            class="bg-surface-container-low border-l-4 border-yellow-400 p-3 rounded-r-lg flex items-start gap-2"
          >
            <span
              class="material-symbols-outlined text-yellow-600 mt-0.5 text-[20px]"
              data-icon="info"
              >info</span
            >
            <div>
              <h4 class="text-label-lg font-label-lg text-on-surface">{{ t('建议开启') }}</h4>
              <p class="text-[13px] text-on-surface-variant mt-1">
                {{ t('历史数据显示，开启自动调价可降低约 15% 的获客成本。') }}
              </p>
            </div>
          </div>
        </div>
        <!-- Estimated Reach & ROI -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-[0_4px_20px_rgba(114,17,153,0.05)] overflow-hidden"
        >
          <div
            class="bg-tertiary-fixed-dim/20 p-4 border-b border-outline-variant flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-tertiary" data-icon="monitoring"
              >monitoring</span
            >
            <h3 class="text-headline-md font-headline-md text-on-surface">
              {{ t('效果预测 (7天)') }}
            </h3>
          </div>
          <div class="p-6 flex flex-col gap-6">
            <div class="flex justify-between items-end">
              <div>
                <p class="text-label-lg font-label-lg text-outline mb-1">{{ t('预计覆盖人数') }}</p>
                <div class="text-display-lg font-num-xl text-on-surface">
                  12,500 <span class="text-body-md font-body-md text-on-surface-variant">+</span>
                </div>
              </div>
              <div class="text-right">
                <p class="text-label-lg font-label-lg text-outline mb-1">
                  {{ t('预估点击率 (CTR)') }}
                </p>
                <div
                  class="text-headline-lg font-num-xl text-primary flex items-center gap-1 justify-end"
                >
                  4.2%
                  <span
                    class="material-symbols-outlined text-[18px] text-green-600"
                    data-icon="trending_up"
                    >trending_up</span
                  >
                </div>
              </div>
            </div>
            <div class="h-[1px] w-full bg-surface-variant"></div>
            <div>
              <p class="text-label-lg font-label-lg text-outline mb-2 flex items-center gap-1">
                {{ t('预期投资回报率 (ROI)') }}
                <span
                  class="material-symbols-outlined text-[16px] text-tertiary cursor-help"
                  data-icon="auto_awesome"
                  title="AI Calculated"
                  >auto_awesome</span
                >
              </p>
              <div class="flex items-end gap-3">
                <span class="text-display-lg font-num-xl text-on-surface">1 : 3.8</span>
                <span class="text-body-md text-on-surface-variant mb-2">{{
                  t('较历史平均 +0.4')
                }}</span>
              </div>
              <!-- Progress bar visualization -->
              <div class="w-full bg-surface-container-high rounded-full h-2 mt-3">
                <div
                  class="bg-gradient-to-r from-primary to-tertiary h-2 rounded-full"
                  style="width: 75%"
                ></div>
              </div>
            </div>
          </div>
        </div>
        <!-- Actions -->
        <div class="mt-auto flex flex-col gap-3">
          <button
            class="w-full bg-primary hover:bg-surface-tint text-on-primary py-3 rounded-lg text-headline-md font-headline-md transition-all active:scale-[0.98] shadow-md flex items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined" data-icon="rocket_launch">rocket_launch</span>
            {{ t('立即开启 (Launch Now)') }}
          </button>
          <button
            class="w-full bg-surface-container-low hover:bg-surface-container text-on-surface-variant py-3 rounded-lg text-label-lg font-label-lg transition-colors"
          >
            {{ t('保存草稿') }}
          </button>
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
