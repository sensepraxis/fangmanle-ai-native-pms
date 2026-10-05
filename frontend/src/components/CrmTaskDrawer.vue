<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const props = defineProps<{
  open: boolean
  segmentId?: number
  segmentName?: string
  guestIds?: number[]
  /** recall=流失召回场景；care=住中；不传则给通用三项 */
  defaultType?: string
}>()

const emit = defineEmits<{ close: []; done: [n: number] }>()

const router = useRouter()
const saving = ref(false)
const toast = ref('')
const taskType = ref(props.defaultType || 'recall')

watch(
  () => [props.open, props.defaultType] as const,
  ([open, def]) => {
    if (open) taskType.value = def || 'recall'
  },
)

/** 高流失「发起关怀」只保留召回；住中入口另走住中关怀页，优惠券为后续占位不在此场景展示 */
const TYPE_OPTS = computed(() => {
  if (props.defaultType === 'recall') {
    return [
      {
        id: 'recall',
        label: t('流失召回'),
        icon: 'campaign',
        desc: t('针对离店/沉默客群建跟进任务，后续可推送到营销触达'),
      },
    ]
  }
  if (props.defaultType === 'care') {
    return [
      {
        id: 'care',
        label: t('住中关怀'),
        icon: 'volunteer_activism',
        desc: t('在住客人即时微评/客需跟进（需当前有在住订单）'),
      },
    ]
  }
  return [
    { id: 'recall', label: t('流失召回'), icon: 'campaign', desc: t('离店客群召回') },
    { id: 'care', label: t('住中关怀'), icon: 'volunteer_activism', desc: t('在住客即时跟进') },
    { id: 'coupon', label: t('专属优惠券（占位）'), icon: 'local_offer', desc: t('尚未接券系统') },
  ]
})

const typeHint = computed(() => TYPE_OPTS.value.find((t) => t.id === taskType.value)?.desc || '')

function flash(msg: string) {
  toast.value = msg
  window.setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2800)
}

async function submit() {
  if (saving.value) return
  saving.value = true
  try {
    const gids = props.guestIds || []
    const res = await api.createCrmTasks(hotelStore.hotelId, {
      task_type: taskType.value,
      title: props.segmentName ? `${props.segmentName} · 运营任务` : undefined,
      guest_ids: gids.length ? gids : undefined,
      segment_id: props.segmentId,
    })
    const n = res?.created ?? 0
    flash(`已创建 ${n} 条任务。请到客群列表右上角「运营任务」查看`)
    emit('done', n)
    window.setTimeout(() => emit('close'), 1200)
  } catch (e: any) {
    alert(e?.message || '创建任务失败')
  } finally {
    saving.value = false
  }
}

function pushAcquisition() {
  const q: Record<string, string> = {}
  if (props.segmentId) q.segment_id = String(props.segmentId)
  if (props.segmentName) q.segment_name = props.segmentName
  router.push({ path: '/acquisition/coupons', query: q })
  emit('close')
}
</script>

<template>
  <div v-if="open" class="drawer-mask" @click.self="emit('close')">
    <div v-if="toast" class="toast">
      {{ toast }}
    </div>
    <div class="drawer">
      <header class="drawer-head">
        <h3>{{ t('客户运营动作') }}</h3>
        <button type="button" class="x" @click="emit('close')">×</button>
      </header>
      <p class="hint">
        <template v-if="segmentName">分群：{{ segmentName }}</template>
        <template v-else-if="guestIds?.length">已选 {{ guestIds.length }} 位客人</template>
        <template v-else>{{ t('选择运营动作类型') }}</template>
      </p>
      <div class="types">
        <button
          v-for="tag in TYPE_OPTS"
          :key="tag.id"
          type="button"
          class="type"
          :class="{ on: taskType === tag.id }"
          @click="taskType = tag.id"
        >
          <span class="material-symbols-outlined">{{ tag.icon }}</span>
          <span class="type-text">
            <strong>{{ tag.label }}</strong>
            <small v-if="tag.desc">{{ tag.desc }}</small>
          </span>
        </button>
      </div>
      <p v-if="typeHint" class="type-hint">{{ typeHint }}</p>
      <div class="actions">
        <button type="button" class="btn ghost" @click="pushAcquisition">
          {{ t('推送到营销获客') }}
        </button>
        <button type="button" class="btn primary" :disabled="saving" @click="submit">
          {{ saving ? t('创建中…') : t('创建运营任务') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 220;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--on-surface);
  color: var(--surface);
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  max-width: min(420px, 90vw);
}
.drawer {
  width: min(400px, 100%);
  background: var(--surface-container-lowest, #fff);
  padding: 20px;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.drawer-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
}
.x {
  border: none;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}
.hint {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.types {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.type {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-bright);
  cursor: pointer;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
}
.type.on {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 8%, #fff);
  color: var(--primary);
}
.type .material-symbols-outlined {
  font-size: 18px;
  margin-top: 2px;
}
.type-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.type-text strong {
  font-size: 13px;
}
.type-text small {
  font-size: 11px;
  font-weight: 500;
  color: var(--on-surface-variant);
  line-height: 1.35;
}
.type.on .type-text small {
  color: color-mix(in srgb, var(--primary) 70%, var(--on-surface-variant));
}
.type-hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
}
.btn {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
}
.btn.ghost {
  background: transparent;
  color: var(--primary);
}
.btn.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
