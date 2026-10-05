// SPDX-License-Identifier: Apache-2.0
/** 通用地图模型：价格助手等业务只依赖本类型 + renderMap，不 import 图商 SDK。 */

export type MapPoint = {
  lng: number
  lat: number
  label?: string
  kind?: 'self' | 'poi' | 'competitor'
}

export type MapJsConfig = {
  engine?: string
  provider_id?: string
  js_enabled?: boolean
  js_key?: string | null
  security_js_code?: string | null
  script_url?: string | null
  tiles_url?: string | null
}

export type RenderMapRequest = {
  el: HTMLElement
  center: { lng: number; lat: number }
  radiusKm: number
  markers: MapPoint[]
  jsConfig: MapJsConfig
  selfLabel?: string
}

export type MapHandle = {
  destroy: () => void
  engine: string
}
