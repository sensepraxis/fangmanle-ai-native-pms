<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 数据合规中心：密钥本地保管、揭密审计、留存匿名化
 */
import { ref, onMounted } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'

const loading = ref(true)
const busy = ref(false)
const status = ref<any>(null)
const audits = ref<any[]>([])

async function load() {
  loading.value = true
  try {
    status.value = await api.complianceStatus(hotelStore.hotelId)
    try {
      audits.value = await api.complianceAudits(hotelStore.hotelId, 30)
    } catch {
      audits.value = []
    }
  } catch (e: any) {
    toast(e?.message || t('加载合规状态失败'), false)
  } finally {
    loading.value = false
  }
}

async function doPurge() {
  if (!confirm(t('确认匿名化离店超留存年限的证件密文？掩码将保留。'))) return
  busy.value = true
  try {
    const r = await api.compliancePurgeIdDocs()
    toast(`已匿名化 ${r.purged} 条证件密文`)
    await load()
  } catch (e: any) {
    toast(e?.message || t('执行失败'), false)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page compliance">
    <div class="page-head">
      <h1>{{ t('数据合规中心') }}</h1>
      <p>{{ t('敏感字段加密 · 酒店本地密钥 · 揭密审计 · 留存匿名化') }}</p>
    </div>

    <p v-if="loading" class="muted">{{ t('加载中…') }}</p>
    <template v-else-if="status">
      <div class="card">
        <div class="sec-title">{{ t('合规清单') }}</div>
        <ul class="checklist">
          <li v-for="c in status.checklist" :key="c.id" :class="{ ok: c.ok }">
            <span class="dot" />
            {{ c.text }}
          </li>
        </ul>
      </div>

      <div class="grid2">
        <div class="card">
          <div class="sec-title">{{ t('密钥与算法') }}</div>
          <div class="kv">
            <div>
              <span>{{ t('算法') }}</span
              ><b>{{ status.key?.algorithm?.toUpperCase() }}</b>
            </div>
            <div>
              <span>{{ t('酒店密钥文件') }}</span
              ><b class="mono">{{ status.key?.hotel_key_file }}</b>
            </div>
            <div>
              <span>{{ t('密钥已就绪') }}</span>
              <b>{{
                status.key?.hotel_key_exists || status.key?.env_key_configured ? t('是') : t('否')
              }}</b>
            </div>
            <div>
              <span>{{ t('厂商持有密钥') }}</span
              ><b>{{ t('否') }}</b>
            </div>
            <div>
              <span>{{ t('当前角色') }}</span
              ><b>{{ status.current_role || '—' }}</b>
            </div>
            <div>
              <span>{{ t('可揭密证件') }}</span
              ><b>{{ status.can_reveal ? t('是') : t('否（需管理员）') }}</b>
            </div>
          </div>
          <p class="hint">{{ status.key?.note }}</p>
        </div>
      </div>

      <div class="card">
        <div class="sec-title row">
          <span>{{ t('留存与匿名化') }}</span>
          <button class="btn btn-ghost" type="button" :disabled="busy" @click="doPurge">
            {{ t('立即匿名化到期证件') }}
          </button>
        </div>
        <div class="kv">
          <div>
            <span>{{ t('离店后证件密文留存') }}</span>
            <b>{{ status.id_doc_retain_years }} {{ t('年') }}</b>
          </div>
          <div>
            <span>{{ t('当前含密文入住') }}</span
            ><b>{{ status.checkins_with_cipher }}</b>
          </div>
          <div>
            <span>{{ t('审计条数') }}</span
            ><b
              >{{ status.audit_count }}（{{ t('不可删，') }}≥{{ status.audit_min_retain_months }}
              {{ t('个月）') }}</b
            >
          </div>
          <div>
            <span>{{ t('人像落地') }}</span
            ><b>{{ t('否（仅上报公安旅业）') }}</b>
          </div>
          <div>
            <span>{{ t('证件落点') }}</span
            ><b>{{ t('仅 pms_checkins（预订单不存）') }}</b>
          </div>
          <div>
            <span>{{ t('导出策略') }}</span
            ><b>{{ t('默认脱敏，拒绝明文一键导出') }}</b>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="sec-title">{{ t('近期证件揭密审计') }}</div>
        <div v-if="!audits.length" class="muted">{{ t('暂无记录或当前账号无权限查看') }}</div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>{{ t('时间') }}</th>
              <th>{{ t('操作人') }}</th>
              <th>{{ t('动作') }}</th>
              <th>{{ t('入住/订单') }}</th>
              <th>{{ t('原因') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in audits" :key="a.id">
              <td class="mono">{{ a.created_at || '—' }}</td>
              <td>{{ a.operator || '—' }}</td>
              <td>{{ a.action }}</td>
              <td class="mono">{{ a.checkin_id || '—' }} / {{ a.order_id || '—' }}</td>
              <td>{{ a.reason || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.compliance .page-head h1 {
  margin: 0 0 4px;
  font-size: 1.45rem;
}
.compliance .page-head p {
  margin: 0 0 1rem;
  color: #79747e;
  font-size: 0.9rem;
}
.card {
  background: #fff;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
.sec-title {
  font-weight: 700;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
}
.sec-title.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.checklist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}
.checklist li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
  color: #49454f;
}
.checklist .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cac4d0;
  flex-shrink: 0;
}
.checklist li.ok .dot {
  background: #1e8e3e;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 900px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
.kv {
  display: grid;
  gap: 0.55rem;
}
.kv > div {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 0.5rem;
  font-size: 0.86rem;
}
.kv span {
  color: #79747e;
}
.kv b {
  font-weight: 600;
  word-break: break-all;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8rem;
}
.hint {
  margin: 0.75rem 0 0;
  font-size: 0.78rem;
  color: #79747e;
  line-height: 1.45;
}
.muted {
  color: #9aa1ad;
  font-size: 0.88rem;
}
.bak-list {
  list-style: none;
  margin: 0.75rem 0 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}
.bak-list li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.8rem;
}
.bak-list em {
  color: #79747e;
  font-style: normal;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.table th,
.table td {
  text-align: left;
  padding: 0.45rem 0.35rem;
  border-bottom: 1px solid #f0ebf4;
}
.table th {
  color: #79747e;
  font-weight: 600;
}
.btn {
  border: none;
  border-radius: 8px;
  padding: 0.45rem 0.9rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-primary {
  background: #005bbf;
  color: #fff;
}
.btn-ghost {
  background: #f1f3f5;
  color: #1c1b1f;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
