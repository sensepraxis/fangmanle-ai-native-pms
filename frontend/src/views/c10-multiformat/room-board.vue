<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 多业态聚合消费（C10 多形态）
// 顶部 3 张 KPI 卡为原型非客房收入快照（忠实还原）；
// 底部「多业态经营概览」绑定 api.demo('multi-format') 渲染真实业态列表。
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const formats = ref<any[]>([])
onMounted(async () => {
  formats.value = await api.demo('multi-format')
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <h2 class="text-display-lg font-display-lg text-on-surface mb-2">
            {{ t('多业态聚合消费') }}
          </h2>
          <p class="text-body-lg font-body-lg text-on-surface-variant">
            {{ t('非客房收入总览与智能推荐') }}
          </p>
        </div>
        <div class="flex gap-4">
          <button
            class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg font-label-lg text-label-lg hover:bg-surface-variant transition-colors border border-outline-variant flex items-center gap-2"
          >
            {{ t('导出报表') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2 shadow-sm"
          >
            {{ t('新增销售') }}
          </button>
        </div>
      </div>
      <!-- KPI Bento -->
      <div class="grid grid-cols-12 gap-gutter">
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between h-40"
        >
          <div class="flex justify-between items-start">
            <span class="text-body-md font-body-md text-on-surface-variant">{{
              t('今日非客房总收')
            }}</span>
            <div class="p-2 bg-tertiary-fixed rounded-lg text-on-tertiary-fixed-variant"></div>
          </div>
          <div>
            <div class="text-display-lg font-num-xl text-on-surface">¥ 4,280</div>
            <div class="flex items-center text-label-lg font-label-lg text-primary mt-1">
              {{ t('较昨日 +12.5%') }}
            </div>
          </div>
        </div>
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between h-40"
        >
          <div class="flex justify-between items-start">
            <span class="text-body-md font-body-md text-on-surface-variant">{{
              t('咖啡馆流水')
            }}</span>
            <div class="p-2 bg-surface-container-high rounded-lg text-on-surface"></div>
          </div>
          <div>
            <div class="text-display-lg font-num-xl text-on-surface">¥ 1,850</div>
            <div class="text-label-lg font-label-lg text-on-surface-variant mt-1">
              {{ t('订单数: 42') }}
            </div>
          </div>
        </div>
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between h-40"
        >
          <div class="flex justify-between items-start">
            <span class="text-body-md font-body-md text-on-surface-variant">{{
              t('在地体验游')
            }}</span>
            <div class="p-2 bg-surface-container-high rounded-lg text-on-surface"></div>
          </div>
          <div>
            <div class="text-display-lg font-num-xl text-on-surface">¥ 2,430</div>
            <div class="text-label-lg font-label-lg text-on-surface-variant mt-1">
              {{ t('参与人数: 15') }}
            </div>
          </div>
        </div>
      </div>

      <!-- 多业态经营概览（绑定 api.demo('multi-format')） -->
      <div
        class="mt-8 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant bg-surface-bright flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-primary">domain</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('多业态经营概览') }}
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr
                class="border-b border-outline-variant bg-surface-container-low font-label-lg text-label-lg text-on-surface-variant"
              >
                <th class="py-3 px-4">{{ t('业态') }}</th>
                <th class="py-3 px-4">{{ t('门店') }}</th>
                <th class="py-3 px-4 text-right">{{ t('房间数') }}</th>
                <th class="py-3 px-4 text-right">{{ t('入住率') }}</th>
                <th class="py-3 px-4">{{ t('备注') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant">
              <tr
                v-for="f in formats"
                :key="f.id"
                class="hover:bg-surface-bright transition-colors"
              >
                <td class="py-3 px-4 font-medium text-on-surface">{{ f.format }}</td>
                <td class="py-3 px-4 text-sm text-on-surface">{{ f.hotel }}</td>
                <td class="py-3 px-4 text-right font-num-md text-on-surface">{{ f.rooms }}</td>
                <td class="py-3 px-4 text-right font-num-md text-primary font-bold">{{ f.occ }}</td>
                <td class="py-3 px-4 text-sm text-on-surface-variant">{{ f.note }}</td>
              </tr>
              <tr v-if="!formats.length">
                <td colspan="5" class="py-8 text-center text-on-surface-variant">
                  {{ t('暂无业态数据') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
