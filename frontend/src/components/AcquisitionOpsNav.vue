<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 私域运营 · 企业微信三级菜单
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { filterByMenu, hasMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()

const WECOM_TABS_ALL = [
  {
    key: 'home',
    label: t('私域总览'),
    icon: 'dashboard',
    path: '/acquisition',
    menu: 'menu.mkt.overview',
  },
  {
    key: 'coupons',
    label: t('优惠券中心'),
    icon: 'confirmation_number',
    path: '/acquisition/coupons',
    menu: 'menu.mkt.coupons',
  },
  {
    key: 'landing',
    label: t('页面装修器'),
    icon: 'web',
    path: '/acquisition/landing-pages',
    menu: 'menu.mkt.landing',
  },
  {
    key: 'members',
    label: t('会员体系设置'),
    icon: 'workspace_premium',
    path: '/acquisition/members',
    menu: 'menu.mkt.members',
  },
  {
    key: 'points',
    label: t('积分规则'),
    icon: 'toll',
    path: '/acquisition/points',
    menu: 'menu.mkt.points',
  },
]

const WECOM_TABS = computed(() => filterByMenu(WECOM_TABS_ALL))
const showAcquisition = computed(() =>
  [
    'menu.mkt.overview',
    'menu.mkt.coupons',
    'menu.mkt.landing',
    'menu.mkt.members',
    'menu.mkt.points',
  ].some(hasMenu),
)

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isWecomTabActive(path: string) {
  const cur = normalize(route.path)
  const target = normalize(path)
  if (target === '/acquisition') {
    return cur === '/acquisition'
  }
  return cur === target || cur.startsWith(target + '/')
}

const activeWecomPath = computed(
  () => WECOM_TABS.value.find((tab) => isWecomTabActive(tab.path))?.path || '',
)

function goWecomTab(path: string) {
  router.push(path)
}
</script>

<template>
  <div v-if="showAcquisition" class="acq-nav-stack">
    <nav class="acq-ops-nav" :aria-label="t('企业微信')">
      <button
        v-for="tab in WECOM_TABS"
        :key="tab.path"
        type="button"
        class="tab"
        :class="{ on: activeWecomPath === tab.path }"
        @click="goWecomTab(tab.path)"
      >
        <span class="material-symbols-outlined">{{ tab.icon }}</span>
        {{ t(tab.label) }}
      </button>
    </nav>
  </div>
</template>

<style scoped>
.acq-nav-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}
.acq-ops-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 9px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
}
.tab .material-symbols-outlined {
  font-size: 18px;
}
.tab:hover {
  background: #fff;
  color: #1f2329;
}
.tab.on {
  background: #1f2329;
  color: #fff;
}
</style>
