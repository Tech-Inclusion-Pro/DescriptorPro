import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/tokens.css'
import './styles/base.css'

// A file dropped outside an explicit drop zone must never navigate the
// window to the file (which the shell's loopback lockdown then blocks,
// leaving a dead page). Drop zones call preventDefault themselves, so
// these defaults only catch stray drops.
window.addEventListener('dragover', (e) => e.preventDefault())
window.addEventListener('drop', (e) => e.preventDefault())

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
