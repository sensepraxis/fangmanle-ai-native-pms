<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'
import { commercialEnabled } from '../../../lib/branding'

import type { BatchRow } from './types'
import { STATUS_META, money, statusLabel } from './types'
import { localizeSeedText } from '../../../lib/localizeSeed'

defineProps<{
  selected: BatchRow | null
  dutyName: string
  aiLoading: boolean
  showOverride: boolean
  overrideNote: string
}>()

const emit = defineEmits<{
  'update:overrideNote': [string]
  runAiExplain: []
  overrideAi: []
  markRefund: []
  acceptAi: []
  saveOverride: []
}>()

function loc(s?: string | null) {
  return localizeSeedText(s)
}
</script>

<template>
  <aside class="drawer" v-if="selected">
    <div class="drawer-h">
      <div class="ttl">{{ t('批次') }} {{ selected.code }}</div>
      <span class="badge" :class="STATUS_META[selected.status].cls">{{
        statusLabel(selected.status)
      }}</span>
      <span v-if="selected.commissionLabel" class="rate-pill lg">{{
        loc(selected.commissionLabel)
      }}</span>
      <span class="meta">
        <template v-if="dutyName">{{ t('值班') }} {{ dutyName }} · </template>{{ selected.bizDate }}
      </span>
    </div>

    <div class="section" v-if="selected.commissionFormula">
      <div class="sec-t">{{ t('OTA 佣金（读取系统配置）') }}</div>
      <div class="comm-box">
        <div class="comm-main">{{ loc(selected.commissionFormula) }}</div>
        <div class="comm-sub">
          {{ t('配置费率') }} <b>{{ loc(selected.commissionLabel) }}</b> · {{ t('预估抽佣') }}
          {{ money(selected.expectedCommission) }} · {{ t('预估净到手') }}
          {{ money(selected.expectedNet) }}
        </div>
      </div>
    </div>

    <div class="section">
      <div class="sec-t">{{ t('三方对账 · 同一笔在三方系统的余额') }}</div>
      <div class="three-col">
        <div class="tc green">
          <div class="src">{{ t('PMS 应收') }}</div>
          <div class="num">{{ money(selected.pms) }}</div>
          <div class="m">{{ loc(selected.guest) }}</div>
        </div>
        <div class="tc" :class="Math.abs(selected.variance) < 0.01 ? 'green' : 'warn'">
          <div class="src">{{ t('渠道实收') }}</div>
          <div class="num">{{ money(selected.gateway) }}</div>
          <div class="m">
            {{ t(selected.channel) }}
            <template v-if="selected.commissionLabel">
              · {{ loc(selected.commissionLabel) }}</template
            >
          </div>
        </div>
        <div class="tc green">
          <div class="src">{{ t('银行到账') }}</div>
          <div class="num">{{ money(selected.bank) }}</div>
          <div class="m">{{ selected.bank == null ? t('T+1 尚未入账') : t('对公户已入账') }}</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="sec-t">
        {{ t('差额拆分 ·')
        }}<span :class="Math.abs(selected.variance) < 0.01 ? 'ok' : 'err'">
          {{ money(selected.variance) }}</span
        >
        <span class="muted">{{ t('（PMS 应收 − 渠道实收）') }}</span>
      </div>
      <div v-for="(row, i) in selected.breakdown" :key="i" class="var-block">
        <div class="var-row">
          <span
            class="badge"
            :class="row.tag === 'normal' ? 'ok' : row.tag === 'check' ? 'warn' : 'err'"
          >
            {{ t(row.tagLabel) }}</span
          >
          <div class="bar">
            <i :style="{ width: `${Math.min(100, row.pct)}%` }" :class="row.tag" />
          </div>
          <b class="r" :class="row.tag === 'normal' ? 'ok' : row.tag === 'check' ? 'warn' : 'err'">
            {{ money(row.amount) }}</b
          >
        </div>
        <div class="var-note">{{ t(row.label) }}：{{ loc(row.note) }}</div>
      </div>
    </div>

    <div class="section">
      <div class="sec-t">{{ t('本批订单（库内明细）') }}</div>
      <div class="similar orders-box" v-if="selected.similar.length">
        <div v-for="(c, i) in selected.similar" :key="i" class="case">
          <span>{{ c.title }}</span>
          <span class="ok" v-if="c.done">✓ {{ t('已对齐') }}</span>
          <span class="err" v-else>{{ t('待核') }}</span>
        </div>
      </div>
      <div v-else class="muted pad-sm">{{ t('加载订单明细中…') }}</div>
    </div>

    <div class="section">
      <div class="sec-t row-between">
        <span>{{ t('AI 差异归因 · 可被人覆盖') }}</span>
        <button
          v-if="commercialEnabled()"
          type="button"
          class="btn soft sm"
          :disabled="aiLoading"
          @click="emit('runAiExplain')"
        >
          {{
            aiLoading ? t('分析中…') : selected.cause ? t('重新生成解释') : t('生成 AI 差异解释')
          }}
        </button>
      </div>
      <div class="ai-card" v-if="selected.cause">
        <div class="ai-head">
          <span class="material-symbols-outlined">troubleshoot</span>
          <b>{{ t('AI 差异解释') }}</b>
          <span class="conf" v-if="selected.modelMeta">{{ selected.modelMeta }}</span>
          <span class="conf" v-if="selected.confidence"
            >{{ t('置信度') }} <b>{{ selected.confidence }}%</b></span
          >
        </div>
        <p class="ai-cause pre">{{ loc(selected.cause) }}</p>
      </div>
      <div v-if="showOverride" class="override">
        <textarea
          :value="overrideNote"
          rows="3"
          :placeholder="t('填写人工复核结论（将覆盖 AI 解释并留痕）')"
          @input="emit('update:overrideNote', ($event.target as HTMLTextAreaElement).value)"
        />
        <button type="button" class="btn primary sm" @click="emit('saveOverride')">
          {{ t('保存覆盖') }}
        </button>
      </div>
    </div>

    <div class="drawer-foot">
      <button type="button" class="btn sm" @click="emit('overrideAi')">
        {{ t('转人工复核') }}
      </button>
      <button type="button" class="btn danger sm" @click="emit('markRefund')">
        {{ t('标记退款异常') }}
      </button>
      <button
        type="button"
        class="btn primary sm"
        :disabled="selected.status === 'closed'"
        @click="emit('acceptAi')"
      >
        {{ t('接受 AI 解释 → 关账') }}
      </button>
    </div>
  </aside>
  <aside v-else class="drawer empty-drawer">{{ t('选中左侧批次查看三方对账详情') }}</aside>
</template>
