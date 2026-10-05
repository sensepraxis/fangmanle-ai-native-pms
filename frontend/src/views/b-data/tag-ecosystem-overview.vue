<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 配置客群 · 治理枢纽
 * 治理轨：定义 → 打标 → 总览；找人保存分群在客群列表
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'

const router = useRouter()
const tagCount = ref(0)
const coverSum = ref(0)

onMounted(async () => {
  try {
    const rows = await api.listTags()
    tagCount.value = rows?.length || 0
    coverSum.value = (rows || []).reduce((s: number, t: any) => s + Number(t.cover_count || 0), 0)
  } catch {
    tagCount.value = 0
  }
})

type Card = {
  path: string
  title: string
  icon: string
  layer: string
  desc: string
}

const governCards: Card[] = [
  {
    path: '/b-data/master-tag-library',
    title: t('基础标签库'),
    icon: 'label',
    layer: t('① 定义'),
    desc: t('维护标签名称、分类维度与命中规则。是一切打标的母版。'),
  },
  {
    path: '/b-data/semantic-tag-rules',
    title: t('语义标签规则'),
    icon: 'rule',
    layer: t('② 打标'),
    desc: t('用自然语言条件自动打标，结果写入客人标签资产。'),
  },
  {
    path: '/b-data/guest-segmentation',
    title: t('标签体系与分群'),
    icon: 'donut_small',
    layer: t('③ 总览'),
    desc: t('按渠道 / RFM / 行为看标签图谱与人群分布。'),
  },
]

function go(path: string) {
  router.push(path)
}
function goCohortList() {
  router.push('/b-data/cohort-list')
}
</script>

<template>
  <div class="page hub">
    <header class="hero">
      <div class="hero-main">
        <p class="eyebrow">{{ t('客户会员 · 经营配置') }}</p>
        <h1 class="title">{{ t('配置客群') }}</h1>
        <p class="sub">
          {{ t('沉淀可复用的标签与分群资产。找人、客群比对请在') }}
          <button type="button" class="inline-link" @click="goCohortList">
            {{ t('客群列表') }}
          </button>
          {{ t('使用。') }}
        </p>
      </div>
      <div class="hero-aside">
        <button type="button" class="btn-back primary" @click="goCohortList">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('回客群列表') }}
        </button>
        <div class="kpis">
          <div class="kpi">
            <div class="kpi-ico">
              <span class="material-symbols-outlined">sell</span>
            </div>
            <div>
              <div class="kl">{{ t('标签定义') }}</div>
              <div class="kv">{{ tagCount }}</div>
            </div>
          </div>
          <div class="kpi">
            <div class="kpi-ico soft">
              <span class="material-symbols-outlined">group</span>
            </div>
            <div>
              <div class="kl">{{ t('累计打标人次') }}</div>
              <div class="kv">{{ coverSum.toLocaleString('zh-CN') }}</div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <section class="flow-map">
      <div class="sec-head">
        <h2 class="sec-h">{{ t('治理闭环') }}</h2>
        <p class="sec-sub">{{ t('定义标签 → 自动打标 → 体系总览') }}</p>
      </div>
      <div class="chain">
        <div class="node">
          <div class="node-ico">
            <span class="material-symbols-outlined">label</span>
          </div>
          <b>{{ t('定义') }}</b>
          <small>{{ t('标签库') }}</small>
        </div>
        <span class="arrow" aria-hidden="true">
          <span class="material-symbols-outlined">arrow_forward</span>
        </span>
        <div class="node">
          <div class="node-ico">
            <span class="material-symbols-outlined">rule</span>
          </div>
          <b>{{ t('打标') }}</b>
          <small>{{ t('语义规则') }}</small>
        </div>
        <span class="arrow" aria-hidden="true">
          <span class="material-symbols-outlined">arrow_forward</span>
        </span>
        <div class="node">
          <div class="node-ico">
            <span class="material-symbols-outlined">donut_small</span>
          </div>
          <b>{{ t('总览') }}</b>
          <small>{{ t('体系图谱') }}</small>
        </div>
      </div>
      <p class="chain-tip">
        {{ t('新建可投放客群请在客群列表用 AI 找人后保存，供运营任务与洞察使用。') }}
      </p>
    </section>

    <section class="track">
      <div class="sec-head">
        <div>
          <h2 class="sec-h">{{ t('治理轨 · 标签与分群资产') }}</h2>
          <p class="sec-sub">{{ t('按顺序配置，或按需进入任一环节') }}</p>
        </div>
        <span class="track-badge govern">{{ t('治理') }}</span>
      </div>
      <div class="card-grid">
        <button
          v-for="(c, i) in governCards"
          :key="c.path"
          type="button"
          class="mod-card"
          @click="go(c.path)"
        >
          <div class="mod-top">
            <span class="layer">{{ c.layer }}</span>
            <span class="ico-wrap">
              <span class="material-symbols-outlined ico">{{ c.icon }}</span>
            </span>
          </div>
          <h3>{{ c.title }}</h3>
          <p>{{ c.desc }}</p>
          <span class="enter">
            {{ t('进入') }}
            <span class="material-symbols-outlined">arrow_forward</span>
          </span>
          <span v-if="i < governCards.length - 1" class="card-next" aria-hidden="true" />
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hub {
  max-width: 1120px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.hero {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}
.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 650;
  color: var(--primary);
  letter-spacing: 0.04em;
}
.title {
  margin: 0;
  font-size: 28px;
  font-weight: 750;
}
.sub {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant);
  max-width: 560px;
  line-height: 1.5;
}
.inline-link {
  display: inline;
  padding: 0;
  border: none;
  background: none;
  color: var(--primary);
  font-weight: 650;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  font-size: inherit;
}
.hero-aside {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}
.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 9px 14px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 13px;
  font-weight: 650;
}
.btn-back.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.btn-back .material-symbols-outlined {
  font-size: 18px;
}
.kpis {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.kpi {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  min-width: 140px;
}
.kpi-ico {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}
.kpi-ico.soft {
  background: color-mix(in srgb, #16a34a 12%, transparent);
  color: #16a34a;
}
.kpi-ico .material-symbols-outlined {
  font-size: 20px;
}
.kl {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.kv {
  font-size: 20px;
  font-weight: 750;
  margin-top: 2px;
}

.flow-map,
.track {
  padding: 20px;
  border-radius: 16px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
}
.sec-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}
.sec-h {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.sec-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.track-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
}
.track-badge.govern {
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}

.chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 4px;
}
.node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 72px;
  padding: 10px 12px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--primary) 6%, transparent);
}
.node.soft {
  background: var(--surface-container);
}
.node-ico {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--primary);
  color: var(--on-primary);
}
.node-ico.mute {
  background: var(--surface-container-highest);
  color: var(--on-surface-variant);
}
.node-ico .material-symbols-outlined {
  font-size: 18px;
}
.node b {
  font-size: 13px;
}
.node small {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.arrow {
  display: grid;
  place-items: center;
  color: var(--on-surface-variant);
  padding: 0 2px;
}
.arrow .material-symbols-outlined {
  font-size: 20px;
}
.chain-tip {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 1100px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
}
.mod-card {
  position: relative;
  text-align: left;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 180px;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.mod-card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 14px rgba(0, 91, 191, 0.08);
}
.mod-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.layer {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
}
.ico-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}
.ico-wrap .ico {
  font-size: 20px;
}
.mod-card h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.mod-card p {
  margin: 0;
  flex: 1;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.enter {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 650;
  color: var(--primary);
}
.enter .material-symbols-outlined {
  font-size: 16px;
}
</style>
