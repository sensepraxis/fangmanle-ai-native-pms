// SPDX-License-Identifier: Apache-2.0
import { t, localeHeader } from './i18n'
/**
 * 企业微信聊天工具栏 JS-SDK：getContext + sendChatMessage（不走群发助手）。
 * SDK 走 npm 打包，避免企微 WebView 拦截 unpkg 外链。
 */
export type WecomContext = {
  entry?: string
  externalUserId?: string
  userId?: string
}

let ready = false
let contextCache: WecomContext | null = null
let wwModule: typeof import('@wecom/jssdk') | null = null

function signUrl(): string {
  return window.location.href.split('#')[0]
}

async function fetchSign(pageUrl?: string) {
  const url = (pageUrl || signUrl()).split('#')[0]
  const res = await fetch(`/api/wecom/jssdk-sign?url=${encodeURIComponent(url)}`, {
    headers: localeHeader(),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.detail || json.message || '获取 JS-SDK 签名失败')
  }
  return json.data as {
    corpId: string
    agentId: string
    config: { timestamp: number; nonceStr: string; signature: string }
    agent: { timestamp: number; nonceStr: string; signature: string }
    jsApiList: string[]
  }
}

async function getWw() {
  if (!wwModule) {
    wwModule = await import('@wecom/jssdk')
  }
  if (!wwModule?.register) throw new Error('企微 JS-SDK 未就绪')
  return wwModule
}

export function isWecomUa(): boolean {
  return /wxwork|WeCom|MicroMessenger/i.test(navigator.userAgent)
}

export async function initWecomSidebarSdk(): Promise<WecomContext> {
  if (ready && contextCache) return contextCache
  const ww = await getWw()
  const sign = await fetchSign()

  ww.register({
    corpId: sign.corpId,
    agentId: sign.agentId,
    jsApiList: sign.jsApiList || ['getContext', 'getCurExternalContact', 'sendChatMessage'],
    getConfigSignature: async (url) => (await fetchSign(url)).config,
    getAgentConfigSignature: async (url) => (await fetchSign(url)).agent,
  })

  const ctx = await ww.getContext()
  let externalUserId: string | undefined
  try {
    const ext = await ww.getCurExternalContact()
    externalUserId = ext.userId
  } catch {
    externalUserId = (ctx as any)?.externalUserId || (ctx as any)?.external_userid
  }

  contextCache = {
    entry: ctx?.entry,
    externalUserId,
    userId: (ctx as any)?.userId || (ctx as any)?.userid,
  }
  ready = true
  return contextCache
}

export async function sendWecomChatText(content: string): Promise<void> {
  const text = (content || '').trim()
  if (!text) throw new Error('消息内容不能为空')
  const ww = await getWw()
  const res = await ww.sendChatMessage({
    msgtype: 'text',
    enterChat: false,
    text: { content: text.slice(0, 2000) },
  })
  if (res.errMsg && !/ok$/i.test(res.errMsg)) {
    throw new Error(res.errMsg)
  }
}

export function isSidebarChatEntry(entry?: string): boolean {
  return entry === 'single_chat_tools' || entry === 'chat_attachment'
}
