<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import type { BatchRow } from './types'
import { STATUS_META, money, statusLabel } from './types'

defineProps<{
  open: boolean
  dateLabel: string
  dutyName: string
  canCloseBatch: boolean
  kpi: { pendingTotal: number; abnormalCount: number; abnormalAmount: number }
  counts: { closed: number }
  abnormalBatches: BatchRow[]
}>()

const emit = defineEmits<{
  close: []
  confirm: []
  jumpToAbnormal: [b: BatchRow]
}>()
</script>

<template>
  <div v-if="open" class="modal" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-h">
        <div class="ttl">{{ t('批次关账 · 不可逆') }}</div>
      </div>
      <div class="modal-b">
        <div class="item">
          <span>{{ t('对账批次') }}</span
          ><b>{{ dateLabel || t('今日') }}</b>
        </div>
        <div class="item">
          <span>{{ t('批次总额（PMS 应收）') }}</span
          ><b>{{ money(kpi.pendingTotal) }}</b>
        </div>
        <div class="item">
          <span>{{ t('已匹配') }}</span
          ><b class="ok">{{ counts.closed }} {{ t('笔') }}</b>
        </div>
        <div class="item">
          <span>{{ t('待处理') }}</span
          ><b class="err"
            >{{ kpi.abnormalCount }} {{ t('笔') }} / {{ money(kpi.abnormalAmount) }}</b
          >
        </div>
        <div class="item" v-if="dutyName">
          <span>{{ t('值班人') }}</span
          ><b>{{ dutyName }}</b>
        </div>
        <div class="warn-line" v-if="!canCloseBatch">
          {{ t('尚有异常未关关账提示') }}
        </div>
        <ul v-if="abnormalBatches.length" class="abn-list">
          <li v-for="b in abnormalBatches" :key="b.id">
            <button type="button" class="abn-link" @click="emit('jumpToAbnormal', b)">
              <span class="abn-code">{{ b.code }}</span>
              <span class="abn-ch">{{ b.channel }}</span>
              <span class="abn-var err">{{ money(b.variance) }}</span>
              <span class="badge" :class="STATUS_META[b.status].cls">{{
                statusLabel(b.status)
              }}</span>
            </button>
          </li>
        </ul>
        <div class="warn-line" v-else>{{ t('确认后批次不可修改，操作将写入审计日志。') }}</div>
      </div>
      <div class="modal-f">
        <button type="button" class="btn" @click="emit('close')">{{ t('取消') }}</button>
        <button type="button" class="btn danger" @click="emit('confirm')">
          {{ t('确认关账（不可逆）') }}
        </button>
      </div>
    </div>
  </div>
</template>
