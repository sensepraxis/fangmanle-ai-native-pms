<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 3D 场地布局方案生成器（C10 多形态 · MICE 宴会）
// 左侧为方案参数配置，右侧为 AI 推荐方案（含 3D 布局 / 人员 / 菜单 / 财务）。
// 数据：api.demo('mice') 取近期 MICE 活动，用于头部「参考活动」上下文。
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const events = ref<any[]>([])
onMounted(async () => {
  events.value = await api.demo('mice')
})
// 参考活动：取最近一条 MICE 活动作为方案生成的输入上下文
function refEvent() {
  return events.value[0] || null
}
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto flex flex-col lg:flex-row gap-gutter">
      <!-- 左栏：方案参数设定 -->
      <div class="w-full lg:w-1/3 flex flex-col gap-6">
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm relative overflow-hidden"
        >
          <div
            class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-tertiary"
          ></div>
          <h2 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary">tune</span>
            {{ t('方案参数设定') }}
          </h2>
          <!-- 参考活动上下文（绑定 mice 第一条） -->
          <div
            v-if="refEvent()"
            class="mb-5 p-3 rounded-lg bg-primary-fixed/20 border border-primary-fixed-dim text-sm text-on-surface"
          >
            {{ t('AI 将基于近期活动') }} <span class="font-bold">{{ refEvent().event }}</span
            >（{{ refEvent().space }} · {{ refEvent().pax }}{{ t('人）生成方案') }}
          </div>
          <form class="flex flex-col gap-5">
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
                t('宴会类型')
              }}</label>
              <select
                class="w-full rounded-lg border-outline-variant bg-surface-container-low text-on-surface focus:border-primary focus:ring-primary"
              >
                <option>{{ t('企业年会 (Corporate Gala)') }}</option>
                <option>{{ t('婚宴 (Wedding Reception)') }}</option>
                <option>{{ t('生日派对 (Birthday Party)') }}</option>
                <option>{{ t('产品发布会 (Product Launch)') }}</option>
              </select>
            </div>
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
                t('预计人数 (Guest Count)')
              }}</label>
              <div class="flex items-center">
                <input
                  class="w-full rounded-lg border-outline-variant bg-surface-container-low text-on-surface font-num-md focus:border-primary focus:ring-primary"
                  type="number"
                  :value="refEvent() ? refEvent().pax : 150"
                />
                <span class="ml-2 text-on-surface-variant">{{ t('人') }}</span>
              </div>
            </div>
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
                t('单人预算 (Budget/Pax)')
              }}</label>
              <div class="relative">
                <span class="absolute left-3 top-2 text-on-surface-variant">¥</span>
                <input
                  class="w-full pl-8 rounded-lg border-outline-variant bg-surface-container-low text-on-surface font-num-md focus:border-primary focus:ring-primary"
                  type="number"
                  value="880"
                />
              </div>
            </div>
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface-variant mb-2">{{
                t('饮食偏好 (Dietary Needs)')
              }}</label>
              <div class="flex flex-wrap gap-2">
                <label
                  class="flex items-center space-x-2 bg-surface-variant px-3 py-1.5 rounded-full cursor-pointer hover:bg-secondary-container"
                >
                  <input
                    checked
                    class="rounded text-primary focus:ring-primary border-outline"
                    type="checkbox"
                  />
                  <span class="font-label-lg text-label-lg text-on-surface">{{
                    t('素食友好 (Vegetarian)')
                  }}</span>
                </label>
                <label
                  class="flex items-center space-x-2 bg-surface-variant px-3 py-1.5 rounded-full cursor-pointer hover:bg-secondary-container"
                >
                  <input
                    class="rounded text-primary focus:ring-primary border-outline"
                    type="checkbox"
                  />
                  <span class="font-label-lg text-label-lg text-on-surface">{{
                    t('清真 (Halal)')
                  }}</span>
                </label>
              </div>
            </div>
            <button
              class="mt-4 w-full bg-primary text-on-primary font-label-lg text-label-lg py-3 rounded-full hover:bg-primary-fixed-variant transition-colors flex items-center justify-center gap-2"
              type="button"
            >
              <span class="material-symbols-outlined">auto_awesome</span>
              {{ t('使用 AI 生成方案 (Generate with AI)') }}
            </button>
          </form>
        </div>
        <!-- 库存预警（护栏 R1） -->
        <div
          class="bg-error-container rounded-xl p-4 border border-yellow-400 flex gap-3 items-start"
        >
          <span class="material-symbols-outlined text-error mt-0.5">warning</span>
          <div>
            <h4 class="font-label-lg text-label-lg text-error font-bold">{{ t('库存预警') }}</h4>
            <p class="font-body-md text-body-md text-on-surface mt-1 text-sm">
              {{ t('提议日期波士顿龙虾库存不足。') }}<br />
              <span class="text-tertiary font-medium">{{ t('AI 建议:') }}</span>
              {{ t('替换为可持续养殖大虾，保持利润率。') }}
            </p>
          </div>
        </div>
      </div>

      <!-- 右栏：AI 推荐方案 -->
      <div class="w-full lg:w-2/3 flex flex-col gap-6">
        <div
          class="bg-surface-container-lowest rounded-xl p-0 border border-outline-variant shadow-sm overflow-hidden flex flex-col h-full ai-border-highlight"
        >
          <div
            class="bg-surface-container-low px-6 py-4 border-b border-outline-variant flex justify-between items-center"
          >
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-tertiary">psychology</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('AI 推荐方案方案 A') }}
              </h2>
              <span
                class="bg-tertiary-fixed text-on-tertiary-fixed text-xs px-2 py-0.5 rounded-full font-medium ml-2"
                >{{ t('98% 匹配度') }}</span
              >
            </div>
            <div class="flex gap-2">
              <button
                class="p-2 text-on-surface-variant hover:bg-surface-variant rounded-full transition-colors"
                :title="t('导出 PDF')"
              >
                <span class="material-symbols-outlined">download</span>
              </button>
              <button
                class="p-2 text-primary hover:bg-primary-fixed rounded-full transition-colors flex items-center gap-1"
              >
                <span class="material-symbols-outlined">refresh</span>
                <span class="font-label-lg text-sm hidden md:inline">{{ t('换一换') }}</span>
              </button>
            </div>
          </div>
          <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 flex-1">
            <!-- 3D 布局 -->
            <div class="flex flex-col">
              <h3
                class="font-label-lg text-label-lg text-on-surface-variant mb-2 flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">view_in_ar</span>
                {{ t('场地布局 (3D Layout)') }}
              </h3>
              <div
                class="relative w-full h-48 bg-surface-variant rounded-lg overflow-hidden border border-outline-variant"
              >
                <img
                  class="w-full h-full object-cover"
                  :alt="t('3D 宴会厅布局')"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuDKNjvP38VmZKMt9rytUMPNTjaLH2Ee269BILP-Z0osNGuunAWxTy6Lrle2Tbk7tZjzkDOFzQyBSpFmgkFfCCgZEQ7iDG_8RIEfIRSfETdzxskPnacXdmfRf8kreh674TIGJMF_UMzJfhhAc_HxPXSOQ-OGJgI4OzbdAWw6LrZFOlXulLke5V0kJWgGdb0tU_qPhfgxRKrGkvhJ2ZamEA7hkm6n15nH7GKp99bzAsa3WYuefvMWTa4"
                />
                <div
                  class="absolute bottom-2 right-2 bg-background/80 backdrop-blur px-2 py-1 rounded text-xs font-num-md text-on-surface shadow"
                >
                  {{ t('大宴会厅 A (800平)') }}
                </div>
              </div>
            </div>
            <!-- 人员配置 -->
            <div class="flex flex-col">
              <h3
                class="font-label-lg text-label-lg text-on-surface-variant mb-2 flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">groups</span>
                {{ t('人员配置 (Staffing Plan)') }}
              </h3>
              <div
                class="bg-surface p-4 rounded-lg border border-outline-variant h-48 overflow-y-auto"
              >
                <ul class="space-y-3">
                  <li class="flex justify-between items-center">
                    <span class="font-body-md text-body-md text-on-surface">{{
                      t('服务主管')
                    }}</span>
                    <span
                      class="font-num-md text-num-md text-primary bg-primary-fixed px-2 py-0.5 rounded"
                      >{{ t('2 人') }}</span
                    >
                  </li>
                  <li class="flex justify-between items-center">
                    <span class="font-body-md text-body-md text-on-surface">{{
                      t('全职侍者')
                    }}</span>
                    <span
                      class="font-num-md text-num-md text-primary bg-primary-fixed px-2 py-0.5 rounded"
                      >{{ t('12 人 (1:12 比例)') }}</span
                    >
                  </li>
                  <li class="flex justify-between items-center">
                    <span class="font-body-md text-body-md text-on-surface">{{
                      t('兼职协助')
                    }}</span>
                    <span
                      class="font-num-md text-num-md text-secondary bg-secondary-container px-2 py-0.5 rounded"
                      >{{ t('4 人') }}</span
                    >
                  </li>
                </ul>
              </div>
            </div>
            <!-- 推荐菜单（跨整行） -->
            <div class="md:col-span-2">
              <h3
                class="font-label-lg text-label-lg text-on-surface-variant mb-2 flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">restaurant_menu</span>
                {{ t('推荐菜单 (Catering Menu)') }}
              </h3>
              <div class="bg-surface rounded-lg border border-outline-variant p-4">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <h4
                      class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2"
                    >
                      {{ t('前菜') }}
                    </h4>
                    <p class="font-body-md text-sm text-on-surface">
                      {{ t('黑松露菌菇汤') }}<br />{{ t('烟熏三文鱼配鱼子酱') }}
                    </p>
                  </div>
                  <div>
                    <h4
                      class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2"
                    >
                      {{ t('主菜') }}
                    </h4>
                    <p class="font-body-md text-sm text-on-surface">
                      {{ t('慢烤澳洲M3和牛排') }}<br />{{ t('清蒸东星斑 (调整)') }}
                    </p>
                  </div>
                  <div>
                    <h4
                      class="text-xs font-bold text-tertiary uppercase tracking-wider mb-2 flex items-center"
                    >
                      <span class="material-symbols-outlined text-[14px] mr-1">spa</span
                      >{{ t('素食特供') }}
                    </h4>
                    <p class="font-body-md text-sm text-on-surface">
                      {{ t('香煎牛肝菌配芦笋') }}<br />{{ t('松露野菌意大利烩饭') }}
                    </p>
                  </div>
                  <div>
                    <h4
                      class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2"
                    >
                      {{ t('甜点') }}
                    </h4>
                    <p class="font-body-md text-sm text-on-surface">
                      {{ t('法式焦糖布丁') }}<br />{{ t('时令鲜果拼盘') }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <!-- 财务 / 底部 -->
          <div
            class="bg-primary-fixed/20 border-t border-outline-variant p-6 flex flex-col md:flex-row justify-between items-center gap-4"
          >
            <div class="flex gap-8">
              <div>
                <p class="font-label-lg text-xs text-on-surface-variant">{{ t('预计总成本') }}</p>
                <p class="font-num-xl text-num-xl text-on-surface">¥ 82,500</p>
              </div>
              <div>
                <p class="font-label-lg text-xs text-on-surface-variant">{{ t('人均成本') }}</p>
                <p class="font-num-xl text-num-xl text-on-surface">¥ 550</p>
              </div>
              <div class="pl-4 border-l border-outline-variant">
                <p class="font-label-lg text-xs text-tertiary font-bold flex items-center">
                  <span class="material-symbols-outlined text-[14px] mr-1">trending_up</span
                  >{{ t('预估利润率') }}
                </p>
                <p class="font-num-xl text-num-xl text-tertiary">37.5%</p>
              </div>
            </div>
            <button
              class="bg-primary text-on-primary px-6 py-2 rounded-full font-label-lg text-label-lg hover:bg-primary-fixed-variant transition-colors shadow-sm"
            >
              {{ t('采纳此方案 (Approve)') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
