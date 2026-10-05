<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import type { BatchRow, Dim, Tab } from './types'
import { STATUS_META, chanClass, money, statusLabel } from './types'
import { localizeSeedText } from '../../../lib/localizeSeed'

defineProps<{
  filtered: BatchRow[]
  counts: { all: number; ai: number; human: number; closed: number }
  tab: Tab
  loading: boolean
  dim: Dim
  checked: Set<string>
  selectedId: string | number | null
}>()

const emit = defineEmits<{
  'update:tab': [Tab]
  selectAllAbnormal: [on: boolean]
  runAiMatch: []
  selectRow: [b: BatchRow]
  toggleCheck: [id: string | number, e: Event]
}>()
</script>

<template>
  <section class="list">
    <div class="list-tabs">
      <button type="button" :class="{ on: tab === 'all' }" @click="emit('update:tab', 'all')">
        {{ t('全部') }} <span class="num">{{ counts.all }}</span>
      </button>
      <button type="button" :class="{ on: tab === 'ai' }" @click="emit('update:tab', 'ai')">
        {{ t('待 AI 分析') }} <span class="num">{{ counts.ai }}</span>
      </button>
      <button type="button" :class="{ on: tab === 'human' }" @click="emit('update:tab', 'human')">
        {{ t('待人复核') }} <span class="num">{{ counts.human }}</span>
      </button>
      <button type="button" :class="{ on: tab === 'closed' }" @click="emit('update:tab', 'closed')">
        {{ t('已关账') }} <span class="num">{{ counts.closed }}</span>
      </button>
    </div>
    <div class="list-filter">
      <label class="chk">
        <input
          type="checkbox"
          :checked="checked.size > 0"
          @change="emit('selectAllAbnormal', ($event.target as HTMLInputElement).checked)"
        />
        {{ t('全选异常') }}</label
      >
      <button type="button" class="btn soft sm" @click="emit('runAiMatch')">
        {{ t('一键 AI 匹配') }}
      </button>
      <span class="muted">{{
        loading
          ? t('加载中…')
          : t('维度：{dim}', {
              dim: dim === 'batch' ? t('批次日') : dim === 'accrual' ? t('应收日') : t('到账日'),
            })
      }}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width: 36px" />
            <th>{{ t('订单/批次') }}</th>
            <th>{{ t('渠道') }}</th>
            <th>{{ t('OTA佣金') }}</th>
            <th class="r">{{ t('PMS 应收') }}</th>
            <th class="r">{{ t('渠道实收') }}</th>
            <th class="r">{{ t('银行到账') }}</th>
            <th class="r">{{ t('差额') }}</th>
            <th>{{ t('状态') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="b in filtered"
            :key="b.id"
            :class="{ cur: selectedId === b.id }"
            @click="emit('selectRow', b)"
          >
            <td @click.stop>
              <input
                type="checkbox"
                :checked="checked.has(String(b.id))"
                @change="emit('toggleCheck', b.id, $event)"
              />
            </td>
            <td>
              <div class="code">{{ b.code }}</div>
              <div class="sub">{{ localizeSeedText(b.guest) }}</div>
            </td>
            <td>
              <span class="chan" :class="chanClass(b.channel)">{{ t(b.channel) }}</span>
            </td>
            <td>
              <span
                v-if="b.commissionLabel"
                class="rate-pill"
                :title="b.commissionFormula || b.commissionLabel"
              >
                {{ b.commissionPctText }}%
              </span>
              <span v-else class="muted">—</span>
            </td>
            <td class="r">{{ money(b.pms) }}</td>
            <td class="r">{{ money(b.gateway) }}</td>
            <td class="r">{{ money(b.bank) }}</td>
            <td class="r" :class="Math.abs(b.variance) < 0.01 ? 'ok' : 'err'">
              {{ Math.abs(b.variance) < 0.01 ? money(0) : money(b.variance) }}
            </td>
            <td>
              <span class="badge" :class="STATUS_META[b.status].cls">{{
                statusLabel(b.status)
              }}</span>
            </td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="9" class="empty">{{ t('当前筛选下无批次') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
