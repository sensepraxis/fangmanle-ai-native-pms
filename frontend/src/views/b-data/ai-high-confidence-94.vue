<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 冲突队列 —— 数据来自 /api/oneid/merge-case
 * 企微 H5 待裁定冲突在「归并台」处理；本页仅核对同号档案并选定主档。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import OneIdFlowSubnav from '../../components/OneIdFlowSubnav.vue'

const router = useRouter()
const loading = ref(true)
const err = ref('')
const mergeCase = ref<any>(null)
const masterPick = ref<number | null>(null)

const guests = computed(() => mergeCase.value?.guests || [])
const suggestedId = computed(
  () => mergeCase.value?.suggested_primary_id || guests.value[0]?.guest_id || null,
)
const canGoResolution = computed(() => Boolean(masterPick.value && guests.value.length >= 2))

onMounted(async () => {
  loading.value = true
  err.value = ''
  try {
    mergeCase.value = await api.oneidMergeCase()
    masterPick.value =
      mergeCase.value?.suggested_primary_id ?? mergeCase.value?.guests?.[0]?.guest_id ?? null
  } catch (e: any) {
    err.value = t(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function goResolution() {
  const ids = guests.value.map((g: any) => g.guest_id)
  const primary = masterPick.value || suggestedId.value
  const secondary = ids.find((id: number) => id !== primary)
  if (primary && secondary) {
    sessionStorage.setItem('fml_merge_primary', String(primary))
    sessionStorage.setItem('fml_merge_secondary', String(secondary))
    if (mergeCase.value?.conflict_id) {
      sessionStorage.setItem('fml_merge_conflict', String(mergeCase.value.conflict_id))
    }
    router.push({
      path: '/b-data/one-id-resolution',
      query: {
        primary: String(primary),
        secondary: String(secondary),
        conflictId: mergeCase.value?.conflict_id ? String(mergeCase.value.conflict_id) : undefined,
      },
    })
  } else {
    router.push('/b-data/one-id-resolution')
  }
}
</script>

<template>
  <div class="page">
    <OneIdFlowSubnav :on-next="goResolution" :next-disabled="!canGoResolution" />
    <div class="mb-6">
      <h1 class="text-2xl font-bold m-0 mb-2">{{ t('冲突队列') }}</h1>
      <p class="text-sm text-on-surface-variant m-0">
        {{ t('同号档案来自数据库扫描。选定主档案后，点顶部「下一步：归并审核」进入合并对比。') }}
      </p>
    </div>

    <div v-if="loading" class="text-sm text-on-surface-variant py-8">{{ t('加载中…') }}</div>
    <div
      v-else-if="err"
      class="rounded-xl border border-red-200 bg-red-50 text-red-800 p-4 text-sm"
    >
      {{ err }}
    </div>
    <template v-else>
      <section
        class="mb-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      >
        <div class="text-xs text-on-surface-variant mb-1">{{ t('当前案例') }}</div>
        <div class="font-semibold text-sm">
          {{ mergeCase?.match_type === 'phone_exact_multi' ? t('全号重复') : t('手机号冲突') }}
          · {{ mergeCase?.phone_mask || mergeCase?.phone }}
          <span v-if="mergeCase?.conflict_id" class="text-on-surface-variant font-normal">
            · {{ t('冲突 #{id}', { id: mergeCase.conflict_id }) }}</span
          >
        </div>
        <p class="text-xs text-on-surface-variant mt-1 m-0">
          {{ mergeCase?.message ? t(mergeCase.message) : '' }}
        </p>
      </section>

      <div class="grid gap-3 md:grid-cols-2">
        <article
          v-for="g in guests"
          :key="g.guest_id"
          class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
          :class="{ 'ring-2 ring-primary/40': masterPick === g.guest_id }"
        >
          <div class="flex items-start justify-between gap-2 mb-3">
            <div>
              <div class="font-bold text-base">{{ g.name }} · #{{ g.guest_id }}</div>
              <div class="text-xs text-on-surface-variant mt-1">
                {{ g.phone_mask }} · {{ g.vip_label }} · {{ g.one_id }}
              </div>
            </div>
            <label class="text-xs font-semibold flex items-center gap-1 cursor-pointer">
              <input v-model="masterPick" type="radio" :value="g.guest_id" />
              {{ t('主档案') }}</label
            >
          </div>
          <div class="grid grid-cols-3 gap-2 text-center text-xs mb-3">
            <div class="rounded-lg bg-surface-container-low p-2">
              <div class="font-bold text-primary">{{ g.order_count }}</div>
              {{ t('订单') }}
            </div>
            <div class="rounded-lg bg-surface-container-low p-2">
              <div class="font-bold text-primary">{{ money(g.ltv) }}</div>
              LTV
            </div>
            <div class="rounded-lg bg-surface-container-low p-2">
              <div class="font-bold text-primary">{{ g.coupon_count }}</div>
              {{ t('券') }}
            </div>
          </div>
          <div class="text-xs text-on-surface-variant mb-1">{{ t('渠道身份') }}</div>
          <div class="flex flex-wrap gap-1 mb-3">
            <span
              v-for="i in g.identities || []"
              :key="i.source + i.external_id"
              class="px-2 py-0.5 rounded bg-surface-container text-[11px]"
            >
              {{ t(i.source_cn || i.source || '') }}</span
            >
            <span v-if="!(g.identities || []).length" class="text-[11px] text-on-surface-variant">{{
              t('暂无')
            }}</span>
          </div>
          <div class="text-xs text-on-surface-variant mb-1">{{ t('近期订单') }}</div>
          <ul class="m-0 p-0 list-none space-y-1">
            <li
              v-for="o in (g.orders || []).slice(0, 3)"
              :key="o.id"
              class="text-xs flex justify-between gap-2"
            >
              <span class="truncate">{{ o.check_in }} · {{ o.room_type || t('客房') }}</span>
              <span class="shrink-0"
                >{{ t(o.status_cn || o.status || '—') }} · {{ money(o.total_amount) }}</span
              >
            </li>
            <li v-if="!(g.orders || []).length" class="text-xs text-on-surface-variant">
              {{ t('暂无订单') }}
            </li>
          </ul>
          <button
            type="button"
            class="mt-3 text-xs text-primary font-semibold"
            @click="router.push(`/guests/${g.guest_id}`)"
          >
            {{ t('打开 360 →') }}
          </button>
        </article>
      </div>
    </template>
  </div>
</template>
