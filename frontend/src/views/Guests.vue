<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { fmt, VIP_CN, VIP_PILL } from '../lib/ui'

const q = ref('')
const guests = ref<any[]>([])
const detail = ref<any>(null)

async function load() {
  let gs = await api.listGuests(hotelStore.hotelId)
  if (q.value)
    gs = gs.filter(
      (g: any) => (g.name || '').includes(q.value) || (g.phone || '').includes(q.value),
    )
  guests.value = gs
}
async function show(id: number) {
  detail.value = await api.guest360(id)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('客户列表') }}</h1>
      <p>
        <RouterLink to="/b-data/global-guest-directory">{{ t('← 客户资源全景列表') }}</RouterLink>
        {{ t('· OneID 统一身份视图：跨平台身份、标签、订单历史、消费 LTV。') }}
      </p>
    </div>

    <div style="display: grid; grid-template-columns: 320px 1fr; gap: 16px">
      <!-- 左：客户列表 -->
      <div class="card-clean">
        <div style="padding: 12px 14px; border-bottom: 1px solid #eef0f4">
          <input
            v-model="q"
            @input="load"
            :placeholder="t('搜索姓名/手机号')"
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
        <div style="max-height: 70vh; overflow-y: auto">
          <div
            v-for="g in guests"
            :key="g.id"
            style="
              padding: 10px 14px;
              cursor: pointer;
              border-bottom: 1px solid #eef0f4;
              transition: background-color 0.1s;
            "
            @click="show(g.id)"
            @mouseover="(e: any) => (e.currentTarget.style.background = '#fafbfc')"
            @mouseleave="(e: any) => (e.currentTarget.style.background = '')"
          >
            <div style="font-weight: 500; font-size: 13px; color: #1f2329">
              {{ g.name }}
              <span style="color: #9aa1ad; font-weight: 400; font-size: 12px; margin-left: 6px">{{
                g.phone
              }}</span>
            </div>
            <div style="font-size: 11px; color: #5b616e; margin-top: 4px">
              LTV {{ fmt(g.ltv) }} ·
              <span
                class="pill"
                :class="VIP_PILL[g.vip_level] || 'pill-slate'"
                style="margin: 0 4px; font-size: 10px"
              >
                {{ VIP_CN[g.vip_level] || g.vip_level }}</span
              >
              · {{ t('流失风险') }} {{ (g.churn_risk * 100).toFixed(0) }}%
            </div>
          </div>
          <div
            v-if="!guests.length"
            style="padding: 30px; text-align: center; color: #9aa1ad; font-size: 13px"
          >
            {{ t('无客户') }}
          </div>
        </div>
      </div>

      <!-- 右：客户 360 详情 -->
      <div class="card-clean">
        <div
          v-if="!detail"
          style="padding: 60px; text-align: center; color: #9aa1ad; font-size: 13px"
        >
          {{ t('选择左侧客户查看 OneID 360 画像') }}
        </div>
        <div v-else style="padding: 22px">
          <!-- 抬头 -->
          <div style="display: flex; gap: 14px; align-items: center; margin-bottom: 20px">
            <div
              style="
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: linear-gradient(135deg, #2563eb, #7c3aed);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                font-weight: 600;
              "
            >
              {{ detail.guest.name?.slice(0, 1) || t('客') }}
            </div>
            <div>
              <div style="font-size: 18px; font-weight: 600; color: #1f2329">
                {{ detail.guest.name }}
              </div>
              <div style="font-size: 12px; color: #5b616e; margin-top: 4px">
                OneID <b>{{ detail.guest.one_id }}</b> · {{ detail.guest.phone }} ·
                {{ detail.guest.city }}
              </div>
            </div>
          </div>

          <!-- KPI -->
          <div class="kpi-grid" style="margin-bottom: 18px">
            <div class="kpi">
              <div class="k">{{ t('终身价值 LTV') }}</div>
              <div class="v">{{ fmt(detail.guest.ltv) }}</div>
              <div class="d up">{{ t('持续上升') }}</div>
            </div>
            <div class="kpi">
              <div class="k">{{ t('会员等级') }}</div>
              <div class="v" style="font-size: 18px">
                <span class="pill" :class="VIP_PILL[detail.guest.vip_level] || 'pill-slate'">
                  {{ VIP_CN[detail.guest.vip_level] || detail.guest.vip_level }}</span
                >
              </div>
              <div class="d flat">{{ t('稳定') }}</div>
            </div>
            <div class="kpi">
              <div class="k">{{ t('流失风险') }}</div>
              <div class="v" style="color: #be123c">
                {{ (detail.guest.churn_risk * 100).toFixed(0) }}%
              </div>
              <div class="d down">
                {{ detail.guest.churn_risk > 0.5 ? t('需干预') : t('健康') }}
              </div>
            </div>
            <div class="kpi">
              <div class="k">{{ t('历史订单数') }}</div>
              <div class="v">{{ detail.orders.length }}</div>
              <div class="d up">{{ t('复购率高') }}</div>
            </div>
          </div>

          <!-- 跨平台身份 -->
          <div style="margin-bottom: 16px">
            <h3 style="font-size: 13px; font-weight: 600; color: #1f2329; margin: 0 0 8px">
              {{ t('跨平台身份 (OneID)') }}
            </h3>
            <div style="display: flex; flex-wrap: wrap; gap: 6px">
              <span
                v-for="i in detail.identities"
                :key="i.id"
                class="pill pill-blue"
                style="font-size: 11px"
              >
                {{ i.source }}: {{ i.external_id }}</span
              >
              <span v-if="!detail.identities.length" style="color: #9aa1ad; font-size: 12px">{{
                t('无')
              }}</span>
            </div>
          </div>

          <!-- 标签 -->
          <div style="margin-bottom: 16px">
            <h3 style="font-size: 13px; font-weight: 600; color: #1f2329; margin: 0 0 8px">
              {{ t('客户标签') }}
            </h3>
            <div style="display: flex; flex-wrap: wrap; gap: 6px">
              <span
                v-for="tag in detail.tags"
                :key="tag.name"
                class="pill pill-amber"
                style="font-size: 11px"
              >
                {{ tag.name }}</span
              >
              <span v-if="!detail.tags.length" style="color: #9aa1ad; font-size: 12px">{{
                t('无')
              }}</span>
            </div>
          </div>

          <!-- 历史订单 -->
          <div style="margin-bottom: 16px">
            <h3 style="font-size: 13px; font-weight: 600; color: #1f2329; margin: 0 0 8px">
              {{ t('历史订单 (') }}{{ detail.orders.length }})
            </h3>
            <div class="card-clean" style="overflow: hidden">
              <table class="data">
                <thead>
                  <tr>
                    <th>{{ t('订单号') }}</th>
                    <th>{{ t('入住区间') }}</th>
                    <th class="num">{{ t('金额') }}</th>
                    <th>{{ t('状态') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="o in detail.orders.slice(0, 8)" :key="o.id">
                    <td style="font-variant-numeric: tabular-nums; font-size: 12px">
                      {{ o.order_no }}
                    </td>
                    <td style="color: #5b616e; font-size: 12px; font-variant-numeric: tabular-nums">
                      {{ o.check_in }} ~ {{ o.check_out }}
                    </td>
                    <td class="num">{{ fmt(o.total_amount) }}</td>
                    <td>
                      <span class="pill pill-slate">{{ o.status }}</span>
                    </td>
                  </tr>
                  <tr v-if="!detail.orders.length">
                    <td colspan="4" style="text-align: center; color: #9aa1ad; padding: 18px">
                      {{ t('无') }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
