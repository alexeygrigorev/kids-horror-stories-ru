#!/bin/bash

# Set the directory to check for images
IMAGE_DIR="images_input"
LOG_DIR="logs"

# Function to check if there are any image files in the directory
check_for_images() {
    if [ -n "$(ls -A $IMAGE_DIR/*.jpg 2>/dev/null)" ] || [ -n "$(ls -A $IMAGE_DIR/*.jpeg 2>/dev/null)" ] || [ -n "$(ls -A $IMAGE_DIR/*.png 2>/dev/null)" ]; then
        return 0 # Images found
    else
        return 1 # No images found
    fi
}

# Loop while there are images in the directory
while check_for_images; do
    # Run the Python script
    pipenv run python process_stories.py
    
    # Check for logs to find the episode name
    if [ -d "$LOG_DIR" ] && [ -n "$(ls -A $LOG_DIR 2>/dev/null)" ]; then
        LATEST_LOG=$(ls -t $LOG_DIR | head -1)
        EPISODE_NAME=$(grep -oP '(?<=title: ).*' "_stories/*.md" | tail -1)
    else
        EPISODE_NAME="Processed episode"
    fi

    # Commit and push changes to Git
    git add -A
    git commit -am "$EPISODE_NAME"
    git push
done

echo "No more images to process."
