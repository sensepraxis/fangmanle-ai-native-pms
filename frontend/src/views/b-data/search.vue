<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = semantic-history
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('semantic-history')
})
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="mb-8 max-w-4xl mx-auto text-center mt-8">
      <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
        {{ t('自然语言客史搜索') }}
      </h1>
      <p class="font-body-lg text-body-lg text-secondary">
        {{ t('利用 AI 洞察力，用自然语言快速筛选目标客群进行精准营销或服务升级。') }}
      </p>
    </div>
    <!-- The Giant NL Search Bar Area -->
    <div class="max-w-4xl mx-auto mb-12">
      <div class="ai-gradient-border bg-surface-container-lowest p-1 rounded-xl shadow-md">
        <div class="flex items-start p-4 bg-surface-container-lowest rounded-lg">
          <span
            class="material-symbols-outlined text-tertiary mt-1 mr-3 text-display-lg"
            style="font-variation-settings: 'FILL' 1"
            >auto_awesome</span
          >
          <div class="flex-1">
            <textarea
              class="w-full bg-transparent border-none focus:ring-0 text-headline-lg font-headline-lg text-on-surface placeholder-outline-variant resize-none h-24 p-0 leading-relaxed"
              :placeholder="
                t('输入复杂的查询条件，例如：住过3次以上、喜欢高楼层且有亲子需求的上海客人...')
              "
            ></textarea>
          </div>
          <button
            class="bg-primary hover:bg-on-primary-fixed-variant text-on-primary rounded-full w-12 h-12 flex items-center justify-center transition-colors self-end shadow-sm"
          >
            <span class="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
      <!-- Suggestions & History -->
      <div class="flex flex-wrap gap-2 mt-4 items-center">
        <span class="text-label-lg font-label-lg text-secondary mr-2">{{ t('推荐:') }}</span>
        <button
          class="px-3 py-1.5 rounded-full border border-outline-variant text-body-md text-on-surface-variant hover:bg-surface-container-low transition-colors bg-surface-container-lowest shadow-sm flex items-center gap-1"
        >
          <span class="material-symbols-outlined text-[16px] text-tertiary"
            >arrow_back_ios_new</span
          >
          {{ t('过去半年内取消订单超过2次的商务客') }}
        </button>
        <button
          class="px-3 py-1.5 rounded-full border border-outline-variant text-body-md text-on-surface-variant hover:bg-surface-container-low transition-colors bg-surface-container-lowest shadow-sm flex items-center gap-1"
        >
          <span class="material-symbols-outlined text-[16px] text-tertiary"
            >arrow_back_ios_new</span
          >
          {{ t('上个月住过海景套房的 VIP 客户') }}
        </button>
        <span class="text-label-lg font-label-lg text-secondary ml-4 mr-2">{{ t('最近:') }}</span>
        <button
          class="px-3 py-1.5 rounded-full bg-surface-container-high text-body-md text-on-surface-variant hover:bg-surface-variant transition-colors flex items-center gap-1"
        >
          <span class="material-symbols-outlined text-[16px]">history</span>
          {{ t('带宠物入住的常客') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原型辅助类（gfnav 外壳已移除，这里保留内容区用到的样式） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
}
.ai-border-glow {
  border-left: 2px solid var(--tertiary);
}
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
