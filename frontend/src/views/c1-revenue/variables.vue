<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 收益模拟与压力测试 (What-if)：调节变量 + 影响预测 + 风险警告
// 长尾域：api.demo('yield') 渲染预测柱状图（predicted_occ 高度）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const yields = ref<any[]>([])
onMounted(async () => {
  yields.value = await api.demo('yield')
})
// 预测入住率转数字（去 %）
function occNum(y: any) {
  return Number(String(y.predicted_occ || '0').replace('%', ''))
}
</script>

<template>
  <div class="page">
    <div class="max-w-[1440px] mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-end mb-6">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
            {{ t('收益模拟与压力测试') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">
            What-if Analysis &amp; Stress Testing Lab
          </p>
        </div>
        <div class="flex gap-4">
          <button
            class="font-label-lg text-label-lg bg-surface-container-high text-on-surface px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-surface-container-highest transition"
          >
            <span class="material-symbols-outlined text-[18px]">history</span> {{ t('历史记录') }}
          </button>
          <button
            class="font-label-lg text-label-lg bg-primary text-on-primary px-4 py-2 rounded-lg flex items-center gap-2 shadow-[0_4px_12px_rgba(26,115,232,0.2)] hover:bg-surface-tint transition"
          >
            <span class="material-symbols-outlined text-[18px]">save</span> {{ t('保存方案') }}
          </button>
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- 左列：变量 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-4">
          <div class="bg-[#f0f4ff] border-l-4 border-primary rounded-r-xl p-4 flex gap-3 shadow-sm">
            <span class="material-symbols-outlined text-primary mt-0.5 icon-fill"
              >auto_awesome</span
            >
            <div>
              <h3 class="font-headline-md text-headline-md text-primary mb-1">
                {{ t('AI 市场预测') }}
              </h3>
              <p class="font-body-md text-body-md text-on-surface-variant">
                {{
                  t('预计下周受暴雨影响，本地旅游需求将下降 15%-20%。建议提前进行降价压力测试。')
                }}
              </p>
            </div>
          </div>
          <div
            class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col gap-6 flex-1"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-secondary">tune</span>
              {{ t('调节变量 (Variables)') }}
            </h2>
            <div>
              <div class="flex justify-between mb-2">
                <label class="font-label-lg text-label-lg text-on-surface font-semibold">{{
                  t('市场需求 (Market Demand)')
                }}</label>
                <span class="font-num-md text-num-md text-primary">-20%</span>
              </div>
              <input
                class="w-full h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer"
                max="50"
                min="-50"
                type="range"
                value="-20"
              />
              <div class="flex justify-between mt-1 text-[12px] text-outline">
                <span>-50%</span><span>0%</span><span>+50%</span>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-2">
                <label class="font-label-lg text-label-lg text-on-surface font-semibold">{{
                  t('竞争对手B降价 (Comp B Price)')
                }}</label>
                <span class="font-num-md text-num-md text-primary">-15%</span>
              </div>
              <input
                class="w-full h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer"
                max="30"
                min="-30"
                type="range"
                value="-15"
              />
            </div>
            <div>
              <div class="flex justify-between mb-2">
                <label class="font-label-lg text-label-lg text-on-surface font-semibold">{{
                  t('本酒店基础房价调整 (Our ADR)')
                }}</label>
                <span class="font-num-md text-num-md text-primary">-5%</span>
              </div>
              <input
                class="w-full h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer"
                max="30"
                min="-30"
                type="range"
                value="-5"
              />
            </div>
            <hr class="border-surface-container-high my-2" />
            <div class="flex gap-3">
              <button
                class="flex-1 py-2 border border-outline-variant rounded-lg font-label-lg text-on-surface hover:bg-surface-container-low transition"
              >
                {{ t('重置') }}
              </button>
              <button
                class="flex-1 py-2 bg-primary-container text-on-primary-container rounded-lg font-label-lg font-semibold hover:bg-[#004bb0] transition shadow-sm"
              >
                {{ t('应用模拟') }}
              </button>
            </div>
          </div>
        </div>
        <!-- 右列：预测与风险 -->
        <div class="col-span-12 lg:col-span-8 flex flex-col gap-4">
          <div
            class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col h-[400px]"
          >
            <div class="flex justify-between items-center mb-6">
              <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-secondary">monitoring</span>
                {{ t('影响预测 (Impact Forecast)') }}
              </h2>
              <div class="flex gap-2">
                <span class="flex items-center gap-1 font-label-lg text-[12px]"
                  ><div class="w-3 h-3 rounded-full bg-outline-variant"></div>
                  {{ t('当前基准线') }}</span
                >
                <span class="flex items-center gap-1 font-label-lg text-[12px]"
                  ><div class="w-3 h-3 rounded-full bg-primary"></div>
                  {{ t('模拟结果') }}</span
                >
              </div>
            </div>
            <div class="grid grid-cols-3 gap-4 mb-6">
              <div class="bg-surface p-4 rounded-lg border border-surface-container-high">
                <p class="font-label-lg text-outline mb-1">{{ t('预计 RevPAR') }}</p>
                <div class="flex items-end gap-2">
                  <span class="font-num-xl text-num-xl text-on-surface">¥315</span
                  ><span class="font-num-md text-error text-[14px] flex items-center"
                    ><span class="material-symbols-outlined text-[16px]">trending_down</span>
                    -12%</span
                  >
                </div>
              </div>
              <div class="bg-surface p-4 rounded-lg border border-surface-container-high">
                <p class="font-label-lg text-outline mb-1">{{ t('预计入住率 (OCC)') }}</p>
                <div class="flex items-end gap-2">
                  <span class="font-num-xl text-num-xl text-on-surface">68%</span
                  ><span class="font-num-md text-error text-[14px] flex items-center"
                    ><span class="material-symbols-outlined text-[16px]">trending_down</span>
                    -8%</span
                  >
                </div>
              </div>
              <div class="bg-surface p-4 rounded-lg border border-surface-container-high">
                <p class="font-label-lg text-outline mb-1">{{ t('总收入 (Total Rev)') }}</p>
                <div class="flex items-end gap-2">
                  <span class="font-num-xl text-num-xl text-on-surface">¥42,500</span
                  ><span class="font-num-md text-error text-[14px] flex items-center"
                    ><span class="material-symbols-outlined text-[16px]">trending_down</span>
                    -15%</span
                  >
                </div>
              </div>
            </div>
            <!-- 预测柱状图（数据驱动：demo('yield') predicted_occ） -->
            <div
              class="flex-1 bg-surface-container-lowest relative border-b-2 border-l-2 border-surface-variant flex items-end px-4 gap-4 pt-4"
            >
              <div class="w-full flex justify-around items-end h-full">
                <div
                  v-for="y in yields"
                  :key="y.id"
                  class="w-10 flex flex-col items-center justify-end h-full"
                >
                  <div
                    class="w-full bg-primary rounded-t shadow-sm"
                    :style="{ height: occNum(y) + '%' }"
                  ></div>
                  <span class="text-[10px] text-on-surface-variant mt-1">{{
                    y.date.slice(5)
                  }}</span>
                </div>
                <div v-if="!yields.length" class="w-full text-center text-on-surface-variant">
                  {{ t('加载中…') }}
                </div>
              </div>
              <div
                class="absolute top-1/4 w-full border-t border-dashed border-surface-variant z-[-1]"
              ></div>
              <div
                class="absolute top-2/4 w-full border-t border-dashed border-surface-variant z-[-1]"
              ></div>
              <div
                class="absolute top-3/4 w-full border-t border-dashed border-surface-variant z-[-1]"
              ></div>
            </div>
          </div>
          <div
            class="bg-error-container border border-[#ffb4ab] rounded-xl p-4 flex gap-3 shadow-sm items-start"
          >
            <span class="material-symbols-outlined text-on-error-container mt-0.5 icon-fill"
              >warning</span
            >
            <div class="flex-1">
              <h3 class="font-headline-md text-headline-md text-on-error-container mb-1">
                {{ t('R3 风险警告：负 ROI 风险') }}
              </h3>
              <p class="font-body-md text-body-md text-[#93000a] opacity-90 mb-3">
                {{
                  t(
                    '当前模拟情境下，若不采取额外营销动作，入住率将跌破 70% 盈亏平衡点，产生亏损风险。需要双重确认或主管授权方可将此策略应用至实盘。',
                  )
                }}
              </p>
              <div class="flex gap-3">
                <button
                  class="bg-surface-container-lowest text-[#93000a] font-label-lg px-4 py-1.5 rounded-lg border border-[#ffb4ab] hover:bg-[#ffdad6] transition"
                >
                  {{ t('查看建议缓解策略') }}
                </button>
              </div>
            </div>
          </div>
          <div class="flex gap-4 mt-2">
            <button
              class="flex-1 bg-surface-container-lowest border border-outline-variant p-4 rounded-xl flex items-center justify-between hover:border-primary transition group cursor-pointer"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-secondary group-hover:bg-primary-container group-hover:text-primary transition"
                >
                  <span class="material-symbols-outlined">shield</span>
                </div>
                <div class="text-left">
                  <div class="font-headline-md text-[16px] text-on-surface">
                    {{ t('保存方案 A (保守型)') }}
                  </div>
                  <div class="font-body-md text-[12px] text-outline">{{ t('小幅降价保底') }}</div>
                </div>
              </div>
              <span class="material-symbols-outlined text-outline-variant group-hover:text-primary"
                >arrow_forward</span
              >
            </button>
            <button
              class="flex-1 bg-surface-container-lowest border border-outline-variant p-4 rounded-xl flex items-center justify-between hover:border-primary transition group cursor-pointer"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-10 h-10 rounded-full bg-[#f8d8ff] flex items-center justify-center text-[#721199] group-hover:bg-[#a84fce] group-hover:text-white transition"
                >
                  <span class="material-symbols-outlined">bolt</span>
                </div>
                <div class="text-left">
                  <div class="font-headline-md text-[16px] text-on-surface">
                    {{ t('保存方案 B (激进型)') }}
                  </div>
                  <div class="font-body-md text-[12px] text-outline">{{ t('深度折扣抢客') }}</div>
                </div>
              </div>
              <span
                class="material-symbols-outlined text-outline-variant group-hover:text-[#8c33b3]"
                >arrow_forward</span
              >
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
