<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 竞品地图：只面向地图防腐层（lib/map + 后端 /map/*），不 import 天地图/高德 SDK。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import { collectMarkers, renderMap, type MapHandle } from '../../lib/map'

const props = defineProps<{
  config: any
  selectedCompetitors: any[]
}>()
const emit = defineEmits<{
  (e: 'config-change', cfg: any): void
  (e: 'added'): void
}>()

const address = ref('')
const radiusKm = ref<3 | 5>(3)
const loc = ref<{ address?: string; lng?: number; lat?: number; city?: string; source?: string }>(
  {},
)
const mapMeta = ref<any>(null)
const hotels = ref<any[]>([])
const checked = ref<Record<string, boolean>>({})
const busy = ref(false)
const mapEl = ref<HTMLElement | null>(null)
const mapNote = ref('')

let handle: MapHandle | null = null

const hasCenter = computed(() => loc.value.lng != null && loc.value.lat != null)
const provider = computed(
  () =>
    mapMeta.value?.js_config?.provider_id ||
    mapMeta.value?.js_config?.engine ||
    mapMeta.value?.engine ||
    mapMeta.value?.provider ||
    'tianditu',
)
const providerLabel = computed(
  () =>
    mapMeta.value?.provider_label ||
    (provider.value === 'gaode' || provider.value === 'amap'
      ? t('高德')
      : provider.value === 'noop'
        ? t('手工坐标')
        : provider.value === 'google'
          ? 'Google Maps'
          : provider.value === 'baidu'
            ? t('百度地图')
            : t('天地图')),
)
const selectedKeys = computed(() => Object.keys(checked.value).filter((k) => checked.value[k]))

function sourceToast(src?: string) {
  if (src === 'tianditu') return t('天地图')
  if (src === 'amap' || src === 'gaode') return t('高德')
  if (src === 'baidu') return t('百度地图')
  if (src === 'google') return 'Google Maps'
  if (src === 'noop') return t('手工坐标')
  return ''
}

onMounted(async () => {
  try {
    mapMeta.value = await api.paAmapStatus()
  } catch {
    mapMeta.value = {
      mode: 'demo',
      js_enabled: false,
      provider: 'tianditu',
      provider_label: '天地图',
    }
  }
  const sl = props.config?.self_location || {}
  if (sl.lng != null) {
    loc.value = { ...sl }
    address.value = sl.address || ''
  }
  const r = Number(props.config?.comp_radius_km || 3)
  radiusKm.value = r >= 5 ? 5 : 3
  if (!address.value) {
    try {
      const g = await api.paAmapGeocode(hotelStore.hotelId, { hint_only: true })
      if (g?.hotel_hint?.address) address.value = g.hotel_hint.address
      else if (g?.address) address.value = g.address
    } catch {
      /* ignore */
    }
  }
  if (hasCenter.value) {
    await searchNearby()
  }
})

onBeforeUnmount(() => {
  handle?.destroy()
  handle = null
})

watch(radiusKm, async (v) => {
  try {
    const cfg = await api.paUpdateConfig(hotelStore.hotelId, { params: { comp_radius_km: v } })
    emit('config-change', cfg)
  } catch {
    /* ignore */
  }
  if (hasCenter.value) await searchNearby()
})

watch(
  () => props.selectedCompetitors,
  () => {
    nextTick(() => paintMap())
  },
  { deep: true },
)

async function resolveAddress() {
  if (!address.value.trim()) {
    toast(t('请先输入本店地址'), false)
    return
  }
  busy.value = true
  try {
    const g = await api.paAmapGeocode(hotelStore.hotelId, {
      address: address.value.trim(),
      save: true,
    })
    loc.value = {
      address: g.address,
      lng: g.lng,
      lat: g.lat,
      city: g.city,
      source: g.source,
    }
    address.value = g.address || address.value
    mapNote.value = g.note || `${sourceToast(g.source)}地理编码`
    const cfg = await api.paConfig(hotelStore.hotelId)
    emit('config-change', cfg)
    toast(t('本店位置已定位（{src}）', { src: sourceToast(g.source) }))
    await searchNearby()
  } catch (e: any) {
    toast(e?.message || t('地址解析失败'), false)
  } finally {
    busy.value = false
  }
}

async function searchNearby() {
  if (!hasCenter.value) return
  busy.value = true
  try {
    const data = await api.paAmapNearby(hotelStore.hotelId, {
      lng: loc.value.lng,
      lat: loc.value.lat,
      radius_km: radiusKm.value,
    })
    hotels.value = data.hotels || []
    checked.value = {}
    mapNote.value = data.note || `${sourceToast(data.source)}周边酒店`
    await nextTick()
    await paintMap()
  } catch (e: any) {
    toast(e?.message || t('周边检索失败'), false)
  } finally {
    busy.value = false
  }
}

async function paintMap() {
  if (!hasCenter.value || !mapEl.value) return
  handle?.destroy()
  handle = null
  const jsConfig = mapMeta.value?.js_config || {
    engine: mapMeta.value?.engine || mapMeta.value?.provider || 'noop',
    js_enabled: mapMeta.value?.js_enabled,
    js_key: mapMeta.value?.js_key,
    security_js_code: mapMeta.value?.security_js_code,
    script_url: mapMeta.value?.script_url,
  }
  handle = await renderMap({
    el: mapEl.value,
    center: { lng: Number(loc.value.lng), lat: Number(loc.value.lat) },
    radiusKm: radiusKm.value,
    markers: collectMarkers({
      hotels: hotels.value,
      checked: checked.value,
      selectedCompetitors: props.selectedCompetitors || [],
    }),
    jsConfig,
    selfLabel: t('本店'),
  })
}

function toggleHotel(h: any) {
  const k = h.poi_id || h.comp_name
  checked.value = { ...checked.value, [k]: !checked.value[k] }
  nextTick(() => paintMap())
}

async function addSelected() {
  const list = hotels.value.filter((h) => checked.value[h.poi_id || h.comp_name])
  if (!list.length) {
    toast(t('请先勾选竞品酒店'), false)
    return
  }
  busy.value = true
  try {
    for (const h of list) {
      await api.paAddCompetitor(hotelStore.hotelId, {
        comp_name: h.comp_name,
        comp_lat: h.comp_lat,
        comp_lng: h.comp_lng,
        address: h.address,
        distance_km: h.distance_km,
        data_source: h.data_source || provider.value || 'tianditu',
        source_ref: h.source_ref || 'map_select',
      })
    }
    toast(t('已加入 {n} 家竞品', { n: list.length }))
    checked.value = {}
    emit('added')
    await paintMap()
  } catch (e: any) {
    toast(e?.message || t('加入失败'), false)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="cmap">
    <div class="sec-title">{{ t('本店定位与周边检索（') }}{{ providerLabel }}）</div>
    <p v-if="mapNote" class="map-note">{{ mapNote }}</p>

    <div class="loc-row">
      <input
        v-model="address"
        class="addr"
        :placeholder="t('手动输入本店地址，如：广州市天河区××路××号')"
      />
      <button type="button" class="btn btn-primary sm" :disabled="busy" @click="resolveAddress">
        {{ t('解析定位') }}
      </button>
    </div>

    <div class="radius-row">
      <span class="lbl">{{ t('搜索半径') }}</span>
      <label class="radio"
        ><input v-model="radiusKm" type="radio" :value="3" /> {{ t('3 公里') }}</label
      >
      <label class="radio"
        ><input v-model="radiusKm" type="radio" :value="5" /> {{ t('5 公里') }}</label
      >
      <button
        type="button"
        class="btn btn-ghost sm"
        :disabled="busy || !hasCenter"
        @click="searchNearby"
      >
        {{ t('刷新周边酒店') }}
      </button>
      <span v-if="loc.lng != null" class="coord-box" :title="t('本酒店坐标')">
        <span class="coord-label">{{ t('本酒店坐标') }}</span>
        <span class="coord-val">{{ loc.lng?.toFixed?.(5) }}, {{ loc.lat?.toFixed?.(5) }}</span>
      </span>
    </div>

    <div class="map-layout">
      <div ref="mapEl" class="map-canvas" />
      <div class="hotel-list">
        <div class="list-head">
          {{ t('周边酒店（') }}{{ hotels.length }}）
          <button
            type="button"
            class="btn btn-primary sm"
            :disabled="busy || !selectedKeys.length"
            @click="addSelected"
          >
            {{ t('加入勾选（') }}{{ selectedKeys.length }}）
          </button>
        </div>
        <div v-if="!hotels.length" class="empty">
          {{
            hasCenter
              ? t('未检索到周边住宿 POI，可点「刷新周边酒店」或到步骤 2 手工补充')
              : t('先解析本店地址，再检索周边酒店')
          }}
        </div>
        <label v-for="h in hotels" :key="h.poi_id || h.comp_name" class="hotel">
          <input
            type="checkbox"
            :checked="!!checked[h.poi_id || h.comp_name]"
            @change="toggleHotel(h)"
          />
          <div class="meta">
            <div class="nm">{{ h.comp_name }}</div>
            <div class="sub">{{ h.distance_km }} {{ t('公里 ·') }} {{ h.address }}</div>
          </div>
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cmap {
  margin-bottom: 14px;
}
.sec-title {
  font-size: 13px;
  font-weight: 650;
  margin-bottom: 6px;
}
.map-note {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.loc-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.addr,
.loc-row input {
  flex: 1;
  min-width: 180px;
  padding: 7px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
}
.radius-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-size: 12px;
}
.lbl {
  color: var(--on-surface-variant);
}
.radio {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
.coord-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: 6px;
  background: #dbeafe;
  color: #1e3a8a;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
}
.coord-label {
  font-weight: 650;
  color: #1d4ed8;
  white-space: nowrap;
}
.coord-val {
  letter-spacing: 0.02em;
}
.map-layout {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
  min-height: 320px;
}
.map-canvas {
  height: 320px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}
.hotel-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: auto;
  max-height: 320px;
  background: #fff;
}
.list-head {
  position: sticky;
  top: 0;
  background: #f9fafb;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  border-bottom: 1px solid #edf1f6;
  z-index: 1;
}
.hotel {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  font-size: 12px;
}
.hotel:hover {
  background: #f8fafc;
}
.meta .nm {
  font-weight: 600;
}
.meta .sub {
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.empty {
  padding: 24px;
  text-align: center;
  color: var(--on-surface-variant);
  font-size: 12px;
}
.sm {
  padding: 5px 10px;
  font-size: 12px;
}
@media (max-width: 900px) {
  .map-layout {
    grid-template-columns: 1fr;
  }
}
</style>
