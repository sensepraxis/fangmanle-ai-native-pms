<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// AI 绿色酒店能耗监测 —— 移植自 D5 eco-intelligence.html
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const metrics = ref<any[]>([])
const anomaly = ref<any>({})
const carbon = ref<any>({})
const bill = ref<any>({})
const hvac = ref<any[]>([])

const seedMetrics = [
  { label: '总用水量', value: '1,240', unit: '吨', delta: '较上周 -4.2%', green: true },
  { label: '总用电量', value: '8,450', unit: 'kWh', delta: '较上周 -8.1%', green: true },
  { label: '总燃气量', value: '320', unit: 'm³', delta: '较上周 -2.1%', green: true },
]

const seedAnomaly = {
  title: 'AI 异常检测：疑似漏水',
  body: '302 房间在过去 4 小时内持续有微量水流通过，且当前房间状态为“空净”。预计可能是马桶漏水或水龙头未关严。',
  time: '刚刚',
}

const seedCarbon = {
  value: '14.2',
  unit: 'tCO₂e',
  trees: '种植 120 棵树',
  desc: '超过区域 85% 的同类酒店',
}

const seedBill = {
  total: '¥ 42,500',
  items: [
    { label: '电费 (约 ¥28,000)', pct: 65, barCls: '#f59e0b' },
    { label: '水费 (约 ¥9,500)', pct: 22, barCls: 'var(--primary)' },
    { label: '燃气 (约 ¥5,000)', pct: 13, barCls: '#f57c00' },
  ],
}

const seedHvac = [
  {
    time: '14:30',
    area: '3层 东侧走廊',
    action: '调高 2℃ (22℃ → 24℃)',
    reason: '传感器检测过去45分钟无人员流动，且室外温度适宜。',
    save: '~¥ 2.5 / 小时',
    saveGreen: true,
  },
  {
    time: '13:15',
    area: '大堂 休息区',
    action: '调低风速 (高 → 中)',
    reason: '午间人流低谷，体感温度达标，降低风机功耗。',
    save: '~¥ 1.8 / 小时',
    saveGreen: true,
  },
  {
    time: '11:40',
    area: '5层 布草间',
    action: '关闭机组',
    reason: '区域无人且非作业时段，AI 判定可完全停机。',
    save: '~¥ 3.2 / 小时',
    saveGreen: true,
  },
  {
    time: '09:20',
    area: '2层 会议室 A',
    action: '预热至 26℃',
    reason: '距预订开始 30 分钟，预调节以平摊峰值负荷。',
    save: '~¥ 1.1 / 小时',
    saveGreen: true,
  },
]

async function load() {
  metrics.value = seedMetrics
  anomaly.value = seedAnomaly
  carbon.value = seedCarbon
  bill.value = seedBill
  hvac.value = seedHvac
  const d = await api.demo('compliance')
  if (d && d.length) {
    const m = d.filter((x: any) => x.label).slice(0, 3)
    if (m.length)
      metrics.value = m.map((x: any) => ({
        label: x.label,
        value: x.value,
        unit: x.unit || '',
        delta: x.delta || '',
        green: x.green !== false,
      }))
    const h = d.filter((x: any) => x.time).slice(0, 6)
    if (h.length)
      hvac.value = h.map((x: any) => ({
        time: x.time,
        area: x.area,
        action: x.action,
        reason: x.reason,
        save: x.save,
        saveGreen: true,
      }))
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <!-- 标题 -->
    <div
      class="page-head"
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 12px;
      "
    >
      <div>
        <h1>{{ t('AI 绿色酒店能耗监测') }}</h1>
        <p>{{ t('实时监测与智能成本控制') }}</p>
      </div>
      <div style="display: flex; gap: 12px">
        <button class="btn btn-ghost">{{ t('导出ESG报告') }}</button>
        <button class="btn btn-primary">
          <span class="material-symbols-outlined" style="font-size: 18px">eco</span>
          {{ t('AI 节能策略配置') }}
        </button>
      </div>
    </div>

    <div class="grid" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 24px">
      <!-- 1. 实时能耗总览（占 8 列） -->
      <div
        class="card-clean"
        style="grid-column: span 8; padding: 24px; display: flex; flex-direction: column"
      >
        <div
          style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
          "
        >
          <h2
            style="
              font-size: 16px;
              font-weight: 700;
              color: var(--on-surface);
              margin: 0;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="font-size: 20px; color: var(--primary)"
              >monitoring</span
            >
            {{ t('实时能耗总览') }}
          </h2>
          <div style="display: flex; gap: 8px">
            <span
              style="
                padding: 4px 12px;
                background: var(--surface-low);
                border-radius: 999px;
                font-size: 12px;
                color: var(--on-surface-variant);
                border: 1px solid var(--outline-variant);
                cursor: pointer;
              "
              >{{ t('今天') }}</span
            >
            <span
              style="
                padding: 4px 12px;
                background: var(--primary-container);
                color: var(--on-primary-container);
                border-radius: 999px;
                font-size: 12px;
                cursor: pointer;
              "
              >{{ t('本周') }}</span
            >
            <span
              style="
                padding: 4px 12px;
                background: var(--surface-low);
                border-radius: 999px;
                font-size: 12px;
                color: var(--on-surface-variant);
                border: 1px solid var(--outline-variant);
                cursor: pointer;
              "
              >{{ t('本月') }}</span
            >
          </div>
        </div>
        <!-- 3 指标卡 -->
        <div
          class="grid"
          style="
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
          "
        >
          <div
            v-for="m in metrics"
            :key="m.label"
            style="
              padding: 16px;
              border-radius: 10px;
              background: var(--surface);
              display: flex;
              flex-direction: column;
              gap: 4px;
            "
          >
            <span style="color: var(--on-surface-variant); font-size: 14px">{{ m.label }}</span>
            <div style="display: flex; align-items: flex-end; gap: 8px">
              <span class="num" style="font-size: 28px; color: var(--on-surface)">{{
                m.value
              }}</span>
              <span style="font-size: 13px; color: var(--on-surface-variant); margin-bottom: 4px">{{
                m.unit
              }}</span>
            </div>
            <span
              style="font-size: 13px; color: #16a34a; display: flex; align-items: center; gap: 4px"
            >
              <span class="material-symbols-outlined" style="font-size: 16px">trending_down</span
              >{{ m.delta }}</span
            >
          </div>
        </div>
        <!-- AI 异常检测 -->
        <div
          style="
            padding: 16px;
            border-radius: 10px;
            background: #fff8e6;
            border: 1px solid #fcd34d;
            display: flex;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 24px;
          "
        >
          <span class="material-symbols-outlined" style="font-size: 24px; color: #b45309"
            >warning</span
          >
          <div style="flex: 1">
            <h4 style="margin: 0 0 4px; font-size: 14px; font-weight: 700; color: #92400e">
              {{ anomaly.title }}
            </h4>
            <p style="margin: 0 0 12px; font-size: 13px; color: #b45309">{{ anomaly.body }}</p>
            <div style="display: flex; gap: 12px">
              <button class="btn" style="background: #ea580c; color: #fff; font-size: 13px">
                {{ t('派发工单给维修部') }}
              </button>
              <button
                class="btn btn-ghost"
                style="font-size: 13px; border-color: #fbbf24; color: #b45309"
              >
                {{ t('忽略此提醒') }}
              </button>
            </div>
          </div>
          <span class="num" style="font-size: 12px; color: #f59e0b">{{ anomaly.time }}</span>
        </div>
        <!-- 能耗趋势图表占位 -->
        <div
          style="
            flex: 1;
            min-height: 200px;
            width: 100%;
            background: var(--surface);
            border: 1px dashed var(--outline-variant);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
          "
        >
          <p
            style="
              color: var(--on-surface-variant);
              display: flex;
              flex-direction: column;
              align-items: center;
              gap: 8px;
              z-index: 10;
            "
          >
            <span class="material-symbols-outlined" style="font-size: 32px">insights</span>
            {{ t('[能耗趋势图表占位]') }}
          </p>
        </div>
      </div>

      <!-- 2. 碳足迹 + 账单预测（占 4 列） -->
      <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 24px">
        <!-- ESG 碳足迹 -->
        <div class="card-clean ai-card" style="padding: 24px; flex: 1">
          <h2
            style="
              font-size: 16px;
              font-weight: 700;
              color: var(--on-surface);
              margin: 0 0 16px;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="font-size: 20px; color: var(--tertiary)"
              >leaf</span
            >
            {{ t('ESG 碳足迹追踪') }}
          </h2>
          <div style="display: flex; align-items: center; justify-content: center; padding: 16px 0">
            <div
              style="
                position: relative;
                width: 128px;
                height: 128px;
                display: flex;
                align-items: center;
                justify-content: center;
              "
            >
              <svg viewBox="0 0 36 36" style="width: 100%; height: 100%; transform: rotate(-90deg)">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--surface-highest)"
                  stroke-width="3"
                ></path>
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--tertiary)"
                  stroke-dasharray="75, 100"
                  stroke-linecap="round"
                  stroke-width="3"
                ></path>
              </svg>
              <div
                style="
                  position: absolute;
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                "
              >
                <span class="num" style="font-size: 24px; color: var(--on-surface)">{{
                  carbon.value
                }}</span>
                <span style="font-size: 12px; color: var(--on-surface-variant)">{{
                  carbon.unit
                }}</span>
              </div>
            </div>
          </div>
          <div
            style="
              padding: 12px;
              background: var(--surface);
              border-radius: 10px;
              border: 1px solid var(--outline-variant);
              margin-top: 16px;
            "
          >
            <p style="margin: 0 0 8px; font-size: 13px; color: var(--on-surface-variant)">
              {{ t('本月减排成果等效于：') }}
            </p>
            <div style="display: flex; align-items: center; gap: 12px">
              <div
                style="
                  width: 40px;
                  height: 40px;
                  border-radius: 999px;
                  background: var(--tertiary-fixed);
                  display: flex;
                  align-items: center;
                  justify-content: center;
                "
              >
                <span class="material-symbols-outlined" style="font-size: 20px; color: #16a34a"
                  >park</span
                >
              </div>
              <div>
                <div class="num" style="color: var(--on-surface)">{{ carbon.trees }}</div>
                <div style="font-size: 12px; color: var(--on-surface-variant)">
                  {{ carbon.desc }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 下期账单预测 -->
        <div class="card-clean" style="padding: 24px; flex: 1">
          <h2
            style="
              font-size: 16px;
              font-weight: 700;
              color: var(--on-surface);
              margin: 0 0 16px;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="font-size: 20px; color: var(--primary)"
              >receipt_long</span
            >
            {{ t('下期账单预测') }}
          </h2>
          <div style="display: flex; align-items: flex-end; gap: 8px; margin-bottom: 24px">
            <span class="num" style="font-size: 28px; font-weight: 700; color: var(--on-surface)">{{
              bill.total
            }}</span>
            <span style="font-size: 13px; color: var(--on-surface-variant); margin-bottom: 4px">{{
              t('预计总额')
            }}</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 16px">
            <div v-for="b in bill.items" :key="b.label">
              <div
                style="
                  display: flex;
                  justify-content: space-between;
                  font-size: 13px;
                  margin-bottom: 4px;
                "
              >
                <span style="color: var(--on-surface-variant)">{{ b.label }}</span>
                <span class="num" style="color: var(--on-surface)">{{ b.pct }}%</span>
              </div>
              <div
                style="
                  width: 100%;
                  height: 8px;
                  background: var(--surface-highest);
                  border-radius: 999px;
                  overflow: hidden;
                "
              >
                <div
                  :style="{
                    width: b.pct + '%',
                    height: '100%',
                    background: b.barCls,
                    borderRadius: '999px',
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. 智能 HVAC 控制记录（占 12 列） -->
      <div class="card-clean" style="grid-column: span 12; overflow: hidden; margin-bottom: 32px">
        <div
          style="
            padding: 24px;
            border-bottom: 1px solid var(--outline-variant);
            background: var(--surface-low);
          "
        >
          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              flex-wrap: wrap;
              gap: 8px;
            "
          >
            <div>
              <h2
                style="
                  font-size: 16px;
                  font-weight: 700;
                  color: var(--on-surface);
                  margin: 0;
                  display: flex;
                  align-items: center;
                  gap: 8px;
                "
              >
                <span
                  class="material-symbols-outlined"
                  style="font-size: 20px; color: var(--tertiary)"
                  >smart_thermostat</span
                >
                {{ t('智能 HVAC 控制记录') }}
              </h2>
              <p style="margin: 4px 0 0; font-size: 13px; color: var(--on-surface-variant)">
                {{ t('AI 在无人区域自动调节温度以节约成本的动作日志') }}
              </p>
            </div>
            <div
              style="display: flex; gap: 16px; font-size: 13px; color: var(--on-surface-variant)"
            >
              <span style="display: flex; align-items: center; gap: 4px"
                ><span
                  style="width: 8px; height: 8px; border-radius: 999px; background: var(--tertiary)"
                ></span
                >{{ t('AI 自动干预') }}</span
              >
              <span style="display: flex; align-items: center; gap: 4px"
                ><span
                  style="width: 8px; height: 8px; border-radius: 999px; background: #16a34a"
                ></span
                >{{ t('节能达成') }}</span
              >
            </div>
          </div>
        </div>
        <table class="data" style="width: 100%; border-collapse: collapse">
          <thead>
            <tr style="background: var(--surface); border-bottom: 1px solid var(--outline-variant)">
              <th
                style="
                  padding: 16px;
                  text-align: left;
                  color: var(--on-surface-variant);
                  font-weight: 600;
                "
              >
                {{ t('时间') }}
              </th>
              <th
                style="
                  padding: 16px;
                  text-align: left;
                  color: var(--on-surface-variant);
                  font-weight: 600;
                "
              >
                {{ t('区域 / 房间') }}
              </th>
              <th
                style="
                  padding: 16px;
                  text-align: left;
                  color: var(--on-surface-variant);
                  font-weight: 600;
                "
              >
                {{ t('AI 动作') }}
              </th>
              <th
                style="
                  padding: 16px;
                  text-align: left;
                  color: var(--on-surface-variant);
                  font-weight: 600;
                "
              >
                {{ t('触发原因') }}
              </th>
              <th
                style="
                  padding: 16px;
                  text-align: right;
                  color: var(--on-surface-variant);
                  font-weight: 600;
                "
              >
                {{ t('预估节省') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(h, i) in hvac" :key="i" style="border-bottom: 1px solid var(--surface)">
              <td class="num" style="padding: 16px; color: var(--on-surface)">{{ h.time }}</td>
              <td style="padding: 16px; color: var(--on-surface); font-weight: 600">
                {{ h.area }}
              </td>
              <td style="padding: 16px; color: var(--on-surface)">{{ h.action }}</td>
              <td style="padding: 16px; font-size: 13px; color: var(--on-surface-variant)">
                {{ h.reason }}
              </td>
              <td
                class="num"
                style="padding: 16px; text-align: right; font-weight: 600; color: #16a34a"
              >
                {{ h.save }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
