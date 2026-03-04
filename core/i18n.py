"""Internationalization support for La Mia Scribe — 22 languages."""

from core.translations import TRANSLATIONS, LANGUAGE_OPTIONS, RTL_LANGUAGES, WHISPER_LANGUAGE_MAP

_current_language = "en"
_change_callbacks = []


def set_language(code: str):
    """Set the active UI language and notify all registered callbacks."""
    global _current_language
    if code in TRANSLATIONS:
        _current_language = code
        for cb in list(_change_callbacks):
            try:
                cb()
            except Exception:
                pass


def get_language() -> str:
    return _current_language


def tr(key: str, **kwargs) -> str:
    """Get translated string for key. Supports {name}-style placeholders."""
    text = TRANSLATIONS.get(_current_language, {}).get(key)
    if text is None:
        text = TRANSLATIONS.get("en", {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def on_language_change(callback):
    """Register a callback invoked when the UI language changes."""
    if callback not in _change_callbacks:
        _change_callbacks.append(callback)


def remove_language_callback(callback):
    try:
        _change_callbacks.remove(callback)
    except ValueError:
        pass


def available_languages():
    """Return list of (code, display_name) for all supported languages."""
    return list(LANGUAGE_OPTIONS)


def is_rtl(code: str = None) -> bool:
    return (code or _current_language) in RTL_LANGUAGES


def whisper_language_code(code: str = None) -> str:
    """Map a UI language code to the closest Whisper-supported code."""
    lang = code or _current_language
    return WHISPER_LANGUAGE_MAP.get(lang, lang)
