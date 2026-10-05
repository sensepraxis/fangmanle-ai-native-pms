<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { ref } from 'vue'
import { fmtInt } from './useAssetProfileDerived'

defineProps<{
  depChart: any
  metrics: { pv: number; rc: number; residual: number; years: number | null }
  failurePct: number
  failureLabel: { text: string; cls: string; tip: string; badge: string }
  needleDeg: number
  failureRiskBreakdown: any
}>()

const failureRiskDetailOpen = ref(false)
</script>

<template>
  <section id="section-value" class="sec-block ltv-block">
    <div class="ltv-grid">
      <div class="card ltv-chart-card">
        <div class="ltv-chart-h">
          <h3 class="card-h !mb-0 flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-[20px]">show_chart</span>
            {{ t('价值折旧曲线') }}
          </h3>
          <div class="text-right">
            <div class="text-xl font-bold text-primary font-mono">
              {{ fmtInt(depChart.estValue) }}
            </div>
            <div class="text-xs text-on-surface-variant">{{ t('当前净值') }}</div>
          </div>
        </div>
        <div class="chart-wrap">
          <div class="chart-ylab">
            <span v-for="lb in depChart.labels" :key="lb">{{ lb }}</span>
          </div>
          <div class="chart-grid">
            <svg
              class="absolute inset-0 w-full h-full overflow-visible"
              preserveAspectRatio="none"
              viewBox="0 0 100 100"
            >
              <path :d="depChart.areaPath" fill="rgba(0,91,191,0.08)" stroke="none" />
              <path
                :d="depChart.path"
                fill="none"
                stroke="#005bbf"
                stroke-width="3"
                vector-effect="non-scaling-stroke"
              />
              <path
                :d="depChart.repairPath"
                fill="none"
                stroke="#a84fce"
                stroke-dasharray="4 4"
                stroke-width="2"
                vector-effect="non-scaling-stroke"
              />
              <line
                x1="0"
                :y1="depChart.salvageLine"
                x2="70"
                :y2="depChart.salvageLine"
                stroke="#a84fce"
                stroke-dasharray="3 3"
                stroke-width="1"
                opacity="0.45"
                vector-effect="non-scaling-stroke"
              />
              <circle
                v-for="(p, i) in depChart.points"
                :key="i"
                :cx="p.x"
                :cy="p.y"
                :r="i === depChart.currentPointIndex ? 3.2 : 2"
                :fill="i === depChart.currentPointIndex ? '#ffffff' : '#005bbf'"
                :stroke="i === depChart.currentPointIndex ? '#005bbf' : 'none'"
                :stroke-width="i === depChart.currentPointIndex ? 2 : 0"
              />
            </svg>
            <div class="chart-tip" :style="{ left: depChart.tipX + '%', top: depChart.tipY + '%' }">
              <div class="text-xs text-on-surface-variant mb-0.5">{{ t('当前净值') }}</div>
              <div class="font-bold text-primary">{{ fmtInt(depChart.estValue) }}</div>
              <div class="text-[11px] text-tertiary mt-0.5">
                {{ t('残值率') }} {{ metrics.residual }}%
              </div>
            </div>
          </div>
          <div class="chart-xlab">
            <span
              v-for="(lb, i) in depChart.xLabels"
              :key="`${lb.year}-${lb.hint}-${i}`"
              class="chart-x-item"
              :style="{ left: `${(lb.x / 70) * 100}%` }"
            >
              <span class="chart-x-year">{{ lb.year }}</span>
              <span v-if="lb.hint" class="chart-x-hint">{{ lb.hint }}</span>
            </span>
          </div>
        </div>
        <div class="chart-guide">
          <div class="chart-guide-title">{{ t('图例说明') }}</div>
          <ul class="chart-guide-list">
            <li>
              <span class="guide-line guide-line-value" aria-hidden="true" />
              <strong>{{ t('净值曲线') }}</strong>
              <span class="guide-desc"
                >{{ t('资产账面价值随时间变化；采购点') }} {{ fmtInt(metrics.pv) }}，{{
                  t('当前高亮圆点为今日净值')
                }}</span
              >
            </li>
            <li>
              <span class="guide-line guide-line-repair" aria-hidden="true" />
              <strong>{{ t('累计维修成本') }}</strong>
              <span class="guide-desc"
                >{{ t('按维修/维保事件逐年累加，当前合计') }} {{ fmtInt(metrics.rc) }}</span
              >
            </li>
            <li>
              <span class="guide-line guide-line-salvage" aria-hidden="true" />
              <strong>{{ t('预估残值线') }}</strong>
              <span class="guide-desc">{{
                t('报废时预计可回收价值（约为原值 5%），供修换决策参考')
              }}</span>
            </li>
          </ul>
          <p class="chart-guide-note">
            <span class="material-symbols-outlined guide-ico">info</span>
            {{ t('纵轴为金额（元），横轴按采购日至预估报废日排列（自') }}
            {{ depChart.purchaseCalYear }} {{ t('年起算）。') }}
            <template v-if="depChart.daysSincePurchase < 45">
              {{ t('新购资产：采购后净值保持平稳，随后按') }} {{ depChart.lifeYears }}
              {{ t('年使用年限直线折旧至预估残值。') }}
            </template>
            <template v-else>
              {{
                t(
                  '已服役 {years} 年；采购至今日按账面净值插值，今日至报废按品类 {life} 年使用年限推算。',
                  { years: metrics.years ?? '—', life: depChart.lifeYears },
                )
              }}
            </template>
          </p>
        </div>
      </div>

      <div class="ltv-side">
        <div class="card churn-card">
          <h3 class="card-h flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary text-[20px]">data_usage</span>
            {{ t('故障风险预警') }}
          </h3>
          <div class="churn-gauge">
            <div class="gauge-arc">
              <div class="gauge-ring" />
              <div
                class="gauge-fill"
                :class="failurePct >= 70 ? 'is-high' : failurePct >= 45 ? 'is-mid' : 'is-low'"
              />
              <div
                class="gauge-needle"
                :style="{ transform: `translateX(-50%) rotate(${needleDeg}deg)` }"
              />
              <div class="gauge-hub" />
            </div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold" :class="failureLabel.cls">{{ failurePct }}%</div>
            <span
              class="inline-block mt-1 text-xs font-bold px-2.5 py-0.5 rounded-full border"
              :class="[failureLabel.cls, failureLabel.badge]"
            >
              {{ failureLabel.text }}</span
            >
            <p class="m-0 mt-2 text-xs text-on-surface-variant">{{ failureLabel.tip }}</p>
            <button
              type="button"
              class="risk-detail-btn"
              @click="failureRiskDetailOpen = !failureRiskDetailOpen"
            >
              {{ failureRiskDetailOpen ? t('收起详情') : t('查看详情') }}
            </button>
          </div>

          <Transition name="risk-expand">
            <div v-if="failureRiskDetailOpen" class="risk-inline-panel">
              <div class="risk-inline-head">
                <div>
                  <h4 class="risk-inline-title">{{ t('计算说明') }}</h4>
                  <p class="risk-inline-sub">{{ t('基于资产台账字段的规则推算') }}</p>
                </div>
                <button
                  type="button"
                  class="risk-inline-close"
                  :aria-label="t('关闭')"
                  @click="failureRiskDetailOpen = false"
                >
                  <span class="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>

              <div
                class="risk-result-banner"
                :class="failurePct >= 70 ? 'is-high' : failurePct >= 45 ? 'is-mid' : 'is-low'"
              >
                <div>
                  <span class="risk-result-label">{{ t('当前故障风险') }}</span>
                  <strong class="risk-result-val">{{ failurePct }}%</strong>
                  <span class="risk-result-badge">{{ failureLabel.text }}</span>
                </div>
                <div class="risk-result-side">
                  <span>{{ t('修换指数 {n}/99', { n: failureRiskBreakdown.replaceIndex }) }}</span>
                </div>
              </div>

              <section class="risk-section">
                <h4 class="risk-section-title">{{ t('输入数据') }}</h4>
                <div class="risk-input-grid">
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('采购原值') }}</span>
                    <span class="risk-input-v">{{
                      fmtInt(failureRiskBreakdown.inputs.purchaseValue)
                    }}</span>
                  </div>
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('累计维修') }}</span>
                    <span class="risk-input-v">{{
                      fmtInt(failureRiskBreakdown.inputs.repairCost)
                    }}</span>
                  </div>
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('维修占比') }}</span>
                    <span class="risk-input-v">{{ failureRiskBreakdown.inputs.repairRatio }}%</span>
                  </div>
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('健康分') }}</span>
                    <span class="risk-input-v">{{
                      failureRiskBreakdown.inputs.healthScore || '—'
                    }}</span>
                  </div>
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('服役年限') }}</span>
                    <span class="risk-input-v">{{
                      t('{n} 年', { n: failureRiskBreakdown.inputs.yearsServed ?? '—' })
                    }}</span>
                  </div>
                  <div class="risk-input-item">
                    <span class="risk-input-k">{{ t('净值残值率') }}</span>
                    <span class="risk-input-v">{{ failureRiskBreakdown.inputs.residualPct }}%</span>
                  </div>
                </div>
              </section>

              <section class="risk-section">
                <h4 class="risk-section-title">{{ t('计算步骤 → 修换指数') }}</h4>
                <div class="risk-steps">
                  <div
                    v-for="(step, i) in failureRiskBreakdown.steps"
                    :key="step.label"
                    class="risk-step"
                    :class="{ inactive: step.inactive }"
                  >
                    <div class="risk-step-no">{{ i + 1 }}</div>
                    <div class="risk-step-body">
                      <div class="risk-step-top">
                        <strong>{{ step.label }}</strong>
                        <span class="risk-step-pts" :class="{ zero: step.points === 0 }"
                          >+{{ step.points }}</span
                        >
                      </div>
                      <p class="risk-step-formula">{{ step.formula }}</p>
                      <p class="risk-step-calc">{{ step.calc }}</p>
                    </div>
                  </div>
                </div>
                <div class="risk-total-row">
                  <span>{{ t('修换指数（上限 99）') }}</span>
                  <strong>{{ failureRiskBreakdown.replaceIndex }}</strong>
                </div>
              </section>

              <section class="risk-section risk-section-last">
                <h4 class="risk-section-title">{{ t('映射为仪表盘') }}</h4>
                <p class="risk-map-line">
                  {{ t('clamp(修换指数,') }} <strong>5%</strong>, <strong>95%</strong>) →
                  <strong class="risk-map-result">{{ failurePct }}%</strong>
                </p>
                <p class="risk-map-note">{{ failureRiskBreakdown.clampNote }}</p>
                <ul class="risk-level-list">
                  <li :class="{ active: failurePct < 45 }">
                    <span>&lt; 45%</span>{{ t('低风险') }}
                  </li>
                  <li :class="{ active: failurePct >= 45 && failurePct < 70 }">
                    <span>45–69%</span>{{ t('中等') }}
                  </li>
                  <li :class="{ active: failurePct >= 70 }"><span>≥ 70%</span>{{ t('高风险') }}</li>
                </ul>
              </section>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </section>
</template>
