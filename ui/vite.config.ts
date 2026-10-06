import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: the service port comes from DS_SERVICE_PORT (exported by scripts/dev.sh
// after the service prints DS_READY). Prod: the service itself serves /ui/,
// so the app is same-origin and no proxy exists.
const servicePort = process.env.DS_SERVICE_PORT || '8300'

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    proxy: {
      '/api': `http://127.0.0.1:${servicePort}`,
      '/health': `http://127.0.0.1:${servicePort}`,
      '/ws': {
        target: `ws://127.0.0.1:${servicePort}`,
        ws: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
} as never)
