import { useEffect, useRef, useState } from 'react'
import { mediaUrl, type CaptionCue, type DescriptionCue, type ImageItem } from '../api/client'
import { t, useI18n } from '../i18n'
import { useAnalysisStore } from '../stores/analysis'
import { useProjectStore } from '../stores/project'

function fmt(seconds: number): string {
  const s = Math.floor(seconds)
  const frac = (seconds - s).toFixed(1).slice(1)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}${frac}`
}

export function ReviewPane({ hidden }: { hidden: boolean }) {
  useI18n()
  const project = useProjectStore()
  const analysis = useAnalysisStore()
  const mediaRef = useRef<HTMLVideoElement>(null)
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const [unapprovedOnly, setUnapprovedOnly] = useState(false)

  useEffect(() => {
    if (project.projectId) {
      void analysis.loadDescriptions()
      void analysis.loadImages()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.projectId])

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

          <div>
            <ol className="cues" aria-label={t('review.cues_label')}>
              {cues.map((cue) => (
                <Cue key={cue.id} cue={cue} onPlay={() => playFrom(cue)} />
              ))}
              {cues.length === 0 ? <li>{t('review.no_matches')}</li> : null}
            </ol>

            <DescriptionSection
              onPlay={(start) => {
                const media = mediaRef.current
                if (!media) return
                media.currentTime = Math.max(0, start - 0.2)
                void media.play()
              }}
            />

            <ImagesSection />
          </div>
        </div>
      )}
    </section>
  )
}

function DescriptionSection({ onPlay }: { onPlay: (start: number) => void }) {
  const analysis = useAnalysisStore()
  const { descriptions, addedRunningTime } = analysis
  const approved = descriptions.filter((c) => c.status === 'approved').length

  return (
    <section aria-labelledby="desc-review-h" style={{ marginBlockStart: '1.5rem' }}>
      <h3 id="desc-review-h">Audio descriptions</h3>
      <div className="field" style={{ maxInlineSize: '24rem' }}>
        <label htmlFor="ad-style">Description style</label>
        <select
          id="ad-style"
          value={analysis.adStyle}
          onChange={(e) => analysis.setAdStyle(e.target.value)}
          disabled={analysis.busy}
        >
          <option value="standard">Standard — fit in natural pauses</option>
          <option value="extended_when_needed">Extended when needed — pause the video if a description does not fit</option>
          <option value="extended_before_content">Extended before content — describe each part before it plays</option>
        </select>
        <p className="hint">
          Extended descriptions pause the video while the narration plays, so nothing is cut short.
        </p>
      </div>
      <div className="row">
        <button
          type="button"
          className="btn"
          disabled={analysis.busy}
          onClick={() => void analysis.runDescribe()}
        >
          {analysis.busy && analysis.phase === 'describe'
            ? 'Drafting and checking...'
            : descriptions.length > 0
              ? 'Draft descriptions again'
              : 'Draft descriptions for decided parts'}
        </button>
        {descriptions.length > 0 ? (
          <p className="std" role="status">
            {approved} / {descriptions.length} approved
            {addedRunningTime > 0
              ? ` — extended descriptions add ${addedRunningTime.toFixed(0)} s of pause time`
              : ''}
          </p>
        ) : null}
      </div>
      {analysis.error ? (
        <p className="flag" role="alert">
          {analysis.error}
        </p>
      ) : null}
      <ol className="cues" aria-label="Description cues">
        {descriptions.map((cue) => (
          <DescriptionCueItem key={cue.id} cue={cue} onPlay={() => onPlay(cue.start)} />
        ))}
        {descriptions.length === 0 ? (
          <li className="std">
            None yet. Mark parts "Describe it" on the need-check step, then draft here.
          </li>
        ) : null}
      </ol>
    </section>
  )
}

function ImagesSection() {
  const analysis = useAnalysisStore()
  const { images } = analysis
  if (images.length === 0) return null
  const approved = images.filter((i) => i.status === 'approved').length
  const undescribed = images.filter((i) => !i.alt).length

  return (
    <section aria-labelledby="img-review-h" style={{ marginBlockStart: '1.5rem' }}>
      <h3 id="img-review-h">Image descriptions</h3>
      <div className="row">
        <button
          type="button"
          className="btn"
          disabled={analysis.busy}
          onClick={() => void analysis.describeImages()}
        >
          {analysis.busy && analysis.phase === 'describe'
            ? 'Describing images...'
            : undescribed > 0
              ? `Describe ${undescribed} images`
              : 'Describe images again'}
        </button>
        <p className="std" role="status">
          {approved} / {images.length} approved
        </p>
      </div>
      <ol className="cues" aria-label="Image descriptions">
        {images.map((item) => (
          <ImageItemRow key={item.id} item={item} />
        ))}
      </ol>
    </section>
  )
}

const IMAGE_FLAG_LABEL: Record<string, string> = {
  alt_too_long: 'Alt text is long',
  unverified_claim: 'Could not be confirmed',
  identity_inference: 'Guesses identity',
  interpretation: 'Interprets instead of describing',
  camera_language: 'Camera language',
  name_from_user: 'Name you supplied',
  name_from_screen: 'Name read from the image',
}

function ImageItemRow({ item }: { item: ImageItem }) {
  const analysis = useAnalysisStore()
  const project = useProjectStore()
  const [alt, setAlt] = useState(item.alt)
  const [long, setLong] = useState(item.long_description)
  useEffect(() => setAlt(item.alt), [item.alt])
  useEffect(() => setLong(item.long_description), [item.long_description])
  const needsDecorativeCall = item.decorative.suggested && item.decorative.confirmed === null

  return (
    <li className="cue">
      <div className="cue__head">
        <span className="cue__kind">Image</span>
        <span className="cue__time">{item.name}</span>
        {item.kind !== 'other' ? <span className="chip">{item.kind}</span> : null}
        <span className="cue__state">
          {item.status === 'approved' ? `Approved by ${item.approved_by}` : 'Draft'}
        </span>
      </div>
      <div className="field">
        <label htmlFor={`img-alt-${item.id}`}>
          Alt text <small>({alt.length} characters; aim under 150)</small>
        </label>
        <input
          id={`img-alt-${item.id}`}
          type="text"
          value={alt}
          onChange={(e) => setAlt(e.target.value)}
          onBlur={() => {
            if (alt !== item.alt) void analysis.patchImage(item.id, { alt })
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`img-long-${item.id}`}>Long description (optional)</label>
        <textarea
          id={`img-long-${item.id}`}
          rows={3}
          value={long}
          onChange={(e) => setLong(e.target.value)}
          onBlur={() => {
            if (long !== item.long_description)
              void analysis.patchImage(item.id, { long_description: long })
          }}
        />
      </div>
      {item.decorative.suggested ? (
        <div className="flag">
          <div>
            <strong>Suggested decorative</strong>
            {item.decorative.reason ? ` — ${item.decorative.reason}` : null}
            <p className="std" style={{ margin: '.2rem 0 .4rem' }}>
              You decide, not the tool. Decorative images are skipped by screen readers.
            </p>
            {item.decorative.confirmed === null ? (
              <div className="row">
                <button
                  type="button"
                  className="btn btn--quiet"
                  onClick={() => void analysis.patchImage(item.id, { decorative_confirmed: true })}
                >
                  Yes, it is decorative
                </button>
                <button
                  type="button"
                  className="btn btn--quiet"
                  onClick={() => void analysis.patchImage(item.id, { decorative_confirmed: false })}
                >
                  No, describe it
                </button>
              </div>
            ) : (
              <p className="std">
                Your call: {item.decorative.confirmed ? 'decorative' : 'not decorative'}
              </p>
            )}
          </div>
        </div>
      ) : null}
      {item.flags.map((flag, ix) => (
        <div className="flag" key={ix}>
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 2 22 21H2Z" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M12 9v6M12 17.6v.4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
          <div>
            <strong>{IMAGE_FLAG_LABEL[flag.type] ?? flag.type}</strong>
            {flag.detail ? ` — ${flag.detail}` : null}
          </div>
        </div>
      ))}
      <div className="row">
        {item.status === 'approved' ? (
          <button
            type="button"
            className="btn btn--quiet"
            onClick={() => void analysis.patchImage(item.id, { approve: false })}
          >
            Undo approval
          </button>
        ) : (
          <button
            type="button"
            className="btn btn--quiet"
            disabled={!project.reviewerName.trim() || needsDecorativeCall}
            title={
              needsDecorativeCall
                ? 'Decide the decorative question first'
                : project.reviewerName.trim()
                  ? undefined
                  : 'Add your name above first'
            }
            onClick={() => void analysis.patchImage(item.id, { approve: true })}
          >
            Approve
          </button>
        )}
      </div>
    </li>
  )
}

const DESCRIPTION_FLAG_LABEL: Record<string, string> = {
  contradicted: 'Contradicted by the video',
  unverified_claim: 'Could not be confirmed',
  too_long_for_gap: 'Too long for the pause',
  shortened_for_gap: 'Shortened to fit the pause',
  identity_inference: 'Guesses identity',
  interpretation: 'Interprets instead of describing',
  camera_language: 'Camera language',
  name_from_user: 'Name you supplied',
  name_from_screen: 'Name read from the screen',
}

function DescriptionCueItem({ cue, onPlay }: { cue: DescriptionCue; onPlay: () => void }) {
  const analysis = useAnalysisStore()
  const project = useProjectStore()
  const [text, setText] = useState(cue.text)
  useEffect(() => setText(cue.text), [cue.text])
  const dirty = text !== cue.text
  const hasSuggestion = cue.suggested_text !== undefined && cue.suggested_text !== cue.text

  return (
    <li className="cue">
      <div className="cue__head">
        <span className="cue__kind">Description</span>
        <span className="cue__time">
          {fmt(cue.start)} · about {cue.est_duration.toFixed(0)} s
        </span>
        <span className="chip">{cue.mode === 'extended' ? 'extended (video pauses)' : 'in a pause'}</span>
        {cue.placement === 'before_content' ? <span className="chip">before the content</span> : null}
        <span className="cue__state">
          {cue.status === 'approved' ? `Approved by ${cue.approved_by}` : 'Draft'}
        </span>
      </div>
      <div className="field">
        <label htmlFor={`desc-${cue.id}`} className="sr-only">
          Description at {fmt(cue.start)}
        </label>
        <textarea
          id={`desc-${cue.id}`}
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            if (dirty) void analysis.patchDescription(cue.id, { text })
          }}
        />
      </div>
      {hasSuggestion ? (
        <div className="flag">
          <div>
            <strong>Verification suggests:</strong> {cue.suggested_text}
            <div className="row" style={{ marginBlockStart: '.3rem' }}>
              <button
                type="button"
                className="btn btn--quiet"
                onClick={() => void analysis.patchDescription(cue.id, { use: 'suggested' })}
              >
                Use the checked version
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {cue.flags.map((flag, ix) => (
        <div className="flag" key={ix}>
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 2 22 21H2Z" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M12 9v6M12 17.6v.4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
          <div>
            <strong>{DESCRIPTION_FLAG_LABEL[flag.type] ?? flag.type}</strong>
            {flag.detail ? ` — ${flag.detail}` : null}
            {cue.criteria.length > 0 ? (
              <p className="std" style={{ margin: '.2rem 0 0' }}>
                Standard: {cue.criteria.join(', ')} (see the Standards view)
              </p>
            ) : null}
          </div>
        </div>
      ))}
      <div className="row">
        <button type="button" className="btn btn--quiet" onClick={onPlay}>
          Play from this cue
        </button>
        {cue.short_text && cue.short_text !== cue.text ? (
          <button
            type="button"
            className="btn btn--quiet"
            onClick={() => void analysis.patchDescription(cue.id, { use: 'short' })}
          >
            Use the short version
          </button>
        ) : null}
        {cue.full_text && cue.full_text !== cue.text ? (
          <button
            type="button"
            className="btn btn--quiet"
            onClick={() => void analysis.patchDescription(cue.id, { use: 'full' })}
          >
            Use the full version
          </button>
        ) : null}
        {cue.status === 'approved' ? (
          <button
            type="button"
            className="btn btn--quiet"
            onClick={() => void analysis.patchDescription(cue.id, { approve: false })}
          >
            Undo approval
          </button>
        ) : (
          <button
            type="button"
            className="btn btn--quiet"
            disabled={!project.reviewerName.trim()}
            onClick={() => void analysis.patchDescription(cue.id, { approve: true })}
          >
            Approve
          </button>
        )}
      </div>
    </li>
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
