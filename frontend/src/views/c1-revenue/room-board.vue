<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 团队与协议价配置（收益管理 C1）：协议价护栏 + 多渠道成本 + 净收益实时计算器
// 数据：多渠道佣金成本来自真实接口 api.listChannels（name / commission_rate）
// 佣金只读展示；维护入口为系统配置 · 财务参数 · OTA佣金
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'

const router = useRouter()
const channels = ref<any[]>([])
const listPrice = ref(400)
const marketingCost = ref(15)

onMounted(async () => {
  channels.value = await api.listChannels()
})

function badge(name: string) {
  return (name || '渠').trim().charAt(0)
}
function commText(c: any) {
  return ((Number(c.commission_rate) || 0) * 100).toFixed(1) + '%'
}
function pctText(rate: number) {
  const pct = Math.round(rate * 10000) / 100
  return String(pct)
    .replace(/\.0+$/, '')
    .replace(/(\.\d*?)0+$/, '$1')
}
function goOtaCommission() {
  router.push({ path: '/a-ai-core/finance-params-float-carry', query: { tab: 'ota' } })
}

/** 净收益 = 挂牌价 × (1 − 佣金率) − 附加营销成本 */
const netCards = computed(() => {
  const price = Number(listPrice.value) || 0
  const mkt = Number(marketingCost.value) || 0
  const otas = (channels.value || [])
    .filter((c: any) => Number(c.commission_rate) >= 0)
    .slice(0, 3)
    .map((c: any) => {
      const rate = Number(c.commission_rate) || 0
      const net = Math.max(0, price * (1 - rate) - mkt)
      const margin = price > 0 ? (net / price) * 100 : 0
      const pct = pctText(rate)
      return {
        key: String(c.code || c.id),
        title: `${c.name || '渠道'}净收益 (${pct}%)`,
        net,
        margin,
        formula: `¥${price} × (1 − ${c.name || '渠道'}佣金 ${pct}%) − ¥${mkt} = ¥${net.toFixed(2)}`,
        highlight: false,
      }
    })
  const ownNet = Math.max(0, price - mkt)
  const ownMargin = price > 0 ? (ownNet / price) * 100 : 0
  return [
    ...otas,
    {
      key: 'direct',
      title: t('自有渠道 (0%)'),
      net: ownNet,
      margin: ownMargin,
      formula: `¥${price} × (1 − 0%) − ¥${mkt} = ¥${ownNet.toFixed(2)}`,
      highlight: true,
    },
  ]
})
</script>

<template>
  <div class="page">
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">
          {{ t('团队与协议价配置') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-2">
          {{ t('管理企业协议价格及多渠道佣金成本，确保 AI 定价符合利润预期。') }}
        </p>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <!-- 协议价管理（定价护栏） -->
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">business_center</span
            >{{ t('协议价管理 (定价护栏)') }}
          </h2>
          <button
            class="bg-primary text-on-primary px-4 py-2 rounded-full font-label-lg text-label-lg hover:bg-surface-tint transition-colors"
          >
            {{ t('+ 新增协议') }}
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr
                class="border-b border-surface-variant text-on-surface-variant font-label-lg text-label-lg"
              >
                <th class="py-3 px-4">{{ t('签约公司') }}</th>
                <th class="py-3 px-4">{{ t('房型') }}</th>
                <th class="py-3 px-4">{{ t('价格类型') }}</th>
                <th class="py-3 px-4">{{ t('基准价/折扣') }}</th>
                <th class="py-3 px-4">{{ t('状态') }}</th>
                <th class="py-3 px-4 text-right">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                class="border-b border-surface-variant hover:bg-surface-container-low transition-colors"
              >
                <td class="py-3 px-4 font-body-md">{{ t('阿里巴巴 (杭州)') }}</td>
                <td class="py-3 px-4 font-body-md">{{ t('高级大床房') }}</td>
                <td class="py-3 px-4 font-body-md">{{ t('固定价') }}</td>
                <td class="py-3 px-4 font-num-md text-num-md">¥350.00</td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[#e6f4ea] text-[#137333]"
                    >{{ t('生效中') }}</span
                  >
                </td>
                <td class="py-3 px-4 text-right">
                  <button class="text-primary hover:text-surface-tint">
                    <span class="material-symbols-outlined text-sm">edit</span>
                  </button>
                </td>
              </tr>
              <tr
                class="border-b border-surface-variant hover:bg-surface-container-low transition-colors"
              >
                <td class="py-3 px-4 font-body-md">{{ t('腾讯科技') }}</td>
                <td class="py-3 px-4 font-body-md">{{ t('全房型') }}</td>
                <td class="py-3 px-4 font-body-md">{{ t('动态折扣') }}</td>
                <td class="py-3 px-4 font-num-md text-num-md">{{ t('8.5折') }}</td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[#e6f4ea] text-[#137333]"
                    >{{ t('生效中') }}</span
                  >
                </td>
                <td class="py-3 px-4 text-right">
                  <button class="text-primary hover:text-surface-tint">
                    <span class="material-symbols-outlined text-sm">edit</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div
          class="mt-4 p-3 bg-surface-container-low rounded-lg border-l-4 border-primary text-sm text-on-surface-variant flex gap-2"
        >
          <span class="material-symbols-outlined text-primary text-base">info</span>
          <p>
            {{
              t(
                'AI 动态调价将严格遵守上述固定价格或折扣比例，不会对已绑定的企业客户展示超出护栏的价格。',
              )
            }}
          </p>
        </div>
      </div>

      <!-- AI 净收入优化模型 -->
      <div
        class="col-span-12 lg:col-span-4 bg-tertiary-fixed border-l-4 border-tertiary rounded-xl p-6 shadow-sm relative overflow-hidden"
      >
        <div class="absolute -right-4 -top-4 opacity-10">
          <span class="material-symbols-outlined text-9xl">psychology</span>
        </div>
        <h2
          class="font-headline-md text-headline-md text-on-tertiary-fixed mb-3 flex items-center gap-2 relative z-10"
        >
          <span class="material-symbols-outlined text-tertiary">arrow_back_ios_new</span
          >{{ t('AI 净收入优化模型') }}
        </h2>
        <p class="font-body-md text-body-md text-on-tertiary-fixed-variant relative z-10 mb-4">
          {{ t('我们的 AI 引擎不仅关注“挂牌价” (GTV)，更核心优化“净收益” (Net RevPAR)。') }}
        </p>
        <ul class="space-y-3 relative z-10">
          <li class="flex items-start gap-2">
            <span class="material-symbols-outlined text-tertiary text-sm mt-1">check_circle</span
            ><span class="text-sm text-on-tertiary-fixed">{{
              t('自动识别高佣金渠道，在需求旺盛时优先将库存分配给低成本/直销渠道。')
            }}</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="material-symbols-outlined text-tertiary text-sm mt-1">check_circle</span
            ><span class="text-sm text-on-tertiary-fixed">{{
              t('计算各渠道净利润边界，确保即使在淡季打折，收益也不会低于盈亏平衡点。')
            }}</span>
          </li>
        </ul>
      </div>

      <!-- 多渠道成本配置（v-for 绑定 api.listChannels；佣金只读） -->
      <div
        class="col-span-12 lg:col-span-5 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
      >
        <div class="flex items-start justify-between gap-3 mb-4">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary">account_tree</span
            >{{ t('多渠道成本配置') }}
          </h2>
          <button
            type="button"
            class="shrink-0 text-xs font-semibold text-primary hover:underline"
            @click="goOtaCommission"
          >
            {{ t('去财务参数 · OTA佣金') }}
          </button>
        </div>
        <p class="text-xs text-on-surface-variant mb-3">
          {{ t('佣金率只读，请在系统配置 · 财务参数 · OTA佣金中维护。') }}
        </p>
        <div class="space-y-4">
          <div
            v-for="c in channels"
            :key="c.id"
            class="flex items-center justify-between p-3 border border-surface-variant rounded-lg hover:border-outline-variant transition-colors"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-8 h-8 rounded bg-primary flex items-center justify-center text-white font-bold text-xs"
              >
                {{ badge(c.name) }}
              </div>
              <span class="font-body-md">{{ c.name || t('渠道') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-on-surface-variant">{{ t('佣金率') }}</span>
              <span class="w-20 text-right py-1 px-2 font-num-md text-num-md text-on-surface">{{
                commText(c)
              }}</span>
            </div>
          </div>
          <div v-if="!channels.length" class="text-sm text-on-surface-variant py-4 text-center">
            {{ t('暂无启用渠道') }}
          </div>
          <div
            class="flex items-center justify-between p-3 border border-surface-variant rounded-lg bg-surface-container-low"
          >
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded bg-primary flex items-center justify-center text-white">
                <span class="material-symbols-outlined text-sm">home</span>
              </div>
              <span class="font-body-md font-medium">{{ t('自有渠道 (小程序)') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-on-surface-variant">{{ t('佣金率') }}</span>
              <span class="w-20 text-right py-1 px-2 font-num-md text-num-md text-secondary"
                >0.0%</span
              >
            </div>
          </div>
        </div>
      </div>

      <!-- 净收益实时计算器 -->
      <div
        class="col-span-12 lg:col-span-7 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex flex-col"
      >
        <h2 class="font-headline-md text-headline-md flex items-center gap-2 mb-4">
          <span class="material-symbols-outlined text-primary">calculate</span
          >{{ t('净收益实时计算器') }}
        </h2>
        <div
          class="flex gap-4 items-end mb-4 bg-surface-bright p-4 rounded-lg border border-surface-variant"
        >
          <div class="flex-1">
            <label class="block text-sm font-medium text-on-surface-variant mb-1">{{
              t('输入挂牌价 (¥)')
            }}</label>
            <input
              v-model.number="listPrice"
              class="w-full py-2 px-3 border border-outline-variant rounded-lg font-num-xl text-num-xl focus:ring-2 focus:ring-primary focus:border-primary"
              type="number"
            />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-on-surface-variant mb-1">{{
              t('附加营销成本 (每单 ¥)')
            }}</label>
            <input
              v-model.number="marketingCost"
              class="w-full py-2 px-3 border border-outline-variant rounded-lg font-num-md text-num-md focus:ring-2 focus:ring-primary focus:border-primary"
              type="number"
            />
          </div>
        </div>
        <p class="text-xs text-on-surface-variant mb-4">
          {{ t('公式：净收益 = 挂牌价 × (1 − 渠道佣金%) − 附加营销成本 · 佣金来自') }}
          <button
            type="button"
            class="text-primary font-semibold hover:underline"
            @click="goOtaCommission"
          >
            {{ t('财务参数 · OTA佣金') }}
          </button>
        </p>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
          <div
            v-for="card in netCards"
            :key="card.key"
            class="rounded-lg p-4 border flex flex-col justify-center items-center text-center"
            :class="
              card.highlight
                ? 'bg-primary-container border-primary-container shadow-[0_0_12px_rgba(26,115,232,0.2)]'
                : 'bg-surface border-surface-variant'
            "
          >
            <span
              class="text-sm mb-1"
              :class="card.highlight ? 'text-on-primary-container' : 'text-on-surface-variant'"
              >{{ card.title }}</span
            >
            <span
              class="font-num-xl text-num-xl"
              :class="card.highlight ? 'text-on-primary-container font-bold' : 'text-primary'"
              >¥{{ card.net.toFixed(2) }}</span
            >
            <span
              class="text-xs mt-1"
              :class="card.highlight ? 'text-inverse-primary' : 'text-secondary'"
            >
              {{ card.highlight ? t('最高收益') : `毛利率: ${card.margin.toFixed(1)}%` }}</span
            >
            <span class="text-[10px] text-on-surface-variant mt-2 leading-snug px-1">{{
              card.formula
            }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
