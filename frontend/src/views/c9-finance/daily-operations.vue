<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { localizeSeedText } from '../../lib/localizeSeed'
import { authHeaders } from '../../lib/api/client'

/**
 * 财务报表 · 财务数据中心
 * 时间筛选 + 4 KPI + 6 类报表树 + 预览 + Excel/PDF/CSV 导出 + 就地 AI 解读（本地 LLM）
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'

const router = useRouter()

const period = ref<'today' | 'week' | 'month' | 'year' | 'custom'>('month')
const compare = ref('yoy')
const customStart = ref('')
const customEnd = ref('')
const showCustom = ref(false)

const loading = ref(false)
const center = ref<any>(null)
const report = ref<any>(null)
const exports = ref<any[]>([])
const activeCode = ref('manager_flash')
const openCats = ref<Record<string, boolean>>({ ops: true, revenue: true })
const exportOpen = ref(false)
const exporting = ref(false)

const aiLoading = ref(false)
const aiError = ref('')
const aiResult = ref<any>(null)
const aiModelMeta = computed(() => formatAiModelMeta(aiResult.value))
const aiToken = ref(0)
const aiConfirming = ref<number | null>(null)
const aiConfirmOpen = ref(false)
const aiConfirmIndex = ref(-1)
const aiConfirmRemark = ref('')

const MODULE_CN: Record<string, string> = {
  finance: '财务',
  revenue: '收益',
  marketing: '营销',
  ops: '运营',
}
const SEV_CN: Record<string, string> = {
  info: '提示',
  warn: '警告',
  critical: '严重',
}
const SEV_PILL: Record<string, string> = {
  info: 'pill-slate',
  warn: 'pill-amber',
  critical: 'pill-rose',
}
const ROLE_CN: Record<string, string> = {
  manager: '店长',
  gm: '总经理',
  finance: '财务',
  revenue: '收益',
}
const KIND_CN: Record<string, string> = {
  draft_reco: '起草调价',
  draft_receivable: '起草催收',
  mark_anomaly: '标记异常',
  submit_close: '结账草稿',
  draft_close: '销账建议',
  escalate: '上报',
  export: '归档导出',
}

function loc(s?: string | null) {
  return localizeSeedText(s)
}

/** 报表单元格中需要按 msgid 再翻一层的文本列 */
const TEXT_COLS = new Set([
  'dept',
  'metric',
  'method',
  'item',
  'channel',
  'customer',
  'name',
  'title',
  'type',
  'note',
  'room_type',
])

const PERIODS = [
  { key: 'today', label: t('今日') },
  { key: 'week', label: t('本周') },
  { key: 'month', label: t('本月') },
  { key: 'year', label: t('本年') },
  { key: 'custom', label: t('自定义') },
] as const

const COMPARE_OPTS = [
  { key: 'yoy', label: t('同比去年（去年同期）') },
  { key: 'mom', label: t('环比上期（上一期间）') },
  { key: 'budget', label: t('对比预算') },
  { key: 'none', label: t('不对比') },
]

const periodOpts = computed(() => ({
  period: period.value,
  start: period.value === 'custom' ? customStart.value || undefined : undefined,
  end: period.value === 'custom' ? customEnd.value || undefined : undefined,
  compare: compare.value,
}))

function fmtSize(n: number) {
  if (!n) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function cellVal(v: any) {
  if (v == null || v === '') return '—'
  if (typeof v === 'number') return v.toLocaleString('zh-CN')
  return String(v)
}

async function loadCenter() {
  loading.value = true
  try {
    center.value = await api.financeReportsCenter(hotelStore.hotelId, periodOpts.value)
    if (!openCats.value || !Object.keys(openCats.value).length) {
      openCats.value = { ops: true, revenue: true }
    }
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

async function loadReport(code?: string) {
  const c = code || activeCode.value
  activeCode.value = c
  try {
    report.value = await api.financeReportDetail(hotelStore.hotelId, c, periodOpts.value)
    exports.value = await api.financeReportExports(hotelStore.hotelId, c)
  } catch (e: any) {
    toast(e?.message || t('报表加载失败'), false)
  }
}

async function refresh() {
  clearAi()
  await loadCenter()
  await loadReport(activeCode.value)
}

function setPeriod(p: typeof period.value) {
  if (p === 'custom') {
    showCustom.value = true
    if (!customStart.value) {
      const t = new Date()
      customEnd.value = t.toISOString().slice(0, 10)
      const s = new Date(t.getFullYear(), t.getMonth(), 1)
      customStart.value = s.toISOString().slice(0, 10)
    }
  } else {
    showCustom.value = false
  }
  period.value = p
  refresh()
}

function toggleCat(key: string) {
  openCats.value = { ...openCats.value, [key]: !openCats.value[key] }
}

function selectReport(item: any) {
  if (item.link && (item.code === 'night_daily' || item.code === 'night_exceptions')) {
    // 仍可预览，同时提供跳转
  }
  clearAi()
  loadReport(item.code)
}

function goNightAudit() {
  router.push('/c9-finance/night-audit')
}

function clearAi() {
  aiToken.value += 1
  aiLoading.value = false
  aiError.value = ''
  aiResult.value = null
  aiConfirmOpen.value = false
  aiConfirmIndex.value = -1
  aiConfirmRemark.value = ''
  aiConfirming.value = null
}

async function runAiInterpret() {
  if (aiLoading.value) return
  if (!report.value) {
    toast(t('请先选择左侧报表'), false)
    return
  }
  const token = ++aiToken.value
  aiLoading.value = true
  aiError.value = ''
  aiResult.value = null
  try {
    const res = await api.financeReportAiInterpret(hotelStore.hotelId, activeCode.value, {
      ...periodOpts.value,
    })
    if (token !== aiToken.value) return
    aiResult.value = res
    if (res?.status === 'failed') {
      aiError.value = loc(res?.insight) || t('解读失败')
    }
  } catch (e: any) {
    if (token !== aiToken.value) return
    aiError.value = e?.message || t('AI 解读失败')
    toast(aiError.value, false)
  } finally {
    if (token === aiToken.value) aiLoading.value = false
  }
}

function openConfirmAction(idx: number) {
  aiConfirmIndex.value = idx
  aiConfirmRemark.value = ''
  aiConfirmOpen.value = true
}

async function decideAction(decision: 'confirmed' | 'dismissed', idx?: number) {
  const interpretationId = aiResult.value?.id
  const actionIndex = idx ?? aiConfirmIndex.value
  if (!interpretationId || actionIndex < 0) return
  aiConfirming.value = actionIndex
  try {
    const res = await api.financeReportAiActionDecide(
      hotelStore.hotelId,
      interpretationId,
      actionIndex,
      {
        decision,
        remark: aiConfirmRemark.value || undefined,
      },
    )
    aiResult.value = res
    aiConfirmOpen.value = false
    const exec = res?.last_decision?.exec_result
    if (decision === 'confirmed') {
      toast(t('已确认'))
      if (exec?.goto) router.push(exec.goto)
      if (exec?.export?.id) {
        exports.value = await api.financeReportExports(hotelStore.hotelId, activeCode.value)
        downloadExport(exec.export.id, exec.export.file_name)
      }
    } else {
      toast(t('已忽略'))
    }
  } catch (e: any) {
    toast(e?.message || t('操作失败'), false)
  } finally {
    aiConfirming.value = null
  }
}

function viewActionDetail(act: any) {
  if (act?.goto) router.push(act.goto)
}

async function doExport(fmt: string) {
  exportOpen.value = false
  exporting.value = true
  try {
    const row = await api.financeReportExport(hotelStore.hotelId, activeCode.value, {
      format: fmt,
      ...periodOpts.value,
    })
    toast(row.async_job ? '已发起导出（大数据量任务）' : `已导出 ${fmt.toUpperCase()}`)
    exports.value = await api.financeReportExports(hotelStore.hotelId, activeCode.value)
    if (row?.id) downloadExport(row.id, row.file_name)
  } catch (e: any) {
    toast(e?.message || t('导出失败'), false)
  } finally {
    exporting.value = false
  }
}

async function downloadExport(id: number, fileName?: string) {
  try {
    const url = api.financeReportExportDownloadUrl(hotelStore.hotelId, id)
    const res = await fetch(url, { headers: authHeaders() })
    if (!res.ok) throw new Error(t('下载失败'))
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = fileName || `report_${id}`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e: any) {
    toast(e?.message || t('下载失败'), false)
  }
}

function onDocClick() {
  exportOpen.value = false
}

onMounted(async () => {
  document.addEventListener('click', onDocClick)
  await refresh()
})
onUnmounted(() => document.removeEventListener('click', onDocClick))
watch(() => hotelStore.hotelId, refresh)

function printReport() {
  window.print()
}

const defaultFmtLabel = computed(() => {
  const f = report.value?.default_format || 'xlsx'
  return f === 'pdf' ? 'PDF' : f === 'csv' ? 'CSV' : 'Excel'
})

function fmtPill(fmt: string) {
  if (fmt === 'pdf') return 'pill-rose'
  if (fmt === 'csv') return 'pill-green'
  return 'pill-blue'
}
</script>

<template>
  <div class="page fr-page">
    <FinanceOpsNav />

    <div class="page-head">
      <h1 class="font-display-lg text-display-lg text-on-background">
        {{ t('财务报表 · 财务数据中心') }}
      </h1>
    </div>

    <div class="toolbar fr-toolbar">
      <div class="range-seg" role="tablist">
        <button
          v-for="p in PERIODS"
          :key="p.key"
          type="button"
          :class="{ on: period === p.key }"
          @click="setPeriod(p.key)"
        >
          {{ p.label }}
        </button>
      </div>
      <div v-if="showCustom || period === 'custom'" class="custom-range">
        <input v-model="customStart" class="toolbar-input" type="date" @change="refresh" />
        <span>~</span>
        <input v-model="customEnd" class="toolbar-input" type="date" @change="refresh" />
      </div>
      <button type="button" class="btn btn-primary" @click="refresh">
        {{ center?.period_label || t('选择期间') }}
      </button>
      <label class="compare ml-auto" :title="t('选择报表数字下方涨跌的参照基准')">
        <span>{{ t('对比基准') }}</span>
        <select v-model="compare" @change="refresh">
          <option v-for="o in COMPARE_OPTS" :key="o.key" :value="o.key">{{ o.label }}</option>
        </select>
      </label>
    </div>

    <div class="kpi-grid">
      <div v-for="k in center?.kpis || []" :key="k.key" class="kpi" :class="{ 'kpi-ai': k.ai }">
        <div class="k">
          {{ t(k.label) }}
          <span v-if="k.ai" class="pill pill-amber" style="margin-left: 6px">AI</span>
        </div>
        <div class="v">{{ k.value_fmt }}</div>
        <div class="d" :class="k.tone === 'ai' ? 'flat' : k.tone">{{ t(k.delta || '') }}</div>
      </div>
    </div>

    <div v-if="loading && !center" class="rf-empty">{{ t('加载中…') }}</div>

    <div class="main-grid">
      <aside class="card-clean reports-nav">
        <div class="card-head">{{ t('报表分类（6 类）') }}</div>
        <div
          v-for="cat in center?.categories || []"
          :key="cat.key"
          class="cat"
          :class="{ open: !!openCats[cat.key] }"
        >
          <button type="button" class="cat-h" @click="toggleCat(cat.key)">
            <span class="arr">▶</span>{{ t(cat.label) }}
          </button>
          <div class="cat-list">
            <button
              v-for="r in cat.reports"
              :key="r.code"
              type="button"
              class="cat-item"
              :class="{ active: activeCode === r.code }"
              @click="selectReport(r)"
            >
              <span>{{ t(r.name) }}{{ r.link && r.code.startsWith('night') ? ' →' : '' }}</span>
              <span v-if="r.badge" class="pill pill-rose">{{ r.badge }}</span>
            </button>
          </div>
        </div>
      </aside>

      <section class="card-clean report-view">
        <div class="card-head view-head">
          <div class="title-wrap">
            <div class="title-row">
              <span>{{ report?.name ? t(report.name) : t('报表预览') }}</span>
              <span v-if="report" class="pill pill-blue"
                >{{ t(report.category) }} · {{ t(report.schedule || '报表') }}</span
              >
            </div>
            <div v-if="report?.meta" class="meta">{{ report.meta }}</div>
          </div>
          <div class="view-actions" @click.stop>
            <button
              type="button"
              class="btn btn-ghost"
              :disabled="aiLoading"
              @click="runAiInterpret"
            >
              {{ aiLoading ? t('解读中…') : t('✦ AI 解读') }}
            </button>
            <button v-if="report?.link" type="button" class="btn btn-ghost" @click="goNightAudit">
              {{ t('打开夜审') }}
            </button>
            <button type="button" class="btn btn-ghost" @click="printReport">
              {{ t('打印') }}
            </button>
            <div class="export-wrap">
              <button
                type="button"
                class="btn btn-primary"
                :disabled="exporting"
                @click="exportOpen = !exportOpen"
              >
                {{ t('导出 ▾') }}
              </button>
              <div v-if="exportOpen" class="export-menu card-clean">
                <button type="button" class="mi" @click="doExport('xlsx')">
                  {{ t('导出为 Excel') }}
                  <span class="ext">.xlsx</span>
                  <span v-if="(report?.default_format || 'xlsx') === 'xlsx'" class="def">{{
                    t('默认')
                  }}</span>
                </button>
                <button type="button" class="mi" @click="doExport('pdf')">
                  {{ t('导出为 PDF') }}
                  <span class="ext">.pdf</span>
                  <span v-if="report?.default_format === 'pdf'" class="def">{{ t('默认') }}</span>
                </button>
                <button type="button" class="mi" @click="doExport('csv')">
                  {{ t('导出为 CSV') }}
                  <span class="ext">.csv</span>
                  <span v-if="report?.default_format === 'csv'" class="def">{{ t('默认') }}</span>
                </button>
                <div class="sep" />
                <div class="mi tip">
                  {{ t('本类默认') }} {{ defaultFmtLabel }} · {{ t('归档保留') }} 7 {{ t('年') }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="ai-card ai-strip">
          <div class="ttl">{{ t('✦ 想让 AI 帮你分析这份报表？') }}</div>
          <div class="ai-body">
            <button
              type="button"
              class="btn btn-link"
              :disabled="aiLoading"
              @click="runAiInterpret"
            >
              {{ aiLoading ? t('解读中…') : aiResult ? t('重新解读 →') : t('立即解读 →') }}
            </button>
          </div>
          <div v-if="aiLoading" class="ai-result muted">{{ t('正在分析当前报表…') }}</div>
          <div v-else-if="aiError && !aiResult?.insight" class="ai-result err">{{ aiError }}</div>
          <div v-else-if="aiResult" class="ai-panel">
            <div class="ai-block">
              <div class="ai-block-h">
                {{ t('本期解读') }}
                <span v-if="aiModelMeta" class="model-meta">{{ aiModelMeta }}</span>
              </div>
              <p class="ai-insight">{{ loc(aiResult.insight) }}</p>
            </div>
            <div v-if="aiResult.findings?.length" class="ai-block">
              <div class="ai-block-h">{{ t('关键发现') }}</div>
              <ul class="ai-list">
                <li v-for="(f, i) in aiResult.findings" :key="i">
                  <span class="pill" :class="SEV_PILL[f.severity] || 'pill-slate'">{{
                    t(SEV_CN[f.severity] || f.severity)
                  }}</span>
                  <div>
                    <b>{{ loc(f.title) }}</b>
                    <div class="ev">{{ loc(f.evidence) }}</div>
                  </div>
                </li>
              </ul>
            </div>
            <div v-if="aiResult.suggestions?.length" class="ai-block">
              <div class="ai-block-h">{{ t('建议') }}</div>
              <ul class="ai-list">
                <li v-for="(s, i) in aiResult.suggestions" :key="i">
                  <span class="pill pill-blue">{{ t(MODULE_CN[s.module] || s.module) }}</span>
                  <div>
                    <b>{{ loc(s.title) }}</b>
                    <div class="ev">{{ loc(s.rationale) }}</div>
                  </div>
                </li>
              </ul>
            </div>
            <div v-if="aiResult.actions?.length" class="ai-block">
              <div class="ai-block-h">{{ t('可执行操作（需确认）') }}</div>
              <div
                v-for="(a, i) in aiResult.actions"
                :key="i"
                class="ai-action"
                :class="{ done: a.status && a.status !== 'pending' }"
              >
                <div class="ai-action-main">
                  <span class="pill pill-slate">{{ t(KIND_CN[a.kind] || a.kind) }}</span>
                  <div>
                    <b>{{ loc(a.title) }}</b>
                    <div class="ev">
                      {{ t('角色') }} {{ t(ROLE_CN[a.required_role] || a.required_role) }} ·
                      {{
                        a.status === 'pending'
                          ? t('待确认')
                          : a.status === 'confirmed'
                            ? t('已确认')
                            : t('已忽略')
                      }}
                    </div>
                  </div>
                </div>
                <div v-if="!a.status || a.status === 'pending'" class="ai-action-ops">
                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="aiConfirming === i"
                    @click="openConfirmAction(i)"
                  >
                    {{ t('确认执行') }}
                  </button>
                  <button
                    type="button"
                    class="btn btn-ghost"
                    :disabled="aiConfirming === i"
                    @click="decideAction('dismissed', i)"
                  >
                    {{ t('忽略') }}
                  </button>
                  <button
                    v-if="a.goto"
                    type="button"
                    class="btn btn-link"
                    @click="viewActionDetail(a)"
                  >
                    {{ t('查看详情') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="aiConfirmOpen" class="ai-modal-mask" @click.self="aiConfirmOpen = false">
          <div class="ai-modal card-clean">
            <div class="card-head">{{ t('确认执行') }}</div>
            <div class="ai-modal-body">
              <p>{{ t('将记录本条 AI 起草操作并由人工确认，不会自动改账。请确认后继续。') }}</p>
              <p v-if="aiResult?.actions?.[aiConfirmIndex]" class="ai-modal-act">
                <b>{{ loc(aiResult.actions[aiConfirmIndex].title) }}</b>
              </p>
              <label class="ai-modal-lab">
                {{ t('备注（可选）') }}
                <input
                  v-model="aiConfirmRemark"
                  class="toolbar-input"
                  type="text"
                  :placeholder="t('工号 / 说明')"
                />
              </label>
              <div class="ai-modal-ops">
                <button type="button" class="btn btn-ghost" @click="aiConfirmOpen = false">
                  {{ t('取消') }}
                </button>
                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="aiConfirming != null"
                  @click="decideAction('confirmed')"
                >
                  {{ t('确认执行') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="view-body">
          <template v-for="(sec, si) in report?.sections || []" :key="si">
            <div v-if="sec.type === 'stats'" class="view-section">
              <div class="section-h">{{ t(sec.title) }}</div>
              <div class="stat-grid">
                <div v-for="(it, ii) in sec.items" :key="ii" class="stat-cell">
                  <div class="lab">{{ t(it.lab) }}</div>
                  <div class="val">
                    {{ it.v }}
                    <span v-if="it.small" class="small">{{ it.small }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="sec.type === 'table'" class="view-section">
              <div class="section-h">{{ t(sec.title) }}</div>
              <div class="table-wrap">
                <table class="data">
                  <thead>
                    <tr>
                      <th
                        v-for="col in sec.columns"
                        :key="col.key"
                        :class="col.align === 'num' ? 'num' : col.align === 'ctr' ? 'center' : ''"
                      >
                        {{ t(col.label) }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(row, ri) in sec.rows"
                      :key="ri"
                      :class="{ subtotal: row._row === 'subtotal', total: row._row === 'total' }"
                    >
                      <td
                        v-for="col in sec.columns"
                        :key="col.key"
                        :class="[
                          col.align === 'num' ? 'num' : col.align === 'ctr' ? 'center' : '',
                          col.key === 'commission_formula' ? 'formula-cell' : '',
                        ]"
                      >
                        <template v-if="col.key === 'yoy'">
                          <span class="yoy" :class="row.yoy_tone">{{
                            t(String(row.yoy ?? ''))
                          }}</span>
                        </template>
                        <template v-else-if="TEXT_COLS.has(col.key)">
                          {{ t(String(row[col.key] ?? '')) }}
                        </template>
                        <template v-else>{{ cellVal(row[col.key]) }}</template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="sec.note" class="sec-note">{{ t(sec.note) }}</p>
            </div>
          </template>
          <div v-if="!report?.sections?.length" class="rf-empty soft">
            {{ t('请选择左侧报表') }}
          </div>
        </div>

        <div class="view-foot">
          <div class="foot-h">{{ t('导出历史（自动归档 7 年）') }}</div>
          <div v-if="!exports.length" class="rf-empty soft tiny">{{ t('暂无导出记录') }}</div>
          <div class="export-list">
            <div
              v-for="ex in exports"
              :key="ex.id"
              class="export-row"
              :class="{ processing: ex.status === 'processing' }"
            >
              <span class="pill" :class="fmtPill(ex.format)">{{
                (ex.format || '').toUpperCase()
              }}</span>
              <span class="nm">{{ ex.file_name }}</span>
              <span class="sz">{{ fmtSize(ex.size_bytes) }}</span>
              <span class="tm">{{ ex.generated_at }} · {{ ex.generated_by }}</span>
              <button
                v-if="ex.status === 'ready'"
                type="button"
                class="btn btn-link"
                @click="downloadExport(ex.id, ex.file_name)"
              >
                {{ t('重下') }}
              </button>
              <span v-else class="pill pill-amber">{{ t('生成中') }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.fr-page {
  padding-bottom: 2rem;
}
.fr-toolbar {
  flex-wrap: wrap;
}
.compare {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.compare select {
  appearance: none;
  border: 1px solid var(--outline-variant);
  background: #fff;
  color: var(--on-surface);
  font-size: 13px;
  padding: 6px 28px 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  min-width: 11em;
}
.custom-range {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ml-auto {
  margin-left: auto;
}

.range-seg {
  display: inline-flex;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.range-seg button {
  border: 0;
  background: transparent;
  padding: 6px 12px;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
  font-weight: 500;
}
.range-seg button + button {
  border-left: 1px solid var(--outline-variant);
}
.range-seg button.on {
  background: var(--primary);
  color: #fff;
}

.kpi .k {
  font-weight: 700;
}
.kpi-ai {
  border-color: color-mix(in srgb, var(--tertiary) 35%, var(--outline-variant));
  background: color-mix(in srgb, var(--tertiary) 6%, #fff);
}
.kpi-ai .k {
  color: var(--tertiary);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.main-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 14px;
}
@media (max-width: 960px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

.reports-nav {
  align-self: start;
  position: sticky;
  top: 0;
  overflow: hidden;
}
.cat-h {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 16px;
  border: 0;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.cat-h:hover {
  background: var(--surface-low);
}
.arr {
  font-size: 10px;
  color: var(--on-surface-variant);
  width: 12px;
  display: inline-block;
  transition: transform 0.2s;
}
.cat.open .arr {
  transform: rotate(90deg);
}
.cat-list {
  display: none;
  padding: 0 12px 8px 28px;
}
.cat.open .cat-list {
  display: block;
}
.cat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  margin: 2px 0;
  border: 0;
  background: transparent;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.cat-item:hover {
  background: var(--surface-low);
  color: var(--on-surface);
}
.cat-item.active {
  background: color-mix(in srgb, var(--primary) 10%, #fff);
  color: var(--primary);
  font-weight: 600;
}

.report-view {
  overflow: hidden;
}
.view-head {
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.title-wrap {
  min-width: 0;
  flex: 1;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 15px;
  font-weight: 700;
}
.meta {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 4px;
  font-weight: 400;
}
.view-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.export-wrap {
  position: relative;
}
.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 6px;
  z-index: 20;
  min-width: 200px;
  padding: 6px;
}
.export-menu .mi {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  border-radius: 6px;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.export-menu .mi:hover {
  background: var(--surface-low);
  color: var(--on-surface);
}
.export-menu .ext {
  margin-left: auto;
  font-size: 10px;
  color: var(--on-surface-variant);
  font-family: monospace;
}
.export-menu .def {
  font-size: 10px;
  color: var(--primary);
  font-weight: 600;
}
.export-menu .sep {
  height: 1px;
  background: var(--surface-high);
  margin: 4px 0;
}
.export-menu .tip {
  cursor: default;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.export-menu .tip:hover {
  background: transparent;
}

.ai-strip {
  margin: 14px 18px 0;
}
.ai-body {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}
.ai-result {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--surface-high);
}
.ai-result.muted {
  font-size: 13px;
  color: var(--on-surface-variant);
}
.ai-result.err {
  font-size: 13px;
  color: #be123c;
}
.ai-panel {
  margin-top: 12px;
  padding-top: 4px;
  border-top: 1px solid var(--surface-high);
}
.ai-block {
  margin-top: 12px;
}
.ai-block-h {
  font-size: 12px;
  font-weight: 700;
  color: var(--tertiary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.model-meta {
  font-size: 11px;
  font-weight: 600;
  color: var(--on-surface-variant);
  font-variant-numeric: tabular-nums;
}
.ai-insight {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--on-surface);
  font-weight: 600;
}
.ai-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-list li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 13px;
}
.ai-list b {
  font-weight: 600;
  color: var(--on-surface);
}
.ai-list .ev {
  margin-top: 2px;
  color: var(--on-surface-variant);
  font-size: 12px;
  line-height: 1.45;
}
.ai-action {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  margin-top: 8px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: #fff;
}
.ai-action.done {
  opacity: 0.72;
  background: var(--surface-low);
}
.ai-action-main {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}
.ai-action-ops {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.ai-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.ai-modal {
  width: min(420px, 100%);
  overflow: hidden;
}
.ai-modal-body {
  padding: 16px 18px 18px;
  font-size: 13px;
  color: var(--on-surface);
}
.ai-modal-body p {
  margin: 0 0 10px;
  line-height: 1.5;
}
.ai-modal-act {
  padding: 8px 10px;
  background: var(--surface-low);
  border-radius: 8px;
}
.ai-modal-lab {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
  color: var(--on-surface-variant);
}
.ai-modal-ops {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.view-body {
  padding: 0 18px 18px;
}
.view-section {
  margin-top: 16px;
}
.section-h {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--on-surface);
}
.section-h::before {
  content: '';
  width: 3px;
  height: 13px;
  background: var(--primary);
  border-radius: 2px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
@media (max-width: 900px) {
  .stat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.stat-cell {
  background: var(--surface-low);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}
.stat-cell .lab {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.stat-cell .val {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--on-surface);
}
.stat-cell .small {
  font-size: 11px;
  color: var(--on-surface-variant);
  font-weight: 500;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius);
}
table.data tbody tr.subtotal td {
  background: var(--surface-low);
  font-weight: 600;
}
table.data tbody tr.total td {
  background: color-mix(in srgb, var(--primary) 8%, #fff);
  font-weight: 700;
  color: var(--primary);
  border-top: 2px solid var(--primary);
}
.yoy {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.yoy.up {
  color: #e11d48;
}
.yoy.down {
  color: #059669;
}
.sec-note {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: var(--on-surface-variant);
}
.formula-cell {
  font-size: 11.5px;
  color: var(--on-surface-variant);
  font-variant-numeric: tabular-nums;
  max-width: 280px;
  white-space: normal;
  line-height: 1.45;
}

.view-foot {
  padding: 12px 18px;
  border-top: 1px solid var(--surface-high);
  background: var(--surface-low);
}
.foot-h {
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
}
.export-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.export-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  font-size: 12px;
}
.export-row.processing {
  background: #fef3c7;
}
.nm {
  flex: 1;
  font-weight: 500;
  min-width: 120px;
  color: var(--on-surface);
}
.tm,
.sz {
  color: var(--on-surface-variant);
  font-size: 11px;
}
.rf-empty {
  padding: 24px;
  text-align: center;
  color: var(--on-surface-variant);
}
.rf-empty.soft {
  padding: 16px;
}
.rf-empty.tiny {
  padding: 8px;
  font-size: 12px;
}
</style>
