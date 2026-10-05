<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = channel-sync
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('channel-sync')
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-6">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-1">
            {{ t('渠道同步总览') }}
          </h1>
          <p class="font-body-md text-on-surface-variant">
            {{ t('实时监测全部已连接 OTA 的价格、房量、预订与档案。') }}
          </p>
        </div>
        <div class="flex items-center gap-4">
          <div
            class="flex items-center gap-2 bg-surface-container-low px-4 py-2 rounded-full border border-outline-variant"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></span
            ><span class="font-label-lg text-label-lg text-on-surface">{{ t('系统在线') }}</span>
          </div>
          <button
            class="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg hover:bg-primary-container transition-colors shadow-sm"
          >
            {{ t('强制同步全部') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- Top Left: Health Score Card (Span 4) -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col justify-between relative overflow-hidden"
        >
          <!-- Decorative AI background -->
          <div
            class="absolute -right-10 -top-10 w-32 h-32 bg-tertiary-container opacity-20 rounded-full blur-3xl pointer-events-none"
          ></div>
          <div>
            <div class="flex items-center gap-2 text-on-surface-variant mb-4">
              <span class="font-headline-md text-headline-md">{{ t('同步健康分') }}</span>
            </div>
            <div class="flex items-baseline gap-2 mb-2">
              <span class="font-num-xl text-4xl text-primary font-bold">98.5</span
              ><span class="font-label-lg text-on-surface-variant">%</span>
            </div>
            <p class="font-body-md text-sm text-on-surface-variant mb-6">
              {{ t('近 24 小时全部活跃渠道的整体数据一致性。') }}
            </p>
          </div>
          <div class="space-y-4">
            <!-- Progress bars for dimensions -->
            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-on-surface">{{ t('价格与房量') }}</span
                ><span class="text-on-surface font-num-md">99.9%</span>
              </div>
              <div class="w-full bg-surface-container-high rounded-full h-1.5">
                <div class="bg-primary h-1.5 rounded-full" style="width: 99.9%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-on-surface">{{ t('预订') }}</span
                ><span class="text-on-surface font-num-md">100%</span>
              </div>
              <div class="w-full bg-surface-container-high rounded-full h-1.5">
                <div class="bg-green-500 h-1.5 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-on-surface">{{ t('客人档案') }}</span
                ><span class="text-on-surface font-num-md">94.2%</span>
              </div>
              <div class="w-full bg-surface-container-high rounded-full h-1.5">
                <div class="bg-tertiary h-1.5 rounded-full" style="width: 94.2%"></div>
              </div>
            </div>
          </div>
          <!-- AI Insight Badge -->
          <div
            class="mt-6 ai-border-left bg-surface-container pl-3 py-2 rounded-r flex gap-2 items-start"
          >
            <p class="text-xs text-on-surface-variant leading-snug">
              {{ t('AI 提示美团客人档案同步略有延迟，已优化重试。') }}
            </p>
          </div>
        </div>
        <!-- Top Right: Channel Matrix (Span 8) -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('渠道同步矩阵') }}
            </h2>
            <span class="text-xs text-on-surface-variant">{{ t('最近更新：刚刚') }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr
                  class="bg-surface-container-low border-b border-outline-variant text-on-surface-variant font-label-lg text-sm"
                >
                  <th class="py-3 px-4 font-medium">{{ t('渠道') }}</th>
                  <th class="py-3 px-4 font-medium text-center">{{ t('房价') }}</th>
                  <th class="py-3 px-4 font-medium text-center">{{ t('库存') }}</th>
                  <th class="py-3 px-4 font-medium text-center">{{ t('订单') }}</th>
                  <th class="py-3 px-4 font-medium text-center">{{ t('客史') }}</th>
                  <th class="py-3 px-4 font-medium text-right">{{ t('延迟') }}</th>
                </tr>
              </thead>
              <tr v-for="(item, i) in rows" :key="i">
                <td class="py-3 px-4 flex items-center gap-3">
                  {{ item.channel || t('携程Ctrip') }}
                </td>
                <td class="py-3 px-4 text-center">{{ item.status || '—' }}</td>
                <td class="py-3 px-4 text-center">{{ item.last_sync || '—' }}</td>
                <td class="py-3 px-4 text-center">{{ item.orders || '—' }}</td>
                <td class="py-3 px-4 text-center">{{ item.errors || '—' }}</td>
                <td class="py-3 px-4 text-right font-num-md text-on-surface-variant">
                  {{ item.col5 || '45毫秒' }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <!-- Bottom: Real-time Sync Log (Span 12) -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col h-96"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('实时同步流水') }}
            </h2>
            <div class="flex items-center gap-4">
              <label class="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer"
                ><input
                  checked
                  class="rounded border-outline-variant text-tertiary focus:ring-tertiary"
                  type="checkbox"
                />{{ t('仅显示 AI 修正') }}</label
              ><button class="text-primary text-sm font-medium hover:underline">
                {{ t('导出日志') }}
              </button>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-4 bg-surface-bright font-num-md text-sm">
            <div class="space-y-2">
              <!-- Normal Log -->
              <div
                class="flex items-start gap-4 p-2 hover:bg-surface-container transition-colors rounded"
              >
                <span class="text-on-surface-variant w-24 shrink-0">14:32:01.002</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800 border border-blue-200 w-16 text-center"
                  >{{ t('信息') }}</span
                >
                <div class="flex-1 text-on-surface">
                  {{ t('[携程] 已推送房型 DLX_DBL 价格更新。状态：')
                  }}<span class="text-green-600">{{ t('成功') }}</span>
                </div>
              </div>
              <!-- Normal Log -->
              <div
                class="flex items-start gap-4 p-2 hover:bg-surface-container transition-colors rounded"
              >
                <span class="text-on-surface-variant w-24 shrink-0">14:32:04.115</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800 border border-blue-200 w-16 text-center"
                  >{{ t('信息') }}</span
                >
                <div class="flex-1 text-on-surface">
                  {{ t('[直连] 收到新预订 RES-99824，房量已减。状态：')
                  }}<span class="text-green-600">{{ t('成功') }}</span>
                </div>
              </div>
              <!-- Error Log -->
              <div
                class="flex items-start gap-4 p-2 bg-error-container/30 border border-error-container rounded"
              >
                <span class="text-on-surface-variant w-24 shrink-0">14:32:15.890</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800 border border-red-200 w-16 text-center"
                  >{{ t('错误') }}</span
                >
                <div class="flex-1 text-on-surface">
                  {{ t('[美团] 检测到房型 STD_TWN 房量不一致。本地：4，远端：5。') }}
                </div>
              </div>
              <!-- AI Correction Log -->
              <div
                class="flex items-start gap-4 p-2 bg-tertiary-fixed/30 ai-border-left rounded relative group overflow-hidden"
              >
                <div
                  class="absolute inset-0 bg-gradient-to-r from-tertiary-fixed/40 to-transparent opacity-50"
                ></div>
                <span class="text-tertiary w-24 shrink-0 relative z-10">14:32:16.012</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-tertiary text-on-tertiary w-16 text-center relative z-10 flex items-center justify-center gap-1"
                  >AI</span
                >
                <div class="flex-1 text-on-surface relative z-10">
                  <span class="font-bold text-tertiary">{{ t('已应用自动修正：') }}</span
                  >{{ t('依据主本地状态将美团 STD_TWN 房量由 5 覆写为 4。处理耗时：122ms。') }}
                </div>
              </div>
              <!-- Normal Log -->
              <div
                class="flex items-start gap-4 p-2 hover:bg-surface-container transition-colors rounded"
              >
                <span class="text-on-surface-variant w-24 shrink-0">14:32:20.441</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800 border border-blue-200 w-16 text-center"
                  >{{ t('信息') }}</span
                >
                <div class="flex-1 text-on-surface">
                  {{ t('[飞猪] 收到心跳确认。状态：')
                  }}<span class="text-green-600">{{ t('正常') }}</span>
                </div>
              </div>
              <!-- AI Log -->
              <div
                class="flex items-start gap-4 p-2 bg-tertiary-fixed/30 ai-border-left rounded relative overflow-hidden"
              >
                <div
                  class="absolute inset-0 bg-gradient-to-r from-tertiary-fixed/40 to-transparent opacity-50"
                ></div>
                <span class="text-tertiary w-24 shrink-0 relative z-10">14:33:01.005</span
                ><span
                  class="px-2 py-0.5 rounded text-xs bg-tertiary text-on-tertiary w-16 text-center relative z-10 flex items-center justify-center gap-1"
                  >AI</span
                >
                <div class="flex-1 text-on-surface relative z-10">
                  <span class="font-bold text-tertiary">{{ t('数据脱敏：') }}</span
                  >{{
                    t('已将客人姓名由“王先生”规范为“王”（携程档案同步），以匹配内部 CRM 结构。')
                  }}
                </div>
              </div>
            </div>
          </div>
        </div>
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
