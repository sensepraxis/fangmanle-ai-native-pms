<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 价格建议详情：Top3 理由 + 特征快照 + 审计链
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { forecastReturnLocation } from '../lib/askDataBridge'
import { fmt, toast } from '../lib/ui'
import OverviewOpsNav from '../components/OverviewOpsNav.vue'
import AcceptModal from './pricing/AcceptModal.vue'

const route = useRoute()
const router = useRouter()
const d = ref<any>(null)
const loading = ref(true)
const modalOpen = ref(false)

const fromForecast = computed(() => route.query.from === 'forecast')
const contextAction = computed(() => String(route.query.action || '').trim())

async function load() {
  loading.value = true
  try {
    const id = String(route.params.id)
    try {
      d.value = await api.paRecoDetail(id)
    } catch {
      const legacy = await api.pricingDetail(Number(id))
      d.value = {
        ...legacy,
        reco_id: String(legacy.id),
        stay_date: legacy.biz_date,
        top_reasons: legacy.guardrail_reasons || [],
        features_snapshot: {},
        est_n: legacy.suggested_price,
        suggested_base: legacy.base_price,
        decisions: [],
        effects: [],
        legacy: true,
      }
    }
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => route.params.id, load)

function backToList() {
  const q: Record<string, string> = { tab: 'calendar' }
  if (fromForecast.value) q.from = 'forecast'
  if (contextAction.value) q.action = contextAction.value
  router.push({ path: '/pricing', query: q })
}

function backToForecast() {
  router.push(forecastReturnLocation())
}

async function doReject() {
  if (!d.value?.reco_id || d.value.legacy) {
    toast(t('旧建议请在列表操作'), false)
    return
  }
  try {
    await api.paDecide(d.value.reco_id, { action: 'reject', note: '详情页驳回' })
    toast(t('已驳回'))
    load()
  } catch (e: any) {
    toast(e?.message || t('失败'), false)
  }
}
</script>

<template>
  <div class="page">
    <OverviewOpsNav />
    <div class="detail-nav">
      <a class="back-link" @click="backToList">
        <span class="material-symbols-outlined">arrow_back</span>
        {{ t('返回价格助手') }}</a
      >
      <button v-if="fromForecast" type="button" class="btn btn-ghost" @click="backToForecast">
        {{ t('返回营收预测') }}
      </button>
    </div>

    <div v-if="loading" style="color: var(--on-surface-variant)">{{ t('加载中…') }}</div>
    <div v-else-if="d">
      <div class="page-actions">
        <div class="page-head" style="margin: 0">
          <h1>{{ d.room_type_name }} · {{ d.stay_date || d.biz_date }}</h1>
          <p>{{ d.reco_id }} · {{ d.channel || t('渠道') }} · {{ t('状态') }} {{ d.status }}</p>
        </div>
        <div style="display: flex; gap: 8px">
          <button
            v-if="d.status === 'pending' && !d.legacy"
            class="btn btn-primary"
            @click="modalOpen = true"
          >
            {{ t('采纳') }}
          </button>
          <button v-if="d.status === 'pending'" class="btn btn-ghost" @click="doReject">
            {{ t('驳回') }}
          </button>
        </div>
      </div>

      <div class="kpi-grid" style="margin-bottom: 16px">
        <div class="kpi">
          <div class="k">{{ t('当前挂牌价') }}</div>
          <div class="v">{{ fmt(d.current_price) }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('AI 建议价') }}</div>
          <div class="v" style="color: var(--primary)">{{ fmt(d.suggested_price) }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('建议底价 B*') }}</div>
          <div class="v">{{ fmt(d.suggested_base) }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ t('预估净到手 N*') }}</div>
          <div class="v">{{ fmt(d.est_n) }}</div>
        </div>
      </div>

      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('Top3 理由（可解释）') }}</span>
        </div>
        <ol class="reasons">
          <li v-for="(r, i) in d.top_reasons || []" :key="i">{{ r }}</li>
        </ol>
        <div v-if="d.features_snapshot" class="feat">
          <div>Pace：{{ d.features_snapshot.pace?.pace_ratio ?? '—' }}</div>
          <div>Tightness：{{ d.features_snapshot.tightness ?? '—' }}</div>
          <div>Gap：{{ d.features_snapshot.gap ?? '—' }}</div>
          <div>{{ t('阶段：') }}{{ d.features_snapshot.horizon ?? '—' }}</div>
        </div>
      </div>

      <div class="card-clean" style="margin-top: 14px">
        <div class="card-head">
          <span>{{ t('审计链') }}</span>
        </div>
        <div class="audit">
          <div><b>Suggestion</b> {{ d.reco_id }}</div>
          <div v-for="dec in d.decisions || []" :key="dec.decision_id">
            <b>Decision</b> {{ dec.decision }} · {{ t('工号') }} {{ dec.decided_by }} ·
            {{ dec.decided_at }}
          </div>
          <div v-for="ef in d.effects || []" :key="ef.effect_id">
            <b>Effect</b> {{ ef.metric }} {{ ef.baseline_value }} → {{ ef.actual_value }}（{{
              ef.delta_pct
            }}%）
          </div>
          <div v-if="!(d.decisions || []).length" style="color: var(--on-surface-variant)">
            {{ t('尚未产生决策单') }}
          </div>
        </div>
      </div>
    </div>

    <AcceptModal :open="modalOpen" :reco="d" @close="modalOpen = false" @done="load" />
  </div>
</template>

<style scoped>
.detail-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.detail-nav .back-link {
  margin: 0;
  cursor: pointer;
}
.reasons {
  padding: 12px 18px 8px;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--on-surface);
}
.feat {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 0 16px 14px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.audit {
  padding: 12px 16px 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--on-surface);
}
@media (max-width: 700px) {
  .feat {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
