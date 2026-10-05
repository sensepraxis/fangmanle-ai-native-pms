<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 合并资产确认 —— 数据来自 /api/oneid/guests/:id/assets
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import OneIdFlowSubnav from '../../components/OneIdFlowSubnav.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const err = ref('')
const confirmed = ref(false)
const assets = ref<any>(null)

const canFinish = computed(() => Boolean(confirmed.value && assets.value?.guest_id))

onMounted(async () => {
  loading.value = true
  try {
    const id =
      Number(route.query.guestId || 0) || Number(sessionStorage.getItem('fml_merged_guest_id') || 0)
    if (!id) {
      err.value = t('缺少合并后的客人 ID。请先完成归并审核。')
      return
    }
    assets.value = await api.oneidGuestAssets(id)
  } catch (e: any) {
    err.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
})

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function finish() {
  if (!canFinish.value) return
  router.push(`/guests/${assets.value.guest_id}`)
}
</script>

<template>
  <div class="page">
    <OneIdFlowSubnav
      :on-next="finish"
      :next-disabled="!canFinish"
      :next-label="t('完成 → 查看 360')"
    />
    <div class="max-w-3xl mx-auto space-y-5">
      <div class="pb-3 border-b border-outline-variant">
        <h1 class="text-2xl font-bold m-0">{{ t('合并资产确认') }}</h1>
        <p class="text-sm text-on-surface-variant mt-1 m-0">
          {{ t('核对合并后资产，勾选确认后点顶部「完成 → 查看 360」进入客户详情。') }}
        </p>
      </div>

      <div v-if="loading" class="text-sm text-on-surface-variant py-8">{{ t('加载中…') }}</div>
      <div
        v-else-if="err"
        class="rounded-xl border border-red-200 bg-red-50 text-red-800 p-4 text-sm"
      >
        {{ err }}
      </div>
      <template v-else-if="assets">
        <div
          class="rounded-xl border-l-4 border-primary bg-surface-container-lowest border border-outline-variant p-4 text-sm"
        >
          {{ assets.insight }}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
            <div class="text-xs text-on-surface-variant mb-2">{{ t('累计 LTV') }}</div>
            <div class="text-2xl font-bold text-primary">{{ money(assets.ltv) }}</div>
          </div>
          <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
            <div class="text-xs text-on-surface-variant mb-2">{{ t('会员等级') }}</div>
            <div class="text-xl font-bold">{{ t(assets.vip_label || '—') }}</div>
            <div class="text-xs text-on-surface-variant mt-1">{{ assets.city || '—' }}</div>
          </div>
          <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
            <div class="text-xs text-on-surface-variant mb-2">{{ t('有效优惠券') }}</div>
            <div class="text-2xl font-bold">{{ assets.active_coupon_count }}</div>
            <div class="text-xs text-on-surface-variant mt-1">
              {{ t('共') }} {{ assets.coupon_count }} {{ t('张记录') }}
            </div>
          </div>
        </div>

        <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
          <div class="font-semibold text-sm mb-3">
            {{ assets.name }} · #{{ assets.guest_id }} · {{ assets.one_id }}
          </div>
          <div class="text-xs text-on-surface-variant mb-2">
            {{ t('手机') }} {{ assets.phone_mask }} · {{ t('订单') }} {{ assets.order_count }}
            {{ t('笔') }}
          </div>
          <div class="text-xs font-semibold mb-1">{{ t('近期订单') }}</div>
          <ul class="m-0 p-0 list-none space-y-2">
            <li
              v-for="o in assets.orders || []"
              :key="o.id"
              class="text-sm flex justify-between gap-2 border-b border-outline-variant/50 pb-2"
            >
              <span>{{ o.order_no }} · {{ o.check_in }} · {{ o.room_type || t('客房') }}</span>
              <span class="shrink-0"
                >{{ t(o.status_cn || o.status || '—') }} · {{ money(o.total_amount) }}</span
              >
            </li>
            <li v-if="!(assets.orders || []).length" class="text-sm text-on-surface-variant">
              {{ t('暂无订单') }}
            </li>
          </ul>
          <div class="text-xs font-semibold mt-4 mb-1">{{ t('优惠券') }}</div>
          <ul class="m-0 p-0 list-none space-y-1">
            <li v-for="c in assets.coupons || []" :key="c.code" class="text-sm">
              {{ c.code }} · {{ c.name }} · {{ c.discount_label || '' }}
            </li>
            <li v-if="!(assets.coupons || []).length" class="text-sm text-on-surface-variant">
              {{ t('暂无券') }}
            </li>
          </ul>
        </div>

        <label class="flex items-start gap-2 text-sm cursor-pointer">
          <input v-model="confirmed" type="checkbox" class="mt-1" />
          <span>{{ t('已核对积分/会员/优惠券与订单归属无误，完成 OneID 合并确认。') }}</span>
        </label>
      </template>
    </div>
  </div>
</template>
