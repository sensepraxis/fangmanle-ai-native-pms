<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
/**
 * 私域运营壳层 · 企业微信三级菜单
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AcquisitionOpsNav from '../../components/AcquisitionOpsNav.vue'
import MktHomePanel from './MktHomePanel.vue'
import MktCouponsPanel from './MktCouponsPanel.vue'
import MktLandingPanel from './MktLandingPanel.vue'
import MktMembersPanel from './MktMembersPanel.vue'
import MktPointsPanel from './MktPointsPanel.vue'

const route = useRoute()

const section = computed(() => {
  const p = route.path.replace(/\/+$/, '')
  if (p.endsWith('/coupons') || p.endsWith('/automation')) return 'coupons'
  if (p.endsWith('/landing-pages')) return 'landing'
  if (p.endsWith('/members')) return 'members'
  if (p.endsWith('/points')) return 'points'
  if (p.endsWith('/ads') || p.endsWith('/ai-seeding') || p.endsWith('/segments')) return 'home'
  return 'home'
})
</script>

<template>
  <div class="page">
    <div class="shell-inner">
      <AcquisitionOpsNav />
      <MktHomePanel v-if="section === 'home'" />
      <MktCouponsPanel v-else-if="section === 'coupons'" />
      <MktLandingPanel v-else-if="section === 'landing'" />
      <MktMembersPanel v-else-if="section === 'members'" />
      <MktPointsPanel v-else-if="section === 'points'" />
      <MktHomePanel v-else />
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  padding: 16px 16px 32px;
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
  background: transparent;
  flex: 1;
  min-height: 0;
}
.shell-inner {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
</style>
