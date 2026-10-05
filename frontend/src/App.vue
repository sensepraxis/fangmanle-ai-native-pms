<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import CustomerFlowNav from './components/CustomerFlowNav.vue'
import AnalyticsDomainNav from './components/AnalyticsDomainNav.vue'
import { hotelStore, initHotel, refreshRbac } from './store/hotel'
import { rbacStore } from './store/rbac'
import { api } from './lib/api'
import { applyBranding } from './lib/branding'

const route = useRoute()
const isLogin = computed(() => route.path === '/login' || route.name === 'login')
const isLanding = computed(() => route.path === '/' || route.name === 'landing')
const isWecomSidebar = computed(() => route.path.startsWith('/wecom/'))
/** 未登录 / 营销首页不渲染业务壳，避免闪一下内容页 */
const showApp = computed(
  () =>
    !isLogin.value &&
    !isLanding.value &&
    !isWecomSidebar.value &&
    !!hotelStore.token &&
    rbacStore.loaded,
)

initHotel()

function onFocus() {
  if (!isLogin.value && !isLanding.value && hotelStore.token) refreshRbac()
}

onMounted(async () => {
  window.addEventListener('focus', onFocus)
  try {
    const b = await api.branding()
    if (b) applyBranding(b)
  } catch {
    /* ignore */
  }
})
onUnmounted(() => window.removeEventListener('focus', onFocus))
</script>

<template>
  <div v-if="isLogin || isLanding || isWecomSidebar" class="login-only">
    <RouterView />
  </div>
  <div v-else-if="showApp" class="app">
    <Sidebar />
    <div class="main">
      <TopBar />
      <div class="stage">
        <CustomerFlowNav />
        <AnalyticsDomainNav />
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </div>
    </div>
  </div>
  <div v-else class="login-only auth-wait">
    <RouterView />
  </div>
</template>

<style scoped>
.login-only {
  min-height: 100vh;
}
</style>
