#!/bin/bash

# Set the directory to check for images
IMAGE_DIR="images_input"

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
    pipenv run python process_stories.py

    EPISODE_NAME=$(ls -t _stories/*.md | head -1)

    git add -A
    git commit -am "$EPISODE_NAME"
    git push
done

echo "No more images to process."
