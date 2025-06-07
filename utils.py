"""
Utility functions for media file organization and renaming.
"""

import os
import re
from pathlib import Path
import magic
import config

def get_file_type(file_path):
    """Determine the type of media file using magic numbers."""
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(str(file_path))
    
    if file_type.startswith('video/'):
        return 'video'
    elif file_type.startswith('audio/'):
        return 'audio'
    elif any(file_type.startswith(t) for t in ['application/', 'text/']):
        return 'software'
    return 'unknown'

def sanitize_filename(filename):
    """Remove or replace special characters that could cause filesystem issues."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized)
    return sanitized.strip()

def extract_year(filename):
    """Extract year from filename if present."""
    year_match = re.search(r'\((\d{4})\)', filename)
    if year_match:
        return year_match.group(1)
    return None

def extract_season_episode(filename):
    """Extract season and episode numbers from filename."""
    # Common patterns for season/episode matching
    patterns = [
        r'S(\d{1,2})E(\d{1,2})',  # S01E01
        r'(\d{1,2})x(\d{1,2})',    # 1x01
        r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})'  # Season 1 Episode 1
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return season, episode
    
    return None, None

def is_tv_show(filename):
    """Determine if the file is likely a TV show episode."""
    patterns = [
        r'S\d{1,2}E\d{1,2}',
        r'\d{1,2}x\d{1,2}',
        r'Season\s*\d{1,2}\s*Episode\s*\d{1,2}'
    ]
    return any(re.search(pattern, filename, re.IGNORECASE) for pattern in patterns)

def get_media_type(file_path, filename):
    """Determine if the file is a movie, TV show, music, book, or software."""
    file_type = get_file_type(file_path)
    suffix = file_path.suffix.lower()
    
    if file_type == 'video':
        return 'tv_show' if is_tv_show(filename) else 'movie'
    elif file_type == 'audio':
        # Check if it's an audiobook
        if suffix in config.VALID_AUDIOBOOK_EXTENSIONS:
            return 'audiobook'
        return 'music'
    elif suffix in config.VALID_BOOK_EXTENSIONS:
        return 'book'
    elif file_type == 'software':
        return 'software'
    return 'unknown'
