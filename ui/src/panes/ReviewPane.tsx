import { useRef, useState } from 'react'
import { mediaUrl, type CaptionCue } from '../api/client'
import { t, useI18n } from '../i18n'
import { useProjectStore } from '../stores/project'

function fmt(seconds: number): string {
  const s = Math.floor(seconds)
  const frac = (seconds - s).toFixed(1).slice(1)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}${frac}`
}

export function ReviewPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const project = useProjectStore()
  const mediaRef = useRef<HTMLVideoElement>(null)
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const [unapprovedOnly, setUnapprovedOnly] = useState(false)

  const cues = project.cues.filter(
    (c) => (!flaggedOnly || c.flags.length > 0) && (!unapprovedOnly || c.status !== 'approved'),
  )
  const approvedCount = project.cues.filter((c) => c.status === 'approved').length

  const playFrom = (cue: CaptionCue) => {
    const media = mediaRef.current
    if (!media) return
    media.currentTime = Math.max(0, cue.start - 0.2)
    void media.play()
  }

  return (
    <section className="pane" role="tabpanel" id="pane-review" aria-labelledby="tab-review" tabIndex={0} hidden={hidden}>
      <h2>{t('review.title')}</h2>
      <p className="lede">{t('review.lede')}</p>

      {!project.projectId ? (
        <p className="example">{t('review.empty')}</p>
      ) : (
        <div className="cols">
          <div>
            {/* Captions are being reviewed in the cue list; the track element
                arrives with the exported VTT, so reviewers use Play from this
                cue + the editable text below. */}
            <video
              ref={mediaRef}
              controls
              src={mediaUrl(project.projectId)}
              style={{ inlineSize: '100%', borderRadius: 'var(--radius)', background: 'var(--media-bg)' }}
              aria-label={t('review.player')}
            />
            <fieldset className="plain" style={{ marginBlockStart: '1rem' }}>
              <legend>{t('review.show')}</legend>
              <label className="check">
                <input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} />
                <span>{t('review.flagged_only')}</span>
              </label>
              <label className="check">
                <input type="checkbox" checked={unapprovedOnly} onChange={(e) => setUnapprovedOnly(e.target.checked)} />
                <span>{t('review.unapproved_only')}</span>
              </label>
            </fieldset>
            <div className="field" style={{ maxInlineSize: '20rem' }}>
              <label htmlFor="reviewerName">{t('review.your_name')}</label>
              <input
                id="reviewerName"
                type="text"
                value={project.reviewerName}
                onChange={(e) => project.setReviewerName(e.target.value)}
              />
              <p className="hint">{t('review.name_hint')}</p>
            </div>
            <p className="std">
              {approvedCount} / {project.cues.length} {t('review.approved_count')}
            </p>
          </div>

          <ol className="cues" aria-label={t('review.cues_label')}>
            {cues.map((cue) => (
              <Cue key={cue.id} cue={cue} onPlay={() => playFrom(cue)} />
            ))}
            {cues.length === 0 ? <li>{t('review.no_matches')}</li> : null}
          </ol>
        </div>
      )}
    </section>
  )
}

function Cue({ cue, onPlay }: { cue: CaptionCue; onPlay: () => void }) {
  const project = useProjectStore()
  const [text, setText] = useState(cue.text)
  const [speaker, setSpeaker] = useState(cue.speaker ?? '')
  const dirty = text !== cue.text
  const speakerDirty = speaker !== (cue.speaker ?? '')

  return (
    <li className="cue">
      <div className="cue__head">
        <span className="cue__kind">Caption</span>
        <span className="cue__time">
          {fmt(cue.start)} to {fmt(cue.end)}
        </span>
        <span className="cue__state">
          {cue.status === 'approved' ? `Approved by ${cue.approved_by}` : 'Draft'}
        </span>
      </div>
      <div className="field" style={{ maxInlineSize: '14rem' }}>
        <label htmlFor={`cue-speaker-${cue.id}`}>Speaker</label>
        <input
          id={`cue-speaker-${cue.id}`}
          type="text"
          value={speaker}
          placeholder="No label"
          onChange={(e) => setSpeaker(e.target.value)}
          onBlur={() => {
            if (speakerDirty) void project.editCue(cue.id, { speaker })
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`cue-${cue.id}`} className="sr-only">
          Caption text at {fmt(cue.start)}
        </label>
        <textarea
          id={`cue-${cue.id}`}
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            if (dirty) void project.editCue(cue.id, { text })
          }}
        />
      </div>
      {cue.flags.map((flag, ix) => (
        <div className="flag" key={ix}>
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 2 22 21H2Z" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M12 9v6M12 17.6v.4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
          <div>
            <strong>
              {flag.type === 'low_confidence'
                ? 'Low confidence word'
                : flag.type === 'reading_rate'
                  ? 'Fast reading speed'
                  : flag.type === 'needs_split'
                    ? 'Caption longer than two lines'
                    : flag.type}
            </strong>
            {flag.type === 'low_confidence' && flag.detail
              ? `"${flag.detail}" was hard to hear. Listen and confirm.`
              : flag.type === 'reading_rate' && flag.detail
                ? `About ${flag.detail}. Consider trimming or splitting this caption.`
                : flag.type === 'needs_split'
                  ? 'Split it into shorter captions so it is comfortable to read.'
                  : null}
          </div>
        </div>
      ))}
      <div className="row">
        <button type="button" className="btn btn--quiet" onClick={onPlay}>
          Play from this cue
        </button>
        {cue.status === 'approved' ? (
          <button type="button" className="btn btn--quiet" onClick={() => void project.approveCue(cue.id, false)}>
            Undo approval
          </button>
        ) : (
          <button
            type="button"
            className="btn btn--quiet"
            disabled={!project.reviewerName.trim()}
            onClick={() => void project.approveCue(cue.id, true)}
          >
            Approve
          </button>
        )}
      </div>
    </li>
  )
}
