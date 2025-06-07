# Configuration settings for the media renamer

import os
from pathlib import Path

# Source and destination directories must be set in .env
SOURCE_DIR = os.getenv('MEDIA_SOURCE_DIR')
DEST_BASE_DIR = os.getenv('MEDIA_DEST_DIR')

if not SOURCE_DIR or not DEST_BASE_DIR:
    raise ValueError("MEDIA_SOURCE_DIR and MEDIA_DEST_DIR must be set in .env file")

# Subdirectories for different media types
MOVIES_DIR = Path(DEST_BASE_DIR) / 'Movies'
TV_SHOWS_DIR = Path(DEST_BASE_DIR) / 'TV Shows'
MUSIC_DIR = Path(DEST_BASE_DIR) / 'Music'
SOFTWARE_DIR = Path(DEST_BASE_DIR) / 'Software'
BOOKS_DIR = Path(DEST_BASE_DIR) / 'Books'  # Single directory for all books

# Extra content directories
EXTRAS_DIR = Path(DEST_BASE_DIR) / 'Extras'
EXTRAS_MOVIES_DIR = EXTRAS_DIR / 'Movies'
EXTRAS_TV_DIR = EXTRAS_DIR / 'TV Shows'

# Junk directories for unprocessed files
JUNK_DIR = Path(DEST_BASE_DIR) / 'junk'
JUNK_SUBTITLES_DIR = JUNK_DIR / 'subtitles'
JUNK_SUBTITLES_TV_DIR = JUNK_SUBTITLES_DIR / 'TV Shows'
JUNK_SUBTITLES_MOVIES_DIR = JUNK_SUBTITLES_DIR / 'Movies'

# Create directories if they don't exist
for directory in [MOVIES_DIR, TV_SHOWS_DIR, MUSIC_DIR, SOFTWARE_DIR, BOOKS_DIR,
                 JUNK_DIR, JUNK_SUBTITLES_DIR, JUNK_SUBTITLES_TV_DIR, 
                 JUNK_SUBTITLES_MOVIES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# OpenAI API configuration
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-0125-preview')  # Get model from env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Make sure to set this in .env file

# File extensions to process
VALID_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
VALID_AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.wav', '.m4b', '.aac'}
VALID_SOFTWARE_EXTENSIONS = {'.exe', '.dmg', '.zip', '.tar.gz', '.deb', '.rpm'}
VALID_BOOK_EXTENSIONS = {'.pdf', '.epub', '.mobi', '.azw', '.azw3', '.djvu', '.fb2'}
VALID_AUDIOBOOK_EXTENSIONS = {'.m4b', '.mp3', '.m4a', '.ogg', '.opus'}
