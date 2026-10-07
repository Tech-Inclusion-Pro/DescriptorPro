import { useState } from 'react'
import { t, useI18n } from '../i18n'
import { useAnalysisStore } from '../stores/analysis'
import { useProjectStore } from '../stores/project'

export function ExportPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const project = useProjectStore()
  const analysis = useAnalysisStore()
  const [vtt, setVtt] = useState(true)
  const [srt, setSrt] = useState(false)
  const [descVtt, setDescVtt] = useState(false)
  const [panopto, setPanopto] = useState(false)
  const [transcriptHtml, setTranscriptHtml] = useState(false)
  const [transcriptDocx, setTranscriptDocx] = useState(false)
  const [scriptDocx, setScriptDocx] = useState(false)
  const [provJson, setProvJson] = useState(false)
  const [playerResult, setPlayerResult] = useState<{ folder: string; embed_code: string } | null>(null)
  const [renderDone, setRenderDone] = useState(false)
  const haveDescriptions = analysis.descriptions.length > 0

  const prov = project.provenance as {
    captions?: { cues?: number; approved?: number; flagged_open?: number }
    status?: string
  }
  const total = prov.captions?.cues ?? project.cues.length
  const approved = prov.captions?.approved ?? 0
  const reviewed = total > 0 && approved === total
  const haveCues = total > 0

  const formats = [
    ...(vtt ? ['vtt'] : []),
    ...(srt ? ['srt'] : []),
    ...(descVtt ? ['descriptions_vtt'] : []),
    ...(panopto ? ['panopto'] : []),
    ...(transcriptHtml ? ['transcript_html'] : []),
    ...(transcriptDocx ? ['transcript_docx'] : []),
    ...(scriptDocx ? ['script_docx'] : []),
    ...(provJson ? ['provenance_json'] : []),
  ]

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
              <input type="checkbox" checked={descVtt} onChange={(e) => setDescVtt(e.target.checked)} disabled={!haveDescriptions} />
              <span>
                Descriptions track (.vtt) <small>For &lt;track kind="descriptions"&gt;; provenance in a NOTE block</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" checked={panopto} onChange={(e) => setPanopto(e.target.checked)} disabled={!haveDescriptions} />
              <span>
                Panopto description file <small>Two variants (A/B) until one is confirmed on a real Panopto site</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" checked={transcriptHtml} onChange={(e) => setTranscriptHtml(e.target.checked)} disabled={!haveDescriptions} />
              <span>
                Described transcript (.html) <small>Speech and descriptions in order, readable without the video</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" checked={transcriptDocx} onChange={(e) => setTranscriptDocx(e.target.checked)} disabled={!haveDescriptions} />
              <span>Described transcript (.docx)</span>
            </label>
            <label className="check">
              <input type="checkbox" checked={scriptDocx} onChange={(e) => setScriptDocx(e.target.checked)} disabled={!haveDescriptions} />
              <span>
                Description script (.docx) <small>Times, modes, and open flags for a narrator or reviewer</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" checked={provJson} onChange={(e) => setProvJson(e.target.checked)} disabled={!haveCues} />
              <span>Provenance record (.json)</span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Described video and player</legend>
            <div className="row">
              <button
                type="button"
                className="btn btn--quiet"
                disabled={!haveDescriptions || analysis.busy}
                onClick={() => {
                  setRenderDone(false)
                  void analysis.renderDescribed().then((r) => setRenderDone(r === 'done'))
                }}
              >
                {analysis.busy && analysis.phase === 'describe'
                  ? 'Rendering described video...'
                  : 'Render described video (.mp4)'}
              </button>
              <button
                type="button"
                className="btn btn--quiet"
                disabled={!haveCues}
                onClick={() => void analysis.exportPlayer().then(setPlayerResult)}
              >
                Export accessible player folder
              </button>
            </div>
            <p className="hint">
              The video mixes a synthetic narration in, ducks the program audio under it, and freezes
              the frame for extended descriptions. The player folder works from any course site with
              zero network requests.
            </p>
            {renderDone ? (
              <p className="std" role="status">
                Described video written to the project's exports folder.
              </p>
            ) : null}
            {playerResult ? (
              <div className="box">
                <h3 style={{ marginBlockStart: 0 }}>Player folder written</h3>
                <p style={{ overflowWrap: 'anywhere' }}>{playerResult.folder}</p>
                <p>Upload the folder, then embed it with:</p>
                <pre className="prov" tabIndex={0} aria-label="Embed code">
                  {playerResult.embed_code}
                </pre>
                <button
                  type="button"
                  className="btn btn--quiet"
                  onClick={() => void navigator.clipboard.writeText(playerResult.embed_code)}
                >
                  Copy embed code
                </button>
              </div>
            ) : null}
            {analysis.error ? (
              <p className="flag" role="alert">
                {analysis.error}
              </p>
            ) : null}
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
