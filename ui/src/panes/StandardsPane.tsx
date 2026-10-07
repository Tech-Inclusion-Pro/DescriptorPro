import { useEffect, useState } from 'react'
import { api, type StandardsDoc } from '../api/client'
import { t, useI18n } from '../i18n'

const LED_BY_LABEL: Record<string, string> = {
  'blind-led': 'Blind-led',
  'deaf-led': 'Deaf-led, not blind-led',
  unconfirmed: 'Leadership not confirmed',
}

export function StandardsPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const [doc, setDoc] = useState<StandardsDoc | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getStandards().then(setDoc, (err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  return (
    <section className="pane" aria-labelledby="std-h" hidden={hidden}>
      <h2 id="std-h">{t('standards.title')}</h2>
      <p className="lede">{t('standards.lede')}</p>

      {error ? (
        <p className="flag" role="alert">
          {error}
        </p>
      ) : !doc ? (
        <p className="example">Loading the standards…</p>
      ) : (
        <>
          {!doc.quotes_verified ? (
            <div className="box" role="note">
              <h3>Quotations pending verification</h3>
              <p>{doc.verification_notice}</p>
            </div>
          ) : null}

          <div className="scroll" tabIndex={0} role="region" aria-label="The ten description criteria" style={{ marginBlockStart: '1rem' }}>
            <table>
              <caption>
                The ten criteria the drafting and flag system check against (version {doc.version}).
                These are the same entries the code reads.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Criterion</th>
                  <th scope="col">The rule, plainly</th>
                  <th scope="col">Quoted source</th>
                  <th scope="col">What the app does</th>
                  <th scope="col">Flags that cite it</th>
                </tr>
              </thead>
              <tbody>
                {doc.criteria.map((criterion) => (
                  <tr key={criterion.id} id={`standard-${criterion.id}`}>
                    <th scope="row">
                      {criterion.id}: {criterion.name}
                    </th>
                    <td>{criterion.plain_rule}</td>
                    <td>
                      <blockquote style={{ margin: 0 }}>“{criterion.quote}”</blockquote>
                      <p className="std" style={{ margin: '.25rem 0 0' }}>
                        {criterion.source_ids
                          .map((id) => doc.sources.find((s) => s.id === id))
                          .filter(Boolean)
                          .map((s) => s!.apa.split('.')[0])
                          .join('; ')}
                      </p>
                    </td>
                    <td>{criterion.app_behavior}</td>
                    <td>
                      {criterion.flag_types.length === 0 ? (
                        <span className="std">—</span>
                      ) : (
                        criterion.flag_types.map((flag) => (
                          <span className="chip" key={flag} style={{ marginInlineEnd: '.3rem' }}>
                            {flag.replace(/_/g, ' ')}
                          </span>
                        ))
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="box" style={{ marginBlockStart: '1.25rem' }}>
            <h3>Who leads the sources</h3>
            <p>
              These standards were chosen to come from organizations of people with disabilities. Not
              every source meets that bar; this table says so plainly.
            </p>
            <table>
              <caption className="sr-only">Source organizations and their leadership</caption>
              <thead>
                <tr>
                  <th scope="col">Source</th>
                  <th scope="col">Leadership</th>
                </tr>
              </thead>
              <tbody>
                {doc.sources.map((source) => (
                  <tr key={source.id}>
                    <td>{source.apa}</td>
                    <td>
                      <strong>{LED_BY_LABEL[source.led_by] ?? source.led_by}</strong>
                      <p className="std" style={{ margin: '.2rem 0 0' }}>
                        {source.leadership_note}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
