<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 风险因子监测配置 (NL Command)：自然语言规则创建器 + 标准数据源监测
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

const counts = ref({ high: 0, mid: 0, low: 0, open: 0, total: 0 })

async function load() {
  try {
    const board = await api.riskBoard(hotelStore.hotelId)
    counts.value = {
      high: Number(board?.counts?.high || 0),
      mid: Number(board?.counts?.mid || 0),
      low: Number(board?.counts?.low || 0),
      open: Number(board?.counts?.open || 0),
      total: Number(board?.counts?.total || 0),
    }
  } catch {
    counts.value = { high: 0, mid: 0, low: 0, open: 0, total: 0 }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto pb-12">
      <!-- 页头 -->
      <div class="mb-8 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background mb-2">
            {{ t('风险因子监测配置') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
            {{
              t(
                '定义和管理可能影响酒店运营和定价策略的外部及内部风险触发条件。AI将持续监控这些因子并提供实时预警。',
              )
            }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2 justify-end">
          <button
            type="button"
            class="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low"
            @click="router.push('/c2-risk/black-swan-warning')"
          >
            {{ t('← 返回预警台') }}
          </button>
          <button
            class="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-primary-fixed-variant transition-colors shadow-sm"
          >
            <span class="material-symbols-outlined text-[20px]">save</span>
            {{ t('保存配置') }}
          </button>
        </div>
      </div>

      <!-- 实时预警计数（来自 riskBoard） -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-gutter mb-8">
        <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
          <div class="font-label-lg text-label-lg text-on-surface-variant mb-1">
            {{ t('开放高风险') }}
          </div>
          <div class="font-num-xl text-num-xl text-error font-bold">{{ counts.high }}</div>
        </div>
        <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
          <div class="font-label-lg text-label-lg text-on-surface-variant mb-1">
            {{ t('开放中风险') }}
          </div>
          <div class="font-num-xl text-num-xl text-orange-600 font-bold">{{ counts.mid }}</div>
        </div>
        <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
          <div class="font-label-lg text-label-lg text-on-surface-variant mb-1">
            {{ t('开放低风险') }}
          </div>
          <div class="font-num-xl text-num-xl text-on-surface font-bold">{{ counts.low }}</div>
        </div>
        <div class="bg-surface-container-lowest rounded-xl border border-outline-variant p-4">
          <div class="font-label-lg text-label-lg text-on-surface-variant mb-1">
            {{ t('开放 / 总计') }}
          </div>
          <div class="font-num-xl text-num-xl text-primary font-bold">
            {{ counts.open }} / {{ counts.total }}
          </div>
        </div>
      </div>

      <!-- NL 规则创建器 -->
      <div
        class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 mb-8 ai-glow ai-tinge relative overflow-hidden"
      >
        <div class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
          <span class="material-symbols-outlined text-9xl text-tertiary">psychology</span>
        </div>
        <div class="relative z-10">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-tertiary">smart_toy</span>
            <h2 class="font-headline-md text-headline-md text-on-background">
              {{ t('自然语言规则创建器 (NL Command)') }}
            </h2>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-4">
            {{ t('使用自然语言描述您想要监控的复杂场景。AI会自动解析并创建监控规则。') }}
          </p>
          <div class="flex gap-4 items-start">
            <div class="flex-1 relative">
              <textarea
                class="w-full bg-surface-bright border border-outline-variant rounded-lg p-4 font-body-md text-body-md text-on-surface placeholder-on-surface-variant focus:outline-none focus:ring-2 focus:ring-tertiary focus:border-tertiary resize-none"
                :placeholder="
                  t(
                    '例如：如果主要竞争对手A的价格在晚上8点后突然下降超过200元，并且我们当前的入住率低于40%，请立即发送红色预警并建议降价策略。',
                  )
                "
                rows="3"
              ></textarea>
            </div>
            <button
              class="bg-tertiary text-on-tertiary px-6 py-3 rounded-lg font-label-lg text-label-lg flex items-center gap-2 hover:bg-tertiary-container hover:text-on-tertiary-container transition-colors shadow-sm h-fit"
            >
              <span class="material-symbols-outlined">auto_awesome</span>
              {{ t('解析生成规则') }}
            </button>
          </div>
        </div>
      </div>
      <!-- 标准数据源监测 -->
      <div class="mb-4 flex items-center gap-2">
        <span class="material-symbols-outlined text-on-surface-variant">monitoring</span>
        <h3 class="font-headline-md text-headline-md text-on-background">
          {{ t('标准数据源监测 (Data Sources)') }}
        </h3>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- 竞对价格波动 -->
        <div
          class="glass-card rounded-xl p-5 flex flex-col h-full bg-surface-container-lowest transition-shadow hover:shadow-md border-t-4 border-t-primary"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-primary-container text-on-primary-container flex items-center justify-center"
              >
                <span class="material-symbols-outlined">storefront</span>
              </div>
              <div>
                <h4 class="font-headline-md text-headline-md text-on-background text-[18px]">
                  {{ t('竞对价格波动') }}
                </h4>
                <span class="font-label-lg text-label-lg text-on-surface-variant text-[12px]"
                  >Competitor Pricing</span
                >
              </div>
            </div>
            <div
              class="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in"
            >
              <input
                checked=""
                class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer z-10"
                id="toggle1"
                name="toggle1"
                type="checkbox"
              />
              <label
                class="toggle-label block overflow-hidden h-5 rounded-full bg-surface-variant cursor-pointer"
                for="toggle1"
              ></label>
            </div>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-6 flex-1 text-[14px]">
            {{ t('监测核心竞争圈内酒店的价格突变。防止市场份额流失。') }}
          </p>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between font-label-lg text-label-lg mb-1">
                <span class="text-on-surface">{{ t('敏感度 (Sensitivity)') }}</span
                ><span class="text-primary font-bold">{{ t('高') }}</span>
              </div>
              <input class="w-full" max="3" min="1" type="range" value="3" />
              <div class="flex justify-between text-[11px] text-on-surface-variant mt-1 px-1">
                <span>{{ t('低 (&gt;20%)') }}</span
                ><span>{{ t('中 (&gt;10%)') }}</span
                ><span>{{ t('高 (&gt;5%)') }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-2 border-t border-outline-variant">
              <span class="material-symbols-outlined text-[16px] text-on-surface-variant"
                >notifications_active</span
              >
              <span class="font-label-lg text-label-lg text-on-surface text-[13px]">{{
                t('通知方式:')
              }}</span>
              <select
                class="bg-transparent border-none text-[13px] font-medium text-primary focus:ring-0 p-0 cursor-pointer"
              >
                <option>{{ t('App推送 + 短信') }}</option>
                <option>{{ t('仅App推送') }}</option>
                <option>{{ t('静默记录') }}</option>
              </select>
            </div>
          </div>
        </div>
        <!-- 极端天气 -->
        <div
          class="glass-card rounded-xl p-5 flex flex-col h-full bg-surface-container-lowest transition-shadow hover:shadow-md border-t-4 border-t-primary"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-primary-container text-on-primary-container flex items-center justify-center"
              >
                <span class="material-symbols-outlined">thunderstorm</span>
              </div>
              <div>
                <h4 class="font-headline-md text-headline-md text-on-background text-[18px]">
                  {{ t('极端天气预警') }}
                </h4>
                <span class="font-label-lg text-label-lg text-on-surface-variant text-[12px]"
                  >Extreme Weather</span
                >
              </div>
            </div>
            <div
              class="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in"
            >
              <input
                checked=""
                class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer z-10"
                id="toggle2"
                name="toggle2"
                type="checkbox"
              />
              <label
                class="toggle-label block overflow-hidden h-5 rounded-full bg-surface-variant cursor-pointer"
                for="toggle2"
              ></label>
            </div>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-6 flex-1 text-[14px]">
            {{ t('关联本地气象数据。台风、暴雨等预警可能引发大面积退订或滞留。') }}
          </p>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between font-label-lg text-label-lg mb-1">
                <span class="text-on-surface">{{ t('触发等级') }}</span
                ><span class="text-error font-bold">{{ t('橙色及以上') }}</span>
              </div>
              <input class="w-full" max="3" min="1" type="range" value="2" />
              <div class="flex justify-between text-[11px] text-on-surface-variant mt-1 px-1">
                <span>{{ t('黄色') }}</span
                ><span>{{ t('橙色') }}</span
                ><span>{{ t('红色') }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-2 border-t border-outline-variant">
              <span class="material-symbols-outlined text-[16px] text-on-surface-variant"
                >notifications_active</span
              >
              <span class="font-label-lg text-label-lg text-on-surface text-[13px]">{{
                t('通知方式:')
              }}</span>
              <select
                class="bg-transparent border-none text-[13px] font-medium text-primary focus:ring-0 p-0 cursor-pointer"
              >
                <option>{{ t('仅App推送') }}</option>
                <option>{{ t('App推送 + 短信') }}</option>
                <option>{{ t('静默记录') }}</option>
              </select>
            </div>
          </div>
        </div>
        <!-- 本地突发事件 -->
        <div
          class="glass-card rounded-xl p-5 flex flex-col h-full bg-surface-container-lowest transition-shadow hover:shadow-md border-t-4 border-t-tertiary"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-tertiary-container text-on-tertiary-container flex items-center justify-center"
              >
                <span class="material-symbols-outlined">festival</span>
              </div>
              <div>
                <h4 class="font-headline-md text-headline-md text-on-background text-[18px]">
                  {{ t('本地突发事件') }}
                </h4>
                <span class="font-label-lg text-label-lg text-on-surface-variant text-[12px]"
                  >Local Events (AI Mined)</span
                >
              </div>
            </div>
            <div
              class="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in"
            >
              <input
                checked=""
                class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer z-10"
                id="toggle3"
                name="toggle3"
                type="checkbox"
              />
              <label
                class="toggle-label block overflow-hidden h-5 rounded-full bg-surface-variant cursor-pointer"
                for="toggle3"
              ></label>
            </div>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant mb-6 flex-1 text-[14px]">
            {{ t('AI自动抓取本地未排期的突发大型活动（如临时演唱会官宣），提示涨价机会。') }}
          </p>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between font-label-lg text-label-lg mb-1">
                <span class="text-on-surface">{{ t('影响半径') }}</span
                ><span class="text-primary font-bold">{{ t('5公里') }}</span>
              </div>
              <input class="w-full" max="3" min="1" type="range" value="2" />
              <div class="flex justify-between text-[11px] text-on-surface-variant mt-1 px-1">
                <span>2km</span><span>5km</span><span>10km</span>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-2 border-t border-outline-variant">
              <span class="material-symbols-outlined text-[16px] text-on-surface-variant"
                >notifications_active</span
              >
              <span class="font-label-lg text-label-lg text-on-surface text-[13px]">{{
                t('通知方式:')
              }}</span>
              <select
                class="bg-transparent border-none text-[13px] font-medium text-primary focus:ring-0 p-0 cursor-pointer"
              >
                <option>{{ t('App推送 + 短信') }}</option>
                <option>{{ t('仅App推送') }}</option>
                <option>{{ t('静默记录') }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
