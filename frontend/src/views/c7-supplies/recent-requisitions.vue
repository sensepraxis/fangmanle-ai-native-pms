<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 易耗品领用与盘点
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
import SuppliesFocusBar from '../../components/SuppliesFocusBar.vue'

const route = useRoute()
const stocks = ref<any[]>([])
const requisitions = ref<any[]>([])
const auditItems = ref<any[]>([])
const auditNote = ref('')
const focusSummary = ref('')

const focusReqId = computed(() => Number(route.query.requisition_id || route.query.focus_id || 0))
const focusSupply = computed(() => String(route.query.supply || ''))
const focusRoom = computed(() => String(route.query.room || ''))

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'amenity')
    const kpi = board?.category_kpi || []
    if (kpi.length) {
      stocks.value = kpi.slice(0, 3).map((c: any) => {
        const danger = Number(c.low || 0) > 0
        const pct = danger ? Math.max(10, 40 - Number(c.low) * 5) : 70
        return {
          title: c.name,
          sub: `${c.sku} 个 SKU`,
          value: Number(c.stock || 0).toLocaleString('zh-CN'),
          unit: t('件'),
          pct,
          color: danger ? 'var(--error)' : 'var(--primary)t(',
          note: danger ? `${c.low} 项低于安全库存` : '储备充足 · 正常消耗速率',
          danger,
        }
      })
    } else {
      stocks.value = []
    }

    let reqs = board?.requisitions || []
    const rid = focusReqId.value
    const supply = focusSupply.value
    const room = focusRoom.value
    if (rid) {
      const hit = reqs.find((r: any) => Number(r.id) === rid)
      if (hit) {
        reqs = [hit, ...reqs.filter((r: any) => Number(r.id) !== rid)]
        focusSummary.value = `领用单 #${hit.id} · ${hit.supply_name} x${hit.qty}（${hit.requester || hit.dept || ''}）`
      }
    } else if (supply || room) {
      const matched = reqs.filter((r: any) => {
        const okSupply = supply ? String(r.supply_name || '').includes(supply) : true
        const okRoom = room
          ? String(r.dept || '').includes(room) || String(r.note || '').includes(room)
          : true
        return okSupply && okRoom
      })
      if (matched.length) {
        reqs = [...matched, ...reqs.filter((r: any) => !matched.includes(r))]
        focusSummary.value = `已按告警筛选领用：${[room, supply].filter(Boolean).join(' · ')}`
      }
    } else {
      focusSummary.value = ''
    }

    if (reqs.length) {
      requisitions.value = reqs.map((r: any) => {
        const who = r.requester || t('申请人')
        const pending = r.status !== 'issued' && r.status !== 'returned'
        return {
          id: r.id,
          no: `RQ-${r.id}`,
          who,
          role: r.dept || '',
          avatar: who[0] || t('申'),
          items: r.supply_name || t('物资'),
          qty: Number(r.qty || 0),
          status:
            r.status === 'issued'
              ? t('已通过')
              : r.status === 'returned'
                ? t('已退回')
                : t('待审批'),
          cls: pending ? 'amber' : 'green',
          highlight: rid > 0 && Number(r.id) === rid,
        }
      })
    } else {
      requisitions.value = []
    }

    const low = (board?.supplies || []).filter((s: any) => s.low).slice(0, 4)
    if (low.length) {
      const base = new Date()
      auditItems.value = low.map((s: any, i: number) => {
        const d = new Date(base)
        // 与原型一致：按缺口紧急程度给出「AI 建议补货日」
        const days = Math.max(
          1,
          Math.min(
            21,
            Math.ceil((Number(s.gap || 1) / Math.max(1, Number(s.safety_stock || 1))) * 14) + i * 3,
          ),
        )
        d.setDate(d.getDate() + days)
        const restockDate = `${d.getMonth() + 1}月${String(d.getDate()).padStart(2, '0')}日`
        return {
          name: s.name,
          book: Number(s.safety_stock || 0),
          real: Number(s.current_stock || 0),
          restockDate,
          danger: true,
        }
      })
      auditNote.value = `系统发现 ${low.length} 项库存低于安全线，请优先核对领用与补货。`
    } else {
      auditItems.value = []
      auditNote.value = ''
    }
  } catch {
    stocks.value = []
    requisitions.value = []
    auditItems.value = []
    auditNote.value = ''
  }
}
onMounted(load)
watch(
  () => [
    hotelStore.hotelId,
    route.query.requisition_id,
    route.query.focus_id,
    route.query.supply,
    route.query.room,
  ],
  load,
)
</script>

<template>
  <div class="page">
    <SuppliesFocusBar :summary="focusSummary" />
    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 24px;
      "
    >
      <div>
        <h1 style="font-size: 24px; font-weight: 700; color: var(--on-surface); margin: 0 0 4px">
          {{ t('易耗品领用与盘点') }}
        </h1>
        <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
          {{ t('易耗品与库存管理') }}
        </p>
      </div>
      <div style="display: flex; gap: 12px">
        <button class="btn btn-ghost">{{ t('导出报表') }}</button>
        <button class="btn btn-primary">{{ t('新建领用单') }}</button>
      </div>
    </div>

    <!-- 顶部 3 卡 -->
    <p v-if="!stocks.length" class="empty-hint" style="margin-bottom: 16px">{{ SUPPLIES_EMPTY }}</p>
    <div
      v-else
      style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px"
    >
      <div
        v-for="(s, i) in stocks"
        :key="i"
        class="card-clean"
        style="padding: 24px; position: relative; overflow: hidden"
      >
        <div
          :style="{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '4px',
            height: '100%',
            background: s.danger
              ? 'var(--tertiary)'
              : s.color === 'var(--error)'
                ? 'var(--error)'
                : 'transparent',
          }"
        ></div>
        <div
          style="
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
          "
        >
          <div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0">
              {{ s.title }}
            </h3>
            <p style="font-size: 12px; color: var(--on-surface-variant); margin: 4px 0 0">
              {{ s.sub }}
            </p>
          </div>
          <div
            :style="{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: s.danger ? 'var(--tertiary-container)' : 'var(--surface-container-high)',
              color: s.danger ? 'var(--on-tertiary-container)' : 'var(--on-surface-variant)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }"
          ></div>
        </div>
        <div style="display: flex; align-items: flex-end; gap: 8px; margin-bottom: 8px">
          <span
            :style="{
              fontSize: '32px',
              fontWeight: 700,
              color: s.danger ? 'var(--error)' : 'var(--on-surface)',
              lineHeight: 1,
              fontFamily: 'Roboto Mono, monospace',
            }"
            >{{ s.value }}</span
          >
          <span
            :style="{
              fontSize: '13px',
              color: s.danger ? 'var(--error)' : 'var(--on-surface-variant)',
              marginBottom: '4px',
            }"
            >{{ s.unit }}</span
          >
        </div>
        <div
          style="
            width: 100%;
            background: var(--surface-container-highest);
            border-radius: 999px;
            height: 8px;
            margin-bottom: 8px;
          "
        >
          <div
            :style="{
              width: s.pct + '%',
              background: s.color,
              height: '8px',
              borderRadius: '999px',
            }"
          ></div>
        </div>
        <p
          :style="{
            fontSize: '12px',
            color: s.danger ? 'var(--error)' : 'var(--on-surface-variant)',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }"
        >
          {{ s.note }}
        </p>
      </div>
    </div>

    <!-- 中部：领用记录 (8) + 盘点 AI (4) -->
    <div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px">
      <!-- 近期领用记录 -->
      <div
        class="card-clean"
        style="grid-column: span 8; overflow: hidden; display: flex; flex-direction: column"
      >
        <div
          style="
            padding: 20px 24px;
            border-bottom: 1px solid var(--outline-variant);
            display: flex;
            justify-content: space-between;
            align-items: center;
          "
        >
          <h2 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0">
            {{ t('近期领用记录') }}
          </h2>
          <button class="link">{{ t('查看全部') }}</button>
        </div>
        <div style="overflow-x: auto">
          <table class="data">
            <thead>
              <tr>
                <th>{{ t('单号') }}</th>
                <th>{{ t('申请人') }}</th>
                <th>{{ t('物品细项') }}</th>
                <th class="num">{{ t('数量') }}</th>
                <th>{{ t('状态') }}</th>
                <th class="center">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!requisitions.length">
                <td colspan="6" class="empty-hint">{{ SUPPLIES_EMPTY }}</td>
              </tr>
              <tr
                v-for="(r, i) in requisitions"
                :key="i"
                :style="
                  r.highlight
                    ? {
                        background: 'rgba(37,99,235,0.08)',
                        outline: '2px solid rgba(37,99,235,0.35)',
                      }
                    : undefined
                "
              >
                <td class="num">{{ r.no }}</td>
                <td>
                  <div style="display: flex; align-items: center; gap: 8px">
                    <div
                      style="
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        background: var(--secondary-container);
                        color: var(--on-secondary-container);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 11px;
                      "
                    >
                      {{ r.avatar }}
                    </div>
                    <span>{{ r.who }} ({{ r.role }})</span>
                  </div>
                </td>
                <td style="color: var(--on-surface)">{{ r.items }}</td>
                <td class="num">{{ r.qty }}</td>
                <td>
                  <span
                    v-if="r.cls === 'amber'"
                    style="
                      background: #fef3c7;
                      color: #b45309;
                      font-size: 12px;
                      padding: 2px 8px;
                      border-radius: 6px;
                      border: 1px solid #fde68a;
                      display: inline-flex;
                      align-items: center;
                    "
                    >{{ r.status }}</span
                  >
                  <span
                    v-else
                    style="
                      background: #d1fae5;
                      color: #047857;
                      font-size: 12px;
                      padding: 2px 8px;
                      border-radius: 6px;
                      border: 1px solid #a7f3d0;
                      display: inline-flex;
                      align-items: center;
                    "
                    >{{ r.status }}</span
                  >
                </td>
                <td class="center">
                  <button class="link">{{ r.cls === 'amber' ? t('审批') : t('详情') }}</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 库存盘点 AI -->
      <div
        class="card-clean"
        style="
          grid-column: span 4;
          padding: 24px;
          position: relative;
          overflow: hidden;
          border: 1px solid rgba(140, 51, 179, 0.3);
        "
      >
        <div
          style="
            position: absolute;
            top: -40px;
            right: -40px;
            width: 128px;
            height: 128px;
            background: var(--tertiary);
            border-radius: 50%;
            filter: blur(60px);
            opacity: 0.2;
            pointer-events: none;
          "
        ></div>
        <h2 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0 0 16px">
          {{ t('库存盘点') }}
        </h2>
        <div
          style="
            background: var(--surface-container);
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 16px;
          "
          v-if="auditNote"
        >
          <h4 style="font-size: 13px; font-weight: 700; color: var(--on-surface); margin: 0 0 4px">
            {{ t('系统发现库存差异') }}
          </h4>
          <p style="font-size: 12px; color: var(--on-surface-variant); margin: 0">
            {{ auditNote }}
          </p>
        </div>
        <h3
          style="
            font-size: 12px;
            color: var(--on-surface-variant);
            font-weight: 500;
            border-bottom: 1px solid var(--outline-variant);
            padding-bottom: 8px;
            margin: 0 0 12px;
          "
        >
          {{ t('需重点复核项') }}
        </h3>
        <p v-if="!auditItems.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
        <div v-else style="display: flex; flex-direction: column; gap: 12px">
          <div
            v-for="(a, i) in auditItems"
            :key="i"
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              background: var(--surface);
              padding: 12px;
              border-radius: 8px;
              border: 1px solid rgba(193, 198, 214, 0.5);
            "
          >
            <div style="display: flex; align-items: center; gap: 12px">
              <div
                :style="{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: a.danger ? 'var(--error-container)' : 'var(--surface-container-high)',
                  color: a.danger ? 'var(--error)' : 'var(--on-surface-variant)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }"
              ></div>
              <div>
                <p style="font-size: 13px; font-weight: 500; color: var(--on-surface); margin: 0">
                  {{ a.name }}
                </p>
                <p style="font-size: 11px; color: var(--on-surface-variant); margin: 2px 0 0">
                  安全线: {{ a.book }} | 实盘:
                  <span
                    :style="{
                      color: a.danger ? 'var(--error)' : 'var(--on-surface)',
                      fontWeight: 500,
                    }"
                    >{{ a.real }}</span
                  >
                </p>
              </div>
            </div>
            <div style="text-align: right">
              <span
                style="font-size: 11px; color: var(--tertiary); display: block; margin-bottom: 2px"
                >{{ t('AI 建议补货日') }}</span
              >
              <span
                style="
                  font:
                    500 13px 'Roboto Mono',
                    monospace;
                  color: var(--on-surface);
                  display: block;
                "
                >{{ a.restockDate }}</span
              >
            </div>
          </div>
        </div>
        <button type="button" class="btn btn-audit">{{ t('发起全盘审核') }}</button>
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
.btn-audit {
  width: 100%;
  justify-content: center;
  margin-top: 16px;
  background: var(--tertiary-container);
  color: #ffffff;
  border: none;
}
.btn-audit:hover {
  background: var(--tertiary);
  color: #ffffff;
}
</style>
