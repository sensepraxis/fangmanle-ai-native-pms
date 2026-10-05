// SPDX-License-Identifier: Apache-2.0
/**
 * 地图防腐层：按后端 render_config.engine 选择实现。
 * 业务页只调用 renderMap，不要直接 loadTianditu / loadAmap。
 */
import {
  createTiandituMap,
  focusTiandituLocal,
  loadAmap,
  loadTianditu,
  projectToSvg,
} from '../amap'
import type { MapHandle, MapPoint, RenderMapRequest } from './types'

function escapeXml(s: string) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function clearEl(el: HTMLElement) {
  el.innerHTML = ''
}

async function renderTianditu(req: RenderMapRequest): Promise<MapHandle> {
  const tk = req.jsConfig.js_key
  if (!tk) throw new Error('缺少浏览器端 JS Key')
  const T = await loadTianditu(tk, req.jsConfig.script_url)
  clearEl(req.el)
  const map = createTiandituMap(T, req.el)
  const { lng, lat } = req.center
  focusTiandituLocal(T, map, lng, lat, req.radiusKm)
  const circle = new T.Circle(new T.LngLat(lng, lat), req.radiusKm * 1000, {
    color: '#2563eb',
    weight: 2,
    opacity: 0.9,
    fillColor: '#3b82f6',
    fillOpacity: 0.12,
  })
  map.addOverLay(circle)
  map.addOverLay(new T.Marker(new T.LngLat(lng, lat)))
  map.addOverLay(
    new T.Label({
      text: req.selfLabel || '本店',
      position: new T.LngLat(lng, lat),
      offset: new T.Point(0, -24),
    }),
  )
  for (const m of req.markers) {
    if (m.kind === 'self') continue
    map.addOverLay(new T.Marker(new T.LngLat(m.lng, m.lat)))
  }
  focusTiandituLocal(T, map, lng, lat, req.radiusKm)
  return {
    engine: 'tianditu',
    destroy() {
      try {
        map.clearOverLays?.()
      } catch {
        /* ignore */
      }
      clearEl(req.el)
    },
  }
}

async function renderAmap(req: RenderMapRequest): Promise<MapHandle> {
  const AMap = await loadAmap(
    req.jsConfig.js_key || '',
    req.jsConfig.security_js_code,
    req.jsConfig.script_url,
  )
  clearEl(req.el)
  const { lng, lat } = req.center
  const map = new AMap.Map(req.el, {
    zoom: req.radiusKm === 5 ? 15 : 16,
    center: [lng, lat],
    viewMode: '2D',
  })
  const circle = new AMap.Circle({
    center: [lng, lat],
    radius: req.radiusKm * 1000,
    strokeColor: '#2563eb',
    strokeWeight: 2,
    strokeOpacity: 0.9,
    fillColor: '#3b82f6',
    fillOpacity: 0.12,
  })
  map.add(circle)
  map.add(
    new AMap.Marker({
      position: [lng, lat],
      title: req.selfLabel || '本店',
      label: { content: req.selfLabel || '本店', direction: 'top' },
    }),
  )
  const overlays: any[] = [circle]
  for (const m of req.markers) {
    if (m.kind === 'self') continue
    const mk = new AMap.Marker({
      position: [m.lng, m.lat],
      title: m.label || '',
    })
    map.add(mk)
    overlays.push(mk)
  }
  map.setFitView([circle], false, [48, 48, 48, 48])
  return {
    engine: 'amap',
    destroy() {
      overlays.forEach((o) => o.setMap?.(null))
      map.destroy?.()
      clearEl(req.el)
    },
  }
}

function renderSvg(req: RenderMapRequest): MapHandle {
  const size = 360
  const cx = size / 2
  const cy = size / 2
  const rPx = size / 2 / 1.15
  const pts: string[] = []
  pts.push(
    `<circle cx="${cx}" cy="${cy}" r="${rPx}" fill="rgba(59,130,246,.12)" stroke="#2563eb" stroke-width="2"/>`,
  )
  pts.push(
    `<circle cx="${cx}" cy="${cy}" r="6" fill="#2563eb"/><text x="${cx}" y="${cy - 12}" text-anchor="middle" font-size="11" fill="#1e40af" font-weight="700">${escapeXml(req.selfLabel || '本店')}</text>`,
  )
  for (const m of req.markers) {
    if (m.kind === 'self') continue
    const p = projectToSvg(m.lng, m.lat, req.center, req.radiusKm, size)
    const color = m.kind === 'competitor' ? '#dc2626' : '#7c3aed'
    const tc = m.kind === 'competitor' ? '#991b1b' : '#4c1d95'
    pts.push(
      `<circle cx="${p.x}" cy="${p.y}" r="5" fill="${color}"/><text x="${p.x + 8}" y="${p.y + 4}" font-size="10" fill="${tc}">${escapeXml(m.label || '')}</text>`,
    )
  }
  req.el.innerHTML = `<svg viewBox="0 0 ${size} ${size}" width="100%" height="100%" style="background:#f8fafc;border-radius:8px">${pts.join('')}</svg>`
  return {
    engine: 'svg',
    destroy() {
      clearEl(req.el)
    },
  }
}

/** 统一渲染入口：engine 来自后端 IMap.render_config() */
export async function renderMap(req: RenderMapRequest): Promise<MapHandle> {
  const engine = (req.jsConfig.engine || 'noop').toLowerCase()
  const live = !!(req.jsConfig.js_enabled && req.jsConfig.js_key)

  if (live && engine === 'tianditu') {
    try {
      return await renderTianditu(req)
    } catch (e: any) {
      console.warn('[map] tianditu failed, svg fallback', e)
    }
  }
  if (live && (engine === 'amap' || engine === 'gaode')) {
    try {
      return await renderAmap(req)
    } catch (e: any) {
      console.warn('[map] amap failed, svg fallback', e)
    }
  }
  // google / baidu / noop / 失败 → SVG 标注
  return renderSvg(req)
}

export function collectMarkers(args: {
  hotels: any[]
  checked: Record<string, boolean>
  selectedCompetitors: any[]
}): MapPoint[] {
  const out: MapPoint[] = []
  for (const h of args.hotels || []) {
    if (!args.checked[h.poi_id || h.comp_name]) continue
    out.push({
      lng: Number(h.comp_lng),
      lat: Number(h.comp_lat),
      label: h.comp_name,
      kind: 'poi',
    })
  }
  for (const c of args.selectedCompetitors || []) {
    if (!c.comp_lng || !c.comp_lat) continue
    out.push({
      lng: Number(c.comp_lng),
      lat: Number(c.comp_lat),
      label: `竞品·${c.comp_name}`,
      kind: 'competitor',
    })
  }
  return out
}
