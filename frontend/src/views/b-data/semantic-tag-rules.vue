<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 语义标签规则 —— 数据：GET /api/tags（rule_expr / cover_count）
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import TagDomainSubnav from '../../components/TagDomainSubnav.vue'

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

const router = useRouter()

type TagRow = {
  id: number
  name: string
  category?: string
  rule_expr?: string
  cover_count?: number
  code?: string
}

const rows = ref<TagRow[]>([])
const activeCat = ref(t('全部'))
const q = ref('')
const editingId = ref<number | null>(null)
const editRule = ref('')
const saving = ref(false)

onMounted(async () => {
  try {
    rows.value = (await api.listTags()) || []
  } catch {
    rows.value = []
  }
})

const CAT_TONE: Record<string, string> = {
  价值: 'tone-value',
  行为: 'tone-behavior',
  画像: 'tone-profile',
  渠道: 'tone-channel',
  忠诚度: 'tone-loyalty',
  风险: 'tone-risk',
}

const categories = computed(() => {
  const set = new Set<string>()
  for (const t of rows.value) if (t.category) set.add(t.category)
  return [t('全部'), ...Array.from(set)]
})

const maxCover = computed(() => Math.max(1, ...rows.value.map((t) => Number(t.cover_count || 0))))

const filtered = computed(() => {
  let list = [...rows.value]
  if (activeCat.value !== t('全部')) {
    list = list.filter((t) => t.category === activeCat.value)
  }
  const s = q.value.trim()
  if (s) {
    list = list.filter(
      (t) =>
        (t.name || '').includes(s) ||
        (t.rule_expr || '').includes(s) ||
        (t.category || '').includes(s),
    )
  }
  return list.sort((a, b) => Number(b.cover_count || 0) - Number(a.cover_count || 0))
})

const totalCover = computed(() => rows.value.reduce((s, t) => s + Number(t.cover_count || 0), 0))

const highlights = computed(() =>
  [...rows.value]
    .sort((a, b) => Number(b.cover_count || 0) - Number(a.cover_count || 0))
    .slice(0, 4),
)

const riskTags = computed(() => rows.value.filter((t) => t.category === t('风险')))

function coverPct(n?: number) {
  return Math.round((Number(n || 0) / maxCover.value) * 100)
}

function tone(cat?: string) {
  return CAT_TONE[cat || ''] || 'tone-default'
}

function startEdit(t: TagRow) {
  editingId.value = t.id
  editRule.value = t.rule_expr || ''
}

function cancelEdit() {
  editingId.value = null
  editRule.value = ''
}

async function saveAndApply(t: TagRow) {
  if (saving.value) return
  saving.value = true
  try {
    await api.updateTag(t.id, {
      name: t.name,
      category: t.category,
      rule_expr: editRule.value,
      is_active: true,
    })
    await api.applyTag(t.id, hotelStore.hotelId)
    const fresh = (await api.listTags()) || []
    rows.value = fresh
    cancelEdit()
    if (confirm(`规则「${t.name}」已保存并应用。是否回到客群运营试用 AI 找人？`)) {
      router.push('/b-data/cohort-list')
    }
  } catch (e: any) {
    alert(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page rules" :class="{ embedded }">
    <TagDomainSubnav v-if="!embedded" />

    <header v-if="!embedded" class="hero">
      <div class="hero-main">
        <p class="eyebrow">{{ t('治理轨 · 自动打标') }}</p>
        <h1 class="title">{{ t('语义标签规则配置') }}</h1>
        <p class="sub">{{ t('用可读的业务规则描述客群特征，系统自动匹配并写入客人标签资产。') }}</p>
      </div>
      <div class="hero-kpis">
        <div class="hk">
          <div class="hk-l">{{ t('规则数') }}</div>
          <div class="hk-v">{{ rows.length }}</div>
        </div>
        <div class="hk">
          <div class="hk-l">{{ t('累计覆盖人次') }}</div>
          <div class="hk-v">{{ totalCover.toLocaleString('zh-CN') }}</div>
        </div>
        <div class="hk">
          <div class="hk-l">{{ t('风险类规则') }}</div>
          <div class="hk-v">{{ riskTags.length }}</div>
        </div>
      </div>
    </header>
    <div v-else class="embed-kpis">
      <div class="hk">
        <div class="hk-l">{{ t('规则数') }}</div>
        <div class="hk-v">{{ rows.length }}</div>
      </div>
      <div class="hk">
        <div class="hk-l">{{ t('累计覆盖人次') }}</div>
        <div class="hk-v">{{ totalCover.toLocaleString('zh-CN') }}</div>
      </div>
      <div class="hk">
        <div class="hk-l">{{ t('风险类规则') }}</div>
        <div class="hk-v">{{ riskTags.length }}</div>
      </div>
    </div>

    <div class="layout">
      <section class="main-col">
        <div class="toolbar">
          <div class="chips">
            <button
              v-for="c in categories"
              :key="c"
              type="button"
              class="chip"
              :class="{ on: activeCat === c }"
              @click="activeCat = c"
            >
              {{ c }}
            </button>
          </div>
          <label class="search">
            <span class="material-symbols-outlined">search</span>
            <input v-model="q" type="search" :placeholder="t('搜索标签或规则…')" />
          </label>
        </div>

        <div v-if="!filtered.length" class="empty">{{ t('暂无匹配的标签规则') }}</div>
        <div v-else class="rule-list">
          <article v-for="tag in filtered" :key="item.id" class="rule-card">
            <div class="rule-top">
              <div class="rule-title-row">
                <h3>{{ tag.name }}</h3>
                <span class="cat" :class="tone(tag.category)">{{
                  tag.category || t('未分类')
                }}</span>
              </div>
              <div class="cover-num">
                <span class="n">{{ Number(tag.cover_count || 0).toLocaleString('zh-CN') }}</span>
                <span class="u">{{ t('人覆盖') }}</span>
              </div>
            </div>
            <p v-if="editingId !== tag.id" class="rule-text">
              <span class="material-symbols-outlined">auto_awesome</span>
              {{ tag.rule_expr || t('暂无规则说明') }}
            </p>
            <div v-else class="edit-box">
              <textarea
                v-model="editRule"
                rows="3"
                class="edit-input"
                :placeholder="t('输入语义规则…')"
              />
              <div class="edit-actions">
                <button type="button" class="ea ghost" @click="cancelEdit">{{ t('取消') }}</button>
                <button
                  type="button"
                  class="ea primary"
                  :disabled="saving"
                  @click="saveAndApply(tag)"
                >
                  {{ saving ? t('应用中…') : t('保存并应用') }}
                </button>
              </div>
            </div>
            <div class="bar-row">
              <div class="bar">
                <div class="bar-fill" :style="{ width: coverPct(tag.cover_count) + '%' }" />
              </div>
              <span class="bar-pct">{{ coverPct(tag.cover_count) }}%</span>
              <button
                v-if="editingId !== tag.id"
                type="button"
                class="edit-link"
                @click="startEdit(tag)"
              >
                {{ t('编辑规则') }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <aside class="side-col">
        <div class="side-card">
          <div class="side-head">
            <h3>{{ t('覆盖表现') }}</h3>
            <span class="side-tag">{{ t('实时') }}</span>
          </div>
          <p class="side-tip">{{ t('按覆盖人数排序的高影响力规则，优先用于营销与服务策略。') }}</p>
          <ul class="hi-list">
            <li v-for="(item, i) in highlights" :key="item.id">
              <span class="rank">{{ i + 1 }}</span>
              <div class="hi-body">
                <div class="hi-name">{{ item.name }}</div>
                <div class="hi-meta">
                  {{ item.category || '—' }} · {{ item.cover_count || 0 }} {{ t('人') }}
                </div>
              </div>
            </li>
          </ul>
        </div>

        <div class="side-card soft">
          <div class="side-head">
            <h3>{{ t('规则说明') }}</h3>
          </div>
          <ul class="tips">
            <li>{{ t('规则用自然语言或业务条件表达，便于运营理解与调整。') }}</li>
            <li>{{ t('覆盖人数反映当前客人画像中命中该标签的规模。') }}</li>
            <li>{{ t('风险类规则建议配合住中关怀与召回策略使用。') }}</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.rules {
  max-width: 1120px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px;
  border-radius: 20px;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--primary-fixed) 50%, #fff) 0%,
    #fff 55%
  );
  border: 1px solid color-mix(in srgb, var(--primary) 12%, var(--outline-variant));
}
.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
  color: var(--primary);
}
.title {
  margin: 0;
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.02em;
}
.sub {
  margin: 10px 0 0;
  max-width: 520px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--on-surface-variant);
}
.hero-kpis {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: stretch;
}
.hk {
  min-width: 112px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid color-mix(in srgb, var(--outline-variant) 75%, transparent);
  box-shadow: 0 8px 18px rgba(25, 28, 29, 0.04);
}
.hk-l {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.hk-v {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  border: 1px solid var(--outline-variant);
  background: #fff;
  color: var(--on-surface-variant);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.chip:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.chip.on {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--on-primary);
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: min(100%, 220px);
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: #fff;
}
.search .material-symbols-outlined {
  font-size: 18px;
  color: var(--on-surface-variant);
}
.search input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 13px;
  background: transparent;
  color: var(--on-surface);
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rule-card {
  padding: 16px 18px;
  border-radius: 16px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  box-shadow: 0 6px 18px rgba(25, 28, 29, 0.03);
  transition:
    border-color 0.15s,
    box-shadow 0.15s,
    transform 0.15s;
}
.rule-card:hover {
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
  box-shadow: 0 10px 24px rgba(0, 91, 191, 0.08);
  transform: translateY(-1px);
}
.rule-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.rule-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.rule-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}
.cat {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.tone-value {
  background: #fef3c7;
  color: #92400e;
}
.tone-behavior {
  background: var(--primary-fixed);
  color: var(--on-primary-fixed-variant);
}
.tone-profile {
  background: #e0f2fe;
  color: #075985;
}
.tone-channel {
  background: #ecfdf5;
  color: #047857;
}
.tone-loyalty {
  background: #fce7f3;
  color: #9d174d;
}
.tone-risk {
  background: #ffedd5;
  color: #9a3412;
}
.tone-default {
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
}

.cover-num {
  text-align: right;
  flex-shrink: 0;
}
.cover-num .n {
  display: block;
  font-size: 20px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  color: var(--on-surface);
}
.cover-num .u {
  font-size: 11px;
  color: var(--on-surface-variant);
}

.rule-text {
  margin: 12px 0 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--surface-bright);
  border: 1px solid color-mix(in srgb, var(--outline-variant) 70%, transparent);
  font-size: 13px;
  line-height: 1.55;
  color: var(--on-surface);
}
.rule-text .material-symbols-outlined {
  font-size: 18px;
  color: var(--primary);
  margin-top: 1px;
  flex-shrink: 0;
}

.bar-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: var(--surface-container-low);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    var(--primary),
    color-mix(in srgb, var(--primary) 60%, #60a5fa)
  );
}
.bar-pct {
  font-size: 11px;
  font-weight: 650;
  color: var(--on-surface-variant);
  min-width: 36px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.side-card {
  padding: 16px;
  border-radius: 16px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  box-shadow: 0 6px 18px rgba(25, 28, 29, 0.03);
  margin-bottom: 12px;
}
.side-card.soft {
  background: linear-gradient(180deg, color-mix(in srgb, var(--primary-fixed) 35%, #fff), #fff);
}
.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.side-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 750;
}
.side-tag {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--primary-fixed);
  color: var(--on-primary-fixed-variant);
}
.side-tip {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--on-surface-variant);
}
.hi-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hi-list li {
  display: flex;
  gap: 10px;
  align-items: center;
}
.rank {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 750;
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
  flex-shrink: 0;
}
.hi-list li:first-child .rank {
  background: var(--primary);
  color: var(--on-primary);
}
.hi-name {
  font-size: 13px;
  font-weight: 700;
}
.hi-meta {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}

.tips {
  margin: 0;
  padding-left: 16px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--on-surface-variant);
}
.tips li {
  margin: 6px 0;
}

.empty {
  padding: 28px;
  text-align: center;
  border-radius: 16px;
  border: 1px dashed var(--outline-variant);
  color: var(--on-surface-variant);
  font-size: 13px;
  background: #fff;
}

.edit-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.edit-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  font-size: 13px;
  resize: vertical;
  font-family: inherit;
}
.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.ea {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
}
.ea.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.ea.ghost {
  background: transparent;
}
.edit-link {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 450,
    'GRAD' 0,
    'opsz' 24;
}
.rules.embedded {
  max-width: none;
}
.embed-kpis {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}
.embed-kpis .hk {
  flex: 1;
  min-width: 120px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
}
.embed-kpis .hk-l {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.embed-kpis .hk-v {
  font-size: 20px;
  font-weight: 750;
  margin-top: 2px;
}
</style>
