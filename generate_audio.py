import os
import sys
from pathlib import Path

import boto3
import frontmatter

from openai import OpenAI
from botocore.exceptions import NoCredentialsError

import mutagen


client = OpenAI()


S3_BUCKET = os.getenv("S3_BUCKET", "kids-horror-stories-ru")
S3_REGION = "eu-west-1"

s3_client = boto3.client("s3", region_name=S3_REGION)


def generate_tts(text, file_name):
    temp_dir = Path(".") / "temp_audio"
    temp_dir.mkdir(exist_ok=True)
    speech_file_path = temp_dir / f"{file_name}.mp3"

    if speech_file_path.exists():
        print(f"Audio file already exists: {speech_file_path}")
        return speech_file_path

    try:
        response = client.audio.speech.create(model="tts-1", voice="onyx", input=text)
        response.stream_to_file(speech_file_path)
        return speech_file_path
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return None


def get_s3_url(s3_file):
    return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_file}"


def upload_to_s3(local_file, s3_file):
    try:
        # Check if the file already exists in S3
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_file)
            print(f"File already exists in S3: {s3_file}")
            return get_s3_url(s3_file)
        except:
            # File doesn't exist, proceed with upload
            s3_client.upload_file(
                local_file,
                S3_BUCKET,
                s3_file,
                # ExtraArgs={'ACL': 'public-read'}
            )
            print(f"Upload Successful: {s3_file}")
            return get_s3_url(s3_file)
    except FileNotFoundError:
        print("The file was not found")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None


def get_audio_info(file_path):
    audio = mutagen.File(file_path)
    size = os.path.getsize(file_path)
    duration = int(audio.info.length)
    return size, f"{duration // 60:02d}:{duration % 60:02d}"


def process_story(file_path):
    try:
        print("Processing story:", file_path)
        post = frontmatter.load(file_path)

        audio_file_name = Path(file_path).stem

        print(f"Generating audio for {audio_file_name}...")
        audio_file_path = generate_tts(post.content, audio_file_name)

        if audio_file_path:
            s3_url = upload_to_s3(audio_file_path, f"audio/{audio_file_name}.mp3")

            if s3_url:
                if post.get("audio_url") != s3_url:
                    post["audio_url"] = s3_url

                    audio_size, duration = get_audio_info(audio_file_path)
                    post["audio_size"] = audio_size
                    post["duration"] = duration

                    frontmatter.dump(post, file_path)
                    print(f"Updated {file_path} with audio URL: {s3_url}")
                    print("Frontmatter now includes 'audio_url' field.")
                else:
                    print(
                        f"Audio URL in frontmatter is already up to date for {file_path}"
                    )
            else:
                print(f"Failed to upload audio for {file_path}")
        else:
            print(f"Failed to generate audio for {file_path}")
    except Exception as e:
        print(f"Error processing story {file_path}: {e}")


def find_story_by_id(story_id):
    stories_dir = Path("_stories")
    for story_file in stories_dir.glob("*.md"):
        if story_file.stem.startswith(story_id):
            return story_file
    return None


def main(story_id):
    story_file = find_story_by_id(story_id)
    if story_file:
        process_story(story_file)
    else:
        print(f"No story found with ID: {story_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_audio.py <story_id>")
        sys.exit(1)

    story_id = sys.argv[1]
    main(story_id)
