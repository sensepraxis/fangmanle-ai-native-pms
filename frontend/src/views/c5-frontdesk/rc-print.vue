<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 入住登记单打印页 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { fmt, toast } from '../../lib/ui'

const route = useRoute()
const router = useRouter()
const data = ref<any>(null)
const err = ref('')

const orderId = computed(() => Number(route.query.orderId || 0))

async function load() {
  err.value = ''
  data.value = null
  if (!orderId.value) {
    err.value = t('缺少 orderId')
    return
  }
  try {
    data.value = await api.orderRc(orderId.value, false)
  } catch (e: any) {
    err.value = e?.message || t('加载失败')
  }
}

function printPage() {
  window.print()
}

onMounted(load)
watch(orderId, load)
</script>

<template>
  <div class="page">
    <div class="no-print mb-4 flex gap-2 flex-wrap">
      <button type="button" class="btn btn-ghost" @click="router.back()">{{ t('返回') }}</button>
      <button type="button" class="btn btn-primary" :disabled="!data" @click="printPage">
        {{ t('打印登记单') }}
      </button>
    </div>
    <p v-if="err" class="text-error">{{ err }}</p>
    <div v-else-if="data" class="rc-sheet card-clean card-pad">
      <h1 style="margin: 0 0 8px; font-size: 20px">{{ t('入住登记单') }}</h1>
      <p style="margin: 0 0 16px; font-size: 12px; color: #666">
        {{ t('打印时') }}{{ t('间') }} {{ data.printed_at }} · {{ data.hotel_note }}
      </p>
      <div
        style="
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px 24px;
          font-size: 13px;
          margin-bottom: 16px;
        "
      >
        <div>
          {{ t('订单号：') }} <b>{{ data.order?.order_no }}</b>
        </div>
        <div>
          {{ t('房号：') }} <b>{{ data.order?.room_no || '—' }}</b>
        </div>
        <div>{{ t('入住：') }}{{ data.order?.check_in }}</div>
        <div>{{ t('离店：') }}{{ data.order?.check_out }}</div>
        <div>{{ t('房型：') }}{{ data.order?.room_type_name }}</div>
        <div>{{ t('金额：') }}{{ fmt(data.order?.total_amount) }}</div>
      </div>
      <h2 style="font-size: 15px; margin: 0 0 8px">{{ t('住客登记') }}</h2>
      <table class="data" style="width: 100%">
        <thead>
          <tr>
            <th>{{ t('姓名') }}</th>
            <th>{{ t('角色') }}</th>
            <th>{{ t('证件类型') }}</th>
            <th>{{ t('证件号') }}</th>
            <th>{{ t('房号') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(g, i) in data.guests" :key="i">
            <td>{{ g.guest_name }}</td>
            <td>{{ g.is_master ? t('主客') : t('同住') }}</td>
            <td>{{ g.id_doc_type || '—' }}</td>
            <td class="mono">{{ g.id_doc_display || '—' }}</td>
            <td>{{ g.room_no || '—' }}</td>
          </tr>
          <tr v-if="!(data.guests || []).length">
            <td colspan="5" style="text-align: center; color: #999">{{ t('暂无入住登记') }}</td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 24px; font-size: 12px; color: #666">
        {{ t('客人签名：________________ 前台：________________') }}
      </p>
    </div>
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
  .rc-sheet {
    box-shadow: none;
    border: none;
  }
}
</style>
