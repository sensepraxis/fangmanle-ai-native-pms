<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()
const data = ref<any>(null)

async function load() {
  data.value = await api.paAlerts(hotelStore.hotelId)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
defineExpose({ reload: load })

function goCalendar() {
  router.replace({ path: '/pricing', query: { tab: 'calendar' } })
}

function sevPill(sev: string) {
  if (sev === 'red') return 'pill-rose'
  if (sev === 'yellow') return 'pill-amber'
  return 'pill-blue'
}
function sevLabel(sev: string) {
  return sev === 'red' ? '红' : sev === 'yellow' ? t('黄') : t('蓝')
}
</script>

<template>
  <div v-if="data">
    <div class="banner card-clean">
      <span class="material-symbols-outlined">warning</span>
      <div>
        <b>{{ data.counts.open }} {{ t('条开放告警') }}</b>
        <span> — {{ data.compliance_note }}</span>
      </div>
    </div>

    <div class="list">
      <div v-for="a in data.alerts" :key="a.alert_id" class="item card-clean" :class="a.severity">
        <span class="pill" :class="sevPill(a.severity)">{{ sevLabel(a.severity) }}</span>
        <div class="body">
          <div class="title">{{ a.title }}</div>
          <div class="detail">{{ a.detail }}</div>
          <div class="meta">
            {{ a.detected_at?.slice(0, 16) }} · {{ a.stay_date }} · {{ a.status }}
          </div>
          <button type="button" class="btn btn-link" @click="goCalendar">
            {{ t('建议：') }}{{ a.suggested_action || t('去定价日历确认') }} →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--on-surface);
  background: #fffbeb;
  border-color: #fde68a;
}
.banner .material-symbols-outlined {
  color: #d97706;
  font-size: 22px;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.item {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-left-width: 3px;
}
.item.red {
  border-left-color: var(--error);
}
.item.yellow {
  border-left-color: #d97706;
}
.item.blue {
  border-left-color: var(--primary);
}
.title {
  font-weight: 650;
  font-size: 13.5px;
  margin-bottom: 4px;
  color: var(--on-surface);
}
.detail {
  font-size: 12.5px;
  color: var(--on-surface-variant);
  line-height: 1.5;
}
.meta {
  font-size: 11px;
  color: var(--outline);
  margin-top: 6px;
}
.btn-link {
  margin-top: 8px;
  padding-left: 0;
}
</style>
