<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// AI 智能布草与易耗品预测 —— 布草线第 2 步
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
const route = useRoute()
const router = useRouter()
const forecast = ref<any[]>([])
const forecastYTicks = ref<number[]>([500, 400, 300, 200, 100, 0])
const suggestions = ref<any[]>([])
const anomalies = ref<any[]>([])
const focusSummary = ref('')

const LINEN_KW = /布草|床单|浴巾|枕套|面巾|毛巾|被套|浴衣/

function goRestock() {
  router.push(')/c7-supplies/smart-restocking')
}

function fmtDay(iso: string, i: number) {
  if (!iso) return `D${i + 1}`
  // 原型：10/1；兼容 2026-08-07 → 08/07
  const m = String(iso).match(/(\d{4})-(\d{2})-(\d{2})/)
  if (m) return `${m[2]}/${m[3]}`
  const p = iso.slice(5).replace('-', '/')
  return p || `D${i + 1}`
}

function niceMax(n: number) {
  if (n <= 100) return 100
  if (n <= 200) return 200
  if (n <= 300) return 300
  if (n <= 500) return 500
  if (n <= 800) return 800
  if (n <= 1000) return 1000
  return Math.ceil(n / 100) * 100
}

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'linen')
    const full = await api.suppliesBoard(hotelStore.hotelId)
    const insightId = Number(route.query.insight_id || 0)
    if (insightId) {
      const ins = [...(board?.insights || []), ...(full?.insights || [])].find(
        (x: any) => Number(x.id) === insightId,
      )
      focusSummary.value = ins ? `洞察：${ins.title}` : ''
    } else {
      focusSummary.value = ''
    }

    const trend = board?.linen_trend || []
    if (trend.length) {
      const loads = trend.map((t: any) => Number(t.pending_wash || 0) + Number(t.in_wash || 0))
      const maxLoad = Math.max(1, ...loads)
      const maxY = niceMax(maxLoad)
      forecastYTicks.value = [
        maxY,
        Math.round(maxY * 0.8),
        Math.round(maxY * 0.6),
        Math.round(maxY * 0.4),
        Math.round(maxY * 0.2),
        0,
      ]
      const peakIdx = loads.indexOf(Math.max(...loads))
      const splitAt = Math.max(0, trend.length - 3)
      forecast.value = trend.map((t: any, i: number) => {
        const loadAmt = loads[i]
        const hPct = Math.max(4, Math.round((loadAmt / maxY) * 100))
        return {
          day: fmtDay(t.biz_date, i),
          value: loadAmt,
          hPct,
          predicted: i >= splitAt,
          peak: i === peakIdx && loadAmt > 0,
        }
      })
    } else {
      forecast.value = []
      forecastYTicks.value = [500, 400, 300, 200, 100, 0]
    }

    const sug: any[] = []
    for (const x of board?.insights || []) {
      if (['forecast', 'restock', 'turnover', 'replace'].includes(x.category)) {
        sug.push({
          name: x.title || t('补货建议'),
          risk: Number(x.impact_amount || 0) >= 1000 ? t('高风险') : t('中风险'),
          riskColor: Number(x.impact_amount || 0) >= 1000 ? 'error' : 'variant',
          stock: t('见洞察'),
          gap: x.impact_amount ? `¥${Number(x.impact_amount).toLocaleString('zh-CN')}` : '-',
          suggest: (x.recommendation || t('执行建议')).slice(0, 24),
        })
      }
    }
    const lowLinen = (board?.supplies || []).filter(
      (s: any) => s.low && LINEN_KW.test(String(s.name || '') + String(s.category || '')),
    )
    for (const s of lowLinen.slice(0, 4)) {
      sug.push({
        name: s.name,
        risk: t('高风险'),
        riskColor: 'error',
        stock: `${s.current_stock}${s.unit || ''}`,
        gap: `${s.gap}${s.unit || ''}`,
        suggest: `建议补货 ${Math.ceil(Number(s.gap || 0) + Number(s.safety_stock || 0))} ${s.unit || ''}`,
      })
    }
    suggestions.value = sug.slice(0, 6)

    const alerts = board?.alerts || []
    if (alerts.length) {
      anomalies.value = alerts.map((a: any) => ({
        room: a.room_no || a.floor || '-',
        item: a.supply_name || t('物资'),
        std: a.severity === 'high' ? t('低') : t('中'),
        act: a.severity === 'high' ? t('高') : a.severity === 'mid' ? t('偏高') : t('关注'),
        reason: a.message || t('异常消耗'),
        action: t('查看详情'),
      }))
    } else {
      anomalies.value = []
    }
  } catch {
    forecast.value = []
    suggestions.value = []
    anomalies.value = []
    focusSummary.value = ''
  }
}
onMounted(load)
watch(() => [hotelStore.hotelId, route.query.insight_id], load)
</script>

<template>
  <div class="page">
    <p v-if="focusSummary" style="margin: 0 0 12px; font-size: 13px; color: var(--tertiary)">
      {{ focusSummary }}
    </p>
    <!-- 页面标题 -->
    <div class="page-head">
      <h1>{{ t('AI 智能布草与易耗品预测') }}</h1>
      <p>{{ t('基于历史数据与即将到来的预订，AI 为您提供库存预警与采购建议。') }}</p>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 16px">
      <button class="btn btn-ghost" type="button">
        <span class="material-symbols-outlined">download</span> {{ t('导出报告') }}
      </button>
      <button
        class="btn btn-primary"
        type="button"
        style="box-shadow: -2px 0 0 0 var(--tertiary)"
        @click="goRestock"
      >
        <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
          >shopping_cart</span
        >
        {{ t('一键生成采购单') }}
      </button>
    </div>

    <!-- Bento 网格 -->
    <div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px">
      <!-- 1. 库存/洗涤负荷预测 (span 8) —— 柱状图对齐原型 -->
      <div class="card-clean" style="grid-column: span 8; padding: 24px">
        <div
          style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
          "
        >
          <h3
            style="
              font-size: 18px;
              font-weight: 600;
              color: var(--on-surface);
              display: flex;
              align-items: center;
              gap: 8px;
              margin: 0;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--primary)">monitoring</span>
            {{ t('布草洗涤负荷预测（近7日）') }}
          </h3>
          <select class="toolbar-input" style="appearance: none; cursor: pointer">
            <option>{{ t('所有品类 (All Categories)') }}</option>
            <option>{{ t('布草 (Linens)') }}</option>
            <option>{{ t('洗漱用品 (Toiletries)') }}</option>
          </select>
        </div>

        <p v-if="!forecast.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <template v-else>
          <div class="chart-frame">
            <div class="y-axis">
              <span v-for="(item, i) in forecastYTicks" :key="i">{{ item }}</span>
            </div>
            <div class="bars-area">
              <div v-for="(b, i) in forecast" :key="i" class="bar-col">
                <div class="bar-track">
                  <div v-if="b.peak" class="peak-tag">{{ t('假期高峰') }}</div>
                  <div
                    class="bar"
                    :class="b.predicted ? 'chart-bar-predicted' : 'chart-bar-primary'"
                    :style="{ height: b.hPct + '%' }"
                    :title="`${b.day}: ${b.value}`"
                  />
                </div>
                <span class="day-label" :class="{ predicted: b.predicted }">{{ b.day }}</span>
              </div>
            </div>
          </div>
          <div class="chart-legend">
            <div class="legend-item">
              <span class="chart-bar-primary legend-dot" />
              <span>{{ t('实际消耗 (Actual)') }}</span>
            </div>
            <div class="legend-item">
              <span class="chart-bar-predicted legend-dot" />
              <span>{{ t('AI 预测 (Predicted)') }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- 2. AI 智能补货建议 (span 4) -->
      <div
        class="card-clean"
        style="
          grid-column: span 4;
          padding: 24px;
          border-top: 4px solid var(--tertiary);
          position: relative;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        "
      >
        <div style="position: absolute; top: 0; right: 0; padding: 16px; opacity: 0.1">
          <span
            class="material-symbols-outlined"
            style="font-size: 60px; color: var(--tertiary); font-variation-settings: 'FILL' 1"
            >auto_awesome</span
          >
        </div>
        <h3
          style="
            font-size: 18px;
            font-weight: 600;
            color: var(--on-surface);
            margin: 0 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
            z-index: 1;
          "
        >
          <span class="material-symbols-outlined" style="color: var(--tertiary)">inventory_2</span>
          {{ t('AI 智能补货建议') }}
        </h3>
        <p
          style="
            font-size: 13px;
            color: var(--on-surface-variant);
            margin: 0 0 20px;
            position: relative;
            z-index: 1;
          "
        >
          {{ t('基于布草周转与低库存物资，以下项目面临断货/短缺风险。') }}
        </p>
        <p v-if="!suggestions.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div
          v-else
          style="
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            position: relative;
            z-index: 1;
          "
        >
          <div
            v-for="(s, i) in suggestions"
            :key="i"
            style="
              background: var(--surface);
              border: 1px solid var(--outline-variant);
              border-radius: 8px;
              padding: 16px;
            "
          >
            <div
              style="
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 8px;
              "
            >
              <div style="font-size: 15px; font-weight: 600; color: var(--on-surface)">
                {{ s.name }}
              </div>
              <span
                v-if="s.riskColor === 'error'"
                style="
                  background: var(--error-container);
                  color: var(--on-error-container);
                  font-size: 12px;
                  padding: 2px 8px;
                  border-radius: 999px;
                "
                >{{ s.risk }}</span
              >
              <span
                v-else
                style="
                  background: var(--surface-variant);
                  color: var(--on-surface-variant);
                  font-size: 12px;
                  padding: 2px 8px;
                  border-radius: 999px;
                  border: 1px solid var(--outline-variant);
                "
                >{{ s.risk }}</span
              >
            </div>
            <div
              style="
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                color: var(--on-surface-variant);
                margin-bottom: 12px;
              "
            >
              <span>当前库存: {{ s.stock }}</span>
              <span
                >{{ t('预测缺口:')
                }}<strong
                  :style="{
                    color: s.riskColor === 'error' ? 'var(--error)' : 'var(--on-surface)',
                    fontWeight: 700,
                  }"
                  >{{ s.gap }}</strong
                ></span
              >
            </div>
            <button
              v-if="s.riskColor === 'error'"
              class="btn btn-primary"
              style="width: 100%; justify-content: center"
            >
              {{ s.suggest }}
            </button>
            <button
              v-else
              class="btn btn-ghost"
              style="
                width: 100%;
                justify-content: center;
                border-color: var(--primary);
                color: var(--primary);
              "
            >
              {{ s.suggest }}
            </button>
          </div>
        </div>
      </div>

      <!-- 3. 异常消耗预警 (span 12) -->
      <div
        class="card-clean"
        style="grid-column: span 12; padding: 24px; border-left: 4px solid var(--error)"
      >
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px">
          <span class="material-symbols-outlined" style="color: var(--error); font-size: 28px"
            >warning</span
          >
          <h3 style="font-size: 18px; font-weight: 600; color: var(--on-surface); margin: 0">
            {{ t('异常消耗预警') }}
          </h3>
          <span style="font-size: 13px; color: var(--on-surface-variant); margin-left: 12px">{{
            t('AI 检测到近期布草周转异常，请注意核查。')
          }}</span>
        </div>
        <p v-if="!anomalies.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div v-else style="overflow-x: auto">
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('房间/区域') }}</th>
                <th>{{ t('异常品类') }}</th>
                <th>{{ t('严重度基准') }}</th>
                <th>{{ t('当前级别') }}</th>
                <th>{{ t('AI 诊断原因') }}</th>
                <th>{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(a, i) in anomalies" :key="i">
                <td class="num" style="font-weight: 700; color: var(--primary)">{{ a.room }}</td>
                <td style="color: var(--on-surface)">{{ a.item }}</td>
                <td style="color: var(--on-surface-variant)">{{ a.std }}</td>
                <td style="color: var(--error); font-weight: 700">
                  {{ a.act }}
                  <span
                    class="material-symbols-outlined"
                    style="font-size: 14px; vertical-align: middle"
                    >trending_up</span
                  >
                </td>
                <td style="color: var(--on-surface-variant)">{{ a.reason }}</td>
                <td>
                  <button class="link">{{ a.action }}</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-frame {
  position: relative;
  height: 256px;
  margin-top: 8px;
  margin-left: 8px;
  border-bottom: 1px solid var(--outline-variant);
  padding-bottom: 28px;
  box-sizing: border-box;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 28px;
  width: 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  padding-right: 8px;
  font-size: 11px;
  color: var(--outline);
  font-family: 'Roboto Mono', monospace;
  pointer-events: none;
}
.bars-area {
  position: absolute;
  left: 40px;
  right: 0;
  top: 0;
  bottom: 28px;
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  gap: 4px;
}
.bar-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  position: relative;
}
.bar-track {
  flex: 1;
  width: 100%;
  min-height: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  position: relative;
}
.bar {
  width: 32px;
  max-width: 70%;
  min-height: 4px;
  border-radius: 3px 3px 0 0;
  transition: height 0.2s ease;
}
.peak-tag {
  position: absolute;
  top: -4px;
  left: 50%;
  transform: translate(-50%, -100%);
  background: var(--error-container);
  color: var(--on-error-container);
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  z-index: 2;
}
.day-label {
  position: absolute;
  bottom: -24px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.day-label.predicted {
  color: var(--tertiary);
}
.chart-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 20px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--on-surface);
}
.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.chart-bar-primary {
  background: var(--primary);
}
.chart-bar-predicted {
  background-color: transparent;
  border: 1px solid var(--primary-fixed-dim, #adc7ff);
  background-image: repeating-linear-gradient(
    45deg,
    var(--primary-fixed-dim, #adc7ff) 0,
    var(--primary-fixed-dim, #adc7ff) 2px,
    transparent 2px,
    transparent 6px
  );
  opacity: 0.9;
  box-sizing: border-box;
}
.empty-hint {
  margin: 0;
  padding: 24px 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
</style>
