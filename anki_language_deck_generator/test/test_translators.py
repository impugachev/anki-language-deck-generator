from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from anki_language_deck_generator.translators import TranslationNotFoundError, glosbe, machine

GLOSBE_WITH_TRANSLATIONS = (
    '<html><p id="content-summary"><strong>sick, ill</strong> are the top translations '
    'of "ziek" into English.</p></html>'
)
# Words that only have machine translations on Glosbe: the summary is empty and the
# translations are loaded by JavaScript from a separate API.
GLOSBE_MACHINE_ONLY = (
    '<html><p id="content-summary"></p>'
    '<section id="translation_automatic"><h2>Automatic translations</h2></section></html>'
)


def fake_session(status, text=''):
    session = MagicMock()
    session.get.return_value = SimpleNamespace(
        status_code=status, text=text, headers={}, raise_for_status=lambda: None
    )
    return session


def test_glosbe_returns_first_translation():
    translator = glosbe.Translator(
        'Dutch', 'English', session=fake_session(200, GLOSBE_WITH_TRANSLATIONS)
    )
    assert translator.translate('ziek') == 'sick'


def test_glosbe_quotes_the_word_in_the_url():
    session = fake_session(200, GLOSBE_WITH_TRANSLATIONS)
    glosbe.Translator('Dutch', 'English', session=session).translate('ziek zijn')
    assert session.get.call_args.args[0] == 'https://glosbe.com/nl/en/ziek%20zijn'


def test_glosbe_404_means_no_translation():
    translator = glosbe.Translator('Dutch', 'English', session=fake_session(404))
    with pytest.raises(TranslationNotFoundError, match='no entry'):
        translator.translate('ziekmelden')


def test_glosbe_machine_only_page_means_no_translation():
    translator = glosbe.Translator(
        'Dutch', 'English', session=fake_session(200, GLOSBE_MACHINE_ONLY)
    )
    with pytest.raises(TranslationNotFoundError, match='no dictionary translation'):
        translator.translate('spreekuur')


def test_machine_translator_has_both_engines_for_a_supported_pair():
    translator = machine.Translator('Dutch', 'Russian')
    assert [name for name, _ in translator.engines] == ['Google Translate', 'MyMemory']


def test_machine_translator_falls_through_to_the_next_engine():
    translator = machine.Translator('Dutch', 'English')
    google = MagicMock()
    google.translate.side_effect = RuntimeError('too many requests')
    mymemory = MagicMock()
    mymemory.translate.return_value = ' office hours '
    translator.engines = [('Google Translate', google), ('MyMemory', mymemory)]

    assert translator.translate('spreekuur') == 'office hours'
    assert translator.last_engine == 'MyMemory'


def test_machine_translator_rejects_a_transliteration_for_a_cyrillic_target():
    translator = machine.Translator('Dutch', 'Russian')
    mymemory = MagicMock()
    mymemory.translate.return_value = 'TOSHNOTA'
    translator.engines = [('MyMemory', mymemory)]

    with pytest.raises(TranslationNotFoundError, match='not in the target script'):
        translator.translate('misselijk')


def test_machine_translator_accepts_cyrillic_for_a_cyrillic_target():
    translator = machine.Translator('Dutch', 'Russian')
    engine = MagicMock()
    engine.translate.return_value = 'тошнота'
    translator.engines = [('Google Translate', engine)]

    assert translator.translate('misselijk') == 'тошнота'


def test_machine_translator_does_not_check_script_for_latin_targets():
    translator = machine.Translator('Dutch', 'English')
    engine = MagicMock()
    engine.translate.return_value = 'nausea'
    translator.engines = [('MyMemory', engine)]

    assert translator.translate('misselijk') == 'nausea'


def test_machine_translator_raises_when_all_engines_fail():
    translator = machine.Translator('Dutch', 'Russian')
    engine = MagicMock()
    engine.translate.side_effect = RuntimeError('down')
    translator.engines = [('Google Translate', engine)]

    with pytest.raises(TranslationNotFoundError, match='Google Translate: down'):
        translator.translate('spreekuur')
