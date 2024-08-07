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


output_image_size = 512
output_image_quality = 80


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


def resize_and_save_original_image(input_path, output_path, size=output_image_size):
    with Image.open(input_path) as img:
        img.thumbnail((size, size), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=output_image_quality)


def create_story(base64_image):
    story_prompt = """
    Я хочу, чтоб ты рассказал страшилку. Я тебе присылаю фотографию, ты описываешь фотографию, а потом
    на основе этой картинки придумываешь страшилку. Страшную, что-нибудь из городского фольклора,
    городских историй ужасов. Конец не обязательно должен быть хорошим. И дай истории название.

    У истории должно быть 8-12 абзацев.

    Для названий не используй слова как "проклятый", "проклятье", "мрачный", "заброшенный", "тайна", "тень", "ужас", "шёпот".
    Не используй никакое форматирование для названия и для текста.
    Для slug используй короткое называние на английском, такое, которое можно использовать в URL.

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
    на основе описания. Используй нейтральные обозначения для людей и животных, не имена.
    Если имя главного героя женское, используй "женщина" или "девочка".
    Если имя главного героя мужское, используй "мужчина" или "мальчик".
    Если в тексте больше одной сцены, выбери только одну, и создай её детальное описание.

    Описание не должно включать в себя последовательность действий, а вместо этого фокусироваться на описании
    одной конкретной сцены.

    Иллюстрация будет использоваться как логотип для эпизода подкаста, поэтому детали должны быть крупным планом
    Не должно быть много объектов, только самые ключевые для описания сцены. Один или два человека, не больше.

    Текст:
    {first_two_paragraphs}

    Стиль иллюстрации:

    a flat, linear style with bold outlines and minimalistic, vibrant colors.
    The scene should include whimsical and slightly eerie elements.
    The overall aesthetic should combine a playful cartoonish feel
    with a touch of spookiness, similar to a light-hearted horror theme.

    Avoid adding text on the illustration.

    Only include the resulting prompt for the illustration, don't include the scene description.
    """.strip()

    illustration_prompt = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )

    return illustration_prompt.choices[0].message.content


def edit_story(story):
    prompt = f"""
    Ты опытный редактор историй ужасов, в совершенстве владеющий русским.
    Исправь эту историю. Сделай так, чтобы вся грамматика была понятна и корректна.
    И чтобы не было странных выражений. Если пропадутся выражения,
    которые в русском обычно не употребляются, или непонятные выражения,
    замени их на более понятные или более употребмые, и более подходящие
    в контексте истории.
    Начинай сразу с истории, не включай в ответ ничего кроме этого.
    
    История:

    {story}
    """.strip()

    result = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}]
    )

    return result.choices[0].message.content

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


def save_story(
    title, slug, story, illustration_url, output_dir, story_id, original_image_path
):
    formatted_slug = f"{str(story_id).zfill(3)}-{slug}"
    story_file = Path(output_dir) / f"{formatted_slug}.md"
    post = frontmatter.Post(story)
    post["title"] = title
    post["slug"] = formatted_slug
    post["illustration"] = f"/images/{formatted_slug}.jpg"
    post["story_number"] = str(story_id).zfill(3)
    post["date"] = datetime.datetime.now().strftime("%Y-%m-%d")

    # Save and add original image information
    image_folder = Path("images")
    image_folder.mkdir(exist_ok=True)
    original_image_output_path = image_folder / f"{formatted_slug}-source.jpg"
    resize_and_save_original_image(original_image_path, original_image_output_path)
    post["image_source"] = f"/images/{formatted_slug}-source.jpg"

    frontmatter.dump(post, story_file)
    print(f"Saved story: {story_file}")

    # Save illustration to the images folder
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
    story = edit_story(story)
    illustration_prompt = create_illustration_prompt(story)
    illustration_url = generate_illustration(illustration_prompt)
    story_id = get_next_story_id(output_dir)
    save_story(title, slug, story, illustration_url, output_dir, story_id, image_path)
    generate_audio(f"{str(story_id).zfill(3)}-{slug}")
    return Path(image_path)


def process_image_from_s3(bucket_name, object_key, output_dir):
    print(f"Processing image from S3: {object_key}")
    s3 = boto3.client("s3")

    # Download the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    image_data = response["Body"].read()

    # Save the image temporarily
    temp_image_path = Path("temp_image.jpg")
    with open(temp_image_path, "wb") as f:
        f.write(image_data)

    base64_image = base64.b64encode(image_data).decode("utf-8")
    title, slug, story = create_story(base64_image)
    story = edit_story(story)
    illustration_prompt = create_illustration_prompt(story)
    illustration_url = generate_illustration(illustration_prompt)
    story_id = get_next_story_id(output_dir)
    save_story(
        title, slug, story, illustration_url, output_dir, story_id, temp_image_path
    )
    generate_audio(f"{str(story_id).zfill(3)}-{slug}")

    # Remove the temporary image
    temp_image_path.unlink()

    return object_key


def main():
    output_dir = Path("_stories")
    output_dir.mkdir(exist_ok=True)

    success_file = None
    failed_file = None

    try:
        if S3_BUCKET_IMAGES:
            s3 = boto3.client("s3")
            bucket_name = S3_BUCKET_IMAGES.split("/")[0]
            prefix = "input/"
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

            if "Contents" in response:
                objects = sorted(response["Contents"], key=lambda x: x["Key"])
                object_key_good = None
                for obj in objects:
                    object_key = obj["Key"]
                    if object_key.lower().endswith((".jpg", ".jpeg", ".png")):
                        object_key_good = object_key
                        break
                
                if object_key_good is not None:
                    success_file = process_image_from_s3(
                        bucket_name, object_key, output_dir
                    )
            else:
                print(f"No files found in {bucket_name}/{prefix}")
        else:
            input_dir = Path("images_input")
            image_files = sorted(input_dir.glob("*"))

            image_file_good = None
            for image_file in image_files:
                if image_file.is_file() and image_file.suffix.lower() in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                ]:
                    image_file_good = image_file
                    break

            success_file = process_image(image_file_good, output_dir)
    except Exception as e:
        error_message = f"Failed to process: {str(e)}"
        print(error_message)
        failed_file = (object_key if S3_BUCKET_IMAGES else image_file, error_message)

    if failed_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        Path("logs").mkdir(exist_ok=True)
        log_file = Path("logs") / f"logs-{timestamp}.txt"
        with open(log_file, "w") as log:
            log.write(f"{failed_file[0]}: {failed_file[1]}\n")
            if S3_BUCKET_IMAGES:
                s3.copy_object(
                    Bucket=bucket_name,
                    CopySource={"Bucket": bucket_name, "Key": failed_file[0]},
                    Key=f"failed/{failed_file[0].split('/')[-1]}",
                )
                s3.delete_object(Bucket=bucket_name, Key=failed_file[0])
            else:
                failed_dir = Path("images_input") / "failed"
                failed_dir.mkdir(exist_ok=True)
                new_location = failed_dir / failed_file[0].name
                failed_file[0].rename(new_location)
                print(f"Moved file to: {new_location}")
        print(f"Log file created: {log_file}")

    if success_file:
        if S3_BUCKET_IMAGES:
            s3.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": success_file},
                Key=f"done/{success_file.split('/')[-1]}",
            )
            s3.delete_object(Bucket=bucket_name, Key=success_file)
        else:
            done_dir = Path("images_input") / "done"
            done_dir.mkdir(exist_ok=True)
            new_location = done_dir / success_file.name
            success_file.rename(new_location)
            print(f"Moved file to: {new_location}")


if __name__ == "__main__":
    main()
