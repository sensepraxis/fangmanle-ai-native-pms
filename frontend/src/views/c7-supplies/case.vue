<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 物资个案：告警 / 洞察 / 领用 —— 与总览卡片一一对应
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
const route = useRoute()
const router = useRouter()

type CaseType = 'alert' | 'insight' | 'requisition'

const loading = ref(true)
const err = ref('')
const caseType = computed(() => String(route.query.type || '') as CaseType)
const caseId = computed(() => Number(route.query.id || 0))

const record = ref<any>(null)
const related = ref<any>({ alerts: [] as any[], insights: [] as any[], requisitions: [] as any[] })

const title = computed(() => {
  const r = record.value
  if (!r) return t('物资个案')
  if (caseType.value === 'alert') {
    const loc = r.room_no || r.floor || t('地点')
    return `${loc} · ${r.supply_name || t('物资告警')}`
  }
  if (caseType.value === 'insight') return r.title || t('AI 洞察')
  if (caseType.value === 'requisition') return `${r.supply_name || t('物资')} · 领用单`
  return t('物资个案')
})

const subtitle = computed(() => {
  if (caseType.value === 'alert') return t('消耗 / 周转告警详情')
  if (caseType.value === 'insight') return t('AI 洞察详情')
  if (caseType.value === 'requisition') return t('领用记录详情')
  return ''
})

async function load() {
  loading.value = true
  err.value = ''
  record.value = null
  try {
    if (!caseId.value || !['alert', 'insight', 'requisition'].includes(caseType.value)) {
      err.value = t('缺少有效的个案参数（type + id）')
      return
    }
    const board = await api.suppliesBoard(hotelStore.hotelId)
    related.value = {
      alerts: board?.alerts || [],
      insights: board?.insights || [],
      requisitions: board?.requisitions || [],
    }
    if (caseType.value === 'alert') {
      record.value = (board?.alerts || []).find((a: any) => Number(a.id) === caseId.value) || null
    } else if (caseType.value === 'insight') {
      record.value = (board?.insights || []).find((a: any) => Number(a.id) === caseId.value) || null
    } else {
      record.value =
        (board?.requisitions || []).find((a: any) => Number(a.id) === caseId.value) || null
    }
    if (!record.value) err.value = t('未找到对应记录，可能已被处理或数据已刷新')
  } catch (e: any) {
    err.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

function go(path: string) {
  router.push(path)
}

onMounted(load)
watch(() => [hotelStore.hotelId, route.query.type, route.query.id], load)
</script>

<template>
  <div class="page case-page">
    <header class="case-head">
      <button type="button" class="back" @click="go('/c7-supplies/price-asst')">
        {{ t('← 物资耗材总览') }}
      </button>
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ title }}</h1>
        <p class="sub">{{ subtitle }}</p>
      </div>
    </header>

    <div v-if="loading" class="muted">{{ t('加载中…') }}</div>
    <div v-else-if="err" class="err-box">{{ err }}</div>

    <template v-else-if="record">
      <!-- 告警 -->
      <section v-if="caseType === 'alert'" class="card main">
        <div class="row">
          <span class="label">{{ t('地点') }}</span>
          <span class="val"
            >{{ record.floor || '—' }} {{ record.room_no ? `· ${record.room_no}` : '' }}</span
          >
        </div>
        <div class="row">
          <span class="label">{{ t('物品') }}</span>
          <span class="val">{{ record.supply_name || '—' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('严重度') }}</span>
          <span class="val sev" :class="record.severity">{{ record.severity || 'mid' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('业务线') }}</span>
          <span class="val">{{ record.line === 'linen' ? t('布草周转') : t('易耗消耗') }}</span>
        </div>
        <div class="block">
          <div class="label">{{ t('说明') }}</div>
          <p>{{ record.message || '—' }}</p>
        </div>
        <div class="block">
          <div class="label">{{ t('状态') }}</div>
          <p>
            {{ record.status || 'open' }} · {{ t('营业日') }} {{ record.biz_date || t('今日') }}
          </p>
        </div>
      </section>

      <!-- 洞察 -->
      <section v-else-if="caseType === 'insight'" class="card main">
        <div class="row">
          <span class="label">{{ t('类别') }}</span>
          <span class="val">{{ record.category || '—' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('影响金额') }}</span>
          <span class="val">¥{{ Number(record.impact_amount || 0).toLocaleString('zh-CN') }}</span>
        </div>
        <div class="block">
          <div class="label">{{ t('标题') }}</div>
          <p class="strong">{{ record.title }}</p>
        </div>
        <div class="block">
          <div class="label">{{ t('建议') }}</div>
          <p>{{ record.recommendation || '—' }}</p>
        </div>
        <div class="block">
          <div class="label">{{ t('状态') }}</div>
          <p>{{ record.status || 'open' }}</p>
        </div>
      </section>

      <!-- 领用 -->
      <section v-else class="card main">
        <div class="row">
          <span class="label">{{ t('时间') }}</span>
          <span class="val">{{ record.created_at || '—' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('部门') }}</span>
          <span class="val">{{ record.dept || '—' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('领用人') }}</span>
          <span class="val">{{ record.requester || '—' }}</span>
        </div>
        <div class="row">
          <span class="label">{{ t('物品') }}</span>
          <span class="val"
            >{{ record.supply_name }} × {{ record.qty }} {{ record.unit || '' }}</span
          >
        </div>
        <div class="row">
          <span class="label">{{ t('状态') }}</span>
          <span class="val">{{ record.status === 'issued' ? t('已领用') : record.status }}</span>
        </div>
        <div v-if="record.note" class="block">
          <div class="label">{{ t('备注') }}</div>
          <p>{{ record.note }}</p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.case-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 18px;
}
.back {
  border: 1px solid var(--outline-variant);
  background: #fff;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}
.sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.muted {
  color: #9aa1ad;
  font-size: 13px;
}
.err-box {
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--error-container);
  color: var(--on-error-container);
  font-size: 13px;
}
.card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: #fff;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 20px rgba(15, 23, 42, 0.06);
  padding: 18px 20px;
  margin-bottom: 14px;
}
.main .row {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
  font-size: 13px;
}
.main .row:last-of-type {
  border-bottom: none;
}
.label {
  color: var(--on-surface-variant);
}
.val {
  font-weight: 600;
  color: var(--on-surface);
}
.val.sev.high {
  color: var(--error);
}
.block {
  margin-top: 12px;
}
.block p {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--on-surface);
}
.block .strong {
  font-weight: 700;
  font-size: 16px;
}
</style>
