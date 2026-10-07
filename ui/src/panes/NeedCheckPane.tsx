import { useEffect } from 'react'
import type { Segment } from '../api/client'
import { t, useI18n } from '../i18n'
import { useAnalysisStore } from '../stores/analysis'
import { useProjectStore } from '../stores/project'

function fmt(seconds: number): string {
  const s = Math.floor(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

const VERDICT_LABEL: Record<string, string> = {
  needed: 'Needs description',
  not_needed: 'Covered by the audio',
  uncertain: 'Not sure — listen and decide',
}

export function NeedCheckPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const analysis = useAnalysisStore()
  const project = useProjectStore()
  const report = analysis.report

  useEffect(() => {
    if (project.projectId) void analysis.loadSegments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.projectId])

  const coached = (report?.segments ?? []).filter((s) => s.need?.coach)

  return (
    <section className="pane" role="tabpanel" id="pane-need" aria-labelledby="tab-need" tabIndex={0} hidden={hidden}>
      <h2>{t('need.title')}</h2>
      <p className="lede">{t('need.lede')}</p>

      {!project.projectId ? (
        <p className="example">Add media and draft captions first, then run the check here.</p>
      ) : (
        <>
          <div className="row">
            <button
              type="button"
              className="btn"
              disabled={analysis.busy}
              onClick={() => void analysis.runNeedCheck()}
            >
              {analysis.busy
                ? analysis.phase === 'visual'
                  ? 'Looking at the screen...'
                  : 'Comparing with the audio...'
                : report && report.segments.length > 0
                  ? 'Run the check again'
                  : 'Check what needs description'}
            </button>
            {report ? (
              <p className="std" role="status">
                {report.tally.needed} parts need description, {report.tally.uncertain} uncertain,{' '}
                {report.tally.not_needed} covered by the audio.
              </p>
            ) : null}
          </div>
          {analysis.error ? (
            <p className="flag" role="alert">
              {analysis.error}
            </p>
          ) : null}

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
                {!report || report.segments.length === 0 ? (
                  <tr>
                    <td colSpan={5}>No findings yet. Run the check above.</td>
                  </tr>
                ) : (
                  report.segments.map((segment) => <SegmentRow key={segment.id} segment={segment} />)
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

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
            Standards checked:{' '}
            {report?.standards_checked.join('; ') ??
              'WCAG 2.1 and 2.2 (1.2.3, 1.2.5, 1.2.7, 1.2.8), Section 508, ADA Title II web rule, EN 301 549, DCMP Description Key'}
            . {report?.notice ?? 'The app reports against these criteria; it does not give legal advice.'}
          </p>
        </div>
        <div className="box">
          <h3>Fix it at the source</h3>
          {coached.length === 0 ? (
            <p>
              When the need check finds segments where the speaker could have said the information aloud,
              re-recording suggestions appear here.
            </p>
          ) : (
            <ul>
              {coached.map((segment) => (
                <li key={segment.id} style={{ marginBlockEnd: '.6rem' }}>
                  <strong>
                    {fmt(segment.start)} to {fmt(segment.end)}:
                  </strong>{' '}
                  {segment.need?.coach}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

function SegmentRow({ segment }: { segment: Segment }) {
  const analysis = useAnalysisStore()
  const project = useProjectStore()
  const need = segment.need
  const essential = segment.visual_facts.filter((f) => f.essential)
  const onScreen = essential.length > 0 ? essential : segment.visual_facts

  return (
    <tr>
      <td>
        {fmt(segment.start)}–{fmt(segment.end)}
      </td>
      <td>
        {onScreen.length === 0 ? (
          <span className="std">Nothing essential found</span>
        ) : (
          <ul style={{ margin: 0, paddingInlineStart: '1.1rem' }}>
            {onScreen.slice(0, 3).map((fact) => (
              <li key={fact.id}>
                {fact.text}
                {fact.flags.map((flag, ix) => (
                  <span className="chip" key={ix} style={{ marginInlineStart: '.4rem' }}>
                    {flag.type.replace(/_/g, ' ')}
                  </span>
                ))}
              </li>
            ))}
            {onScreen.length > 3 ? <li className="std">and {onScreen.length - 3} more</li> : null}
          </ul>
        )}
      </td>
      <td>
        {segment.transcript_window ? (
          <span>
            {segment.transcript_window.length > 120
              ? `${segment.transcript_window.slice(0, 120)}…`
              : segment.transcript_window}
          </span>
        ) : (
          <span className="std">Nothing spoken here</span>
        )}
      </td>
      <td>
        {need ? (
          <>
            <strong>{VERDICT_LABEL[need.verdict] ?? need.verdict}</strong>
            <p style={{ margin: '.2rem 0 0' }}>{need.reason}</p>
            <p className="std" style={{ margin: '.2rem 0 0' }}>
              {need.criteria.join(', ')}
            </p>
          </>
        ) : (
          <span className="std">Not checked yet</span>
        )}
      </td>
      <td>
        {need && (need.verdict === 'needed' || need.verdict === 'uncertain') ? (
          segment.decision.value !== 'undecided' ? (
            <>
              <strong>{segment.decision.value === 'describe' ? 'Describe it' : 'Skip it'}</strong>
              <p className="std" style={{ margin: '.2rem 0 0' }}>
                {segment.decision.by}
              </p>
              <button
                type="button"
                className="btn btn--quiet"
                onClick={() => void analysis.setDecision(segment.id, 'undecided')}
              >
                Undo
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn btn--quiet"
                disabled={!project.reviewerName.trim()}
                title={project.reviewerName.trim() ? undefined : 'Add your name on the Review step first'}
                onClick={() => void analysis.setDecision(segment.id, 'describe')}
              >
                Describe it
              </button>
              <button
                type="button"
                className="btn btn--quiet"
                disabled={!project.reviewerName.trim()}
                onClick={() => void analysis.setDecision(segment.id, 'skip')}
              >
                Skip it
              </button>
            </>
          )
        ) : (
          <span className="std">—</span>
        )}
      </td>
    </tr>
  )
}
