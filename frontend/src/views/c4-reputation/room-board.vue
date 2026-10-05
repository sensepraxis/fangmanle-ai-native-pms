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
    cls: 'bg-surface-container-lowest rounded-xl border border-outline-variant p-6 hover:shadow-md transition-shadow',
    raw: '\n<div class="flex justify-between items-start mb-4">\n<div class="flex items-center gap-3">\n<div class="w-10 h-10 rounded-full bg-primary-container text-primary flex items-center justify-center">\n<span class="material-symbols-outlined">cake</span>\n</div>\n<div>\n<h3 class="font-headline-lg text-headline-lg text-on-surface">生日关怀流程</h3>\n<p class="font-body-md text-body-md text-on-surface-variant">针对即将过生日的在住或即将入住宾客。</p>\n</div>\n</div>\n<div class="flex items-center gap-2">\n<span class="px-3 py-1 bg-surface-container-high rounded-full font-label-lg text-label-lg text-on-surface">已启用</span>\n<button class="text-on-surface-variant hover:text-primary transition-colors">\n<span class="material-symbols-outlined">more_vert</span>\n</button>\n</div>\n</div>\n<div class="bg-surface-container-low rounded-lg p-4 mb-4 flex flex-col md:flex-row gap-4 md:items-center">\n<div class="flex-1">\n<span class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider block mb-1">IF (触发条件)</span>\n<div class="font-body-lg text-body-lg text-on-surface bg-surface-container-lowest border border-outline-variant rounded p-2">\n                                        宾客生日 = 明天 <span class="text-outline mx-2">AND</span> 状态 = 预订/在住\n                                    </div>\n</div>\n<span class="material-symbols-outlined text-outline hidden md:block">arrow_forward</span>\n<div class="flex-1">\n<span class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider block mb-1">THEN (AI执行动作)</span>\n<div class="font-body-lg text-body-lg text-tertiary bg-tertiary-fixed rounded p-2 border border-tertiary-fixed-dim ai-glow flex flex-col gap-1">\n<span>1. 向前台推送本地蛋糕店预订建议</span>\n<span>2. 自动下发客房布置工单至客房部</span>\n</div>\n</div>\n</div>\n',
  },
  {
    id: 1,
    cls: 'bg-surface-container-lowest rounded-xl border border-outline-variant p-6 hover:shadow-md transition-shadow',
    raw: '\n<div class="flex justify-between items-start mb-4">\n<div class="flex items-center gap-3">\n<div class="w-10 h-10 rounded-full bg-primary-container text-primary flex items-center justify-center">\n<span class="material-symbols-outlined">star</span>\n</div>\n<div>\n<h3 class="font-headline-lg text-headline-lg text-on-surface">忠诚宾客礼遇</h3>\n<p class="font-body-md text-body-md text-on-surface-variant">提升高频复购客户的入住体验。</p>\n</div>\n</div>\n<div class="flex items-center gap-2">\n<span class="px-3 py-1 bg-surface-container-high rounded-full font-label-lg text-label-lg text-on-surface">已启用</span>\n<button class="text-on-surface-variant hover:text-primary transition-colors">\n<span class="material-symbols-outlined">more_vert</span>\n</button>\n</div>\n</div>\n<div class="bg-surface-container-low rounded-lg p-4 mb-4 flex flex-col md:flex-row gap-4 md:items-center">\n<div class="flex-1">\n<span class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider block mb-1">IF (触发条件)</span>\n<div class="font-body-lg text-body-lg text-on-surface bg-surface-container-lowest border border-outline-variant rounded p-2">\n                                        历史入住次数 &gt;= 3 <span class="text-outline mx-2">AND</span> 房型偏好 = 未指定\n                                    </div>\n</div>\n<span class="material-symbols-outlined text-outline hidden md:block">arrow_forward</span>\n<div class="flex-1">\n<span class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider block mb-1">THEN (AI执行动作)</span>\n<div class="font-body-lg text-body-lg text-tertiary bg-tertiary-fixed rounded p-2 border border-tertiary-fixed-dim ai-glow">\n                                        自动预分配景观角房 (Corner Room)，并在App推送欢迎信。\n                                    </div>\n</div>\n</div>\n',
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
    <div class="max-w-[1440px] mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface">
            {{ t('个性化服务策略配置') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant mt-1">
            {{ t('管理AI驱动的宾客细分服务规则，提升满意度。') }}
          </p>
        </div>
        <button
          class="bg-primary text-on-primary px-6 py-2.5 rounded-full font-label-lg text-label-lg hover:bg-primary-container hover:text-on-primary-container transition-colors flex items-center gap-2 shadow-sm"
        >
          <span class="material-symbols-outlined text-[20px]">add</span>
          {{ t('新建策略') }}
        </button>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- Left Column: Active Strategies List -->
        <div class="lg:col-span-8 flex flex-col gap-gutter">
          <template v-for="(item, i) in rows" :key="i"
            ><div :class="item.cls" v-html="item.raw"></div
          ></template>
        </div>
        <!-- Right Column: AI Insights -->
        <div class="lg:col-span-4 flex flex-col gap-gutter">
          <!-- AI Prediction Module -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 ai-glow relative overflow-hidden h-full flex flex-col"
          >
            <!-- Background Decoration -->
            <div
              class="absolute -top-10 -right-10 w-40 h-40 bg-tertiary-fixed rounded-full blur-3xl opacity-50 pointer-events-none"
            ></div>
            <div class="flex items-center gap-2 mb-6 relative z-10">
              <span class="material-symbols-outlined text-tertiary">auto_awesome</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('AI 效能预测') }}
              </h2>
            </div>
            <div
              class="flex-1 flex flex-col justify-center items-center text-center mb-6 relative z-10"
            >
              <span class="font-body-lg text-body-lg text-on-surface-variant mb-2">{{
                t('预计NPS (净推荐值) 提升')
              }}</span>
              <div class="font-num-xl text-[64px] leading-none text-tertiary font-bold mb-2">
                +12<span class="text-[32px]">%</span>
              </div>
              <p class="font-body-md text-body-md text-on-surface-variant max-w-xs">
                {{ t('基于当前生效的5条个性化策略，AI预测未来30天内的宾客满意度将显著提高。') }}
              </p>
            </div>
            <div class="bg-surface-container-low rounded-lg p-4 relative z-10">
              <h4 class="font-label-lg text-label-lg text-on-surface mb-3">{{ t('洞察亮点') }}</h4>
              <ul class="space-y-3">
                <li class="flex items-start gap-2">
                  <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5"
                    >check_circle</span
                  >
                  <span class="font-body-md text-body-md text-on-surface"
                    >{{ t('“生日关怀流程”使好评转化率提升了') }} <strong>4.2%</strong>。</span
                  >
                </li>
                <li class="flex items-start gap-2">
                  <span class="material-symbols-outlined text-[16px] text-tertiary mt-0.5"
                    >check_circle</span
                  >
                  <span class="font-body-md text-body-md text-on-surface"
                    >{{ t('角房自动分配策略减少了前台') }} <strong>15%</strong>
                    {{ t('的手动排房时间。') }}</span
                  >
                </li>
              </ul>
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
