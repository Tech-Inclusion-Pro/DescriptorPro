import { APP_NAME } from '../lib/branding'
import { t, useI18n, AVAILABLE_LANGUAGES } from '../i18n'
import { useSessionStore } from '../stores/session'

// Compact flat-glass header, Atrium PageHeader idiom: one line, logo + name,
// subtitle faint, status chips pushed to the end.
export function AppBar() {
  const { lang, setLang } = useI18n()
  const connected = useSessionStore((s) => s.connected)

  return (
    <header className="appbar">
      <div className="wrap" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '.6rem 1rem' }}>
        <img className="appbar__logo" src="./logo.png" alt="" aria-hidden="true" />
        <div style={{ minInlineSize: 0 }}>
          <h1 className="appbar__name">{APP_NAME}</h1>
          <p className="appbar__tag">{t('app.tagline')}</p>
        </div>
        <span style={{ flex: '1 1 1rem' }} aria-hidden="true" />
        <ul className="chips" aria-label="Processing status">
          <li>
            <span className="chip">
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M6 11V8a6 6 0 0 1 12 0v3" fill="none" stroke="currentColor" strokeWidth="2.4" />
                <rect x="4" y="11" width="16" height="10" rx="2" fill="currentColor" />
              </svg>
              {t('app.local_chip')}
            </span>
          </li>
          <li>
            <span className="chip">{t('app.cloud_chip')}</span>
          </li>
          <li>
            <span className="chip">
              {connected ? t('app.service_connected') : t('app.service_disconnected')}
            </span>
          </li>
          <li>
            <label className="chip" htmlFor="langPick">
              {t('app.language')}
              <select
                id="langPick"
                value={lang}
                onChange={(event) => setLang(event.target.value)}
                style={{ font: 'inherit', border: 'none', background: 'transparent', color: 'inherit' }}
              >
                {AVAILABLE_LANGUAGES.map(([code, name]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </li>
        </ul>
      </div>
    </header>
  )
}
