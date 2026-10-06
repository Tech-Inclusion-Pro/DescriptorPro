import { t, useI18n } from '../i18n'

export function ReviewPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" role="tabpanel" id="pane-review" aria-labelledby="tab-review" tabIndex={0} hidden={hidden}>
      <h2>{t('review.title')}</h2>
      <p className="lede">{t('review.lede')}</p>
      <div className="cols">
        <div>
          <div className="player" role="img" aria-label="Video player placeholder. No media loaded.">
            <p>
              <strong>Video player</strong>
              <br />
              No media loaded
            </p>
          </div>
          <fieldset className="plain" style={{ marginBlockStart: '1rem' }}>
            <legend>Show</legend>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>Captions</span>
            </label>
            <label className="check">
              <input type="checkbox" defaultChecked disabled />
              <span>Audio description</span>
            </label>
            <label className="check">
              <input type="checkbox" disabled />
              <span>Flagged cues only</span>
            </label>
          </fieldset>
        </div>
        <div>
          <p className="example">
            Cues appear here after captions are drafted (Phase 1). Every cue shows its kind, time, gap,
            flags, and an Approve action, all operable from the keyboard.
          </p>
        </div>
      </div>
    </section>
  )
}
