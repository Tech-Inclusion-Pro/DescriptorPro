// Minimal i18n matching core/i18n.py semantics: flat key dict per language,
// en fallback, RTL for ar/arz/ur. ui/scripts/export-translations.py merges
// keys from core/translations.py with the UI-only keys in this folder.

import { create } from 'zustand'
import en from './en.json'
import es from './es.json'

// Engine strings for all 23 languages, generated from core/translations.py
// by ui/scripts/export-translations.py. Hand-written UI keys (en/es) win on
// conflict; the other 21 languages fall back to en for UI-only keys.
const GENERATED = import.meta.glob<Record<string, string>>('./generated/*.core.json', {
  eager: true,
  import: 'default',
})

const DICTS: Record<string, Record<string, string>> = {}
for (const [path, dict] of Object.entries(GENERATED)) {
  const lang = path.replace('./generated/', '').replace('.core.json', '')
  DICTS[lang] = { ...dict }
}
DICTS.en = { ...(DICTS.en ?? {}), ...en }
DICTS.es = { ...(DICTS.es ?? {}), ...es }

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

// Matches core/translations.py LANGUAGE_OPTIONS (23 languages).
export const AVAILABLE_LANGUAGES: Array<[string, string]> = [
  ['en', 'English'],
  ['zh', '中文 (Chinese)'],
  ['hi', 'हिन्दी (Hindi)'],
  ['es', 'Español (Spanish)'],
  ['fr', 'Français (French)'],
  ['ar', 'العربية (Arabic)'],
  ['bn', 'বাংলা (Bengali)'],
  ['pt', 'Português (Portuguese)'],
  ['ru', 'Русский (Russian)'],
  ['ur', 'اردو (Urdu)'],
  ['id', 'Bahasa Indonesia'],
  ['de', 'Deutsch (German)'],
  ['ja', '日本語 (Japanese)'],
  ['pcm', 'Naijá (Nigerian Pidgin)'],
  ['arz', 'مصري (Egyptian Arabic)'],
  ['mr', 'मराठी (Marathi)'],
  ['te', 'తెలుగు (Telugu)'],
  ['tr', 'Türkçe (Turkish)'],
  ['ta', 'தமிழ் (Tamil)'],
  ['yue', '粵語 (Cantonese)'],
  ['vi', 'Tiếng Việt (Vietnamese)'],
  ['tl', 'Filipino (Tagalog)'],
  ['it', 'Italiano (Italian)'],
]

// Apply persisted language before first paint.
const initial = useI18n.getState().lang
document.documentElement.lang = initial
document.documentElement.dir = RTL.has(initial) ? 'rtl' : 'ltr'
