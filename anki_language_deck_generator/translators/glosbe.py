from urllib.parse import quote

from bs4 import BeautifulSoup

from anki_language_deck_generator.http_utils import get_with_retry, make_session
from anki_language_deck_generator.language_codes import get_language_codes
from anki_language_deck_generator.translators.errors import TranslationNotFoundError


class Translator:
    def __init__(self, source_language, target_language, session=None):
        source_language_code, target_language_code = get_language_codes(
            source_language, target_language
        )
        self.base_url = '/'.join(
            ['https://glosbe.com', source_language_code, target_language_code]
        )
        self.session = session or make_session()

    def translate(self, word):
        response = get_with_retry(self.session, f'{self.base_url}/{quote(word)}')
        if response.status_code == 404:
            raise TranslationNotFoundError(f"Glosbe has no entry for '{word}'")
        response.raise_for_status()

        # Parse HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find content summary paragraph
        summary_paragraph = soup.find('p', id='content-summary')
        if summary_paragraph is None:
            raise TranslationNotFoundError(
                f"Glosbe page for '{word}' has no content summary (page layout changed?)"
            )

        # Find translations in strong tags. Words that only have machine
        # translations on Glosbe have an empty summary: those translations are
        # loaded by JavaScript and are not in the HTML.
        translations = summary_paragraph.find('strong')
        if translations is None:
            raise TranslationNotFoundError(
                f"Glosbe has no dictionary translation for '{word}'"
            )

        # Extract and split translations
        return translations.text.split(", ")[0]
