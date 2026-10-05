<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/** 系统配置 / 扩展能力 页内子导航（随当前路由只显示本组） */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { hasMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()
const localeTick = ref(0)
function onLocale() {
  localeTick.value++
}
onMounted(() => window.addEventListener('fml:locale', onLocale))
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))

/** Extensions：Map / LLM / 私域通道 —— 对应 src/extensions */
const EXT_LINKS = [
  {
    label: '大语言模型',
    path: '/a-ai-core/ai-system-configuration',
    icon: 'psychology',
    menu: 'menu.system.llm',
  },
  { label: '地图配置', path: '/a-ai-core/map-config', icon: 'map', menu: 'menu.system.map' },
  { label: '私域通道', path: '/a-ai-core/private-channel', icon: 'hub', menu: 'menu.system.wecom' }, // menu key 历史兼容；国内外通用
]

/** System 参数：财务 / 房型 / 房间 / 用户 / RBAC */
const PARAM_LINKS = [
  {
    label: '财务参数',
    path: '/a-ai-core/finance-params-float-carry',
    icon: 'payments',
    menu: 'menu.system.finance_params',
  },
  {
    label: '房型管理',
    path: '/a-ai-core/room-type-management',
    icon: 'meeting_room',
    menu: 'menu.system.room_types',
  },
  {
    label: '房间档案',
    path: '/a-ai-core/room-master',
    icon: 'door_front',
    menu: 'menu.system.room_master',
  },
  { label: '用户与账号', path: '/a-ai-core/users', icon: 'group', menu: 'menu.system.users' },
  {
    label: '角色权限',
    path: '/a-ai-core/rbac',
    icon: 'admin_panel_settings',
    menu: 'menu.system.rbac',
  },
]

const EXT_PATHS = new Set([
  '/a-ai-core/ai-system-configuration',
  '/a-ai-core/map-config',
  '/a-ai-core/private-channel',
  '/a-ai-core/wecom-integration',
])

const isExtensions = computed(() => {
  const cur = (route.path || '').replace(/\/+$/, '')
  return EXT_PATHS.has(cur)
})

const navAria = computed(() => {
  localeTick.value
  return isExtensions.value ? t('nav.extensions') : t('nav.system')
})

const links = computed(() => {
  localeTick.value
  const src = isExtensions.value ? EXT_LINKS : PARAM_LINKS
  return src.filter((l) => hasMenu(l.menu)).map((l) => ({ ...l, title: t(l.label) }))
})

function isActive(path: string) {
  const cur = (route.path || '').replace(/\/+$/, '')
  if (path === '/a-ai-core/finance-params-float-carry') {
    return cur === path || cur === '/a-ai-core/ota-commission'
  }
  if (path === '/a-ai-core/private-channel') {
    return cur === path || cur === '/a-ai-core/wecom-integration'
  }
  return cur === path
}
</script>

<template>
  <div class="sys-nav-wrap">
    <nav v-if="links.length" class="sys-nav" :aria-label="navAria">
      <button
        v-for="l in links"
        :key="l.path"
        type="button"
        class="sys-nav-btn"
        :class="{ active: isActive(l.path) }"
        @click="router.push(l.path)"
      >
        <span class="material-symbols-outlined">{{ l.icon }}</span>
        {{ l.title }}
      </button>
    </nav>
  </div>
</template>

<style scoped>
.sys-nav-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  margin: 0 0 16px;
}
.sys-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  padding: 0;
}
.sys-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c9ced8);
  background: var(--surface-container-lowest, #fff);
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.sys-nav-btn .material-symbols-outlined {
  font-size: 18px;
}
.sys-nav-btn:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.sys-nav-btn.active {
  border-color: var(--primary, #005bbf);
  background: rgba(0, 91, 191, 0.08);
  color: var(--primary, #005bbf);
}
</style>
