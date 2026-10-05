// SPDX-License-Identifier: Apache-2.0
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const localesDir = fileURLToPath(new URL('../locales', import.meta.url))

// 前后端分离：开发期前端(5173) 通过 /api 代理访问后端 FastAPI(8000)
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@locales': localesDir,
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: ['..'],
    },
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
