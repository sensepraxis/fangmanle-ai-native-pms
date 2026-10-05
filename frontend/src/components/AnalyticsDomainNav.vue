<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 经营分析域二级树导航（文档 IA）
 * 经营分析 → 订单健康 / 渠道洞察 / 营销归因 / 收益概览 → 具体页
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ANALYTICS_PATH,
  ANALYTICS_TREE,
  findAnalyticsBranch,
  findAnalyticsLeaf,
  isAnalyticsDomain,
} from '../lib/analyticsNav'

const route = useRoute()
const router = useRouter()

const show = computed(() => {
  // 总览页与 AI助手不展示树导航；仅详情页显示「返回总览 + 兄弟入口」
  if (route.path === ANALYTICS_PATH) return false
  if (route.path === '/ai' || route.path.startsWith('/ai/')) return false
  return isAnalyticsDomain(route.path)
})
const activeBranch = computed(() => findAnalyticsBranch(route.path))
const activeLeaf = computed(() => findAnalyticsLeaf(route.path))

function go(path: string) {
  router.push(path)
}

function branchActive(b: (typeof ANALYTICS_TREE)[0]) {
  return activeBranch.value?.key === b.key
}

function leafActive(path: string) {
  return route.path === path
}
</script>

<template>
  <nav v-if="show" class="an-domain" :aria-label="t('经营分析导航')">
    <div class="an-domain-inner">
      <button
        type="button"
        class="home"
        :class="{ on: route.path === ANALYTICS_PATH }"
        @click="go(ANALYTICS_PATH)"
      >
        <span class="material-symbols-outlined">monitoring</span>
        <span>{{ t('经营分析') }}</span>
      </button>

      <div class="tree">
        <div
          v-for="b in ANALYTICS_TREE"
          :key="b.key"
          class="branch"
          :class="{ open: branchActive(b) }"
        >
          <button
            type="button"
            class="branch-btn"
            :class="{ on: branchActive(b) }"
            @click="go(b.leaves[0]?.path || b.path)"
          >
            <span class="material-symbols-outlined">{{ b.icon }}</span>
            <span class="branch-text">
              <span class="branch-title">{{ t(b.title) }}</span>
              <span class="branch-sub">{{ t(b.subtitle) }}</span>
            </span>
          </button>
          <div v-if="branchActive(b)" class="leaves">
            <button
              v-for="leaf in b.leaves"
              :key="leaf.key"
              type="button"
              class="leaf-btn"
              :class="{ on: leafActive(leaf.path), muted: leaf.muted }"
              @click="go(leaf.path)"
            >
              <span class="dot" />
              <span>{{ t(leaf.title) }}</span>
              <span v-if="leaf.badge" class="badge" :class="{ dim: leaf.muted }">{{
                t(leaf.badge)
              }}</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="activeLeaf" class="crumb">
        {{ activeBranch ? t(activeBranch.title) : '' }}
        <span class="sep">/</span>
        {{ t(activeLeaf.title) }}
      </div>
    </div>
  </nav>
</template>

<style scoped>
.an-domain {
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  background: #fafbfc;
}
.an-domain-inner {
  padding: 10px 20px 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 12px 16px;
}
.home {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  color: #1f2329;
}
.home.on,
.home:hover {
  border-color: #c4b5fd;
  background: #faf5ff;
  color: #6d28d9;
}
.home .material-symbols-outlined {
  font-size: 18px;
}
.tree {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.branch {
  min-width: 160px;
}
.branch-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
}
.branch-btn:hover {
  background: #fff;
  border-color: #e2e8f0;
}
.branch-btn.on {
  background: #fff;
  border-color: #c4b5fd;
  box-shadow: 0 1px 4px rgba(109, 40, 217, 0.08);
}
.branch-btn .material-symbols-outlined {
  font-size: 20px;
  color: #7c3aed;
}
.branch-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.branch-title {
  font-size: 13px;
  font-weight: 700;
  color: #1f2329;
}
.branch-sub {
  font-size: 11px;
  color: #6b7280;
}
.leaves {
  margin: 4px 0 0 28px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.leaf-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
  text-align: left;
}
.leaf-btn:hover {
  background: #f3e8ff;
  color: #6d28d9;
}
.leaf-btn.on {
  background: #ede9fe;
  color: #5b21b6;
  font-weight: 700;
}
.leaf-btn.muted {
  color: #94a3b8;
}
.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.5;
  flex-shrink: 0;
}
.badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: #ede9fe;
  color: #6d28d9;
}
.badge.dim {
  background: #e2e8f0;
  color: #64748b;
}
.crumb {
  width: 100%;
  font-size: 12px;
  color: #6b7280;
}
.sep {
  margin: 0 4px;
  color: #cbd5e1;
}
@media (min-width: 1100px) {
  .an-domain-inner {
    padding: 12px 24px 14px;
  }
}
</style>
