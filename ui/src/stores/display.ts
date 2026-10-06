// Display settings store: 1:1 port of the mockup widget's state model.
// Choices are stored on the device (localStorage) and applied as data-*
// attributes on <html>, which the palette CSS in styles/tokens.css reads.

import { create } from 'zustand'

export interface DisplayState {
  textsize: '0' | '1' | '2' | '3'
  spacing: '0' | '1' | '2'
  palette: 'brand' | 'cvd' | 'mono' | 'hc'
  cursor: 'default' | 'large' | 'xlarge' | 'contrast'
  motion: 'auto' | 'slow' | 'none'
  corner: 'br' | 'bl' | 'tr' | 'tl' | 'dock'
  dyslexic: boolean
  trail: boolean
  x: number | null
  y: number | null
  cornerChosen: boolean
}

const KEY = 'describe-studio-a11y-v1'

export const DEFAULTS: DisplayState = {
  textsize: '0',
  spacing: '0',
  palette: 'brand',
  cursor: 'default',
  motion: 'auto',
  corner: 'br',
  dyslexic: false,
  trail: false,
  x: null,
  y: null,
  cornerChosen: false,
}

function load(): DisplayState {
  try {
    const raw = window.localStorage.getItem(KEY)
    if (raw) return { ...DEFAULTS, ...(JSON.parse(raw) as Partial<DisplayState>) }
  } catch {
    /* fall through to defaults */
  }
  return { ...DEFAULTS }
}

function save(state: DisplayState): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    /* storage unavailable; settings stay for this session only */
  }
}

export function applyToDocument(state: DisplayState): void {
  const root = document.documentElement
  root.setAttribute('data-textsize', state.textsize)
  root.setAttribute('data-spacing', state.spacing)
  root.setAttribute('data-palette', state.palette)
  root.setAttribute('data-cursor', state.cursor)
  root.setAttribute('data-motion', state.motion)
  root.setAttribute('data-dyslexic', state.dyslexic ? 'on' : 'off')
  root.setAttribute('data-trail', state.trail ? 'on' : 'off')
}

interface DisplayStore extends DisplayState {
  set: (patch: Partial<DisplayState>) => void
  reset: () => void
}

export const useDisplayStore = create<DisplayStore>((set, get) => ({
  ...load(),
  set(patch) {
    set(patch)
    const { set: _s, reset: _r, ...state } = get()
    applyToDocument(state as DisplayState)
    save(state as DisplayState)
  },
  reset() {
    set({ ...DEFAULTS })
    applyToDocument(DEFAULTS)
    save(DEFAULTS)
  },
}))

// Apply persisted settings on module load, before first paint.
applyToDocument(load())
