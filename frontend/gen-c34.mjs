// SPDX-License-Identifier: Apache-2.0
// 一次性生成脚本：把原型 C3/C4 的 <main> 内容移植为 Vue SFC
// 仅提取 <main>（外壳 nav 在 main 之外，自动剥离），保留全部 Tailwind 类名以 1:1 还原
// onMounted 拉取真实后端数据；检测到的 <tbody> 表格用 v-for 绑定（示例值作为兜底）
import fs from 'node:fs'
import path from 'node:path'

const ROOT = 'E:/Workspace/新一代PMS原型/fangmanle-ui-prototype/C_business'
const C3_DIR = path.join(ROOT, 'C3-acquisition-growth')
const C4_DIR = path.join(ROOT, 'C4-reputation-relations')
const OUT_C3 = 'E:/Workspace/Ai-Native-PMS/fangmanle-demo/frontend/src/views/c3-acquisition'
const OUT_C4 = 'E:/Workspace/Ai-Native-PMS/fangmanle-demo/frontend/src/views/c4-reputation'

// C3 数据源：营销/获客实体优先真实接口 listCampaigns；长尾域用 demo 兜底
const C3_MAP = {
  '5-2-4-geo.html': { api: 'listCampaigns' },
  'ai-engine-optimization.html': { api: 'listCampaigns' },
  'ai-xiaohongshu-analytics.html': { api: 'listCampaigns' },
  'auto-awesome-ai-active.html': { api: 'listCampaigns' },
  'competitor-set.html': { api: 'listCampaigns' },
  'content-ai.html': { api: 'listCampaigns' },
  'douyin-acquisition.html': { api: 'listCampaigns' },
  'filter-list.html': { api: 'listCampaigns' },
  'flow.html': { api: 'listCampaigns' },
  'geo.html': { api: 'listCampaigns' },
  'geo-attribution-roi.html': { api: 'listCampaigns' },
  'geofencing.html': { api: 'listCampaigns' },
  'one-id.html': { api: 'demo', entity: 'oneid' },
  'ota.html': { api: 'listCampaigns' },
  'ota-2.html': { api: 'listCampaigns' },
  'ota-3.html': { api: 'listCampaigns' },
  'ota-reputation-management.html': { api: 'demo', entity: 'reputation' },
  'poi.html': { api: 'listCampaigns' },
  'room-board.html': { api: 'listCampaigns' },
  'room-board-2.html': { api: 'listCampaigns' },
  'wecom-mini-program-direct-sales.html': { api: 'listCampaigns' },
  'xiaohongshu-native-analytics.html': { api: 'listCampaigns' },
}
// C4 数据源：口碑/关系用 demo('reputation') / demo('relation')
const C4_MAP = {
  'auto-awesome-ai-verified.html': { api: 'demo', entity: 'reputation' },
  'download.html': { api: 'demo', entity: 'reputation' },
  'in-stay-proactive-care.html': { api: 'demo', entity: 'reputation' },
  'ltv.html': { api: 'demo', entity: 'relation' },
  'ms-lin-vip.html': { api: 'demo', entity: 'relation' },
  'one-id-tracing-path-to-purchase.html': { api: 'demo', entity: 'relation' },
  'roi.html': { api: 'demo', entity: 'reputation' },
  'room-board.html': { api: 'demo', entity: 'reputation' },
}

function slugify(s) {
  return String(s).trim().replace(/\s+/g, '_').replace(/[^\w一-龥]/g, '') || 'col'
}
function plainText(html) {
  return String(html)
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
// 给未自闭合的 void 元素补 /
function fixVoid(html) {
  return html.replace(/<(img|input|br|hr|meta|link)((?:"[^"]*"|'[^']*'|[^>])*?)>/g, (m, tag, inner) => {
    if (inner.trim().endsWith('/')) return m
    return `<${tag}${inner} />`
  })
}
// 剥离原型里无效的 data-="" 空属性（AI 出图 prompt 占位），避免 Vue 模板解析报错
function stripDataDash(html) {
  return html.replace(/\sdata-="[^"]*"/g, '')
}
// 抽取 <main> 内部
function extractMain(html) {
  const i = html.indexOf('<main')
  if (i < 0) return html
  const openEnd = html.indexOf('>', i)
  const close = html.indexOf('</main>', openEnd)
  return html.slice(openEnd + 1, close)
}
// 把 <tbody> 静态行改为 v-for 绑定（首行表头 slug + 示例兜底）
function bindTables(html) {
  return html.replace(/<table\b[\s\S]*?<\/table>/g, (table) => {
    const thead = table.match(/<thead[\s\S]*?<\/thead>/)
    if (!thead) return table
    const ths = [...thead[0].matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((m) => plainText(m[1]))
    if (!ths.length) return table
    const tbodyM = table.match(/<tbody[^>]*>([\s\S]*?)<\/tbody>/)
    if (!tbodyM) return table
    const rows = tbodyM[1].split('</tr>').filter((r) => r.includes('<td'))
    if (rows.length < 1) return table
    const firstCells = [...rows[0].matchAll(/<td([^>]*)>/g)].map((m) => m[1])
    let body = '<tbody>\n'
    body += `        <tr v-for="item in rows" :key="item.id" class="hover:bg-surface-bright transition-colors">\n`
    ths.forEach((h, idx) => {
      const cls = (firstCells[idx] || '').match(/class="([^"]*)"/)
      const classAttr = cls ? ` class="${cls[1]}"` : ''
      const cellMatch = rows[0].match(/<td[^>]*>([\s\S]*?)<\/td>/g)
      const rawCell = cellMatch ? cellMatch[idx] || h : h
      const fb = plainText(rawCell)
      const fallback = fb ? JSON.stringify(fb) : "''"
      body += `          <td${classAttr}>{{ item.col${idx} || ${fallback} }}</td>\n`
    })
    body += '        </tr>\n      </tbody>'
    return table.replace(/<tbody[^>]*>[\s\S]*?<\/tbody>/, body)
  })
}

function genTemplate(inner) {
  // 去掉原型 main 外层冗余包裹（.page 已提供 max-width/padding），保留内部网格
  inner = inner.replace(/^\s*<div class="max-w-\[1440px\] mx-auto space-y-gutter">/, '')
  inner = inner.replace(/<div class="grid grid-cols-12 gap-gutter h-full min-h-\[800px\]">/, '<div class="grid grid-cols-12 gap-gutter">')
  return fixVoid(stripDataDash(bindTables(inner)))
}

function buildScript(cfg) {
  const lines = [
    "<script setup lang=\"ts\">",
    "import { ref, onMounted } from 'vue'",
    "import { api } from '../lib/api'",
    "import { hotelStore } from '../store/hotel'",
    "",
    "// 数据从后端取：营销/获客实体优先真实接口，长尾域用 demo 兜底",
    "const rows = ref<any[]>([])",
    "onMounted(async () => {",
    "  try {",
  ]
  if (cfg.api === 'listCampaigns') {
    lines.push("    rows.value = await api.listCampaigns(hotelStore.hotelId)")
  } else {
    lines.push(`    rows.value = await api.demo('${cfg.entity}')`)
  }
  lines.push("  } catch (e) {")
  lines.push("    // 演示兜底：接口未就绪时仍保证页面可渲染")
  lines.push("    rows.value = []")
  lines.push("  }")
  lines.push("})")
  lines.push("</script>")
  return lines.join('\n')
}

function process(file, dir, outDir, cfg) {
  const html = fs.readFileSync(path.join(dir, file), 'utf8')
  const inner = extractMain(html)
  const tpl = genTemplate(inner)
  const out = `<!-- 移植自原型 ${file}（内容区 1:1，外壳由 App.vue 统一提供） -->\n`
    + buildScript(cfg)
    + '\n\n<template>\n  <div class="page">\n'
    + tpl.split('\n').map((l) => (l.trim() ? '    ' + l : l)).join('\n')
    + '\n  </div>\n</template>\n'
  const name = file.replace(/\.html$/, '.vue')
  fs.writeFileSync(path.join(outDir, name), out, 'utf8')
  return name
}

let count = 0
for (const [file, cfg] of Object.entries(C3_MAP)) {
  process(file, C3_DIR, OUT_C3, cfg); count++
}
for (const [file, cfg] of Object.entries(C4_MAP)) {
  process(file, C4_DIR, OUT_C4, cfg); count++
}
console.log('generated', count, 'files')
