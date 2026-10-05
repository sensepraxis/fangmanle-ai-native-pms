<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const loading = ref(false)
const tasks = ref<any[]>([])
const guestMap = ref<Record<number, any>>({})
const filter = ref<'open' | 'done' | 'all'>('open')

const TYPE_META: Record<string, { label: string; what: string; steps: string[] }> = {
  recall: {
    label: t('流失召回'),
    what: '这不是自动发消息，而是一条「待人工跟进」工单：提醒店员去联系这位高流失风险客人，争取再次预订。',
    steps: ['看客史与偏好', '私域/电话触达', '可推营销活动', '跟进完标记完成'],
  },
  care: {
    label: t('住中关怀'),
    what: '在住期间的跟进工单：处理微评、客需或低分预警，防止离店差评。',
    steps: [t('打开客户画像'), t('回复或派工'), t('标记完成')],
  },
  coupon: {
    label: t('专属优惠券'),
    what: '发券占位任务（尚未接券系统），正式环境会跳到发券并记录结果。',
    steps: ['选券面额', '推送到客人', '标记完成'],
  },
}

const shown = computed(() => {
  if (filter.value === 'all') return tasks.value
  return tasks.value.filter((t) => (t.status || 'open') === filter.value)
})

const openN = computed(() => tasks.value.filter((t) => (t.status || 'open') === 'open').length)

function meta(t: any) {
  return (
    TYPE_META[t.task_type] || {
      label: t.task_type || '运营',
      what: '客户运营跟进工单。',
      steps: ['处理', '标记完成'],
    }
  )
}

async function load() {
  loading.value = true
  try {
    const [ts, gs] = await Promise.all([
      api.listCrmTasks(hotelStore.hotelId),
      api.listGuests(hotelStore.hotelId).catch(() => []),
    ])
    tasks.value = ts || []
    const m: Record<number, any> = {}
    for (const g of gs || []) m[g.id] = g
    guestMap.value = m
  } catch {
    tasks.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) load()
  },
)

watch(
  () => hotelStore.hotelId,
  () => {
    if (props.open) load()
  },
)

async function markDone(t: any) {
  try {
    await api.completeCrmTask(t.id, hotelStore.hotelId)
    t.status = 'done'
    t.done_at = new Date().toISOString()
  } catch (e: any) {
    alert(e?.message || '更新失败')
  }
}

function openGuest(gid?: number) {
  if (!gid) return
  emit('close')
  router.push(`/guests/${gid}`)
}

function openButler(gid?: number) {
  emit('close')
  if (gid) router.push(`/guests/${gid}`)
  else router.push('/b-data/global-guest-directory')
}

function pushAcquisition(t: any) {
  emit('close')
  const q: Record<string, string> = {}
  if (t.segment_id) q.segment_id = String(t.segment_id)
  if (t.title) q.segment_name = String(t.title).replace(/ · 运营任务$/, '')
  if (t.guest_id) q.guest_id = String(t.guest_id)
  router.push({ path: '/acquisition/coupons', query: q })
}

function guestName(gid?: number) {
  return guestMap.value[gid || 0]?.name || (gid ? `客人 #${gid}` : '—')
}

defineExpose({ reload: load })
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <aside class="panel">
      <header class="head">
        <div>
          <h3>{{ t('运营任务') }}</h3>
          <p>{{ t('待处理') }} {{ openN }} · {{ t('每条是「跟进工单」，需店员执行具体动作') }}</p>
        </div>
        <button type="button" class="x" @click="emit('close')">×</button>
      </header>

      <div class="explain">
        <strong>{{ t('任务是什么？') }}</strong>
        {{
          t(
            '创建时只生成待办清单（谁、什么类型），不会自动打电话或发微信。 店员按建议动作联系客人后，再点「标记完成」。',
          )
        }}
      </div>

      <div class="tabs">
        <button type="button" :class="{ on: filter === 'open' }" @click="filter = 'open'">
          {{ t('待处理') }}
        </button>
        <button type="button" :class="{ on: filter === 'done' }" @click="filter = 'done'">
          {{ t('已完成') }}
        </button>
        <button type="button" :class="{ on: filter === 'all' }" @click="filter = 'all'">
          {{ t('全部') }}
        </button>
        <button type="button" class="refresh" @click="load">{{ t('刷新') }}</button>
      </div>

      <div class="list">
        <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
        <div v-else-if="!shown.length" class="empty">{{ t('暂无任务') }}</div>
        <article v-for="tag in shown" :key="tag.id" class="card">
          <div class="row">
            <span class="badge">{{ meta(tag).label }}</span>
            <span class="st" :class="tag.status">{{
              tag.status === 'done' ? t('已完成') : t('待处理')
            }}</span>
          </div>
          <h4>{{ tag.title || t('运营任务') }}</h4>
          <p class="who">
            {{ t('客人：') }}
            <button type="button" class="link" @click="openGuest(tag.guest_id)">
              {{ guestName(tag.guest_id) }}
            </button>
          </p>
          <p class="what">{{ meta(tag).what }}</p>
          <ol class="steps">
            <li v-for="(s, i) in meta(tag).steps" :key="i">{{ s }}</li>
          </ol>
          <p class="meta">
            #{{ tag.id }} ·
            {{
              String(tag.created_at || '')
                .slice(0, 19)
                .replace('T', ' ')
            }}
          </p>

          <div v-if="tag.status !== 'done'" class="acts">
            <button type="button" class="act" @click="openGuest(tag.guest_id)">
              {{ t('① 看 360 客史') }}
            </button>
            <button
              v-if="tag.task_type === 'recall' || tag.task_type === 'care'"
              type="button"
              class="act"
              @click="openButler(tag.guest_id)"
            >
              {{ t('② 私域/管家对话') }}
            </button>
            <button
              v-if="tag.task_type === 'recall'"
              type="button"
              class="act"
              @click="pushAcquisition(tag)"
            >
              {{ t('③ 去营销获客触达') }}
            </button>
            <button type="button" class="done" @click="markDone(tag)">
              {{ t('已跟进，标记完成') }}
            </button>
          </div>
        </article>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 210;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.panel {
  width: min(460px, 100%);
  background: var(--surface-container-lowest, #fff);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.12);
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 10px;
}
.head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
}
.head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.x {
  border: none;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}
.explain {
  margin: 0 16px 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--primary) 6%, #fff);
  border: 1px solid color-mix(in srgb, var(--primary) 18%, transparent);
  font-size: 12px;
  line-height: 1.5;
  color: var(--on-surface-variant);
}
.explain strong {
  color: var(--on-surface);
  display: block;
  margin-bottom: 2px;
}
.tabs {
  display: flex;
  gap: 6px;
  padding: 0 16px 10px;
  border-bottom: 1px solid var(--outline-variant);
  flex-wrap: wrap;
}
.tabs button {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: var(--on-surface-variant);
}
.tabs button.on {
  background: color-mix(in srgb, var(--primary) 12%, #fff);
  color: var(--primary);
  border-color: color-mix(in srgb, var(--primary) 30%, transparent);
}
.tabs .refresh {
  margin-left: auto;
}
.list {
  flex: 1;
  overflow: auto;
  padding: 12px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.empty {
  padding: 32px 8px;
  text-align: center;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.card {
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 12px;
  background: var(--surface-bright, #fff);
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 10%, #fff);
  color: var(--primary);
}
.st {
  font-size: 11px;
  font-weight: 650;
  color: #b45309;
}
.st.done {
  color: #047857;
}
.card h4 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
}
.who {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.what {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--on-surface);
}
.steps {
  margin: 0 0 8px;
  padding-left: 18px;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.5;
}
.meta {
  margin: 0 0 8px;
  font-size: 11px;
  color: var(--on-surface-variant);
  opacity: 0.9;
}
.link {
  border: none;
  background: none;
  color: var(--primary);
  font-weight: 650;
  cursor: pointer;
  padding: 0;
  font-size: 12px;
}
.acts {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.act,
.done {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  text-align: left;
}
.act {
  border: 1px solid var(--outline-variant);
  background: transparent;
  color: var(--on-surface);
}
.done {
  border: none;
  background: var(--primary);
  color: var(--on-primary);
  text-align: center;
}
</style>
