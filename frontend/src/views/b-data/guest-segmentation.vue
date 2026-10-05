<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 标签体系与分群 —— 对齐原型 B3/guest-segmentation
 * 数据：GET /api/tags + /api/segments
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import TagDomainSubnav from '../../components/TagDomainSubnav.vue'

const router = useRouter()
const tags = ref<any[]>([])
const segs = ref<any[]>([])
const selectedTagIds = ref<Set<number>>(new Set())

onMounted(async () => {
  try {
    const [t, s] = await Promise.all([
      api.listTags(),
      api.listSegments(hotelStore.hotelId).catch(() => []),
    ])
    tags.value = t || []
    segs.value = s || []
    // 默认高亮若干标签，贴近原型选中态
    const pick = (t || []).filter((x: any) =>
      /抖音|小红书|高价值|VIP|商务|亲子|价格/.test(String(x.name || '')),
    )
    selectedTagIds.value = new Set(pick.slice(0, 3).map((x: any) => x.id))
  } catch {
    tags.value = []
  }
})

const RULE_CN: Record<string, string> = {
  'ltv>5000 and repeat': t('年消费较高且具备复购特征'),
  family: t('历史携儿童入住 ≥ 2 次'),
  'churn_risk>=0.7': t('流失风险偏高，建议召回'),
  business: t('工作日入住偏好 · 商务出行'),
  vip: t('会员等级达到 VIP / 金卡及以上'),
  new_guest: t('本自然月首次到店'),
}

function ruleLabel(raw?: string) {
  const key = String(raw || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '')
  if (RULE_CN[key]) return RULE_CN[key]
  const soft = String(raw || '')
    .replace(/ltv\s*>\s*5000/gi, t('年消费较高'))
    .replace(/AND/gi, t('且'))
    .replace(/churn_risk\s*>=\s*0\.7/gi, t('流失风险偏高'))
    .replace(/_/g, ' ')
  return soft || t('组合标签规则')
}

/** 图谱分组：尽量贴近原型「渠道 / RFM / 行为」 */
const atlasGroups = computed(() => {
  const channel = tags.value.filter((t) => t.category === t('渠道'))
  const rfm = tags.value.filter((t) => [t('价值'), t('忠诚度')].includes(t.category))
  const behavior = tags.value.filter((t) => [t('画像'), t('行为'), t('风险')].includes(t.category))
  return [
    { key: 'channel', label: t('渠道来源'), items: channel },
    { key: 'rfm', label: t('RFM 价值'), items: rfm },
    { key: 'behavior', label: t('行为偏好'), items: behavior },
  ].filter((g) => g.items.length)
})

const totalCover = computed(() => tags.value.reduce((s, t) => s + Number(t.cover_count || 0), 0))

const guestPool = computed(() =>
  Math.max(
    80,
    segs.value.reduce((s, x) => s + Number(x.member_count || 0), 0),
  ),
)

const previewReach = computed(() => {
  const ids = selectedTagIds.value
  if (!ids.size) return Math.round(guestPool.value * 0.35)
  const covers = tags.value.filter((t) => ids.has(t.id)).map((t) => Number(t.cover_count || 0))
  const avg = covers.reduce((a, b) => a + b, 0) / Math.max(covers.length, 1)
  return Math.max(40, Math.round(avg * 1.2))
})

const convRate = computed(() => {
  const base = 3.4 + Math.min(2.2, selectedTagIds.value.size * 0.35)
  return Math.round(base * 10) / 10
})

const expectOrders = computed(() =>
  Math.max(8, Math.round((previewReach.value * convRate.value) / 100)),
)

const activeSegs = computed(() =>
  segs.value.slice(0, 6).map((s, i) => ({
    ...s,
    ruleCn: ruleLabel(s.rule || s.filter_rule),
    channel: i % 2 === 0 ? t('企微自动化') : t('短信推送'),
    pct: guestPool.value
      ? Math.max(1, Math.round((Number(s.member_count || 0) / guestPool.value) * 100))
      : 0,
    tone: i % 2 === 0 ? 'ok' : 'warn',
  })),
)

function toggleTag(id: number) {
  const next = new Set(selectedTagIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedTagIds.value = next
}

function isOn(id: number) {
  return selectedTagIds.value.has(id)
}

function isAccent(row: any) {
  // category 存中文 msgid，勿用 t() 后再比（EN 下会变成英文对不上）
  const cat = String(row.category || '')
  return cat === '价值' || cat === '风险' || /高价值|高净值/.test(String(row.name || ''))
}

function goCohort() {
  router.push('/b-data/cohort-list')
}

function openSeg(name: string) {
  router.push({ path: '/b-data/global-guest-directory', query: { segment: name } })
}
</script>

<template>
  <div class="page seg">
    <TagDomainSubnav />

    <div class="head">
      <div>
        <h1>{{ t('标签体系与分群') }}</h1>
        <p>{{ t('用标签规则做分群，服务营销与留存。') }}</p>
      </div>
      <button type="button" class="btn-primary" @click="goCohort">{{ t('去客群列表') }}</button>
    </div>

    <div class="grid-main">
      <!-- 左：标签图谱 -->
      <aside class="panel atlas">
        <h2>{{ t('标签图谱') }}</h2>
        <div v-for="g in atlasGroups" :key="g.key" class="atlas-block">
          <h3>{{ g.label }}</h3>
          <div class="pills">
            <button
              v-for="tag in g.items"
              :key="tag.id"
              type="button"
              class="pill"
              :class="{ on: isOn(tag.id), accent: isAccent(t) && isOn(tag.id) }"
              @click="toggleTag(tag.id)"
            >
              {{ tag.name }}
            </button>
          </div>
        </div>
        <p v-if="!atlasGroups.length" class="muted">{{ t('暂无标签数据') }}</p>
        <p class="atlas-foot">{{ t('累计打标人次') }} {{ totalCover.toLocaleString('zh-CN') }}</p>
      </aside>

      <!-- 右：编辑器 + 底部双卡 -->
      <div class="right-col">
        <section class="panel editor">
          <div class="editor-accent" aria-hidden="true" />
          <div class="editor-head">
            <div>
              <h2>
                {{ t('分群编辑器') }}
                <span class="ai-badge">{{ t('规则') }}</span>
              </h2>
              <p>{{ t('配置召回营销逻辑。') }}</p>
            </div>
            <div class="editor-actions">
              <button type="button" class="btn-ghost">{{ t('存为草稿') }}</button>
              <button type="button" class="btn-primary">{{ t('生成执行 标准作业程序') }}</button>
            </div>
          </div>

          <div class="rule-box">
            <div class="rule-match">
              <span class="match-label">{{ t('符合') }}</span>
              <select class="sel">
                <option>{{ t('全部条件') }}</option>
                <option>{{ t('任意条件') }}</option>
              </select>
            </div>

            <div class="rule-stack">
              <div class="rule-row">
                <select class="sel w-28">
                  <option>{{ t('渠道') }}</option>
                  <option>{{ t('标签') }}</option>
                  <option>{{ t('最近入住') }}</option>
                </select>
                <span class="op">{{ t('等于') }}</span>
                <span class="chip-on">{{ t('私域 小程序') }}</span>
              </div>

              <div class="and-mark">{{ t('并且') }}</div>

              <div class="rule-row">
                <select class="sel w-28">
                  <option>{{ t('最近入住') }}</option>
                  <option>{{ t('渠道') }}</option>
                  <option>{{ t('标签') }}</option>
                </select>
                <span class="op">{{ t('早于') }}</span>
                <input class="inp" type="text" value="90天前" readonly />
              </div>
            </div>

            <button type="button" class="link-add">{{ t('添加条件') }}</button>
          </div>

          <div class="action-bar">
            <div>
              <div class="action-title">{{ t('执行动作') }}</div>
              <div class="action-desc">{{ t('企微 标准作业程序 推送 + ￥50 唤醒代金券') }}</div>
            </div>
            <button type="button" class="link">{{ t('编辑配置') }}</button>
          </div>
        </section>

        <div class="bottom-grid">
          <section class="panel predict">
            <h3>{{ t('转化预测') }}</h3>
            <p class="muted">{{ t('基于该规则集的历史数据。') }}</p>
            <div class="rate-row">
              <div class="rate">{{ convRate }} <span>%</span></div>
              <div class="delta">{{ t('较均值 +0.8%') }}</div>
            </div>
            <div class="bars">
              <div class="bar-item">
                <div class="bar-meta">
                  <span>{{ t('触达人数') }}</span>
                  <span class="num">{{ previewReach.toLocaleString('zh-CN') }}</span>
                </div>
                <div class="bar"><i style="width: 100%" /></div>
              </div>
              <div class="bar-item">
                <div class="bar-meta">
                  <span>{{ t('预计成单') }}</span>
                  <span class="num">{{ expectOrders }}</span>
                </div>
                <div class="bar">
                  <i class="tertiary" :style="{ width: Math.min(100, convRate * 8) + '%' }" />
                </div>
              </div>
            </div>
          </section>

          <section class="panel active">
            <div class="active-head">
              <h3>{{ t('活跃分群') }}</h3>
              <button type="button" class="link" @click="goCohort">{{ t('客群列表 →') }}</button>
            </div>
            <div class="active-list">
              <button
                v-for="s in activeSegs"
                :key="s.id"
                type="button"
                class="active-item"
                @click="openSeg(s.name)"
              >
                <div class="active-left">
                  <span class="dot" :class="s.tone" />
                  <div>
                    <div class="active-name">{{ s.name }}</div>
                    <div class="active-sub">{{ s.channel }} · {{ s.ruleCn }}</div>
                  </div>
                </div>
                <div class="active-right">
                  <div class="active-n">
                    {{ Number(s.member_count || 0).toLocaleString('zh-CN') }} {{ t('人') }}
                  </div>
                  <div class="active-pct">{{ t('占总量') }} {{ s.pct }}%</div>
                </div>
              </button>
              <p v-if="!activeSegs.length" class="muted">{{ t('暂无分群') }}</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.seg {
  max-width: 1180px;
}

.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 20px;
}
.head h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.02em;
}
.head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant);
}

.btn-primary {
  border: none;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 13px;
  font-weight: 650;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 91, 191, 0.18);
}
.btn-primary:hover {
  filter: brightness(1.05);
}
.btn-ghost {
  border: 1px solid var(--outline-variant);
  background: #fff;
  color: var(--on-surface);
  font-size: 13px;
  font-weight: 650;
  padding: 9px 14px;
  border-radius: 10px;
  cursor: pointer;
}
.btn-ghost:hover {
  background: var(--surface-container-low);
}

.grid-main {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
@media (max-width: 980px) {
  .grid-main {
    grid-template-columns: 1fr;
  }
}

.panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 16px;
  box-shadow: 0 6px 18px rgba(25, 28, 29, 0.03);
}
.panel h2,
.panel h3 {
  margin: 0;
  font-weight: 750;
}
.panel h2 {
  font-size: 17px;
}
.panel h3 {
  font-size: 16px;
}
.muted {
  color: var(--on-surface-variant);
  font-size: 13px;
}
.link,
.link-add {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  padding: 0;
}
.link-add {
  margin-top: 12px;
}
.link:hover,
.link-add:hover {
  text-decoration: underline;
}

/* 图谱 */
.atlas {
  padding: 20px 18px;
}
.atlas-block {
  margin-top: 18px;
}
.atlas-block h3 {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--on-surface-variant);
}
.pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pill {
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-high);
  color: var(--on-surface);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}
.pill:hover {
  border-color: color-mix(in srgb, var(--primary) 40%, var(--outline-variant));
}
.pill.on {
  background: var(--primary-container);
  border-color: var(--primary-container);
  color: var(--on-primary-container);
}
.pill.on.accent {
  background: var(--tertiary-container);
  border-color: var(--tertiary-container);
  color: #fff;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tertiary) 18%, transparent);
}
.atlas-foot {
  margin: 20px 0 0;
  padding-top: 14px;
  border-top: 1px dashed var(--outline-variant);
  font-size: 12px;
  color: var(--on-surface-variant);
}

.right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* 编辑器 */
.editor {
  position: relative;
  overflow: hidden;
  padding: 20px 20px 18px;
}
.editor-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--tertiary);
}
.editor-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.editor-head p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.ai-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  vertical-align: middle;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--tertiary-container);
  color: #fff;
}
.editor-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rule-box {
  background: var(--surface-container);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 14px;
}
.rule-match {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.match-label {
  font-size: 13px;
  font-weight: 700;
  width: 36px;
}
.sel {
  border: 1px solid var(--outline-variant);
  background: #fff;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--on-surface);
}
.w-28 {
  width: 112px;
}
.rule-stack {
  position: relative;
  margin-left: 8px;
  padding-left: 16px;
  border-left: 2px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rule-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  background: #fff;
  border: 1px solid color-mix(in srgb, var(--outline-variant) 80%, transparent);
  border-radius: 10px;
  padding: 10px 12px;
}
.op {
  font-size: 13px;
  color: var(--on-surface-variant);
}
.chip-on {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--primary-container);
  color: var(--on-primary-container);
  font-size: 12px;
  font-weight: 650;
}
.inp {
  flex: 1;
  min-width: 140px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  background: #fff;
}
.and-mark {
  align-self: flex-start;
  margin-left: -28px;
  font-size: 10px;
  font-weight: 750;
  color: var(--tertiary);
  background: var(--tertiary-fixed);
  padding: 2px 6px;
  border-radius: 6px;
}

.action-bar {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed var(--outline-variant);
  background: var(--surface-container-low);
}
.action-title {
  font-size: 13px;
  font-weight: 700;
}
.action-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--on-surface-variant);
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 860px) {
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

.predict {
  padding: 18px;
  border-left: 4px solid var(--outline-variant);
}
.predict .muted {
  margin: 6px 0 14px;
}
.rate-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}
.rate {
  font-size: 40px;
  font-weight: 750;
  line-height: 1;
  letter-spacing: -0.03em;
}
.rate span {
  font-size: 20px;
  margin-left: 2px;
}
.delta {
  font-size: 13px;
  font-weight: 650;
  color: var(--on-surface-variant);
  padding-bottom: 6px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-bottom: 6px;
}
.bar-meta .num {
  color: var(--on-surface);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.bar {
  height: 8px;
  border-radius: 999px;
  background: var(--surface-container);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  background: var(--primary);
  border-radius: inherit;
}
.bar i.tertiary {
  background: var(--tertiary);
}

.active {
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
}
.active-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 0 4px;
}
.active-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.active-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 12px;
  padding: 10px;
  cursor: pointer;
}
.active-item:hover {
  background: var(--surface-container-low);
  border-color: color-mix(in srgb, var(--outline-variant) 70%, transparent);
}
.active-left {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--outline);
}
.dot.ok {
  background: #22c55e;
}
.dot.warn {
  background: #f59e0b;
}
.active-name {
  font-size: 13px;
  font-weight: 700;
}
.active-sub {
  margin-top: 2px;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.active-right {
  text-align: right;
  flex-shrink: 0;
}
.active-n {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.active-pct {
  font-size: 10px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
</style>
