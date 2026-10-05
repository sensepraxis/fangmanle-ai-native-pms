<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 收益概览占位（文档：未来 RevPAR / ADR / OCC + AI 定价） */
import { useRouter } from 'vue-router'
import { ANALYTICS_PATH } from '../../lib/analyticsNav'

const router = useRouter()
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1>{{ t('RevPAR · ADR · OCC 趋势') }}</h1>
      <p>
        {{
          t(
            '收益概览 · 规划中。上线后将与价格助手、智能定价打通，展示收益趋势与 AI 提价/控房建议。',
          )
        }}
      </p>
    </header>
    <div class="card">
      <ul>
        <li>{{ t('RevPAR / ADR / OCC 时间序列') }}</li>
        <li>{{ t('AI 定价建议与一键回写价格日历') }}</li>
        <li>{{ t('与「渠道洞察」联动的周末需求提示') }}</li>
      </ul>
      <button type="button" class="btn" @click="router.push(ANALYTICS_PATH)">
        {{ t('返回数据洞察') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.card {
  max-width: 640px;
  padding: 24px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
}
.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}
h1 {
  margin: 0 0 10px;
  font-size: 22px;
}
.desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: #5b616e;
  line-height: 1.5;
}
ul {
  margin: 0 0 16px;
  padding-left: 18px;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.7;
}
.btn {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #c4b5fd;
  background: #faf5ff;
  color: #6d28d9;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
</style>
