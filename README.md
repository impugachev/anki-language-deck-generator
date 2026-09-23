# Anki Language Deck Generator

A tool to automatically generate Anki decks for language learning, with translations, images, and pronunciations.

[Anki addon can be found here](https://ankiweb.net/shared/info/290385946)

> **Note:** The Anki addon currently supports only Windows platforms. The standalone tool can be used on any platform.

## Features

- Automatic translation using Glosbe, with Google Translate / MyMemory as a fallback for words Glosbe does not know (such cards are listed for review)
- Image search for visual associations
- Audio pronunciation using Google TTS
- Usage examples from Tatoeba
- Two-way cards (source -> target language and vice versa)
- Re-running a word updates its existing card instead of creating a duplicate
- A report at the end lists every word that failed, with the reason, and every card that should be checked
- Can be used as both a standalone tool and an Anki addon

## Supported Languages

The following languages are available for both source and target:

- Arabic
- English
- Catalan
- Czech
- Danish
- Dutch
- Finnish
- French
- German
- Greek
- Hebrew
- Italian
- Japanese
- Korean
- Chinese
- Norwegian
- Polish
- Portuguese
- Romanian
- Russian
- Spanish
- Swedish
- Turkish

> **Note:** For Dutch, additional information (such as article, plural, transcription, part of speech, and images) is fetched from Dutch Wiktionary for richer cards.

## Installation

### As a standalone tool:
```bash
pip install .
```

### As an Anki addon:
1. Open Anki
2. Go to Tools -> Add-ons
3. Click "Get Add-ons..."
4. Enter the addon code: 290385946
5. Restart Anki

## Usage

### Standalone tool:
```bash
python -m anki_language_deck_generator --words-file path/to/words.txt \
                            --source-language Russian \
                            --target-language Dutch \
                            --deck-name "My Language Deck" \
                            -o output_deck.apkg
```

### As an Anki addon:
1. Open Anki
2. Go to Tools -> Generate Language Learning Deck...
3. Select source and target languages
4. Enter your word list (one word per line)
5. Click "Generate Deck"

### Arguments (Standalone mode)

- `--words-file`: Path to a text file with words to learn, one per line (required)
- `--source-language`: Source language (required)
- `--target-language`: Target language (required)
- `--deck-name`: Name of the generated Anki deck (default: "Generated deck")
- `-o, --output`: Output path for the Anki deck (default: deck.apkg)
- `--working-dir`: Working directory for media files (optional)
