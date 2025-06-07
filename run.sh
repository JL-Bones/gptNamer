#!/bin/bash

# Get the absolute path of the script directory if not already set
if [ -z "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
fi

# Set the working directory to the script's location
cd "${SCRIPT_DIR}"

# Function to load environment variables
load_env() {
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ $line =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            
            # Remove any trailing comments
            line=$(echo "$line" | sed 's/#.*$//')
            
            # Extract variable and value
            if [[ $line =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
                
                # Remove leading/trailing whitespace and quotes
                key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                value=$(echo "$value" | sed -e 's/^[[:space:]"]*//g' -e 's/[[:space:]"]*$//g')
                
                # Export the variable
                export "$key=$value"
            fi
        done < "${SCRIPT_DIR}/.env"
    else
        echo "$(date) - Error: .env file not found at ${SCRIPT_DIR}/.env" >> "${SCRIPT_DIR}/organizer.log"
        exit 1
    fi
}

# Add timestamp to log
echo "$(date) - Starting media organizer service" >> "${SCRIPT_DIR}/organizer.log"
echo "$(date) - Script directory: ${SCRIPT_DIR}" >> "${SCRIPT_DIR}/organizer.log"

# Create virtual environment if it doesn't exist
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "$(date) - Creating virtual environment..." >> "${SCRIPT_DIR}/organizer.log"
    python3 -m venv "${SCRIPT_DIR}/venv"
    source "${SCRIPT_DIR}/venv/bin/activate"
    pip install -r "${SCRIPT_DIR}/requirements.txt" >> "${SCRIPT_DIR}/organizer.log" 2>&1
else
    source "${SCRIPT_DIR}/venv/bin/activate"
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed. Attempting to install..."
    sudo apt-get update && sudo apt-get install -y ffmpeg
fi

# Load environment variables
load_env

# Validate required environment variables
if [ -z "$MEDIA_SOURCE_DIR" ] || [ -z "$MEDIA_DEST_DIR" ]; then
    echo "$(date) - Error: MEDIA_SOURCE_DIR and MEDIA_DEST_DIR must be set in .env file" >> "${SCRIPT_DIR}/organizer.log"
    exit 1
fi

# Log the environment variables
echo "$(date) - Environment variables loaded:" >> "${SCRIPT_DIR}/organizer.log"
echo "MEDIA_SOURCE_DIR=$MEDIA_SOURCE_DIR" >> "${SCRIPT_DIR}/organizer.log"
echo "MEDIA_DEST_DIR=$MEDIA_DEST_DIR" >> "${SCRIPT_DIR}/organizer.log"

# Validate required environment variables
if [ -z "$MEDIA_SOURCE_DIR" ] || [ -z "$MEDIA_DEST_DIR" ]; then
    echo "Error: MEDIA_SOURCE_DIR and MEDIA_DEST_DIR must be set in .env file" >> organizer.log
    exit 1
fi

# Create source and destination directories if they don't exist
mkdir -p "$MEDIA_SOURCE_DIR" "$MEDIA_DEST_DIR"

# Ensure correct permissions
sudo chown -R $USER:$USER "$MEDIA_SOURCE_DIR" "$MEDIA_DEST_DIR"

# Log the directories being used
echo "$(date) - Using source directory: $MEDIA_SOURCE_DIR" >> organizer.log
echo "$(date) - Using destination directory: $MEDIA_DEST_DIR" >> organizer.log

# Run the media organizer
echo "$(date) - Starting media organizer..." >> "${SCRIPT_DIR}/organizer.log"
python "${SCRIPT_DIR}/main.py"
