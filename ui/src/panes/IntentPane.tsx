import { useEffect, useState } from 'react'
import type { IntentProfile } from '../api/client'
import { t, useI18n } from '../i18n'
import { useAnalysisStore } from '../stores/analysis'
import { useProjectStore } from '../stores/project'

export function IntentPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const analysis = useAnalysisStore()
  const project = useProjectStore()
  const [draft, setDraft] = useState('')

  useEffect(() => {
    if (project.projectId) void analysis.loadIntent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.projectId])

  const { questions, step, answers } = analysis
  const current = questions[step]
  const done = questions.length > 0 && step >= questions.length

  const submit = () => {
    analysis.answerCurrent(draft)
    setDraft('')
  }

  return (
    <section className="pane" role="tabpanel" id="pane-intent" aria-labelledby="tab-intent" tabIndex={0} hidden={hidden}>
      <h2>{t('intent.title')}</h2>
      <p className="lede">{t('intent.lede')}</p>

      {!project.projectId ? (
        <p className="example">Add media first. This whole step is optional — skipping it uses concise detail, auto-detected content type, and no named people.</p>
      ) : (
        <div className="cols">
          <div>
            <ul className="talk" aria-label="Conversation so far">
              {questions.slice(0, Math.min(step + 1, questions.length)).map((q, ix) => (
                <li className="app" key={q.id}>
                  <span className="who">DescriptorPro</span>
                  {q.text}
                  {ix < step ? (
                    <p className="std" style={{ marginBlockStart: '.35rem' }}>
                      {answers[q.id] ? `You: ${answers[q.id]}` : 'Skipped.'}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>

            {current ? (
              <>
                <div className="field">
                  <label htmlFor="intentText">Your answer</label>
                  <textarea
                    id="intentText"
                    rows={2}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        submit()
                      }
                    }}
                  />
                </div>
                <div className="row">
                  <button type="button" className="btn" onClick={submit}>
                    Next question
                  </button>
                  <button type="button" className="btn btn--quiet" onClick={() => analysis.skipCurrent()}>
                    Skip this question
                  </button>
                </div>
              </>
            ) : done ? (
              <div className="row">
                <button
                  type="button"
                  className="btn"
                  disabled={analysis.intentBusy}
                  onClick={() => void analysis.buildProfile()}
                >
                  {analysis.intentBusy ? 'Building your profile...' : 'Build my profile'}
                </button>
                <button type="button" className="btn btn--quiet" onClick={() => analysis.restartConversation()}>
                  Start over
                </button>
              </div>
            ) : null}
            {analysis.error ? (
              <p className="flag" role="alert">
                {analysis.error}
              </p>
            ) : null}
          </div>

          <ProfileEditor />
        </div>
      )}
    </section>
  )
}

function ProfileEditor() {
  const analysis = useAnalysisStore()
  const intent = analysis.intent

  if (!intent) {
    return (
      <div className="box">
        <h3>What the app understood</h3>
        <p>Nothing yet. Answers appear here, and every field can be edited before anything runs.</p>
      </div>
    )
  }

  const update = (patch: Partial<IntentProfile>) => {
    void analysis.saveIntent({ ...intent, ...patch })
  }

  return (
    <div className="box">
      <h3>What the app understood — edit anything</h3>
      <Field label="Audience" value={intent.audience} onSave={(v) => update({ audience: v })} />
      <Field label="Purpose" value={intent.purpose} onSave={(v) => update({ purpose: v })} />
      <div className="field">
        <label htmlFor="intent-content-type">Content type</label>
        <select
          id="intent-content-type"
          value={intent.content_type}
          onChange={(e) => update({ content_type: e.target.value })}
        >
          {['lecture_slides', 'screen_recording', 'demonstration', 'narrative', 'interview', 'other'].map(
            (option) => (
              <option key={option} value={option}>
                {option.replace('_', ' ')}
              </option>
            ),
          )}
        </select>
      </div>
      <div className="field">
        <label htmlFor="intent-detail">Detail level</label>
        <select
          id="intent-detail"
          value={intent.detail_level}
          onChange={(e) => update({ detail_level: e.target.value })}
        >
          <option value="concise">concise</option>
          <option value="standard">standard</option>
          <option value="detailed">detailed</option>
        </select>
      </div>
      <Field
        label="People to name (comma separated; I never guess names)"
        value={intent.people.map((p) => (p.role ? `${p.label} (${p.role})` : p.label)).join(', ')}
        onSave={(v) =>
          update({
            people: v
              .split(',')
              .map((raw) => raw.trim())
              .filter(Boolean)
              .map((raw) => {
                const match = raw.match(/^(.*?)\s*\((.*)\)$/)
                return {
                  label: match ? match[1] : raw,
                  role: match ? match[2] : '',
                  self_description: null,
                  source: 'user',
                }
              }),
          })
        }
      />
      <Field
        label="Languages (comma separated)"
        value={intent.languages.join(', ')}
        onSave={(v) => update({ languages: v.split(',').map((s) => s.trim()).filter(Boolean) })}
      />
      <Field
        label="Terms to spell exactly (comma separated)"
        value={intent.key_terms.join(', ')}
        onSave={(v) => update({ key_terms: v.split(',').map((s) => s.trim()).filter(Boolean) })}
      />
      <Field label="Notes" value={intent.notes} onSave={(v) => update({ notes: v })} />
    </div>
  )
}

function Field({ label, value, onSave }: { label: string; value: string; onSave: (v: string) => void }) {
  const [text, setText] = useState(value)
  useEffect(() => setText(value), [value])
  const id = `intent-${label.toLowerCase().replace(/[^a-z]+/g, '-')}`
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          if (text !== value) onSave(text)
        }}
      />
    </div>
  )
}
