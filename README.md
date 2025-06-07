# GPT Namer

## Overview
GPT Namer is a Python-based project designed to organize and manage media files using AI-powered naming conventions.

## Usage
1. Ensure the `.env` file is properly configured with the required environment variables:
   - `MEDIA_SOURCE_DIR`: Path to the source directory for media files.
   - `MEDIA_DEST_DIR`: Path to the destination directory for organized media files.

2. Run the `run.sh` script:
   ```bash
   ./run.sh
   ```
   This script will:

   1. Set up the environment if not already configured.
   2. Load necessary environment variables.
   3. Run the main media organizer script.

## Prerequisites
- Python 3.12 or higher
- Bash shell


## Additional Scripts
- `install-service.sh`: Install the media organizer as a system service.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
