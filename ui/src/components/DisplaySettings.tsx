// Display settings widget — behavior ported 1:1 from the mockup:
// floating button, panel with grouped options, pointer drag + arrow-key nudge
// on the grip, corner choice, cursor trail, reset, polite announcements.

import { useEffect, useRef, useState } from 'react'
import { DEFAULTS, useDisplayStore, type DisplayState } from '../stores/display'
import { t, useI18n } from '../i18n'

const LABELS: Record<string, Record<string, string>> = {
  textsize: { '0': 'Default text size', '1': 'Large text', '2': 'Larger text', '3': 'Largest text' },
  spacing: { '0': 'Default text spacing', '1': 'Roomy text spacing', '2': 'Widest text spacing' },
  palette: { brand: 'Brand colors', cvd: 'Color-vision friendly palette', mono: 'Monochrome', hc: 'High contrast' },
  cursor: { default: 'System cursor', large: 'Large cursor', xlarge: 'Extra large cursor', contrast: 'High contrast cursor' },
  motion: { auto: 'Motion matches your device setting', slow: 'Animation slowed', none: 'Animation stopped' },
  corner: { br: 'Button moved to bottom right', bl: 'Button moved to bottom left', tr: 'Button moved to top right', tl: 'Button moved to top left', dock: 'Button kept at the top of the page' },
}

export function DisplaySettings() {
  useI18n() // re-render on language change
  const store = useDisplayStore()
  const [open, setOpen] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const widgetRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)
  const drag = useRef({ dragging: false, justDragged: false, startX: 0, startY: 0, baseX: 0, baseY: 0 })

  const say = (message: string) => setAnnouncement(message)

  useEffect(() => {
    if (open) closeRef.current?.focus()
  }, [open])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && open) {
        event.preventDefault()
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  // Cursor trail
  useEffect(() => {
    if (!store.trail) return
    const dots: Array<{ el: HTMLDivElement; born: number }> = []
    let lastSpawn = 0
    let raf = 0

    const onMove = (event: PointerEvent) => {
      if (event.pointerType === 'touch') return
      const now = performance.now()
      if (now - lastSpawn < 22) return
      lastSpawn = now
      const el = document.createElement('div')
      el.className = 'trail-dot'
      el.setAttribute('aria-hidden', 'true')
      el.style.transform = `translate(${event.clientX}px,${event.clientY}px)`
      document.body.appendChild(el)
      dots.push({ el, born: now })
      while (dots.length > 18) dots.shift()?.el.remove()
    }

    const fade = () => {
      const now = performance.now()
      for (let i = dots.length - 1; i >= 0; i--) {
        const age = now - dots[i].born
        if (age >= 620) {
          dots[i].el.remove()
          dots.splice(i, 1)
        } else {
          const k = 1 - age / 620
          dots[i].el.style.opacity = k.toFixed(3)
          dots[i].el.style.scale = (0.35 + 0.65 * k).toFixed(3)
        }
      }
      raf = requestAnimationFrame(fade)
    }
    document.addEventListener('pointermove', onMove, { passive: true })
    raf = requestAnimationFrame(fade)
    return () => {
      document.removeEventListener('pointermove', onMove)
      cancelAnimationFrame(raf)
      dots.forEach((d) => d.el.remove())
    }
  }, [store.trail])

  const moveTo = (x: number, y: number) => {
    const box = widgetRef.current?.getBoundingClientRect()
    if (!box) return
    const maxX = Math.max(0, window.innerWidth - box.width - 4)
    const maxY = Math.max(0, window.innerHeight - box.height - 4)
    store.set({
      x: Math.round(Math.min(Math.max(4, x), maxX)),
      y: Math.round(Math.min(Math.max(4, y), maxY)),
      cornerChosen: true,
    })
  }

  const onPointerDown = (event: React.PointerEvent) => {
    const box = widgetRef.current?.getBoundingClientRect()
    if (!box) return
    drag.current = {
      dragging: true,
      justDragged: false,
      startX: event.clientX,
      startY: event.clientY,
      baseX: box.left,
      baseY: box.top,
    }
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }
  const onPointerMove = (event: React.PointerEvent) => {
    const d = drag.current
    if (!d.dragging) return
    const dx = event.clientX - d.startX
    const dy = event.clientY - d.startY
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) d.justDragged = true
    moveTo(d.baseX + dx, d.baseY + dy)
    event.preventDefault()
  }
  const onPointerUp = () => {
    const d = drag.current
    if (!d.dragging) return
    d.dragging = false
    if (d.justDragged) say('Panel moved')
    window.setTimeout(() => {
      drag.current.justDragged = false
    }, 0)
  }

  const nudge = (event: React.KeyboardEvent) => {
    const STEP = event.shiftKey ? 48 : 16
    const box = widgetRef.current?.getBoundingClientRect()
    if (!box) return
    let dx = 0
    let dy = 0
    if (event.key === 'ArrowLeft') dx = -STEP
    else if (event.key === 'ArrowRight') dx = STEP
    else if (event.key === 'ArrowUp') dy = -STEP
    else if (event.key === 'ArrowDown') dy = STEP
    else return
    event.preventDefault()
    moveTo(box.left + dx, box.top + dy)
  }

  const setRadio = (name: keyof DisplayState, value: string) => {
    if (name === 'corner') {
      store.set({ corner: value as DisplayState['corner'], x: null, y: null, cornerChosen: true })
    } else {
      store.set({ [name]: value } as Partial<DisplayState>)
    }
    say(LABELS[name as string]?.[value] ?? value)
  }

  const docked = store.corner === 'dock'
  const floating = !docked && store.x !== null && store.y !== null
  const style: React.CSSProperties = floating
    ? { insetBlockStart: store.y ?? 0, insetInlineStart: store.x ?? 0, insetBlockEnd: 'auto', insetInlineEnd: 'auto' }
    : {}

  const radioGroup = (
    legend: string,
    name: keyof DisplayState,
    options: Array<[string, string, string?]>,
    hint?: string,
  ) => (
    <fieldset>
      <legend>{legend}</legend>
      {hint ? <p className="hint">{hint}</p> : null}
      {options.map(([value, label, small]) => (
        <label className="opt" key={value}>
          <input
            type="radio"
            name={name as string}
            value={value}
            checked={store[name] === value}
            onChange={() => setRadio(name, value)}
          />
          <span>
            {label}
            {small ? <small>{small}</small> : null}
          </span>
        </label>
      ))}
    </fieldset>
  )

  return (
    <>
      <div
        className="a11y"
        id="a11yWidget"
        ref={widgetRef}
        data-corner={floating ? undefined : docked ? undefined : store.corner}
        data-docked={docked ? 'yes' : undefined}
        style={style}
      >
        <button
          type="button"
          className="fab"
          ref={toggleRef}
          aria-expanded={open}
          aria-controls="a11yPanel"
          aria-label={t('a11y.open')}
          onClick={() => {
            if (drag.current.justDragged) {
              drag.current.justDragged = false
              return
            }
            setOpen(!open)
          }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onKeyDown={(event) => {
            if (event.altKey) nudge(event)
          }}
        >
          <svg className="fab__icon" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" strokeWidth="2" />
            <circle cx="12" cy="6.2" r="1.7" fill="currentColor" />
            <path d="M5.5 9.3h13M12 9.6v5.1m0 0-2.9 5.2m2.9-5.2 2.9 5.2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="fab__label" aria-hidden="true">
            {t('a11y.open')}
          </span>
        </button>

        <div className="panel" id="a11yPanel" role="group" aria-labelledby="a11yTitle" hidden={!open}>
          <div className="panel__bar">
            <button
              type="button"
              className="grip"
              aria-label={t('a11y.grip')}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              onKeyDown={nudge}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="8" cy="6" r="1.8" fill="currentColor" />
                <circle cx="16" cy="6" r="1.8" fill="currentColor" />
                <circle cx="8" cy="12" r="1.8" fill="currentColor" />
                <circle cx="16" cy="12" r="1.8" fill="currentColor" />
                <circle cx="8" cy="18" r="1.8" fill="currentColor" />
                <circle cx="16" cy="18" r="1.8" fill="currentColor" />
              </svg>
            </button>
            <h2 className="panel__title" id="a11yTitle">
              {t('a11y.open')}
            </h2>
            <button
              type="button"
              className="panel__close"
              ref={closeRef}
              aria-label={t('a11y.close')}
              onClick={() => {
                setOpen(false)
                toggleRef.current?.focus()
              }}
            >
              ×
            </button>
          </div>

          {radioGroup(t('a11y.textsize'), 'textsize', [
            ['0', 'Default'],
            ['1', 'Large', '115%'],
            ['2', 'Larger', '130%'],
            ['3', 'Largest', '150%'],
          ])}

          {radioGroup(t('a11y.spacing'), 'spacing', [
            ['0', 'Default'],
            ['1', 'Roomy'],
            ['2', 'Widest', 'Meets the WCAG text-spacing metrics'],
          ])}

          {radioGroup(
            t('a11y.color'),
            'palette',
            [
              ['brand', 'Brand colors'],
              ['cvd', 'Color-vision friendly', 'Blue and orange, separable across protan, deutan, and tritan vision'],
              ['mono', 'Monochrome', 'Grayscale only'],
              ['hc', 'High contrast', 'Yellow on black'],
            ],
            t('a11y.color_hint'),
          )}

          <fieldset>
            <legend>{t('a11y.font')}</legend>
            <label className="opt">
              <input
                type="checkbox"
                checked={store.dyslexic}
                onChange={(event) => {
                  store.set({ dyslexic: event.target.checked })
                  say(event.target.checked ? 'OpenDyslexic font on' : 'OpenDyslexic font off')
                }}
              />
              <span>
                {t('a11y.dyslexic')} <small>{t('a11y.dyslexic_hint')}</small>
              </span>
            </label>
          </fieldset>

          {radioGroup(t('a11y.pointer'), 'cursor', [
            ['default', 'System cursor'],
            ['large', 'Large cursor'],
            ['xlarge', 'Extra large cursor'],
            ['contrast', 'High contrast cursor', 'Yellow with a black outline'],
          ])}
          <fieldset>
            <legend className="sr-only">Pointer trail</legend>
            <label className="opt">
              <input
                type="checkbox"
                checked={store.trail}
                onChange={(event) => {
                  store.set({ trail: event.target.checked })
                  say(event.target.checked ? 'Cursor trail on' : 'Cursor trail off')
                }}
              />
              <span>
                Show a trail behind the cursor <small>Makes the pointer easier to follow</small>
              </span>
            </label>
          </fieldset>

          {radioGroup(t('a11y.motion'), 'motion', [
            ['auto', 'Match my device setting'],
            ['slow', 'Slow down animation'],
            ['none', 'Stop animation'],
          ])}

          {radioGroup(
            t('a11y.position'),
            'corner',
            [
              ['br', 'Bottom right'],
              ['bl', 'Bottom left'],
              ['tr', 'Top right'],
              ['tl', 'Top left'],
              ['dock', 'Keep it at the top of the page', 'Best when this page is embedded in another page, where a floating button can end up off screen'],
            ],
            t('a11y.position_hint'),
          )}

          <button
            type="button"
            className="reset"
            onClick={() => {
              store.reset()
              say(t('a11y.reset_done'))
            }}
          >
            {t('a11y.reset')}
          </button>
        </div>
      </div>
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
    </>
  )
}
