<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, getLocale } from '../../lib/i18n'

import { useRouter } from 'vue-router'
import { fmt } from '../../lib/ui'
import OneIdAuditPanel from '../../components/OneIdAuditPanel.vue'

defineProps<{
  g: any
  vipLabel: string
  churnPct: number
  inWecomPrivate: boolean
  wecomBound: boolean
  wecomExternalId: string
  wecom: any
  phoneDisplay: string
  stayCount: number
  tags: any[]
  h5Membership: any
  oneidExpanded: boolean
  oneIdLabel: string
  channelCount: number
  mergeConfidence: number
  channelChips: string[]
  avgTicket: number
  ltvScore: string
  nextStay: any
  nextStayNights: number
}>()

const emit = defineEmits<{
  care: []
  'toggle-oneid': []
}>()

const router = useRouter()
</script>

<template>
  <header class="hero">
    <div class="hero-top">
      <div class="avatar-wrap">
        <div class="avatar">{{ (g.name || '?').slice(0, 1) }}</div>
        <span class="online" />
      </div>
      <div class="hero-main">
        <div class="title-row">
          <div class="title-left">
            <h1 class="name">{{ g.name }}</h1>
            <span class="vip">{{ vipLabel }}{{ t('贵宾') }}</span>
            <span
              v-if="Number(g.ltv) >= 5000"
              class="status-badge hi"
              :title="t('累计 LTV ≥ ¥5,000')"
              >{{ t('高价值') }}</span
            >
            <span class="ai-badge">{{ t('AI 已核验') }}</span>
            <span
              v-if="inWecomPrivate"
              class="ai-badge wecom-badge"
              :title="t('已扫码/加过企业微信 → 可企微触达')"
              >{{ t('私域客户') }}</span
            >
            <span
              v-else
              class="ai-badge wecom-badge off"
              :title="t('尚未扫码加企微，企微推送不可达')"
              >{{ t('非私域客户') }}</span
            >
            <span
              v-if="churnPct >= 45"
              class="status-badge risk"
              role="button"
              :title="t('流失风险偏高，点击发送关怀')"
              @click="emit('care')"
              >{{ t('流失预警') }}</span
            >
          </div>
        </div>
        <p class="meta">
          {{ phoneDisplay }}
          <span v-if="(g.alias_names || []).length">
            · {{ t('其他名字') }}
            {{ (g.alias_names || []).join(getLocale() === 'en' ? ', ' : '、') }}</span
          >
          <span v-if="wecomExternalId" class="wecom-id" :title="wecomExternalId">
            · {{ t('企微') }}ID
            {{
              wecomExternalId.length > 18
                ? wecomExternalId.slice(0, 10) + '…' + wecomExternalId.slice(-6)
                : wecomExternalId
            }}</span
          >
          <span v-if="g.city"> · {{ g.city }}</span>
          · {{ stayCount }} {{ t('次入住') }}
        </p>
        <div v-if="tags.length" class="tags">
          <button
            v-for="tag in tags.slice(0, 4)"
            :key="tag.name"
            type="button"
            class="tag tag-btn"
            :title="`${t('查看标签配置：')}${t(String(tag.name || ''))}`"
            @click="router.push('/b-data/master-tag-library')"
          >
            {{ t(String(tag.name || '')) }}
          </button>
        </div>
        <div v-if="h5Membership && inWecomPrivate" class="h5-member-card">
          <div class="h5-head">
            <span class="h5-badge">{{ t('企微私域') }}</span>
          </div>
          <div class="h5-grid">
            <div class="h5-item">
              <div class="h5-k">{{ h5Membership.labels?.level || t('私域会员等级') }}</div>
              <div class="h5-v">{{ h5Membership.level_name || h5Membership.level_code }}</div>
            </div>
            <div class="h5-item">
              <div class="h5-k">{{ h5Membership.labels?.points || t('私域积分') }}</div>
              <div class="h5-v">{{ h5Membership.points_balance ?? 0 }}</div>
            </div>
          </div>
          <div v-if="h5Membership.progress" class="h5-progress">
            {{ t('距') }} {{ h5Membership.progress.next_level_name || t('下一等级') }}：
            {{ h5Membership.progress.current }}/{{ h5Membership.progress.need }} （{{
              h5Membership.progress.pct
            }}%）
          </div>
        </div>
      </div>
    </div>

    <div class="hero-nav">
      <div class="hero-actions">
        <button v-if="wecomBound" type="button" class="btn-hero primary" @click="emit('care')">
          <span class="material-symbols-outlined text-[18px]">volunteer_activism</span>
          {{ t('发送关怀') }}
        </button>
        <button
          type="button"
          class="btn-hero"
          @click="router.push('/b-data/global-guest-directory')"
        >
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('返回全景') }}
        </button>
      </div>
    </div>

    <div class="oneid-bar" :class="{ expanded: oneidExpanded }">
      <div class="oneid-bar-head">
        <div class="oneid-left">
          <div class="oneid-ico" :title="t('统一身份')">
            <span class="material-symbols-outlined">fingerprint</span>
          </div>
          <div class="oneid-text">
            <div class="oneid-title-row">
              <span class="oneid-k">{{ t('OneID 统一身份') }}</span>
              <span class="oneid-id">{{ oneIdLabel }}</span>
              <span class="oneid-ok">
                <span class="material-symbols-outlined text-[14px]">verified</span>
                {{ t('已归并') }} {{ channelCount }} {{ t('渠道') }}</span
              >
              <span class="oneid-conf">{{ t('置信度') }} {{ mergeConfidence }}%</span>
            </div>
            <div class="oneid-chips">
              <span v-for="c in channelChips" :key="c" class="oneid-chip">{{ c }}</span>
            </div>
            <p v-if="wecomBound && wecomExternalId" class="oneid-wecom-id">
              <span class="material-symbols-outlined text-[14px]">chat</span>
              {{ t('企微外部联系人ID：') }} <code>{{ wecomExternalId }}</code>
              <span v-if="wecom?.follow_userid">
                · {{ t('跟进人') }} {{ wecom.follow_userid }}</span
              >
              <span v-if="wecom?.linked_at">
                · {{ t('建联') }} {{ String(wecom.linked_at).slice(0, 16) }}</span
              >
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn-hero oneid-toggle"
          :aria-expanded="oneidExpanded"
          @click="emit('toggle-oneid')"
        >
          <span class="material-symbols-outlined">{{
            oneidExpanded ? 'expand_less' : 'expand_more'
          }}</span>
          {{ oneidExpanded ? t('收起归并审计') : t('展开归并审计') }}
        </button>
      </div>
      <OneIdAuditPanel v-if="oneidExpanded" :guest-id="Number(g.id)" :guest-name="g.name" />
    </div>

    <div class="metrics">
      <div>
        <div class="ml">{{ t('总消费') }}</div>
        <div class="mv">{{ fmt(g.ltv) }}</div>
      </div>
      <div>
        <div class="ml">{{ t('入住次数') }}</div>
        <div class="mv">{{ stayCount }}</div>
      </div>
      <div>
        <div class="ml">{{ t('平均房价') }}</div>
        <div class="mv">{{ fmt(avgTicket) }}</div>
      </div>
      <div class="m-ai">
        <div class="ml">{{ t('AI LTV 评分') }}</div>
        <div class="mv text-tertiary">
          {{ ltvScore }}<span class="text-sm font-normal">/10</span>
        </div>
      </div>
      <div v-if="nextStay" class="m-next">
        <div class="ml">{{ t('即将入住') }}</div>
        <div class="mv-sm">{{ nextStay.check_in }} — {{ nextStay.check_out }}</div>
        <div class="ml">{{ nextStayNights }} {{ t('晚 ·') }} {{ nextStay.order_no }}</div>
      </div>
    </div>
  </header>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
