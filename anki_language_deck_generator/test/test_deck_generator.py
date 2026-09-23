from types import SimpleNamespace
from unittest.mock import patch

import genanki
import pytest

from anki_language_deck_generator.deck_generator import (
    AnkiDeckGenerator,
    _stable_id,
    format_report,
)
from anki_language_deck_generator.dutch_wiktionary import WiktionaryUnavailableError
from anki_language_deck_generator.translators import TranslationNotFoundError

MODULE = 'anki_language_deck_generator.deck_generator'


@pytest.fixture
def generator(tmp_path):
    """A generator whose network helpers are all mocked to succeed."""
    with patch(f'{MODULE}.translators') as translators, \
            patch(f'{MODULE}.GoogleVoice') as voice, \
            patch(f'{MODULE}.ImageDownloader') as images, \
            patch(f'{MODULE}.UsageExampleFetcher') as usage, \
            patch(f'{MODULE}.DutchWiktionaryWord') as wiktionary:
        translators.glosbe.Translator.return_value.translate.return_value = 'sick'
        translators.machine.Translator.return_value.translate.return_value = 'office hours'
        translators.machine.Translator.return_value.last_engine = 'Google Translate'
        voice.return_value.download_sound.return_value = tmp_path / 'ziek.mp3'
        images.return_value.download_image.return_value = tmp_path / 'ziek.jpg'
        usage.return_value.fetch_usage.return_value = '<b>Ik ben ziek.</b>'
        page = wiktionary.return_value
        page.try_get_article.return_value = 'de'
        page.try_download_image.return_value = None
        page.try_get_transcription.return_value = '/zik/'
        page.try_get_part_of_speech.return_value = 'bijvoeglijk naamwoord'
        page.try_get_plural_form.return_value = None

        deck_generator = AnkiDeckGenerator('Test deck', 'Dutch', 'Russian', tmp_path)
        deck_generator.mocks = SimpleNamespace(
            glosbe=translators.glosbe.Translator.return_value,
            machine=translators.machine.Translator.return_value,
            images=images.return_value,
            wiktionary=wiktionary,
        )
        yield deck_generator


def test_note_uses_glosbe_translation_and_wiktionary_data(generator):
    generator.add_word('ziek')

    assert generator.failed_words == []
    assert generator.warnings == []
    [note] = generator.deck.notes
    assert note.fields[:2] == ['de ziek', 'sick']
    assert note.fields[2:4] == ['<img src="ziek.jpg">', '[sound:ziek.mp3]']
    assert note.fields[5:7] == ['/zik/', 'bijvoeglijk naamwoord']
    assert note.guid == genanki.guid_for('Dutch', 'Russian', 'ziek')


def test_falls_back_to_machine_translation_with_a_note(generator):
    generator.mocks.glosbe.translate.side_effect = TranslationNotFoundError('no entry')

    generator.add_word('spreekuur')

    [note] = generator.deck.notes
    assert note.fields[1] == 'office hours'
    assert generator.failed_words == []
    assert generator.warnings == [
        ('spreekuur', 'translated automatically by Google Translate, please check')
    ]


def test_word_fails_with_a_reason_when_nothing_translates(generator):
    generator.mocks.glosbe.translate.side_effect = TranslationNotFoundError('Glosbe has no entry')
    generator.mocks.machine.translate.side_effect = TranslationNotFoundError(
        "no machine translation for 'x' (Google Translate: 429)"
    )

    generator.add_word('x')

    assert generator.deck.notes == []
    assert generator.failed_word_names == ['x']
    [(_, reason)] = generator.failed_words
    assert 'Glosbe' in reason
    assert 'Google Translate: 429' in reason
    assert generator.warnings == []


def test_card_is_created_without_wiktionary_data_when_unavailable(generator):
    generator.mocks.wiktionary.side_effect = WiktionaryUnavailableError(
        'HTTP error 429 from Dutch Wiktionary'
    )

    generator.add_word('ziek')

    [note] = generator.deck.notes
    assert note.fields[0] == 'ziek'
    assert note.fields[1] == 'sick'
    assert note.fields[2:4] == ['<img src="ziek.jpg">', '[sound:ziek.mp3]']
    assert note.fields[5:8] == ['', '', '']
    assert generator.failed_words == []
    assert generator.warnings == [
        ('ziek', 'created without Dutch Wiktionary data: HTTP error 429 from Dutch Wiktionary')
    ]


def test_failed_word_drops_its_notes(generator):
    generator.mocks.wiktionary.side_effect = WiktionaryUnavailableError('HTTP error 429')
    generator.mocks.images.download_image.side_effect = RuntimeError(
        'Bing image search returned no image'
    )

    generator.add_word('ziek')

    assert generator.failed_words == [('ziek', 'Bing image search returned no image')]
    assert generator.warnings == []


def test_ids_are_stable_across_runs(tmp_path):
    first = AnkiDeckGenerator('My deck', 'Dutch', 'Russian', tmp_path)
    second = AnkiDeckGenerator('My deck', 'Dutch', 'Russian', tmp_path)
    other_pair = AnkiDeckGenerator('My deck', 'Dutch', 'English', tmp_path)

    assert first.model.model_id == second.model.model_id
    assert first.deck.deck_id == second.deck.deck_id
    assert other_pair.model.model_id != first.model.model_id
    assert 2 ** 30 <= first.model.model_id < 2 ** 31


def test_stable_id_depends_on_the_order_of_parts():
    assert _stable_id('model', 'Dutch', 'Russian') == _stable_id('model', 'Dutch', 'Russian')
    assert _stable_id('model', 'Dutch', 'Russian') != _stable_id('model', 'Russian', 'Dutch')


def test_format_report():
    text = format_report([('a', 'reason a')], [('b', 'note b')])
    assert text.splitlines() == [
        'Failed words (no card was created, copy this list to re-run them):',
        'a',
        '',
        'Reasons:',
        'a: reason a',
        '',
        'Notes (a card was created, but please check it):',
        'b: note b',
    ]
    assert format_report([], []) == ''
