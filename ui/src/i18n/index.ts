// Minimal i18n matching core/i18n.py semantics: flat key dict per language,
// en fallback, RTL for ar/arz/ur. ui/scripts/export-translations.py merges
// keys from core/translations.py with the UI-only keys in this folder.

import { create } from 'zustand'
import en from './en.json'
import es from './es.json'

const DICTS: Record<string, Record<string, string>> = { en, es }
const RTL = new Set(['ar', 'arz', 'ur'])
const KEY = 'describe-studio-lang'

interface I18nState {
  lang: string
  setLang: (lang: string) => void
}

export const useI18n = create<I18nState>((set) => ({
  lang: window.localStorage.getItem(KEY) ?? 'en',
  setLang(lang) {
    window.localStorage.setItem(KEY, lang)
    document.documentElement.lang = lang
    document.documentElement.dir = RTL.has(lang) ? 'rtl' : 'ltr'
    set({ lang })
  },
}))

export function t(key: string, vars?: Record<string, string | number>): string {
  const { lang } = useI18n.getState()
  let text = DICTS[lang]?.[key] ?? DICTS.en[key] ?? key
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value))
    }
  }
  return text
}

export const AVAILABLE_LANGUAGES: Array<[string, string]> = [
  ['en', 'English'],
  ['es', 'Español'],
]

// Apply persisted language before first paint.
const initial = useI18n.getState().lang
document.documentElement.lang = initial
document.documentElement.dir = RTL.has(initial) ? 'rtl' : 'ltr'
