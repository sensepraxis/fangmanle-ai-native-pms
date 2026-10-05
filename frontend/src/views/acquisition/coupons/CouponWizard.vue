<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, getLocale } from '../../../lib/i18n'

import { computed } from 'vue'
import { TYPES, LEVEL_OPTS_MSGID, fmtDt, listTypeMetas } from './constants'
import type { CouponForm, CouponTypeMeta } from './types'

const props = defineProps<{
  form: CouponForm
  step: number
  busy: boolean
  roomTypeOpts: string[]
}>()

const emit = defineEmits<{
  (e: 'update:step', v: number): void
  (e: 'close'): void
  (e: 'create', publish: boolean): void
}>()

const typeCards = computed(() => listTypeMetas())

const typeMeta = computed(() => TYPES[props.form.type] || TYPES.DISCOUNT)

const previewFace = computed(() => {
  const raw = String(props.form.face_raw ?? '').trim()
  if (!raw) return t('（待填）')
  if (props.form.type === 'DISCOUNT') {
    const v = Number(raw)
    if (!Number.isFinite(v)) return raw
    if (getLocale() === 'en' && v > 0 && v <= 1) {
      return `${Math.round((1 - v) * 100)}% off room rate`
    }
    const n = (v * 10).toFixed(1).replace(/\.0$/, '')
    return t('房价 {n} 折').replace('{n}', n)
  }
  if (props.form.type === 'CASH_ROOM') {
    return t('指定房型立减¥{amt}（满{thr}可用）')
      .replace('{amt}', raw)
      .replace('{thr}', String(props.form.threshold || 0))
  }
  if (props.form.type === 'CASH_ALL') {
    return t('通用立减¥{amt}（无门槛）').replace('{amt}', raw)
  }
  if (props.form.type === 'BENEFIT' || typeMeta.value.isText) return raw
  return raw
})

function selectType(t: string) {
  props.form.type = t
  const T = TYPES[t] as CouponTypeMeta
  props.form.face_raw = T.isText ? '' : T.ph
  if (T.thrHide) props.form.threshold = 0
}

function toggleChip(list: string[], v: string) {
  const i = list.indexOf(v)
  if (i >= 0) list.splice(i, 1)
  else list.push(v)
}

function toggleRoom(r: string) {
  const i = props.form.rooms.indexOf(r)
  if (i >= 0) props.form.rooms.splice(i, 1)
  else props.form.rooms.push(r)
}

function go(d: number) {
  if (d > 0 && props.step === 4) {
    emit('create', true)
    return
  }
  const n = Math.min(4, Math.max(1, props.step + d))
  emit('update:step', n)
}
</script>

<template>
  <div class="wizard panel-box">
    <div class="wz-head">
      <div>
        <h3>{{ t('新建优惠券批次') }}</h3>
        <div class="wz-steps">
          <div
            v-for="n in 4"
            :key="n"
            class="wz-step"
            :class="{ cur: step === n, done: step > n }"
            @click="emit('update:step', n)"
          >
            <div class="num">{{ n }}</div>
            {{ [t('选类型'), t('填参数'), t('定范围'), t('预览投放')][n - 1] }}
          </div>
        </div>
      </div>
      <button type="button" class="btn sm" @click="emit('close')">{{ t('✕ 关闭') }}</button>
    </div>

    <div class="wz-body">
      <div v-if="step === 1">
        <div class="coupon-types">
          <button
            v-for="item in typeCards"
            :key="item.key"
            type="button"
            class="coupon-type"
            :class="{ selected: form.type === item.key }"
            @click="selectType(String(item.key))"
          >
            <div class="ico">{{ item.meta.ico }}</div>
            <div class="nm">{{ item.meta.nm }}</div>
            <div class="ds">{{ item.meta.ds }}</div>
          </button>
        </div>
      </div>

      <div v-else-if="step === 2" class="form-grid">
        <div class="fg">
          <label>{{ t('批次号') }}</label>
          <input :value="form.batch_no" readonly />
          <div class="hint">{{ t('系统按 COUPON-YYYYMMDD-NNN 自动生成') }}</div>
        </div>
        <div class="fg">
          <label>{{ t('券名称 *') }}</label>
          <input v-model="form.name" :placeholder="t('例：房价7折 / 通用立减¥50')" />
        </div>
        <div v-if="form.type === 'BENEFIT'" class="fg">
          <label>{{ t('权益类型') }}</label>
          <select v-model="form.benefit_key">
            <option value="BREAKFAST">{{ t('免费早餐') }}</option>
            <option value="LATE_CHECKOUT">{{ t('延迟退房') }}</option>
            <option value="ROOM_UPGRADE">{{ t('升房') }}</option>
            <option value="FREE_NIGHT">{{ t('连住送夜') }}</option>
            <option value="CUSTOM">{{ t('自定义') }}</option>
          </select>
        </div>
        <div class="fg">
          <label>{{ typeMeta.lbl }}</label>
          <input
            v-model="form.face_raw"
            type="text"
            :inputmode="typeMeta.isText ? 'text' : 'decimal'"
            :placeholder="typeMeta.ph"
          />
          <div class="hint">{{ typeMeta.hint }}</div>
        </div>
        <div v-if="form.type === 'DISCOUNT'" class="fg">
          <label>{{ t('最高减免（元，可选）') }}</label>
          <input v-model="form.max_discount" type="number" :placeholder="t('不封顶可留空')" />
        </div>
        <div v-if="!typeMeta.thrHide" class="fg">
          <label>{{ t('使用门槛（元）') }}</label>
          <input v-model.number="form.threshold" type="number" />
          <div class="hint">{{ t('满 X 元可用；0 表示无门槛') }}</div>
        </div>
        <div class="fg">
          <label>{{ t('发行总量 *') }}</label>
          <input v-model.number="form.total_qty" type="number" />
        </div>
        <div class="fg">
          <label>{{ t('每人限领') }}</label>
          <input v-model.number="form.per_user_qty" type="number" />
        </div>
        <div class="fg">
          <label>{{ t('有效期怎么算 *') }}</label>
          <select v-model="form.validity_mode">
            <option value="FIXED">{{ t('统一有效期（所有人同一段时间可用）') }}</option>
            <option value="RELATIVE">{{ t('领券后起算（每人领到后单独算天数）') }}</option>
          </select>
          <div class="hint">
            <template v-if="form.validity_mode === 'FIXED'">{{
              t('例如：2026-09-01 ～ 2026-09-30，不管哪天领，都只能在这段日期内用。')
            }}</template>
            <template v-else>{{
              t(
                '例如：设 7 天，客人 9 月 1 日领 → 用到 9 月 8 日；另一人 9 月 5 日领 → 用到 9 月 12 日。',
              )
            }}</template>
          </div>
        </div>
        <div v-if="form.validity_mode === 'RELATIVE'" class="fg">
          <label>{{ t('领券后几天内可用 *') }}</label>
          <input v-model.number="form.validity_days" type="number" min="1" />
          <div class="hint">{{ t('从领取当天起算，含领取日') }}</div>
        </div>
        <template v-else>
          <div class="fg">
            <label>{{ t('可用开始时间 *') }}</label>
            <input v-model="form.valid_from" type="datetime-local" />
          </div>
          <div class="fg">
            <label>{{ t('可用结束时间 *') }}</label>
            <input v-model="form.valid_to" type="datetime-local" />
          </div>
        </template>
      </div>

      <div v-else-if="step === 3">
        <div class="fg full mb">
          <label>{{ t('适用房型') }}</label>
          <div v-if="roomTypeOpts.length" class="check-row room-checks">
            <label v-for="r in roomTypeOpts" :key="r" class="chk">
              <input type="checkbox" :checked="form.rooms.includes(r)" @change="toggleRoom(r)" />
              <span>{{ r }}</span>
            </label>
          </div>
          <p v-else class="hint warn-hint">
            {{ t('暂无房型，请先在「系统配置 · 房型管理」中维护。') }}
          </p>
        </div>
        <div class="fg full">
          <label>{{ t('会员等级限制（可不选 = 不限）') }}</label>
          <div class="check-row">
            <button
              v-for="lv in LEVEL_OPTS_MSGID"
              :key="lv"
              type="button"
              class="chip"
              :class="{ on: form.levels.includes(lv) }"
              @click="toggleChip(form.levels, lv)"
            >
              {{ t(lv) }}
            </button>
          </div>
        </div>
      </div>

      <div v-else>
        <div class="preview">
          <div class="tt">{{ t('客户领券预览') }} · {{ typeMeta.nm }}</div>
          <div class="big">{{ previewFace }}</div>
          <div class="nm">{{ form.name || t('未命名券') }}</div>
          <div class="row">
            <span>{{ t('适用房型') }}</span
            ><span>{{ form.rooms.join('、') || '—' }}</span>
          </div>
          <div class="row">
            <span>{{ t('有效期') }}</span
            ><span>{{ fmtDt(form.valid_from) }} ~ {{ fmtDt(form.valid_to) }}</span>
          </div>
          <div class="row">
            <span>{{ t('批次号') }}}</span><span>{{ form.batch_no }}</span>
          </div>
        </div>
        <div class="note ok">
          {{
            t(
              '✅ 创建后生成唯一批次号；券实例按「每人限领」发放。「创建并投放」进入进行中。券与活动解耦，活动可后续绑定本批次。',
            )
          }}
        </div>
      </div>
    </div>

    <div class="wz-foot">
      <button
        type="button"
        class="btn"
        :style="{ visibility: step > 1 ? 'visible' : 'hidden' }"
        @click="go(-1)"
      >
        {{ t('← 上一步') }}
      </button>
      <div class="foot-actions">
        <button type="button" class="btn" :disabled="busy" @click="emit('create', false)">
          {{ t('存草稿') }}
        </button>
        <button type="button" class="btn pri" :disabled="busy" @click="go(1)">
          {{ step === 4 ? t('✅ 创建并投放') : t('下一步 →') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './coupons-shared.css';
</style>
