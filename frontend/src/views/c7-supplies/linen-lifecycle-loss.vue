<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 布草寿命与报损根因 —— 布草线第 3 步
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
const router = useRouter()
const kpis = ref<any[]>([])
const batches = ref<any[]>([])
const causes = ref<any[]>([])
const tip = ref('')

const LIFE_MAX = 150

function goDamage() {
  router.push('/c8-assets/damage-registration')
}

function goReplaceStrategy() {
  router.push('/c7-supplies/smart-restocking')
}

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'linen')
    const stages = board?.linen_stages || []
    const high = board?.linen_high_wash || []
    const lossInsights = (board?.insights || []).filter((x: any) =>
      ['replace', 'loss'].includes(x.category),
    )
    const fee = board?.damage_cost || {}

    const totalItems = stages.reduce((s: number, x: any) => s + Number(x.count || 0), 0) || 1
    const pending = stages.find((x: any) => x.stage === t('待换'))?.count || 0
    const worn = stages.find((x: any) => x.stage === t('磨损'))?.count || 0
    const avgWash = Number(board?.linen_avg_wash || 0)
    const health = Math.max(
      40,
      Math.min(
        100,
        Math.round(100 - (Number(pending) / totalItems) * 120 - (Number(worn) / totalItems) * 40),
      ),
    )

    kpis.value = [
      {
        label: t('布草报损待处理费用'),
        value: `¥${Number(fee.pending || fee.total || 0).toLocaleString('zh-CN')}`,
        delta: pending ? `${pending} 件待换` : undefined,
        deltaCls: 'error',
        sub: `累计报损 ¥${Number(fee.total || 0).toLocaleString('zh-CN')}`,
      },
      {
        label: t('高洗次数样本均值'),
        value: String(avgWash),
        unit: t('次'),
        sub: `(行业参考: ${LIFE_MAX})`,
        pct: Math.min(100, Math.round((avgWash / LIFE_MAX) * 100)),
        barCls: 'var(--primary)',
      },
      {
        label: t('AI 质量健康度'),
        value: String(health),
        unit: '/100',
        badge: health < 75 ? t('需关注') : t('良好'),
        badgeCls: 'tertiary',
        sub: stages.map((s: any) => `${s.stage} ${s.count}`).join(' · ') || t('生命周期分布'),
      },
    ]

    if (high.length) {
      batches.value = high.map((x: any, i: number) => {
        const washes = Number(x.wash_count || 0)
        const remainLife = Math.max(0, LIFE_MAX - washes)
        const remainPct = Math.round((remainLife / LIFE_MAX) * 100)
        const stage =
          x.lifecycle_stage || (washes >= 100 ? t('待换') : washes >= 60 ? t('磨损') : t('良好'))
        const statusCls = stage === t('待换') ? 'error' : stage === t('磨损') ? 'amber' : 'green'
        return {
          name: `${x.item_type || t('布草')} #${x.id || i + 1}`,
          cat: x.item_type || t('布草'),
          inTime: stage,
          washes,
          remain: remainPct,
          remainCls:
            statusCls === 'error'
              ? 'var(--error)'
              : statusCls === 'amber'
                ? '#f57f17'
                : 'var(--tertiary)t(',
          remainTxt: `~${remainLife}次`,
          status: stage === '待换' ? t('高危临界') : stage === t('磨损') ? t('关注') : t('正常'),
          statusCls,
        }
      })
    } else {
      batches.value = []
    }

    if (lossInsights.length) {
      causes.value = lossInsights.map((x: any) => ({
        title: x.title,
        pct: x.category === 'replace' ? t('置换建议') : t('损耗洞察'),
        pctCls: x.category === 'replace' ? 'var(--tertiary)' : 'var(--error)',
        desc: x.recommendation || '',
        action: x.impact_amount
          ? `影响约 ¥${Number(x.impact_amount).toLocaleString(')zh-CN')}`
          : t('查看详情'),
      }))
      tip.value = lossInsights[0]?.recommendation || ''
    } else {
      causes.value = []
      tip.value = ''
    }
  } catch {
    kpis.value = []
    batches.value = []
    causes.value = []
    tip.value = ''
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 20px;
      "
    >
      <div>
        <h1 style="font-size: 24px; font-weight: 700; color: var(--on-surface); margin: 0 0 4px">
          {{ t('布草寿命与待换') }}
        </h1>
        <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
          {{ t('布草生命周期与损耗分析仪表盘') }}
        </p>
      </div>
      <div style="display: flex; gap: 12px">
        <button class="btn btn-ghost" type="button">{{ t('导出报告') }}</button>
        <button class="btn btn-ghost" type="button" @click="goReplaceStrategy">
          {{ t('损耗置换策略') }}
        </button>
        <button class="btn btn-primary" type="button" @click="goDamage">{{ t('登记报损') }}</button>
      </div>
    </div>

    <!-- KPI 行 -->
    <div
      style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px"
    >
      <div
        v-for="(k, i) in kpis"
        :key="i"
        class="card-clean"
        style="padding: 24px; position: relative; overflow: hidden"
        :style="k.badgeCls === 'tertiary' ? { borderLeft: '4px solid var(--tertiary)' } : {}"
      >
        <p style="font-size: 12px; font-weight: 700; color: var(--on-surface); margin: 0 0 8px">
          {{ k.label }}
        </p>
        <div style="display: flex; align-items: baseline; gap: 8px">
          <span
            style="
              font-size: 32px;
              font-weight: 700;
              color: var(--on-surface);
              font-family: 'Roboto Mono, monospace';
            "
            >{{ k.value }}</span
          >
          <span v-if="k.unit" style="font-size: 12px; color: var(--secondary)">{{ k.unit }}</span>
          <span
            v-if="k.delta"
            :style="{
              fontSize: '12px',
              color: 'var(--error)',
              background: 'rgba(186,26,26,0.1)',
              padding: '2px 8px',
              borderRadius: '6px',
            }"
            >{{ k.delta }}</span
          >
          <span
            v-if="k.badge"
            style="
              background: rgba(140, 51, 179, 0.1);
              color: var(--on-tertiary-container);
              font-size: 11px;
              padding: 2px 8px;
              border-radius: 6px;
              font-weight: 700;
            "
            >{{ k.badge }}</span
          >
        </div>
        <p v-if="k.sub" style="font-size: 12px; color: var(--on-surface-variant); margin: 8px 0 0">
          {{ k.sub }}
        </p>
        <div
          v-if="k.pct !== undefined"
          style="
            width: 100%;
            background: var(--surface-container);
            border-radius: 999px;
            height: 6px;
            margin-top: 16px;
          "
        >
          <div
            :style="{
              width: k.pct + '%',
              background: k.barCls,
              height: '6px',
              borderRadius: '999px',
            }"
          ></div>
        </div>
      </div>
    </div>

    <div
      style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; align-items: start"
    >
      <!-- 批次监控 (span 8) -->
      <div class="card-clean" style="grid-column: span 8; overflow: hidden">
        <div
          style="
            padding: 20px;
            border-bottom: 1px solid rgba(193, 198, 214, 0.5);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--surface-low);
          "
        >
          <h2 style="font-size: 16px; font-weight: 700; color: var(--on-surface); margin: 0">
            {{ t('高洗涤次数布草监控') }}
          </h2>
        </div>
        <div style="overflow-x: auto">
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('批次名称') }}</th>
                <th>{{ t('品类') }}</th>
                <th>{{ t('生命周期') }}</th>
                <th class="num">{{ t('已洗涤次数') }}</th>
                <th>{{ t('剩余寿命预估') }}</th>
                <th>{{ t('状态') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!batches.length">
                <td colspan="6" class="empty-hint">{{ SUPPLIES_EMPTY }}</td>
              </tr>
              <tr v-for="(b, i) in batches" :key="i">
                <td style="font-weight: 500">{{ b.name }}</td>
                <td style="color: var(--on-surface-variant)">{{ b.cat }}</td>
                <td style="color: var(--on-surface-variant)">{{ b.inTime }}</td>
                <td class="num">{{ b.washes }}</td>
                <td>
                  <div style="display: flex; align-items: center; gap: 8px">
                    <div
                      style="
                        width: 64px;
                        background: var(--surface-container);
                        height: 6px;
                        border-radius: 999px;
                        overflow: hidden;
                      "
                    >
                      <div
                        :style="{ width: b.remain + '%', background: b.remainCls, height: '6px' }"
                      ></div>
                    </div>
                    <span
                      :style="{
                        fontFamily: 'Roboto Mono, monospace',
                        fontSize: '11px',
                        color: b.remainCls,
                      }"
                      >{{ b.remainTxt }}</span
                    >
                  </div>
                </td>
                <td>
                  <span
                    v-if="b.statusCls === 'error'"
                    style="
                      background: var(--error-container);
                      color: var(--on-error-container);
                      border: 1px solid rgba(186, 26, 26, 0.2);
                      font-size: 11px;
                      padding: 2px 8px;
                      border-radius: 6px;
                    "
                    >{{ b.status }}</span
                  >
                  <span
                    v-else-if="b.statusCls === 'amber'"
                    style="
                      background: #fff8e1;
                      color: #f57f17;
                      border: 1px solid #ffe082;
                      font-size: 11px;
                      padding: 2px 8px;
                      border-radius: 6px;
                    "
                    >{{ b.status }}</span
                  >
                  <span
                    v-else
                    style="
                      background: #e8f5e9;
                      color: #2e7d32;
                      border: 1px solid #a5d6a7;
                      font-size: 11px;
                      padding: 2px 8px;
                      border-radius: 6px;
                    "
                    >{{ b.status }}</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 右侧栏 (span 4) -->
      <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 16px">
        <div class="card-clean" style="padding: 20px; border: 1px solid rgba(140, 51, 179, 0.4)">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px">
            <div
              style="
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: rgba(140, 51, 179, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
              "
            ></div>
            <h3 style="font-size: 16px; font-weight: 700; color: var(--on-surface); margin: 0">
              {{ t('报损根因 AI 诊断') }}
            </h3>
          </div>
          <div style="display: flex; flex-direction: column; gap: 16px">
            <p v-if="!causes.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
            <div
              v-for="(c, i) in causes"
              :key="i"
              style="
                background: var(--background);
                border-radius: 8px;
                padding: 12px;
                border: 1px solid rgba(193, 198, 214, 0.3);
              "
            >
              <div
                style="
                  display: flex;
                  justify-content: space-between;
                  align-items: flex-start;
                  margin-bottom: 4px;
                "
              >
                <span style="font-weight: 700; color: var(--on-surface); font-size: 13px">{{
                  c.title
                }}</span>
                <span :style="{ color: c.pctCls, fontWeight: 700, fontSize: '13px' }">{{
                  c.pct
                }}</span>
              </div>
              <p style="font-size: 12px; color: var(--on-surface-variant); margin: 0">
                {{ c.desc }}
              </p>
              <button
                class="link"
                type="button"
                style="
                  font-size: 11px;
                  display: flex;
                  align-items: center;
                  gap: 4px;
                  margin-top: 8px;
                "
                @click="goReplaceStrategy"
              >
                {{ c.action }} →
              </button>
            </div>
          </div>
        </div>
        <div
          v-if="tip"
          style="
            background: #fffae6;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #ffd966;
            display: flex;
            align-items: flex-start;
            gap: 12px;
          "
        >
          <div>
            <h4 style="font-size: 13px; font-weight: 700; color: #805b00; margin: 0 0 4px">
              {{ t('建议审查报废标准') }}
            </h4>
            <p style="font-size: 12px; color: #997300; margin: 0">{{ tip }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-hint {
  margin: 0;
  padding: 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
</style>
