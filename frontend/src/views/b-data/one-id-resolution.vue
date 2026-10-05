<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 归并审核 —— 对比两份数据库档案并执行 OneID 合并
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import OneIdFlowSubnav from '../../components/OneIdFlowSubnav.vue'

const VIP_RANK: Record<string, number> = {
  diamond: 4,
  platinum: 3,
  gold: 2,
  silver: 1,
  normal: 0,
}

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const err = ref('')
const mergeCase = ref<any>(null)
const primaryId = ref<number | null>(null)
const secondaryId = ref<number | null>(null)
const merging = ref(false)

const primary = computed(
  () => (mergeCase.value?.guests || []).find((g: any) => g.guest_id === primaryId.value) || null,
)
const secondary = computed(
  () => (mergeCase.value?.guests || []).find((g: any) => g.guest_id === secondaryId.value) || null,
)
const canMerge = computed(() =>
  Boolean(primaryId.value && secondaryId.value && primary.value && secondary.value),
)

const mergedPreview = computed(() => {
  const p = primary.value
  const s = secondary.value
  if (!p || !s) return null

  const orders = [
    ...(p.orders || []).map((o: any) => ({ ...o, from_guest_id: p.guest_id, from_name: p.name })),
    ...(s.orders || []).map((o: any) => ({ ...o, from_guest_id: s.guest_id, from_name: s.name })),
  ].sort((a, b) => String(b.check_in || '').localeCompare(String(a.check_in || '')))

  const couponMap = new Map<string, any>()
  for (const c of [...(p.coupons || []), ...(s.coupons || [])]) {
    if (c?.code) couponMap.set(c.code, c)
  }
  const coupons = Array.from(couponMap.values())

  const identMap = new Map<string, any>()
  for (const i of [...(p.identities || []), ...(s.identities || [])]) {
    identMap.set(`${i.source}:${i.external_id}`, i)
  }
  const identities = Array.from(identMap.values())

  const pRank = VIP_RANK[(p.vip_level || 'normal').toLowerCase()] ?? 0
  const sRank = VIP_RANK[(s.vip_level || 'normal').toLowerCase()] ?? 0
  const keepHigherVip = sRank > pRank

  const primaryAliases = [...(p.alias_names || [])]
  const secondaryAliases = [...(s.alias_names || [])]
  const mergedAliasSet = new Set<string>([...primaryAliases, ...secondaryAliases])
  if (s.name && s.name !== p.name) mergedAliasSet.add(s.name)
  mergedAliasSet.delete(p.name)
  const mergedAliasNames = Array.from(mergedAliasSet)

  return {
    name: p.name,
    one_id: p.one_id,
    phone: p.phone,
    phone_mask: p.phone_mask || p.phone,
    city: p.city || s.city || '—',
    vip_label: keepHigherVip ? s.vip_label : p.vip_label,
    vip_note: keepHigherVip
      ? t('取较高等级（原次档 {label}）', { label: s.vip_label })
      : t('保留主档 {label}', { label: p.vip_label }),
    ltv: Number(p.ltv || 0) + Number(s.ltv || 0),
    order_count: Number(p.order_count || 0) + Number(s.order_count || 0),
    coupon_count: coupons.length,
    active_coupon_count: coupons.filter(
      (c) => c.status === 'active' && c.redeem_status !== 'redeemed',
    ).length,
    orders,
    coupons,
    identities,
    alias_names: mergedAliasNames,
    primary_alias_names: primaryAliases,
    secondary_alias_to_add: s.name && s.name !== p.name ? s.name : null,
    absorbed: {
      guest_id: s.guest_id,
      name: s.name,
      one_id: s.one_id,
    },
  }
})

onMounted(async () => {
  loading.value = true
  try {
    const conflictId =
      Number(route.query.conflictId || sessionStorage.getItem('fml_merge_conflict') || 0) ||
      undefined
    const c = await api.oneidMergeCase(conflictId)
    mergeCase.value = c
    const qPrimary = Number(route.query.primary || sessionStorage.getItem('fml_merge_primary') || 0)
    const qSecondary = Number(
      route.query.secondary || sessionStorage.getItem('fml_merge_secondary') || 0,
    )
    primaryId.value = qPrimary || c.suggested_primary_id || c.guests?.[0]?.guest_id || null
    const ids = (c.guests || []).map((g: any) => g.guest_id)
    secondaryId.value =
      qSecondary ||
      ids.find((id: number) => id !== primaryId.value) ||
      c.guests?.[1]?.guest_id ||
      null
  } catch (e: any) {
    err.value = t(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function swap() {
  const a = primaryId.value
  primaryId.value = secondaryId.value
  secondaryId.value = a
}

async function confirmMerge() {
  if (merging.value || !primaryId.value || !secondaryId.value) return
  merging.value = true
  try {
    const res = await api.mergeOneid(primaryId.value, secondaryId.value)
    const merged = res?.merged_into ?? res?.guest?.id ?? primaryId.value
    sessionStorage.setItem('fml_merged_guest_id', String(merged))
    router.push({
      path: '/b-data/consolidated-asset-confirmation',
      query: { guestId: String(merged) },
    })
  } catch (e: any) {
    alert(t(e?.message || '合并失败'))
  } finally {
    merging.value = false
  }
}
</script>

<template>
  <div class="page">
    <OneIdFlowSubnav
      :on-next="confirmMerge"
      :next-disabled="!canMerge"
      :next-loading="merging"
      :next-label="t('确认合并 → 资产确认')"
    />

    <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold m-0 mb-2">{{ t('身份归并审核') }}</h1>
        <p class="text-sm text-on-surface-variant m-0">
          {{
            t(
              '对比两份同号档案（数据库），确认后将次档合并入主档。订单原始归属不变，360 统一展示；渠道身份与别名迁入主档。',
            )
          }}
        </p>
      </div>
      <button type="button" class="swap-btn" :disabled="!primary || !secondary" @click="swap">
        <span class="material-symbols-outlined">swap_horiz</span>
        {{ t('交换主/次档') }}
      </button>
    </div>

    <div v-if="loading" class="text-sm text-on-surface-variant py-8">{{ t('加载中…') }}</div>
    <div
      v-else-if="err"
      class="rounded-xl border border-red-200 bg-red-50 text-red-800 p-4 text-sm"
    >
      {{ err }}
    </div>
    <template v-else-if="primary && secondary && mergedPreview">
      <div class="hint-bar">
        <span class="material-symbols-outlined">info</span>
        {{ t('手机') }} {{ mergeCase?.phone_mask }} · {{ t('建议主档') }}
        <strong>{{
          (mergeCase?.guests || []).find((g: any) => g.guest_id === mergeCase?.suggested_primary_id)
            ?.name || '—'
        }}</strong>
        {{ t('（LTV 更高）') }}
      </div>

      <div class="compare-table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th>{{ t('维度') }}</th>
              <th class="col-primary">{{ t('主档案（保留）') }}#{{ primary.guest_id }}</th>
              <th class="col-secondary">{{ t('次档案（并入）') }}#{{ secondary.guest_id }}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ t('姓名') }}</td>
              <td class="col-primary">{{ primary.name }}</td>
              <td>{{ secondary.name }}</td>
            </tr>
            <tr>
              <td>{{ t('其他名字') }}</td>
              <td class="col-primary">
                <span v-if="(primary.alias_names || []).length" class="tag">{{
                  (primary.alias_names || []).join('、')
                }}</span>
                <span v-else class="text-on-surface-variant">—</span>
              </td>
              <td>
                <span v-if="secondary.name !== primary.name" class="tag tag-merge">{{
                  t('并入后写入：{name}', { name: secondary.name })
                }}</span>
                <span v-else-if="(secondary.alias_names || []).length">{{
                  (secondary.alias_names || []).join('、')
                }}</span>
                <span v-else class="text-on-surface-variant">—</span>
              </td>
            </tr>
            <tr>
              <td>{{ t('手机') }}</td>
              <td class="col-primary font-mono">{{ primary.phone }}</td>
              <td class="font-mono">{{ secondary.phone }}</td>
            </tr>
            <tr>
              <td>OneID</td>
              <td class="col-primary font-mono text-xs">{{ primary.one_id }}</td>
              <td class="font-mono text-xs">{{ secondary.one_id }}</td>
            </tr>
            <tr>
              <td>{{ t('会员') }}</td>
              <td class="col-primary">{{ t(primary.vip_label || '—') }}</td>
              <td>{{ t(secondary.vip_label || '—') }}</td>
            </tr>
            <tr>
              <td>LTV</td>
              <td class="col-primary font-bold">{{ money(primary.ltv) }}</td>
              <td>{{ money(secondary.ltv) }}</td>
            </tr>
            <tr>
              <td>{{ t('订单数') }}</td>
              <td class="col-primary">{{ primary.order_count }}</td>
              <td>{{ secondary.order_count }}</td>
            </tr>
            <tr>
              <td>{{ t('优惠券') }}</td>
              <td class="col-primary">{{ primary.coupon_count }}</td>
              <td>{{ secondary.coupon_count }}</td>
            </tr>
            <tr>
              <td>{{ t('渠道') }}</td>
              <td class="col-primary">
                <span
                  v-for="i in primary.identities || []"
                  :key="'p' + i.external_id"
                  class="tag"
                  >{{ t(i.source_cn || i.source || '') }}</span
                >
              </td>
              <td>
                <span
                  v-for="i in secondary.identities || []"
                  :key="'s' + i.external_id"
                  class="tag"
                  >{{ t(i.source_cn || i.source || '') }}</span
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <section class="preview">
        <div class="preview-head">
          <div>
            <div class="preview-kicker">{{ t('合并后预览') }}</div>
            <h2 class="preview-title">{{ mergedPreview.name }} · {{ mergedPreview.one_id }}</h2>
            <p class="preview-sub">
              {{ t('次档') }}
              <strong
                >#{{ mergedPreview.absorbed.guest_id }} {{ mergedPreview.absorbed.name }}</strong
              >
              {{ t('并入主档 · OneID 保留') }}
              <span class="font-mono">{{ mergedPreview.one_id }}</span>
            </p>
          </div>
          <div class="preview-badge">
            <span class="material-symbols-outlined">merge</span>
            {{ t('待确认合并') }}
          </div>
        </div>

        <div class="preview-stats">
          <div class="stat">
            <div class="stat-label">{{ t('主档姓名') }}</div>
            <div class="stat-value text-base">{{ mergedPreview.name }}</div>
            <div class="stat-hint">OneID {{ mergedPreview.one_id }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('其他名字') }}</div>
            <div class="stat-value text-base">
              {{ mergedPreview.alias_names.length ? mergedPreview.alias_names.join('、') : '—' }}
            </div>
            <div class="stat-hint">
              <span v-if="mergedPreview.secondary_alias_to_add">{{
                t('含次档 {name}', { name: mergedPreview.secondary_alias_to_add })
              }}</span>
              <span v-else>{{ t('无新增别名') }}</span>
            </div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('累计 LTV') }}</div>
            <div class="stat-value accent">{{ money(mergedPreview.ltv) }}</div>
            <div class="stat-hint">{{ money(primary.ltv) }} + {{ money(secondary.ltv) }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('会员等级') }}</div>
            <div class="stat-value">{{ t(mergedPreview.vip_label || '—') }}</div>
            <div class="stat-hint">{{ mergedPreview.vip_note }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('订单') }}</div>
            <div class="stat-value">{{ mergedPreview.order_count }} {{ t('笔') }}</div>
            <div class="stat-hint">
              {{ t('主') }} {{ primary.order_count }} + {{ t('次') }} {{ secondary.order_count }}
            </div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('优惠券') }}</div>
            <div class="stat-value">{{ mergedPreview.coupon_count }} {{ t('张') }}</div>
            <div class="stat-hint">
              {{ t('有效') }} {{ mergedPreview.active_coupon_count }} {{ t('张') }}
            </div>
          </div>
        </div>

        <div class="preview-grid">
          <article class="preview-panel">
            <header class="panel-head">
              <span class="material-symbols-outlined">receipt_long</span>
              <span>{{ t('合并后订单清单') }}</span>
              <span class="panel-count">{{ mergedPreview.orders.length }} {{ t('笔展示') }}</span>
            </header>
            <ul v-if="mergedPreview.orders.length" class="item-list">
              <li
                v-for="o in mergedPreview.orders"
                :key="`${o.id}-${o.from_guest_id}`"
                class="item-row"
              >
                <div class="item-main">
                  <div class="item-title">{{ o.order_no || t('订单 #{id}', { id: o.id }) }}</div>
                  <div class="item-meta">
                    {{ o.check_in }} → {{ o.check_out || '—' }} · {{ o.room_type || t('客房') }} ·
                    {{ o.nights || 1 }} {{ t('晚') }}
                  </div>
                </div>
                <div class="item-side">
                  <span
                    class="origin-tag"
                    :class="o.from_guest_id === primaryId ? 'primary' : 'secondary'"
                  >
                    {{ t('原') }} #{{ o.from_guest_id }}</span
                  >
                  <span class="item-amount">{{ money(o.total_amount) }}</span>
                  <span class="item-status">{{ t(o.status_cn || o.status || '—') }}</span>
                </div>
              </li>
            </ul>
            <p v-else class="empty">{{ t('暂无订单') }}</p>
          </article>

          <article class="preview-panel">
            <header class="panel-head">
              <span class="material-symbols-outlined">confirmation_number</span>
              <span>{{ t('合并后优惠券') }}</span>
              <span class="panel-count">{{ mergedPreview.coupons.length }} {{ t('张') }}</span>
            </header>
            <ul v-if="mergedPreview.coupons.length" class="item-list">
              <li v-for="c in mergedPreview.coupons" :key="c.code" class="item-row compact">
                <div class="item-main">
                  <div class="item-title font-mono">{{ c.code }}</div>
                  <div class="item-meta">
                    {{ c.name }} · {{ c.discount_label || c.discount_type || t('优惠券') }}
                  </div>
                </div>
                <div class="item-side">
                  <span class="item-status">{{
                    c.status === 'active' ? t('有效') : t(c.status_cn || c.status || '—')
                  }}</span>
                </div>
              </li>
            </ul>
            <p v-else class="empty">{{ t('暂无优惠券') }}</p>
          </article>

          <article class="preview-panel span-full">
            <header class="panel-head">
              <span class="material-symbols-outlined">hub</span>
              <span>{{ t('合并后渠道身份') }}</span>
              <span class="panel-count">{{ mergedPreview.identities.length }} {{ t('条') }}</span>
            </header>
            <div v-if="mergedPreview.identities.length" class="ident-grid">
              <div
                v-for="i in mergedPreview.identities"
                :key="i.source + i.external_id"
                class="ident-card"
              >
                <div class="ident-source">{{ t(i.source_cn || i.source || '') }}</div>
                <div class="ident-id font-mono">{{ i.external_id }}</div>
                <div class="ident-meta">
                  {{ t('置信度') }} {{ Math.round(Number(i.confidence || 0) * 100) }}%
                </div>
              </div>
            </div>
            <p v-else class="empty">{{ t('暂无渠道身份') }}</p>
          </article>
        </div>
      </section>
    </template>
    <div v-else class="text-sm text-on-surface-variant py-8">
      {{ t('未找到可对比的两份档案，请回到冲突队列。') }}
    </div>
  </div>
</template>

<style scoped>
.swap-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  color: var(--on-surface);
}
.swap-btn:hover:not(:disabled) {
  background: var(--surface-container-low);
}
.swap-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.swap-btn .material-symbols-outlined {
  font-size: 18px;
}

.hint-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 12px 14px;
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--primary) 25%, transparent);
  background: color-mix(in srgb, var(--primary) 6%, var(--surface-container-lowest));
  font-size: 13px;
}
.hint-bar .material-symbols-outlined {
  font-size: 18px;
  color: var(--primary);
}

.compare-table-wrap {
  overflow-x: auto;
  border-radius: 14px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  margin-bottom: 20px;
}
.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.compare-table th,
.compare-table td {
  padding: 12px 14px;
  text-align: left;
  border-top: 1px solid var(--outline-variant);
}
.compare-table thead th {
  border-top: none;
  background: var(--surface-container-low);
  font-weight: 700;
  color: var(--on-surface-variant);
}
.compare-table td:first-child {
  width: 88px;
  color: var(--on-surface-variant);
  font-weight: 600;
}
.col-primary {
  color: var(--primary);
  font-weight: 650;
}
.col-secondary {
  color: var(--on-surface-variant);
}
.tag {
  display: inline-block;
  margin: 0 4px 4px 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-container);
  font-size: 11px;
}
.tag-merge {
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}

.preview {
  border-radius: 16px;
  border: 1px solid var(--outline-variant);
  background: linear-gradient(
    165deg,
    color-mix(in srgb, var(--primary) 8%, var(--surface-container-lowest)) 0%,
    var(--surface-container-lowest) 42%
  );
  overflow: hidden;
  box-shadow: 0 8px 28px color-mix(in srgb, var(--primary) 6%, transparent);
}
.preview-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--outline-variant);
}
.preview-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: 4px;
}
.preview-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--on-surface);
}
.preview-sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.preview-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  height: fit-content;
}
.preview-badge .material-symbols-outlined {
  font-size: 16px;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: var(--outline-variant);
  border-bottom: 1px solid var(--outline-variant);
}
.stat {
  padding: 16px 18px;
  background: var(--surface-container-lowest);
}
.stat-label {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.stat-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.2;
  color: var(--on-surface);
}
.stat-value.accent {
  color: var(--primary);
}
.stat-hint {
  margin-top: 4px;
  font-size: 11px;
  color: var(--on-surface-variant);
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 16px;
}
.preview-panel {
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  overflow: hidden;
}
.preview-panel.span-full {
  grid-column: 1 / -1;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 13px;
  font-weight: 700;
}
.panel-head .material-symbols-outlined {
  font-size: 18px;
  color: var(--primary);
}
.panel-count {
  margin-left: auto;
  font-size: 11px;
  font-weight: 650;
  color: var(--on-surface-variant);
}
.item-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.item-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--outline-variant) 70%, transparent);
}
.item-row:last-child {
  border-bottom: none;
}
.item-row.compact {
  padding: 10px 14px;
}
.item-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
}
.item-meta {
  margin-top: 3px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.item-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}
.item-amount {
  font-size: 13px;
  font-weight: 750;
  color: var(--primary);
}
.item-status {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.origin-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
}
.origin-tag.primary {
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  color: var(--primary);
}
.origin-tag.secondary {
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.empty {
  margin: 0;
  padding: 20px 14px;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}
.ident-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
  padding: 14px;
}
.ident-card {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.ident-source {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface);
}
.ident-id {
  margin-top: 4px;
  font-size: 11px;
  color: var(--on-surface-variant);
  word-break: break-all;
}
.ident-meta {
  margin-top: 4px;
  font-size: 10px;
  color: var(--on-surface-variant);
}

@media (max-width: 900px) {
  .preview-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
