<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { localizeSeedText } from '../../../lib/localizeSeed'
import { fmtDate, fmtDateTime, fmtMoney, statusClsMaint } from './useAssetProfileDerived'

defineProps<{
  workOrders: any[]
  woSummary: { total: number; open: number; done: number }
  selectedWoId: string | null
  woDetailOpen: boolean
  woDetailLoading: boolean
  woDetail: any
  woProgressSteps: string[]
  woProgressStep: number
  assetName: string
  assetNo: string
}>()

const emit = defineEmits<{
  goWorkOrderCreate: []
  openDetail: [w: { id: string; maintId: number }]
  closeDetail: []
}>()
</script>

<template>
  <section id="section-workorders" class="card-clean wo-card wo-bottom">
    <div class="wo-head">
      <div>
        <h2>{{ t('关联工单') }}</h2>
        <p v-if="workOrders.length" class="wo-sub">
          {{ t('共') }} {{ woSummary.total }} {{ t('条 · 待办') }} {{ woSummary.open }} ·
          {{ t('已完成') }} {{ woSummary.done }}
        </p>
      </div>
      <button class="btn-new-wo" type="button" @click="emit('goWorkOrderCreate')">
        <span class="material-symbols-outlined">add</span>
        {{ t('新建关联工单') }}
      </button>
    </div>
    <p v-if="!workOrders.length" class="empty-hint">{{ t('暂无关联工单') }}</p>
    <table v-else class="wo-table">
      <thead>
        <tr>
          <th>{{ t('工单编号') }}</th>
          <th>{{ t('类型') }}</th>
          <th>{{ t('计划日期') }}</th>
          <th>{{ t('处理人') }}</th>
          <th>{{ t('状态') }}</th>
          <th class="right">{{ t('操作') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="w in workOrders" :key="w.id" :class="{ 'wo-row-active': selectedWoId === w.id }">
          <td class="num">{{ w.id }}</td>
          <td>
            <span
              class="wo-tag"
              :style="{ background: w.typeCls, color: w.typeOn }"
              :title="w.note || undefined"
              >{{ localizeSeedText(w.type) }}</span
            >
          </td>
          <td class="num muted">
            <div>{{ w.dueDate }}</div>
            <div v-if="w.rawStatus === 'done' && w.completedAt" class="wo-done-at">
              {{ t('完成 {time}', { time: w.completedAt }) }}
            </div>
          </td>
          <td>{{ localizeSeedText(w.owner) }}</td>
          <td>
            <span :style="{ color: w.statusCls, fontWeight: 500 }">{{ w.status }}</span>
          </td>
          <td class="right">
            <button type="button" class="link-btn" @click="emit('openDetail', w)">
              {{ selectedWoId === w.id ? t('收起') : t('查看') }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="woDetailOpen" class="wo-detail-panel">
      <div v-if="woDetailLoading" class="wo-detail-loading">{{ t('加载工单详情…') }}</div>
      <template v-else-if="woDetail">
        <div class="wo-detail-head">
          <div>
            <p class="wo-detail-k">{{ t('工单编号') }}</p>
            <h3 class="wo-detail-id">{{ woDetail.wo_no }}</h3>
          </div>
          <button
            type="button"
            class="wo-detail-close"
            :aria-label="t('关闭')"
            @click="emit('closeDetail')"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="wo-detail-top">
          <span class="wo-detail-status" :style="{ color: statusClsMaint(woDetail.status) }">
            {{ t(woDetail.status_label || '') }}</span
          >
          <span
            class="wo-tag"
            :style="{
              background: 'var(--secondary-container)',
              color: 'var(--on-secondary-container)',
            }"
          >
            {{ localizeSeedText(woDetail.task_type) || t('维保') }}</span
          >
          <span v-if="woDetail.is_overdue" class="wo-detail-overdue">{{ t('已逾期') }}</span>
          <span
            v-else-if="woDetail.days_until_due != null && woDetail.status !== 'done'"
            class="wo-detail-due"
          >
            {{
              woDetail.days_until_due >= 0
                ? t('{n} 天后到期', { n: woDetail.days_until_due })
                : t('逾期 {n} 天', { n: Math.abs(woDetail.days_until_due) })
            }}</span
          >
        </div>

        <p class="wo-detail-title">
          {{ localizeSeedText(woDetail.note || woDetail.task_type) || t('维保工单') }}
        </p>

        <div class="wo-detail-grid">
          <div>
            <p class="lbl">{{ t('计划日期') }}</p>
            <p class="val num">{{ fmtDate(woDetail.due_date) }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('创建时间') }}</p>
            <p class="val num">{{ fmtDateTime(woDetail.created_at) }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('完成时间') }}</p>
            <p class="val num">{{ fmtDateTime(woDetail.completed_at) }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('处理人') }}</p>
            <p class="val">{{ localizeSeedText(woDetail.owner) || '—' }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('维修费用') }}</p>
            <p class="val num">{{ fmtMoney(woDetail.cost) }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('关联设备') }}</p>
            <p class="val">
              {{ localizeSeedText(woDetail.asset?.name || assetName) }} ·
              {{ woDetail.asset?.asset_no || assetNo }}
            </p>
          </div>
        </div>

        <div class="wo-detail-progress">
          <p class="lbl">{{ t('处理进度') }}</p>
          <div class="wo-flow-labels">
            <span
              v-for="(s, i) in woProgressSteps"
              :key="s"
              :class="{ on: woProgressStep > i || (woDetail.status === 'done' && i === 3) }"
              >{{ t(s) }}</span
            >
          </div>
          <div class="wo-flow-track">
            <template v-for="(s, i) in woProgressSteps" :key="'dot-' + s">
              <span
                class="wo-flow-dot"
                :class="{ on: woProgressStep > i || (woDetail.status === 'done' && i <= 3) }"
              />
              <span
                v-if="i < woProgressSteps.length - 1"
                class="wo-flow-line"
                :class="{ on: woProgressStep > i + 1 }"
              />
            </template>
          </div>
        </div>

        <div class="wo-detail-timeline">
          <p class="lbl">{{ t('流转记录') }}</p>
          <div class="wo-tl-list">
            <div
              v-for="(ev, i) in woDetail.timeline || []"
              :key="i"
              class="wo-tl-item"
              :class="{ done: ev.done }"
            >
              <span class="wo-tl-dot" />
              <div>
                <div class="wo-tl-label">{{ t(ev.label || '') }}</div>
                <div class="wo-tl-time num">{{ fmtDateTime(ev.time) }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
