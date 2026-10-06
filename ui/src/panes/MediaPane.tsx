import { useState } from 'react'
import { t, useI18n } from '../i18n'
import { useJobsStore } from '../stores/jobs'
import { useSessionStore } from '../stores/session'
import { api } from '../api/client'

export function MediaPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" role="tabpanel" id="pane-media" aria-labelledby="tab-media" tabIndex={0} hidden={hidden}>
      <h2>{t('media.title')}</h2>
      <p className="lede">{t('media.lede')}</p>
      <div className="cols">
        <div>
          <div className="drop">
            <p>
              <strong>{t('media.drop')}</strong>
            </p>
            <p>{t('media.formats')}</p>
            <button type="button" className="btn">
              {t('media.browse')}
            </button>
          </div>
          <TestJobBox />
        </div>
        <div>
          <fieldset className="plain">
            <legend>What to make</legend>
            <label className="check">
              <input type="checkbox" defaultChecked />
              <span>
                Captions <small>Speech, speaker names, and meaningful sounds, for Deaf and hard of hearing viewers</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" defaultChecked />
              <span>
                Audio description <small>Narration of what is visible, for blind and low vision viewers</small>
              </span>
            </label>
            <label className="check">
              <input type="checkbox" />
              <span>
                Image descriptions <small>Alt text and long descriptions for still images, slides, and charts</small>
              </span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Audio description style</legend>
            <label className="check">
              <input type="radio" name="adstyle" value="standard" />
              <span>
                Standard <small>Descriptions fit into natural pauses. The video length does not change. WCAG 1.2.5, Level AA.</small>
              </span>
            </label>
            <label className="check">
              <input type="radio" name="adstyle" value="extended" defaultChecked />
              <span>
                Extended where needed <small>When a description does not fit the pause, the video pauses until the description finishes. WCAG 1.2.7, Level AAA. Suggested for lectures.</small>
              </span>
            </label>
            <label className="check">
              <input type="radio" name="adstyle" value="before" />
              <span>
                Extended, described first <small>The video pauses and each visual is described before the speaker discusses it, so students get the information at the same moment as their peers.</small>
              </span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>How much review</legend>
            <label className="check">
              <input type="radio" name="reviewlvl" value="full" defaultChecked />
              <span>
                Review before export <small>Recommended. Nothing is released until a person approves it.</small>
              </span>
            </label>
            <label className="check">
              <input type="radio" name="reviewlvl" value="quick" />
              <span>
                Quick draft for Panopto <small>Runs the need check, drafts the descriptions, and writes a Panopto-ready file in one pass. The file is stamped "not reviewed by a person."</small>
              </span>
            </label>
          </fieldset>
          <fieldset className="plain">
            <legend>Where processing happens</legend>
            <label className="check">
              <input type="radio" name="where" value="local" defaultChecked />
              <span>
                On this computer <small>Default. Works offline. Slower on long videos.</small>
              </span>
            </label>
            <label className="check">
              <input type="radio" name="where" value="cloud" />
              <span>
                Cloud service with my own key <small>Off until you turn it on. You will see exactly which files would be sent before anything is sent.</small>
              </span>
            </label>
          </fieldset>
        </div>
      </div>
    </section>
  )
}

// Phase 0 connectivity check: submits a `noop` job against a throwaway project
// and streams progress over the websocket into the live region and a visible bar.
function TestJobBox() {
  const run = useJobsStore((s) => s.run)
  const jobs = useJobsStore((s) => s.jobs)
  const connected = useSessionStore((s) => s.connected)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const job = jobId ? jobs[jobId] : null

  const start = async () => {
    setError(null)
    try {
      const settings = await api.getSettings()
      const probe = `${settings.library_dir}/.phase0-probe`
      // The noop job only needs a project id; use a fixed probe id. Its stage
      // files land in the library and demonstrate resume on a second run.
      setJobId(await run('phase0-probe', 'noop', { steps: 4, delay: 0.5, probe }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <div className="box" style={{ marginBlockStart: '1.25rem' }}>
      <h3>{t('debug.run_test_job')}</h3>
      <p>{t('debug.test_job_hint')}</p>
      <div className="row">
        <button type="button" className="btn btn--quiet" onClick={start} disabled={!connected}>
          {t('debug.run_test_job')}
        </button>
      </div>
      {job ? (
        <p aria-hidden="true" style={{ marginBlockEnd: 0 }}>
          <progress max={100} value={job.percent} style={{ inlineSize: '100%' }} />
          <br />
          {job.state} — {job.statusText || job.stage} ({job.percent}%)
        </p>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </div>
  )
}
