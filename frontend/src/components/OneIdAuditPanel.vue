<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * OneID 归并审计内联面板 —— 渠道身份表 + 归并时间线
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'

const props = defineProps<{
  guestId: number
  guestName?: string
}>()

const router = useRouter()
const loading = ref(false)
const err = ref('')
const data = ref<any>(null)

async function load() {
  if (!props.guestId) return
  loading.value = true
  err.value = ''
  try {
    data.value = await api.guestOneidAudit(props.guestId)
  } catch (e: any) {
    data.value = null
    err.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.guestId, load, { immediate: true })

const identities = () => data.value?.identities || []
const events = () => data.value?.events || []

function confPct(c: number) {
  return `${Math.round(Number(c || 0) * 100)}%`
}
function goLineage() {
  router.push(`/b-data/data-source-lineage?guestId=${props.guestId}`)
}
function dotClass(action: string) {
  if (action === 'oneid_born') return 'born'
  if (action === 'primary_bind') return 'create'
  if (action === 'merge_confirm') return 'confirm'
  return 'link'
}
</script>

<template>
  <div class="audit-panel">
    <div v-if="loading" class="muted">{{ t('正在加载归并审计…') }}</div>
    <div v-else-if="err" class="err-box">{{ err }}</div>
    <template v-else>
      <section class="block">
        <div class="block-head">
          <h3 class="h3">{{ t('已绑定渠道身份') }}</h3>
          <button type="button" class="link-btn" @click="goLineage">
            <span class="material-symbols-outlined">account_tree</span>
            {{ t('数据溯源') }}
          </button>
        </div>
        <div v-if="!identities().length" class="muted">
          {{ t('暂无跨渠道身份记录（仅本店主档）。') }}
        </div>
        <div v-else class="table-wrap">
          <table class="tbl">
            <thead>
              <tr>
                <th>{{ t('渠道') }}</th>
                <th>{{ t('外部账号 ID') }}</th>
                <th>{{ t('归并方式') }}</th>
                <th>{{ t('置信度') }}</th>
                <th>{{ t('归并时间') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in identities()" :key="i.id">
                <td>
                  <span class="chip">{{ i.source_cn || i.source || '—' }}</span>
                  <span v-if="i.is_primary" class="chip primary">{{ t('主档') }}</span>
                </td>
                <td class="mono">{{ i.external_id || '—' }}</td>
                <td class="method">{{ i.merge_method_cn || i.merge_method || '—' }}</td>
                <td>
                  <div class="conf-row">
                    <div class="bar"><div :style="{ width: confPct(i.confidence) }" /></div>
                    <span>{{ confPct(i.confidence) }}</span>
                  </div>
                </td>
                <td class="muted">
                  {{
                    String(i.linked_at || '')
                      .replace('T', ' ')
                      .slice(0, 19) || '—'
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="block">
        <h3 class="h3">{{ t('归并时间线') }}</h3>
        <div class="timeline">
          <div v-for="e in events()" :key="e.id + '-' + e.action" class="ev">
            <div class="dot" :class="dotClass(e.action)" />
            <div class="ev-body">
              <div class="ev-top">
                <strong>{{ e.action_cn }}</strong>
                <span v-if="e.source && e.source !== 'system'" class="chip">{{
                  e.source_cn || e.source
                }}</span>
                <span v-if="e.merge_method_cn" class="method-badge">{{ e.merge_method_cn }}</span>
                <span v-if="e.confidence != null" class="conf-badge"
                  >{{ t('置信度') }} {{ confPct(e.confidence) }}</span
                >
                <span class="when">{{ e.at || '—' }}</span>
              </div>
              <p class="ev-note">{{ e.note }}</p>
              <p v-if="e.operator" class="ev-meta">{{ t('操作方：') }}{{ e.operator }}</p>
              <p v-if="e.external_id && e.action !== 'oneid_born'" class="ev-id mono">
                {{ t('外部账号：') }}{{ e.external_id }}
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.audit-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 12px;
  border-top: 1px solid color-mix(in srgb, var(--primary) 18%, var(--outline-variant));
}
.muted {
  color: var(--on-surface-variant);
  font-size: 13px;
}
.err-box {
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef3f2;
  border: 1px solid #fecaca;
  color: #b42318;
  font-size: 13px;
}
.block {
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 750;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  padding: 0;
}
.link-btn .material-symbols-outlined {
  font-size: 16px;
}
.link-btn:hover {
  text-decoration: underline;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.table-wrap {
  overflow: auto;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th {
  text-align: left;
  padding: 8px 6px;
  color: var(--on-surface-variant);
  font-weight: 650;
  border-bottom: 1px solid var(--outline-variant);
}
.tbl td {
  padding: 10px 6px;
  border-bottom: 1px solid var(--outline-variant);
  vertical-align: middle;
}
.chip {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  background: var(--primary-fixed, #d8e2ff);
  color: var(--on-primary-fixed-variant, #004493);
}
.chip.primary {
  margin-left: 4px;
  background: #ecfdf3;
  color: #027a48;
}
.method {
  font-size: 12px;
  color: var(--on-surface-variant);
  max-width: 140px;
}
.conf-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bar {
  width: 64px;
  height: 6px;
  border-radius: 999px;
  background: var(--surface-container-high);
  overflow: hidden;
}
.bar > div {
  height: 100%;
  background: var(--primary);
  border-radius: 999px;
}
.timeline {
  position: relative;
  padding-left: 16px;
  border-left: 2px solid var(--surface-container-high);
}
.ev {
  position: relative;
  padding: 0 0 14px 12px;
}
.dot {
  position: absolute;
  left: -23px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #fff;
  background: var(--primary);
  box-shadow: 0 0 0 1px var(--outline-variant);
}
.dot.born {
  background: var(--tertiary);
}
.dot.create {
  background: #027a48;
}
.dot.link {
  background: var(--primary);
}
.dot.confirm {
  background: #f59e0b;
}
.ev-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 13px;
}
.when {
  margin-left: auto;
  font-size: 11px;
  color: var(--on-surface-variant);
  white-space: nowrap;
}
.conf-badge,
.method-badge {
  font-size: 11px;
  font-weight: 650;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
}
.method-badge {
  color: var(--on-surface-variant);
}
.ev-note {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.5;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface-container-low);
}
.ev-meta {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.ev-id {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--on-surface-variant);
}
</style>
