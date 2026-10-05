<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = ai-engine
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('ai-engine')
})
</script>

<template>
  <div class="page">
    <!-- Center Voice Assistant -->
    <div class="flex flex-col items-center mb-16 relative">
      <div class="absolute -inset-20 bg-primary/5 rounded-full blur-3xl z-0"></div>
      <button
        class="w-48 h-48 bg-primary rounded-full flex flex-col items-center justify-center text-on-primary ai-glow voice-ripple hover:scale-105 transition-transform duration-300 z-10 relative cursor-pointer shadow-xl"
      >
        <span
          class="material-symbols-outlined mb-2"
          style="font-variation-settings: 'FILL' 1; font-size: 64px"
          >mic</span
        >
        <span class="font-headline-md text-headline-md mt-2">{{ t('点击说话') }}</span>
      </button>
      <div class="mt-8 text-center z-10">
        <h2 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('欢迎光临，请问需要什么帮助？') }}
        </h2>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('您可以直接对我说 "办理入住" 或 "查询周边美食"') }}
        </p>
      </div>
    </div>
    <!-- Quick Actions Bento Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl z-10">
      <!-- Fast Check-in -->
      <div
        class="bg-surface rounded-3xl p-8 shadow-sm border border-outline-variant/30 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low transition-colors group relative overflow-hidden"
      >
        <div
          class="w-16 h-16 bg-primary-container text-on-primary-container rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
        >
          <span class="material-symbols-outlined" style="font-size: 32px">drafts</span>
        </div>
        <h3 class="font-headline-md text-headline-md text-on-surface mb-2">{{ t('刷脸快住') }}</h3>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('30秒极速办理，无需证件') }}
        </p>
        <div
          class="absolute bottom-0 left-0 w-full h-1 bg-primary transform scale-x-0 group-hover:scale-x-100 transition-transform origin-left"
        ></div>
      </div>
      <!-- Instant Key -->
      <div
        class="bg-surface rounded-3xl p-8 shadow-sm border border-outline-variant/30 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low transition-colors group relative overflow-hidden"
      >
        <div
          class="w-16 h-16 bg-primary-container text-on-primary-container rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
        >
          <span class="material-symbols-outlined" style="font-size: 32px">vpn_key</span>
        </div>
        <h3 class="font-headline-md text-headline-md text-on-surface mb-2">{{ t('获取房卡') }}</h3>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('领取实体卡或绑定手机蓝牙') }}
        </p>
        <div
          class="absolute bottom-0 left-0 w-full h-1 bg-primary transform scale-x-0 group-hover:scale-x-100 transition-transform origin-left"
        ></div>
      </div>
      <!-- AI Concierge -->
      <div
        class="bg-surface rounded-3xl p-8 shadow-sm border border-outline-variant/30 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low transition-colors group relative overflow-hidden"
      >
        <div
          class="w-16 h-16 bg-tertiary-container text-on-tertiary-container rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
        >
          <span class="material-symbols-outlined" style="font-size: 32px">assistant</span>
        </div>
        <h3 class="font-headline-md text-headline-md text-on-surface mb-2">{{ t('AI 管家') }}</h3>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('发票开具、客房服务、周边推荐') }}
        </p>
        <div
          class="absolute bottom-0 left-0 w-full h-1 bg-tertiary transform scale-x-0 group-hover:scale-x-100 transition-transform origin-left"
        ></div>
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
