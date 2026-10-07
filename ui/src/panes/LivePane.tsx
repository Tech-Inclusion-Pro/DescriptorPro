import { useEffect, useRef, useState } from 'react'
import { getBootstrap, httpBase, wsBase } from '../lib/bootstrap'
import { t, useI18n } from '../i18n'

interface Sentence {
  text: string
  start: number
  end: number
}

interface SlideChange {
  slide_number: number
  title: string
  lines: string[]
  graphics_note: string | null
}

export function LivePane({ hidden }: { hidden: boolean }) {
  useI18n()
  // --- captions state
  const [running, setRunning] = useState(false)
  const [recording, setRecording] = useState(false)
  const [lagMs, setLagMs] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [sentences, setSentences] = useState<Sentence[]>([])
  const [stopped, setStopped] = useState(false)
  const [savedProject, setSavedProject] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [textSize, setTextSize] = useState(1.6)
  const [lineCount, setLineCount] = useState(3)
  const [highContrast, setHighContrast] = useState(true)
  // --- announcer state
  const [announcing, setAnnouncing] = useState(false)
  const [readAll, setReadAll] = useState(false)
  const [speakOn, setSpeakOn] = useState(true)
  const [slideLog, setSlideLog] = useState<SlideChange[]>([])

  const socketRef = useRef<WebSocket | null>(null)
  const audioRef = useRef<{ ctx: AudioContext; stream: MediaStream; node: ScriptProcessorNode } | null>(null)
  const sessionRef = useRef<string | null>(null)
  const detachedRef = useRef<Window | null>(null)
  const announceRef = useRef<{ stream: MediaStream; timer: number; video: HTMLVideoElement } | null>(null)

  useEffect(() => () => stopCaptions(true), []) // eslint-disable-line react-hooks/exhaustive-deps

  const lastLines = (() => {
    const words = text.split(/\s+/).filter(Boolean)
    const perLine = 10
    const lines: string[] = []
    for (let i = 0; i < words.length; i += perLine) lines.push(words.slice(i, i + perLine).join(' '))
    return lines.slice(-lineCount)
  })()

  useEffect(() => {
    const win = detachedRef.current
    if (win && !win.closed) {
      const el = win.document.getElementById('cap')
      if (el) el.textContent = lastLines.join('\n')
    }
  }, [lastLines])

  const startCaptions = async () => {
    setError(null)
    setStopped(false)
    setSavedProject(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })
      const { token } = getBootstrap()
      const socket = new WebSocket(`${wsBase()}/ws/live?token=${encodeURIComponent(token)}`)
      socket.binaryType = 'arraybuffer'
      socketRef.current = socket

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data as string) as Record<string, unknown>
        if (message.type === 'ready') sessionRef.current = String(message.session_id)
        else if (message.type === 'caption') {
          setText(String(message.text ?? ''))
          setSentences((message.sentences as Sentence[]) ?? [])
          setLagMs(Number(message.lag_ms))
        } else if (message.type === 'recording') setRecording(Boolean(message.on))
        else if (message.type === 'final') {
          setSentences((message.sentences as Sentence[]) ?? [])
          setStopped(true)
        }
      }
      socket.onerror = () => setError('The live connection failed.')

      await new Promise<void>((resolve, reject) => {
        socket.onopen = () => resolve()
        socket.onclose = () => reject(new Error('Could not open the live connection.'))
      })

      const ctx = new AudioContext({ sampleRate: 16000 })
      const source = ctx.createMediaStreamSource(stream)
      const node = ctx.createScriptProcessor(8192, 1, 1)
      node.onaudioprocess = (e) => {
        if (socket.readyState === WebSocket.OPEN) {
          const pcm = e.inputBuffer.getChannelData(0)
          socket.send(new Float32Array(pcm).buffer)
        }
      }
      source.connect(node)
      node.connect(ctx.destination)
      audioRef.current = { ctx, stream, node }
      setRunning(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const stopCaptions = (silent = false) => {
    const audio = audioRef.current
    if (audio) {
      audio.node.disconnect()
      audio.stream.getTracks().forEach((track) => track.stop())
      void audio.ctx.close()
      audioRef.current = null
    }
    const socket = socketRef.current
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop' }))
      if (silent) socket.close()
    }
    setRunning(false)
    setRecording(false)
  }

  const toggleRecording = () => {
    socketRef.current?.send(JSON.stringify({ type: 'record', on: !recording }))
  }

  const detach = () => {
    const win = window.open('', 'live-captions', 'width=900,height=260')
    if (!win) return
    win.document.title = 'Live captions'
    win.document.body.innerHTML =
      '<pre id="cap" style="font-family:Arial;white-space:pre-wrap;margin:1rem;' +
      `font-size:${textSize}rem;line-height:1.5;` +
      (highContrast ? 'background:#000;color:#fff;' : '') +
      '"></pre>'
    win.document.body.style.background = highContrast ? '#000' : '#fff'
    detachedRef.current = win
  }

  const saveProject = async () => {
    const sessionId = sessionRef.current
    if (!sessionId) return
    const { token } = getBootstrap()
    const response = await fetch(`${httpBase()}/api/live/${sessionId}/project`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    if (response.ok) {
      const data = (await response.json()) as { project_id: string }
      setSavedProject(data.project_id)
    } else {
      setError('Could not save the session as a project.')
    }
  }

  // --- slide announcer
  const speak = (phrase: string) => {
    if (!speakOn) return
    const utterance = new SpeechSynthesisUtterance(phrase)
    window.speechSynthesis.speak(utterance)
  }

  const startAnnouncer = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      const video = document.createElement('video')
      video.srcObject = stream
      await video.play()
      const canvas = document.createElement('canvas')
      const timer = window.setInterval(async () => {
        const sessionId = sessionRef.current
        if (!sessionId) return // captions session carries the watcher
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        canvas.getContext('2d')?.drawImage(video, 0, 0)
        const blob = await new Promise<Blob | null>((resolve) =>
          canvas.toBlob(resolve, 'image/jpeg', 0.7),
        )
        if (!blob) return
        const { token } = getBootstrap()
        const response = await fetch(`${httpBase()}/api/live/${sessionId}/frame`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: blob,
        })
        if (!response.ok) return
        const change = (await response.json()) as { changed: boolean } & SlideChange
        if (!change.changed) return
        setSlideLog((log) => [...log, change])
        const parts = [`Slide ${change.slide_number}.`]
        if (change.title) parts.push(change.title + '.')
        if (readAll && change.lines.length > 1) parts.push(change.lines.slice(1).join('. '))
        if (change.graphics_note) parts.push(change.graphics_note)
        speak(parts.join(' '))
      }, 2000)
      announceRef.current = { stream, timer, video }
      stream.getVideoTracks()[0].addEventListener('ended', stopAnnouncer)
      setAnnouncing(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const stopAnnouncer = () => {
    const current = announceRef.current
    if (current) {
      window.clearInterval(current.timer)
      current.stream.getTracks().forEach((track) => track.stop())
      announceRef.current = null
    }
    setAnnouncing(false)
  }

  return (
    <section className="pane" aria-labelledby="live-h" hidden={hidden}>
      <h2 id="live-h">{t('live.title')}</h2>
      <p className="lede">{t('live.lede')}</p>

      <div className="box" role="note">
        <h3>Before you start</h3>
        <ul>
          <li>
            Live mode adds access where there would otherwise be none. It does <strong>not</strong>{' '}
            replace a human captioner (CART) when one is a person's approved accommodation.
          </li>
          <li>Its error rate is higher for some accents and speech patterns than others.</li>
          <li>
            Recording other people may require their consent. <strong>The app does not record unless
            you turn recording on.</strong>
          </li>
        </ul>
      </div>

      <div className="cols" style={{ marginBlockStart: '1.25rem' }}>
        <div>
          <h3>Live captions</h3>
          <div className="row">
            {!running ? (
              <button type="button" className="btn" onClick={() => void startCaptions()}>
                Start captions (microphone)
              </button>
            ) : (
              <button type="button" className="btn" onClick={() => stopCaptions()}>
                Stop
              </button>
            )}
            <button type="button" className="btn btn--quiet" disabled={!running} onClick={toggleRecording}>
              {recording ? 'Recording is ON — turn off' : 'Recording is off — turn on'}
            </button>
            <button type="button" className="btn btn--quiet" disabled={!running} onClick={detach}>
              Detach caption window
            </button>
          </div>
          {lagMs != null && running ? (
            <p className="std" role="status">
              Measured delay: about {(lagMs / 1000).toFixed(1)} s behind the speaker.
            </p>
          ) : null}

          <div
            aria-live="off"
            style={{
              marginBlockStart: '.75rem',
              padding: '1rem',
              borderRadius: 'var(--radius)',
              minBlockSize: `${lineCount * 2.2}em`,
              fontSize: `${textSize}rem`,
              lineHeight: 1.5,
              background: highContrast ? '#000' : 'var(--tile)',
              color: highContrast ? '#fff' : 'inherit',
              whiteSpace: 'pre-wrap',
            }}
          >
            {lastLines.join('\n') || (running ? 'Listening…' : 'Captions appear here.')}
          </div>

          <div className="row" style={{ marginBlockStart: '.5rem' }}>
            <div className="field" style={{ maxInlineSize: '9rem' }}>
              <label htmlFor="live-size">Text size</label>
              <select id="live-size" value={textSize} onChange={(e) => setTextSize(Number(e.target.value))}>
                <option value={1.2}>Smaller</option>
                <option value={1.6}>Standard</option>
                <option value={2.2}>Large</option>
                <option value={3}>Largest</option>
              </select>
            </div>
            <div className="field" style={{ maxInlineSize: '9rem' }}>
              <label htmlFor="live-lines">Lines shown</label>
              <select id="live-lines" value={lineCount} onChange={(e) => setLineCount(Number(e.target.value))}>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
              </select>
            </div>
            <label className="check" style={{ alignSelf: 'end' }}>
              <input type="checkbox" checked={highContrast} onChange={(e) => setHighContrast(e.target.checked)} />
              <span>High contrast</span>
            </label>
          </div>

          {stopped ? (
            <div className="box" style={{ marginBlockStart: '1rem' }}>
              <h3 style={{ marginBlockStart: 0 }}>Session ended — {sentences.length} caption lines</h3>
              <p>
                Save it as a project to review the transcript
                {recording ? ' and the recording' : ''}, or run the full recorded pipeline on it.
              </p>
              {savedProject ? (
                <p className="std" role="status">
                  Saved. Open it from the Media step to review and re-caption properly.
                </p>
              ) : (
                <button type="button" className="btn" onClick={() => void saveProject()}>
                  Save as a project
                </button>
              )}
            </div>
          ) : null}
        </div>

        <div>
          <h3>Slide announcer</h3>
          <p className="hint">
            Reads the slide number and title aloud when the slide changes — through the device you
            pick in your system sound output (headphones for a private channel, or room speakers).
            It reads text only; it never describes images, charts, or people live.
          </p>
          <div className="row">
            {!announcing ? (
              <button
                type="button"
                className="btn"
                disabled={!running}
                title={running ? undefined : 'Start captions first — the announcer shares its session'}
                onClick={() => void startAnnouncer()}
              >
                Start announcer (pick the slides window)
              </button>
            ) : (
              <button type="button" className="btn" onClick={stopAnnouncer}>
                Stop announcer
              </button>
            )}
          </div>
          <label className="check">
            <input type="checkbox" checked={speakOn} onChange={(e) => setSpeakOn(e.target.checked)} />
            <span>Speak announcements</span>
          </label>
          <label className="check">
            <input type="checkbox" checked={readAll} onChange={(e) => setReadAll(e.target.checked)} />
            <span>Read all slide text, not just the title</span>
          </label>
          <ol aria-label="Slide changes this session">
            {slideLog.map((change, ix) => (
              <li key={ix}>
                <strong>Slide {change.slide_number}:</strong> {change.title || '(no title read)'}
                {change.graphics_note ? <em> — {change.graphics_note}</em> : null}
              </li>
            ))}
          </ol>
        </div>
      </div>

      {error ? (
        <p className="flag" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  )
}
