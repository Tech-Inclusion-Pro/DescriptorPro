// Describe Studio shell: spawn the Python service, read the DS_READY
// handshake, load the UI, enforce loopback-only networking, shut down cleanly.

const { app, BrowserWindow, dialog, session } = require('electron')
const { spawn } = require('node:child_process')
const path = require('node:path')

const DEV = process.env.DS_DEV === '1'
const REPO_ROOT = path.resolve(__dirname, '..')
const HEALTH_TIMEOUT_MS = 30000

let serviceProcess = null
let bootstrap = null // { port, token }
let mainWindow = null
let quitting = false

function serviceCommand() {
  if (DEV) {
    const python = path.join(REPO_ROOT, '.venv', 'bin', 'python')
    return { cmd: python, args: ['-m', 'service.main', '--dev'], cwd: REPO_ROOT }
  }
  // Packaged with a PyInstaller service binary in resources (Phase 7).
  const bin = path.join(process.resourcesPath, 'service', 'describe-studio-service')
  if (require('node:fs').existsSync(bin)) {
    return { cmd: bin, args: [], cwd: path.dirname(bin) }
  }
  // Interim Phase 0 install: run the service from the repo checkout.
  const repo = path.join(require('node:os').homedir(), 'la-mia-scribe')
  return { cmd: path.join(repo, '.venv', 'bin', 'python'), args: ['-m', 'service.main'], cwd: repo }
}

function startService() {
  return new Promise((resolve, reject) => {
    const { cmd, args, cwd } = serviceCommand()
    serviceProcess = spawn(cmd, args, { cwd, stdio: ['ignore', 'pipe', 'pipe'] })

    const timer = setTimeout(
      () => reject(new Error('The local service did not start within 30 seconds.')),
      HEALTH_TIMEOUT_MS,
    )

    let buffer = ''
    serviceProcess.stdout.on('data', (chunk) => {
      buffer += chunk.toString()
      const match = buffer.match(/^DS_READY (.*)$/m)
      if (match) {
        clearTimeout(timer)
        try {
          const payload = JSON.parse(match[1])
          resolve({ port: payload.port, token: payload.token })
        } catch (err) {
          reject(err)
        }
      }
    })
    serviceProcess.stderr.on('data', (chunk) => {
      if (DEV) process.stderr.write(chunk)
    })
    serviceProcess.on('exit', (code) => {
      clearTimeout(timer)
      serviceProcess = null
      if (!quitting) {
        dialog.showErrorBox(
          'DescriptorPro',
          `The local service stopped unexpectedly (code ${code}). Please reopen the app.`,
        )
        app.quit()
      }
    })
    serviceProcess.on('error', (err) => {
      clearTimeout(timer)
      reject(err)
    })
  })
}

async function waitForHealth(port) {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`)
      if (response.ok) return
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  throw new Error('The local service never answered its health check.')
}

function lockDownNetwork() {
  // Zero-network enforcement (spec §13): the shell refuses any request that
  // is not loopback. Model downloads and allowlisted calls happen in the
  // Python service, never in the UI.
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    try {
      const url = new URL(details.url)
      const local =
        url.hostname === '127.0.0.1' ||
        url.hostname === 'localhost' ||
        url.protocol === 'devtools:' ||
        url.protocol === 'chrome-extension:'
      callback({ cancel: !local })
    } catch {
      callback({ cancel: true })
    }
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 320,
    title: 'DescriptorPro',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--ds-port=${bootstrap.port}`, `--ds-token=${bootstrap.token}`],
    },
  })
  const url = DEV ? 'http://localhost:5173' : `http://127.0.0.1:${bootstrap.port}/ui/`
  // A file dropped on the window must never navigate away from the UI
  // (Electron's default is to open the dropped file as a page).
  mainWindow.webContents.on('will-navigate', (event, target) => {
    if (target !== url) event.preventDefault()
  })
  mainWindow.loadURL(url)
}

async function shutdownService() {
  if (!serviceProcess || !bootstrap) return
  try {
    await fetch(`http://127.0.0.1:${bootstrap.port}/api/shutdown`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${bootstrap.token}` },
    })
    await new Promise((r) => setTimeout(r, 1500))
  } catch {
    /* fall through to kill */
  }
  if (serviceProcess) serviceProcess.kill()
}

app.whenReady().then(async () => {
  lockDownNetwork()
  try {
    if (DEV && process.env.DS_PORT && process.env.DS_TOKEN) {
      // scripts/dev.sh already started the service; attach to it.
      bootstrap = { port: Number(process.env.DS_PORT), token: process.env.DS_TOKEN }
    } else {
      bootstrap = await startService()
    }
    await waitForHealth(bootstrap.port)
    createWindow()
  } catch (err) {
    dialog.showErrorBox('DescriptorPro', String(err && err.message ? err.message : err))
    app.quit()
  }
})

app.on('before-quit', (event) => {
  if (quitting) return
  quitting = true
  event.preventDefault()
  shutdownService().finally(() => app.exit(0))
})

app.on('window-all-closed', () => {
  app.quit()
})
