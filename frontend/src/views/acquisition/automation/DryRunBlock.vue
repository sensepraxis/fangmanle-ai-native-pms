<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import type { useAutoRuleForm } from './useAutoRuleForm'
import type { useAutoRuleApi } from './useAutoRuleApi'

const props = defineProps<{
  formApi: ReturnType<typeof useAutoRuleForm>
  ruleApi: ReturnType<typeof useAutoRuleApi>
}>()

const { dry } = props.formApi
const { rules, h5Guests, dryResult, showHistory, historyRows, runDry } = props.ruleApi
</script>

<template>
  <div>
    <div class="dry">
      <h4>{{ t('试跑') }}</h4>
      <div class="dry-row">
        <select v-model="dry.rule_id">
          <option value="">{{ t('选择规则') }}</option>
          <option
            v-for="r in rules.filter((x) => x.status !== 'expired')"
            :key="r.id"
            :value="r.id"
          >
            {{ r.name }}
          </option>
        </select>
        <select v-model="dry.guest_id">
          <option value="">{{ t('选择客户') }}</option>
          <option v-for="g in h5Guests" :key="g.id || g.guest_id" :value="g.id || g.guest_id">
            {{ g.name }} · {{ g.phone || g.id }}
          </option>
        </select>
        <button type="button" class="btn pri" @click="runDry">{{ t('试跑') }}</button>
      </div>
      <div v-if="dryResult?.cards?.length" class="dry-result">
        <div
          v-for="(card, i) in dryResult.cards"
          :key="i"
          :class="card.matched ? 'dry-hit' : 'dry-miss'"
        >
          {{ card.matched ? t('命中') : t('未命中') }}
          {{ card.name || '客户 ' + card.customer_id }}
          <span v-if="!card.matched && card.reason"> · {{ card.reason }}</span>
          <ul v-if="card.steps?.length" class="dry-list">
            <li v-for="(s, j) in card.steps" :key="j">{{ s.ok ? '✓' : '✗' }} {{ s.text }}</li>
          </ul>
        </div>
      </div>
    </div>

    <div v-if="showHistory" class="history">
      <div class="hist-hd">
        <b>{{ t('触发历史') }}</b>
        <button type="button" class="link" @click="showHistory = false">{{ t('关闭') }}</button>
      </div>
      <div v-for="h in historyRows" :key="h.id" class="hist-line">
        {{ h.triggered_at }} · {{ h.customer_name || h.customer_id }} ·
        {{ h.matched ? t('成功') : t('拦截') }}
        <span v-if="h.reason">（{{ h.reason }}）</span>
      </div>
      <div v-if="!historyRows.length" class="empty">{{ t('暂无流水') }}</div>
    </div>
  </div>
</template>
