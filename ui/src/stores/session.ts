import { create } from 'zustand'
import { api } from '../api/client'

interface SessionState {
  connected: boolean
  version: string | null
  checking: boolean
  checkHealth: () => Promise<void>
}

export const useSessionStore = create<SessionState>((set) => ({
  connected: false,
  version: null,
  checking: false,
  async checkHealth() {
    set({ checking: true })
    try {
      const health = await api.health()
      set({ connected: health.status === 'ok', version: health.version, checking: false })
    } catch {
      set({ connected: false, version: null, checking: false })
    }
  },
}))
