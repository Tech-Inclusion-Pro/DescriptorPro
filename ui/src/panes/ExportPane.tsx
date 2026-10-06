import { useState } from 'react'
import { t, useI18n } from '../i18n'
import { useProjectStore } from '../stores/project'

export function ExportPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const project = useProjectStore()
  const [vtt, setVtt] = useState(true)
  const [srt, setSrt] = useState(false)

  const prov = project.provenance as {
    captions?: { cues?: number; approved?: number; flagged_open?: number }
    status?: string
  }
  const total = prov.captions?.cues ?? project.cues.length
  const approved = prov.captions?.approved ?? 0
  const reviewed = total > 0 && approved === total
  const haveCues = total > 0

  const formats = [...(vtt ? ['vtt'] : []), ...(srt ? ['srt'] : [])]

  return (
    <section className="pane" role="tabpanel" id="pane-export" aria-labelledby="tab-export" tabIndex={0} hidden={hidden}>
      <h2>{t('export.title')}</h2>
      <p className="lede">{t('export.lede')}</p>
      <div className="cols">
        <div>
          <fieldset className="plain">
            <legend>Captions</legend>
            <label className="check">
              <input type="checkbox" checked={vtt} onChange={(e) => setVtt(e.target.checked)} disabled={!haveCues} />
              <span>
                WebVTT captions (.vtt) <small>Provenance travels as a NOTE block inside the file</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" checked={srt} onChange={(e) => setSrt(e.target.checked)} disabled={!haveCues} />
              <span>
                SRT captions (.srt) <small>Provenance travels as a sidecar text file</small>
              </span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Audio description</legend>
            <label className="check">
              <input type="checkbox" disabled />
              <span>
                Descriptions track, Panopto file, described video, described transcript{' '}
                <small>Arrive with the description pipeline (Phases 3 and 4)</small>
              </span>
            </label>
          </fieldset>
          <button
            type="button"
            className="btn"
            disabled={!haveCues || formats.length === 0}
            onClick={() => void project.exportCaptions(formats)}
          >
            {t('export.button')}
          </button>
          {!reviewed && haveCues ? (
            <p className="example" style={{ marginBlockStart: '1rem' }}>
              {t('export.unreviewed_warning', { approved: String(approved), total: String(total) })}
            </p>
          ) : null}
          {project.error ? (
            <p role="alert" className="example">
              {project.error}
            </p>
          ) : null}
          {project.exported.length > 0 ? (
            <div className="box" style={{ marginBlockStart: '1rem' }}>
              <h3 style={{ marginBlockStart: 0 }}>{t('export.written')}</h3>
              <ul>
                {project.exported.map((path) => (
                  <li key={path} style={{ overflowWrap: 'anywhere' }}>
                    {path}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <div>
          <h3 style={{ marginBlockStart: 0 }}>{t('export.record_title')}</h3>
          <pre className="prov" tabIndex={0} aria-label={t('export.record_title')}>
            {haveCues
              ? [
                  `Project: ${String((project.project as { title?: string } | null)?.title ?? '')}`,
                  `Captions: drafted by a speech model on this computer, ${approved} of ${total} cues approved`,
                  `Open flags: ${prov.captions?.flagged_open ?? 0}`,
                  'Cloud services used: none',
                  reviewed ? 'Status: reviewed' : 'Status: DRAFT. Not yet reviewed by a person.',
                ].join('\n')
              : `Project: (none)\nCaptions: not drafted\nCloud services used: none\nStatus: DRAFT. Not yet reviewed by a person.`}
          </pre>
        </div>
      </div>
    </section>
  )
}
