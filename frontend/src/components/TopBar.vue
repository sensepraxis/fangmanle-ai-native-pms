<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
/**
 * 全局顶栏：品牌标识 + 语言切换 + 通知/头像（点头像可登出）
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearSession, hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'
import { appName, appNameEn, logoUrl } from '../lib/branding'
import { getLocale, setLocale, t } from '../lib/i18n'

const router = useRouter()
const menuOpen = ref(false)
const locale = ref(getLocale())

const displayName = (() => {
  const u = hotelStore.user
  return u?.name || u?.username || t('common.manager')
})()

const avatarChar = displayName.trim().slice(0, 1) || 'M'
const brandLabel = () => (locale.value === 'en' ? appNameEn() || appName() : appName())

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function onDocClick(e: MouseEvent) {
  const el = e.target as HTMLElement | null
  if (!el?.closest?.('.tb-user') && !el?.closest?.('.tb-lang')) closeMenu()
}

function logout() {
  closeMenu()
  clearSession()
  toast(t('common.logged_out'))
  router.push('/login')
}

function switchLocale(next: 'zh-CN' | 'en') {
  setLocale(next)
  locale.value = next
  // 刷新当前视图文案（多数页用静态中文时需 reload 才全量生效；壳层已响应）
  window.location.reload()
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <header class="topbar">
    <div class="tb-brand">
      <img v-if="logoUrl()" class="tb-logo" :src="logoUrl()" alt="" />
      <span
        v-else
        class="material-symbols-outlined cottage"
        style="font-variation-settings: 'FILL' 1"
        >cottage</span
      >
      <span class="name">{{ brandLabel() }}</span>
    </div>

    <div class="top-actions">
      <div class="tb-lang" title="Language">
        <button
          type="button"
          class="lang-btn"
          :class="{ on: locale === 'zh-CN' }"
          @click="switchLocale('zh-CN')"
        >
          {{ t('中文') }}
        </button>
        <button
          type="button"
          class="lang-btn"
          :class="{ on: locale === 'en' }"
          @click="switchLocale('en')"
        >
          EN
        </button>
      </div>
      <button type="button" class="icon-btn" :title="t('common.notifications')">
        <span class="material-symbols-outlined">notifications</span>
      </button>
      <div class="tb-user">
        <button
          type="button"
          class="avatar"
          :title="displayName"
          :aria-expanded="menuOpen"
          aria-haspopup="menu"
          @click.stop="toggleMenu"
        >
          {{ avatarChar }}
        </button>
        <div v-if="menuOpen" class="tb-menu" role="menu">
          <div class="tb-menu-name">{{ displayName }}</div>
          <button type="button" class="tb-menu-item" role="menuitem" @click="logout">
            <span class="material-symbols-outlined">logout</span>
            {{ t('common.logout') }}
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.tb-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.tb-logo {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: 6px;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}
.tb-lang {
  display: inline-flex;
  border: 1px solid #d8dee6;
  border-radius: 999px;
  overflow: hidden;
}
.lang-btn {
  border: 0;
  background: transparent;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: #5b6b7c;
}
.lang-btn.on {
  background: #0f2742;
  color: #fff;
}
.icon-btn {
  border: 0;
  background: transparent;
  cursor: pointer;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 0;
  background: #143a5a;
  color: #fff;
  cursor: pointer;
}
.tb-user {
  position: relative;
}
.tb-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 160px;
  background: #fff;
  border: 1px solid #e6ebf0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 39, 66, 0.12);
  padding: 8px;
  z-index: 40;
}
.tb-menu-name {
  padding: 6px 8px;
  font-size: 12px;
  color: #5b6b7c;
}
.tb-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.tb-menu-item:hover {
  background: #f3f6f9;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #e6ebf0;
  background: #fff;
}
</style>
