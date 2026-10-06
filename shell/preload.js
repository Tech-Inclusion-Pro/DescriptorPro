// Exposes the service port + token to the UI without putting the token in the
// URL or giving the renderer any Node access.

const { contextBridge } = require('electron')

function arg(name) {
  const prefix = `--${name}=`
  const found = process.argv.find((a) => a.startsWith(prefix))
  return found ? found.slice(prefix.length) : null
}

const port = Number(arg('ds-port'))
const token = arg('ds-token') || ''

if (port && token) {
  contextBridge.exposeInMainWorld('__DS_BOOTSTRAP__', { port, token })
}
