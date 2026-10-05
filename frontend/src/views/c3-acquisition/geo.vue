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
    cls: 'bg-primary text-on-primary px-3 py-1 rounded-full text-sm font-bold shadow-[0_4px_12px_rgba(26,115,232,0.4)] whitespace-nowrap transform group-hover:scale-110 transition-transform relative z-20',
    raw: t('\n                            ¥899 | 房满乐精选酒店\n                        '),
  },
  {
    id: 1,
    cls: 'w-3 h-3 bg-primary rotate-45 -mt-1.5 z-10',
    raw: '',
  },
  {
    id: 2,
    cls: 'w-8 h-8 rounded-full bg-primary/20 animate-ping absolute -bottom-2 -z-10',
    raw: '',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('geo')
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
    <div class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('GEO 品牌植入 (GEO Brand Placement)') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('AI 自动优化地图搜索结果，提升品牌曝光与预订转化率。') }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          class="bg-surface-container-low hover:bg-surface-container text-on-surface-variant font-label-lg text-label-lg px-4 py-2 rounded-full border border-outline-variant flex items-center gap-2 transition-colors"
        >
          <span class="material-symbols-outlined text-sm">download</span>
          {{ t('导出报告') }}
        </button>
        <button
          class="bg-primary hover:bg-surface-tint text-on-primary font-label-lg text-label-lg px-4 py-2 rounded-full flex items-center gap-2 transition-colors shadow-[0_4px_12px_rgba(26,115,232,0.2)]"
        >
          <span class="material-symbols-outlined text-sm">play_arrow</span>
          {{ t('应用全部 AI 建议') }}
        </button>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- Map View (Takes up majority left) -->
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden shadow-sm flex flex-col relative h-[600px]"
      >
        <div
          class="p-4 border-b border-outline-variant flex justify-between items-center bg-white/80 backdrop-blur-sm z-10 absolute top-0 left-0 w-full"
        >
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">map</span>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('实时地图植入预览') }}
            </h2>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm text-on-surface-variant">{{ t('搜索词：') }}</span>
            <span
              class="bg-surface-container px-3 py-1 rounded-full text-sm font-medium border border-outline-variant"
              >{{ t('西湖边 亲子酒店') }}</span
            >
          </div>
        </div>
        <div
          class="flex-1 w-full bg-surface-container-low relative mt-16"
          data-alt="A stylized, clean digital map interface showing an urban area with water features. The map uses a very pale, light color palette with soft greys, white, and subtle blue for water. It looks like a high-end vector map design, very minimalist and professional, suitable for a corporate dashboard background. The lighting is flat and bright."
          style="
            background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuBnRpJZ3S3LrLrS5qAtXYYOAftp8vTLBWJ6l-1UC6LbkrhIQaR70giRXNjwDYFQooIM7RPA_-S3UfEjWxa1Et8hN5k5koJ5-IygAOwOcgZ29QjuqyHk4sWNLASK2QsYbXyZ0MQO-tUSjlRvEfbh3N0qPS9smCc-6AyYWFmrHZfcArp0pRsDB0Gb5KLTyH0Z3L2vr_qh0YqBhDAVc1nqn0t1YMnKcrzkQxWpiSkn24DDYtBP5iF9xyo');
          "
        >
          <!-- Brand Bubbles on Map -->
          <div
            class="absolute top-[30%] left-[45%] flex flex-col items-center group cursor-pointer"
          >
            <template v-for="(item, i) in rows" :key="i"
              ><div :class="item.cls" v-html="item.raw"></div
            ></template>
          </div>
          <div
            class="absolute top-[45%] left-[25%] flex flex-col items-center opacity-70 cursor-pointer"
          >
            <div
              class="bg-surface text-on-surface px-2 py-1 rounded-full text-xs border border-outline-variant shadow-sm whitespace-nowrap"
            >
              {{ t('¥750 | 竞品A') }}
            </div>
            <div
              class="w-2 h-2 bg-surface border-r border-b border-outline-variant rotate-45 -mt-1"
            ></div>
          </div>
        </div>
      </div>
      <!-- Right Column Insights -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
        <!-- AI Suggestions Card -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 shadow-sm border-l-2 border-l-tertiary relative overflow-hidden"
        >
          <div
            class="absolute -right-4 -top-4 w-16 h-16 bg-tertiary-fixed opacity-50 rounded-full blur-xl"
          ></div>
          <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-tertiary">auto_awesome</span>
            <h3 class="font-headline-md text-headline-md text-on-surface">
              {{ t('AI 投放建议') }}
            </h3>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-4">
            {{ t('当前地图区域搜索量激增，建议提升品牌气泡曝光权重。') }}
          </p>
          <div class="space-y-3">
            <div
              class="bg-surface-container-low p-3 rounded-lg border border-outline-variant flex justify-between items-center"
            >
              <div>
                <div class="font-label-lg text-label-lg text-on-surface">
                  {{ t('关键词加价提权') }}
                </div>
                <div class="text-xs text-on-surface-variant">{{ t('针对 \"亲子\" 标签') }}</div>
              </div>
              <button
                class="text-primary hover:bg-primary/10 p-1 rounded transition-colors text-sm font-medium"
              >
                {{ t('执行') }}
              </button>
            </div>
            <div
              class="bg-surface-container-low p-3 rounded-lg border border-outline-variant flex justify-between items-center"
            >
              <div>
                <div class="font-label-lg text-label-lg text-on-surface">
                  {{ t('更新商圈配图') }}
                </div>
                <div class="text-xs text-on-surface-variant">{{ t('替换为高点击率图') }}</div>
              </div>
              <button
                class="text-primary hover:bg-primary/10 p-1 rounded transition-colors text-sm font-medium"
              >
                {{ t('执行') }}
              </button>
            </div>
          </div>
        </div>
        <!-- Competitor Analysis -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 shadow-sm flex-1"
        >
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-headline-md text-headline-md text-on-surface">
              {{ t('周边竞品对比') }}
            </h3>
            <span class="material-symbols-outlined text-outline">analytics</span>
          </div>
          <div class="space-y-4">
            <!-- Our Hotel -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded bg-primary-container text-on-primary-container flex items-center justify-center font-bold"
                >
                  {{ t('我') }}
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">
                    {{ t('房满乐精选') }}
                  </div>
                  <div class="text-xs text-on-surface-variant">
                    {{ t('曝光得分: 92 (AI优化)') }}
                  </div>
                </div>
              </div>
              <div class="font-num-md text-num-md text-primary font-bold">¥899</div>
            </div>
            <div class="w-full h-[1px] bg-outline-variant/50"></div>
            <!-- Competitor 1 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded bg-surface-container text-on-surface-variant flex items-center justify-center"
                >
                  {{ t('竞') }}
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">
                    {{ t('全季酒店(西湖店)') }}
                  </div>
                  <div class="text-xs text-on-surface-variant">{{ t('曝光得分: 75') }}</div>
                </div>
              </div>
              <div class="font-num-md text-num-md text-on-surface">¥750</div>
            </div>
            <!-- Competitor 2 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded bg-surface-container text-on-surface-variant flex items-center justify-center"
                >
                  {{ t('竞') }}
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('桔子酒店') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('曝光得分: 68') }}</div>
                </div>
              </div>
              <div class="font-num-md text-num-md text-on-surface">¥680</div>
            </div>
          </div>
        </div>
      </div>
      <!-- Bottom Search Hotwords Banner -->
      <div
        class="col-span-12 bg-surface-container-low rounded-xl border border-outline-variant p-4 shadow-sm flex items-center gap-4"
      >
        <div
          class="bg-secondary-container text-on-secondary-container p-2 rounded-lg flex items-center justify-center"
        >
          <span class="material-symbols-outlined">trending_up</span>
        </div>
        <div class="flex-1">
          <h4 class="font-label-lg text-label-lg text-on-surface mb-1">
            {{ t('当前区域搜索热词关联') }}
          </h4>
          <div class="flex flex-wrap gap-2">
            <span
              class="bg-surface text-on-surface text-xs px-2 py-1 rounded border border-outline-variant"
              >{{ t('西湖风景名胜区') }}<span class="text-error">↑24%</span></span
            >
            <span
              class="bg-surface text-on-surface text-xs px-2 py-1 rounded border border-outline-variant"
              >{{ t('亲子套房') }}<span class="text-error">↑15%</span></span
            >
            <span
              class="bg-surface text-on-surface text-xs px-2 py-1 rounded border border-outline-variant"
              >{{ t('带停车位') }}<span class="text-on-surface-variant">-</span></span
            >
            <span
              class="bg-tertiary-fixed text-on-tertiary-fixed text-xs px-2 py-1 rounded border border-tertiary-fixed-dim"
              >{{ t('AI已自动覆盖热词') }}</span
            >
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
