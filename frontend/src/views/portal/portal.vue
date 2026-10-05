<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 原型导航门户 —— 忠实重做自 index.html 的 body 结构
// 数据由 api.demo('workflow') 兜底返回（分类树 + 统计 + 页清单）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// —— 数据契约（与 api.demo('workflow') 返回结构对齐）——
interface PortalPage {
  name: string
  title: string
}
interface PortalModule {
  code: string // 模块编号 + 英文名（如 A1 · Natural Language Workbench）
  cn: string // 中文名
  pages: PortalPage[] // 该模块下的页面清单
  built?: string // 已移植 SFC 的锚点 key（c7/c8/d5）
  gap?: boolean // 覆盖缺口模块（暂无页面）
}
interface PortalSection {
  key: string // A / B / C / D
  title: string // 层标题
  icon: string // 层图标（material-symbols）
  modules: PortalModule[]
}
interface PortalData {
  title: string
  subtitle: string
  stats: { b: string; s: string }[] // 顶部统计条
  sections: PortalSection[]
  footer: string
}

// 兜底默认值：即便后端无 workflow 实体，也能渲染完整骨架
const data = ref<PortalData>({
  title: '房满乐 Fangmanle · AI 原生酒店 PMS 原型工程',
  subtitle:
    '按功能分类树（A 智能中枢 / B 数据底座 / C 业务域 / D 平台治理）模块化整合 · 源：原始原型导出 194 页',
  stats: [
    { b: '194', s: '源页面' },
    { b: '188', s: '去重保留' },
    { b: '6', s: '合并重复' },
    { b: '18', s: '覆盖模块' },
  ],
  sections: [],
  footer: '由原始原型导出自动整合生成 · 命名依据页面语义（英文设计名/标题）· 详见 manifest.csv',
})

// 已移植为可跳转 SFC 的模块 → 路由锚点前缀
const builtMap: Record<string, string> = {
  c7: '/c7/',
  c8: '/c8/',
  d5: '/d5/',
}

onMounted(async () => {
  // 兜底数据层：优先从 demo 种子取 portal 分类树
  try {
    const res = await api.demo('workflow')
    if (Array.isArray(res) && res.length) {
      const d = res[0] as PortalData
      if (d && Array.isArray(d.sections)) data.value = d
    }
  } catch {
    // 网络/接口异常时沿用上面兜底默认值
  }
})

// 页面 chip 跳转地址：已移植模块指向对应 SFC 路由，否则占位
function pageHref(m: PortalModule, p: PortalPage): string {
  const base = m.built ? builtMap[m.built] : ''
  return base ? `${base}${p.name}` : '#'
}
</script>

<template>
  <div class="page">
    <!-- 页头（原型 header） -->
    <div class="page-head">
      <h1>{{ data.title }}</h1>
      <p>{{ data.subtitle }}</p>
    </div>

    <!-- 统计条（原型 .stats） -->
    <div class="portal-stats">
      <div v-for="st in data.stats" :key="st.s" class="card-clean portal-stat">
        <div class="num portal-stat-b">{{ st.b }}</div>
        <div class="portal-stat-s">{{ st.s }}</div>
      </div>
    </div>

    <!-- 分类层（原型 section.layer） -->
    <section v-for="sec in data.sections" :key="sec.key" class="portal-layer">
      <h2 class="portal-h2">
        <span class="material-symbols-outlined portal-h2-ico">{{ sec.icon }}</span>
        {{ sec.title }}
      </h2>

      <!-- 模块网格（原型 .mod） -->
      <div class="portal-mods">
        <div
          v-for="m in sec.modules"
          :key="m.code"
          class="card-clean portal-mod"
          :class="{ 'portal-mod-gap': m.gap }"
        >
          <div class="portal-mod-head">
            <h3 class="portal-mod-code">{{ m.code }}</h3>
            <span v-if="m.built" class="pill pill-blue">{{ t('已移植') }}</span>
          </div>
          <div class="portal-cn">{{ m.cn }}</div>

          <!-- 页面 chip 清单（原型 .pages a） -->
          <div v-if="!m.gap" class="portal-pages">
            <a
              v-for="p in m.pages"
              :key="p.name"
              :href="pageHref(m, p)"
              :title="p.title"
              class="portal-chip"
            >
              <span class="material-symbols-outlined portal-chip-ico">open_in_new</span>
              {{ p.name }}</a
            >
          </div>
          <div v-else class="portal-empty">{{ t('— 暂无页面 —') }}</div>
        </div>
      </div>
    </section>

    <footer class="portal-footer">{{ data.footer }}</footer>
  </div>
</template>

<style scoped>
/* 统计条：4 等分卡片 */
.portal-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.portal-stat {
  padding: 18px 20px;
  text-align: center;
}
.portal-stat-b {
  font-size: 30px;
  font-weight: 700;
  color: var(--primary); /* 品牌主蓝令牌 */
  line-height: 1.1;
}
.portal-stat-s {
  font-size: 13px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}

/* 分类层 */
.portal-layer {
  margin-bottom: 30px;
}
.portal-h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
  margin: 0 0 14px;
  padding-left: 10px;
  border-left: 4px solid var(--primary); /* 原型左紫蓝边 */
}
.portal-h2-ico {
  font-size: 20px;
  color: var(--primary);
}

/* 模块网格 */
.portal-mods {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.portal-mod {
  padding: 16px 18px;
}
.portal-mod-gap {
  opacity: 0.7;
}
.portal-mod-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.portal-mod-code {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
  margin: 0;
}
.portal-cn {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-bottom: 12px;
}

/* 页面 chip */
.portal-pages {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.portal-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--surface-low);
  color: var(--on-surface-variant);
  border: 1px solid var(--outline-variant);
  text-decoration: none;
  white-space: nowrap;
  transition: 0.15s;
}
.portal-chip:hover {
  background: var(--primary);
  color: var(--on-primary);
  border-color: var(--primary);
}
.portal-chip-ico {
  font-size: 13px;
}
.portal-empty {
  font-size: 12px;
  color: var(--on-surface-variant);
}

/* 页脚 */
.portal-footer {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--outline-variant);
  font-size: 12px;
  color: var(--on-surface-variant);
}
</style>
