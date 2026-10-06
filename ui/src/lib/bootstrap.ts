// Service connection details. In the Electron shell the preload script injects
// window.__DS_BOOTSTRAP__ = { port, token }. In the Vite dev server the proxy
// forwards /api and /ws to the service, and the token comes from
// VITE_DS_TOKEN (exported by scripts/dev.sh).

export interface Bootstrap {
  port: number | null
  token: string
}

declare global {
  interface Window {
    __DS_BOOTSTRAP__?: { port: number; token: string }
  }
}

export function getBootstrap(): Bootstrap {
  if (window.__DS_BOOTSTRAP__) {
    return { ...window.__DS_BOOTSTRAP__ }
  }
  return {
    port: null, // same origin (dev proxy or served from /ui/)
    token: (import.meta as { env?: Record<string, string> }).env?.VITE_DS_TOKEN ?? '',
  }
}

export function httpBase(): string {
  const b = getBootstrap()
  return b.port ? `http://127.0.0.1:${b.port}` : ''
}

export function wsBase(): string {
  const b = getBootstrap()
  if (b.port) return `ws://127.0.0.1:${b.port}`
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}
