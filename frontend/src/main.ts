// SPDX-License-Identifier: Apache-2.0
import { createApp, h } from 'vue'
import App from './App.vue'
import router from './router'
import './index.css'
import { initLocale, t } from './lib/i18n'

initLocale()

const app = createApp(App)
app.use(router)
app.config.globalProperties.$t = t
;(window as any).$t = t

// 重建前端后浏览器若仍缓存旧入口，懒加载 chunk 会 404，表现为“点了没跳转”
router.onError((err) => {
  const msg = String((err as any)?.message || err)
  if (
    /Failed to fetch dynamically imported module|Loading chunk|Importing a module script failed|error loading dynamically imported module/i.test(
      msg,
    )
  ) {
    const target = location.hash || '#/'
    location.replace(`${location.pathname}${location.search}${target}`)
    location.reload()
  }
})

// 全局挂载 ⌘K 命令面板：在 body 末尾生成一个独立根节点
import { defineComponent, ref, onMounted, onUnmounted } from 'vue'
import CommandPalette from './components/CommandPalette.vue'

const GlobalPaletteHost = defineComponent({
  setup() {
    const palette = ref<any>(null)
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        palette.value?.show()
      }
    }
    onMounted(() => document.addEventListener('keydown', onKey))
    onUnmounted(() => document.removeEventListener('keydown', onKey))
    return () =>
      h(CommandPalette, {
        ref: (el: any) => (palette.value = el),
      })
  },
})

app.mount('#app')

// 在 app 之后追加独立根节点给 ⌘K 面板
const globalRoot = document.createElement('div')
globalRoot.id = '__global_palette__'
document.body.appendChild(globalRoot)
createApp(GlobalPaletteHost).mount(globalRoot)

// 暴露到 window
;(window as any).__openPalette = () => {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true }))
}
