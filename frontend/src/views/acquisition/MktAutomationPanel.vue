<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 基于规则自动发放 — 对照原型六步画布 + 四表 API
 * 壳层：embedded + KPI + 组合 composable / 子面板
 */
import { onMounted, ref, watch } from 'vue'
import { hotelStore } from '../../store/hotel'
import { FALLBACK_FIELDS, useAutoRuleForm } from './automation/useAutoRuleForm'
import { useAutoRuleApi } from './automation/useAutoRuleApi'
import RuleStepperCanvas from './automation/RuleStepperCanvas.vue'
import RuleListSidebar from './automation/RuleListSidebar.vue'
import DryRunBlock from './automation/DryRunBlock.vue'
import './automation/automation-shared.css'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

const fields = ref<any[]>([...FALLBACK_FIELDS])
const coupons = ref<any[]>([])
const preview = ref<any>(null)

let refreshPreview: () => void | Promise<void> = () => {}

const formApi = useAutoRuleForm({
  fields,
  coupons,
  preview,
  onGotoPreview: () => {
    void refreshPreview()
  },
})

const ruleApi = useAutoRuleApi(formApi, { fields, coupons, preview })
refreshPreview = ruleApi.refreshPreview

const { openNew } = formApi
const { kpi, statusCounts, fmtNum, load, openHistory } = ruleApi
const { form, step } = formApi

onMounted(load)
watch(() => hotelStore.hotelId, load)

watch(
  () => [form.filters, form.event_type, form.coupons],
  () => {
    if (step.value === 5) void ruleApi.refreshPreview()
  },
  { deep: true },
)
</script>

<template>
  <div class="ar-page" :class="{ embedded: props.embedded }">
    <div class="page-head">
      <div>
        <div v-if="!props.embedded" class="crumbs">
          {{ t('营销获客 /') }} <b>{{ t('优惠券中心') }}</b> {{ t('/ 基于规则自动发放') }}
        </div>
        <h2 v-if="!props.embedded" class="page-title">{{ t('基于规则自动发放') }}</h2>
      </div>
      <div class="page-actions">
        <button type="button" class="btn" @click="openHistory">{{ t('查看触发历史') }}</button>
        <button type="button" class="btn pri" @click="openNew">{{ t('+ 新建规则') }}</button>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi">
        <div class="lbl">{{ t('启用中规则') }}</div>
        <div class="val">
          {{ kpi.active_rules ?? statusCounts.active }}<span class="unit">{{ t('条') }}</span>
        </div>
      </div>
      <div class="kpi">
        <div class="lbl">{{ t('今日触发') }}</div>
        <div class="val">
          {{ fmtNum(kpi.today_triggers) }}<span class="unit">{{ t('次') }}</span>
        </div>
      </div>
      <div class="kpi">
        <div class="lbl">{{ t('今日发券') }}</div>
        <div class="val">
          {{ fmtNum(kpi.today_issued) }}<span class="unit">{{ t('张') }}</span>
        </div>
      </div>
      <div class="kpi">
        <div class="lbl">{{ t('7 日触达') }}</div>
        <div class="val">
          {{ fmtNum(kpi.reach_7d) }}<span class="unit">{{ t('人') }}</span>
        </div>
      </div>
    </div>

    <div class="main-grid">
      <RuleStepperCanvas :form-api="formApi" :rule-api="ruleApi" />
      <section class="card right">
        <RuleListSidebar :rule-api="ruleApi" />
        <DryRunBlock :form-api="formApi" :rule-api="ruleApi" />
      </section>
    </div>
  </div>
</template>
