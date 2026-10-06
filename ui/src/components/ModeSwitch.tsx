import { t, useI18n } from '../i18n'

export type Mode = 'recorded' | 'live' | 'standards'

export function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (mode: Mode) => void }) {
  useI18n()
  const entries: Array<[Mode, string, string]> = [
    ['recorded', t('modes.recorded'), t('modes.recorded_hint')],
    ['live', t('modes.live'), t('modes.live_hint')],
    ['standards', t('modes.standards'), t('modes.standards_hint')],
  ]
  return (
    <div className="modes" role="group" aria-label={t('modes.label')}>
      {entries.map(([value, label, hint]) => (
        <button
          key={value}
          type="button"
          className="mode"
          aria-pressed={mode === value}
          onClick={() => onChange(value)}
        >
          {label} <small>{hint}</small>
        </button>
      ))}
    </div>
  )
}
