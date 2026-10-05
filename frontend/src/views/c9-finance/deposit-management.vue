<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 押金管理 —— 日常收银二级
 * 对齐技术方案：KPI / 台账 / 收押向导 / 详情抽屉 / 二次确认
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const router = useRouter()
const route = useRoute()

const aiOpen = ref(false)

type MainTab = 'ledger' | 'collect'
const mainTab = ref<MainTab>('ledger')
const bucket = ref<'all' | 'holding' | 'pending_release' | 'abnormal' | 'cash'>('all')
const keyword = ref('')
const loading = ref(false)
const err = ref('')
const toast = ref('')

const summary = ref({
  held_yuan: 0,
  count: 0,
  today_refund_yuan: 0,
  anomaly_count: 0,
})
const deposits = ref<any[]>([])

const collectOrders = ref<any[]>([])
const selectedOrderId = ref<number | null>(null)
const collectForm = ref('WECHAT_DEPOSIT')
const collectAmountYuan = ref(0)
const collectAuthExpire = ref('')
const collectReceipt = ref('')
const collectAuthCode = ref('')
const collecting = ref(false)

/** 收押主路径：手机号 → 客人 → 有效订单 */
const phoneInput = ref('')
const lookupLoading = ref(false)
const lookupHint = ref('请报一下预订手机号')
const matchedGuest = ref<any>(null)
const guestCandidates = ref<any[]>([])
const emptyAction = ref<any>(null)
const fallbackOpen = ref(false)
const roomFallback = ref('')
let phoneTimer: ReturnType<typeof setTimeout> | null = null

const drawerOpen = ref(false)
const detail = ref<any>(null)
const confirmOpen = ref(false)
const confirmAction = ref<'release' | 'reauthorize' | 'dispute' | 'collect' | null>(null)
const confirmMemo = ref('')

const FORM_META: Record<string, { label: string; hint: string; fields: string }> = {
  WECHAT_DEPOSIT: {
    label: t('微信押金 API'),
    hint: t('连通余额冻结（不可提现）· 私有字段 auth_code / auth_expire_at(+30d)'),
    fields: t('不碰钱 · 资金托管于支付通道'),
  },
  ALIPAY_DEPOSIT: {
    label: t('支付宝押金 API'),
    hint: t('连通余额冻结 · auth_code / auth_expire_at(+30d)'),
    fields: t('不碰钱 · 资金托管于支付通道'),
  },
  PREAUTH_CARD: {
    label: t('银行卡预授权'),
    hint: t('银联 POS 冻结额度 · 默认 +30 天'),
    fields: t('不碰钱 · 持牌收单机构清结算'),
  },
  CASH: {
    label: t('现金'),
    hint: t('必须收据号 + 保险柜登记'),
    fields: t('红线：无收据号禁止释放'),
  },
  AR: {
    label: t('企业挂账'),
    hint: t('转协议应收，不碰现金'),
    fields: t('适用于高信用 / 免押策略'),
  },
}

const BUCKETS = [
  { key: 'all' as const, label: t('全部') },
  { key: 'holding' as const, label: t('在押') },
  { key: 'pending_release' as const, label: t('待释放') },
  { key: 'abnormal' as const, label: t('异常') },
  { key: 'cash' as const, label: t('现金') },
]

const selectedOrder = computed(
  () => collectOrders.value.find((o) => o.order_id === selectedOrderId.value) || null,
)

const guestPreview = computed(
  () => matchedGuest.value?.preview || selectedOrder.value?.preview || null,
)

function money(n: number | undefined | null) {
  const v = Number(n || 0)
  return `¥${v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function statusClass(st: string) {
  if (st === 'FROZEN') return 'pill-ok'
  if (st === 'PARTIAL_CAPTURE') return 'pill-warn'
  if (st === 'EXPIRED' || st === 'DISPUTED') return 'pill-danger'
  if (st === 'RELEASED' || st === 'RELEASED_AFTER_CAPTURE' || st === 'CAPTURED') return 'pill-mute'
  return 'pill-mute'
}

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2800)
}

async function loadBoard() {
  loading.value = true
  err.value = ''
  try {
    const data = await api.depositsBoard(hotelStore.hotelId, {
      q: keyword.value || undefined,
      bucket: bucket.value === 'all' ? undefined : bucket.value,
    })
    summary.value = data.summary || summary.value
    deposits.value = data.deposits || []
  } catch (e: any) {
    err.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadCollectOrders() {
  /* 旧入口保留兼容；主路径改走手机号查找 */
}

function resetCollectLookup() {
  matchedGuest.value = null
  guestCandidates.value = []
  collectOrders.value = []
  selectedOrderId.value = null
  emptyAction.value = null
  lookupHint.value = t('请报一下预订手机号')
}

async function runPhoneLookup(raw?: string) {
  const phone = (raw ?? phoneInput.value).replace(/\D/g, '')
  if (phone.length < 3) {
    resetCollectLookup()
    lookupHint.value = t('满 3 位开始关联客户')
    return
  }
  lookupLoading.value = true
  try {
    const data = await api.depositsLookupByPhone(hotelStore.hotelId, phone)
    lookupHint.value = data.hint || ''
    guestCandidates.value = data.candidates || []
    emptyAction.value = data.empty_action || null
    if (data.matched && data.guest) {
      matchedGuest.value = data.guest
      collectOrders.value = data.orders || []
      if (data.auto_select_order_id) {
        selectOrder(data.auto_select_order_id)
      } else {
        selectedOrderId.value = null
      }
    } else {
      matchedGuest.value = null
      collectOrders.value = []
      selectedOrderId.value = null
    }
  } catch (e: any) {
    lookupHint.value = e?.message || t('查找失败')
    resetCollectLookup()
  } finally {
    lookupLoading.value = false
  }
}

function onPhoneInput() {
  phoneInput.value = phoneInput.value.replace(/[^\d]/g, '').slice(0, 11)
  if (phoneTimer) clearTimeout(phoneTimer)
  phoneTimer = setTimeout(() => runPhoneLookup(), 280)
}

async function lookupByRoom() {
  const rn = roomFallback.value.trim()
  if (!rn) {
    showToast(t('请输入房号'))
    return
  }
  lookupLoading.value = true
  try {
    const data = await api.depositsLookupByRoom(hotelStore.hotelId, rn)
    if (!data.matched) {
      showToast(data.hint || '未找到在住单')
      return
    }
    matchedGuest.value = data.guest
    collectOrders.value = data.orders || []
    emptyAction.value = null
    lookupHint.value = t('已通过房号定位')
    if (data.auto_select_order_id) selectOrder(data.auto_select_order_id)
  } catch (e: any) {
    showToast(e?.message || '房号查找失败')
  } finally {
    lookupLoading.value = false
  }
}

async function pickCandidate(guestId: number) {
  lookupLoading.value = true
  try {
    const data = await api.depositsLookupByGuest(hotelStore.hotelId, guestId)
    lookupHint.value = data.hint || t('已点选客人，请口头核验后选单')
    guestCandidates.value = []
    emptyAction.value = data.empty_action || null
    if (data.matched && data.guest) {
      matchedGuest.value = data.guest
      collectOrders.value = data.orders || []
      if (data.auto_select_order_id) selectOrder(data.auto_select_order_id)
      else selectedOrderId.value = null
    }
  } catch (e: any) {
    showToast(e?.message || '加载客人失败')
  } finally {
    lookupLoading.value = false
  }
}

function selectOrder(id: number) {
  selectedOrderId.value = id
  const o = collectOrders.value.find((x) => x.order_id === id)
  if (!o) return
  const p = o.preview || matchedGuest.value?.preview || {}
  collectForm.value = p.form_hint || 'WECHAT_DEPOSIT'
  collectAmountYuan.value = Number(p.suggested_amount_yuan || 0)
  const d = new Date()
  d.setDate(d.getDate() + 30)
  collectAuthExpire.value = d.toISOString().slice(0, 10)
  collectAuthCode.value = ''
  collectReceipt.value = ''
}

function openCollectTab() {
  mainTab.value = 'collect'
  resetCollectLookup()
  phoneInput.value = ''
  roomFallback.value = ''
  fallbackOpen.value = false
}

function depStatusClass(st: string) {
  if (st === 'collected') return 'pill-ok'
  if (st === 'need_topup') return 'pill-warn'
  return 'pill-mute'
}

async function openDetail(dep: any) {
  try {
    detail.value = await api.depositDetail(dep.deposit_id, hotelStore.hotelId)
    drawerOpen.value = true
  } catch (e: any) {
    showToast(e?.message || '加载详情失败')
  }
}

function askConfirm(action: typeof confirmAction.value) {
  confirmAction.value = action
  confirmMemo.value = ''
  confirmOpen.value = true
}

async function runConfirm() {
  if (!confirmAction.value) return
  try {
    if (confirmAction.value === 'collect') {
      await doCollect(true)
    } else if (confirmAction.value === 'release' && detail.value) {
      await api.depositRelease(detail.value.deposit_id, {
        refund_method: 'ORIGINAL',
        idempotency_key: `rel-${detail.value.deposit_id}-${Date.now()}`,
        memo: confirmMemo.value || undefined,
      })
      showToast(t('已释放/退押'))
      detail.value = await api.depositDetail(detail.value.deposit_id, hotelStore.hotelId)
      await loadBoard()
    } else if (confirmAction.value === 'reauthorize' && detail.value) {
      await api.depositReauthorize(detail.value.deposit_id, {
        memo: confirmMemo.value || t('重授权'),
      })
      showToast(t('重授权成功'))
      detail.value = await api.depositDetail(detail.value.deposit_id, hotelStore.hotelId)
      await loadBoard()
    } else if (confirmAction.value === 'dispute' && detail.value) {
      await api.depositDispute(detail.value.deposit_id, {
        memo: confirmMemo.value || t('争议登记'),
      })
      showToast(t('已登记争议'))
      detail.value = await api.depositDetail(detail.value.deposit_id, hotelStore.hotelId)
      await loadBoard()
    }
  } catch (e: any) {
    showToast(e?.message || '操作失败')
  } finally {
    confirmOpen.value = false
    confirmAction.value = null
  }
}

async function doCollect(confirmed = false) {
  const o = selectedOrder.value
  if (!o) {
    showToast(t('请先选择关联订单'))
    return
  }
  if (!confirmed) {
    askConfirm('collect')
    return
  }
  if (collectForm.value === 'CASH' && collectAmountYuan.value > 0 && !collectReceipt.value.trim()) {
    showToast(t('现金押金必须填写收据号'))
    return
  }
  collecting.value = true
  try {
    const waived = Number(collectAmountYuan.value) <= 0
    await api.depositCollect({
      order_id: o.order_id,
      customer_id: o.customer_id,
      guest_id: o.guest_id,
      room_no: o.room_no === '待排房' ? '0000' : o.room_no,
      guest_name: o.guest_name,
      form: collectForm.value,
      original_amount_yuan: Number(collectAmountYuan.value) || 0,
      waived,
      auth_code: collectAuthCode.value || undefined,
      auth_expire_at: collectAuthExpire.value ? `${collectAuthExpire.value}T23:59:59` : undefined,
      receipt_no: collectReceipt.value || undefined,
      nights: o.nights || 1,
      idempotency_key: `col-${o.order_id}-${Date.now()}`,
    })
    showToast(waived ? t('已确认免押') : t('收押成功'))
    mainTab.value = 'ledger'
    await loadBoard()
    resetCollectLookup()
    phoneInput.value = ''
  } catch (e: any) {
    showToast(e?.message || '收押失败')
  } finally {
    collecting.value = false
  }
}

watch(bucket, () => loadBoard())
watch(
  () => hotelStore.hotelId,
  () => {
    loadBoard()
    if (mainTab.value === 'collect') loadCollectOrders()
  },
)
watch(mainTab, (tab) => {
  if (tab === 'collect') {
    resetCollectLookup()
    phoneInput.value = ''
  }
})

onMounted(async () => {
  await loadBoard()
  const openId = String(route.query.open || '')
  if (openId) {
    mainTab.value = 'ledger'
    try {
      detail.value = await api.depositDetail(openId, hotelStore.hotelId)
      drawerOpen.value = true
    } catch {
      /* ignore */
    }
  }
})
</script>

<template>
  <div class="page deposit-page">
    <FinanceOpsNav />

    <div class="flex justify-between items-start gap-4 flex-wrap mb-5">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('押金管理') }}</h1>
      </div>
      <div class="flex gap-2 flex-wrap">
        <button
          v-if="commercialEnabled()"
          type="button"
          class="px-3 py-2 rounded-lg border border-primary text-sm font-semibold text-primary hover:bg-primary/5"
          @click="aiOpen = true"
        >
          {{ t('AI 安排') }}
        </button>
        <button
          type="button"
          class="px-3 py-2 rounded-lg border border-outline-variant text-sm font-semibold text-on-surface"
          disabled
        >
          {{ t('打印') }}
        </button>
      </div>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="deposit" @confirmed="loadBoard" />

    <!-- KPI -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <div class="kpi-card">
        <div class="kpi-label">{{ t('在押押金') }}</div>
        <div class="kpi-value">{{ money(summary.held_yuan) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">{{ t('笔数') }}</div>
        <div class="kpi-value">{{ summary.count }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">{{ t('今日退还') }}</div>
        <div class="kpi-value">{{ money(summary.today_refund_yuan) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">{{ t('异常') }}</div>
        <div class="kpi-value text-error">{{ summary.anomaly_count }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <nav class="sub-tabs mb-4" :aria-label="t('押金二级')">
      <button
        type="button"
        class="subtab"
        :class="{ on: mainTab === 'ledger' }"
        @click="mainTab = 'ledger'"
      >
        {{ t('押金台账') }}
      </button>
      <button
        type="button"
        class="subtab"
        :class="{ on: mainTab === 'collect' }"
        @click="openCollectTab"
      >
        {{ t('收押向导') }}
      </button>
    </nav>

    <p v-if="err" class="text-sm text-error mb-3">{{ err }}</p>
    <p v-if="toast" class="toast">{{ toast }}</p>

    <!-- 台账 -->
    <div v-show="mainTab === 'ledger'">
      <div class="toolbar mb-3">
        <div class="bucket-row">
          <button
            v-for="b in BUCKETS"
            :key="b.key"
            type="button"
            class="bucket"
            :class="{ on: bucket === b.key }"
            @click="bucket = b.key"
          >
            {{ b.label }}
          </button>
        </div>
        <div class="flex gap-2 flex-wrap items-center">
          <input
            v-model="keyword"
            class="search-input"
            :placeholder="t('房号 / 订单号 / 客人')"
            @keyup.enter="loadBoard"
          />
          <button type="button" class="btn-ghost" @click="loadBoard">{{ t('搜索') }}</button>
          <button type="button" class="btn-primary" @click="openCollectTab">
            {{ t('+ 收押') }}
          </button>
        </div>
      </div>

      <div class="table-card">
        <table>
          <thead>
            <tr>
              <th>{{ t('房号 / 客人') }}</th>
              <th>{{ t('关联订单') }}</th>
              <th>{{ t('形态') }}</th>
              <th>{{ t('金额') }}</th>
              <th>{{ t('状态') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="empty">{{ t('加载中…') }}</td>
            </tr>
            <tr v-else-if="!deposits.length">
              <td colspan="6" class="empty">{{ t('暂无押金记录') }}</td>
            </tr>
            <tr v-for="d in deposits" :key="d.deposit_id" class="row-click" @click="openDetail(d)">
              <td>
                <div class="font-semibold">{{ d.room_no }} · {{ d.guest_name || '—' }}</div>
                <div class="text-xs text-on-surface-variant">{{ d.deposit_id }}</div>
              </td>
              <td class="mono">{{ d.order_no || d.order_id }}</td>
              <td>{{ t(d.form_label || d.form || '') }}</td>
              <td class="font-semibold">{{ money(d.original_yuan) }}</td>
              <td>
                <span class="pill" :class="statusClass(d.status)">{{
                  t(d.status_label || d.status || '')
                }}</span>
              </td>
              <td>
                <button type="button" class="link" @click.stop="openDetail(d)">
                  {{ t('详情') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="table-tip">
          {{
            t(
              '点击行打开「关联订单 / 客户 360」抽屉。状态变更自动留审计流水（入住收押 / 退房释放）。',
            )
          }}
        </p>
      </div>
    </div>

    <!-- 收押向导：手机号 → 客户 → 有效订单 → 收押 -->
    <div v-show="mainTab === 'collect'" class="collect-wizard">
      <section class="panel collect-main">
        <h3 class="panel-title">{{ t('① 报预订手机号 · 定位客人') }}</h3>
        <p class="text-xs text-on-surface-variant mb-3">
          {{ t('先找客，再选单。一人多单须人工二次确认，系统不默认乱选。') }}
        </p>

        <label class="field-label">{{ t('预订手机号') }}</label>
        <div class="phone-row">
          <input
            v-model="phoneInput"
            class="field phone-input"
            type="tel"
            inputmode="numeric"
            maxlength="11"
            :placeholder="t('报一下预订手机号')"
            autocomplete="off"
            @input="onPhoneInput"
          />
          <span v-if="lookupLoading" class="lookup-spin">{{ t('查找中…') }}</span>
        </div>
        <p class="lookup-hint">{{ lookupHint }}</p>

        <div class="fallback-bar">
          <button type="button" class="link-quiet" @click="fallbackOpen = !fallbackOpen">
            {{ fallbackOpen ? t('收起边角入口') : t('无手机号？房号 / 姓名+到店日 / 会员码') }}
          </button>
          <div v-if="fallbackOpen" class="fallback-box mt-2">
            <label class="field-label">{{ t('房号快捷') }}</label>
            <div class="phone-row">
              <input
                v-model="roomFallback"
                class="field"
                :placeholder="t('如 1203')"
                @keyup.enter="lookupByRoom"
              />
              <button type="button" class="btn-ghost" @click="lookupByRoom">{{ t('定位') }}</button>
            </div>
            <p class="text-xs text-on-surface-variant mt-2">
              {{ t('姓名+到店日、会员码可后续接入；优先走手机号主路径。') }}
            </p>
          </div>
        </div>

        <!-- 多候选客人 -->
        <div v-if="guestCandidates.length > 1 && !matchedGuest" class="cand-list mt-3">
          <div class="text-xs font-semibold mb-2">
            {{ t('匹配到多位客人，请继续输入或口头核验') }}
          </div>
          <button
            v-for="c in guestCandidates"
            :key="c.guest_id"
            type="button"
            class="cand-row cand-btn"
            @click="pickCandidate(c.guest_id)"
          >
            <span>{{ c.name_masked }}</span>
            <span class="text-on-surface-variant">{{ c.phone_mask }}</span>
            <span class="text-xs">{{ c.vip_level || 'normal' }}</span>
          </button>
        </div>

        <!-- 有效订单卡片 -->
        <div v-if="matchedGuest" class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-bold">{{ t('② 有效订单') }}</h4>
            <span class="text-xs text-on-surface-variant">
              {{ collectOrders.length }} {{ t('笔 ·') }}
              {{
                collectOrders.length === 1
                  ? t('已自动选中')
                  : collectOrders.length > 1
                    ? t('请点选一笔')
                    : t('无')
              }}</span
            >
          </div>

          <div v-if="emptyAction" class="empty-orders">
            <p>{{ emptyAction.message }}</p>
            <div class="empty-actions">
              <router-link
                v-for="(a, i) in emptyAction.actions || []"
                :key="i"
                :to="a.path"
                class="btn-ghost"
              >
                {{ a.label }}</router-link
              >
            </div>
          </div>

          <div v-else class="order-cards">
            <button
              v-for="o in collectOrders"
              :key="o.order_id"
              type="button"
              class="order-pick"
              :class="{ on: selectedOrderId === o.order_id }"
              @click="selectOrder(o.order_id)"
            >
              <div class="flex justify-between gap-2">
                <b>{{ o.order_no }}</b>
                <span class="dep-pill" :class="depStatusClass(o.deposit_status)">{{
                  o.deposit_status_label
                }}</span>
              </div>
              <div class="text-xs mt-1">
                {{ o.room_type_name }} · {{ t('房') }} {{ o.room_no }} ·
                {{ o.status_label || o.status }}
              </div>
              <div class="text-xs text-on-surface-variant mt-1">
                {{ o.check_in }} → {{ o.check_out }} · {{ o.channel_name }}
              </div>
            </button>
          </div>
        </div>

        <!-- 选单后：形态 / 金额 -->
        <template v-if="selectedOrder">
          <div class="selected-strip mt-4">
            {{ t('已选') }} {{ selectedOrder.order_no }} · {{ selectedOrder.room_no }} ·
            {{ selectedOrder.check_in }} → {{ selectedOrder.check_out }}
          </div>

          <label class="field-label mt-4">{{ t('押金形态') }}</label>
          <select v-model="collectForm" class="field">
            <option v-for="(m, code) in FORM_META" :key="code" :value="code">{{ m.label }}</option>
          </select>
          <div class="form-hint">
            <div class="text-sm font-semibold text-on-surface">
              {{ FORM_META[collectForm]?.hint }}
            </div>
            <div class="text-xs text-primary mt-1">{{ FORM_META[collectForm]?.fields }}</div>
          </div>

          <label v-if="collectForm !== 'CASH' && collectForm !== 'AR'" class="field-label mt-3">{{
            t('预授权有效期')
          }}</label>
          <input
            v-if="collectForm !== 'CASH' && collectForm !== 'AR'"
            v-model="collectAuthExpire"
            type="date"
            class="field"
          />

          <label v-if="collectForm === 'CASH'" class="field-label mt-3">{{
            t('收据号（必填）')
          }}</label>
          <input
            v-if="collectForm === 'CASH'"
            v-model="collectReceipt"
            class="field"
            :placeholder="t('如 RCPT-20260831-01')"
          />

          <label class="field-label mt-3">{{ t('应收金额（策略试算，可改）') }}</label>
          <div class="amount-row">
            <input
              v-model.number="collectAmountYuan"
              type="number"
              min="0"
              step="50"
              class="field"
            />
            <span v-if="guestPreview?.waived" class="waive-tag">{{ t('建议免押') }}</span>
          </div>
          <p class="text-xs text-on-surface-variant mt-2">
            {{ t('提交前请再核对客人与金额；金额单位为元。') }}
          </p>

          <button
            type="button"
            class="btn-primary w-full mt-4 py-3"
            :disabled="collecting || !selectedOrder"
            @click="doCollect(false)"
          >
            {{ collecting ? t('提交中…') : collectAmountYuan <= 0 ? t('确认免押') : t('提交收押') }}
          </button>
        </template>
      </section>

      <section class="panel guest-panel" :class="{ lit: !!matchedGuest }">
        <h3 class="panel-title">{{ t('客户 360') }}</h3>
        <template v-if="matchedGuest">
          <div class="guest-head">
            <div>
              <div class="text-lg font-bold">
                {{ matchedGuest.name_masked || matchedGuest.name }}
              </div>
              <div class="text-xs text-on-surface-variant mt-1">
                {{ matchedGuest.phone_mask }} · {{ matchedGuest.vip_level || 'normal' }} · 年住
                {{ matchedGuest.stay_frequency || 0 }} 次
              </div>
              <div v-if="matchedGuest.confirm_hint" class="confirm-oral mt-2">
                {{ matchedGuest.confirm_hint }}
              </div>
            </div>
            <div class="score-ring">
              <div class="score-num">{{ matchedGuest.credit_score }}</div>
              <div class="score-lab">{{ t('信用分') }}</div>
            </div>
          </div>
          <div class="tag-row mt-3">
            <span
              v-for="(tag, i) in matchedGuest.risk_tags || ['—']"
              :key="i"
              class="risk-tag"
              :class="{ ok: String(tag).includes(t('无风险')) }"
            >
              {{ tag }}</span
            >
          </div>
          <div v-if="guestPreview" class="mt-4 text-sm text-on-surface-variant">
            规则：{{ guestPreview.rule }}
          </div>
          <div v-if="guestPreview" class="suggest mt-3">
            {{ t('系统建议押金：') }}
            <b>{{
              guestPreview.waived ? t('免押 ¥0') : money(guestPreview.suggested_amount_yuan)
            }}</b>
            · 形态 {{ FORM_META[guestPreview.form_hint]?.label || guestPreview.form_hint }}
          </div>
          <div v-if="selectedOrder" class="order-card mt-4">
            <div class="text-xs text-on-surface-variant mb-1">{{ t('已选订单卡') }}</div>
            <div>
              <b>{{ selectedOrder.order_no }}</b> · {{ selectedOrder.room_type_name }}
            </div>
            <div class="text-xs mt-1">
              房 {{ selectedOrder.room_no }} · {{ selectedOrder.channel_name }}
            </div>
            <div class="text-xs text-on-surface-variant mt-1">
              {{ selectedOrder.check_in }} → {{ selectedOrder.check_out }}
            </div>
          </div>
        </template>
        <p v-else class="text-sm text-on-surface-variant guest-idle">
          {{ t('输入满 3 位手机号后，此处点亮脱敏姓名、信用分、风险标签与历史入住。') }}
        </p>
      </section>
    </div>

    <!-- 详情抽屉 -->
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <aside class="drawer">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="text-lg font-bold">{{ t('押金详情') }}</h3>
            <div class="text-xs text-on-surface-variant mt-1">{{ detail?.deposit_id }}</div>
          </div>
          <button type="button" class="icon-btn" @click="drawerOpen = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <template v-if="detail">
          <div class="detail-grid">
            <div>
              <span>{{ t('房号') }}</span
              ><b>{{ detail.room_no }}</b>
            </div>
            <div>
              <span>{{ t('客人') }}</span
              ><b>{{ detail.guest_name }}</b>
            </div>
            <div>
              <span>{{ t('订单') }}</span
              ><b>{{ detail.order_no }}</b>
            </div>
            <div>
              <span>{{ t('形态') }}</span
              ><b>{{ t(detail.form_label || detail.form || '') }}</b>
            </div>
            <div>
              <span>{{ t('原额') }}</span
              ><b>{{ money(detail.original_yuan) }}</b>
            </div>
            <div>
              <span>{{ t('已扣') }}</span
              ><b>{{ money(detail.captured_yuan) }}</b>
            </div>
            <div>
              <span>{{ t('可退') }}</span
              ><b>{{ money(detail.remaining_yuan) }}</b>
            </div>
            <div>
              <span>{{ t('状态') }}</span>
              <b
                ><span class="pill" :class="statusClass(detail.status)">{{
                  t(detail.status_label || detail.status || '')
                }}</span></b
              >
            </div>
            <div v-if="detail.auth_code">
              <span>{{ t('授权码') }}</span
              ><b class="mono">{{ detail.auth_code }}</b>
            </div>
            <div v-if="detail.auth_expire_at">
              <span>{{ t('授权到期') }}</span
              ><b>{{ detail.auth_expire_at.slice(0, 10) }}</b>
            </div>
            <div v-if="detail.receipt_no">
              <span>{{ t('收据号') }}</span
              ><b>{{ detail.receipt_no }}</b>
            </div>
          </div>

          <h4 class="text-sm font-bold mt-5 mb-2">{{ t('状态时间线') }}</h4>
          <ul class="timeline">
            <li v-for="e in detail.ledger || []" :key="e.id">
              <div class="font-semibold text-sm">{{ e.event }} → {{ e.to_status }}</div>
              <div class="text-xs text-on-surface-variant">
                {{ e.created_at?.slice(0, 19) }} · {{ e.memo ? t(e.memo) : '—' }}
                <span v-if="e.amount_delta"> · ¥{{ e.amount_delta_yuan }}</span>
              </div>
            </li>
            <li v-if="!(detail.ledger || []).length" class="text-sm text-on-surface-variant">
              {{ t('暂无流水') }}
            </li>
          </ul>

          <div class="flex flex-wrap gap-2 mt-5">
            <button
              v-if="['FROZEN', 'PARTIAL_CAPTURE'].includes(detail.status)"
              type="button"
              class="btn-primary"
              @click="askConfirm('release')"
            >
              {{ t('释放 / 退押') }}
            </button>
            <button
              v-if="['EXPIRED', 'DISPUTED'].includes(detail.status)"
              type="button"
              class="btn-ghost"
              @click="askConfirm('reauthorize')"
            >
              {{ t('重授权') }}
            </button>
            <button
              v-if="['FROZEN', 'PARTIAL_CAPTURE'].includes(detail.status)"
              type="button"
              class="btn-ghost danger"
              @click="askConfirm('dispute')"
            >
              {{ t('登记争议') }}
            </button>
            <button
              type="button"
              class="btn-ghost"
              @click="router.push(detail.order_id ? `/orders/${detail.order_id}` : '/orders')"
            >
              {{ t('打开关联订单') }}
            </button>
          </div>
        </template>
      </aside>
    </div>

    <!-- 二次确认 -->
    <div v-if="confirmOpen" class="drawer-mask" @click.self="confirmOpen = false">
      <div class="confirm-card">
        <h3 class="text-lg font-bold mb-2">{{ t('二次确认') }}</h3>
        <p class="text-sm text-on-surface-variant mb-3">
          <template v-if="confirmAction === 'collect'">{{
            t('确认提交收押？将写审计流水并生成押金单。')
          }}</template>
          <template v-else-if="confirmAction === 'release'">{{
            t('确认释放/退押？现金单须已有收据号。')
          }}</template>
          <template v-else-if="confirmAction === 'reauthorize'">{{
            t('确认重授权并恢复为在押？')
          }}</template>
          <template v-else>{{ t('确认登记争议？操作将冻结直至协商结案。') }}</template>
        </p>
        <input v-model="confirmMemo" class="field mb-3" :placeholder="t('备注（可选）')" />
        <div class="flex gap-2 justify-end">
          <button type="button" class="btn-ghost" @click="confirmOpen = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="btn-primary" @click="runConfirm">{{ t('确认执行') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deposit-page {
  padding-bottom: 2.5rem;
}
.kpi-card {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.kpi-label {
  font-size: 12px;
  color: #79747e;
  font-weight: 600;
}
.kpi-value {
  margin-top: 0.35rem;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1c1b1f;
}

.sub-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid #e5e7eb;
}
.subtab {
  border: none;
  background: transparent;
  padding: 10px 16px 11px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.subtab.on {
  color: #1f2329;
  border-bottom-color: #1f2329;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
}
.bucket-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.bucket {
  border: 1px solid #e7e0ec;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
}
.bucket.on {
  background: #1f2329;
  border-color: #1f2329;
  color: #fff;
}
.search-input {
  border: 1px solid #cac4d0;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  min-width: 180px;
}
.btn-primary {
  background: #6750a4;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost {
  background: #fff;
  border: 1px solid #cac4d0;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: #1f2329;
}
.btn-ghost.danger {
  color: #c5221f;
  border-color: #f5c2c0;
}

.table-card {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  overflow: hidden;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th {
  text-align: left;
  padding: 12px 14px;
  background: #f3f4f6;
  color: #5b616e;
  font-weight: 600;
}
td {
  padding: 12px 14px;
  border-top: 1px solid #f0edf2;
  color: #1c1b1f;
}
.row-click {
  cursor: pointer;
}
.row-click:hover {
  background: #f7f2fa;
}
.empty {
  text-align: center;
  color: #79747e;
  padding: 2rem !important;
}
.table-tip {
  margin: 0;
  padding: 10px 14px;
  font-size: 12px;
  color: #5b616e;
  background: #eef4ff;
  border-top: 1px solid #d3e3fd;
}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.pill-ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.pill-warn {
  background: #fff8e1;
  color: #b26a00;
}
.pill-danger {
  background: #fce8e6;
  color: #c5221f;
}
.pill-mute {
  background: #f3f4f6;
  color: #5b616e;
}
.link {
  border: none;
  background: none;
  color: #6750a4;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}

.collect-wizard {
  display: grid;
  grid-template-columns: 1.25fr 0.85fr;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 960px) {
  .collect-wizard {
    grid-template-columns: 1fr;
  }
}
.phone-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.phone-input {
  font-size: 18px;
  letter-spacing: 0.06em;
  font-weight: 600;
  padding: 12px 14px;
}
.lookup-spin {
  font-size: 12px;
  color: #6750a4;
  white-space: nowrap;
}
.lookup-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: #79747e;
}
.fallback-bar {
  margin-top: 12px;
}
.link-quiet {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #6750a4;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.fallback-box {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f2fa;
  border: 1px dashed #cac4d0;
}
.cand-list {
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  padding: 10px 12px;
}
.cand-row {
  display: flex;
  gap: 12px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid #f3edf7;
  width: 100%;
  background: none;
  border-left: none;
  border-right: none;
  border-top: none;
  text-align: left;
}
.cand-btn {
  cursor: pointer;
  border-radius: 6px;
  padding: 8px 4px;
}
.cand-btn:hover {
  background: #f7f2fa;
}
.cand-row:last-child {
  border-bottom: none;
}
.order-cards {
  display: grid;
  gap: 8px;
}
.order-pick {
  text-align: left;
  border: 1px solid #e7e0ec;
  background: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.order-pick:hover {
  border-color: #b69df8;
}
.order-pick.on {
  border-color: #6750a4;
  box-shadow: 0 0 0 2px rgba(103, 80, 164, 0.18);
  background: #f7f2fa;
}
.dep-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.pill-ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.pill-warn {
  background: #fff3e0;
  color: #ef6c00;
}
.pill-mute {
  background: #f3edf7;
  color: #49454f;
}
.empty-orders {
  padding: 14px;
  border-radius: 12px;
  background: #fff8e1;
  border: 1px solid #ffe082;
  font-size: 13px;
}
.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.selected-strip {
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #e8def8;
  color: #1d192b;
}
.guest-panel {
  opacity: 0.55;
  transition:
    opacity 0.2s,
    border-color 0.2s,
    box-shadow 0.2s;
}
.guest-panel.lit {
  opacity: 1;
  border-color: #b69df8;
  box-shadow: 0 4px 18px rgba(103, 80, 164, 0.12);
}
.guest-idle {
  line-height: 1.6;
  padding: 8px 0;
}
.confirm-oral {
  font-size: 12px;
  color: #6750a4;
  background: #f3edf7;
  padding: 6px 8px;
  border-radius: 8px;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  border: 1px solid #cac4d0;
  background: #fff;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 12px;
  cursor: pointer;
  text-decoration: none;
  color: inherit;
}
.btn-ghost:hover {
  background: #f7f2fa;
}
.panel {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  padding: 1.1rem 1.2rem;
}
.panel-title {
  margin: 0 0 1rem;
  font-size: 15px;
  font-weight: 700;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #79747e;
  margin-bottom: 6px;
}
.field {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 13px;
  background: #fff;
  box-sizing: border-box;
}
.form-hint {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f2fa;
  border: 1px solid #e7e0ec;
}
.order-card {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f3f4f6;
  font-size: 13px;
  display: grid;
  gap: 4px;
}
.amount-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.waive-tag {
  font-size: 11px;
  font-weight: 700;
  color: #2e7d32;
  background: #e8f5e9;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}
.guest-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.score-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 4px solid #6750a4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.score-num {
  font-size: 1.25rem;
  font-weight: 800;
  color: #6750a4;
  line-height: 1;
}
.score-lab {
  font-size: 10px;
  color: #79747e;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.risk-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  background: #fff8e1;
  color: #b26a00;
}
.risk-tag.ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.suggest {
  padding: 10px 12px;
  border-radius: 10px;
  background: #eef4ff;
  font-size: 13px;
}

.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(28, 27, 31, 0.4);
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: min(420px, 100%);
  height: 100%;
  background: #fffbfe;
  padding: 1.25rem;
  overflow: auto;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.12);
}
.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #5b616e;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
  font-size: 13px;
}
.detail-grid span {
  display: block;
  font-size: 11px;
  color: #79747e;
  margin-bottom: 2px;
}
.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-left: 2px solid #e7e0ec;
  padding-left: 12px;
}
.confirm-card {
  margin: auto;
  background: #fff;
  border-radius: 14px;
  padding: 1.25rem;
  width: min(400px, calc(100% - 2rem));
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2329;
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  z-index: 60;
  font-weight: 600;
}
.w-full {
  width: 100%;
}
.mt-3 {
  margin-top: 0.75rem;
}
.mt-4 {
  margin-top: 1rem;
}
.mt-5 {
  margin-top: 1.25rem;
}
.mb-3 {
  margin-bottom: 0.75rem;
}
</style>
