<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 报损登记 —— 设备设施报废流程
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
const router = useRouter()

const cost = ref({ total: '¥0.00', pending: '¥0.00', incurred: '¥0.00' })
const tracking = ref<any[]>([])
const insightText = ref('')
const resolving = ref<number | null>(null)

function goNewDamage() {
  router.push('/c8-assets/tracking')
}

const STATUS_UI: Record<string, { label: string; cls: string; action: string }> = {
  open: { label: t('待处理'), cls: 'amber', action: t('办结') },
  repairing: { label: t('维修中'), cls: 'amber', action: t('办结') },
  replaced: { label: t('已更换'), cls: 'green', action: t('已归档') },
  scrapped: { label: t('已报废'), cls: 'error', action: t('采购申请') },
  closed: { label: t('已关闭'), cls: 'green', action: t('已归档') },
}

function iconFor(name: string) {
  if (/壶|电/.test(name)) return 'coffee_maker'
  if (/椅|家具/.test(name)) return 'chair'
  if (/花洒|卫浴|漏/.test(name)) return 'shower'
  return 'build'
}

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId, 'amenity')
    const fee = board?.damage_cost || {}
    cost.value = {
      total: `¥${Number(fee.total || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      pending: `¥${Number(fee.pending || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      incurred: `¥${Number(fee.incurred || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    }

    const damages = board?.damages || []
    if (damages.length) {
      tracking.value = damages.map((d: any) => {
        const ui = STATUS_UI[d.status] || STATUS_UI.open
        const canResolve = d.status === 'open' || d.status === 'repairing'
        return {
          id: d.id,
          room: d.room_no || '-',
          item: d.item_name || t('损坏物品'),
          icon: iconFor(d.item_name || ''),
          status: ui.label,
          cls: ui.cls,
          fee: `¥ ${Number(d.fee || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`,
          time: d.created_at ? String(d.created_at).replace('T', ' ').slice(0, 16) : '',
          action: ui.action,
          canResolve,
        }
      })
    } else {
      tracking.value = []
    }

    const ins =
      (board?.insights || []).find((x: any) => x.category === 'loss' || x.category === 'rca') ||
      board?.insights?.[0]
    if (ins) insightText.value = `${ins.title}：${ins.recommendation}`
    else insightText.value = SUPPLIES_EMPTY
  } catch {
    tracking.value = []
    insightText.value = SUPPLIES_EMPTY
  }
}

async function onAction(row: any) {
  if (row.action === t('采购申请')) {
    router.push('/c8-assets/inventory-2?action=register')
    return
  }
  if (row.action === t('已归档')) {
    return
  }
  if (!row.canResolve || !row.id || resolving.value) return
  resolving.value = row.id
  try {
    await api.resolveDamage(row.id)
    await load()
  } catch {
    /* keep */
  } finally {
    resolving.value = null
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 20px;
      "
    >
      <div>
        <button type="button" class="back" @click="router.push('/c8-assets/inventory-2')">
          {{ t('← 工作台') }}
        </button>
        <h1 style="font-size: 24px; font-weight: 700; color: var(--on-surface); margin: 0 0 4px">
          {{ t('物资报废登记') }}
        </h1>
        <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
          {{ t('登记设备 / 固定资产报废；客用品与布草报损亦可在此统一处理。') }}
        </p>
      </div>
      <div style="display: flex; gap: 12px">
        <button type="button" class="btn btn-primary" @click="goNewDamage">
          <span class="material-symbols-outlined" style="font-size: 14px">add</span>
          {{ t('新建报损单') }}
        </button>
      </div>
    </div>

    <!-- AI 维修洞察 -->
    <div
      class="ai-card"
      style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 16px"
    >
      <div
        style="
          background: var(--tertiary-container);
          color: var(--on-tertiary-container);
          padding: 8px;
          border-radius: 50%;
          margin-top: 4px;
        "
      >
        <span class="material-symbols-outlined" style="font-size: 16px">auto_awesome</span>
      </div>
      <div>
        <h3 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0 0 4px">
          {{ t('AI 维修洞察') }}
        </h3>
        <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
          {{ insightText }}
        </p>
      </div>
    </div>

    <div
      style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; align-items: start"
    >
      <!-- 快速登记表单 (span 5) -->
      <div
        class="card-clean"
        style="grid-column: span 5; padding: 24px; display: flex; flex-direction: column"
      >
        <h2
          style="
            font-size: 16px;
            font-weight: 600;
            color: var(--on-surface);
            margin: 0 0 20px;
            display: flex;
            align-items: center;
            gap: 8px;
          "
        >
          <span class="material-symbols-outlined" style="color: var(--primary)">edit_document</span>
          {{ t('快速登记') }}
        </h2>
        <form style="display: flex; flex-direction: column; gap: 16px; flex: 1">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px">
            <div>
              <label
                style="
                  display: block;
                  font-size: 12px;
                  color: var(--on-surface-variant);
                  margin-bottom: 4px;
                "
                >{{ t('房号') }}</label
              >
              <input
                class="toolbar-input"
                style="width: 100%"
                :placeholder="t('例如: 302')"
                type="text"
              />
            </div>
            <div>
              <label
                style="
                  display: block;
                  font-size: 12px;
                  color: var(--on-surface-variant);
                  margin-bottom: 4px;
                "
                >{{ t('物品类别') }}</label
              >
              <select class="toolbar-input" style="width: 100%; appearance: none; cursor: pointer">
                <option>{{ t('电器设备') }}</option>
                <option>{{ t('布草') }}</option>
                <option>{{ t('家具') }}</option>
                <option>{{ t('卫浴五金') }}</option>
              </select>
            </div>
          </div>
          <div>
            <label
              style="
                display: block;
                font-size: 12px;
                color: var(--on-surface-variant);
                margin-bottom: 4px;
              "
              >{{ t('损坏详情') }}</label
            >
            <textarea
              class="toolbar-input"
              style="width: 100%; height: 96px; resize: none"
              :placeholder="t('描述具体损坏情况...')"
            ></textarea>
          </div>
          <div>
            <label
              style="
                display: block;
                font-size: 12px;
                color: var(--on-surface-variant);
                margin-bottom: 4px;
              "
              >{{ t('现场照片') }}</label
            >
            <div
              style="
                border: 2px dashed var(--outline-variant);
                border-radius: 8px;
                padding: 24px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: var(--surface-container-low);
                cursor: pointer;
              "
            >
              <span
                class="material-symbols-outlined"
                style="font-size: 28px; color: var(--outline); margin-bottom: 8px"
                >add_a_photo</span
              >
              <span style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('点击或拖拽上传照片')
              }}</span>
              <span style="font-size: 11px; color: var(--outline); margin-top: 4px">{{
                t('支持 JPG, PNG')
              }}</span>
            </div>
          </div>
          <div
            style="
              margin-top: auto;
              padding-top: 16px;
              display: flex;
              justify-content: flex-end;
              gap: 12px;
            "
          >
            <button class="btn btn-ghost" type="button">{{ t('取消') }}</button>
            <button class="btn btn-primary" type="button">{{ t('提交报损') }}</button>
          </div>
        </form>
      </div>

      <!-- 成本 & 进度 (span 7) -->
      <div style="grid-column: span 7; display: flex; flex-direction: column; gap: 16px">
        <!-- 成本 widget -->
        <div
          class="card-clean"
          style="padding: 24px; display: flex; align-items: center; justify-content: space-between"
        >
          <div>
            <h3 style="font-size: 12px; color: var(--on-surface-variant); margin: 0 0 4px">
              {{ t('本月预估维修总成本') }}
            </h3>
            <div
              style="
                font-size: 32px;
                font-weight: 700;
                color: var(--on-surface);
                font-family: 'Roboto Mono', monospace;
                display: flex;
                align-items: baseline;
                gap: 4px;
              "
            >
              <span style="font-size: 18px; color: var(--on-surface-variant)">¥</span
              >{{ cost.total.replace('¥', '') }}
            </div>
          </div>
          <div style="display: flex; gap: 16px">
            <div style="text-align: right">
              <div style="font-size: 12px; color: var(--outline); margin-bottom: 4px">
                {{ t('待审批') }}
              </div>
              <div style="font-size: 16px; font-weight: 500; color: var(--error)">
                {{ cost.pending }}
              </div>
            </div>
            <div style="width: 1px; height: 48px; background: var(--outline-variant)"></div>
            <div style="text-align: right">
              <div style="font-size: 12px; color: var(--outline); margin-bottom: 4px">
                {{ t('已产生') }}
              </div>
              <div style="font-size: 16px; font-weight: 500; color: var(--on-surface)">
                {{ cost.incurred }}
              </div>
            </div>
          </div>
        </div>

        <!-- 进度追踪表 -->
        <div
          class="card-clean"
          style="overflow: hidden; display: flex; flex-direction: column; flex: 1"
        >
          <div
            style="
              padding: 16px;
              border-bottom: 1px solid var(--outline-variant);
              display: flex;
              justify-content: space-between;
              align-items: center;
              background: var(--surface-lowest);
            "
          >
            <h2 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0">
              {{ t('处理进度追踪') }}
            </h2>
            <button class="icon-btn" style="width: 32px; height: 32px">
              <span class="material-symbols-outlined" style="font-size: 16px">filter_list</span>
            </button>
          </div>
          <div style="overflow-x: auto; flex: 1">
            <table class="data">
              <thead>
                <tr>
                  <th>{{ t('房号') }}</th>
                  <th>{{ t('损坏物品') }}</th>
                  <th>{{ t('状态') }}</th>
                  <th class="num">{{ t('预估费用') }}</th>
                  <th>{{ t('上报时间') }}</th>
                  <th class="center">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!tracking.length">
                  <td colspan="6" class="empty-hint">{{ SUPPLIES_EMPTY }}</td>
                </tr>
                <tr v-for="(item, i) in tracking" :key="i">
                  <td class="num" style="font-weight: 500">{{ item.room }}</td>
                  <td>
                    <div style="display: flex; align-items: center; gap: 8px">
                      <span
                        class="material-symbols-outlined"
                        style="font-size: 16px; color: var(--outline)"
                        >{{ item.icon }}</span
                      >{{ item.item }}
                    </div>
                  </td>
                  <td>
                    <span
                      v-if="item.cls === 'amber'"
                      style="
                        background: #fff8e1;
                        color: #f57f17;
                        border: 1px solid #ffe082;
                        font-size: 11px;
                        padding: 2px 10px;
                        border-radius: 999px;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                      "
                      ><span
                        style="
                          width: 6px;
                          height: 6px;
                          border-radius: 50%;
                          background: #f57f17;
                          display: inline-block;
                        "
                      ></span
                      >{{ item.status }}</span
                    >
                    <span
                      v-else-if="item.cls === 'error'"
                      style="
                        background: var(--error-container);
                        color: var(--on-error-container);
                        border: 1px solid #ffb4ab;
                        font-size: 11px;
                        padding: 2px 10px;
                        border-radius: 999px;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                      "
                      ><span
                        style="
                          width: 6px;
                          height: 6px;
                          border-radius: 50%;
                          background: var(--error);
                          display: inline-block;
                        "
                      ></span
                      >{{ item.status }}</span
                    >
                    <span
                      v-else
                      style="
                        background: #e8f5e9;
                        color: #2e7d32;
                        border: 1px solid #a5d6a7;
                        font-size: 11px;
                        padding: 2px 10px;
                        border-radius: 999px;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                      "
                      ><span
                        style="
                          width: 6px;
                          height: 6px;
                          border-radius: 50%;
                          background: #2e7d32;
                          display: inline-block;
                        "
                      ></span
                      >{{ item.status }}</span
                    >
                  </td>
                  <td class="num">{{ item.fee }}</td>
                  <td
                    style="
                      color: var(--on-surface-variant);
                      font:
                        500 12px 'Roboto Mono',
                        monospace;
                    "
                  >
                    {{ item.time }}
                  </td>
                  <td class="center">
                    <button
                      class="link"
                      type="button"
                      :disabled="item.canResolve && resolving === item.id"
                      @click="onAction(item)"
                    >
                      {{ item.canResolve && resolving === item.id ? t('处理中…') : item.action }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.back {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  margin-bottom: 6px;
  display: block;
}
.empty-hint {
  margin: 0;
  padding: 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
</style>
