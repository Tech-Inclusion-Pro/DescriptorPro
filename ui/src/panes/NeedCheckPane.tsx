import { t, useI18n } from '../i18n'

export function NeedCheckPane({ hidden }: { hidden: boolean }) {
  useI18n()
  return (
    <section className="pane" role="tabpanel" id="pane-need" aria-labelledby="tab-need" tabIndex={0} hidden={hidden}>
      <h2>{t('need.title')}</h2>
      <p className="lede">{t('need.lede')}</p>

      <div className="scroll" tabIndex={0} role="region" aria-label="Segment findings table">
        <table>
          <caption>Findings by segment</caption>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">On screen</th>
              <th scope="col">Said aloud</th>
              <th scope="col">Finding</th>
              <th scope="col">Your decision</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={5}>No findings yet. Add media and run the need check (Phase 2).</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="cols" style={{ marginBlockStart: '1.25rem' }}>
        <div className="box">
          <h3>The rule this check applies</h3>
          <p>
            W3C states that if all important information in the video track is already conveyed in the
            audio track, no additional audio description is necessary. The app never marks a whole video
            as exempt by itself. It reports segment by segment and records your decision with your name
            and the date.
          </p>
          <p className="std">
            Standards checked: WCAG 2.1 and 2.2 (1.2.3, 1.2.5, 1.2.7, 1.2.8), Section 508, ADA Title II
            web rule, EN 301 549, DCMP Description Key. The app reports against these criteria; it does
            not give legal advice.
          </p>
        </div>
        <div className="box">
          <h3>Fix it at the source</h3>
          <p>
            When the need check finds segments where the speaker could have said the information aloud,
            re-recording suggestions appear here.
          </p>
        </div>
      </div>
    </section>
  )
}
