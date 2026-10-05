<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 冷启动方案（收益管理 C1）：新酒店初始定价向导 + AI 竞品基准 + 模拟定价
// 数据：api.demo('rate') 取房型作为竞品基准 (Comp Set) 列表
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const comps = ref<any[]>([])
onMounted(async () => {
  comps.value = await api.demo('rate')
})
// 由房型数据推导一个竞品均价占位
function avg(r: any) {
  return Number(r.current_price || 0)
}
function dist(i: number) {
  return [(1.2 + i * 0.5).toFixed(1)] + 'km'
}
function weight(i: number) {
  return 40 - i * 5
}
</script>

<template>
  <div class="page">
    <div class="max-w-[1200px] mx-auto">
      <div class="mb-8">
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('冷启动方案 (Cold Start Strategies)') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('配置新酒店或无历史数据房型的初始定价策略。AI 将协助建立基础模型。') }}
        </p>
      </div>
      <div class="grid grid-cols-12 gap-gutter">
        <!-- 左列：向导步骤 -->
        <div class="col-span-12 md:col-span-8 flex flex-col gap-6">
          <section
            class="bg-surface rounded-xl border border-outline-variant/60 shadow-sm p-6 relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>
            <h2
              class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
            >
              <span
                class="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-on-primary text-sm font-bold"
                >1</span
              >{{ t('模板类型选择') }}
            </h2>
            <div class="grid grid-cols-3 gap-4">
              <label class="cursor-pointer group relative">
                <input checked class="peer sr-only" name="hotel_type" type="radio" />
                <div
                  class="h-32 rounded-lg border-2 border-outline-variant peer-checked:border-primary peer-checked:bg-primary-fixed/10 p-4 flex flex-col items-center justify-center gap-2 transition-all hover:border-primary/50 bg-surface-bright"
                >
                  <span
                    class="material-symbols-outlined text-3xl text-secondary peer-checked:text-primary transition-colors"
                    >home_work</span
                  >
                  <span
                    class="font-label-lg text-label-lg text-on-surface-variant peer-checked:text-on-surface font-medium"
                    >{{ t('精品酒店 (Boutique)') }}</span
                  >
                </div>
              </label>
              <label class="cursor-pointer group relative">
                <input class="peer sr-only" name="hotel_type" type="radio" />
                <div
                  class="h-32 rounded-lg border-2 border-outline-variant peer-checked:border-primary peer-checked:bg-primary-fixed/10 p-4 flex flex-col items-center justify-center gap-2 transition-all hover:border-primary/50 bg-surface-bright"
                >
                  <span
                    class="material-symbols-outlined text-3xl text-secondary peer-checked:text-primary transition-colors"
                    >beach_access</span
                  >
                  <span
                    class="font-label-lg text-label-lg text-on-surface-variant peer-checked:text-on-surface font-medium"
                    >{{ t('度假村 (Resort)') }}</span
                  >
                </div>
              </label>
              <label class="cursor-pointer group relative">
                <input class="peer sr-only" name="hotel_type" type="radio" />
                <div
                  class="h-32 rounded-lg border-2 border-outline-variant peer-checked:border-primary peer-checked:bg-primary-fixed/10 p-4 flex flex-col items-center justify-center gap-2 transition-all hover:border-primary/50 bg-surface-bright"
                >
                  <span
                    class="material-symbols-outlined text-3xl text-secondary peer-checked:text-primary transition-colors"
                    >apartment</span
                  >
                  <span
                    class="font-label-lg text-label-lg text-on-surface-variant peer-checked:text-on-surface font-medium"
                    >{{ t('商务酒店 (Business)') }}</span
                  >
                </div>
              </label>
            </div>
          </section>

          <!-- 竞争对手基准 (v-for 绑定 demo('rate')) -->
          <section
            class="bg-surface rounded-xl border border-outline-variant/60 shadow-sm p-6 relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-surface-container-highest"></div>
            <div class="flex justify-between items-center mb-4">
              <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span
                  class="flex items-center justify-center w-6 h-6 rounded-full bg-surface-container-highest text-on-surface-variant text-sm font-bold"
                  >2</span
                >{{ t('竞争对手基准 (Comp Set)') }}
              </h2>
              <button
                class="text-primary hover:text-primary-fixed-variant font-label-lg text-label-lg flex items-center gap-1 transition-colors"
              >
                <span class="material-symbols-outlined text-[18px]">add</span> {{ t('添加对手') }}
              </button>
            </div>
            <div
              class="bg-primary-fixed/20 border-l-2 border-primary p-3 rounded-r-md mb-4 flex gap-3 items-start"
            >
              <span class="material-symbols-outlined text-primary mt-0.5">info</span>
              <div>
                <p class="font-body-md text-body-md text-on-surface">
                  {{
                    t(
                      'AI 建议: 根据您选择的“精品酒店”类型，系统已自动推荐相似定位的酒店作为价格锚点。',
                    )
                  }}
                </p>
              </div>
            </div>
            <div class="space-y-3">
              <div
                v-for="(r, i) in comps"
                :key="r.id"
                class="flex items-center justify-between p-3 border border-outline-variant/40 rounded-lg hover:bg-surface-bright transition-colors"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded bg-surface-container-high flex items-center justify-center"
                  >
                    <span class="material-symbols-outlined text-secondary">hotel</span>
                  </div>
                  <div>
                    <div class="font-label-lg text-label-lg text-on-surface font-medium">
                      {{ r.room_type || t('竞品酒店') }}
                    </div>
                    <div
                      class="font-body-md text-body-md text-on-surface-variant text-sm flex gap-2"
                    >
                      <span>{{ t('距离') }} {{ dist(i) }}</span
                      ><span class="text-outline">•</span>
                      <span
                        >{{ t('基础房型均价:') }} <span class="num">¥{{ avg(r) }}</span></span
                      >
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-2">
                    <span class="text-sm text-on-surface-variant">{{ t('权重') }}</span
                    ><input
                      class="w-16 h-8 text-center border-outline-variant rounded-md num text-sm focus:border-primary focus:ring-primary"
                      type="number"
                      :value="weight(i)"
                    /><span class="text-sm text-on-surface-variant">%</span>
                  </div>
                  <button class="text-outline hover:text-error transition-colors">
                    <span class="material-symbols-outlined text-[20px]">delete</span>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section
            class="bg-surface rounded-xl border border-outline-variant/60 shadow-sm p-6 relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-surface-container-highest"></div>
            <h2
              class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
            >
              <span
                class="flex items-center justify-center w-6 h-6 rounded-full bg-surface-container-highest text-on-surface-variant text-sm font-bold"
                >3</span
              >{{ t('初始参数微调') }}
            </h2>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                  t('目标入住率 (Target OCC)')
                }}</label>
                <div class="relative">
                  <input
                    class="w-full h-2 bg-surface-container-high rounded-lg appearance-none cursor-pointer accent-primary"
                    max="100"
                    min="0"
                    type="range"
                    value="65"
                  />
                  <div class="mt-2 text-right num font-medium text-primary">65%</div>
                </div>
              </div>
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                  t('新店折扣策略 (Opening Promo)')
                }}</label>
                <select
                  class="w-full h-10 border-outline-variant rounded-md text-body-md focus:border-primary focus:ring-primary"
                >
                  <option value="aggressive">{{ t('激进: 首月 8 折抢占市场') }}</option>
                  <option selected value="moderate">{{ t('稳健: 首月 9 折平稳过渡') }}</option>
                  <option value="conservative">{{ t('保守: 原价，依市场反应调整') }}</option>
                </select>
              </div>
            </div>
          </section>
        </div>

        <!-- 右列：AI 模拟 -->
        <div class="col-span-12 md:col-span-4 flex flex-col gap-6">
          <div
            class="bg-surface rounded-xl border border-outline-variant/60 shadow-sm overflow-hidden flex flex-col"
          >
            <div
              class="p-5 border-b border-outline-variant/40 bg-surface-bright flex justify-between items-center"
            >
              <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-tertiary-container">model_training</span
                >{{ t('模拟初始定价') }}
              </h3>
              <div
                class="px-2 py-1 rounded bg-tertiary-fixed text-on-tertiary-fixed-variant text-xs font-bold uppercase tracking-wider flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
                {{ t('AI 推演中') }}
              </div>
            </div>
            <div class="p-6 flex-1 flex flex-col items-center justify-center min-h-[200px]">
              <div class="text-sm text-on-surface-variant mb-2">{{ t('建议基准价 (BAR)') }}</div>
              <div class="font-display-lg text-display-lg text-primary flex items-baseline gap-1">
                <span class="text-2xl font-medium">¥</span
                ><span class="num text-5xl">{{
                  comps.length
                    ? Math.round(comps.reduce((s: number, r: any) => s + avg(r), 0) / comps.length)
                    : 598
                }}</span>
              </div>
              <div
                class="mt-4 px-4 py-2 rounded-full bg-surface-container-low border border-outline-variant/30 text-sm text-on-surface-variant flex items-center gap-2"
              >
                <span class="w-2 h-2 rounded-full bg-green-600"></span> {{ t('预期 RevPAR:') }}
                <span class="num font-medium text-on-surface">¥388</span>
              </div>
            </div>
          </div>
          <div class="bg-surface rounded-xl border border-outline-variant/60 shadow-sm p-5">
            <h4 class="font-label-lg text-label-lg font-bold text-on-surface mb-4">
              {{ t('AI 价格推导路径') }}
            </h4>
            <div class="relative pl-4 space-y-6">
              <div class="absolute left-[7px] top-2 bottom-2 w-0.5 bg-surface-container-high"></div>
              <div class="relative pl-6">
                <div
                  class="absolute left-[-5px] top-1 w-3 h-3 rounded-full bg-primary ring-4 ring-surface"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('竞品均价计算') }}
                </div>
                <div class="text-sm text-on-surface-variant mt-1 num">
                  {{ t('基础均价: ¥595') }}
                </div>
              </div>
              <div class="relative pl-6">
                <div
                  class="absolute left-[-5px] top-1 w-3 h-3 rounded-full bg-primary ring-4 ring-surface"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('设施溢价调整') }}
                </div>
                <div class="text-sm text-on-surface-variant mt-1">
                  {{ t('基于新装修及智能设备') }}
                  <span class="text-primary font-medium num">+¥65</span>
                </div>
              </div>
              <div class="relative pl-6">
                <div
                  class="absolute left-[-5px] top-1 w-3 h-3 rounded-full bg-tertiary-container ring-4 ring-surface shadow-[0_0_8px_rgba(168,79,206,0.5)]"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('冷启动折扣应用') }}
                </div>
                <div class="text-sm text-on-surface-variant mt-1">
                  {{ t('稳健策略 (9折)') }} <span class="text-error font-medium num">-¥62</span>
                </div>
                <div
                  class="mt-2 p-2 rounded bg-tertiary-fixed/30 border border-tertiary-container/20 text-xs text-on-tertiary-container"
                >
                  <strong>{{ t('AI 解释:') }}</strong>
                  {{ t('新店首月需通过略低于溢价的终端价格积累初始流量和评价。') }}
                </div>
              </div>
            </div>
          </div>
          <div class="flex gap-3 mt-auto">
            <button
              class="flex-1 py-3 px-4 rounded-lg border border-outline-variant text-on-surface font-label-lg font-medium hover:bg-surface-container-low transition-colors text-center"
            >
              {{ t('保存草稿') }}
            </button>
            <button
              class="flex-[2] py-3 px-4 rounded-lg bg-primary text-on-primary font-label-lg font-medium hover:bg-primary-fixed-variant transition-colors shadow-sm text-center flex justify-center items-center gap-2"
            >
              <span class="material-symbols-outlined text-[18px]">rocket_launch</span
              >{{ t('应用冷启动方案') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
