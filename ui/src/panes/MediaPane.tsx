import { useRef, useState } from 'react'
import { t, useI18n } from '../i18n'
import { useJobsStore } from '../stores/jobs'
import { useProjectStore } from '../stores/project'
import { useSessionStore } from '../stores/session'

const ACCEPT = '.mp4,.mov,.mkv,.avi,.mp3,.wav,.m4a,.ogg'

export function MediaPane({ hidden, onDrafted }: { hidden: boolean; onDrafted: () => void }) {
  useI18n()
  const connected = useSessionStore((s) => s.connected)
  const project = useProjectStore()
  const jobs = useJobsStore((s) => s.jobs)
  const inputRef = useRef<HTMLInputElement>(null)
  const [model, setModel] = useState('medium')
  const [dragOver, setDragOver] = useState(false)
  const notifiedRef = useRef(false)

  const job = project.jobId ? jobs[project.jobId] : null
  if (job?.state === 'succeeded' && !notifiedRef.current) {
    notifiedRef.current = true
    onDrafted()
  }

  const start = (file: File) => {
    notifiedRef.current = false
    void project.createFromFile(file, { captions: true, audio_description: false }, model)
  }

  return (
    <section className="pane" role="tabpanel" id="pane-media" aria-labelledby="tab-media" tabIndex={0} hidden={hidden}>
      <h2>{t('media.title')}</h2>
      <p className="lede">{t('media.lede')}</p>
      <div className="cols">
        <div>
          <div
            className="drop"
            style={dragOver ? { borderColor: 'var(--focus)' } : undefined}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              const file = e.dataTransfer.files?.[0]
              if (file) start(file)
            }}
          >
            <p>
              <strong>{t('media.drop')}</strong>
            </p>
            <p>{t('media.formats_now')}</p>
            <button type="button" className="btn" onClick={() => inputRef.current?.click()} disabled={!connected || project.busy}>
              {t('media.browse')}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              className="sr-only"
              aria-label={t('media.browse')}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) start(file)
                e.target.value = ''
              }}
            />
          </div>

          {project.busy || job ? (
            <div className="box" style={{ marginBlockStart: '1.25rem' }} aria-label={t('media.progress')}>
              <h3 style={{ marginBlockStart: 0 }}>{t('media.progress')}</h3>
              {job ? (
                <>
                  <progress max={100} value={job.percent} style={{ inlineSize: '100%' }} aria-hidden="true" />
                  <p style={{ marginBlockEnd: 0 }}>
                    {job.state} — {job.statusText || job.stage} ({job.percent}%)
                    {job.etaSeconds != null ? ` — about ${Math.ceil(job.etaSeconds / 60)} min left` : ''}
                  </p>
                </>
              ) : (
                <p style={{ marginBlockEnd: 0 }}>{t('media.uploading')}</p>
              )}
              {job?.state === 'succeeded' ? (
                <p style={{ marginBlockEnd: 0 }}>
                  <strong>{t('media.done_hint')}</strong>
                </p>
              ) : null}
            </div>
          ) : null}
          {project.error ? (
            <p role="alert" className="example">
              {project.error}
            </p>
          ) : null}
        </div>
        <div>
          <fieldset className="plain">
            <legend>{t('media.what_to_make')}</legend>
            <label className="check">
              <input type="checkbox" defaultChecked />
              <span>
                Captions <small>Speech, speaker names, and meaningful sounds, for Deaf and hard of hearing viewers</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" disabled />
              <span>
                Audio description <small>Arrives with the description pipeline (Phases 2 and 3)</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" disabled />
              <span>
                Image descriptions <small>Arrives in Phase 5</small>
              </span>
            </label>
          </fieldset>
          <div className="field" style={{ maxInlineSize: '20rem' }}>
            <label htmlFor="modelPick">{t('media.model')}</label>
            <select id="modelPick" value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="tiny">tiny — fastest, roughest</option>
              <option value="base">base — fast</option>
              <option value="small">small — balanced</option>
              <option value="medium">medium — better, slower (default)</option>
              <option value="large-v3">large-v3 — best, slowest</option>
            </select>
            <p className="hint">{t('media.model_hint')}</p>
          </div>
          <fieldset className="plain">
            <legend>{t('media.where')}</legend>
            <label className="check">
              <input type="radio" name="where" value="local" defaultChecked />
              <span>
                On this computer <small>Default. Works offline. Slower on long videos.</small>
              </span>
            </label>
            <label className="check">
              <input type="radio" name="where" value="cloud" disabled />
              <span>
                Cloud service with my own key <small>Off until you turn it on (Phase 7). You will see exactly which files would be sent first.</small>
              </span>
            </label>
          </fieldset>
        </div>
      </div>
    </section>
  )
}
