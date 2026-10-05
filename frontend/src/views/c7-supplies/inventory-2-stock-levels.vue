<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 易耗库存水位 —— 仅展示非布草物资（清洁用品 / 客用品 / 易耗品）。
 * 布草请走「布草周转」；从总览「清洁用品」进入时默认筛清洁用品。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
const route = useRoute()
const router = useRouter()

type Tab = 'all' | string

const allItems = ref<any[]>([])
const rooms = ref<string[]>([])
const tab = ref<Tab>('all')

const LINEN_KW = /布草|床单|被套|毛巾|浴巾|枕套|浴袍|linen|towel|sheet/i

function isLinen(x: any) {
  const cat = String(x.category || '')
  if (cat === t('布草')) return true
  return LINEN_KW.test(String(x.name || ''))
}

function normalizeTab(raw: unknown): Tab {
  const s = String(raw || '').trim()
  if (s === t('清洁用品') || s === 'clean') return t('清洁用品')
  if (s === t('客用品') || s === t('易耗品') || s === 'amenity') return t('客用品')
  return 'all'
}

function goPurchase() {
  router.push('/c7-supplies/smart-restocking')
}

function setTab(next: Tab) {
  tab.value = next
  const q = { ...route.query } as Record<string, string>
  if (next === 'all') delete q.cat
  else q.cat = next
  router.replace({ path: route.path, query: q })
}

function stockStyle(low: boolean, bar: number) {
  if (low || bar < 30) {
    return {
      dotCls: 'bg-error-container',
      barCls: 'bg-error',
      numCls: 'text-error',
      noteCls: 'text-error',
      note: t('低库存'),
    }
  }
  if (bar < 60) {
    return {
      dotCls: 'bg-tertiary-container',
      barCls: 'bg-tertiary',
      numCls: 'text-on-background',
      noteCls: 'text-tertiary',
      note: t('健康'),
    }
  }
  return {
    dotCls: 'bg-primary-fixed',
    barCls: 'bg-primary',
    numCls: 'text-on-background',
    noteCls: 'text-primary',
    note: t('充足'),
  }
}

function mapSupply(x: any) {
  const cur = Number(x.current_stock ?? x.cur ?? 0)
  const safe = Number(x.safety_stock ?? x.total ?? 0)
  const total = Math.max(cur, safe * 2, safe + cur, 1)
  const bar = Math.round((cur / total) * 100)
  const low = x.low ?? cur < safe
  const style = stockStyle(low, bar)
  return {
    name: x.name || x.item || t('物资'),
    category: x.category || '',
    cur: cur.toLocaleString('zh-CN'),
    total: Math.round(total).toLocaleString('zh-CN'),
    bar,
    ...style,
  }
}

const items = computed(() => {
  let rows = allItems.value.filter((x) => !isLinen(x))
  if (tab.value === t('清洁用品')) {
    rows = rows.filter((x) => String(x.category) === t('清洁用品'))
  } else if (tab.value === t('客用品')) {
    rows = rows.filter((x) => {
      const c = String(x.category || '')
      return c === t('客用品') || c === t('易耗品')
    })
  }
  return rows.slice(0, 12).map(mapSupply)
})

const damageChoices = computed(() => items.value.slice(0, 6).map((x) => x.name).filter(Boolean))

async function load() {
  tab.value = normalizeTab(route.query.cat)
  try {
    let supplies: any[] = []
    try {
      const board = await api.suppliesBoard(hotelStore.hotelId, 'amenity')
      supplies = board?.supplies || []
    } catch {
      /* fallback */
    }
    if (!supplies.length) {
      try {
        supplies = (await api.listSupplies(hotelStore.hotelId) || []).filter((x: any) => !isLinen(x))
      } catch {
        supplies = []
      }
    }

    allItems.value = supplies.filter((x: any) => !isLinen(x))
    rooms.value = []
  } catch {
    allItems.value = []
    rooms.value = []
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(() => route.query.cat, (v) => {
  tab.value = normalizeTab(v)
})
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end mb-8">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">
          {{ t('易耗库存水位') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('清洁用品 / 客用品库存（不含布草）') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="flex items-center gap-2 px-4 py-2 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg transition-colors border border-outline-variant"
          type="button"
        >
          <span class="font-label-lg text-label-lg">{{ t('导出报表') }}</span>
        </button>
        <button
          class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary hover:bg-surface-tint rounded-lg transition-colors shadow-sm"
          type="button"
          @click="goPurchase"
        >
          <span class="font-label-lg text-label-lg">{{ t('采购申请') }}</span>
        </button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-6 mb-8">
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="font-headline-md text-headline-md text-on-background flex items-center gap-2">
            {{ t('当前库存水平') }}
          </h2>
          <div class="flex gap-2">
            <button
              type="button"
              class="px-3 py-1 rounded-full font-label-lg text-sm transition-colors"
              :class="
                tab === 'all'
                  ? 'bg-primary-container text-on-primary-container'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              "
              @click="setTab('all')"
            >
              {{ t('全部易耗') }}
            </button>
            <button
              type="button"
              class="px-3 py-1 rounded-full font-label-lg text-sm transition-colors"
              :class="
                tab === t('清洁用品')
                  ? 'bg-primary-container text-on-primary-container'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              "
              @click="setTab(t('清洁用品'))"
            >
              {{ t('清洁用品') }}
            </button>
            <button
              type="button"
              class="px-3 py-1 rounded-full font-label-lg text-sm transition-colors"
              :class="
                tab === t('客用品')
                  ? 'bg-primary-container text-on-primary-container'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              "
              @click="setTab(t('客用品'))"
            >
              {{ t('客用品') }}
            </button>
          </div>
        </div>
        <p v-if="!items.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="(it, i) in items"
            :key="i"
            class="bg-surface rounded-lg p-4 border border-outline-variant hover:shadow-md transition-shadow"
          >
            <div class="flex justify-between items-start mb-4">
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center"
                :class="it.dotCls"
              ></div>
            </div>
            <h3 class="font-body-lg text-body-lg font-medium text-on-surface mb-1">
              {{ it.name }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="font-num-xl text-num-xl" :class="it.numCls">{{ it.cur }}</span>
              <span class="font-body-md text-body-md text-on-surface-variant pb-1"
                >/ {{ it.total }}</span
              >
            </div>
            <div class="w-full bg-surface-container-highest rounded-full h-1.5 mb-2">
              <div
                class="h-1.5 rounded-full"
                :class="it.barCls"
                :style="{ width: it.bar + '%' }"
              ></div>
            </div>
            <span class="font-label-lg text-label-lg text-xs" :class="it.noteCls">{{
              it.note
            }}</span>
          </div>
        </div>
      </div>

      <div
        class="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col"
      >
        <h2
          class="font-headline-md text-headline-md text-on-background flex items-center gap-2 mb-6 text-error"
        >
          {{ t('报废登记') }}
        </h2>
        <form class="flex-1 flex flex-col gap-4">
          <div>
            <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
              t('关联房间')
            }}</label>
            <div class="relative">
              <select
                class="w-full bg-surface border border-outline-variant rounded-lg px-4 py-2 text-on-surface font-body-md focus:border-primary focus:ring-1 focus:ring-primary appearance-none"
              >
                <option>{{ t('选择房间……') }}</option>
                <option v-for="r in rooms" :key="r">{{ r }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
              t('报废物品')
            }}</label>
            <div class="relative">
              <select
                class="w-full bg-surface border border-outline-variant rounded-lg px-4 py-2 text-on-surface font-body-md focus:border-primary focus:ring-1 focus:ring-primary appearance-none"
              >
                <option>{{ t('选择物品……') }}</option>
                <option v-for="d in damageChoices" :key="d">{{ d }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
              t('现场照片')
            }}</label>
            <div
              class="border-2 border-dashed border-outline-variant rounded-lg h-32 flex flex-col items-center justify-center bg-surface-container-lowest hover:bg-surface-container-low transition-colors cursor-pointer group"
            >
              <span
                class="font-body-md text-sm text-on-surface-variant group-hover:text-primary transition-colors"
                >{{ t('点击上传或拖拽') }}</span
              >
            </div>
          </div>
          <div>
            <label class="block font-label-lg text-label-lg text-on-surface-variant mb-1">{{
              t('详情描述')
            }}</label>
            <textarea
              class="w-full bg-surface border border-outline-variant rounded-lg px-4 py-2 text-on-surface font-body-md focus:border-primary focus:ring-1 focus:ring-primary resize-none"
              rows="2"
              :placeholder="t('提供详情……')"
            ></textarea>
          </div>
          <button
            class="mt-auto w-full py-3 bg-error hover:bg-[#a61717] text-on-error rounded-lg font-label-lg text-label-lg transition-colors flex items-center justify-center gap-2"
            type="button"
          >
            {{ t('提交报废') }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-hint {
  font-size: 13px;
  color: var(--on-surface-variant);
  padding: 8px 0;
}
</style>
