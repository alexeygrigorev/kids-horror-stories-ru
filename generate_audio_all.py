import os
from pathlib import Path
import frontmatter
from tqdm import tqdm

from generate_audio import main as generate_audio_main


def find_stories_without_audio():
    stories_dir = Path("_stories")
    stories_without_audio = []
    for story_file in stories_dir.glob("*.md"):
        post = frontmatter.load(story_file)
        if "audio_url" not in post:
            stories_without_audio.append(story_file.stem.split("-")[0])
    return stories_without_audio


def process_stories(story_ids):
    for story_id in tqdm(story_ids, desc="Processing stories"):
        try:
            generate_audio_main(story_id)
        except Exception as e:
            print(f"Error processing story {story_id}: {e}")


def main():
    stories_to_process = find_stories_without_audio()
    print(f"Found {len(stories_to_process)} stories without audio.")

    if stories_to_process:
        process_stories(stories_to_process)
        print("All stories processed.")
    else:
        print("No stories to process.")


if __name__ == "__main__":
    main()
