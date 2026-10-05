// SPDX-License-Identifier: Apache-2.0
import { t } from './i18n'
/**
 * 地图 JS 懒加载：天地图（默认）/ 高德
 * 天地图底图经同源代理 /api/system/map-tile，避免浏览器端瓦片 403 裂图。
 * 交互底图使用 Web 墨卡托 vec_w + cva_w（道路 + 注记），局部中心缩放。
 */
declare global {
  interface Window {
    T?: any
    AMap?: any
    _AMapSecurityConfig?: { securityJsCode?: string }
  }
}

let tdLoading: Promise<any> | null = null
let tdLoadedTk: string | null = null
let amapLoading: Promise<any> | null = null

function tileProxyBase(tilesUrl?: string | null): string {
  const path = (tilesUrl || '/api/v1/system/map-tile').replace(/\/+$/, '')
  if (typeof window === 'undefined') return path.startsWith('http') ? path : path
  if (path.startsWith('http')) return path
  return `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`
}

/** 清空默认层，改挂同源代理底图（图层名来自后端 IMap.render_config.tile_layers） */
export function applyTiandituBaseLayers(
  T: any,
  map: any,
  _tk?: string,
  opts?: { tilesUrl?: string | null; tileLayers?: string[] | null },
) {
  if (!T || !map) return
  try {
    const layers = map.getLayers?.() || []
    for (let i = layers.length - 1; i >= 0; i--) {
      try {
        map.removeLayer(layers[i])
      } catch {
        /* ignore */
      }
    }
  } catch {
    /* ignore */
  }

  const base = tileProxyBase(opts?.tilesUrl)
  // 默认天地图墨卡托道路+注记；其它图商由 render_config.tile_layers 指定
  const names = opts?.tileLayers?.length ? opts.tileLayers : ['vec_w', 'cva_w']
  const mk = (layer: string) => {
    const url = `${base}/${layer}/{z}/{y}/{x}`
    return new T.TileLayer(url, { minZoom: 3, maxZoom: 18, opacity: 1 })
  }
  try {
    for (const name of names) map.addLayer(mk(name))
  } catch (e) {
    console.warn('[map] addLayer failed', e)
  }
}

/** 创建天地图实例：墨卡托投影 + 代理底图 + 缩放控件 */
export function createTiandituMap(T: any, el: HTMLElement) {
  const map = new T.Map(el, { projection: 'EPSG:3857' })
  applyTiandituBaseLayers(T, map)
  try {
    map.enableScrollWheelZoom?.()
    map.enableDoubleClickZoom?.()
    map.enableDrag?.()
    map.enableInertia?.()
  } catch {
    /* ignore */
  }
  try {
    if (T.Control?.Zoom) map.addControl(new T.Control.Zoom())
  } catch {
    /* ignore */
  }
  return map
}

/** 局部放大：按检索半径落到街区尺度，并固定中心缩放（不依赖 setViewport） */
export function focusTiandituLocal(T: any, map: any, lng: number, lat: number, radiusKm: number) {
  if (!T || !map) return
  const r = Math.max(0.5, Number(radiusKm) || 3)
  // 墨卡托下：3km≈15，5km≈14（再大一级会只见色块、不见路网）
  const want = r >= 5 ? 14 : 15
  try {
    map.enableScrollWheelZoom?.()
    map.enableDoubleClickZoom?.()
    map.enableDrag?.()
  } catch {
    /* ignore */
  }
  try {
    map.centerAndZoom(new T.LngLat(lng, lat), want)
  } catch {
    /* ignore */
  }
  // 下一帧再钉一次，避免默认全国视野盖住
  try {
    window.setTimeout(() => {
      try {
        const cur = Number(map.getZoom?.() || 0)
        if (!cur || Math.abs(cur - want) > 0.5) {
          map.centerAndZoom(new T.LngLat(lng, lat), want)
        }
      } catch {
        /* ignore */
      }
    }, 80)
  } catch {
    /* ignore */
  }
}

export async function loadTianditu(tk: string, scriptUrl?: string | null): Promise<any> {
  if (typeof window === 'undefined') throw new Error('仅浏览器可用')
  if (!tk) throw new Error('未配置天地图浏览器端 JS Key（不可用服务器端 Key 代替）')

  const existed = document.querySelector('script[data-tianditu="1"]') as HTMLScriptElement | null
  if (existed && existed.dataset.tk && existed.dataset.tk !== tk) {
    existed.remove()
    try {
      delete (window as any).T
    } catch {
      ;(window as any).T = undefined
    }
    tdLoading = null
    tdLoadedTk = null
  }

  if (window.T?.Map && tdLoadedTk === tk) return window.T
  if (tdLoading && tdLoadedTk === tk) return tdLoading

  tdLoadedTk = tk
  tdLoading = new Promise((resolve, reject) => {
    const again = document.querySelector('script[data-tianditu="1"]') as HTMLScriptElement | null
    if (again && again.dataset.tk === tk) {
      const done = () => (window.T?.Map ? resolve(window.T) : reject(new Error('天地图未就绪')))
      if (window.T?.Map) done()
      else {
        again.addEventListener('load', done)
        again.addEventListener('error', () => reject(new Error('天地图脚本加载失败')))
      }
      return
    }
    const s = document.createElement('script')
    s.dataset.tianditu = '1'
    s.dataset.tk = tk
    s.async = true
    s.referrerPolicy = 'strict-origin-when-cross-origin'
    s.src = scriptUrl || `https://api.tianditu.gov.cn/api?v=4.0&tk=${encodeURIComponent(tk)}`
    s.onload = () => {
      if (window.T?.Map) resolve(window.T)
      else reject(new Error('天地图 T.Map 未就绪'))
    }
    s.onerror = () => reject(new Error('天地图脚本加载失败'))
    document.head.appendChild(s)
  })
  try {
    return await tdLoading
  } catch (e) {
    tdLoading = null
    tdLoadedTk = null
    throw e
  }
}

export async function loadAmap(
  jsKey: string,
  securityJsCode?: string | null,
  scriptUrl?: string | null,
): Promise<any> {
  if (typeof window === 'undefined') throw new Error('仅浏览器可用')
  if (window.AMap) return window.AMap
  if (!jsKey) throw new Error('未配置高德 JS Key')
  if (amapLoading) return amapLoading

  amapLoading = new Promise((resolve, reject) => {
    if (securityJsCode) {
      window._AMapSecurityConfig = { securityJsCode }
    }
    const existed = document.querySelector('script[data-amap="1"]') as HTMLScriptElement | null
    if (existed) {
      existed.addEventListener('load', () => resolve(window.AMap))
      existed.addEventListener('error', () => reject(new Error('高德脚本加载失败')))
      if (window.AMap) resolve(window.AMap)
      return
    }
    const s = document.createElement('script')
    s.dataset.amap = '1'
    s.async = true
    s.src = scriptUrl || `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(jsKey)}`
    s.onload = () => {
      if (window.AMap) resolve(window.AMap)
      else reject(new Error('AMap 未就绪'))
    }
    s.onerror = () => reject(new Error('高德脚本加载失败'))
    document.head.appendChild(s)
  })
  return amapLoading
}

/** 简易墨卡托投影：把 lng/lat 画到 SVG 视口 */
export function projectToSvg(
  lng: number,
  lat: number,
  center: { lng: number; lat: number },
  radiusKm: number,
  size = 360,
) {
  const kmPerDegLat = 111.32
  const kmPerDegLng = 111.32 * Math.cos((center.lat * Math.PI) / 180)
  const half = radiusKm * 1.15
  const x = size / 2 + (((lng - center.lng) * kmPerDegLng) / half) * (size / 2)
  const y = size / 2 - (((lat - center.lat) * kmPerDegLat) / half) * (size / 2)
  return { x, y }
}
