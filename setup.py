import re

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

with open('anki_language_deck_generator/version.py', 'r', encoding='utf-8') as fh:
    version = re.search(r"__version__ = '([^']+)'", fh.read()).group(1)

setup(
    name='anki-language-deck-generator',
    version=version,
    author='Igor Pugachev',
    description='A tool to automatically generate Anki decks for language learning',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/impugachev/anki-language-deck-generator',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'anki_language_deck_generator': ['templates/*'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'icrawler==0.6.10',
        'genanki==0.13.1',
        'requests==2.32.3',
        'beautifulsoup4==4.12.3',
        'gTTS==2.5.4',
        'deep-translator==1.11.4',
    ],
    extras_require={
        'dev': [
            'pytest',
        ]
    },
    entry_points={
        'console_scripts': [
            'anki-language-deck-generator=anki_language_deck_generator.__main__:main',
        ],
    },
)
