<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { fmt, toast } from '../lib/ui'

const bizDate = ref(new Date().toISOString().slice(0, 10))
const result = ref<any>(null)
const history = ref<any[]>([])

async function runAudit() {
  result.value = await api.runAudit({ hotel_id: hotelStore.hotelId, biz_date: bizDate.value })
  history.value.unshift({
    biz_date: bizDate.value,
    status: result.value.status,
    revenue: result.value.revenue,
    exceptions: result.value.exceptions,
    ran_at: result.value.ran_at,
  })
  toast(t('夜审完成'))
}

onMounted(async () => {
  // 加载历史（这里复用 dashboard 数据简化）：可选拉一个 /api/audit-history 端点
  history.value = []
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('智能夜审') }}</h1>
      <p>{{ t('每日凌晨自动跑账，校验营收一致性并输出差异项。') }}</p>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px">
      <!-- 左：触发器 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('手动触发') }}</span>
        </div>
        <div style="padding: 18px 20px">
          <div style="margin-bottom: 14px">
            <div style="font-size: 12px; color: #5b616e; margin-bottom: 6px">
              {{ t('业务日期') }}
            </div>
            <input
              v-model="bizDate"
              type="date"
              style="
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #e7e9ee;
                border-radius: 8px;
                background: #fff;
                font-size: 13px;
                outline: none;
              "
            />
          </div>
          <button
            class="btn btn-primary"
            style="width: 100%; justify-content: center"
            @click="runAudit"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              style="width: 14px; height: 14px"
            >
              <path d="M21 12a9 9 0 1 1-3-6.7L21 8" />
              <path d="M21 3v5h-5" />
            </svg>
            {{ t('运行夜审') }}
          </button>

          <div
            v-if="result"
            style="
              margin-top: 18px;
              padding: 14px;
              background: #f5f6f8;
              border-radius: 10px;
              border: 1px solid #e7e9ee;
            "
          >
            <div style="font-size: 12px; color: #5b616e; margin-bottom: 8px">
              {{ t('本次结果') }}
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px">
              <div>
                <div style="color: #9aa1ad; font-size: 11px">{{ t('状态') }}</div>
                <div style="font-weight: 600">
                  <span
                    class="pill"
                    :class="result.status === 'passed' ? 'pill-green' : 'pill-rose'"
                  >
                    {{ result.status === 'passed' ? t('通过') : t('异常') }}</span
                  >
                </div>
              </div>
              <div>
                <div style="color: #9aa1ad; font-size: 11px">{{ t('营收') }}</div>
                <div style="font-weight: 600; font-variant-numeric: tabular-nums">
                  {{ fmt(result.revenue) }}
                </div>
              </div>
              <div>
                <div style="color: #9aa1ad; font-size: 11px">{{ t('过夜房晚') }}</div>
                <div style="font-weight: 600">{{ result.room_nights }}</div>
              </div>
              <div>
                <div style="color: #9aa1ad; font-size: 11px">{{ t('异常数') }}</div>
                <div style="font-weight: 600; color: #be123c">{{ result.exceptions }}</div>
              </div>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #9aa1ad">
              {{ t('运行于') }} {{ result.ran_at }}
            </div>
          </div>
        </div>
      </div>

      <!-- 右：历史 + AI -->
      <div>
        <div class="card-clean" style="overflow: hidden; margin-bottom: 16px">
          <div class="card-head">
            <span>{{ t('历史记录') }}</span>
            <span style="font-size: 11px; color: #9aa1ad">{{ t('近 7 日') }}</span>
          </div>
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('日期') }}</th>
                <th>{{ t('状态') }}</th>
                <th class="num">{{ t('营收') }}</th>
                <th class="num">{{ t('房晚') }}</th>
                <th class="num">{{ t('异常') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(h, i) in history" :key="i">
                <td style="font-variant-numeric: tabular-nums">{{ h.biz_date }}</td>
                <td>
                  <span class="pill" :class="h.status === 'passed' ? 'pill-green' : 'pill-rose'">
                    {{ h.status === 'passed' ? t('通过') : t('异常') }}</span
                  >
                </td>
                <td class="num">{{ fmt(h.revenue) }}</td>
                <td class="num">{{ h.room_nights }}</td>
                <td class="num" :style="{ color: h.exceptions > 0 ? '#be123c' : '#5b616e' }">
                  {{ h.exceptions }}
                </td>
              </tr>
              <tr v-if="!history.length">
                <td colspan="5" style="text-align: center; color: #9aa1ad; padding: 30px">
                  {{ t('暂无历史，请运行夜审') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="ai-card">
          <div class="ttl">{{ t('✦ AI 夜审提示') }}</div>
          <ul>
            <li>{{ t('每日 03:00 自动运行（生产环境）；手动触发仅作应急。') }}</li>
            <li>{{ t('异常项通常为：未平账 / OTA 渠道对账差异 / 房费与加项不一致。') }}</li>
            <li>{{ t('异常 0 时可一键闭店；&gt;0 时系统自动推送告警至店长企微。') }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
