<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 常住客长住阶梯价（时长折扣）—— 与协议客「企业量价阶梯」区分
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const autoApply = ref(true)

// 阶梯规则（入住天数 → 折扣力度）—— 常住客定价驱动：时长折扣
const rules = ref<any[]>([
  { id: 1, days: '7 - 14', pct: 15, ai: false },
  { id: 2, days: '15 - 30', pct: 25, ai: false },
  { id: 3, days: '30+', pct: 35, ai: true },
])

onMounted(async () => {
  try {
    await api.demo('ai-engine')
  } catch (e) {}
})
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end mb-8 flex-wrap gap-3">
      <div>
        <h1 class="font-headline-lg text-headline-lg text-on-surface mb-2">
          {{ t('常住客 · 长住阶梯价') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('按时长折扣（住得越久单价越低）。企业协议价 / 挂账请走「协议企业」工作台。') }}
        </p>
      </div>
      <div class="flex flex-col items-end gap-3">
        <OrdersFlowNav mode="longstay" hide-back />
        <div
          class="flex items-center gap-4 bg-surface-container-low p-2 pr-4 rounded-full border border-outline-variant"
        >
          <label class="relative inline-flex items-center cursor-pointer ml-2">
            <input v-model="autoApply" type="checkbox" class="sr-only peer" />
            <div
              class="w-11 h-6 bg-surface-variant peer-checked:bg-primary-container rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"
            ></div>
          </label>
          <span class="font-label-lg text-label-lg text-on-surface"
            >Auto-apply AI Recommended Rates</span
          >
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <div
        class="col-span-12 border rounded-xl p-4 flex gap-4 items-start"
        style="background: rgba(26, 115, 232, 0.08); border-color: #1a73e8"
      >
        <div class="p-2 bg-primary-container text-on-primary-container rounded-full shrink-0">
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
            >lightbulb</span
          >
        </div>
        <div class="flex-1 pt-1">
          <h3 class="font-label-lg text-label-lg text-primary mb-1">{{ t('AI 市场洞察') }}</h3>
          <p class="font-body-md text-body-md text-on-surface">
            {{ t('基于近期竞对数据分析，将 30 天以上长住折扣调整为') }}
            <strong class="text-tertiary">35%</strong>{{ t('，预计可提升整体入住率') }}
            <strong class="text-tertiary">22%</strong>。
          </p>
        </div>
        <button
          class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-primary/90 transition-colors"
        >
          {{ t('应用建议') }}
        </button>
      </div>

      <div
        class="col-span-12 lg:col-span-7 bg-surface rounded-xl shadow-sm border border-outline-variant p-6 relative overflow-hidden"
      >
        <div
          class="absolute top-0 right-0 w-32 h-32 bg-primary-fixed/20 rounded-bl-full -z-10"
        ></div>
        <h2 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">rule</span>
          {{ t('基础长住规则设置') }}
        </h2>
        <div class="space-y-4">
          <div
            v-for="r in rules"
            :key="r.id"
            class="flex items-center gap-4 p-4 rounded-lg border"
            :class="
              r.ai
                ? 'bg-tertiary-fixed/20 border-2 border-tertiary/30'
                : 'bg-background border-surface-variant'
            "
          >
            <div class="flex-1 grid grid-cols-3 gap-4 items-center">
              <div class="col-span-1">
                <span class="font-label-lg text-label-lg text-on-surface-variant block mb-1">{{
                  t('入住天数')
                }}</span>
                <div class="flex items-center gap-2">
                  <span class="font-num-md text-num-md text-on-surface">{{ r.days }}}</span
                  ><span class="font-body-md text-body-md text-on-surface-variant">{{
                    t('天')
                  }}</span>
                </div>
              </div>
              <div class="col-span-2">
                <span
                  class="font-label-lg text-label-lg block mb-1"
                  :class="
                    r.ai ? 'text-tertiary flex items-center gap-1' : 'text-on-surface-variant'
                  "
                >
                  <span v-if="r.ai" class="material-symbols-outlined text-[14px]"
                    >auto_awesome</span
                  >
                  {{ r.ai ? t('建议折扣区') : t('折扣力度') }}</span
                >
                <div class="flex items-center gap-3">
                  <input
                    v-model.number="r.pct"
                    type="range"
                    min="0"
                    max="50"
                    class="w-full h-2 bg-surface-variant rounded-lg appearance-none cursor-pointer"
                  />
                  <div
                    class="w-16 h-10 border border-outline-variant rounded bg-surface flex items-center justify-center font-num-md text-num-md"
                    :class="r.ai ? 'text-tertiary font-bold border-tertiary/50' : ''"
                  >
                    {{ r.pct }}%
                  </div>
                </div>
              </div>
            </div>
            <button class="text-on-surface-variant hover:text-error transition-colors p-2">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
        <button
          class="mt-4 flex items-center justify-center w-full gap-2 py-3 border border-dashed border-outline-variant rounded-lg text-primary hover:bg-primary-fixed-dim/10 transition-colors font-label-lg"
        >
          <span class="material-symbols-outlined">add</span> {{ t('添加阶梯规则') }}
        </button>
      </div>

      <div
        class="col-span-12 lg:col-span-5 bg-surface rounded-xl shadow-sm border border-outline-variant p-6 flex flex-col"
      >
        <h2 class="font-headline-md text-headline-md text-on-surface mb-2 flex items-center gap-2">
          <span class="material-symbols-outlined text-secondary">monitoring</span>
          {{ t('天数与折扣关系模型') }}
        </h2>
        <p class="font-body-md text-body-md text-on-surface-variant mb-6">
          {{ t('直观展示入住时长对最终均价的影响（常住客）。') }}
        </p>
        <div
          class="flex-1 bg-surface-container-lowest border border-outline-variant rounded-lg relative overflow-hidden flex items-end p-4 pt-10"
        >
          <div class="absolute top-4 right-4 flex gap-3 text-xs">
            <div class="flex items-center gap-1">
              <div class="w-2 h-2 rounded-full bg-surface-variant"></div>
              <span class="text-on-surface-variant">{{ t('当前设定') }}</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="w-2 h-2 rounded-full bg-tertiary"></div>
              <span class="text-tertiary">{{ t('AI 建议区间') }}</span>
            </div>
          </div>
          <div
            class="absolute left-2 top-10 bottom-8 flex flex-col justify-between text-xs text-on-surface-variant font-num-md"
          >
            <span>50%</span><span>25%</span><span>0%</span>
          </div>
          <div
            class="w-full h-full ml-6 border-l border-b border-surface-variant relative flex items-end justify-between px-2 pb-1"
          >
            <div
              v-for="r in rules"
              :key="r.id"
              class="w-1/4 rounded-t-sm relative group cursor-pointer transition-all hover:opacity-90"
              :class="r.ai ? 'bg-tertiary/40 border border-tertiary/50' : 'bg-primary-container/40'"
              :style="{ height: r.pct * 2 + '%' }"
            >
              <div
                class="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 bg-inverse-surface text-inverse-on-surface text-xs py-1 px-2 rounded font-num-md transition-opacity"
              >
                {{ r.pct }}%
              </div>
            </div>
          </div>
          <div
            class="absolute bottom-1 left-8 right-2 flex justify-between text-xs text-on-surface-variant font-num-md px-2"
          >
            <span>{{ t('7天') }}</span
            ><span>{{ t('15天') }}</span
            ><span>{{ t('30天+') }}</span>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="px-6 py-2 border border-outline text-on-surface font-label-lg rounded-full hover:bg-surface-container-low transition-colors"
          >
            {{ t('重置') }}
          </button>
          <button
            class="px-6 py-2 bg-primary text-on-primary font-label-lg rounded-full hover:bg-primary/90 transition-colors shadow-sm"
          >
            {{ t('保存配置') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
