<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 客户详情工作台 —— 数据：GET /api/guests + /api/guests/:id
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { VIP_CN } from '../../lib/ui'

const router = useRouter()
const route = useRoute()
const d = ref<any>(null)
const loading = ref(true)

function maskPhone(p?: string) {
  if (!p) return '—'
  return p.length >= 7 ? `${p.slice(0, 3)}****${p.slice(-4)}` : p
}

async function load() {
  loading.value = true
  try {
    let id = Number(route.query.id || 0)
    if (!id) {
      const gs = await api.listGuests(hotelStore.hotelId)
      id = gs?.[0]?.id
    }
    if (!id) {
      d.value = null
      return
    }
    d.value = await api.guest360(id)
  } catch {
    d.value = null
  } finally {
    loading.value = false
  }
}
onMounted(load)

const g = computed(() => d.value?.guest || {})
const tags = computed(() => (d.value?.tags || []).map((t: any) => t.name).filter(Boolean))
const orders = computed(() => d.value?.orders || [])
const identities = computed(() => d.value?.identities || [])
const spend = computed(() => Number(g.value.ltv || 0))
const stayN = computed(() => orders.value.length)
const adr = computed(() => (stayN.value ? Math.round(spend.value / stayN.value) : 0))
const ltvScore = computed(() => {
  const v = spend.value
  if (v >= 10000) return 9.4
  if (v >= 5000) return 8.2
  if (v >= 2000) return 7.1
  return 6.0
})
const churnPct = computed(() => Math.round(Number(g.value.churn_risk || 0) * 100))
const vipLabel = computed(() => VIP_CN[g.value.vip_level] || g.value.vip_level || t('会员'))
const roomShare = computed(() => Math.round(spend.value * 0.7))
const dineShare = computed(() => Math.round(spend.value * 0.2))
const spaShare = computed(() =>
  Math.max(0, Math.round(spend.value - roomShare.value - dineShare.value)),
)

function go(path: string) {
  router.push(path)
}
function goDetail() {
  if (g.value.id) router.push(`/guests/${g.value.id}`)
}
</script>

<template>
  <div class="page">
    <div class="col-span-12 flex justify-between items-end mb-4">
      <div>
        <div class="text-label-lg font-label-lg text-on-surface-variant flex items-center gap-2">
          <button
            type="button"
            class="hover:text-primary transition-colors"
            @click="go('/b-data/global-guest-directory')"
          >
            {{ t('客史中心 / 全景列表') }}
          </button>
          <span class="text-on-surface">{{ t('客户详情') }}</span>
        </div>
        <h2 class="text-display-lg font-display-lg text-on-surface mt-2">
          {{ t('客户详情工作台') }}
        </h2>
      </div>
      <div class="flex gap-4 flex-wrap">
        <button
          type="button"
          class="bg-surface-container-low text-on-surface border border-outline-variant px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-surface-variant transition-colors"
          @click="go('/b-data/one-id-resolution')"
        >
          {{ t('身份归并') }}
        </button>
        <button
          type="button"
          class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-primary-fixed-variant transition-colors shadow-sm"
          @click="goDetail"
        >
          {{ t('完整 360') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-on-surface-variant">{{ t('加载中…') }}</div>
    <div v-else-if="!d" class="text-on-surface-variant">{{ t('暂无客户数据') }}</div>
    <template v-else>
      <div class="col-span-12 lg:col-span-8 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] flex flex-col sm:flex-row gap-6 relative overflow-hidden"
        >
          <div class="flex flex-col items-center gap-3 relative z-10">
            <div class="relative">
              <div
                class="w-24 h-24 rounded-full bg-primary-fixed text-on-primary-fixed flex items-center justify-center text-3xl font-bold border-4 border-surface"
              >
                {{ (g.name || '?').slice(0, 1) }}
              </div>
              <div
                class="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-gold text-on-surface-variant px-3 py-0.5 rounded-full text-xs font-bold border-2 border-surface shadow-sm whitespace-nowrap"
              >
                {{ vipLabel }}
              </div>
            </div>
          </div>
          <div class="flex-1 flex flex-col justify-center z-10">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-display-lg font-display-lg text-on-surface">{{ g.name || '—' }}</h3>
              <span
                class="bg-surface-container-high text-on-surface-variant px-2 py-1 rounded text-label-lg font-label-lg border border-outline-variant"
                >{{ maskPhone(g.phone) }}</span
              >
            </div>
            <div class="flex flex-wrap gap-2 mb-4">
              <button
                v-for="tag in tags.slice(0, 4)"
                :key="tag"
                type="button"
                class="bg-primary-fixed text-on-primary-fixed px-3 py-1 rounded-full text-label-lg font-label-lg border border-primary-fixed-dim hover:opacity-90"
                @click="go('/b-data/tag-ecosystem-overview')"
              >
                {{ tag }}
              </button>
              <span v-if="!tags.length" class="text-sm text-on-surface-variant">{{
                t('暂无标签')
              }}</span>
            </div>
            <div class="grid grid-cols-4 gap-4 border-t border-outline-variant pt-4 mt-2">
              <div>
                <p class="text-label-lg font-label-lg text-on-surface-variant">{{ t('总消费') }}</p>
                <p class="text-num-xl font-num-xl text-on-surface">
                  ¥{{ spend.toLocaleString('zh-CN') }}
                </p>
              </div>
              <div>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('入住次数') }}
                </p>
                <p class="text-num-xl font-num-xl text-on-surface">{{ stayN }}</p>
              </div>
              <div>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('平均房价') }}
                </p>
                <p class="text-num-xl font-num-xl text-on-surface">
                  ¥{{ adr.toLocaleString('zh-CN') }}
                </p>
              </div>
              <div class="bg-tertiary-fixed/30 p-2 rounded-lg border border-tertiary-fixed-dim">
                <p class="text-[10px] font-bold text-tertiary uppercase tracking-wider">
                  {{ t('AI LTV 评分') }}
                </p>
                <p class="text-num-xl font-num-xl text-on-tertiary-fixed">
                  {{ ltvScore }}<span class="text-label-lg">/10</span>
                </p>
              </div>
            </div>
          </div>
        </div>

        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 grid grid-cols-1 md:grid-cols-2 gap-6"
        >
          <div class="bg-surface rounded-lg p-5 border border-outline-variant">
            <h4 class="text-headline-md font-headline-md text-on-surface mb-4">
              {{ t('消费结构（按 LTV 估算）') }}
            </h4>
            <div class="flex flex-col gap-4">
              <div>
                <div class="flex mb-2 items-center justify-between">
                  <div class="text-label-lg font-label-lg">{{ t('客房收入') }}</div>
                  <div class="text-num-md font-bold">¥{{ roomShare.toLocaleString('zh-CN') }}</div>
                </div>
                <div class="overflow-hidden h-2 rounded bg-primary-fixed">
                  <div class="h-full bg-primary" style="width: 70%"></div>
                </div>
              </div>
              <div>
                <div class="flex mb-2 items-center justify-between">
                  <div class="text-label-lg font-label-lg">{{ t('餐饮') }}</div>
                  <div class="text-num-md font-bold">¥{{ dineShare.toLocaleString('zh-CN') }}</div>
                </div>
                <div class="overflow-hidden h-2 rounded bg-secondary-fixed">
                  <div class="h-full bg-secondary" style="width: 40%"></div>
                </div>
              </div>
              <div>
                <div class="flex mb-2 items-center justify-between">
                  <div class="text-label-lg font-label-lg">{{ t('其他附加') }}</div>
                  <div class="text-num-md font-bold">¥{{ spaShare.toLocaleString('zh-CN') }}</div>
                </div>
                <div class="overflow-hidden h-2 rounded bg-tertiary-fixed">
                  <div class="h-full bg-tertiary" style="width: 20%"></div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-surface rounded-lg p-5 border border-outline-variant">
            <h4 class="text-headline-md font-headline-md text-on-surface mb-4">
              {{ t('渠道身份') }}
            </h4>
            <ul class="space-y-2">
              <li
                v-for="i in identities"
                :key="i.id"
                class="text-sm flex justify-between border-b border-outline-variant py-2"
              >
                <span>{{ i.source }}</span>
                <span class="text-on-surface-variant"
                  >{{ i.external_id }} · {{ Math.round(Number(i.confidence || 0) * 100) }}%</span
                >
              </li>
              <li v-if="!identities.length" class="text-on-surface-variant text-sm">
                {{ t('暂无身份链路') }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <aside class="col-span-12 lg:col-span-4 mt-4 lg:mt-0">
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] h-full flex flex-col ai-glow overflow-hidden"
        >
          <div
            class="bg-tertiary-fixed p-4 border-b border-outline-variant flex items-center justify-between"
          >
            <h3 class="text-headline-md font-headline-md text-on-tertiary-container font-bold">
              {{ t('AI 客户洞察') }}
            </h3>
            <span
              class="text-[10px] bg-tertiary text-on-tertiary px-2 py-0.5 rounded-sm uppercase tracking-wide"
              >{{ t('实时') }}</span
            >
          </div>
          <div class="p-5 flex flex-col gap-6 flex-1">
            <section>
              <h4
                class="text-label-lg font-label-lg text-on-surface-variant mb-3 uppercase tracking-wider"
              >
                {{ t('行为摘要') }}
              </h4>
              <div
                class="bg-surface-bright rounded-lg p-3 border border-outline-variant text-body-md leading-relaxed"
              >
                {{ g.name || t('该客人') }} OneID {{ g.one_id || '—' }}，{{ t('城市') }}
                {{ g.city || '—' }}， {{ t('已关联') }} {{ identities.length }}
                {{ t('个渠道身份，累计') }} {{ stayN }} {{ t('笔订单。') }}
              </div>
            </section>
            <section>
              <h4
                class="text-label-lg font-label-lg text-on-surface-variant mb-3 uppercase tracking-wider"
              >
                {{ t('留存指标') }}
              </h4>
              <div
                class="bg-surface-bright rounded-lg p-4 border border-outline-variant flex items-center justify-between"
              >
                <div>
                  <div class="text-body-md mb-1">{{ t('流失风险') }}</div>
                  <div class="text-headline-md font-bold">{{ churnPct }}%</div>
                </div>
              </div>
            </section>
            <section class="mt-auto">
              <h4
                class="text-label-lg font-label-lg text-on-surface-variant mb-3 uppercase tracking-wider"
              >
                {{ t('建议后续操作') }}
              </h4>
              <div class="flex flex-col gap-2">
                <button
                  type="button"
                  class="w-full text-left bg-surface-container-low hover:bg-tertiary-fixed-dim transition-colors rounded-lg p-3 border border-outline-variant"
                  @click="goDetail"
                >
                  <div class="font-bold">{{ t('打开完整客户 360') }}</div>
                  <div class="text-[12px] text-on-surface-variant mt-1">
                    {{ t('查看订单时间线与评价。') }}
                  </div>
                </button>
              </div>
            </section>
          </div>
        </div>
      </aside>
    </template>
  </div>
</template>

<style scoped>
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
