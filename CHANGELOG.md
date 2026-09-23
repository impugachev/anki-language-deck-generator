# Changelog

## 0.6.0 (2026-09-23)

### Fixed
- Words no longer fail in bulk when Dutch Wiktionary rate-limits requests (HTTP 429). Requests are retried honouring `Retry-After`, one HTTP session with a descriptive User-Agent is reused, and if Wiktionary still cannot be reached the card is created without the extra Dutch data instead of failing.
- Each run no longer creates a new note type ("Generated Model ... +++"). Note type, deck and note ids are now stable, and re-running a word updates its existing card instead of adding a duplicate.
- The Dutch article, plural, transcription and part of speech are read only from the Dutch section of the Wiktionary page. The preposition "sinds" used to get the article "het" from the Danish noun section of its page.
- Wiktionary images work again (Wikimedia moved thumbnails to thumb.wikimedia.org).
- Tatoeba example translations are requested in the chosen target language. They were always Russian.

### Added
- Fallback translation via Google Translate, then MyMemory, when Glosbe has no dictionary entry. Results that are not in the target script are rejected. Such cards are listed for review at the end of the run.
- The report at the end of a run names every failed word with the reason, and every card that should be checked.
- Reflexive verbs entered as "zich ..." (for example "zich wassen") get their Dutch Wiktionary data from the bare infinitive, while the translation, audio and image keep the full phrase.

### Packaging
- New dependency `deep-translator` (vendored in the addon package).
