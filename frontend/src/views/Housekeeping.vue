<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { TASK_CN, TASK_ST_CN, TASK_ST_PILL, toast } from '../lib/ui'

const router = useRouter()

const tasks = ref<any[]>([])
const supplies = ref<any[]>([])

async function load() {
  const [t, s] = await Promise.all([
    api.listHousekeeping(hotelStore.hotelId),
    api.listSupplies(hotelStore.hotelId),
  ])
  tasks.value = t
  supplies.value = s.filter((x: any) => x.current_stock < x.safety_stock)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

async function finish(id: number) {
  await api.finishHousekeeping(id)
  toast(t('任务完成'))
  load()
}

// 分桶：待处理 / 已分派 / 进行中 / 已完成
const buckets = computed(() => {
  const b: Record<string, any[]> = {
    open: [],
    assigned: [],
    in_progress: [],
    done: [],
    verified: [],
  }
  for (const t of tasks.value) (b[t.status] || (b[t.status] = [])).push(t)
  return b
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('房务管理') }}</h1>
      <p>{{ t('清扫 / 查房工单与物资库存告警。') }}</p>
    </div>

    <div class="page-actions">
      <div></div>
      <button class="btn btn-primary" @click="router.push('/dispatch')">
        <span class="material-symbols-outlined" style="font-size: 16px; vertical-align: -3px"
          >bolt</span
        >
        {{ t('派工控制台') }}
      </button>
    </div>

    <!-- KPI -->
    <div class="kpi-grid">
      <div class="kpi">
        <div class="k">{{ t('待处理工单') }}</div>
        <div class="v">{{ (buckets.open || []).length + (buckets.assigned || []).length }}</div>
        <div class="d flat">{{ t('今日新增') }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('进行中') }}</div>
        <div class="v" style="color: #b45309">{{ (buckets.in_progress || []).length }}</div>
        <div class="d down">{{ t('需跟进') }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('已完成') }}</div>
        <div class="v" style="color: #047857">
          {{ (buckets.done || []).length + (buckets.verified || []).length }}
        </div>
        <div class="d up">{{ t('已核验') }}</div>
      </div>
      <div class="kpi">
        <div class="k">{{ t('库存预警') }}</div>
        <div class="v" style="color: #be123c">{{ supplies.length }}</div>
        <div class="d down">{{ t('需补货') }}</div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px">
      <!-- 工单表 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('房务工单') }}</span>
          <span style="font-size: 11px; color: #9aa1ad"
            >{{ t('共') }} {{ tasks.length }} {{ t('条') }}</span
          >
        </div>
        <table class="data">
          <thead>
            <tr>
              <th style="width: 100px">{{ t('类型') }}</th>
              <th style="width: 100px">{{ t('房间') }}</th>
              <th style="width: 100px">{{ t('优先级') }}</th>
              <th>{{ t('分派 → 状态') }}</th>
              <th class="center" style="width: 100px">{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tag in tasks" :key="tag.id">
              <td>
                <span class="pill pill-blue">{{ TASK_CN[tag.task_type] || tag.task_type }}</span>
              </td>
              <td style="font-weight: 500">{{ tag.room_no }}</td>
              <td>
                <span
                  class="pill"
                  :class="
                    tag.priority >= 4
                      ? 'pill-rose'
                      : tag.priority >= 2
                        ? 'pill-amber'
                        : 'pill-slate'
                  "
                >
                  P{{ tag.priority }}</span
                >
              </td>
              <td>
                <span class="pill" :class="TASK_ST_PILL[tag.status] || 'pill-slate'">
                  {{ TASK_ST_CN[tag.status] || tag.status }}</span
                >
                <span style="color: #9aa1ad; font-size: 12px; margin-left: 6px">{{
                  tag.assignee || t('未分派')
                }}</span>
              </td>
              <td class="center">
                <button
                  v-if="tag.status !== 'done' && tag.status !== 'verified'"
                  class="btn btn-primary"
                  style="padding: 5px 12px; font-size: 12px"
                  @click="finish(tag.id)"
                >
                  {{ t('完成') }}
                </button>
                <span v-else style="color: #9aa1ad; font-size: 12px">—</span>
              </td>
            </tr>
            <tr v-if="!tasks.length">
              <td colspan="5" style="text-align: center; color: #9aa1ad; padding: 30px">
                {{ t('无任务') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 库存预警 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('库存预警') }}</span>
          <span style="font-size: 11px; color: #be123c"
            >{{ supplies.length }} {{ t('项需补') }}</span
          >
        </div>
        <div style="padding: 14px 18px">
          <div
            v-for="s in supplies"
            :key="s.id"
            style="
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 10px 0;
              border-bottom: 1px solid #eef0f4;
              font-size: 13px;
            "
          >
            <div>
              <div style="font-weight: 500; color: #1f2329">{{ s.name }}</div>
              <div style="color: #9aa1ad; font-size: 11px">{{ s.unit }}</div>
            </div>
            <div style="text-align: right">
              <div style="color: #be123c; font-weight: 600; font-variant-numeric: tabular-nums">
                {{ s.current_stock }} / {{ s.safety_stock }}
              </div>
              <div style="color: #9aa1ad; font-size: 11px">{{ t('需补货') }}</div>
            </div>
          </div>
          <div
            v-if="!supplies.length"
            style="text-align: center; color: #047857; padding: 30px; font-size: 13px"
          >
            {{ t('✓ 库存充足') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
