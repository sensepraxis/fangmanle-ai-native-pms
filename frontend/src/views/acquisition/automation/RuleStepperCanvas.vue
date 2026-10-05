<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { CUSTOM, EVENTS, OP_LABEL, PRESETS, type useAutoRuleForm } from './useAutoRuleForm'
import type { useAutoRuleApi } from './useAutoRuleApi'

const props = defineProps<{
  formApi: ReturnType<typeof useAutoRuleForm>
  ruleApi: ReturnType<typeof useAutoRuleApi>
}>()

const {
  step,
  form,
  paramPick,
  fieldOptions,
  activeCoupons,
  summaryText,
  onParamModeChange,
  selectEvent,
  goto,
  gotoNextFromStep1,
  fieldMeta,
  onFilterFieldChange,
  clearFilters,
  filterHumanSummary,
  addFilter,
  removeFilter,
  addCoupon,
  removeCoupon,
  couponInfo,
} = props.formApi

const { busy, preview, fmtNum, save, refreshPreview } = props.ruleApi
</script>

<template>
  <section class="card">
    <h3>{{ t('规则画布') }}</h3>
    <div class="stepper">
      <button
        v-for="s in 6"
        :key="s"
        type="button"
        class="step"
        :class="{ active: step === s, done: step > s }"
        @click="goto(s)"
      >
        <span class="n">{{ s }}</span>
        {{
          [t('选触发器'), t('客户条件'), t('选择券'), t('防骚扰'), t('实时预览'), t('启用')][s - 1]
        }}
      </button>
    </div>

    <!-- Step1 -->
    <div v-show="step === 1" class="step-panel">
      <div class="step-title">{{ t('选触发器') }}</div>
      <div class="event-grid">
        <button
          v-for="ev in EVENTS"
          :key="ev.key"
          type="button"
          class="ev-card"
          :class="{ on: form.event_type === ev.key }"
          @click="selectEvent(ev.key)"
        >
          <div class="ico">{{ ev.ico }}</div>
          <div class="nm">{{ t(ev.nm) }}</div>
          <div class="meta">
            <span
              class="pill"
              :class="ev.pill === '实时' ? 'g' : ev.pill === '指定日' ? 'o' : 'b'"
              >{{ t(ev.pill) }}</span
            >
          </div>
        </button>
      </div>
      <div class="evt-params">
        <template v-if="form.event_type === 'REG_DAYS'">
          <label>{{ t('注册满') }}</label>
          <select v-model="paramPick.reg_days.mode" @change="onParamModeChange('reg_days')">
            <option v-for="d in PRESETS.reg_days" :key="d" :value="d">{{ d }} {{ t('天') }}</option>
            <option :value="CUSTOM">{{ t('自定义') }}</option>
          </select>
          <template v-if="paramPick.reg_days.mode === CUSTOM">
            <input
              v-model="paramPick.reg_days.custom"
              class="custom-num"
              type="text"
              inputmode="numeric"
              maxlength="4"
            />
            <span class="unit">{{ t('天') }}</span>
          </template>
        </template>
        <template v-else-if="form.event_type === 'CHECKOUT_DAYS'">
          <label>{{ t('退房后') }}</label>
          <select
            v-model="paramPick.checkout_days.mode"
            @change="onParamModeChange('checkout_days')"
          >
            <option v-for="d in PRESETS.checkout_days" :key="d" :value="d">
              {{ d }} {{ t('天') }}
            </option>
            <option :value="CUSTOM">{{ t('自定义') }}</option>
          </select>
          <template v-if="paramPick.checkout_days.mode === CUSTOM">
            <input
              v-model="paramPick.checkout_days.custom"
              class="custom-num"
              type="text"
              inputmode="numeric"
              maxlength="4"
            />
            <span class="unit">{{ t('天') }}</span>
          </template>
        </template>
        <template v-else-if="form.event_type === 'SILENT_DAYS'">
          <label>{{ t('沉默 ≥') }}</label>
          <select v-model="paramPick.silent_days.mode" @change="onParamModeChange('silent_days')">
            <option v-for="d in PRESETS.silent_days" :key="d" :value="d">
              {{ d }} {{ t('天') }}
            </option>
            <option :value="CUSTOM">{{ t('自定义') }}</option>
          </select>
          <template v-if="paramPick.silent_days.mode === CUSTOM">
            <input
              v-model="paramPick.silent_days.custom"
              class="custom-num"
              type="text"
              inputmode="numeric"
              maxlength="4"
            />
            <span class="unit">{{ t('天') }}</span>
          </template>
        </template>
        <template v-else-if="form.event_type === 'BIRTHDAY'">
          <label>{{ t('提前') }}</label>
          <select v-model="paramPick.ahead_days.mode" @change="onParamModeChange('ahead_days')">
            <option v-for="d in PRESETS.ahead_days" :key="d" :value="d">
              {{ d }} {{ t('天') }}
            </option>
            <option :value="CUSTOM">{{ t('自定义') }}</option>
          </select>
          <template v-if="paramPick.ahead_days.mode === CUSTOM">
            <input
              v-model="paramPick.ahead_days.custom"
              class="custom-num"
              type="text"
              inputmode="numeric"
              maxlength="4"
            />
            <span class="unit">{{ t('天') }}</span>
          </template>
        </template>
        <template v-else-if="form.event_type === 'HOLIDAY'">
          <label>{{ t('节日') }}</label>
          <select v-model="form.event_params.holiday">
            <option value="national_day">{{ t('国庆节') }}</option>
            <option value="mid_autumn">{{ t('中秋节') }}</option>
            <option value="spring">{{ t('春节') }}</option>
            <option value="new_year">{{ t('元旦') }}</option>
          </select>
        </template>
        <template v-else-if="form.event_type === 'HIGH_VALUE_NEW'">
          <label>{{ t('单价 ≥') }}</label>
          <select
            v-model="paramPick.min_avg_order.mode"
            @change="onParamModeChange('min_avg_order')"
          >
            <option v-for="d in PRESETS.min_avg_order" :key="d" :value="d">
              {{ d }} {{ t('元') }}
            </option>
            <option :value="CUSTOM">{{ t('自定义') }}</option>
          </select>
          <template v-if="paramPick.min_avg_order.mode === CUSTOM">
            <input
              v-model="paramPick.min_avg_order.custom"
              class="custom-num"
              type="text"
              inputmode="numeric"
              maxlength="6"
            />
            <span class="unit">{{ t('元') }}</span>
          </template>
        </template>
        <template v-else-if="form.event_type === 'CUSTOM'">
          <label>{{ t('事件 key') }}</label>
          <input v-model="form.event_params.event_key" type="text" />
        </template>
      </div>
      <div class="step-bar">
        <button type="button" class="btn" :disabled="busy" @click="save(true)">
          {{ t('存草稿') }}
        </button>
        <button type="button" class="btn pri" @click="gotoNextFromStep1">{{ t('下一步') }}</button>
      </div>
    </div>

    <!-- Step2 -->
    <div v-show="step === 2" class="step-panel">
      <div class="step-title">{{ t('客户条件') }}</div>

      <div v-if="!form.filters.length" class="filter-empty">{{ t('暂无条件') }}</div>

      <div v-else class="filter-list">
        <div v-for="(f, i) in form.filters" :key="i" class="fblock">
          <div class="frow">
            <div class="logic">
              {{
                i === 0 || f.group_id !== form.filters[i - 1]?.group_id
                  ? i === 0
                    ? t('当')
                    : t('或')
                  : t('且')
              }}
            </div>
            <select v-model="f.field" @change="onFilterFieldChange(f)">
              <option v-for="fd in fieldOptions" :key="fd.key" :value="fd.key">
                {{ t(fd.label) }}
              </option>
            </select>
            <select v-model="f.op">
              <option v-for="op in fieldMeta(f.field)?.ops || ['=']" :key="op" :value="op">
                {{ t(OP_LABEL[op] || op) }}
              </option>
            </select>
            <select v-if="fieldMeta(f.field)?.type === 'bool'" v-model="f.value">
              <option :value="1">{{ t('是') }}</option>
              <option :value="0">{{ t('否') }}</option>
            </select>
            <select v-else-if="fieldMeta(f.field)?.enum" v-model="f.value">
              <option v-for="e in fieldMeta(f.field).enum" :key="e" :value="e">{{ t(e) }}</option>
            </select>
            <input v-else v-model="f.value" type="text" inputmode="numeric" />
            <button type="button" class="del" @click="removeFilter(i)">×</button>
          </div>
        </div>
      </div>

      <div class="add-filter">
        <button type="button" class="small" @click="addFilter(false)">{{ t('+ 条件') }}</button>
        <button type="button" class="small" @click="addFilter(true)">{{ t('+ 条件组') }}</button>
      </div>

      <div class="step-bar">
        <button type="button" class="btn" @click="goto(1)">{{ t('上一步') }}</button>
        <button type="button" class="btn" @click="clearFilters">{{ t('跳过') }}</button>
        <button type="button" class="btn pri" @click="goto(3)">{{ t('下一步') }}</button>
      </div>
    </div>

    <!-- Step3 -->
    <div v-show="step === 3" class="step-panel">
      <div class="step-title">{{ t('选择券') }}</div>
      <div v-for="(c, i) in form.coupons" :key="i" class="cp-row">
        <div class="prio">{{ c.priority || i + 1 }}</div>
        <div class="info">
          <select v-model.number="c.batch_id" class="batch-sel">
            <option v-for="b in activeCoupons" :key="b.id" :value="b.id">
              {{ b.name }}（{{ b.batch_no }}）
            </option>
          </select>
        </div>
        <div class="stock">
          {{ t('剩余') }}
          <b>{{
            Math.max(
              0,
              (couponInfo(c.batch_id)?.total_qty || 0) - (couponInfo(c.batch_id)?.granted_qty || 0),
            )
          }}</b>
          / {{ couponInfo(c.batch_id)?.total_qty || 0 }}
        </div>
        <button type="button" class="btn ghost" @click="removeCoupon(i)">{{ t('移除') }}</button>
      </div>
      <button type="button" class="btn ghost" @click="addCoupon">{{ t('+ 添加券批次') }}</button>
      <div class="step-bar">
        <button type="button" class="btn" @click="goto(2)">{{ t('上一步') }}</button>
        <button type="button" class="btn pri" @click="goto(4)">{{ t('下一步') }}</button>
      </div>
    </div>

    <!-- Step4 -->
    <div v-show="step === 4" class="step-panel">
      <div class="step-title">{{ t('防骚扰') }}</div>
      <div class="limit-grid">
        <div class="limit-card">
          <div class="lbl">{{ t('每人每天上限') }}</div>
          <div class="desc">
            {{ t('同一客人，今天最多被这条规则发几张券。填 1 就是一天一张，避免连发刷屏。') }}
          </div>
          <div class="ctrl">
            <input v-model.number="form.max_per_customer_day" type="number" min="1" max="10" />
            <span class="unit">{{ t('张 / 人 / 天') }}</span>
          </div>
        </div>
        <div class="limit-card">
          <div class="lbl">{{ t('规则冷却期') }}</div>
          <div class="desc">
            {{
              t(
                '同一客人被这条规则发过之后，要隔多少天才能再发。比如填 30，一个月内不会重复收到同一条规则的券。',
              )
            }}
          </div>
          <div class="ctrl">
            <input v-model.number="form.rule_cooldown_days" type="number" min="0" />
            <span class="unit">{{ t('天') }}</span>
          </div>
        </div>
        <div class="limit-card">
          <div class="lbl">{{ t('全局沉默期') }}</div>
          <div class="desc">
            {{
              t(
                '不管哪条规则，只要客人最近刚领过任何券，这几天就先别再发。避免今天欢迎礼、明天又召回券，把人吵烦了。',
              )
            }}
          </div>
          <div class="ctrl">
            <input v-model.number="form.global_silence_days" type="number" min="0" />
            <span class="unit">{{ t('天') }}</span>
          </div>
        </div>
        <div class="limit-card">
          <div class="lbl">{{ t('触发时段') }}</div>
          <div class="desc">
            {{ t('只在这段时间里发券，比如 09:00–21:00。半夜不会打扰客人。') }}
          </div>
          <div class="ctrl">
            <input v-model="form.active_window_start" type="time" />
            <span>~</span>
            <input v-model="form.active_window_end" type="time" />
          </div>
        </div>
      </div>
      <div class="step-bar">
        <button type="button" class="btn" @click="goto(3)">{{ t('上一步') }}</button>
        <button type="button" class="btn pri" @click="goto(5)">{{ t('下一步') }}</button>
      </div>
    </div>

    <!-- Step5 -->
    <div v-show="step === 5" class="step-panel">
      <div class="step-title">
        {{ t('实时预览')
        }}<button type="button" class="link" @click="refreshPreview">{{ t('刷新') }}</button>
      </div>
      <div v-if="preview" class="prev-hero">
        <div class="row">
          <div>
            <div class="big">
              {{ fmtNum(preview.estimated_daily) }}<span class="unit">{{ t('张 / 日') }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="preview" class="prev-stat">
        <div class="box">
          <div class="l">{{ t('每日触发') }}</div>
          <div class="v">{{ fmtNum(preview.event_daily_freq) }}</div>
        </div>
        <div class="box">
          <div class="l">{{ t('条件通过率') }}</div>
          <div class="v">{{ ((preview.condition_pass_rate || 0) * 100).toFixed(1) }}%</div>
        </div>
        <div class="box">
          <div class="l">{{ t('防骚扰通过') }}</div>
          <div class="v">{{ ((preview.antiharass_pass_rate || 0) * 100).toFixed(0) }}%</div>
        </div>
      </div>
      <div v-if="preview?.samples?.length" class="push-preview">
        <div v-for="(s, i) in preview.samples" :key="i" class="pp-card">
          <div class="ph" />
          <div class="ph2">
            <div class="name">{{ s.name }}</div>
            <span class="coupon">{{ s.coupon }}</span>
          </div>
        </div>
      </div>
      <div class="step-bar">
        <button type="button" class="btn" @click="goto(4)">{{ t('上一步') }}</button>
        <button type="button" class="btn pri" @click="goto(6)">{{ t('下一步') }}</button>
      </div>
    </div>

    <!-- Step6 -->
    <div v-show="step === 6" class="step-panel">
      <div class="step-title">{{ t('启用') }}</div>
      <label class="field-name">
        <span>{{ t('规则名称') }}</span>
        <input v-model="form.name" />
      </label>
      <div class="sample-list">
        <b>{{ t('触发器：') }}</b> {{ summaryText.event }}<br />
        <b>{{ t('客户条件：') }}</b> {{ filterHumanSummary() }}<br />
        <b>{{ t('券批次：') }}</b> {{ summaryText.coupons }}<br />
        <b>{{ t('防骚扰：') }}</b> {{ summaryText.anti }}
      </div>
      <label class="chk">
        <input v-model="form.enable_now" type="checkbox" />{{ t('保存后立即启用') }}</label
      >
      <div class="step-bar">
        <button type="button" class="btn" @click="goto(5)">{{ t('上一步') }}</button>
        <button type="button" class="btn" :disabled="busy" @click="save(true)">
          {{ t('存草稿') }}
        </button>
        <button type="button" class="btn pri" :disabled="busy" @click="save(false)">
          {{ form.enable_now ? t('保存并启用') : t('保存') }}
        </button>
      </div>
    </div>
  </section>
</template>
