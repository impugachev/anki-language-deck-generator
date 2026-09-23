import argparse
import logging
import tempfile
from anki_language_deck_generator.deck_generator import AnkiDeckGenerator, format_report


def main():
    parser = argparse.ArgumentParser(
        prog='anki-language-deck-generator',
        description='Generate simple Anki deck from list of words',
    )
    parser.add_argument('--deck-name', default='Generated deck', help='Name of the Anki deck')
    parser.add_argument(
        '--words-file',
        required=True,
        help='Path to the file with words, one word per line',
    )
    parser.add_argument('--source-language', required=True, help='Source language')
    parser.add_argument('--target-language', required=True, help='Target language')
    parser.add_argument('-o', '--output', default='deck.apkg', help='Output path for the Anki deck')
    parser.add_argument('--working-dir', help='Working directory for media files')
    args = parser.parse_args()

    if args.working_dir:
        working_dir = args.working_dir
    else:
        temp_dir = tempfile.TemporaryDirectory()
        working_dir = temp_dir.name

    logging.basicConfig(level=logging.INFO)  # TODO: make it better
    deck_generator = AnkiDeckGenerator(
        deck_name=args.deck_name,
        source_language=args.source_language,
        target_language=args.target_language,
        working_dir=working_dir,
    )
    words = []
    with open(args.words_file, 'r', encoding='UTF-8') as f:
        words = f.readlines()
    deck_generator.add_words(words)
    deck_generator.save_deck(args.output)

    # Print failed words (with reasons) and cards that should be checked, if any
    report = format_report(deck_generator.failed_words, deck_generator.warnings)
    if report:
        print('\n' + report)

    if not args.working_dir:
        temp_dir.cleanup()  # Clean up the temporary directory if it was used


if __name__ == '__main__':
    main()
