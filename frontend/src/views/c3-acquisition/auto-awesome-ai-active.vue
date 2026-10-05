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
    cls: 'bg-tertiary-fixed/30 rounded-lg p-3 border border-tertiary-fixed-dim/30',
    raw: '<div class="flex justify-between items-start mb-2"><span class="font-label-lg text-label-lg text-on-tertiary-fixed flex items-center gap-1">刚刚</span><span class="font-num-md text-num-md text-tertiary">出价 +10%</span></div><p class="font-body-md text-body-md text-on-surface">检测到机场客流激增 -> 出价提升10%</p><p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">检测到机场高流量 → 出价上调 10%</p>',
  },
  {
    id: 1,
    cls: 'bg-surface-container rounded-lg p-3 border border-outline-variant/50',
    raw: '<div class="flex justify-between items-start mb-2"><span class="font-label-lg text-label-lg text-on-surface-variant">2 分钟前</span><span class="font-num-md text-num-md text-on-surface-variant">维持</span></div><p class="font-body-md text-body-md text-on-surface">市中心区域竞价平稳，保持当前出价。</p>',
  },
  {
    id: 2,
    cls: 'bg-primary-fixed/30 rounded-lg p-3 border border-primary-fixed-dim/30',
    raw: '<div class="flex justify-between items-start mb-2"><span class="font-label-lg text-label-lg text-on-primary-fixed">5 分钟前</span><span class="font-num-md text-num-md text-primary">出价 -5%</span></div><p class="font-body-md text-body-md text-on-surface">竞争对手降低出价，同步下调5%以优化CPO。</p>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('bidding')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="douyin" /></div>
    <div class="max-w-max-content-width mx-auto">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-6">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2 flex items-center gap-3">
            {{ t('实时出价策略监控')
            }}<span
              class="inline-flex items-center gap-1 bg-tertiary-fixed text-on-tertiary-fixed px-3 py-1 rounded-full font-label-lg text-label-lg border border-tertiary-fixed-dim/50 shadow-[0_0_10px_rgba(140,51,179,0.15)]"
              >{{ t('AI 已启用') }}</span
            >
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">
            {{ t('地理实时出价仪表盘') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 border border-outline text-on-surface rounded-lg font-label-lg text-label-lg hover:bg-surface-container transition-colors flex items-center gap-2"
          >
            {{ t('暂停策略') }}</button
          ><button
            class="px-4 py-2 bg-error text-on-error rounded-lg font-label-lg text-label-lg hover:bg-error/90 transition-colors shadow-sm flex items-center gap-2"
          >
            {{ t('人工覆盖') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- Main Map View (Spans 8 cols) -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col h-[500px] relative"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest/80 backdrop-blur-sm z-10 absolute top-0 w-full"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('实时广告位展示') }}
            </h2>
            <div class="flex items-center gap-2 text-primary font-label-lg text-label-lg">
              <span class="relative flex h-3 w-3"
                ><span
                  class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"
                ></span
                ><span class="relative inline-flex rounded-full h-3 w-3 bg-primary"></span></span
              >{{ t('实时同步') }}
            </div>
          </div>
          <div class="flex-1 w-full h-full relative bg-surface-variant">
            <img
              class="w-full h-full object-cover"
              data-location="Shanghai"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuC9Vy1Y1OIt-1MfuNLqAi_YCvAFa9AJPjmSP0hSPJLiD_d_9aaroFfujv-G6q8bKY7PjXRSLFrPcHGwjCpPB1QynqcKGUDp32e6nzCVBVGHeUPu-Gv5nkN5PZppCJBHYpXeoDP858e9zwWDXluzQTO9pAH9SFZpmTKy6HjiS-nuERVxNfENL0XbSRyHT5r1Dz4k34sQh1wcVAqfeZtvfrLy7U5bn8gy4itIIjQ0Kaj-hUGeRU3SeQY"
            />
            <!-- Map Overlay UI -->
            <div
              class="absolute bottom-4 right-4 bg-surface-container-lowest rounded-lg border border-outline-variant p-3 shadow-md"
            >
              <div class="flex flex-col gap-2">
                <div class="flex items-center gap-2 font-label-lg text-label-lg text-on-surface">
                  <div class="w-3 h-3 rounded-full bg-error"></div>
                  {{ t('高竞争') }}
                </div>
                <div class="flex items-center gap-2 font-label-lg text-label-lg text-on-surface">
                  <div class="w-3 h-3 rounded-full bg-primary"></div>
                  {{ t('最优出价') }}
                </div>
                <div class="flex items-center gap-2 font-label-lg text-label-lg text-on-surface">
                  <div class="w-3 h-3 rounded-full bg-tertiary"></div>
                  {{ t('AI 已调整') }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- AI Action Log (Spans 4 cols) -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl border-l-2 border-tertiary shadow-sm flex flex-col h-[500px]"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('AI 策略日志') }}
            </h2>
          </div>
          <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            <template v-for="(item, i) in rows" :key="i"
              ><div :class="item.cls" v-html="item.raw"></div
            ></template>
          </div>
        </div>
        <!-- Metrics Row (Spans 12 cols, 2 metrics) -->
        <div class="col-span-12 grid grid-cols-2 gap-gutter">
          <!-- CPC Trend -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-4 flex flex-col h-48"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h3
                  class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider"
                >
                  {{ t('单次点击成本（CPC）') }}
                </h3>
                <div class="font-num-xl text-num-xl text-on-surface mt-1">¥ 2.45</div>
              </div>
              <div
                class="flex items-center text-[#ba1a1a] bg-error-container px-2 py-1 rounded font-num-md text-num-md"
              >
                +0.12
              </div>
            </div>
            <div
              class="flex-1 w-full bg-surface-container-low rounded flex items-end px-2 pb-2 relative overflow-hidden"
            >
              <!-- Faux Chart -->
              <div class="w-full flex items-end justify-between h-full gap-1 opacity-60">
                <div class="w-1/12 bg-primary-fixed-dim h-1/3 rounded-t"></div>
                <div class="w-1/12 bg-primary-fixed-dim h-2/5 rounded-t"></div>
                <div class="w-1/12 bg-primary-fixed-dim h-1/2 rounded-t"></div>
                <div class="w-1/12 bg-primary-fixed-dim h-2/3 rounded-t"></div>
                <div class="w-1/12 bg-primary-fixed-dim h-3/5 rounded-t"></div>
                <div class="w-1/12 bg-primary-fixed-dim h-4/5 rounded-t"></div>
                <div class="w-1/12 bg-primary h-full rounded-t"></div>
              </div>
            </div>
          </div>
          <!-- CPO Trend -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-4 flex flex-col h-48"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h3
                  class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider"
                >
                  {{ t('单次订单成本（CPO）') }}
                </h3>
                <div class="font-num-xl text-num-xl text-on-surface mt-1">¥ 45.20</div>
              </div>
              <div
                class="flex items-center text-[#146c2e] bg-[#e6f4ea] px-2 py-1 rounded font-num-md text-num-md"
              >
                -2.40
              </div>
            </div>
            <div
              class="flex-1 w-full bg-surface-container-low rounded flex items-end px-2 pb-2 relative overflow-hidden"
            >
              <!-- Faux Chart -->
              <div class="w-full flex items-end justify-between h-full gap-1 opacity-60">
                <div class="w-1/12 bg-tertiary-fixed-dim h-4/5 rounded-t"></div>
                <div class="w-1/12 bg-tertiary-fixed-dim h-3/4 rounded-t"></div>
                <div class="w-1/12 bg-tertiary-fixed-dim h-2/3 rounded-t"></div>
                <div class="w-1/12 bg-tertiary-fixed-dim h-1/2 rounded-t"></div>
                <div class="w-1/12 bg-tertiary-fixed-dim h-3/5 rounded-t"></div>
                <div class="w-1/12 bg-tertiary-fixed-dim h-2/5 rounded-t"></div>
                <div class="w-1/12 bg-tertiary h-1/3 rounded-t"></div>
              </div>
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
