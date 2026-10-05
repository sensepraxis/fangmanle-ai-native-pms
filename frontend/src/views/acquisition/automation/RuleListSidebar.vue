<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import type { useAutoRuleApi } from './useAutoRuleApi'

const props = defineProps<{
  ruleApi: ReturnType<typeof useAutoRuleApi>
}>()

const { statusFilter, statusCounts, filteredRules, fmtNum, editRule, toggleRule, removeRule } =
  props.ruleApi

function statusLabel(status: string) {
  const map: Record<string, string> = {
    active: t('启用中'),
    paused: t('已暂停'),
    draft: t('草稿'),
    expired: t('已过期'),
  }
  return map[status] || status
}
</script>

<template>
  <div>
    <h3>{{ t('已配置规则') }}</h3>
    <div class="chips">
      <button
        v-for="c in [
          { k: 'all', t: `${t('全部')} (${statusCounts.all})` },
          { k: 'active', t: `${t('启用中')} (${statusCounts.active})` },
          { k: 'draft', t: `${t('草稿')} (${statusCounts.draft})` },
          { k: 'paused', t: `${t('已暂停')} (${statusCounts.paused})` },
        ]"
        :key="c.k"
        type="button"
        class="filter-chip"
        :class="{ on: statusFilter === c.k }"
        @click="statusFilter = c.k"
      >
        {{ c.t }}
      </button>
    </div>
    <div class="tbl-wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t('规则') }}</th>
            <th>{{ t('触发器') }}</th>
            <th>{{ t('7 日') }}</th>
            <th>{{ t('上次') }}</th>
            <th>{{ t('状态') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredRules" :key="r.id">
            <td>
              <div class="name">{{ r.name }}</div>
            </td>
            <td>
              <span class="pill" :class="r.scan_frequency === 'realtime' ? 'g' : 'b'">{{
                r.event_pill || r.scan_frequency
              }}</span>
            </td>
            <td>
              <b>{{ fmtNum(r.trigger_count_7d) }}</b>
            </td>
            <td>{{ r.last_triggered_text || '—' }}</td>
            <td>
              <span class="st" :class="r.status">{{ statusLabel(r.status) }}</span>
            </td>
            <td class="acts">
              <button type="button" class="row-act" @click="editRule(r)">{{ t('编辑') }}</button>
              <button type="button" class="row-act" @click="toggleRule(r)">
                {{ r.status === 'active' ? t('暂停') : t('启用') }}
              </button>
              <button type="button" class="row-act danger" @click="removeRule(r)">
                {{ t('删除') }}
              </button>
            </td>
          </tr>
          <tr v-if="!filteredRules.length">
            <td colspan="6" class="empty">{{ t('暂无规则') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
