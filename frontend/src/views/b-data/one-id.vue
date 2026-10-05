<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * One ID 归并系统 —— 数据：GET /api/oneid/board + /api/oneid/conflicts
 * 闭环：H5 全号/后六位多人冲突 → 本台人工裁定 → 发券绑企微 → 客人重开链接进会员中心
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import OneIdFlowSubnav from '../../components/OneIdFlowSubnav.vue'

const router = useRouter()
const board = ref<any>(null)
const conflicts = ref<any[]>([])
const resolving = ref<number | null>(null)
const lastResolveMsg = ref('')
const conflictSection = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const [b, conf] = await Promise.all([
      api.oneidBoard(),
      api.listOneidConflicts('pending').catch(() => []),
    ])
    board.value = b
    conflicts.value = conf || []
  } catch {
    board.value = null
  }
})

const conflictN = computed(() =>
  Number(board.value?.phone_conflicts_pending ?? conflicts.value.length ?? 0),
)
const multiN = computed(() => Number(board.value?.multi_source_guests || 0))

async function goConflict() {
  await nextTick()
  conflictSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function maskPhone(p?: string) {
  if (!p) return '—'
  const d = String(p).replace(/\D/g, '')
  const n = d.length >= 13 && d.startsWith('86') ? d.slice(2) : d
  return n.length >= 7 ? `${n.slice(0, 3)}****${n.slice(-4)}` : p
}
function matchBadge(c: any) {
  return c.match_type === 'phone_exact_multi' ? t('全号重复') : t('后六位撞车')
}

async function resolveConflict(c: any, guestId: number) {
  if (resolving.value) return
  const target = (c.candidates || []).find((x: any) => Number(x.guest_id) === Number(guestId))
  const name = target?.name || target?.guest_name || t('客人 #{id}', { id: guestId })
  if (!window.confirm(t('确认归并到「{name}」并完成发券？\n发券后不可撤回。', { name }))) return
  resolving.value = c.id
  lastResolveMsg.value = ''
  try {
    const r = await api.resolveOneidConflict(c.id, guestId)
    conflicts.value = conflicts.value.filter((x) => x.id !== c.id)
    board.value = await api.oneidBoard().catch(() => board.value)
    lastResolveMsg.value = t(
      r?.message || '已归并到 {name} 并发券。请通知客人重新打开欢迎语卡片进入会员中心。',
      { name: r?.guest_name || guestId },
    )
  } catch (e: any) {
    alert(t(e?.message || '裁定失败'))
  } finally {
    resolving.value = null
  }
}

async function dismissConflict(c: any) {
  if (resolving.value) return
  resolving.value = c.id
  try {
    await api.dismissOneidConflict(c.id, t('保持分离'))
    conflicts.value = conflicts.value.filter((x) => x.id !== c.id)
    lastResolveMsg.value = t('已驳回该冲突，客人可重新提交手机号。')
  } catch (e: any) {
    alert(t(e?.message || '驳回失败'))
  } finally {
    resolving.value = null
  }
}

function openGuest(id: number) {
  router.push(`/guests/${id}`)
}
</script>

<template>
  <div class="page">
    <OneIdFlowSubnav />
    <div class="mb-6">
      <h1 class="font-display-lg text-display-lg text-on-background mb-2">
        {{ t('One ID 归并台') }}
      </h1>
      <p class="font-body-lg text-body-lg text-on-surface-variant">
        {{
          t(
            '企微领券时若手机号对应多位档案（全号相同，或仅后六位相同），在此人工选定目标客人并完成发券。完成后点「下一步」进入冲突队列。',
          )
        }}
      </p>
    </div>

    <div
      v-if="lastResolveMsg"
      class="mb-4 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-on-surface"
    >
      {{ lastResolveMsg }}
    </div>

    <div class="grid grid-cols-12 gap-gutter mb-6">
      <div
        class="col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-4"
      >
        <div class="text-xs text-on-surface-variant">{{ t('多源身份客人') }}</div>
        <div class="text-2xl font-bold text-primary mt-1">{{ multiN }}</div>
      </div>
      <button
        type="button"
        class="col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-4 text-left hover:border-primary/40 hover:shadow-sm transition-all"
        @click="goConflict"
      >
        <div class="text-xs text-on-surface-variant">{{ t('待处理手机号冲突') }}</div>
        <div class="text-2xl font-bold mt-1 text-primary">{{ conflictN }}</div>
      </button>
      <div
        class="col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-4"
      >
        <div class="text-xs text-on-surface-variant">{{ t('身份链路总数') }}</div>
        <div class="text-2xl font-bold mt-1">{{ board?.identity_total ?? 0 }}</div>
      </div>
    </div>

    <section
      ref="conflictSection"
      class="mb-6 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden"
    >
      <div class="px-4 py-3 border-b border-outline-variant flex items-center justify-between">
        <h2 class="m-0 text-base font-bold">{{ t('手机号冲突 · 待人工归集') }}</h2>
        <span class="text-xs text-on-surface-variant"
          >{{ t('共') }} {{ conflicts.length }} {{ t('条') }}</span
        >
      </div>
      <div v-if="!conflicts.length" class="p-8 text-center text-on-surface-variant text-sm">
        {{
          t('暂无待处理冲突。当 360 中存在同号多人，或仅尾号撞车时，客人 H5 提交后会出现在这里。')
        }}
      </div>
      <div v-for="c in conflicts" :key="c.id" class="border-t border-outline-variant p-4">
        <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div>
            <div class="font-semibold text-sm flex flex-wrap items-center gap-2">
              <span>{{ t('冲突') }} #{{ c.id }} · {{ c.nickname || t('企微客人') }}</span>
              <span
                class="text-[11px] font-bold px-2 py-0.5 rounded-full"
                :class="
                  c.match_type === 'phone_exact_multi'
                    ? 'bg-amber-100 text-amber-900'
                    : 'bg-slate-100 text-slate-700'
                "
                >{{ matchBadge(c) }}</span
              >
            </div>
            <div class="text-xs text-on-surface-variant mt-1 font-mono">
              {{ t('提交') }} {{ maskPhone(c.phone_submitted) }}
              <span v-if="c.match_type !== 'phone_exact_multi'">
                · {{ t('后六位 {n}', { n: c.phone_last6 || c.phone_last4 }) }}</span
              >
              · {{ t('企微') }} {{ c.external_userid }}
            </div>
            <div v-if="c.note" class="text-xs text-on-surface-variant mt-1">{{ c.note }}</div>
          </div>
          <button
            type="button"
            class="text-xs px-3 py-1.5 rounded-lg border border-outline-variant"
            :disabled="resolving === c.id"
            @click="dismissConflict(c)"
          >
            {{ t('保持分离 / 驳回') }}
          </button>
        </div>
        <div class="grid gap-2 md:grid-cols-2">
          <div
            v-for="g in c.candidates || []"
            :key="g.guest_id"
            class="border border-outline-variant rounded-lg p-3 flex items-center justify-between gap-2"
          >
            <button type="button" class="text-left min-w-0" @click="openGuest(g.guest_id)">
              <div class="font-semibold text-sm truncate">{{ g.name }} · #{{ g.guest_id }}</div>
              <div class="text-xs text-on-surface-variant mt-0.5">
                {{ maskPhone(g.phone) }} · {{ g.vip_label || g.vip_level || t('会员') }}
              </div>
              <div class="text-xs text-on-surface-variant mt-0.5">
                {{ t('订单') }} {{ g.order_count ?? 0 }} · LTV ¥{{
                  Number(g.ltv || 0).toLocaleString('zh-CN')
                }}
                <span v-if="g.one_id"> · {{ g.one_id }}</span>
              </div>
            </button>
            <button
              type="button"
              class="shrink-0 px-3 py-1.5 rounded-lg bg-primary text-on-primary text-xs font-semibold disabled:opacity-50"
              :disabled="resolving === c.id"
              @click="resolveConflict(c, g.guest_id)"
            >
              {{ t('归并到此并发券') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <aside class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 text-sm">
      <div class="font-semibold mb-2">{{ t('归集规则') }}</div>
      <ol class="m-0 pl-4 text-on-surface-variant space-y-1 list-decimal">
        <li>{{ t('客人 H5 提交手机号（可带 +86）') }}</li>
        <li>{{ t('全号唯一 → 自动归集发券') }}</li>
        <li>{{ t('全号多人同号 → 本台人工') }}</li>
        <li>{{ t('无全号、后六位唯一 → 自动归集') }}</li>
        <li>{{ t('后六位多人 → 本台人工') }}</li>
        <li>{{ t('零命中 → 新建档案；裁定后请客人重开卡片') }}</li>
      </ol>
    </aside>
  </div>
</template>
