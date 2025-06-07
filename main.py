"""
Media file organizer and renamer using OpenAI API.
Monitors a directory for new files and organizes them based on type and content.
"""

import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import openai
from dotenv import load_dotenv

import config
from utils import (
    get_media_type,
    sanitize_filename,
    extract_year,
    extract_season_episode
)

def log_operation(operation_type, source_path, destination_path=None, extra_info=None):
    """Log file operations to a log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = Path(config.DEST_BASE_DIR) / 'file_operations.log'
    
    log_entry = f"[{timestamp}] {operation_type}:\n"
    log_entry += f"  Source: {source_path}\n"
    if destination_path:
        log_entry += f"  Destination: {destination_path}\n"
    if extra_info:
        log_entry += f"  Info: {extra_info}\n"
    log_entry += "-" * 80 + "\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MediaFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.client = openai.OpenAI()
        self.prompts = {}
        self.load_prompts()

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def load_prompts(self):
        """Load all prompt files from the prompts directory."""
        prompts_dir = Path(__file__).parent / 'prompts'
        for prompt_file in prompts_dir.glob('*.txt'):
            prompt_name = prompt_file.stem
            with open(prompt_file, 'r') as f:
                self.prompts[prompt_name] = f.read()

    def analyze_franchise(self, movie_title, year):
        """Analyze if a movie belongs to a franchise."""
        try:
            messages = [
                {"role": "system", "content": self.prompts['franchise_detection_prompt']},
                {"role": "user", "content": f"Movie: {movie_title}\nYear: {year}"}
            ]
            
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=150,
                response_format={ "type": "json_object" }
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logging.error(f"Error analyzing franchise for {movie_title}: {str(e)}")
            return None

    def is_extra_content(self, filename, parent_folders):
        """Check if the file is likely extra content."""
        extra_keywords = [
            'behind the scenes', 'bts', 'making of', 'deleted scenes',
            'extra', 'extras', 'special features', 'bonus', 'interview',
            'featurette', 'commentary', 'blooper', 'gag reel'
        ]
        
        search_text = (filename + ' ' + parent_folders).lower()
        return any(keyword in search_text for keyword in extra_keywords)

    def analyze_book(self, file_path, is_audiobook=False):
        """Analyze book or audiobook files using OpenAI API."""
        try:
            parent_folders = '/'.join(file_path.relative_to(config.SOURCE_DIR).parent.parts)
            
            messages = [
                {"role": "system", "content": self.prompts['book_analysis_prompt']},
                {"role": "user", "content": f"""Please analyze this book file and provide information:
                Filename: {file_path.name}
                Parent folders: {parent_folders}
                Type: {'Audiobook' if is_audiobook else 'Ebook'}"""}
            ]

            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=250,
                response_format={ "type": "json_object" }
            )

            result = json.loads(response.choices[0].message.content)
            
            # Create the directory structure under the shared Books directory
            if result.get('is_standalone'):
                # For standalone books
                authors = result.get('authors', ['Unknown Author'])
                author_text = f" - {authors[0]}" if authors else ""
                
                # Add format prefix for audiobooks
                format_prefix = "[Audiobook] " if is_audiobook else ""
                book_dir = config.BOOKS_DIR / f"{format_prefix}{sanitize_filename(result['title'])}{author_text}"
            else:
                # For series
                series_name = result.get('series_name', 'Unknown Series')
                series_num = result.get('series_number', '')
                
                # Create format-specific subdirectories within series
                format_dir = "Audiobooks" if is_audiobook else "Ebooks"
                series_dir = config.BOOKS_DIR / sanitize_filename(series_name) / format_dir
                
                number_prefix = f"{str(series_num).zfill(2)} - " if series_num else ""
                book_dir = series_dir / f"{sanitize_filename(number_prefix + result['title'])}"
            
            return {
                'filename': file_path.name,  # Keep original filename for the actual file
                'directory': book_dir,
                'title': result.get('title'),
                'is_standalone': result.get('is_standalone', True),
                'series_name': result.get('series_name'),
                'book_type': 'audiobook' if is_audiobook else 'book'
            }

        except Exception as e:
            logging.error(f"Error analyzing book: {str(e)}")
            return None

    def analyze_file(self, file_path, media_type):
        """Analyze file using OpenAI API to get proper naming and metadata."""
        try:
            if media_type == 'book':
                return self.analyze_book(file_path, is_audiobook=False)
            elif media_type == 'audiobook':
                return self.analyze_book(file_path, is_audiobook=True)
                
            # Include parent folder names for better context
            parent_folders = '/'.join(file_path.relative_to(config.SOURCE_DIR).parent.parts)
            
            # Check if it's likely extra content
            is_extra = self.is_extra_content(file_path.name, parent_folders)
            
            # Prepare the message for OpenAI
            messages = [
                {"role": "system", "content": self.prompts['file_analysis_prompt']},
                {"role": "user", "content": f"""Please analyze this file path and provide the following information in JSON format:
                Filename: {file_path.name}
                Parent folders: {parent_folders}
                Media type: {media_type}
                Is Extra Content: {is_extra}
                
                For TV Shows, include:
                - show_name
                - season_number
                - episode_number
                - episode_title
                - is_extra (true/false)
                - extra_type (if applicable: behind the scenes, deleted scenes, etc.)
                
                For Movies, include:
                - movie_title
                - year
                - is_extra (true/false)
                - extra_type (if applicable)
                - related_title (main movie/show this extra belongs to)"""}
            ]

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=250,
                response_format={ "type": "json_object" }
            )

            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            if media_type == 'tv_show':
                season_num = str(result.get('season_number', '01')).zfill(2)
                episode_num = str(result.get('episode_number', '01')).zfill(2)
                show_name = result.get('show_name', 'Unknown Show')
                episode_title = result.get('episode_title', '')
                is_extra = result.get('is_extra', False)
                
                if is_extra:
                    # Create path for TV show extras
                    base_dir = Path(config.EXTRAS_TV_DIR) / sanitize_filename(show_name)
                    if season_num != '00':
                        base_dir = base_dir / f"Season {season_num}"
                    extra_type = result.get('extra_type', 'Bonus Content')
                    new_filename = f"{show_name} - S{season_num}E{episode_num} - {extra_type} - {episode_title or 'Special'}{file_path.suffix}"
                else:
                    # Regular TV show episode
                    base_dir = Path(config.TV_SHOWS_DIR) / sanitize_filename(show_name) / f"Season {season_num}"
                    new_filename = f"{show_name} - S{season_num}E{episode_num}{' - ' + episode_title if episode_title else ''}{file_path.suffix}"
                
                return {
                    'filename': sanitize_filename(new_filename),
                    'directory': base_dir,
                    'show_name': show_name,
                    'is_extra': is_extra
                }
            
            elif media_type == 'movie':
                movie_title = result.get('movie_title', 'Unknown Movie')
                year = result.get('year', '')
                is_extra = result.get('is_extra', False)
                
                if is_extra:
                    # Handle movie extras
                    related_title = result.get('related_title', movie_title)
                    extra_type = result.get('extra_type', 'Bonus Content')
                    franchise_info = self.analyze_franchise(related_title, year)
                    
                    if franchise_info and franchise_info.get('franchise_name'):
                        base_dir = Path(config.EXTRAS_MOVIES_DIR) / sanitize_filename(franchise_info['franchise_sub_dir'])
                    else:
                        base_dir = Path(config.EXTRAS_MOVIES_DIR)
                    
                    new_filename = f"{related_title} ({year}) - {extra_type}{file_path.suffix}"
                else:
                    # Regular movie
                    franchise_info = self.analyze_franchise(movie_title, year)
                    if franchise_info and franchise_info.get('franchise_name'):
                        base_dir = config.MOVIES_DIR / sanitize_filename(franchise_info['franchise_sub_dir'])
                    else:
                        base_dir = config.MOVIES_DIR
                    
                    new_filename = f"{movie_title} ({year}){file_path.suffix}" if year else f"{movie_title}{file_path.suffix}"
                
                return {
                    'filename': sanitize_filename(new_filename),
                    'directory': base_dir,
                    'title': movie_title,
                    'franchise_info': franchise_info if not is_extra else None,
                    'is_extra': is_extra
                }
            
            return None

        except Exception as e:
            logging.error(f"Error analyzing file: {str(e)}")
            return None

    def find_and_process_subtitles(self, video_path, new_video_path, file_info):
        """Find and embed subtitle files for the video."""
        try:
            video_dir = video_path.parent
            video_name = video_path.stem
            found_subs = []
            unmatched_subs = []
            
            # Search for subtitle files in the same directory and subdirectories
            for srt_file in video_dir.rglob('*.srt'):
                # Check if this subtitle might belong to our video
                if (video_name.lower() in srt_file.stem.lower() or
                    srt_file.stem.lower() in video_name.lower()):
                    found_subs.append(srt_file)
                else:
                    unmatched_subs.append(srt_file)
                    
            # Process unmatched subtitles
            for sub in unmatched_subs:
                try:
                    # Analyze subtitle file to determine if it's for a TV show or movie
                    sub_info = self.analyze_file(sub, 'tv_show')  # Try TV show first
                    if sub_info and 'show_name' in sub_info:
                        # It's a TV show subtitle
                        dest_dir = Path(config.JUNK_SUBTITLES_TV_DIR) / sanitize_filename(sub_info['show_name']) / f"Season {sub_info['season_num']}"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        new_sub_path = dest_dir / sub_info['filename'].replace(sub_info['filename'].suffix, '.srt')
                    else:
                        # Try as movie or move to general subtitles
                        sub_info = self.analyze_file(sub, 'movie')
                        if sub_info and 'title' in sub_info:
                            dest_dir = Path(config.JUNK_SUBTITLES_MOVIES_DIR)
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            new_sub_path = dest_dir / f"{sub_info['filename'].replace(sub_info['filename'].suffix, '.srt')}"
                        else:
                            # Couldn't identify, put in root of subtitles dir
                            new_sub_path = Path(config.JUNK_SUBTITLES_DIR) / sub.name
                    
                    # Move the subtitle file
                    sub.rename(new_sub_path)
                    log_operation("MOVE_SUBTITLE", str(sub), str(new_sub_path), "Unmatched subtitle moved to junk")
                except Exception as e:
                    logging.error(f"Error processing unmatched subtitle {sub}: {str(e)}")
            
            if not found_subs:
                return
            
            # Create a temporary file for the video with embedded subtitles
            temp_output = new_video_path.parent / f"temp_{new_video_path.name}"
            
            # Prepare ffmpeg command for subtitle embedding
            subtitle_maps = []
            subtitle_metadata = []
            
            for idx, sub in enumerate(found_subs, 1):
                subtitle_maps.extend(['-i', str(sub)])
                subtitle_metadata.extend([
                    f'-map {idx}:s',
                    f'-metadata:s:s:{idx-1} language=eng',
                    f'-metadata:s:s:{idx-1} title="Subtitle {idx}"'
                ])
            
            # Build the complete ffmpeg command
            cmd = [
                'ffmpeg', '-i', str(new_video_path),
                *[item for pair in zip(['-i'] * len(found_subs), map(str, found_subs)) for item in pair],
                '-map', '0:v', '-map', '0:a',
                *[f'-map {i}:s' for i in range(1, len(found_subs) + 1)],
                '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text',
                str(temp_output)
            ]
            
            # Execute ffmpeg command
            logging.info(f"Embedding {len(found_subs)} subtitle(s) into video...")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Replace original with the version with embedded subtitles
            temp_output.replace(new_video_path)
            
            # Log the subtitle embedding
            sub_info = f"Embedded {len(found_subs)} subtitle(s): {', '.join(s.name for s in found_subs)}"
            log_operation("SUBTITLE_EMBED", str(video_path), str(new_video_path), sub_info)
            
            # Delete the processed subtitle files
            for sub in found_subs:
                try:
                    sub.unlink()
                    log_operation("DELETE_SUBTITLE", str(sub), extra_info="Subtitle embedded and file removed")
                except Exception as e:
                    logging.error(f"Error deleting subtitle file {sub}: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Error processing subtitles for {video_path}: {str(e)}")

    def process_file(self, file_path):
        """Process a new file and organize it appropriately."""
        try:
            # Check if file still exists and is not in the destination directory
            if not file_path.exists() or str(file_path).startswith(str(config.DEST_BASE_DIR)):
                return

            logging.info(f"Processing new file: {file_path}")
            
            # Get media type
            media_type = get_media_type(file_path, file_path.name)
            
            if media_type == 'unknown':
                # Move to junk directory
                junk_path = config.JUNK_DIR / file_path.name
                file_path.rename(junk_path)
                logging.warning(f"Unknown media type, moved to junk: {file_path}")
                log_operation("MOVE_TO_JUNK", str(file_path), str(junk_path), "Unknown media type")
                return

            # Generate new filename and metadata using OpenAI
            file_info = self.analyze_file(file_path, media_type)
            if not file_info:
                logging.error(f"Could not analyze file: {file_path}")
                return
            
            # Create all necessary directories
            file_info['directory'].mkdir(parents=True, exist_ok=True)
            
            # Create final destination path
            new_path = file_info['directory'] / file_info['filename']
            
            # Move the file
            file_path.rename(new_path)
            logging.info(f"Successfully moved and renamed file to: {new_path}")
            log_operation("MOVE", str(file_path), str(new_path))

            # If it's a video file, find and process subtitles
            if file_info['directory'] == config.TV_SHOWS_DIR or file_info['directory'] == config.MOVIES_DIR:
                self.find_and_process_subtitles(file_path, new_path, file_info)

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")

    def generate_new_filename(self, file_path, media_type):
        """Generate a new filename using OpenAI API."""
        try:
            # Prepare the message for OpenAI
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Please analyze this filename and provide the proper name: {file_path.name}\nMedia type: {media_type}"}
            ]

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )

            # Get the suggested name from the response
            new_name = response.choices[0].message.content.strip()
            
            # Ensure we keep the original extension
            original_extension = file_path.suffix
            if not new_name.endswith(original_extension):
                new_name += original_extension

            return sanitize_filename(new_name)

        except Exception as e:
            logging.error(f"Error generating new filename: {str(e)}")
            return None

    def get_destination_directory(self, media_type):
        """Get the appropriate destination directory based on media type."""
        return {
            'movie': config.MOVIES_DIR,
            'tv_show': config.TV_SHOWS_DIR,
            'music': config.MUSIC_DIR,
            'software': config.SOFTWARE_DIR
        }.get(media_type)

def cleanup_source_directory(source_dir):
    """Move all remaining files and directories to junk folder."""
    source_path = Path(source_dir)
    
    # Skip if source directory doesn't exist
    if not source_path.exists():
        return
        
    logging.info("Cleaning up source directory...")
    
    # Process all remaining items
    for item in source_path.iterdir():
        try:
            if item.is_file():
                # Move file to junk
                dest_path = config.JUNK_DIR / item.name
                item.rename(dest_path)
                log_operation("CLEANUP_MOVE", str(item), str(dest_path), "Remaining file moved to junk")
            elif item.is_dir():
                # Move entire directory to junk
                dest_path = config.JUNK_DIR / item.name
                # Ensure we don't have naming conflicts
                if dest_path.exists():
                    dest_path = config.JUNK_DIR / f"{item.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                item.rename(dest_path)
                log_operation("CLEANUP_MOVE", str(item), str(dest_path), "Remaining directory moved to junk")
        except Exception as e:
            logging.error(f"Error moving item {item} to junk: {str(e)}")
            
    logging.info("Source directory cleanup completed")

def main():
    """Main function to start the file monitoring system."""
    load_dotenv()  # Load environment variables from .env file
    
    # Validate configuration
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    if not os.path.exists(config.SOURCE_DIR):
        raise ValueError(f"Source directory does not exist: {config.SOURCE_DIR}")

    # Create event handler and observer
    event_handler = MediaFileHandler()
    
    # Process any existing files in the source directory and its subdirectories
    logging.info("Recursively checking for existing files in source directory...")
    source_path = Path(config.SOURCE_DIR)
    for file_path in source_path.rglob('*'):
        if file_path.is_file():
            logging.info(f"Processing existing file: {file_path}")
            event_handler.process_file(file_path)
    
    # Clean up any remaining files and directories
    cleanup_source_directory(config.SOURCE_DIR)
    
    # Set up the observer for new files
    observer = Observer()
    observer.schedule(event_handler, config.SOURCE_DIR, recursive=True)
    
    # Start monitoring
    observer.start()
    logging.info(f"Started monitoring directory: {config.SOURCE_DIR}")
    
    try:
        cleanup_timer = 0
        while True:
            time.sleep(1)
            cleanup_timer += 1
            # Clean up source directory every 5 minutes
            if cleanup_timer >= 300:  # 300 seconds = 5 minutes
                cleanup_source_directory(config.SOURCE_DIR)
                cleanup_timer = 0
    except KeyboardInterrupt:
        observer.stop()
        # Do one final cleanup before stopping
        cleanup_source_directory(config.SOURCE_DIR)
        logging.info("Stopping directory monitoring")
    
    observer.join()

if __name__ == "__main__":
    main()
