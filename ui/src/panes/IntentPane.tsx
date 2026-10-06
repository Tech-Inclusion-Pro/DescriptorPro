import { t, useI18n } from '../i18n'

export function IntentPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" role="tabpanel" id="pane-intent" aria-labelledby="tab-intent" tabIndex={0} hidden={hidden}>
      <h2>{t('intent.title')}</h2>
      <p className="lede">{t('intent.lede')}</p>
      <div className="cols">
        <div>
          <ul className="talk" aria-label="Conversation so far">
            <li className="app">
              <span className="who">DescriptorPro</span>
              Who is this video for, and what do they need to get from it?
            </li>
          </ul>
          <div className="field">
            <label htmlFor="intentText">Your answer</label>
            <textarea id="intentText" rows={2} placeholder="Type here, or use the Speak button" disabled />
          </div>
          <div className="row">
            <button type="button" className="btn" disabled>
              Speak
            </button>
            <button type="button" className="btn btn--quiet" disabled>
              Add to my answers
            </button>
          </div>
          <p className="example" style={{ marginBlockStart: '1rem' }}>
            The intent conversation arrives in Phase 2. Until then this step can be skipped; the
            defaults are concise detail, auto-detected content type, and no named people.
          </p>
        </div>
        <div className="box">
          <h3>What the app understood</h3>
          <p>Nothing yet. Answers appear here, and every field can be edited before anything runs.</p>
        </div>
      </div>
    </section>
  )
}
