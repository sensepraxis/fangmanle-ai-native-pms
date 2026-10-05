# 房满乐 PMS —— 前端页面移植设计契约（DESIGN CONTRACT）

> 本文件是「把原型 HTML 移植为 Vue SFC」的**唯一保真规范**。所有生成页面（170+）必须严格遵循，确保视觉 1:1 忠于原型 `E:\Workspace\新一代PMS原型\fangmanle-ui-prototype`。
> 参考实现：`src/views/RoomBoard.vue`（已按原型 room-board.html 重绘，先看它再动手）。

---

## 0. 铁律（违反即失真）
1. **不发明任何颜色**。只用下面的令牌色；原型的 `bg-primary`/`text-tertiary`/`border-outline-variant`/`bg-surface-low` 等已写进 `tailwind.config.js`，可直接用。
2. **不改外壳**。外壳（80px 侧栏 + 顶栏 ⌘K）由 `App.vue` 全局套好，页面**不要再画侧栏/顶栏**，直接写内容区。
3. **照搬原型布局与类名**。打开对应原型 `.html`，把结构/间距/组件形态照抄进 Vue 模板；只把写死的示例值（如"张三""302房""¥688"）换成 `{{ data.xxx }}`。
4. **图标统一用 `<span class="material-symbols-outlined">icon_name</span>`**，图标名取自原型（如 `cottage` `bed` `auto_graph` `smart_toy` `payments` `campaign` `share_reviews`）。
5. **字体已全局加载**：正文 Source Sans 3，数字加 class `num`/`tnum`（Roboto Mono）。

---

## 1. 色板（tailwind 类名 → 十六进制）

| 类名 | 值 | 用途 |
|---|---|---|
| `bg-primary` / `text-primary` | #005bbf | 品牌主蓝（激活态、主按钮、链接） |
| `bg-primary-container` | #1a73e8 | 主蓝容器 |
| `bg-tertiary` / `text-tertiary` | #8c33b3 | AI 紫（AI 面板标题/左紫边/搜索图标） |
| `bg-tertiary-container` | #a84fce | AI 紫容器 |
| `bg-background` | #f8fafb | 页面底色（stage 已设） |
| `bg-surface-lowest` | #ffffff | 卡片白底 |
| `bg-surface-low` | #f2f4f5 | 侧栏/浅表面、表头 |
| `bg-surface` | #eceeef | 悬浮表面 |
| `border-outline-variant` | #c1c6d6 | 所有描边/分割线 |
| `text-on-surface` | #191c1d | 主文字 |
| `text-on-surface-variant` | #414754 | 次要文字/表头 |
| `text-error` / `bg-error` | #ba1a1a | 危险/出错 |
| `bg-secondary` | #5b5f64 | 次要 |

状态色（徽标/房间态）直接用下方 `.pill-*` / `.room-*` 类，勿手写。

---

## 2. 内容区骨架（每个页面模板）

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../lib/api'
// 数据从数据库取：核心实体用 api.xxx，长尾域用 api.demo('entity')
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => { rows.value = await api.demo('xxx') })
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>页面标题</h1>
      <p>页面副标题 / 说明</p>
    </div>
    <!-- 工具栏 / 卡片 / 表格 / AI 面板 见下 -->
  </div>
</template>
```

`.page` 已含 `padding:24px 28px;max-width:1440px;margin:auto`。

---

## 3. 可直接复用的组件类（来自 `src/index.css`，照抄即用）

- **卡片**：`<div class="card-clean card-pad">…</div>` 或带标题 `<div class="card-clean"><div class="card-head">标题 <span>右侧</span></div><div class="card-pad">…</div></div>`
- **KPI**：`<div class="kpi-grid">` 内 `<div class="kpi"><div class="k">标签</div><div class="v num">688</div><div class="d up">+12%</div></div>`
- **表格**：`<table class="data"><thead><tr><th>…</th></tr></thead><tbody><tr class="clickable"><td>…</td></tr></tbody></table>`（`td.num` 右对齐、`td.center` 居中、`tr.clickable` 可点）
- **状态徽标**：`<span class="pill pill-green">已入住</span>` / `pill-rose` / `pill-amber` / `pill-blue` / `pill-slate`
- **按钮**：`<button class="btn btn-primary">主操作</button>` / `btn-ghost`（描边）/ `btn-link`（文字链）
- **工具栏**：`<div class="toolbar"><select>…</select><input class="toolbar-input" placeholder="搜索"></div>`
- **AI 面板（左 3px 紫边）**：`<div class="ai-card"><div class="ttl"><span class="material-symbols-outlined">auto_awesome</span>AI 建议</div><ul><li>…</li></ul></div>`
- **房间态色块**：`<div class="room-grid"><div class="room-cell room-occupied">302<small>在住</small></div></div>`（`room-vacant` `room-occupied` `room-dirty` `room-clean` `room-ooo`）
- **返回链**：`<div class="back-link"><span class="material-symbols-outlined">arrow_back</span>返回</div>`
- **链接**：`<span class="link" @click="...">查看</span>`

---

## 4. 数据层（`src/lib/api.ts`）

核心实体（真实 DB）：
`api.listRooms(hid)` `api.listOrders(hid,status?)` `api.getOrder(id)` `api.listPricing(hid)` `api.pricingDetail(pid)` `api.listGuests(hid)` `api.guest360(id)` `api.listAudits(hid)` `api.auditDetail(hid,date)` `api.listHousekeeping(hid)` `api.listSupplies(hid)` `api.listCampaigns(hid)` `api.dashboard(hid)` `api.listHotels()` `api.listChannels()`

长尾域（确定性种子，`GET /api/demo/<entity>`）：
`api.demo('linen' | 'reputation' | 'asset' | 'risk' | 'channel-sync' | 'tag' | 'semantic-history' | 'oneid' | 'ai-engine' | 'multi-format' | '…')` → 返回 `any[]`。

页面里**优先用真实实体接口**，原型页展示的实体若不在核心列表，就用 `api.demo('<对应实体名>')`，返回数组直接 `v-for` 渲染。

---

## 5. 文件与路由约定
- 每个原型页 → 一个 SFC：`src/views/<domain>/<page>.vue`（domain 如 `c1-revenue` `c6-housekeeping` `a-ai-core` `b-data`）。
- 文件名用原型文件名去 `.html`（如 `room-board.html` → `room-board.vue`）。
- 路由由脚本按文件路径自动生成（`/c1-revenue/room-board`），无需手写。
- 同一域的列表/详情/分步变体各自成文件；变体页在标题注明「（变体：同 XXX）」。

---

## 6. 质量自检（提交前逐条过）
- [ ] 颜色全来自第 1 节令牌，无 `#xxx` 硬编码新色（允许原生 white/black 文本）
- [ ] 无侧栏/顶栏重复绘制
- [ ] 用了第 3 节组件类，外观接近原型
- [ ] 示例数据已替换为 `api` 绑定（至少列表/标题/KPI 绑定）
- [ ] 图标用 `material-symbols-outlined`
- [ ] `<template>` 无 TS 语法错误、无未定义变量
