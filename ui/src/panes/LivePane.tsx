import { t, useI18n } from '../i18n'

export function LivePane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" aria-labelledby="live-h" hidden={hidden}>
      <h2 id="live-h">{t('live.title')}</h2>
      <p className="lede">{t('live.lede')}</p>
      <p className="example">Live captions and the slide announcer arrive in Phase 6.</p>
      <div className="box" style={{ marginBlockStart: '1.25rem' }}>
        <h3>What live mode is for</h3>
        <p>
          It adds access where there would otherwise be none. It does not replace a human captioner
          (CART) when one is a student's approved accommodation, and its error rate is higher for some
          accents and speech patterns than others. The app does not record unless recording is turned
          on.
        </p>
      </div>
    </section>
  )
}
