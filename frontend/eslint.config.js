// SPDX-License-Identifier: Apache-2.0
import js from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default [
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'src/locales/**',
      'src/views/c7-supplies/inventory-2-stock-levels.vue',
    ],
  },
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
        sourceType: 'module',
      },
    },
  },
  {
    files: ['**/*.ts'],
    ...js.configs.recommended,
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: { sourceType: 'module' },
    },
  },
  eslintConfigPrettier,
  {
    files: ['**/*.{js,ts,vue}'],
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/no-mutating-props': 'off',
      'vue/valid-template-root': 'off',
      'vue/no-textarea-mustache': 'off',
      'vue/valid-v-for': 'off',
      'vue/valid-attribute-name': 'off',
      'vue/no-unused-vars': 'off',
      'no-undef': 'off',
      'no-unused-vars': 'off',
      'no-useless-escape': 'off',
      'no-redeclare': 'off',
      'no-empty': 'off',
    },
  },
]
