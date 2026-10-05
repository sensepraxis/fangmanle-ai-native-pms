<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 智能补货与采购
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
import SuppliesFocusBar from '../../components/SuppliesFocusBar.vue'

const route = useRoute()
const focusSummary = ref('')
const autoApprove = ref(true)
const peakMode = ref(true)
const items = ref<any[]>([])
const suppliers = ref<any[]>([])
const orderId = ref<number | null>(null)
const approving = ref(false)

const totalCount = computed(() => items.value.length)
const totalAmt = computed(() => {
  const sum = items.value.reduce(
    (s: number, it: any) => s + Number(String(it.amt).replace(/[^\d.]/g, '') || 0),
    0,
  )
  return '¥' + sum.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'amenity')
    const full = await api.suppliesBoard(hotelStore.hotelId)
    const insightId = Number(route.query.insight_id || 0)
    if (insightId) {
      const ins = (full?.insights || board?.insights || []).find(
        (x: any) => Number(x.id) === insightId,
      )
      if (ins) {
        focusSummary.value = `洞察：${ins.title} — ${ins.recommendation || ''}`
      }
    } else {
      focusSummary.value = ''
    }

    const orders = board?.restock_orders || []
    const order = orders[0]
    orderId.value = order?.id ?? null
    const supplyMap: Record<number, any> = {}
    for (const s of board?.supplies || []) {
      if (s.id != null) supplyMap[s.id] = s
    }

    if (order?.items?.length) {
      items.value = order.items.map((it: any) => {
        const urg = it.urgency || 'normal'
        const supply = it.supply_id != null ? supplyMap[it.supply_id] : null
        const name = it.name || t('物资')
        const matchInsight = insightId
          ? focusSummary.value.includes(name) ||
            /牙刷|洗发|拖鞋|补货/.test(focusSummary.value + name)
          : false
        return {
          name,
          vendor: order.vendor || '',
          badge:
            urg === 'critical'
              ? t('急需补货')
              : urg === 'high'
                ? t('优先补货')
                : matchInsight
                  ? t('洞察相关')
                  : '',
          borderCls:
            urg === 'critical' || matchInsight
              ? 'border-l-4 border-error rounded-r-xl border-y border-r border-outline-variant'
              : urg === 'high'
                ? 'border-l-4 border-tertiary rounded-r-xl border-y border-r border-outline-variant'
                : 'border rounded-xl border-outline-variant',
          badgeCls:
            urg === 'critical' || matchInsight
              ? 'bg-error/10 text-error'
              : urg === 'high'
                ? 'bg-tertiary/10 text-tertiary'
                : '',
          cur: supply ? `${supply.current_stock}` : '-',
          curErr: urg === 'critical',
          midLabel: t('建议数量'),
          mid: String(it.qty ?? '-'),
          midCls: 'text-on-surface',
          ai: `+${it.qty ?? 0}`,
          amt: `¥${Number(it.amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          highlight: matchInsight,
        }
      })
      if (insightId) {
        items.value = [
          ...items.value.filter((x: any) => x.highlight),
          ...items.value.filter((x: any) => !x.highlight),
        ]
      }
    } else {
      items.value = []
    }

    const vendors = [...new Set(orders.map((o: any) => o.vendor).filter(Boolean))] as string[]
    if (vendors.length) {
      suppliers.value = vendors.map((name, i) => ({
        name,
        initial: name[0] || t('供'),
        score: `${(4.9 - i * 0.1).toFixed(1)}评分`,
        lead: i === 0 ? t('1-2 天') : `${2 + i} 天`,
        note: i === 0 ? t('交期稳定') : t('标准交期'),
        noteCls: i === 0 ? 'text-[#059669]' : 'text-on-surface-variant',
      }))
    } else {
      suppliers.value = []
    }
  } catch {
    items.value = []
    suppliers.value = []
    orderId.value = null
  }
}

async function approve() {
  if (!orderId.value || approving.value) return
  approving.value = true
  try {
    await api.approveRestock(orderId.value)
    await load()
  } catch {
    /* keep UI */
  } finally {
    approving.value = false
  }
}

onMounted(load)
watch(() => [hotelStore.hotelId, route.query.insight_id], load)
</script>

<template>
  <div class="page">
    <SuppliesFocusBar :summary="focusSummary" />
    <!-- 页头 + 策略开关 -->
    <div class="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ t('智能补货与采购') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant flex items-center gap-2 mt-2">
          {{ t('AI 已基于当前库存生成建议采购清单。') }}
        </p>
      </div>
      <!-- 策略开关 -->
      <div
        class="flex flex-col gap-3 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-sm w-full md:w-auto"
      >
        <div class="flex items-center justify-between gap-6">
          <label
            class="font-label-lg text-label-lg text-on-surface flex items-center gap-2 cursor-pointer"
            >{{ t('安全库存自动审批') }}</label
          >
          <label class="relative inline-flex items-center cursor-pointer">
            <input v-model="autoApprove" type="checkbox" class="sr-only peer" />
            <div
              class="w-9 h-5 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-outline-variant after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"
            ></div>
          </label>
        </div>
        <div class="flex items-center justify-between gap-6">
          <label
            class="font-label-lg text-label-lg text-on-surface flex items-center gap-2 cursor-pointer"
            >{{ t('AI动态库存调整 (旺季模式)') }}</label
          >
          <label class="relative inline-flex items-center cursor-pointer">
            <input v-model="peakMode" type="checkbox" class="sr-only peer" />
            <div
              class="w-9 h-5 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-outline-variant after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-tertiary"
            ></div>
          </label>
        </div>
      </div>
    </div>

    <!-- Bento 网格 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <!-- 待采购物资清单 (Span 8) -->
      <div class="lg:col-span-8 flex flex-col gap-4">
        <h2 class="font-headline-md text-headline-md text-on-surface mb-2">
          {{ t('待采购物资清单') }}
        </h2>
        <p v-if="!items.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(it, i) in items"
            :key="i"
            class="bg-surface-container-lowest p-5 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow"
            :class="it.borderCls"
          >
            <div
              v-if="it.badge"
              class="absolute top-0 right-0 px-3 py-1 rounded-bl-lg font-label-lg text-[12px] font-bold flex items-center gap-1"
              :class="it.badgeCls"
            >
              {{ it.badge }}
            </div>
            <div class="flex items-start gap-4 mb-4" :class="it.badge ? '' : 'mt-2'">
              <div
                class="w-12 h-12 rounded-lg bg-surface-container flex items-center justify-center text-on-surface-variant"
              ></div>
              <div>
                <h3 class="font-headline-md text-[18px] text-on-surface">{{ it.name }}</h3>
                <p class="font-body-md text-sm text-on-surface-variant">
                  {{ t('供应商:') }} {{ it.vendor }}
                </p>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-2 mb-4 bg-surface-container-low p-3 rounded-lg">
              <div class="text-center">
                <div class="text-[12px] text-on-surface-variant mb-1">{{ t('当前库存') }}</div>
                <div
                  class="font-num-md font-bold"
                  :class="it.curErr ? 'text-error' : 'text-on-surface'"
                >
                  {{ it.cur }}
                </div>
              </div>
              <div class="text-center border-x border-outline-variant/30">
                <div class="text-[12px] text-on-surface-variant mb-1">{{ it.midLabel }}</div>
                <div class="font-num-md" :class="it.midCls">{{ it.mid }}</div>
              </div>
              <div class="text-center">
                <div class="text-[12px] text-tertiary mb-1 flex items-center justify-center gap-1">
                  {{ t('AI建议') }}
                </div>
                <div class="font-num-md text-tertiary font-bold">{{ it.ai }}</div>
              </div>
            </div>
            <div
              class="flex items-center justify-between mt-2 pt-3 border-t border-outline-variant/50"
            >
              <div class="font-body-md text-sm text-on-surface">
                {{ t('预估金额:')
                }}<span class="font-num-md font-bold text-on-surface"> {{ it.amt }}</span>
              </div>
              <button
                class="text-primary hover:bg-primary/10 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
              >
                {{ t('修改数量') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作 & 供应商 (Span 4) -->
      <div class="lg:col-span-4 flex flex-col gap-6">
        <!-- 生成采购单 -->
        <div
          class="bg-primary-container text-on-primary-container rounded-2xl p-6 shadow-md relative overflow-hidden"
        >
          <div
            class="absolute inset-0 opacity-10"
            style="
              background-image: radial-gradient(circle at 2px 2px, white 1px, transparent 0);
              background-size: 20px 20px;
            "
          ></div>
          <div class="relative z-10">
            <h3 class="font-headline-lg text-[22px] font-bold mb-2">{{ t('生成采购申请单') }}</h3>
            <p class="font-body-md text-sm opacity-90 mb-6">
              {{ t('共包含') }} {{ totalCount }} {{ t('项物资，基于当前') }}AI策略优化。
            </p>
            <div class="bg-on-primary-container/10 rounded-xl p-4 mb-6">
              <div class="flex justify-between items-center mb-2">
                <span class="font-body-md">{{ t('总计采购项:') }}</span
                ><span class="font-num-md font-bold">{{ totalCount }} {{ t('项') }}</span>
              </div>
              <div class="flex justify-between items-center text-lg">
                <span class="font-body-md font-medium">{{ t('预估总金额:') }}}</span
                ><span class="font-num-xl font-bold">{{ totalAmt }}</span>
              </div>
            </div>
            <button
              class="w-full bg-white text-primary-container font-headline-md text-[16px] py-4 rounded-xl shadow-sm hover:shadow-md hover:bg-surface-bright transition-all active:scale-[0.98] flex items-center justify-center gap-2"
              type="button"
              :disabled="approving || !orderId"
              @click="approve"
            >
              {{ approving ? t('审批中…') : t('一键批准采购单') }}
            </button>
          </div>
        </div>
        <!-- 优选供应商交期 -->
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm"
        >
          <h3 class="font-headline-md text-[18px] text-on-surface mb-4 flex items-center gap-2">
            {{ t('优选供应商交期') }}
          </h3>
          <p v-if="!suppliers.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
          <div v-else class="flex flex-col gap-3">
            <div
              v-for="(s, i) in suppliers"
              :key="i"
              class="flex items-center justify-between p-3 bg-surface rounded-lg border border-outline-variant/50"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container text-sm font-bold"
                >
                  {{ s.initial }}
                </div>
                <div>
                  <div class="font-label-lg text-on-surface">{{ s.name }}</div>
                  <div class="text-[12px] text-on-surface-variant flex items-center gap-1">
                    {{ s.score }}
                  </div>
                </div>
              </div>
              <div class="text-right">
                <div class="font-num-md text-sm text-on-surface font-medium">{{ s.lead }}</div>
                <div class="text-[11px]" :class="s.noteCls">{{ s.note }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-hint {
  margin: 0;
  padding: 24px 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
</style>
