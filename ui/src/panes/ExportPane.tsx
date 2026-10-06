import { t, useI18n } from '../i18n'

export function ExportPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" role="tabpanel" id="pane-export" aria-labelledby="tab-export" tabIndex={0} hidden={hidden}>
      <h2>{t('export.title')}</h2>
      <p className="lede">{t('export.lede')}</p>
      <div className="cols">
        <div>
          <fieldset className="plain">
            <legend>Captions</legend>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>WebVTT captions (.vtt)</span>
            </label>
            <label className="check">
              <input type="checkbox" disabled />
              <span>SRT captions (.srt)</span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Audio description</legend>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>
                Descriptions track (.vtt) <small>Standard WebVTT descriptions, for web players</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>
                Panopto descriptions file (.vtt) <small>Timestamped text that Panopto reads aloud</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" disabled />
              <span>
                Described video (.mp4) <small>Narration mixed in with a local voice, original audio lowered under it</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>
                Described transcript (.html, .docx) <small>Speech and descriptions together, readable without the video</small>
              </span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Player for your own site</legend>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>
                Accessible player (.html) <small>One page with the video, captions, spoken and on-screen description, extended description, and a transcript</small>
              </span>
            </label>
          </fieldset>
          <button type="button" className="btn" disabled>
            Export
          </button>
          <p className="example" style={{ marginBlockStart: '1rem' }}>
            Exports arrive with their pipelines (Phases 1 and 4). Nothing can be exported before it
            exists.
          </p>
        </div>
        <div>
          <h3 style={{ marginBlockStart: 0 }}>Record that travels with the files</h3>
          <pre className="prov" tabIndex={0} aria-label="Provenance record preview">
{`Project: (none)
Captions: not drafted
Descriptions: not drafted
Need check: not run
Cloud services used: none
Status: DRAFT. Not yet reviewed by a person.`}
          </pre>
        </div>
      </div>
    </section>
  )
}
