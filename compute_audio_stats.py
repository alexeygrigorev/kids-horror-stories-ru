import os
import sys
from pathlib import Path
import mutagen
import frontmatter
from tqdm import tqdm


def get_audio_info(file_path):
    audio = mutagen.File(file_path)
    size = os.path.getsize(file_path)
    duration = int(audio.info.length)
    return size, f"{duration // 60:02d}:{duration % 60:02d}"


def update_story_frontmatter(story_file, audio_size, duration):
    post = frontmatter.load(story_file)
    post["audio_size"] = audio_size
    post["duration"] = duration
    frontmatter.dump(post, story_file)
    print(f"Updated {story_file} with audio size and duration")


def find_audio_file(temp_audio_dir, story_id):
    possible_names = [f"{story_id}.mp3", f"{story_id}-*.mp3", f"*-{story_id}-*.mp3"]
    for pattern in possible_names:
        matches = list(temp_audio_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def find_story_file(stories_dir, story_id):
    possible_names = [f"{story_id}.md", f"{story_id}-*.md", f"*-{story_id}-*.md"]
    for pattern in possible_names:
        matches = list(stories_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def process_audio_file(audio_file, stories_dir, story_id):
    if not audio_file.exists():
        print(f"Audio file not found: {audio_file}")
        return

    audio_size, duration = get_audio_info(audio_file)

    story_file = find_story_file(stories_dir, story_id)

    if story_file:
        update_story_frontmatter(story_file, audio_size, duration)
    else:
        print(f"No corresponding story file found for story ID: {story_id}")


def process_audio_files(story_id=None):
    temp_audio_dir = Path("temp_audio")
    stories_dir = Path("_stories")

    if not temp_audio_dir.exists():
        print(f"Error: The directory {temp_audio_dir} does not exist.")
        return

    if story_id:
        audio_file = find_audio_file(temp_audio_dir, story_id)
        if audio_file:
            process_audio_file(audio_file, stories_dir, story_id)
        else:
            print(f"No audio file found for story ID: {story_id}")
            print(f"Searched in: {temp_audio_dir}")
            print(f"Existing audio files: {list(temp_audio_dir.glob('*.mp3'))}")
    else:
        audio_files = list(temp_audio_dir.glob("*.mp3"))
        for audio_file in tqdm(audio_files, desc="Processing audio files"):
            story_id = audio_file.stem.split("-")[0]
            process_audio_file(audio_file, stories_dir, story_id)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        story_id = sys.argv[1]
        print(f"Processing audio for story ID: {story_id}")
        process_audio_files(story_id)
    else:
        print("Processing all audio files")
        process_audio_files()
