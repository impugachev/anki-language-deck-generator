import hashlib
import logging
from pathlib import Path

import genanki
import requests

import anki_language_deck_generator.translators as translators
from anki_language_deck_generator.dutch_wiktionary import (
    DutchWiktionaryWord,
    WiktionaryUnavailableError,
    WordNotFoundError,
)
from anki_language_deck_generator.google_voice import GoogleVoice
from anki_language_deck_generator.http_utils import make_session
from anki_language_deck_generator.image_downloader import ImageDownloader
from anki_language_deck_generator.tatoeba_usage_fetcher import UsageExampleFetcher
from anki_language_deck_generator.translators import TranslationNotFoundError

ID_RANGE_START = 2 ** 30


def _stable_id(*parts):
    """Deterministic Anki model/deck id in [2**30, 2**31) built from `parts`.

    Anki matches note types and decks by id, so the id must be the same on
    every run: a random id makes Anki import a new note type each time and
    rename it with a '+' suffix.
    """
    digest = hashlib.sha1('/'.join(parts).encode('utf-8')).digest()
    return ID_RANGE_START + int.from_bytes(digest[:4], 'big') % ID_RANGE_START


def format_report(failed_words, warnings):
    """Plain-text report of failed words (with reasons) and cards that need a check."""
    lines = []
    if failed_words:
        lines.append('Failed words (no card was created, copy this list to re-run them):')
        lines.extend(word for word, _ in failed_words)
        lines.append('')
        lines.append('Reasons:')
        lines.extend(f'{word}: {reason}' for word, reason in failed_words)
    if warnings:
        if lines:
            lines.append('')
        lines.append('Notes (a card was created, but please check it):')
        lines.extend(f'{word}: {note}' for word, note in warnings)
    return '\n'.join(lines)


class AnkiDeckGenerator:
    def __init__(self, deck_name, source_language, target_language, working_dir, progress_callback=None):
        self.deck_name = deck_name
        self.source_language = source_language
        self.target_language = target_language
        self.working_dir = Path(working_dir)
        self.progress_callback = progress_callback
        self.deck = genanki.Deck(_stable_id('deck', deck_name), deck_name)
        self.media = []
        self.model = self._generate_model()

        # (word, reason) for words that got no card
        self.failed_words = []
        # (word, note) for words that got a card which should be checked
        self.warnings = []

        # Initialize helper classes. One HTTP session is shared by the scrapers.
        self.session = make_session()
        self.translator = translators.glosbe.Translator(
            self.source_language, self.target_language, session=self.session
        )
        self.fallback_translator = translators.machine.Translator(
            self.source_language, self.target_language
        )
        self.voice = GoogleVoice(self.source_language, self.working_dir)
        self.image_downloader = ImageDownloader(self.working_dir)
        self.usage_fetcher = UsageExampleFetcher(
            self.source_language, self.target_language, session=self.session
        )

    @property
    def failed_word_names(self):
        return [word for word, _ in self.failed_words]

    def _make_word_dir(self, word):
        (self.working_dir / word).mkdir(parents=True, exist_ok=True)

    def _load_css(self):
        css_path = Path(__file__).parent / 'templates' / 'card_styles.css'
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_template(self, template_name):
        template_path = Path(__file__).parent / 'templates' / template_name
        with open(template_path, 'r', encoding='utf-8') as f:
            return (
                f.read()
                .replace('SOURCE_LANGUAGE', self.source_language)
                .replace('TARGET_LANGUAGE', self.target_language)
            )

    def _generate_model(self):
        return genanki.Model(
            _stable_id('model', self.source_language, self.target_language),
            f'Generated Model {self.source_language} to {self.target_language}',
            fields=[
                {'name': self.source_language},
                {'name': self.target_language},
                {'name': 'Image'},
                {'name': 'Sound'},
                {'name': 'Usage'},
                {'name': 'Transcription'},
                {'name': 'PartOfSpeech'},
                {'name': 'Plural'},
            ],
            templates=[
                {
                    'name': f'{self.target_language}+{self.source_language} -> {self.source_language}',
                    'qfmt': self._load_template('target_to_source_question.html'),
                    'afmt': self._load_template('target_to_source_answer.html'),
                },
                {
                    'name': f'{self.source_language}+{self.target_language} -> {self.target_language}',
                    'qfmt': self._load_template('source_to_target_question.html'),
                    'afmt': self._load_template('source_to_target_answer.html'),
                },
            ],
            css=self._load_css(),
        )

    def _translate(self, word):
        """Glosbe first, then machine translation (with a note for the user) if Glosbe has nothing."""
        try:
            return self.translator.translate(word)
        except TranslationNotFoundError as e:
            logging.warning(f'{e}, falling back to machine translation')
        try:
            translation = self.fallback_translator.translate(word)
        except TranslationNotFoundError as e:
            raise TranslationNotFoundError(f'Glosbe has no translation and {e}') from e
        self.warnings.append((
            word,
            f'translated automatically by {self.fallback_translator.last_engine}, please check',
        ))
        return translation

    def _fetch_dutch_wiktionary(self, word):
        """Optional enrichment from Dutch Wiktionary. Empty if the page is unavailable."""
        try:
            wiktionary = DutchWiktionaryWord(word, self.working_dir, session=self.session)
            return {
                'article': wiktionary.try_get_article(),
                # the sound quality is poor, so gTTS is always used instead
                'image_file': wiktionary.try_download_image(),
                'transcription': wiktionary.try_get_transcription(),
                'part_of_speech': wiktionary.try_get_part_of_speech(),
                'plural': wiktionary.try_get_plural_form(),
            }
        except (WordNotFoundError, WiktionaryUnavailableError, requests.RequestException) as e:
            logging.warning(f"Dutch Wiktionary data unavailable for '{word}': {e}")
            self.warnings.append((word, f'created without Dutch Wiktionary data: {e}'))
            return {}

    def _make_note(self, word):
        self._make_word_dir(word)

        translation = self._translate(word)
        usage = self.usage_fetcher.fetch_usage(word)

        enrichment = {}
        if self.source_language == 'Dutch':
            enrichment = self._fetch_dutch_wiktionary(word)
        article = enrichment.get('article')
        image_file = enrichment.get('image_file')
        transcription = enrichment.get('transcription')
        part_of_speech = enrichment.get('part_of_speech')
        plural = enrichment.get('plural')

        sound_file = self.voice.download_sound(word)
        if image_file is None:
            image_file = self.image_downloader.download_image(word)

        note = genanki.Note(
            model=self.model,
            fields=[
                f'{article} {word}' if article else word,
                translation,
                f'<img src="{image_file.name}">' if image_file else '',
                f'[sound:{sound_file.name}]' if sound_file else '',
                usage,
                transcription or '',
                part_of_speech or '',
                f'Plural: {plural}' if plural else ''
            ],
            # Stable per word, so re-running a word updates its card instead of duplicating it
            guid=genanki.guid_for(self.source_language, self.target_language, word),
        )
        media_files = []
        if sound_file:
            media_files.append(sound_file)
        if image_file:
            media_files.append(image_file)
        return note, media_files

    def add_word(self, word):
        logging.info(f"Creating a card for the word '{word}'...")
        try:
            note, media_files = self._make_note(word)
            self.deck.add_note(note)
            self.media.extend(media_files)
            logging.info(f"The card for the word '{word}' has been created!")
        except Exception as e:
            reason = str(e) or type(e).__name__
            logging.error(f"Error creating a card for the word '{word}': {reason}")
            self.failed_words.append((word, reason))
            # notes about a card that was never created are not useful
            self.warnings = [warning for warning in self.warnings if warning[0] != word]

    def add_words(self, words, skip_empty=True):
        total_words = len(words)
        for i, word in enumerate(words):
            word = word.strip()
            if word == '':
                if skip_empty:
                    continue
                else:
                    raise ValueError('Empty word found in the list')
            self.add_word(word)
            if self.progress_callback:
                self.progress_callback(i + 1, total_words)

    def save_deck(self, output_path):
        package = genanki.Package(self.deck)
        package.media_files = self.media
        package.write_to_file(output_path)
