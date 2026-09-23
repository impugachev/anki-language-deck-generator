"""Machine translation fallback, used only when Glosbe has no dictionary entry.

Engines are tried in order; each is a thin wrapper over deep-translator.
"""
import logging

from deep_translator import GoogleTranslator, MyMemoryTranslator

from anki_language_deck_generator.language_codes import get_language_codes
from anki_language_deck_generator.translators.errors import TranslationNotFoundError

# language_codes.LANGUAGES uses ISO 639-1 codes; the engines spell some differently
GOOGLE_CODES = {'zh': 'zh-CN', 'he': 'iw'}
MYMEMORY_CODES = {
    'ar': 'ar-SA', 'en': 'en-US', 'ca': 'ca-ES', 'cs': 'cs-CZ', 'da': 'da-DK',
    'nl': 'nl-NL', 'fi': 'fi-FI', 'fr': 'fr-FR', 'de': 'de-DE', 'el': 'el-GR',
    'he': 'he-IL', 'it': 'it-IT', 'ja': 'ja-JP', 'ko': 'ko-KR', 'zh': 'zh-CN',
    'no': 'nb-NO', 'pl': 'pl-PL', 'pt': 'pt-PT', 'ro': 'ro-RO', 'ru': 'ru-RU',
    'es': 'es-ES', 'sv': 'sv-SE', 'tr': 'tr-TR',
}
ENGINES = (
    ('Google Translate', GoogleTranslator, GOOGLE_CODES),
    ('MyMemory', MyMemoryTranslator, MYMEMORY_CODES),
)
# Unicode ranges a translation into these languages must contain. MyMemory sometimes
# answers with a Latin transliteration ("TOSHNOTA"), which is useless on a card.
TARGET_SCRIPTS = {
    'ru': [(0x0400, 0x04FF)],
    'el': [(0x0370, 0x03FF)],
    'he': [(0x0590, 0x05FF)],
    'ar': [(0x0600, 0x06FF)],
    'ja': [(0x3040, 0x30FF), (0x4E00, 0x9FFF)],
    'ko': [(0xAC00, 0xD7AF), (0x1100, 0x11FF)],
    'zh': [(0x4E00, 0x9FFF)],
}


def _in_target_script(text, target_code):
    ranges = TARGET_SCRIPTS.get(target_code)
    if not ranges:
        return True
    return any(low <= ord(char) <= high for char in text for low, high in ranges)


class Translator:
    def __init__(self, source_language, target_language):
        source_code, target_code = get_language_codes(source_language, target_language)
        self.target_code = target_code
        self.engines = []
        for name, engine_class, codes in ENGINES:
            try:
                engine = engine_class(
                    source=codes.get(source_code, source_code),
                    target=codes.get(target_code, target_code),
                )
            except Exception as e:
                logging.warning(
                    f'{name} is not available for {source_language} -> {target_language}: {e}'
                )
                continue
            self.engines.append((name, engine))
        # Name of the engine that produced the last translation
        self.last_engine = None

    def translate(self, word):
        errors = []
        for name, engine in self.engines:
            try:
                translation = engine.translate(word)
            except Exception as e:
                logging.warning(f"{name} failed for '{word}': {e}")
                errors.append(f'{name}: {str(e)[:120]}')
                continue
            translation = (translation or '').strip()
            if not translation:
                errors.append(f'{name}: empty result')
                continue
            if not _in_target_script(translation, self.target_code):
                errors.append(f'{name}: "{translation}" is not in the target script')
                continue
            self.last_engine = name
            return translation
        details = '; '.join(errors) or 'no engines available'
        raise TranslationNotFoundError(f"no machine translation for '{word}' ({details})")
