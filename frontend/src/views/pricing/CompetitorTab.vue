<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const sets = ref<any[]>([])
const maps = ref<any[]>([])
const sources = ref<any[]>([])
const candidates = ref<any[]>([])
const rateForm = ref({
  comp_id: '',
  stay_date: new Date().toISOString().slice(0, 10),
  observed_price: '',
  channel: 'ota_ctrip',
  room_type_eq: '大床房',
})
const importText = ref('')

async function load() {
  const hid = hotelStore.hotelId
  ;[sets.value, maps.value, sources.value, candidates.value] = await Promise.all([
    api.paCompetitorSets(hid),
    api.paRoomMaps(hid),
    api.paDataSources(hid),
    api.paMapCandidates(hid),
  ])
  if (!rateForm.value.comp_id && sets.value[0]?.properties?.[0]) {
    rateForm.value.comp_id = sets.value[0].properties[0].comp_id
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

async function confirmCandidate(c: any) {
  try {
    await api.paAddCompetitor(hotelStore.hotelId, {
      comp_name: c.comp_name,
      comp_lat: c.comp_lat,
      comp_lng: c.comp_lng,
      star_rating: c.star_rating,
      review_score: c.review_score,
      distance_km: c.distance_km,
      data_source: 'manual',
      source_ref: 'ai_candidate_confirmed',
    })
    toast(t('已加入竞品集（商家确认）'))
    c.confirmed = true
    load()
  } catch (e: any) {
    toast(e?.message || t('加入失败'), false)
  }
}

async function submitRate() {
  try {
    await api.paCompetitorRate(hotelStore.hotelId, {
      ...rateForm.value,
      observed_price: Number(rateForm.value.observed_price),
      data_source: 'manual',
    })
    toast(t('已手工录入竞品客付挂牌价'))
    load()
  } catch (e: any) {
    toast(e?.message || t('录入失败'), false)
  }
}

async function doImport() {
  try {
    const r = await api.paImportCompetitorRates(hotelStore.hotelId, importText.value)
    toast(t('导入 {n} 条', { n: r.imported }))
    load()
  } catch (e: any) {
    toast(e?.message || t('导入失败'), false)
  }
}

function downloadTemplate() {
  const sample =
    'comp_id,stay_date,observed_price,channel,room_type_eq\n' +
    `${rateForm.value.comp_id || 'cp_xxx'},${rateForm.value.stay_date},428,ota_ctrip,大床房\n`
  const blob = new Blob([sample], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'competitor_rates_template.csv'
  a.click()
}
</script>

<template>
  <div>
    <div class="banner card-clean">
      <span class="material-symbols-outlined">travel_explore</span>
      <div>
        <b>{{ t('竞品由商家自主设置') }}</b
        >{{
          t('。AI 仅出候选需店长确认。地图为 Mock 选点（未接高德 Key）。 价格口径：录入竞品 OTA')
        }}
        <b>{{ t('公开展示客付价') }}</b
        >{{ t('，不是净到手。') }}
      </div>
    </div>

    <div class="grid2">
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('Mock 地图选点（3km）') }}</span>
          <span class="sub">{{ t('AI 候选需确认') }}</span>
        </div>
        <div class="map">
          <div class="pin self">{{ t('本店') }}</div>
          <div class="ring" />
          <div
            v-for="(c, i) in candidates"
            :key="c.candidate_id"
            class="pin cand"
            :style="{ left: 20 + i * 12 + '%', top: 30 + (i % 3) * 18 + '%' }"
            :title="c.comp_name"
          >
            {{ i + 1 }}
          </div>
        </div>
        <div class="cands">
          <div v-for="c in candidates" :key="c.candidate_id" class="cand-row">
            <div>
              <b>{{ c.comp_name }}</b>
              <div class="meta">
                {{ c.distance_km }}km · {{ c.star_rating }}{{ t('星 · 匹配') }} {{ c.match_score }}
              </div>
            </div>
            <button
              type="button"
              class="btn btn-primary"
              style="padding: 5px 10px; font-size: 12px"
              :disabled="c.confirmed"
              @click="confirmCandidate(c)"
            >
              {{ c.confirmed ? t('已加入') : t('确认加入') }}
            </button>
          </div>
        </div>
      </div>

      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('竞品集') }}</span>
        </div>
        <div v-for="s in sets" :key="s.set_id" class="set">
          <div class="set-h">
            <b>{{ s.set_name }}</b>
            <span class="pill pill-slate">{{ s.segment_tag }}</span>
            <span v-if="s.is_active" class="pill pill-blue">{{ t('默认') }}</span>
          </div>
          <div class="props">
            <div v-for="p in s.properties" :key="p.comp_id" class="prop">
              {{ p.comp_name }} · {{ p.distance_km }}km · {{ p.data_source }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card-clean" style="margin-top: 14px">
      <div class="card-head">
        <span>{{ t('竞品价数据源（合规标注）') }}</span>
      </div>
      <table class="data">
        <thead>
          <tr>
            <th>{{ t('竞品') }}</th>
            <th>{{ t('数据源') }}</th>
            <th>{{ t('合规级别') }}</th>
            <th>{{ t('采集频率') }}</th>
            <th>{{ t('最近采集') }}</th>
            <th>{{ t('状态') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in sources" :key="i">
            <td>{{ s.comp_name }}</td>
            <td>{{ s.data_source }}</td>
            <td>
              <span class="pill pill-slate">{{ s.compliance_level }}</span>
            </td>
            <td>{{ s.frequency }}</td>
            <td>{{ s.last_captured?.slice(0, 16) || '—' }}</td>
            <td>
              <span class="pill pill-green">{{ s.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card-clean" style="margin-top: 14px">
      <div class="card-head">
        <span>{{ t('房型映射（apples-to-apples）') }}</span>
      </div>
      <table class="data">
        <thead>
          <tr>
            <th>{{ t('竞品') }}</th>
            <th>{{ t('竞品房型（原始）') }}</th>
            <th>{{ t('→ 本店房型') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in maps" :key="m.map_id">
            <td>{{ m.comp_name }}</td>
            <td>{{ m.comp_room_type_raw }}</td>
            <td>{{ m.self_room_type_name }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card-clean" style="margin-top: 14px">
      <div class="card-head">
        <span>{{ t('小酒店取数兜底') }}</span>
      </div>
      <div class="fallback card-pad">
        <div class="box">
          <b>{{ t('P1 手工录入价') }}</b>
          <div class="form">
            <select v-model="rateForm.comp_id">
              <option v-for="p in sets[0]?.properties || []" :key="p.comp_id" :value="p.comp_id">
                {{ p.comp_name }}
              </option>
            </select>
            <input v-model="rateForm.stay_date" type="date" />
            <input v-model="rateForm.observed_price" type="number" :placeholder="t('OTA 客付价')" />
            <button type="button" class="btn btn-primary" @click="submitRate">
              {{ t('录入') }}
            </button>
          </div>
        </div>
        <div class="box">
          <b>{{ t('P2 引导式抄录') }}</b>
          <p class="hint">{{ t('打开竞品 OTA 公开链接，回填展示价（系统不爬登录态）。') }}</p>
          <a
            v-for="p in (sets[0]?.properties || []).slice(0, 3)"
            :key="p.comp_id"
            class="link"
            :href="p.ota_public_url"
            target="_blank"
            rel="noopener"
          >
            {{ p.comp_name }} ↗
          </a>
        </div>
        <div class="box">
          <b>{{ t('P2b Excel/CSV 导入') }}</b>
          <div class="form">
            <button type="button" class="btn btn-ghost" @click="downloadTemplate">
              {{ t('下载模板') }}
            </button>
          </div>
          <textarea v-model="importText" rows="4" :placeholder="t('粘贴 CSV 文本…')" />
          <button type="button" class="btn btn-primary" style="margin-top: 8px" @click="doImport">
            {{ t('导入') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--on-surface-variant);
}
.banner .material-symbols-outlined {
  color: var(--primary);
  font-size: 22px;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 900px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
.sub {
  font-size: 11px;
  color: var(--on-surface-variant);
  font-weight: 400;
}
.map {
  position: relative;
  height: 180px;
  margin: 12px;
  border-radius: 12px;
  background: linear-gradient(160deg, #e8f0fe 0%, var(--surface-low) 60%, #dbeafe 100%);
  border: 1px solid var(--outline-variant);
  overflow: hidden;
}
.ring {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 120px;
  height: 120px;
  margin: -60px 0 0 -60px;
  border: 2px dashed color-mix(in srgb, var(--primary) 40%, transparent);
  border-radius: 50%;
}
.pin {
  position: absolute;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
}
.pin.self {
  left: 50%;
  top: 50%;
  margin: -14px 0 0 -14px;
  background: var(--primary);
  width: auto;
  padding: 0 8px;
  border-radius: 14px;
  z-index: 2;
}
.pin.cand {
  background: #d97706;
}
.cands {
  padding: 0 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cand-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}
.meta {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.set {
  padding: 12px 16px;
  border-bottom: 1px solid var(--surface-high);
}
.set:last-child {
  border-bottom: none;
}
.set-h {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}
.prop {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.6;
}
.fallback {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 900px) {
  .fallback {
    grid-template-columns: 1fr;
  }
}
.box {
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
  background: var(--surface-lowest);
}
.hint {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin: 6px 0;
}
.form {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.form select,
.form input,
textarea {
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 7px 8px;
  font-size: 12px;
  width: 100%;
  box-sizing: border-box;
  background: #fff;
}
.link {
  display: block;
  font-size: 12px;
  margin-top: 4px;
  color: var(--primary);
  cursor: pointer;
}
</style>
