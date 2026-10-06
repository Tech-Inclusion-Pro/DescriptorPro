import { t, useI18n } from '../i18n'

export function StandardsPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" aria-labelledby="std-h" hidden={hidden}>
      <h2 id="std-h">{t('standards.title')}</h2>
      <p className="lede">{t('standards.lede')}</p>
      <p className="example">
        The ten criteria (DS-1 to DS-10), their quoted sources, and the source-organization table load
        from standards/description_criteria.json in Phase 3, so the standards shown here are the same
        ones the drafting checks apply. Quotations ship marked as needing a line-by-line check against
        the original documents until that check is confirmed.
      </p>
    </section>
  )
}
