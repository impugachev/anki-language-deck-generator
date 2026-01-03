import random
import logging
from pathlib import Path
import genanki
import anki_language_deck_generator.translators as translators
from anki_language_deck_generator.google_voice import GoogleVoice
from anki_language_deck_generator.dutch_wiktionary import DutchWiktionaryWord
from anki_language_deck_generator.image_downloader import ImageDownloader
from anki_language_deck_generator.tatoeba_usage_fetcher import UsageExampleFetcher


class AnkiDeckGenerator:
    def __init__(self, deck_name, source_language, target_language, working_dir, progress_callback=None):
        self.deck_name = deck_name
        self.source_language = source_language
        self.target_language = target_language
        self.working_dir = Path(working_dir)
        self.progress_callback = progress_callback
        self.deck = genanki.Deck(random.randint(1, 2**31 - 1), deck_name)
        self.media = []
        self.model = self._generate_model()

        # Track failed words
        self.failed_words = []

        # Initialize helper classes
        self.translator = translators.glosbe.Translator(self.source_language, self.target_language)
        self.reverso_voice = GoogleVoice(self.source_language, self.working_dir)
        self.image_downloader = ImageDownloader(self.working_dir)
        self.usage_fetcher = UsageExampleFetcher(self.source_language, self.target_language)

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
            random.randint(1, 2**31 - 1),
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

    def _make_note(self, word):
        self._make_word_dir(word)

        translation = self.translator.translate(word)
        usage = self.usage_fetcher.fetch_usage(word)

        sound_file = None
        image_file = None
        transcription = None
        part_of_speech = None
        plural = None
        article = None
        
        # TODO: fix it, doesn't work now
        if self.source_language == 'Dutch':
            wiktionary = DutchWiktionaryWord(word, self.working_dir)
            # the quality is so bad, so better always use gTTS
            # sound_file = wiktionary.try_download_sound()
            article = wiktionary.try_get_article()
            image_file = wiktionary.try_download_image()
            transcription = wiktionary.try_get_transcription()
            part_of_speech = wiktionary.try_get_part_of_speech()
            plural = wiktionary.try_get_plural_form()

        if sound_file is None:
            sound_file = self.reverso_voice.download_sound(word)

        if image_file is None:
            image_file = self.image_downloader.download_image(word)

        note = genanki.Note(
            model=self.model, fields=[
                f'{article} {word}' if article else word,
                translation,
                f'<img src="{image_file.name}">' if image_file else '',
                f'[sound:{sound_file.name}]' if sound_file else '',
                usage,
                transcription or '',
                part_of_speech or '',
                f'Plural: {plural}' if plural else ''
            ]
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
            logging.error(f"Error creating a card for the word '{word}': {e}")
            self.failed_words.append(word)

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
