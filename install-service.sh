#!/bin/bash

# Make sure we're running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Copy service file to systemd directory
cp media-organizer.service /etc/systemd/system/

# Reload systemd daemon
systemctl daemon-reload

# Enable and start the service
systemctl enable media-organizer.service
systemctl start media-organizer.service

echo "Media organizer service has been installed and started."
echo "To check status: systemctl status media-organizer"
echo "To view logs: journalctl -u media-organizer -f"
