<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 基础标签库管理 —— 对齐原型 B3/master-tag-library.html
 * 数据：GET /api/tags（tag_definitions + guest_tags 覆盖人数）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import TagDomainSubnav from '../../components/TagDomainSubnav.vue'

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

type TagRow = {
  id: number
  code?: string
  name: string
  category?: string
  rule_expr?: string
  is_active?: boolean
  cover_count?: number
  kind?: 'rule' | 'ai'
  heat?: number
}

const CAT_ICON: Record<string, string> = {
  价值: 'payments',
  行为: 'trending_up',
  忠诚度: 'loyalty',
  画像: 'group',
  渠道: 'hub',
  风险: 'psychology',
  人口统计: 'group',
  消费行为: 'payments',
  偏好习惯: 'favorite',
  'AI 预测': 'psychology',
}

/** DB category → UI 维度 msgid（展示时再 t()） */
const CAT_MAP: Record<string, string> = {
  价值: '消费行为',
  行为: '消费行为',
  忠诚度: '消费行为',
  画像: '人口统计',
  渠道: '偏好习惯',
  风险: 'AI 预测',
}

const activeCat = ref('全部')
const q = ref('')
const loading = ref(false)
const tags = ref<TagRow[]>([])
const showNew = ref(false)
const savingNew = ref(false)
const newKind = ref<'rule' | 'ai'>('rule')
const newName = ref('')
/** 维度/字段一律存中文 msgid，展示用 t() */
const newDim = ref('消费行为')
const newField = ref('总消费')
const newOp = ref('≥')
const newValue = ref('3000')

/** UI 维度 msgid → 规则字段 msgid */
const FIELD_BY_DIM: Record<string, string[]> = {
  消费行为: ['总消费', '年均消费', 'LTV', '订单均价', '促销转化次数'],
  人口统计: ['携儿童订单数', '工作日入住占比', '出行人数', '累计间夜'],
  偏好习惯: ['渠道来源', '偏好楼层', '评价关键词', '私域互动次数'],
  'AI 预测': ['流失风险分', '投诉风险置信度', '复购概率'],
}

/** UI 维度 msgid → 入库 category（与种子标签一致，勿翻译） */
const DIM_TO_DB: Record<string, string> = {
  消费行为: '价值',
  人口统计: '画像',
  偏好习惯: '渠道',
  'AI 预测': '风险',
}

const newFieldOptions = computed(() => FIELD_BY_DIM[newDim.value] || FIELD_BY_DIM['消费行为'])

const newRulePreview = computed(() => {
  const fieldLab = t(newField.value)
  if (newKind.value === 'ai') {
    return t('模型：{field}（{op} {val}）', {
      field: fieldLab,
      op: newOp.value,
      val: newValue.value || '—',
    })
  }
  const unit = /占比|概率|置信度|风险分/.test(newField.value)
    ? String(newValue.value).includes('%')
      ? ''
      : '%'
    : ''
  const val = newValue.value || '—'
  const showYen = /消费|LTV|均价/.test(newField.value) && !String(val).startsWith('¥')
  return `${fieldLab} ${newOp.value} ${showYen ? '¥' : ''}${val}${unit}`
})

watch(newDim, () => {
  const opts = FIELD_BY_DIM[newDim.value] || []
  if (opts.length && !opts.includes(newField.value)) {
    newField.value = opts[0]
  }
  // 按维度给一个更合理的默认阈值
  if (newDim.value === '消费行为') {
    newOp.value = '≥'
    newValue.value = '3000'
  } else if (newDim.value === '人口统计') {
    newOp.value = '≥'
    newValue.value = '2'
  } else if (newDim.value === '偏好习惯') {
    newOp.value = '='
    newValue.value = '抖音'
  } else {
    newOp.value = '>'
    newValue.value = '80'
  }
})

watch(newKind, (k) => {
  if (k === 'ai') {
    newDim.value = 'AI 预测'
  } else if (newDim.value === 'AI 预测') {
    newDim.value = '消费行为'
  }
})

function openNewDialog() {
  newKind.value = 'rule'
  newName.value = ''
  newDim.value =
    activeCat.value !== '全部' && FIELD_BY_DIM[activeCat.value] ? activeCat.value : '消费行为'
  const opts = FIELD_BY_DIM[newDim.value] || FIELD_BY_DIM['消费行为']
  newField.value = opts[0]
  newOp.value = '≥'
  newValue.value = '3000'
  showNew.value = true
}

async function saveNewTag() {
  const name = newName.value.trim()
  if (!name) {
    alert(t('请填写标签名称'))
    return
  }
  if (savingNew.value) return
  savingNew.value = true
  try {
    const ascii = name
      .replace(/[^\w]+/g, '_')
      .toLowerCase()
      .replace(/^_|_$/g, '')
    const code =
      ascii && /[a-z0-9]/.test(ascii) ? ascii.slice(0, 40) : `tag_${Date.now().toString(36)}`
    const created = await api.createTag({
      name,
      code,
      category: DIM_TO_DB[newDim.value] || '画像',
      rule_expr: newRulePreview.value,
    })
    showNew.value = false
    await load()
    const id = Number(created?.id)
    if (id) {
      try {
        const res = await api.applyTag(id, hotelStore.hotelId)
        await load()
        const row = tags.value.find((x) => x.id === id)
        const n = Number(row?.cover_count ?? 0)
        showToast(t('「{name}」已创建并同步 · 覆盖 {n} 人', { name, n: fmtCover(n) }))
      } catch (e: any) {
        showToast(e?.message || t('创建成功，同步失败，请点「立即同步」'))
      }
    }
  } catch (e: any) {
    alert(e?.message || t('保存失败'))
  } finally {
    savingNew.value = false
  }
}

const CATEGORIES = computed(() => {
  const bucket: Record<string, string[]> = {}
  for (const row of tags.value) {
    const raw = String(row.category || '其他')
    const dimKey = CAT_MAP[raw] || raw
    bucket[dimKey] ||= []
    if (!bucket[dimKey].includes(row.name)) bucket[dimKey].push(row.name)
  }
  const keys = Object.keys(bucket)
  if (!keys.length) {
    return [
      { key: 'all', label: t('全部'), dimKey: '全部', icon: 'label', children: [] as string[] },
    ]
  }
  return keys.map((dimKey) => ({
    key: dimKey,
    dimKey,
    label: t(dimKey),
    icon:
      CAT_ICON[dimKey] ||
      CAT_ICON[Object.keys(CAT_MAP).find((k) => CAT_MAP[k] === dimKey) || ''] ||
      'label',
    children: bucket[dimKey],
  }))
})

function isAi(tag: TagRow) {
  if (tag.kind === 'ai') return true
  const c = String(tag.category || '')
  const n = String(tag.name || '')
  return c === '风险' || /流失|预测|AI|风险/.test(n)
}

function heatLevel(cover: number) {
  if (cover >= 100) return 5
  if (cover >= 60) return 4
  if (cover >= 30) return 3
  if (cover >= 10) return 2
  return 1
}

function ruleText(tag: TagRow) {
  const raw = String(tag.rule_expr || '').trim()
  if (!raw) return '—'
  // 兼容旧种子 rule:code
  if (/^rule:/.test(raw)) {
    const code = raw.slice(5)
    const FALLBACK: Record<string, string> = {
      high_value: t('年消费 ≥ ¥50,000 或 LTV ≥ ¥8,000'),
      price_sensitive: t('促销转化率高 · 均价低于门市价 15%'),
      family: t('历史携儿童订单 ≥ 2'),
      business: t('工作日入住占比 > 70%'),
      complaint_risk: t('模型：Complaint_v2（置信度 > 80%）'),
      douyin_fan: t('抖音渠道订单 ≥ 1 或私域互动 ≥ 3'),
      xhs_fan: t('小红书来源订单 ≥ 1'),
      repeat: t('180 天内订单 ≥ 5'),
      vip: t('会员等级 ∈ {金卡, 白金} 或累计间夜 ≥ 20'),
    }
    return FALLBACK[code] || FALLBACK[tag.code || ''] || raw
  }
  if (raw === tag.code) {
    return ruleText({ ...tag, rule_expr: `rule:${raw}` })
  }
  return raw
}

function typeLabel(tag: TagRow) {
  if (isAi(tag)) return t('AI 预测')
  const dim = CAT_MAP[String(tag.category || '')]
  return dim ? t(dim) : t(String(tag.category || '规则'))
}

async function load() {
  loading.value = true
  try {
    const rows = await api.listTags()
    tags.value = (rows || []).map((row: any) => ({
      ...row,
      cover_count: Number(row.cover_count || 0),
      heat: heatLevel(Number(row.cover_count || 0)),
      kind: /风险|流失|预测/.test(String(row.category || '') + String(row.name || ''))
        ? 'ai'
        : 'rule',
    }))
    // 若库为空则回退 demo
    if (!tags.value.length) {
      const demo = await api.demo('tag')
      tags.value = (demo || []).map((d: any) => ({
        id: d.id,
        name: d.name,
        category: d.group,
        rule_expr: d.rule,
        cover_count: d.count,
        is_active: true,
        heat: heatLevel(Number(d.count || 0)),
        kind: /风险|AI/.test(String(d.group || '') + String(d.name || '')) ? 'ai' : 'rule',
      }))
    }
  } finally {
    loading.value = false
  }
}
onMounted(load)

const filtered = computed(() => {
  const dim = activeCat.value
  let list = [...tags.value]
  if (dim && dim !== '全部') {
    list = list.filter((tag) => {
      const mapped = CAT_MAP[String(tag.category || '')] || String(tag.category || '其他')
      if (dim === 'AI 预测') return mapped === 'AI 预测' || isAi(tag)
      return mapped === dim
    })
  }
  const s = q.value.trim()
  if (s) {
    list = list.filter(
      (tag) =>
        (tag.name || '').includes(s) ||
        (tag.category || '').includes(s) ||
        (tag.rule_expr || '').includes(s),
    )
  }
  return list
})

function selectCat(label: string) {
  activeCat.value = label
}

function fmtCover(n: number) {
  return Number(n || 0).toLocaleString('zh-CN')
}

const rowBusyId = ref<number | null>(null)
const drafts = ref<Record<number, string>>({})
const toast = ref('')
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(msg: string) {
  toast.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
  }, 3200)
}

function ruleDraft(tag: TagRow) {
  if (drafts.value[tag.id] != null) return drafts.value[tag.id]
  return ruleText(tag)
}

function onRuleInput(tag: TagRow, e: Event) {
  drafts.value[tag.id] = (e.target as HTMLTextAreaElement).value
}

function ruleDirty(tag: TagRow) {
  const d = drafts.value[tag.id]
  return d != null && d.trim() !== ruleText(tag).trim()
}

async function onRuleBlur(tag: TagRow) {
  if (!ruleDirty(tag)) {
    delete drafts.value[tag.id]
    return
  }
  await saveAndSync(tag, drafts.value[tag.id].trim())
}

async function saveAndSync(tag: TagRow, ruleExpr: string) {
  if (rowBusyId.value != null) return
  rowBusyId.value = tag.id
  try {
    await api.updateTag(tag.id, {
      name: tag.name,
      category: tag.category,
      rule_expr: ruleExpr,
      is_active: true,
    })
    await api.applyTag(tag.id, hotelStore.hotelId)
    delete drafts.value[tag.id]
    await load()
    const row = tags.value.find((x) => x.id === tag.id)
    const n = Number(row?.cover_count ?? 0)
    showToast(t('「{name}」已保存并同步 · 覆盖 {n} 人', { name: tag.name, n: fmtCover(n) }))
  } catch (e: any) {
    showToast(e?.message || t('保存失败'))
  } finally {
    rowBusyId.value = null
  }
}

async function syncTag(tag: TagRow) {
  if (rowBusyId.value != null) return
  rowBusyId.value = tag.id
  try {
    await api.applyTag(tag.id, hotelStore.hotelId)
    await load()
    const row = tags.value.find((x) => x.id === tag.id)
    const n = Number(row?.cover_count ?? 0)
    showToast(t('「{name}」已同步 · 覆盖 {n} 人', { name: tag.name, n: fmtCover(n) }))
  } catch (e: any) {
    showToast(e?.message || t('同步失败'))
  } finally {
    rowBusyId.value = null
  }
}

defineExpose({ openNewDialog })
</script>

<template>
  <div class="page tag-lib" :class="{ embedded }">
    <TagDomainSubnav v-if="!embedded" />
    <div v-if="!embedded" class="flex justify-between items-end mb-6 flex-wrap gap-3">
      <div>
        <h1 class="text-display-lg font-display-lg text-on-surface m-0">
          {{ t('基础标签库管理') }}
        </h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-1 m-0">
          {{ t('管理客群规则与 AI 驱动的洞察。') }}
        </p>
      </div>
      <button type="button" class="btn-new" @click="openNewDialog">
        <span class="material-symbols-outlined text-[18px]">add</span>
        {{ t('新建标签') }}
      </button>
    </div>
    <div
      class="grid grid-cols-12 gap-4"
      :class="embedded ? 'embed-grid' : 'min-h-[calc(100vh-240px)]'"
    >
      <!-- Left: Category Tree（独立页） -->
      <aside v-if="!embedded" class="col-span-12 md:col-span-3 panel aside">
        <div class="flex items-center gap-2 mb-4 px-2">
          <span class="material-symbols-outlined text-primary text-[20px]">category</span>
          <h2 class="text-headline-md font-headline-md text-on-surface m-0">{{ t('分类维度') }}</h2>
        </div>
        <ul class="space-y-1 m-0 p-0 list-none">
          <li>
            <button
              type="button"
              class="cat-btn"
              :class="{ on: activeCat === '全部' }"
              @click="selectCat('全部')"
            >
              <span class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[18px]">label</span>
                {{ t('全部') }}</span
              >
            </button>
          </li>
          <li v-for="c in CATEGORIES" :key="c.key">
            <button
              type="button"
              class="cat-btn"
              :class="{ on: activeCat === c.dimKey }"
              @click="selectCat(c.dimKey)"
            >
              <span class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[18px]">{{ c.icon }}</span>
                {{ c.label }}</span
              >
            </button>
          </li>
        </ul>
      </aside>

      <!-- Right: Tag List -->
      <section
        class="panel list-panel"
        :class="embedded ? 'list-panel-embed' : 'col-span-12 md:col-span-9'"
      >
        <div class="list-head">
          <h3 class="text-headline-md font-headline-md text-on-surface m-0">
            {{ activeCat === '全部' ? t('全部标签') : t(activeCat) }}
            <span class="list-count">{{ filtered.length }}</span>
          </h3>
          <div class="relative">
            <span class="material-symbols-outlined search-ico">search</span>
            <input
              v-model="q"
              class="search-input"
              :placeholder="t('搜索标签或规则...')"
              type="search"
            />
          </div>
        </div>
        <div v-if="embedded" class="cat-bar">
          <button
            type="button"
            class="cat-chip"
            :class="{ on: activeCat === '全部' }"
            @click="selectCat('全部')"
          >
            <span class="material-symbols-outlined">label</span>
            {{ t('全部') }}
          </button>
          <button
            v-for="c in CATEGORIES"
            :key="c.key"
            type="button"
            class="cat-chip"
            :class="{ on: activeCat === c.dimKey }"
            @click="selectCat(c.dimKey)"
          >
            <span class="material-symbols-outlined">{{ c.icon }}</span>
            {{ c.label }}
          </button>
        </div>

        <div class="overflow-auto flex-1 tag-scroll">
          <div v-if="loading" class="p-6 text-sm text-on-surface-variant">{{ t('加载中…') }}</div>
          <div v-else-if="!filtered.length" class="empty">{{ t('该分类下暂无标签') }}</div>
          <div v-else class="tag-cards">
            <article
              v-for="tag in filtered"
              :key="tag.id"
              class="tag-card"
              :class="{ busy: rowBusyId === tag.id }"
            >
              <div class="tag-card-head">
                <div class="name-cell">
                  <span class="dot" :class="isAi(tag) ? 'dot-ai' : 'dot-rule'" />
                  <strong>{{ t(tag.name) }}</strong>
                  <span class="type-badge" :class="isAi(tag) ? 'type-ai' : 'type-rule'">{{
                    typeLabel(tag)
                  }}</span>
                  <code v-if="tag.code" class="code-chip">{{ tag.code }}</code>
                </div>
                <div
                  class="cover-badge"
                  :class="Number(tag.cover_count || 0) > 0 ? 'synced' : 'pending'"
                >
                  <template v-if="rowBusyId === tag.id">
                    <span class="material-symbols-outlined spin">progress_activity</span>
                    {{ t('同步中…') }}</template
                  >
                  <template v-else-if="Number(tag.cover_count || 0) > 0">
                    <span class="material-symbols-outlined">check_circle</span>
                    {{ t('覆盖 {n} 人', { n: fmtCover(tag.cover_count || 0) }) }}
                  </template>
                  <template v-else>
                    <span class="material-symbols-outlined">sync</span>
                    {{ t('待同步') }}
                    <button type="button" class="sync-btn" @click="syncTag(tag)">
                      {{ t('立即同步') }}
                    </button>
                  </template>
                </div>
              </div>
              <label class="rule-label">{{ t('命中规则') }}</label>
              <textarea
                class="rule-inline"
                :class="{ dirty: ruleDirty(tag) }"
                :value="ruleDraft(tag)"
                rows="2"
                :placeholder="t('输入命中规则，失焦后自动保存并同步到客人')"
                :disabled="rowBusyId === tag.id"
                @input="onRuleInput(tag, $event)"
                @blur="onRuleBlur(tag)"
                @keydown.enter.exact.prevent="onRuleBlur(tag)"
              />
              <p v-if="ruleDirty(tag)" class="rule-hint">
                {{ t('已修改 · 失焦或 Enter 保存并同步') }}
              </p>
            </article>
          </div>
        </div>
      </section>
    </div>

    <Transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </Transition>

    <!-- 新建标签对话框 -->
    <div v-if="showNew" class="dialog-mask" @click.self="showNew = false">
      <div class="dialog">
        <div class="dialog-h">
          <h2 class="m-0 text-lg font-bold">{{ t('新建标签') }}</h2>
          <button type="button" class="icon-btn" @click="showNew = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="dialog-b space-y-5">
          <div class="grid grid-cols-2 gap-3">
            <label class="type-card">
              <input
                v-model="newKind"
                class="sr-only peer"
                name="tagType"
                type="radio"
                value="rule"
              />
              <div
                class="type-card-inner peer-checked:border-primary peer-checked:bg-primary-fixed/20"
              >
                <div class="font-medium mb-1">{{ t('规则标签') }}</div>
                <p class="text-sm text-on-surface-variant m-0">
                  {{ t('定义严格的逻辑条件（例如：消费 ≥ 3000）。') }}
                </p>
              </div>
            </label>
            <label class="type-card">
              <input
                v-model="newKind"
                class="sr-only peer"
                name="tagType"
                type="radio"
                value="ai"
              />
              <div
                class="type-card-inner peer-checked:border-tertiary peer-checked:bg-tertiary-fixed/30"
              >
                <div class="font-medium mb-1">{{ t('AI 标签') }}</div>
                <p class="text-sm text-on-surface-variant m-0">
                  {{ t('利用模型分值获取洞察（例如：流失风险）。') }}
                </p>
              </div>
            </label>
          </div>
          <div>
            <label class="field-label">{{ t('标签名称') }}</label>
            <input
              v-model="newName"
              class="field"
              :placeholder="t('例如: 高净值用户')"
              type="text"
            />
          </div>
          <div>
            <label class="field-label">{{ t('归属分类') }}</label>
            <select v-model="newDim" class="field" :disabled="newKind === 'ai'">
              <option value="消费行为">{{ t('消费行为') }}</option>
              <option value="人口统计">{{ t('人口统计') }}</option>
              <option value="偏好习惯">{{ t('偏好习惯') }}</option>
              <option value="AI 预测">{{ t('AI 预测') }}</option>
            </select>
          </div>
          <div class="logic-box">
            <div class="field-label mb-3">{{ t('规则逻辑定义') }}</div>
            <div class="flex gap-2 items-center flex-wrap text-sm">
              <span class="text-on-surface-variant">{{ t('如果') }}</span>
              <select v-model="newField" class="mini">
                <option v-for="f in newFieldOptions" :key="f" :value="f">{{ t(f) }}</option>
              </select>
              <select v-model="newOp" class="mini">
                <option>≥</option>
                <option>&gt;</option>
                <option>≤</option>
                <option>&lt;</option>
                <option>=</option>
                <option>{{ t('包含') }}</option>
              </select>
              <input v-model="newValue" class="mini w-28" type="text" :placeholder="t('阈值')" />
            </div>
            <p class="rule-preview">{{ t('将保存为：') }}{{ newRulePreview }}</p>
          </div>
        </div>
        <div class="dialog-f">
          <button type="button" class="btn-ghost-pill" @click="showNew = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="btn-primary-pill" :disabled="savingNew" @click="saveNewTag">
            {{ savingNew ? t('保存中…') : t('保存标签') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-lib {
  max-width: 1200px;
}
.btn-new {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--primary);
  color: var(--on-primary);
  padding: 8px 24px;
  border-radius: 999px;
  border: none;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.btn-new:hover {
  filter: brightness(1.05);
}

.panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.aside {
  padding: 16px;
  overflow: auto;
}
.list-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 520px;
}

.cat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--on-surface);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}
.cat-btn:hover {
  background: var(--surface-container-low);
}
.cat-btn.on {
  background: var(--secondary-container, #dde0e6);
  color: var(--primary);
  font-weight: 750;
}
.child-list {
  margin: 4px 0 0 28px;
  padding: 0 0 0 8px;
  list-style: none;
  border-left: 2px solid var(--surface-container-high);
}
.child-btn {
  width: 100%;
  text-align: left;
  padding: 8px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--on-surface-variant);
  font-size: 13px;
  cursor: pointer;
}
.child-btn:hover {
  background: var(--surface-container-low);
}
.child-btn.on {
  background: var(--surface-container-low);
  color: var(--primary);
  font-weight: 650;
}

.ai-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--tertiary-fixed, #f8d8ff) 20%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--tertiary-fixed-dim, #ebb2ff) 30%, transparent);
}
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-bright, #f8fafb);
}
.search-ico {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--on-surface-variant);
  pointer-events: none;
}
.search-input {
  padding: 6px 12px 6px 36px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  width: 280px;
  max-width: 100%;
  font-size: 14px;
  outline: none;
  background: var(--surface-container-lowest);
}
.search-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}
.list-count {
  margin-left: 6px;
  font-size: 13px;
  font-weight: 650;
  color: var(--on-surface-variant);
}

.tag-scroll {
  padding: 12px 16px 16px;
}
.tag-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tag-lib.embedded .tag-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 960px) {
  .tag-lib.embedded .tag-cards {
    grid-template-columns: 1fr;
  }
}
.tag-card {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.tag-card:hover {
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
}
.tag-card.busy {
  opacity: 0.75;
  pointer-events: none;
}
.tag-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.name-cell strong {
  font-size: 15px;
  font-weight: 750;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.dot-rule {
  background: var(--primary);
}
.dot-ai {
  background: var(--tertiary, #8c33b3);
}
.code-chip {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
}
.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
}
.type-rule {
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.type-ai {
  background: color-mix(in srgb, var(--tertiary, #8c33b3) 12%, transparent);
  color: var(--tertiary, #8c33b3);
}
.cover-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.cover-badge .material-symbols-outlined {
  font-size: 16px;
}
.cover-badge.synced {
  color: #16a34a;
}
.cover-badge.pending {
  color: #c2410c;
}
.sync-btn {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  padding: 0 0 0 4px;
  text-decoration: underline;
}
.rule-label {
  display: block;
  font-size: 11px;
  font-weight: 650;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.rule-inline {
  width: 100%;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  line-height: 1.45;
  resize: vertical;
  min-height: 52px;
  background: var(--surface-container-low, #f8f6f2);
  outline: none;
}
.rule-inline:focus {
  border-color: var(--primary);
  background: var(--surface-container-lowest);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 15%, transparent);
}
.rule-inline.dirty {
  border-color: color-mix(in srgb, var(--primary) 50%, var(--outline-variant));
}
.rule-hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--primary);
  font-weight: 650;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  padding: 32px 16px;
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 10px 18px;
  border-radius: 999px;
  background: var(--inverse-surface, #2e3132);
  color: var(--inverse-on-surface, #f0f0f3);
  font-size: 13px;
  font-weight: 650;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
  max-width: min(90vw, 480px);
  text-align: center;
}
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

.dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(46, 49, 50, 0.4);
  backdrop-filter: blur(4px);
}
.dialog {
  width: 600px;
  max-width: calc(100vw - 32px);
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.dialog-h {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-bright, #f8fafb);
}
.icon-btn {
  border: none;
  background: transparent;
  color: var(--on-surface-variant);
  cursor: pointer;
  padding: 4px;
  border-radius: 8px;
}
.icon-btn:hover {
  color: var(--primary);
  background: var(--surface-container-low);
}
.dialog-b {
  padding: 24px;
  overflow: auto;
  max-height: 60vh;
}
.dialog-f {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.type-card {
  cursor: pointer;
}
.type-card-inner {
  padding: 16px;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.type-card:hover .type-card-inner {
  background: var(--surface-container-low);
}
.field-label {
  display: block;
  font-size: 13px;
  font-weight: 650;
  margin-bottom: 4px;
}
.field {
  width: 100%;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  outline: none;
  background: var(--surface-container-lowest);
}
.field:focus {
  border-color: var(--primary);
}
.logic-box {
  background: var(--surface-container);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--outline-variant) 50%, transparent);
}
.rule-preview {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.mini {
  border: 1px solid var(--outline-variant);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
  background: #fff;
}
.btn-ghost-pill {
  padding: 8px 20px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: transparent;
  cursor: pointer;
  font-weight: 650;
}
.btn-primary-pill {
  padding: 8px 20px;
  border-radius: 999px;
  border: none;
  background: var(--primary);
  color: var(--on-primary);
  cursor: pointer;
  font-weight: 650;
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.tag-lib.embedded {
  max-width: none;
  width: 100%;
}
.embed-grid {
  display: block;
  min-height: auto;
}
.list-panel-embed {
  width: 100%;
  min-height: calc(100vh - 180px);
}
.cat-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px 12px;
  border-bottom: 1px solid var(--outline-variant);
}
.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}
.cat-chip .material-symbols-outlined {
  font-size: 16px;
}
.cat-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.cat-chip.on {
  background: var(--secondary-container, #dde0e6);
  border-color: transparent;
  color: var(--primary);
  font-weight: 750;
}
</style>
