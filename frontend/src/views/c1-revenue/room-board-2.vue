<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 新店定价策略配置（冷启动模式）：数据源选择 + 市场先验参考 + 首日定价模拟
// 长尾域数据：api.demo('rate') 提供冷启动建议价预览
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const rate = ref<any[]>([])
onMounted(async () => {
  rate.value = await api.demo('rate')
})
// 首日模拟预览：取前 2 条房型建议价
const preview = () => rate.value.slice(0, 2)
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="mb-8 flex justify-between items-end">
        <div>
          <div class="flex items-center gap-2 mb-2">
            <span
              class="bg-surface-variant text-on-surface-variant px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider flex items-center gap-1"
            >
              <span class="material-symbols-outlined text-sm">ac_unit</span>
              {{ t('冷启动模式 (无历史数据)') }}</span
            >
          </div>
          <h1 class="font-display-lg text-display-lg text-on-surface">
            {{ t('新店定价策略配置') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant mt-2 max-w-2xl">
            {{
              t(
                '系统检测到您的店铺缺乏历史交易数据。请选择一种冷启动策略，AI 将在此基础上进行动态调价。在数据积累达标前，系统将保持',
              )
            }}
            <strong class="text-primary">{{ t('模式 B (逐条确认)') }}</strong
            >{{ t('，确保每次价格变更都在您的掌控之中。') }}
          </p>
        </div>
      </div>
      <!-- 警告横幅 -->
      <div
        class="bg-[#eef3fd] border-l-4 border-primary p-4 rounded-r-lg mb-8 flex items-start gap-4"
      >
        <span
          class="material-symbols-outlined text-primary"
          style="font-variation-settings: 'FILL' 1"
          >info</span
        >
        <div>
          <h3 class="font-headline-md text-headline-md text-primary-fixed-variant">
            {{ t('当前运行状态：模式 B (逐条确认)') }}
          </h3>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            由于处于冷启动阶段，所有 AI
            建议价的置信度被标记为"低"。系统不会自动执行改价，您需要在"待确认列表"中手动审核每一条调价建议。预计需要收集
            30 天的交易数据后方可切换至全自动模式。
          </p>
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- 步骤 1：选择基础数据源 -->
        <div class="col-span-12 lg:col-span-8 space-y-6">
          <h2
            class="font-headline-md text-headline-md text-on-surface border-b border-surface-variant pb-2"
          >
            {{ t('步骤 1: 选择基础数据源') }}
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              class="relative bg-surface-container-lowest border-2 border-primary rounded-xl p-6 shadow-sm cursor-pointer hover:shadow-md transition-shadow group"
            >
              <div class="absolute top-4 right-4 text-primary">
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                  >radio_button_checked</span
                >
              </div>
              <div
                class="w-12 h-12 bg-primary-container text-on-primary-container rounded-full flex items-center justify-center mb-4"
              >
                <span class="material-symbols-outlined">timeline</span>
              </div>
              <h3 class="font-headline-md text-headline-md text-on-surface mb-2">
                {{ t('市场指数迁移') }}
              </h3>
              <p class="font-body-md text-body-md text-on-surface-variant text-sm h-20">
                {{ t('抓取同城同商圈、同档次酒店的公开市场价格均线，作为基础起步价。推荐使用。') }}
              </p>
              <div class="mt-4 flex items-center gap-1 text-tertiary font-medium text-sm">
                <span class="material-symbols-outlined text-sm">arrow_back_ios_new</span>
                {{ t('AI 推荐') }}
              </div>
            </div>
            <div
              class="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm cursor-pointer hover:border-outline hover:shadow-md transition-all group"
            >
              <div class="absolute top-4 right-4 text-outline-variant group-hover:text-outline">
                <span class="material-symbols-outlined">radio_button_unchecked</span>
              </div>
              <div
                class="w-12 h-12 bg-surface-container-high text-on-surface rounded-full flex items-center justify-center mb-4 group-hover:bg-surface-variant transition-colors"
              >
                <span class="material-symbols-outlined">storefront</span>
              </div>
              <h3 class="font-headline-md text-headline-md text-on-surface mb-2">
                {{ t('相似店迁移') }}
              </h3>
              <p class="font-body-md text-body-md text-on-surface-variant text-sm h-20">
                {{ t('如果您在系统内有其他相似的成熟门店，可直接复制其基础价格体系和动态规则。') }}
              </p>
              <div class="mt-4 text-on-surface-variant font-medium text-sm">
                {{ t('需绑定其他门店') }}
              </div>
            </div>
            <div
              class="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm cursor-pointer hover:border-outline hover:shadow-md transition-all group"
            >
              <div class="absolute top-4 right-4 text-outline-variant group-hover:text-outline">
                <span class="material-symbols-outlined">radio_button_unchecked</span>
              </div>
              <div
                class="w-12 h-12 bg-surface-container-high text-on-surface rounded-full flex items-center justify-center mb-4 group-hover:bg-surface-variant transition-colors"
              >
                <span class="material-symbols-outlined">edit_note</span>
              </div>
              <h3 class="font-headline-md text-headline-md text-on-surface mb-2">
                {{ t('手动设置基线') }}
              </h3>
              <p class="font-body-md text-body-md text-on-surface-variant text-sm h-20">
                {{ t('为每个房型手动输入平日起步价和周末起步价。适合对自有客源极度自信的商家。') }}
              </p>
            </div>
          </div>
          <!-- 已选配置 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mt-6 shadow-[0_4px_12px_rgba(0,0,0,0.03)]"
          >
            <div class="flex items-center gap-2 mb-4">
              <h3 class="font-headline-md text-headline-md text-on-surface">
                {{ t('市场指数配置') }}
              </h3>
              <span class="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs">{{
                t('已选择')
              }}</span>
            </div>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                  t('对比商圈')
                }}</label>
                <select
                  class="w-full bg-surface-bright border border-outline-variant rounded-lg p-3 text-body-md focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                >
                  <option>{{ t('天河体育中心商圈') }}</option>
                  <option>{{ t('珠江新城商圈') }}</option>
                </select>
              </div>
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                  t('对比档次')
                }}</label>
                <select
                  class="w-full bg-surface-bright border border-outline-variant rounded-lg p-3 text-body-md focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                >
                  <option>{{ t('中高端精品酒店') }}</option>
                  <option>{{ t('经济型快捷酒店') }}</option>
                </select>
              </div>
            </div>
            <div class="mt-6 flex justify-end">
              <button
                class="bg-primary text-on-primary px-6 py-2.5 rounded-full font-label-lg text-label-lg hover:bg-surface-tint hover:shadow-md transition-all flex items-center gap-2"
              >
                <span class="material-symbols-outlined text-sm">play_arrow</span>
                {{ t('生成初始价格表') }}
              </button>
            </div>
          </div>
        </div>
        <!-- 市场先验数据参考 -->
        <div class="col-span-12 lg:col-span-4 space-y-6">
          <h2
            class="font-headline-md text-headline-md text-on-surface border-b border-surface-variant pb-2"
          >
            {{ t('市场先验数据参考') }}
          </h2>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm"
          >
            <div class="flex justify-between items-center mb-4">
              <span class="font-label-lg text-label-lg text-on-surface">{{
                t('同城同档均价走势 (近30天)')
              }}</span>
              <span class="material-symbols-outlined text-on-surface-variant text-sm">info</span>
            </div>
            <div
              class="h-40 bg-surface-bright border border-surface-variant rounded flex items-center justify-center relative overflow-hidden"
            >
              <div
                class="absolute bottom-0 left-0 w-full h-full flex items-end px-2 gap-1 opacity-60"
              >
                <div class="w-1/6 bg-primary/20 h-[40%] rounded-t"></div>
                <div class="w-1/6 bg-primary/30 h-[45%] rounded-t"></div>
                <div class="w-1/6 bg-primary/40 h-[60%] rounded-t"></div>
                <div class="w-1/6 bg-primary/60 h-[80%] rounded-t"></div>
                <div class="w-1/6 bg-primary/50 h-[70%] rounded-t"></div>
                <div class="w-1/6 bg-primary/80 h-[90%] rounded-t"></div>
              </div>
              <div class="z-10 flex flex-col items-center">
                <span class="font-num-xl text-num-xl text-primary">¥385</span>
                <span class="text-xs text-on-surface-variant">{{ t('平均基础价格') }}</span>
              </div>
            </div>
          </div>
          <!-- 首日定价模拟预览（数据驱动：demo('rate')） -->
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-[0_4px_12px_rgba(0,0,0,0.03)] border-l-2 border-l-tertiary"
          >
            <div class="flex justify-between items-start mb-3">
              <div class="flex items-center gap-2">
                <span
                  class="material-symbols-outlined text-tertiary text-sm"
                  style="font-variation-settings: 'FILL' 1"
                  >science</span
                >
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('首日定价模拟预览')
                }}</span>
              </div>
              <span
                class="bg-surface-variant text-on-surface-variant px-2 py-0.5 rounded text-[10px] font-bold border border-outline-variant flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-[10px]">warning</span>
                {{ t('置信度: 低') }}</span
              >
            </div>
            <div class="space-y-3">
              <div
                v-for="r in preview()"
                :key="r.id"
                class="flex justify-between items-center py-2 border-b border-surface-variant"
              >
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ r.room_type }}</div>
                  <div class="text-xs text-tertiary flex items-center gap-1 mt-0.5">
                    <span class="material-symbols-outlined text-[12px]">ac_unit</span>
                    {{ t('冷启动建议') }}
                  </div>
                </div>
                <div class="text-right">
                  <div class="font-num-md text-num-md text-on-surface">
                    {{ fmt(r.suggested_price) }}
                  </div>
                </div>
              </div>
              <div
                v-if="!preview().length"
                class="py-4 text-center text-on-surface-variant text-sm"
              >
                {{ t('暂无模拟数据') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
