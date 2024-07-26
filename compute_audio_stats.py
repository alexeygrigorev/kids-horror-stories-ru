import os
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
    post['audio_size'] = audio_size
    post['duration'] = duration
    frontmatter.dump(post, story_file)
    print(f"Updated {story_file} with audio size and duration")

def find_matching_story_file(stories_dir, audio_file_stem):
    for story_file in stories_dir.glob("*.md"):
        if story_file.stem.startswith(audio_file_stem):
            return story_file
    return None

def process_audio_files():
    temp_audio_dir = Path("temp_audio")
    stories_dir = Path("_stories")

    audio_files = list(temp_audio_dir.glob("*.mp3"))
    
    for audio_file in tqdm(audio_files, desc="Processing audio files"):
        audio_size, duration = get_audio_info(audio_file)
        
        # Find corresponding story file
        audio_file_stem = audio_file.stem.split('-')[0]  # Get the ID part
        story_file = find_matching_story_file(stories_dir, audio_file_stem)
        
        if story_file:
            update_story_frontmatter(story_file, audio_size, duration)
        else:
            print(f"No corresponding story file found for {audio_file}")

if __name__ == "__main__":
    process_audio_files()