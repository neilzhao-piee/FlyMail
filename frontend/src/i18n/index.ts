import { createI18n } from 'vue-i18n'
import en from './en'

export const LOCALE_KEY = 'flymail_locale'
export const SUPPORTED_LOCALES = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en', label: 'English' },
]

function initialLocale(): string {
  const saved = localStorage.getItem(LOCALE_KEY)
  if (saved === 'en' || saved === 'zh-CN') return saved
  return navigator.language?.toLowerCase().startsWith('en') ? 'en' : 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'zh-CN',
  // 中文文案直接以中文原文作为 key：zh 不配置 messages 时 t() 回退返回 key 本身
  messages: { en } as any,
  missingWarn: false,
  fallbackWarn: false,
})

export function currentLocale(): string {
  return i18n.global.locale.value as string
}

export function setLocale(locale: string): void {
  if (locale !== 'en' && locale !== 'zh-CN') return
  i18n.global.locale.value = locale
  localStorage.setItem(LOCALE_KEY, locale)
  document.documentElement.lang = locale === 'en' ? 'en' : 'zh-CN'
}

document.documentElement.lang = currentLocale() === 'en' ? 'en' : 'zh-CN'
