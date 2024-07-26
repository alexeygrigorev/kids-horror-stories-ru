import os
import base64
import requests
from pathlib import Path
from openai import OpenAI
import frontmatter
from generate_audio import main as generate_audio
import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from PIL import Image
from io import BytesIO

client = OpenAI()

S3_BUCKET_IMAGES = os.getenv("S3_BUCKET_IMAGES")
PROCESS_ONE = os.getenv("PROCESS_ONE", "1") == "1"

def download_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def download_image_from_s3_to_base64(bucket_name, object_key):
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    return base64.b64encode(response["Body"].read()).decode("utf-8")


def resize_image(image_data, size=(512, 512)):
    image = Image.open(BytesIO(image_data))
    image = image.resize(size, Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer


def create_story(base64_image):
    story_prompt = """
    Я хочу, чтоб ты рассказал страшилку. Я тебе присылаю фотографию, ты описываешь фотографию, а потом
    на основе этой картинки придумываешь страшилку. Страшную, что-нибудь из городского фольклора,
    городских историй ужасов. Конец не обязательно должен быть хорошим. И дай истории название.

    У истории должно быть 8-12 абзацев.

    Для названий не используй слова как "проклятый", "проклятье", "тайна". Не используй никакое форматирование
    для названия и для текста. Для slug используй короткое называние на английском, такое, которое можно использовать
    в URL.

    Следование формату обязательно.

    Формат:

    Название

    --- 

    slug

    ---

    История
    """

    story_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": story_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
    )

    story_raw = story_response.choices[0].message.content
    title, slug, story = story_raw.split("---")
    return title.strip(), slug.strip(), story.strip()


def create_illustration_prompt(story):
    def extract_first_two_paragraphs(text):
        paragraphs = text.split("\n\n")
        return "\n\n".join(paragraphs[:2])

    first_two_paragraphs = extract_first_two_paragraphs(story)
    prompt = f"""
    На основе текста из истории, создай детальное описание одной сцены на английском, а затем иллюстрацию
    на основе описания. Используй нейтральные обозначения для людей и животных, не имена, например,
    "мальчик" вместо "Ваня", "женщина" вместо "Анна", "собака" вместо "Жучка", и т.п.
    Если в тексте больше одной сцены, выбери только одну, и создай её детальное описание.

    Описание не должно включать в себя последовательность действий, а вместо этого фокусироваться на описании
    одной конкретной сцены.

    Иллюстрация будет использоваться как логотип для эпизода подкаста, поэтому детали должны быть крупным планом
    Не должно быть много объектов, только самые ключевые для описания сцены. Один или два человека, не больше.

    Текст:
    {first_two_paragraphs}

    Стиль иллюстрации:

    a flat, linear style with bold outlines and minimalistic, vibrant colors.
    The scene should include whimsical and slightly eerie elements, such as mountains with skeletal figures,
    simple trees, and small groups of people exploring or interacting with the environment.
    The overall aesthetic should combine a playful cartoonish feel with a touch of spookiness, similar
    to a light-hearted horror theme.

    Avoid adding text on the illustration.

    Only include the resulting prompt for the illustration, don't include the scene description.
    """.strip()

    illustration_prompt = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )

    return illustration_prompt.choices[0].message.content


def generate_illustration(prompt):
    illustration_response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return illustration_response.data[0].url


def get_next_story_id(output_dir):
    existing_files = list(output_dir.glob("*.md"))
    if not existing_files:
        return 1

    max_id = 0
    for file in existing_files:
        content = frontmatter.load(file)
        story_number = int(content.get("story_number", "0"))
        if story_number > max_id:
            max_id = story_number

    return max_id + 1


def save_story(title, slug, story, illustration_url, output_dir, story_id):
    formatted_slug = f"{str(story_id).zfill(3)}-{slug}"
    story_file = Path(output_dir) / f"{formatted_slug}.md"
    post = frontmatter.Post(story)
    post["title"] = title
    post["slug"] = formatted_slug
    post["illustration"] = f"/images/{formatted_slug}.jpg"
    post["story_number"] = str(story_id).zfill(3)
    post["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
    frontmatter.dump(post, story_file)
    print(f"Saved story: {story_file}")

    # Save illustration to the images folder
    image_folder = Path("images")
    image_folder.mkdir(exist_ok=True)
    illustration_path = image_folder / f"{formatted_slug}.jpg"

    # Fetch and resize the illustration
    response = requests.get(illustration_url)
    resized_image = resize_image(response.content)

    with open(illustration_path, "wb") as f:
        f.write(resized_image.getvalue())
    print(f"Saved resized illustration: {illustration_path}")


def process_image(image_path, output_dir):
    print(f"Processing image: {image_path}")
    base64_image = download_image_to_base64(image_path)
    title, slug, story = create_story(base64_image)
    illustration_prompt = create_illustration_prompt(story)
    illustration_url = generate_illustration(illustration_prompt)
    story_id = get_next_story_id(output_dir)
    save_story(title, slug, story, illustration_url, output_dir, story_id)
    generate_audio(f"{str(story_id).zfill(3)}-{slug}")
    return Path(image_path)


def process_image_from_s3(bucket_name, object_key, output_dir):
    print(f"Processing image from S3: {object_key}")
    base64_image = download_image_from_s3_to_base64(bucket_name, object_key)
    title, slug, story = create_story(base64_image)
    illustration_prompt = create_illustration_prompt(story)
    illustration_url = generate_illustration(illustration_prompt)
    story_id = get_next_story_id(output_dir)
    save_story(title, slug, story, illustration_url, output_dir, story_id)
    generate_audio(f"{str(story_id).zfill(3)}-{slug}")
    return object_key


def main():
    output_dir = Path("_stories")
    output_dir.mkdir(exist_ok=True)
    done_dir = Path("images_input") / "done"
    failed_dir = Path("images_input") / "failed"

    success_files = []
    failed_files = []

    if S3_BUCKET_IMAGES:
        s3 = boto3.client("s3")
        bucket_name, prefix = S3_BUCKET_IMAGES.split("/", 1)
        try:
            for obj in sorted(
                s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)["Contents"],
                key=lambda x: x["Key"],
            ):
                object_key = obj["Key"]
                if object_key.endswith((".jpg", ".jpeg", ".png")):
                    try:
                        success_file = process_image_from_s3(
                            bucket_name, object_key, output_dir
                        )
                        success_files.append(success_file)
                        if PROCESS_ONE:
                            break
                    except Exception as e:
                        error_message = f"Failed to process {object_key}: {str(e)}"
                        print(error_message)
                        failed_files.append((object_key, error_message))
                        if PROCESS_ONE:
                            break
        except (NoCredentialsError, ClientError) as e:
            print(f"Failed to access S3 bucket: {str(e)}")
    else:
        input_dir = Path("images_input")
        try:
            for image_file in sorted(input_dir.glob("*")):
                if image_file.is_file() and image_file.suffix.lower() in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                ]:
                    success_file = process_image(image_file, output_dir)
                    success_files.append(success_file)

                    if PROCESS_ONE:
                        break
        except Exception as e:
            error_message = f"Failed to process {image_file.name}: {str(e)}"
            print(error_message)
            failed_files.append((image_file, error_message))

    if failed_files:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        Path("logs").mkdir(exist_ok=True)
        log_file = Path("logs") / f"logs-{timestamp}.txt"
        with open(log_file, "w") as log:
            for file, error in failed_files:
                log.write(f"{file}: {error}\n")
                if S3_BUCKET_IMAGES:
                    s3.copy_object(
                        Bucket=bucket_name,
                        CopySource={"Bucket": bucket_name, "Key": file},
                        Key=f"failed/{file.split('/')[-1]}",
                    )
                    s3.delete_object(Bucket=bucket_name, Key=file)
                else:
                    failed_dir.mkdir(exist_ok=True)
                    new_location = failed_dir / file.name
                    file.rename(new_location)
                    print(f"Moved file to: {new_location}")
        print(f"Log file created: {log_file}")

    # Move all successfully processed files
    for file in success_files:
        if S3_BUCKET_IMAGES:
            s3.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": file},
                Key=f"done/{file.split('/')[-1]}",
            )
            s3.delete_object(Bucket=bucket_name, Key=file)
        else:
            done_dir.mkdir(exist_ok=True)
            new_location = done_dir / file.name
            file.rename(new_location)
            print(f"Moved file to: {new_location}")


if __name__ == "__main__":
    main()
