// Five-step tablist with the exact keyboard pattern from the mockup:
// arrow keys move and select, Home/End jump, roving tabindex.

import { useRef } from 'react'
import { t, useI18n } from '../i18n'

export type StepId = 'media' | 'intent' | 'need' | 'review' | 'export'

export interface StepInfo {
  id: StepId
  label: string
  state: string
}

export function useSteps(): StepInfo[] {
  useI18n()
  return [
    { id: 'media', label: t('steps.media'), state: t('steps.state.not_started') },
    { id: 'intent', label: t('steps.intent'), state: t('steps.state.not_started') },
    { id: 'need', label: t('steps.need'), state: t('steps.state.not_started') },
    { id: 'review', label: t('steps.review'), state: t('steps.state.not_started') },
    { id: 'export', label: t('steps.export'), state: t('steps.state.not_started') },
  ]
}

export function StepTabs({
  steps,
  active,
  onSelect,
}: {
  steps: StepInfo[]
  active: StepId
  onSelect: (id: StepId) => void
}) {
  const refs = useRef<Array<HTMLButtonElement | null>>([])

  const onKeyDown = (event: React.KeyboardEvent, index: number) => {
    let next: number | null = null
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % steps.length
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp')
      next = (index - 1 + steps.length) % steps.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = steps.length - 1
    if (next === null) return
    event.preventDefault()
    onSelect(steps[next].id)
    refs.current[next]?.focus()
  }

  return (
    <div className="steps" role="tablist" aria-label={t('steps.label')}>
      {steps.map((step, index) => {
        const selected = step.id === active
        return (
          <button
            key={step.id}
            ref={(el) => {
              refs.current[index] = el
            }}
            type="button"
            className="step"
            role="tab"
            id={`tab-${step.id}`}
            aria-controls={`pane-${step.id}`}
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(step.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            <span className="step__n" aria-hidden="true">
              {index + 1}
            </span>
            <span>
              {step.label}
              <span className="step__state">{step.state}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
